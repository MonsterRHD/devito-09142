"""
Plan layer: the rank-to-rank routing induced by a Selection on a Layout.

`ExchangePlan` is a value object built once (no communication) from a
`Selection` and a `Layout`. It computes, for every routed element, its
owner rank and owner-local offset, and arranges the result/value array as
`(npoints, payload)` so packing and unpacking are single NumPy fancy-index
operations. The same plan drives `get` (pull) and `put` (push).

Every axis falls in one of four quadrants and is handled uniformly:

============== ================================== ============================
               structured (scalar / slice)        scattered (array / mask)
============== ================================== ============================
replicated     local payload block                local payload block
distributed    block redistribution (owner index) owner index via decomposition
============== ================================== ============================

The unit of exchange is one "point" (a coordinate tuple over the distributed
axes) carrying a payload block addressed by the replicated axes.
"""

import hashlib
import struct
from functools import cached_property

import numpy as np

from devito.data.distributed.selection import Affine, IndexScalar
from devito.data.distributed.transport import (
    CONSENSUS_MESSAGES,
    DUP_CODE,
    OOB_CODE,
    channel_for,
    join_consensus_codes,
    sparse_exchange,
)
from devito.tools import prod

__all__ = ['ExchangePlan', 'channel_key', 'sparse_push']


class ExchangePlan:

    """
    The rank-to-rank routing induced by a Selection on a Layout.

    A plan is built once, without communication, and then drives both `get`
    (pull `data[idx]`) and `put` (assign `data[idx] = value`). It maps
    every routed result element to its owner rank and owner-local offset, and
    splits the result axes into a "T" (transport) block over the distributed
    axes and a contiguous "payload" block over the replicated axes, so packing
    and unpacking are single NumPy fancy-index operations.

    Use `build` to construct one; the constructor takes the already
    computed routing tables.

    Parameters
    ----------
    layout : Layout
        Physical placement of the array being indexed.
    selection : Selection
        Normalized meaning of the index expression.
    perm : list of int
        Permutation taking the result axes to `(T-dims..., payload-dims...)`.
    t_shape : tuple of int
        Shape of the transport block (the distributed result axes).
    payload_shape : tuple of int
        Shape of the payload block (the replicated result axes).
    owners : numpy.ndarray
        Owner rank of each T row (`-1` when out of bounds).
    peers : dict
        Maps a peer rank to `(rows, dist_lin)`: the T rows it owns and their
        owner-local linear offsets over the distributed axes.
    block_offsets : numpy.ndarray
        Offset of each payload element within the owner's replicated block.
    repl_total : int
        Full replicated stride (product of the replicated axis sizes).
    oob_error : str or None
        Message for an out-of-bounds index (checked on get and set).
    dup_error : str or None
        Message for a duplicate assignment target (checked on set only).
    identity : bytes or None
        Stable, rank-independent identity of the array being indexed, used to
        keep the channels of distinct (but identically shaped) arrays apart.
        `None` falls back to a layout/selection-content identity.
    """

    def __init__(self, layout, selection, perm, t_shape, payload_shape, owners,
                 peers, block_offsets, repl_total, oob_error, dup_error,
                 identity=None):
        self.layout = layout
        self.selection = selection
        self._perm = perm
        self._t_shape = t_shape
        self._payload_shape = payload_shape
        self._owners = owners
        self._peers = peers
        self._block_offsets = block_offsets
        self._repl_total = repl_total
        self._oob_error = oob_error
        self._dup_error = dup_error
        self._identity = identity

    # ------------------------------------------------------------------ build

    @classmethod
    def build(cls, selection, layout, identity=None):
        """
        Plan the exchange for `data[idx]`; the result serves both get and set.

        Parameters
        ----------
        selection : Selection
            Normalized meaning of the index expression.
        layout : Layout
            Physical placement of the array being indexed.
        identity : int or None, optional
            Stable, rank-independent identity of the array being indexed (its
            distributed allocation number). Distinct arrays with identical
            shape and decomposition still get distinct communication channels.

        Returns
        -------
        ExchangePlan
            A ready-to-replay plan.
        """
        dist = set(layout.distributed_axes)
        repl = set(layout.replicated_axes)

        # An advanced group may not straddle a distributed and a replicated axis
        adv_dist = [a for a in selection.advanced_axes if a in dist]
        adv_repl = [a for a in selection.advanced_axes if a in repl]
        if adv_dist and adv_repl:
            raise NotImplementedError(
                "Advanced indexing coupling distributed and replicated axes is "
                "not supported"
            )
        advanced_distributed = bool(adv_dist)

        # Split the result axes into transport (T) and payload, in result order
        dims = selection.result_dims
        is_t = [_dim_is_distributed(d, dist, advanced_distributed) for d in dims]
        t_pos = [i for i, t in enumerate(is_t) if t]
        p_pos = [i for i, t in enumerate(is_t) if not t]
        perm = t_pos + p_pos

        t_shape = tuple(selection.result_shape[i] for i in t_pos)
        payload_shape = tuple(selection.result_shape[i] for i in p_pos)
        t_dims = [dims[i] for i in t_pos]
        p_dims = [dims[i] for i in p_pos]

        # Resolve, per T row, the owning rank and its owner-local position
        gcoords = _distributed_coords(selection, layout, t_dims, t_shape)
        owners, dist_local, sub = _resolve_owners(selection, layout, gcoords)

        block_offsets = _replicated_block(selection, layout, p_dims, payload_shape)
        repl_total = layout.replicated_size

        peers, oob_error, dup_error = _group_peers(layout, owners, dist_local,
                                                   sub, gcoords)
        return cls(layout, selection, perm, t_shape, payload_shape, owners,
                   peers, block_offsets, repl_total, oob_error, dup_error,
                   identity=identity)

    # --------------------------------------------------------------- helpers

    @property
    def comm(self):
        return self.layout.distributor.comm

    @property
    def nprocs(self):
        return self.layout.distributor.nprocs

    @property
    def payload_size(self):
        return prod(self._payload_shape)

    def _channel(self, kind):
        # The channel identifies the *array and the operation*, not the index
        # content: the advanced-index arrays are rank-local, so two ranks in
        # the same call legitimately drive different plans, while every header
        # is self-describing (payload size, offsets) and every reply is
        # gathered by the requester that asked for it. Get and put use
        # distinct channels, since each rank may interleave them differently.
        return channel_for(self.comm,
                           channel_key(kind, self._identity, self.layout))

    @cached_property
    def get_channel(self):
        """Channel driving the `get` (pull) calls of this plan."""
        return self._channel(b'get')

    @cached_property
    def put_channel(self):
        """Channel driving the `put` (push) calls of this plan."""
        return self._channel(b'put')

    def _error_code(self, check_dup):
        """This rank's consensus code (out-of-bounds wins over duplicate)."""
        if self._oob_error is not None:
            return OOB_CODE
        if check_dup and self._dup_error is not None:
            return DUP_CODE
        return 0

    def _raise_on_error(self, check_dup):
        """Raise the local error in the single-process (serial) fast path."""
        code = self._error_code(check_dup)
        if self.nprocs <= 1 and code:
            raise ValueError(CONSENSUS_MESSAGES[code])
        return code

    def _moved(self, local):
        """View of the rank-local array with distributed axes moved to front."""
        axes = self.layout.distributed_axes
        return np.moveaxis(local, axes, range(len(axes)))

    def _owner_apply(self, moved, dist_lin, block_offsets):
        """Owner-local (row, column) multi-index for a received message."""
        elem = dist_lin[:, None] * self._repl_total + block_offsets[None, :]
        return np.unravel_index(elem.reshape(-1), moved.shape)

    # ------------------------------------------------------------------- get

    def get(self, local):
        """
        Return `data[idx]` as a NumPy array by pulling from the owner ranks.

        Parameters
        ----------
        local : numpy.ndarray
            The caller's rank-local array.

        Returns
        -------
        numpy.ndarray
            The indexed result, in `selection.result_shape`.
        """
        code = self._raise_on_error(check_dup=False)
        comm, ps = self.comm, self.payload_size
        dtype = local.dtype

        # Send each owner the offsets of the elements we want from it...
        headers = {r: _encode(ps, self._block_offsets, dist_lin)
                   for r, (_, dist_lin) in self._peers.items()}

        # ...the channel binds isolated, fresh tags to this call, so this get
        # cannot exchange messages with any concurrent, nested or previous call
        with self.get_channel(comm) as call:
            requests, codes = sparse_exchange(comm, headers, np.int64, call,
                                              step=0, code=code)

            # All ranks reach the same verdict from the envelopes. On error,
            # run the (empty) value phase to completion first, so no request
            # is left in flight on any rank before the consistent raise.
            if codes is not None and np.any(codes):
                sparse_exchange(comm, {}, dtype, call, step=1)
                raise ValueError(join_consensus_codes(codes))

            # ...and reply to whoever asked us with the requested values
            moved = self._moved(local)
            replies = {}
            for src, buf in requests.items():
                block_offsets, dist_lin = _decode(buf)
                midx = self._owner_apply(moved, dist_lin, block_offsets)
                replies[src] = np.ascontiguousarray(moved[midx]).reshape(-1)
            payloads, _ = sparse_exchange(comm, replies, dtype, call, step=1)

        # Scatter the received values back into result-row order
        rows_flat = np.zeros((self._nrows(), ps), dtype=dtype)
        for r, (rows, _) in self._peers.items():
            if rows.size:
                rows_flat[rows] = payloads[r].reshape(rows.size, ps)
        return self._rows_to_result(rows_flat)

    # ------------------------------------------------------------------- put

    def put(self, local, value):
        """
        Assign `data[idx] = value` by pushing to the owner ranks.

        Parameters
        ----------
        local : numpy.ndarray
            The caller's rank-local array (written in place).
        value : array_like
            The value to assign, broadcast to `selection.result_shape`.
        """
        code = self._raise_on_error(check_dup=True)
        # Build the rows only when there is no local error: a malformed value
        # must not preempt the all-ranks consensus ValueError, and on error no
        # payload is ever sent (the push phases run empty before the raise).
        rows_flat = None if code else self._value_to_rows(value, local.dtype)
        sparse_push(self.comm, self.put_channel,
                    self.layout.distributed_axes, self._repl_total,
                    self._peers, self._block_offsets, self.payload_size,
                    rows_flat, local, code=code, dtype=local.dtype)

    # ------------------------------------------------------- result <-> rows

    def _nrows(self):
        return prod(self._t_shape)

    def _rows_to_result(self, rows_flat):
        moved_shape = self._t_shape + self._payload_shape
        moved = rows_flat.reshape(moved_shape)
        result = np.moveaxis(moved, range(len(self._perm)), self._perm)
        return np.ascontiguousarray(result).reshape(self.selection.result_shape)

    def _value_to_rows(self, value, dtype):
        value = np.broadcast_to(np.asarray(value, dtype=dtype),
                                self.selection.result_shape)
        moved = np.transpose(value, self._perm)
        return np.ascontiguousarray(moved).reshape(self._nrows(), self.payload_size)


# --------------------------------------------------------------------- free fns


def _dim_is_distributed(dim, dist, advanced_distributed):
    """True if a result dimension lands on a distributed (transport) axis."""
    kind, val = dim
    if kind == 'basic':
        return val in dist
    return advanced_distributed


def _distributed_coords(selection, layout, t_dims, t_shape):
    """Global coordinate per distributed axis, one value per T row."""
    nrows = prod(t_shape)
    grids = (np.indices(t_shape).reshape(len(t_dims), -1)
             if t_dims else np.zeros((0, nrows), dtype=np.int64))

    # Index of advanced T dims, flattened into a single point index q
    adv_rows = [ri for ri, d in enumerate(t_dims) if d[0] == 'adv']
    q = None
    if adv_rows:
        q = np.ravel_multi_index([grids[ri] for ri in adv_rows],
                                 selection.advanced_shape)

    gcoords = {}
    for axis in layout.distributed_axes:
        s = selection.selectors[axis]
        if isinstance(s, IndexScalar):
            gcoords[axis] = np.full(nrows, s.index, dtype=np.int64)
        elif isinstance(s, Affine):
            ri = t_dims.index(('basic', axis))
            gcoords[axis] = s.coords[grids[ri]]
        else:  # Explicit
            gcoords[axis] = s.coords[q]
    return gcoords


def _resolve_owners(selection, layout, gcoords):
    """
    Resolve the owner of each transport row from its global coordinates.

    Parameters
    ----------
    selection : Selection or None
        Unused; kept for a uniform call signature with the other planners.
    layout : Layout
        Physical placement of the array.
    gcoords : dict
        Maps each distributed axis to its global coordinate per T row.

    Returns
    -------
    owners : numpy.ndarray
        Flat owner rank per T row (`-1` if out of bounds).
    local : numpy.ndarray
        Per-axis owner-local offset per T row, shaped `(naxes, nrows)`.
    sub : numpy.ndarray
        Per-axis owner sub-rank per T row, shaped `(naxes, nrows)`.
    """
    axes = layout.distributed_axes
    nrows = len(next(iter(gcoords.values()))) if gcoords else 0

    sub = np.zeros((len(axes), nrows), dtype=np.int64)
    local = np.zeros((len(axes), nrows), dtype=np.int64)
    valid = np.ones(nrows, dtype=bool)
    for k, axis in enumerate(axes):
        owner_lut, local_lut, _ = layout.axis_maps(axis)
        g = gcoords[axis]
        in_range = (g >= 0) & (g < owner_lut.size)
        safe = np.where(in_range, g, 0)
        sub[k] = np.where(in_range, owner_lut[safe], -1)
        local[k] = np.where(in_range, local_lut[safe], -1)
        valid &= in_range & (sub[k] >= 0)

    # Map sub-rank tuples to flat ranks through the topology
    rank_arr = np.full(layout.topology_shape, -1, dtype=np.int64)
    for coord, r in layout.coord_to_rank.items():
        rank_arr[coord] = r
    owners = np.full(nrows, -1, dtype=np.int64)
    if nrows:
        safe_sub = np.where(valid, sub, 0)
        owners = np.where(valid, rank_arr[tuple(safe_sub)], -1)
    return owners, local, sub


def _replicated_block(selection, layout, p_dims, payload_shape):
    """Offsets of the selected replicated block within the owner's repl block."""
    payload_size = prod(payload_shape)
    offsets = np.zeros(payload_size, dtype=np.int64)
    if not layout.replicated_axes:
        return offsets

    pgrids = (np.indices(payload_shape).reshape(len(p_dims), -1)
              if p_dims else np.zeros((0, payload_size), dtype=np.int64))
    adv_rows = [ri for ri, d in enumerate(p_dims) if d[0] == 'adv']
    q = None
    if adv_rows:
        q = np.ravel_multi_index([pgrids[ri] for ri in adv_rows],
                                 selection.advanced_shape)

    # Strides over replicated axes (increasing order) of the owner-local block
    sizes = [layout.global_shape[a] for a in layout.replicated_axes]
    strides = {a: int(prod(sizes[i + 1:]))
               for i, a in enumerate(layout.replicated_axes)}

    for axis in layout.replicated_axes:
        s = selection.selectors[axis]
        if isinstance(s, IndexScalar):
            coord = np.full(payload_size, s.index, dtype=np.int64)
        elif isinstance(s, Affine):
            ri = p_dims.index(('basic', axis))
            coord = s.coords[pgrids[ri]]
        else:  # Explicit (replicated advanced)
            coord = s.coords[q]
        offsets += coord * strides[axis]
    return offsets


def _group_peers(layout, owners, dist_local, sub, gcoords):
    """
    Group transport rows by owner and flag out-of-bounds/duplicate targets.

    Returns
    -------
    peers : dict
        Maps a peer rank to `(rows, dist_lin)`: the T rows it owns and their
        owner-local linear offsets over the distributed axes.
    oob_error : str or None
        Set when any row addresses an out-of-bounds global index.
    dup_error : str or None
        Set when two rows address the same distributed coordinate.
    """
    axes = layout.distributed_axes
    oob_error = dup_error = None

    if owners.size:
        # Within-rank duplicate detection over distributed coordinates
        stacked = np.stack([gcoords[a] for a in axes], axis=1) if axes \
            else np.zeros((owners.size, 0), dtype=np.int64)
        if np.unique(stacked, axis=0).shape[0] != stacked.shape[0]:
            dup_error = "Duplicate global indices in distributed assignment"

    if np.any(owners < 0):
        oob_error = "Advanced index contains out-of-bounds global indices"

    peers = {}
    for r in np.unique(owners[owners >= 0]) if owners.size else []:
        rows = np.where(owners == r)[0]
        subranks = sub[:, rows[0]]
        local_shape = tuple(int(layout.axis_maps(a)[2][subranks[k]])
                            for k, a in enumerate(axes))
        if local_shape:
            dist_lin = np.ravel_multi_index([dist_local[k, rows]
                                             for k in range(len(axes))],
                                            local_shape)
        else:
            dist_lin = np.zeros(rows.size, dtype=np.int64)
        peers[int(r)] = (rows, np.asarray(dist_lin, dtype=np.int64))
    return peers, oob_error, dup_error


def sparse_push(comm, channel, distributed_axes, repl_total, peers,
                block_offsets, payload_size, rows_flat, local, code=0,
                dtype=None):
    """
    Route `rows_flat` to the owner ranks and scatter each received payload
    into `local` at its owner-local position.

    This is the single push primitive behind both `ExchangePlan.put`
    (advanced/replicated assignment, `payload_size` >= 1) and the structured
    redistribution layer (one value per point, `payload_size` == 1).

    Parameters
    ----------
    comm : MPI communicator
        The communicator to push over.
    channel : Channel
        The isolated communication channel driving this call. It binds fresh
        tags to the call and serializes calls on the same routing, so pushes
        never consume another call's messages.
    distributed_axes : tuple of int
        The array axes that are MPI-distributed.
    repl_total : int
        Full replicated stride (1 when there is no replicated payload).
    peers : dict
        Maps a peer rank to `(rows, dist_lin)` (see `_group_peers`).
    block_offsets : numpy.ndarray
        Offset of each payload element within an owner's replicated block.
    payload_size : int
        Number of payload elements per point.
    rows_flat : numpy.ndarray or None
        Values to push, shaped `(nrows, payload_size)` in owner-grouped
        order. `None` when a consensus error was detected before the value
        array was built; the phases then run empty before the raise.
    local : numpy.ndarray
        The owner's rank-local array (written in place).
    code : int, optional
        This rank's consensus code for the call (`0` = no error).
    dtype : numpy.dtype or None, optional
        Payload dtype; defaults to `rows_flat.dtype` and is only needed when
        `rows_flat` is `None` (so the empty error phases still type-match).
    """
    dtype = rows_flat.dtype if rows_flat is not None else np.dtype(dtype)

    # Tell each owner which of its local slots we are about to write...
    headers = {r: _encode(payload_size, block_offsets, dist_lin)
               for r, (_, dist_lin) in peers.items()}
    payloads = {}
    if rows_flat is not None:
        payloads = {r: rows_flat[rows].reshape(-1)
                    for r, (rows, _) in peers.items() if rows.size}

    with channel(comm) as call:
        requests, codes = sparse_exchange(comm, headers, np.int64, call,
                                          step=0, code=code)
        # Consistent error across all ranks: drain the (empty) value phase so
        # that no payload send can be left outstanding, then raise together.
        if codes is not None and np.any(codes):
            sparse_exchange(comm, {}, dtype, call, step=1)
            raise ValueError(join_consensus_codes(codes))
        values, _ = sparse_exchange(comm, payloads, dtype, call, step=1)

        # ...then scatter whatever we received into our own local array
        moved = np.moveaxis(local, distributed_axes,
                            range(len(distributed_axes)))
        for src, buf in requests.items():
            offsets, dist_lin = _decode(buf)
            elem = dist_lin[:, None] * repl_total + offsets[None, :]
            midx = np.unravel_index(elem.reshape(-1), moved.shape)
            moved[midx] = values[src]


def channel_key(kind, identity, layout, selection=None, extra=b''):
    """
    Content-address the communication channel of a routing.

    The key is built only from values identical on every rank (the global
    shape, the global per-subrank decomposition bounds, the index selectors,
    the stable array identity, and optional caller-supplied bytes), never from
    process-local object ids, addresses or rank-local coordinate lists.

    Parameters
    ----------
    kind : bytes
        Routing family, `b'get'`/`b'put'` for a plan or `b'redist'`/
        `b'redist-gate'` for a structured redistribution.
    identity : int, tuple of int or None
        Stable, rank-independent array identity (a distributed allocation
        number, or a (target, source) pair for redistribution).
    layout : Layout
        Physical placement of the routed array.
    selection : Selection or None
        The normalized, global index for the routing. Rank-local advanced
        array contents must never be folded in.
    extra : bytes, optional
        Additional globally-replicated content to fold in (e.g. the source
        array global shape for a redistribution).

    Returns
    -------
    bytes
        An 8-byte digest usable as a `channel_for` key.
    """
    h = hashlib.blake2b(digest_size=8)
    h.update(kind)
    identities = identity if isinstance(identity, tuple) else (identity,)
    for i in identities:
        h.update(struct.pack('q', -1 if i is None else int(i)))
    _hash_layout(h, layout)
    if selection is not None:
        for s in selection.selectors:
            if isinstance(s, IndexScalar):
                h.update(b's')
                h.update(struct.pack('q', s.index))
            elif isinstance(s, Affine):
                h.update(b'a')
                h.update(struct.pack('qqq', s.start, s.stop, s.step))
            else:  # Explicit
                h.update(b'e')
                h.update(np.ascontiguousarray(s.coords, dtype=np.int64).tobytes())
    h.update(struct.pack('q', len(extra)))
    h.update(bytes(extra))
    return h.digest()


def _hash_layout(hasher, layout):
    """Fold the globally-replicated layout content into `hasher`."""
    hasher.update(struct.pack('q', len(layout.global_shape)))
    for n in layout.global_shape:
        hasher.update(struct.pack('q', int(n)))
    for axis, dec in enumerate(layout.decomposition):
        hasher.update(struct.pack('q', axis))
        if dec is None:
            hasher.update(b'r')
            continue
        hasher.update(b'd')
        # `Decomposition` is a tuple of globally-replicated sub-ranges; the
        # (first, last, size) of each sub-range identifies the placement.
        for sub in dec:
            arr = np.ascontiguousarray(sub, dtype=np.int64)
            hasher.update(struct.pack('q', arr.size))
            if arr.size:
                hasher.update(struct.pack('qq', int(arr[0]), int(arr[-1])))



def _encode(payload_size, block_offsets, dist_lin):
    """Pack a request header as `[payload_size, *block_offsets, *dist_lin]`."""
    return np.concatenate(([payload_size], block_offsets, dist_lin)).astype(np.int64)


def _decode(buf):
    """Unpack a request header into `(block_offsets, dist_lin)`."""
    payload_size = int(buf[0])
    block_offsets = buf[1:1 + payload_size]
    dist_lin = buf[1 + payload_size:]
    return block_offsets, dist_lin
