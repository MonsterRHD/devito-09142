"""
Transport layer for distributed data redistribution.

This module knows nothing about indexing or `Data`; it only moves contiguous
buffers between MPI ranks. The single primitive, `sparse_exchange`, performs a
sparse "all-to-some" exchange in which only the ranks that actually share data
exchange payloads.

Communication identity
----------------------
Every exchange runs inside a `Channel` -- an isolated, reusable communication
identity content-addressed by the routing it serves (a particular get, put or
structured redistribution on particular data). Channels are shared by the
corresponding call on every rank, so both sides of every message derive the
same MPI tags without any handshake.

Each `with channel(comm)` call block binds a fresh *sequence number* and with
it a fresh block of four MPI tags -- (envelope, payload) times (header, value).
Hence:

* concurrent calls on different channels (different `Data`, different index
  plans, different redistribution regions, different dtypes) use disjoint tag
  sets and can never consume each other's messages, even though they share one
  communicator;
* consecutive calls on the same channel always run on fresh tags, so a
  message orphaned by a failed call can never be parsed by a later call;
* nested calls (different channels) are simply independent.

No tagless collective is used anywhere, so two threads may run exchanges
concurrently without their collective calls mismatching across ranks.

Wire protocol
-------------
Each exchange phase consists of two strictly paired rounds:

1. a fixed-size *envelope* is sent between every ordered pair of ranks
   (`[element_count, consensus_code, wire_itemsize, magic]`; a zero element
   count means "nothing for you"). Each rank therefore knows, without probing
   or a collective, that it will receive exactly `nprocs - 1` envelopes;
2. the actual payloads then flow point-to-point, one message per non-zero
   envelope count. The self rank never enters MPI: its envelope and payload
   are delivered through a local fast path using the same per-source keys.

The envelope also carries the rank-local consensus code (out-of-bounds /
duplicate target), so all ranks reach the same verdict before the payload
round: on error every rank skips its payloads while still completing the
phase, and no non-blocking request is ever left in flight.
"""

import contextlib
import hashlib
import threading
import weakref

import numpy as np

from devito.mpi import MPI
from devito.tools import mpi4py_mapper

__all__ = ['CONSENSUS_MESSAGES', 'Channel', 'DUP_CODE', 'OOB_CODE',
           'channel_for', 'join_consensus_codes', 'sparse_exchange']

# ---------------------------------------------------------------------------
# Consensus codes (carried by the envelopes, identical vocabulary on all ranks)
# ---------------------------------------------------------------------------

OOB_CODE = 1
DUP_CODE = 2

CONSENSUS_MESSAGES = {
    OOB_CODE: "Advanced index contains out-of-bounds global indices",
    DUP_CODE: "Duplicate global indices in distributed assignment",
}


def join_consensus_codes(codes):
    """Build the all-ranks error message from a vector of consensus codes."""
    return "; ".join(f"rank {r}: {CONSENSUS_MESSAGES[int(c)]}"
                     for r, c in enumerate(codes) if c)


# ---------------------------------------------------------------------------
# Communication identity
# ---------------------------------------------------------------------------

# Stay clear of the low tag numbers (halo traffic uses tag 0). Four tags are
# used per call: (envelope, payload) for the header phase and the same pair
# for the value phase.
_TAG_BASE = 128
_TAGS_PER_CALL = 4

# A fixed-size int64 envelope: [element count, consensus code, itemsize, magic]
_ENVELOPE_FIELDS = 4

_GOLDEN1 = 0x9E3779B97F4A7C15
_GOLDEN2 = 0xBF58476D1CE4E5B9
_MASK63 = 0x7FFFFFFFFFFFFFFF

# Per-communicator channel registries. Communicators are weak-referenced so
# the tables die with them; a plain id-keyed fallback is used for communicator
# objects that cannot be weak-referenced.
_registry_lock = threading.Lock()
_registry = weakref.WeakKeyDictionary()
_id_registry = {}


class Channel:

    """
    An isolated, reusable communication identity for one logical routing.

    Channels are obtained through `channel_for`, keyed by a content-addressed
    byte signature that is identical on every rank participating in the
    routing. A channel carries only a hash, a lock and a call counter; it
    never holds per-call request state, so it is safe to reuse after a failed
    call and cannot leak the state of one call into the next.

    Calls are serialized per channel with an `RLock` (the same plan cannot be
    driven twice concurrently from one process), and each call is bound to a
    fresh sequence number, hence fresh tags.
    """

    __slots__ = ('key', 'hash', 'lock', '_seq')

    def __init__(self, key):
        self.key = bytes(key)
        digest = hashlib.blake2b(self.key, digest_size=8).digest()
        self.hash = int.from_bytes(digest, 'little') & _MASK63
        self.lock = threading.RLock()
        self._seq = 0

    def __call__(self, comm):
        """Begin a new call: acquire the channel lock and bind a tag block."""
        self.lock.acquire()
        try:
            call = _Call(self, comm, self._seq)
            self._seq += 1
            return call
        except BaseException:
            self.lock.release()
            raise

    def __repr__(self):
        return f"Channel(seq={self._seq}, key={self.key.hex()})"


class _Call:

    """
    One in-flight channel call: its sequence number and its four MPI tags.

    The call object is the only place per-call communication state exists;
    it disappears when the `with` block ends, taking every request and buffer
    reference with it.
    """

    __slots__ = ('channel', 'seq', 'tags')

    def __init__(self, channel, comm, seq):
        self.channel = channel
        self.seq = seq
        ub = _tag_ub(comm)
        nblocks = (ub - _TAG_BASE + 1) // _TAGS_PER_CALL
        block = (channel.hash + seq) % nblocks
        self.tags = tuple(_TAG_BASE + block * _TAGS_PER_CALL + i
                          for i in range(_TAGS_PER_CALL))

    def magic(self, tag):
        """63-bit check value expected on a message tagged `tag` of this call."""
        x = (self.channel.hash ^ ((self.seq + 1) * _GOLDEN1)
             ^ ((tag + 1) * _GOLDEN2))
        return int(x & _MASK63)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.channel.lock.release()
        return False


def channel_for(comm, key):
    """
    Return the channel for `key` on `comm`, creating it on first use.

    The same `key` on every rank (identical bytes, derived from the routing
    content, never from process-local object ids) resolves to channels that
    hash to the same tags.
    """
    key = bytes(key)
    with _registry_lock:
        try:
            table = _registry.get(comm)
            if table is None:
                table = {}
                _registry[comm] = table
        except TypeError:
            # The communicator object does not support weak references
            table = _id_registry.setdefault(id(comm), {})
        channel = table.get(key)
        if channel is None:
            channel = Channel(key)
            table[key] = channel
        return channel


def _tag_ub(comm):
    """Largest legal MPI tag on `comm` (the MPI-standard floor is 32767)."""
    try:
        ub = comm.Get_attr(MPI.TAG_UB)
    except Exception:
        ub = None
    return int(ub) if ub else 32767


# ---------------------------------------------------------------------------
# Request lifecycle
# ---------------------------------------------------------------------------

def _drain_requests(requests):
    """
    Cancel, complete and release every unfinished request in `requests`.

    Called from an error path so that a failed exchange leaves no nonblocking
    send or receive that could later match another call's message.
    """
    for request in requests:
        if request is None:
            continue
        with contextlib.suppress(Exception):
            if not request.Test():
                request.Cancel()
        with contextlib.suppress(Exception):
            request.Wait()
        with contextlib.suppress(Exception):
            request.Free()


# ---------------------------------------------------------------------------
# Exchange
# ---------------------------------------------------------------------------

def sparse_exchange(comm, sendbufs, dtype, call, step, code=0):
    """
    Sparse "all-to-some" exchange of contiguous buffers.

    Each rank sends a buffer to each peer listed in `sendbufs` and receives
    from whichever ranks actually send to it, as announced by the per-peer
    envelopes. Payloads move strictly point-to-point; an entry for the caller's
    own rank is delivered locally, bypassing MPI, under the same source key.

    Parameters
    ----------
    comm : MPI communicator
        The communicator over which to exchange.
    sendbufs : dict
        Maps a destination rank to the buffer (a NumPy array) to send it. An
        entry for the caller's own rank is delivered locally. Empty buffers
        are skipped.
    dtype : numpy.dtype
        Element type shared by every buffer.
    call : _Call
        The active channel call (a `with channel(comm):` block); it provides
        the isolated, per-call tags and magic.
    step : int
        `0` for the header phase of the call, `1` for the value phase.
    code : int, optional
        This rank's consensus code for the call (`0` = no error). It is
        fanned out with the envelopes and aggregated on every rank.

    Returns
    -------
    recvd : dict
        Maps each source rank to the 1D buffer received from it (including
        the self rank through the local fast path). The caller reshapes using
        its known payload shape.
    codes : numpy.ndarray or None
        The consensus code of every rank, or `None` in the single-process
        serial fast path where no MPI takes place.
    """
    try:
        rank = comm.Get_rank()
        nprocs = comm.Get_size()
    except Exception:
        rank, nprocs = 0, 1

    # Same byte-equivalent wire type as the halo exchange for builds lacking
    # a native MPI datatype (e.g. float16); inferred per buffer by mpi4py.
    wire = np.dtype(mpi4py_mapper.get(np.dtype(dtype).type, dtype))

    # Resolve, locally, how much (if anything) we send to every destination
    counts = np.zeros(max(nprocs, 1), dtype=np.int64)
    prepared = {}
    recvd = {}

    local = sendbufs.get(rank)
    if local is not None and local.size:
        counts[rank] = local.size
        recvd[rank] = np.ravel(np.ascontiguousarray(local))

    for peer, buf in sendbufs.items():
        if peer == rank:
            continue
        buf = np.ascontiguousarray(buf)
        if buf.size:
            counts[peer] = buf.size
            prepared[peer] = buf

    # Single process: only the self fast path exists, no MPI at all
    if nprocs <= 1:
        return recvd, None

    env_tag, pay_tag = call.tags[step*2], call.tags[step*2 + 1]
    env_magic = call.magic(env_tag)
    peers = [r for r in range(nprocs) if r != rank]

    # Round 1: one fixed-size envelope per ordered pair of ranks. All receives
    # are posted before any send, so matching is deadlock-free and every rank
    # knows it will receive exactly nprocs-1 envelopes.
    env_recv_bufs = [np.empty(_ENVELOPE_FIELDS, dtype=np.int64)
                     for _ in peers]
    env_recv_reqs = []
    try:
        for peer, buf in zip(peers, env_recv_bufs, strict=True):
            env_recv_reqs.append(comm.Irecv(buf, source=peer, tag=env_tag))
    except BaseException:
        _drain_requests(env_recv_reqs)
        raise

    env_send_bufs = []
    env_send_reqs = []
    try:
        for peer in peers:
            envelope = np.array([counts[peer], int(code), wire.itemsize,
                                 env_magic], dtype=np.int64)
            env_send_bufs.append(envelope)
            env_send_reqs.append(comm.Isend(envelope, dest=peer, tag=env_tag))
    except BaseException:
        _drain_requests(env_send_reqs + env_recv_reqs)
        raise

    try:
        MPI.Request.Waitall(env_recv_reqs)
    except BaseException:
        _drain_requests(env_send_reqs + env_recv_reqs)
        raise

    codes = np.zeros(nprocs, dtype=np.int64)
    codes[rank] = code
    expected = {}
    for peer, envelope in zip(peers, env_recv_bufs, strict=True):
        count, peer_code, peer_itemsize, peer_magic = envelope
        # A mismatched magic means another exchange's message carries this
        # tag (hash collision or an orphaned call); refuse to consume it.
        if peer_magic != env_magic or peer_itemsize != wire.itemsize:
            _drain_requests(env_send_reqs)
            raise RuntimeError(
                "distributed exchange received an envelope from a different "
                "communication context (tag/magic mismatch); aborting rather "
                "than consuming another exchange's message"
            )
        codes[peer] = peer_code
        if count:
            expected[peer] = int(count)

    # Round 2: announce nothing more than the non-zero envelopes promised,
    # point-to-point. Receives are posted before sends so a sender failure
    # never blocks a receiver and every request is cancellable as a set.
    pay_recv_bufs = {}
    pay_recv_reqs = []
    try:
        for peer, count in expected.items():
            buf = np.empty(count, dtype=wire)
            pay_recv_bufs[peer] = buf
            pay_recv_reqs.append(comm.Irecv(buf, source=peer, tag=pay_tag))
    except BaseException:
        _drain_requests(pay_recv_reqs + env_send_reqs)
        raise

    pay_send_bufs = [buf.view(wire) for buf in prepared.values()]
    pay_send_reqs = []
    try:
        for peer, buf in zip(prepared, pay_send_bufs, strict=True):
            pay_send_reqs.append(comm.Isend(buf, dest=peer, tag=pay_tag))
    except BaseException:
        _drain_requests(pay_send_reqs + pay_recv_reqs + env_send_reqs)
        raise

    try:
        MPI.Request.Waitall(pay_recv_reqs)
    except BaseException:
        _drain_requests(pay_send_reqs + pay_recv_reqs + env_send_reqs)
        raise
    try:
        MPI.Request.Waitall(pay_send_reqs)
    except BaseException:
        _drain_requests(pay_send_reqs)
        raise

    # Envelope sends were matched when the peer's envelope receive completed;
    # reap them now so no request outlives the call.
    _drain_requests(env_send_reqs)

    for peer, buf in pay_recv_bufs.items():
        recvd[peer] = buf.view(dtype)

    return recvd, codes
