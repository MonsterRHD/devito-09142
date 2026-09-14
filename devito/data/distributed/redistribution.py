"""
Structured redistribution between distributed arrays (the "structured" quadrant).

`redistribute_set` assigns `self[idx] = other` (`other` distributed) by
pushing `other`'s block into a strided region of `self`, point-to-point.

The source-to-destination mapping is derived directly from the index as a
per-axis affine map (`source_coord = start + k*step`), so it never relies on
the legacy `_process_args` machinery. Both reuse the engine's `Layout` and
owner-resolution/transport.

The structured path is chosen only if *every* rank can build it; the verdict
is exchanged over an isolated point-to-point gate channel (one tag-paired
envelope per pair of ranks), never over a tagless collective that another
concurrent exchange could mismatch. This keeps the communication pattern
identical on all ranks -- essential, since a value/result with
non-uniformly-structured decomposition metadata would otherwise make the
per-rank choice diverge and deadlock. Unsupported patterns fall back to the
legacy path -- no behavior is lost.
"""

import hashlib
import struct

import numpy as np

from devito.data.distributed.layout import Layout
from devito.data.distributed.plan import (
    _group_peers,
    _hash_layout,
    _resolve_owners,
    channel_key,
    sparse_push,
)
from devito.data.distributed.selection import Affine, Selection
from devito.data.distributed.transport import channel_for, sparse_exchange

__all__ = ['redistribute_set']


def redistribute_set(data, glb_idx, other):
    """
    Assign `data[glb_idx] = other` via a structured point-to-point exchange.

    The structured path is taken only if *every* rank can build it; the verdict
    is reached by fanning one vote per rank out over the (isolated) gate
    channel envelopes -- a point-to-point all-gather, never a tagless
    collective that another concurrent exchange could mismatch. This keeps the
    choice -- and therefore the communication pattern -- identical on all
    ranks, which is essential: a value produced by the legacy path (e.g. a
    reversed slice) may carry decomposition metadata that is not uniformly
    structured, and a diverging choice would deadlock.

    Parameters
    ----------
    data : Data
        The MPI-distributed array being assigned into.
    glb_idx : index expression
        The global index of the assigned region.
    other : Data
        The MPI-distributed value to assign.

    Returns
    -------
    bool
        `True` when handled here; `False` when the pattern is unsupported and
        the caller should fall back to the legacy path.
    """
    try:
        spec = _structured_spec(data, glb_idx, other)
    except (IndexError, ValueError, TypeError):
        spec = None

    identity = (getattr(data, '_dist_uid', None),
                getattr(other, '_dist_uid', None))
    comm = data._distributor.comm
    gate = _gate_channel(data, glb_idx, identity)

    # The envelope round fans every rank's vote out to every rank; no payload
    # is involved. Isolated tags keep this vote independent of any get/put
    # running concurrently on the same communicator.
    with gate(comm) as call:
        _, votes = sparse_exchange(comm, {}, np.int64, call, step=0,
                                   code=int(spec is not None))
    if votes is not None and not np.all(votes):
        return False

    _push(spec, np.asarray(data), identity)
    return True


def _gate_channel(data, glb_idx, identity):
    """
    Deterministic channel for the structured/fallback vote.

    Only rank-independent, structural content is folded in (array *values*
    are rank-local and deliberately excluded), so every rank in the same
    assignment statement derives the same gate even when it ends up voting
    for the legacy fallback.
    """
    global_shape = tuple(
        dec.size if dec is not None else size
        for dec, size in zip(data._decomposition, data.shape, strict=True)
    )
    layout = Layout(data._distributor, data._decomposition, global_shape)

    h = hashlib.blake2b(digest_size=8)
    h.update(b'redist-gate')
    for i in identity:
        h.update(struct.pack('q', -1 if i is None else int(i)))
    _hash_layout(h, layout)
    components = glb_idx if isinstance(glb_idx, tuple) else (glb_idx,)
    for component in components:
        if isinstance(component, slice):
            h.update(b's')
            h.update(struct.pack('qqq',
                                 component.start if component.start is not None else -1,
                                 component.stop if component.stop is not None else -1,
                                 component.step if component.step is not None else -1))
        elif isinstance(component, np.ndarray):
            h.update(b'a')
            h.update(repr(component.shape).encode())
            h.update(component.dtype.str.encode())
        elif isinstance(component, (list, tuple)):
            h.update(b'l')
            arr = np.asarray(component)
            h.update(repr(arr.shape).encode())
        else:
            h.update(b'x')
            try:
                h.update(struct.pack('q', int(component)))
            except (TypeError, ValueError):
                h.update(repr(component).encode())
    return channel_for(data._distributor.comm, h.digest())


def _structured_spec(data, glb_idx, other):
    """
    Build the routing spec for the supported structured case.

    The case is: `data` and `other` both fully distributed with matching
    rank, every axis sliced (no scalars/arrays), and each sliced region matching
    `other`'s extent.

    Returns
    -------
    tuple or None
        `(layout, gcoords, values, selection, source_shape)` for `_push`, or
        `None` when the pattern is unsupported and the caller should fall back
        to the legacy path.
    """
    decomposition = data._decomposition
    if any(d is None for d in decomposition):
        return None
    if not (isinstance(other, type(data)) and other._is_distributed):
        return None
    if other.ndim != data.ndim:
        return None
    other_dec = other._decomposition
    if any(d is None for d in other_dec):
        return None

    global_shape = tuple(d.size for d in decomposition)
    selection = Selection.from_index(glb_idx, global_shape)
    if any(not isinstance(s, Affine) for s in selection.selectors):
        return None

    coords_per_axis = []
    for axis, affine in enumerate(selection.selectors):
        # `other` fills the sliced region in the order of its own global indices;
        # map each to the corresponding `self` coordinate: start + c*step. The
        # per-axis owned indices come from this rank's subdomain (a replicated
        # axis owns the full extent), 0-based within `other`'s global space.
        dec = other_dec[axis]
        if affine.size != dec.size:
            return None
        owned = np.asarray(dec.loc_abs_numb, dtype=np.int64) - (dec.glb_min or 0)
        coords_per_axis.append(affine.start + owned*affine.step)

    mesh = np.meshgrid(*coords_per_axis, indexing='ij')
    gcoords = {axis: m.reshape(-1) for axis, m in enumerate(mesh)}
    values = np.ascontiguousarray(np.asarray(other)).reshape(-1)

    layout = Layout(data._distributor, decomposition, global_shape)
    source_shape = tuple(d.size for d in other_dec)
    return layout, gcoords, values, selection, source_shape


def _push(spec, local, identity):
    """
    Push `values` (one per global coordinate in `gcoords`) to their owners.

    A structured assignment has exactly one value per distributed point and no
    replicated payload, so it is `sparse_push` with `payload_size == 1`
    (`block_offsets == [0]`, `repl_total == 1`).
    """
    layout, gcoords, values, selection, source_shape = spec
    owners, dist_local, sub = _resolve_owners(None, layout, gcoords)
    peers, _, _ = _group_peers(layout, owners, dist_local, sub, gcoords)

    block_offsets = np.zeros(1, dtype=np.int64)   # no replicated payload
    extra = struct.pack(f'{len(source_shape)}q', *source_shape)
    key = channel_key(b'redist', identity, layout, selection=selection,
                      extra=extra)
    channel = channel_for(layout.distributor.comm, key)
    sparse_push(layout.distributor.comm, channel, layout.distributed_axes, 1,
                peers, block_offsets, 1, values.reshape(-1, 1), local)
