class DevitoError(Exception):
    """
    Base class for all Devito-related exceptions.
    """


class CompilationError(DevitoError):
    """
    Raised by the JIT compiler when the generated code cannot be compiled,
    typically due to a syntax error.

    These errors typically stem by one of the following:

    * A flaw in the user-provided equations;
    * An issue with the user-provided compiler options, not compatible
      with the given equations and/or backend;
    * A bug or a limitation in the Devito compiler itself.
    """


class InvalidArgument(ValueError, DevitoError):
    """
    Raised by the runtime system when an `op.apply(...)` argument, either a
    default argument or a user-provided one ("override"), is not valid.

    These are typically user-level errors, such as passing an incorrect
    type of argument, or passing an argument with an incorrect value.
    """


class InvalidOperator(DevitoError):
    """
    Raised by the runtime system when an `Operator` cannot be constructed.

    This generally occurs when an invalid combination of arguments is supplied to
    `Operator(...)` (e.g., a GPU-only optimization option is provided, while the
    Operator is being generated for the CPU).
    """


class ExecutionError(DevitoError):
    """
    Raised after `op.apply(...)` if a runtime error occurred during the execution
    of the Operator is detected.

    The nature of these errors can be various, for example:

    * Unstable numerical behavior (e.g., NaNs);
    * Out-of-bound accesses to arrays, which in turn can be caused by:
        * Incorrect user-provided equations (e.g., abuse of the "indexed notation");
        * A buggy optimization pass;
    * Running out of resources:
        * Memory (e.g., too many temporaries in the generated code);
        * Device shared memory or registers (e.g., too many threads per block);
    * etc.
    """


class MemoryPrecheckError(DevitoError):
    """
    Base class for failures detected by the optional pre-execution memory
    budget check enabled through ``op.apply(memory_limit=...)``.

    These errors are always raised *before* any data allocation, auto-tuning,
    or generated-kernel submission takes place, hence they are kept separate
    from `ExecutionError`, which instead concerns genuine kernel-time failures.
    """


class MemoryBudgetExceeded(MemoryPrecheckError):
    """
    Raised before execution when the estimated memory footprint of an
    Operator exceeds the caller-provided ``memory_limit`` budget.

    Attributes
    ----------
    op_name : str
        The name of the Operator whose execution was blocked.
    budget : dict
        The normalized budget in bytes, as ``{'host': int | None,
        'device': int | None, 'total': int | None}``; ``None`` means that no
        limit was supplied for that layer.
    estimate : dict
        The estimated footprint in bytes, as ``{'host': int, 'device': int,
        'total': int}``. With MPI this is the cross-rank, conservative
        (i.e., maximum) local footprint.
    available : dict
        The memory available on the system at pre-check time, in bytes, as
        ``{'host': int | None, 'device': int | None}``; ``None`` means that
        the information could not be obtained.
    layers : tuple of str
        The budget layer(s) whose limit was violated, in a stable order; a
        subset of ``('host', 'device', 'total')``.
    """

    def __init__(self, op_name, budget, estimate, available, layers):
        # Import locally to avoid an import cycle (devito.tools pulls in parts
        # of the runtime that themselves rely on devito.exceptions)
        from types import MappingProxyType

        from devito.tools.utils import humanbytes

        self.op_name = op_name
        self.budget = MappingProxyType(dict(budget))
        self.estimate = MappingProxyType(dict(estimate))
        self.available = MappingProxyType(dict(available))
        self.layers = tuple(layers)

        pretty = lambda d: {k: (humanbytes(v) if v is not None else 'unbounded')
                            for k, v in d.items()}
        est = pretty(estimate)

        lines = [
            f"Operator `{op_name}` aborted by the memory budget check: "
            f"{', '.join(self.layers)} budget exceeded."
        ]
        for layer in self.layers:
            lines.append(
                f"  {layer}: estimated {est[layer]} > budget "
                f"{humanbytes(budget[layer])}"
            )
        lines.append(f"Estimated footprint: {pretty(estimate)}")
        lines.append(f"Budget: {pretty(budget)}")
        lines.append(f"Currently available: {pretty(available)}")

        super().__init__("\n".join(lines))


class DeviceQueryError(MemoryPrecheckError):
    """
    Raised before execution when a budgeted run targets a device (e.g., a GPU)
    but the device cannot be queried for visibility or available memory -- for
    example because no driver/device is present on the orchestration node.

    This is deliberately distinct from `MemoryBudgetExceeded` (the footprint
    did fit, or could not even be compared against physical memory) and from
    `ExecutionError` (no kernel was ever submitted).

    Attributes
    ----------
    op_name : str
        The name of the Operator whose execution was blocked.
    deviceid : int or None
        The physical device ID that was being queried, if resolvable.
    reason : str
        A human-readable explanation of the query failure.
    """

    def __init__(self, op_name, reason, deviceid=None):
        self.op_name = op_name
        self.deviceid = deviceid
        self.reason = reason

        where = f"device `{deviceid}`" if deviceid is not None else "the device"
        super().__init__(
            f"Operator `{op_name}` aborted by the memory budget check: unable "
            f"to query available memory on {where}: {reason}"
        )
