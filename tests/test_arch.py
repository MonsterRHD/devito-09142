import os

import pytest

from devito import configuration, switchconfig
from devito.arch.archinfo import ANYCPU
from devito.arch.compiler import (
    CudaCompiler, GNUCompiler, HipCompiler, compiler_registry, sniff_compiler_version,
    sniff_mpi_distro, sniff_mpi_flags,
)
from devito.exceptions import CompilationError


@pytest.mark.parametrize("cc", [
    "doesn'texist",
    "/root/doesn'texist",
])
def test_sniff_compiler_version(cc):
    with pytest.raises(RuntimeError, match=cc):
        sniff_compiler_version(cc)


@pytest.mark.parametrize("cc", ['gcc-4.9', 'gcc-11', 'gcc', 'gcc-14', 'gcc-123'])
def test_gcc(cc):
    assert cc in compiler_registry


def test_switcharch():
    old_compiler = configuration['compiler']
    with switchconfig(compiler='gcc-4.9'):
        tmp_comp = configuration['compiler']
        assert isinstance(tmp_comp, GNUCompiler)
        assert tmp_comp.suffix == '4.9'

    tmp_comp = configuration['compiler']
    assert isinstance(tmp_comp, old_compiler.__class__)
    assert old_compiler.suffix == tmp_comp.suffix
    assert old_compiler.name == tmp_comp.name


# *** MPI compiler wrapper probing ***


HYDRA_LAUNCHER = """\
if [ "$1" = "--version" ]; then
  echo "HYDRA build details:"
  echo "    Version:                                 4.2.3"
fi
"""

OPENMPI_LAUNCHER = """\
if [ "$1" = "--version" ]; then
  echo "Open MPI launcher (open-mpi) 5.0.0"
fi
"""

UNKNOWN_LAUNCHER = """\
if [ "$1" = "--version" ]; then
  echo "some unheard-of mpi launcher 9000"
fi
"""

# Modern MPICH wrapper: segregated -show-compile-info/-show-link-info output.
# Note the quoted paths (with spaces), duplicate entries and empty fields.
MODERN_MPICC = """\
case "$1" in
  -show)
    printf '%s\\n' "gcc '-I/opt/my mpi/include' -m64 -pthread " \\
"'-L/opt/my mpi/lib' -Wl,-rpath,/x -lmpi -lmpi" ;;
  -show-compile-info)
    printf '%s\\n' "'-I/opt/my mpi/include' -m64  " ;;
  -show-link-info)
    printf '%s\\n' "-m64 -pthread '-L/opt/my mpi/lib' " \\
"-Wl,-rpath,/x -lmpi -lmpi ''" ;;
  --version)
    echo "mpicc for MPICH version 4.2.3 (gcc)" ;;
esac
"""

# Legacy MPICH wrapper: only -show is recognised; the segregated options are
# forwarded to the compiler which rejects them, like the real wrappers do.
LEGACY_MPICC = """\
case "$1" in
  -show)
    printf '%s\\n' "gcc -I/opt/mpich/include -m64 -pthread " \\
"-L/opt/mpich/lib -Xlinker -rpath -Xlinker /opt/mpich/lib " \\
"-Xlinker --enable-new-dtags -lmpi -lmpi" ;;
  -show-compile-info|-show-link-info)
    echo "gcc: error: unrecognized command-line option '$1'" >&2
    exit 1 ;;
esac
"""

OPENMPI_MPICC = """\
case "$1" in
  --showme:compile) echo "-I/opt/openmpi/include -pthread" ;;
  --showme:link) echo "-L/opt/openmpi/lib -lmpi" ;;
esac
"""

CUDA_MPICXX = """\
case "$1" in
  -show)
    printf '%s\\n' "g++ -I/cuda-mpi/include -pthread " \\
"-L/cuda-mpi/lib -Wl,-rpath,/cuda-mpi/lib -lmpi" ;;
  -show-compile-info)
    printf '%s\\n' "-I/cuda-mpi/include -pthread" ;;
  -show-link-info)
    printf '%s\\n' "-L/cuda-mpi/lib -Wl,-rpath,/cuda-mpi/lib -lmpi" ;;
esac
"""

FAKE_NVCC = """\
if [ "$1" = "--version" ]; then
  echo "Cuda compilation tools, release 12.0, V12.0.140"
fi
"""

FAKE_HIPCC = """\
if [ "$1" = "--version" ]; then
  echo "HIP clang version 17.0.0"
fi
"""


@pytest.fixture
def fake_mpi_bin(tmp_path, monkeypatch):
    """
    Provide a throw-away bin directory with fake MPI commands, prepended to
    PATH, and ensure the process-wide probe caches start/end empty so that
    failed probes can't leak across tests.
    """
    from devito.arch import compiler as _compiler

    _compiler._mpi_distro_cache.clear()
    _compiler._mpi_flags_cache.clear()

    bindir = tmp_path / 'bin'
    bindir.mkdir()

    def write(name, body, executable=True):
        f = bindir / name
        f.write_text("#!/bin/sh\n" + body)
        f.chmod(0o755 if executable else 0o644)
        return f

    monkeypatch.setenv('PATH', f"{bindir}{os.pathsep}{os.environ['PATH']}")

    yield write, bindir

    _compiler._mpi_distro_cache.clear()
    _compiler._mpi_flags_cache.clear()


def test_sniff_mpich_distro(fake_mpi_bin):
    write, _ = fake_mpi_bin
    write('mpiexec', HYDRA_LAUNCHER)

    assert sniff_mpi_distro('mpiexec') == 'MPICH'


def test_sniff_mpich_flags_modern(fake_mpi_bin):
    """Quoted paths, duplicates and empty fields are handled correctly."""
    write, _ = fake_mpi_bin
    write('mpiexec', HYDRA_LAUNCHER)
    write('mpicc', MODERN_MPICC)

    compile_flags, link_flags = sniff_mpi_flags('mpicc')

    assert compile_flags == ['-I/opt/my mpi/include', '-m64']
    assert link_flags == [
        '-m64', '-pthread', '-L/opt/my mpi/lib', '-Wl,-rpath,/x', '-lmpi']
    assert all(f for f in compile_flags + link_flags)


def test_sniff_mpich_flags_uses_wrapper_argument(fake_mpi_bin):
    """The `mpicc` argument selects the wrapper (e.g. mpicxx for nvcc)."""
    write, _ = fake_mpi_bin
    write('mpiexec', HYDRA_LAUNCHER)
    # A stale mpicc that must not be consulted
    write('mpicc', "exit 1\n")
    write('mpicxx', MODERN_MPICC)

    compile_flags, link_flags = sniff_mpi_flags('mpicxx')

    assert compile_flags == ['-I/opt/my mpi/include', '-m64']
    assert '-lmpi' in link_flags


def test_sniff_mpich_flags_legacy_show_fallback(fake_mpi_bin):
    """Old MPICH wrappers (only -show) are partitioned into compile/link."""
    write, _ = fake_mpi_bin
    write('mpiexec', HYDRA_LAUNCHER)
    write('mpicc', LEGACY_MPICC)

    compile_flags, link_flags = sniff_mpi_flags()

    assert compile_flags == ['-I/opt/mpich/include', '-m64', '-pthread']
    # Repeated -Xlinker entries carry different values and must survive
    # duplicate removal as atomic (option, value) arguments
    assert link_flags == [
        '-m64', '-pthread', '-L/opt/mpich/lib',
        '-Xlinker', '-rpath', '-Xlinker', '/opt/mpich/lib',
        '-Xlinker', '--enable-new-dtags', '-lmpi']


def test_sniff_mpi_flags_stable_within_job(fake_mpi_bin):
    write, _ = fake_mpi_bin
    write('mpiexec', HYDRA_LAUNCHER)
    write('mpicc', MODERN_MPICC)

    first = sniff_mpi_flags()
    second = sniff_mpi_flags()

    assert first == second
    # Fresh mutable lists are returned: mutating one result must not affect
    # later probes (nor the cached result)
    first[0].append('polluted')
    first[1].append('polluted')
    third = sniff_mpi_flags()
    assert third == second
    assert 'polluted' not in third[0] + third[1]


def test_sniff_mpi_distro_failure_is_not_cached(fake_mpi_bin):
    """A first unknown/failed probe must not poison a later successful one."""
    write, _ = fake_mpi_bin
    write('mpiexec', UNKNOWN_LAUNCHER)
    write('mpicc', MODERN_MPICC)

    assert sniff_mpi_distro('mpiexec') == 'unknown'
    with pytest.raises(CompilationError, match="unrecognised"):
        sniff_mpi_flags()

    # Simulate the MPI module being loaded later on in the same job
    write('mpiexec', HYDRA_LAUNCHER)

    assert sniff_mpi_distro('mpiexec') == 'MPICH'
    compile_flags, link_flags = sniff_mpi_flags()
    assert '-lmpi' in link_flags and compile_flags


def test_sniff_mpi_flags_nonexecutable_wrapper(fake_mpi_bin):
    write, _ = fake_mpi_bin
    write('mpiexec', HYDRA_LAUNCHER)
    mpicc = write('mpicc', MODERN_MPICC, executable=False)

    # Use the absolute path on purpose: otherwise a non-executable file in
    # PATH would be skipped in favour of a later, executable one
    with pytest.raises(CompilationError, match="not executable"):
        sniff_mpi_flags(str(mpicc))

    # Fixing permissions later on must allow the probe to succeed
    mpicc.chmod(0o755)
    _, link_flags = sniff_mpi_flags(str(mpicc))
    assert '-lmpi' in link_flags


def test_sniff_mpi_flags_unparseable_output(fake_mpi_bin):
    write, _ = fake_mpi_bin
    write('mpiexec', HYDRA_LAUNCHER)
    # Unmatched single quote in the -show output
    write('mpicc', """\
case "$1" in
  -show) printf '%s\\n' "gcc '-I/broken" ;;
  -show-compile-info|-show-link-info) exit 1 ;;
esac
""")

    with pytest.raises(CompilationError, match="parse"):
        sniff_mpi_flags()


def test_sniff_openmpi_path_unchanged(fake_mpi_bin):
    """The OpenMPI/Spectrum MPI --showme path keeps its original behavior."""
    write, _ = fake_mpi_bin
    write('mpiexec', OPENMPI_LAUNCHER)
    write('mpicc', OPENMPI_MPICC)

    assert sniff_mpi_distro('mpiexec') == 'OpenMPI'
    assert sniff_mpi_flags('mpicxx') == (
        ['-I/opt/openmpi/include', '-pthread'],
        ['-L/opt/openmpi/lib', '-lmpi'])


def test_mpich_flags_reach_jit_cache_signature(fake_mpi_bin):
    """MPICH flags feed the toolchain and hence codepy's abi_id signature."""
    write, _ = fake_mpi_bin
    write('mpiexec', HYDRA_LAUNCHER)
    write('mpicc', MODERN_MPICC)
    write('hipcc', FAKE_HIPCC)

    with switchconfig(mpi=True):
        hip = HipCompiler(platform=ANYCPU)

        assert '-I/opt/my mpi/include' in hip.cflags
        assert '-L/opt/my mpi/lib' in hip.ldflags
        assert '-lmpi' in hip.ldflags

        # codepy signs the full command line (cflags + ldflags)
        cmdline = hip.abi_id()[2]
        assert '-I/opt/my mpi/include' in cmdline
        assert '-L/opt/my mpi/lib' in cmdline
        assert '-lmpi' in cmdline

        # Same job, same probe -> identical signature
        assert HipCompiler(platform=ANYCPU).abi_id() == hip.abi_id()

        # A different MPICH installation yields a different signature
        write('mpicc', MODERN_MPICC.replace('/opt/my mpi', '/opt/other mpi')
              .replace('/x', '/y'))
        from devito.arch import compiler as _compiler
        _compiler._mpi_flags_cache.clear()
        assert HipCompiler(platform=ANYCPU).abi_id() != hip.abi_id()

    # Serial toolchains do not carry any probed MPI flag in their signature
    gnu = GNUCompiler(platform=ANYCPU)
    cmdline = gnu.abi_id()[2]
    assert not any('mpi' in f for f in cmdline)


def test_cuda_mpich_flags_rewritten_and_signed(fake_mpi_bin):
    """nvcc path: -pthread/-Wl are rewritten for the host compiler."""
    write, _ = fake_mpi_bin
    write('mpiexec', HYDRA_LAUNCHER)
    write('mpicxx', CUDA_MPICXX)
    write('nvcc', FAKE_NVCC)

    with switchconfig(mpi=True):
        nvcc = CudaCompiler(platform=ANYCPU)

        assert '-I/cuda-mpi/include' in nvcc.cflags
        # -pthread is dropped from compile flags by the nvcc workaround
        assert '-pthread' not in nvcc.cflags
        # -Wl flags are rewritten into -Xcompiler arguments
        assert any(f.startswith('"-Wl') for f in nvcc.ldflags)
        assert '-lmpi' in nvcc.ldflags

        cmdline = nvcc.abi_id()[2]
        assert '-I/cuda-mpi/include' in cmdline
        assert '-lmpi' in cmdline


def test_explicit_compiler_options_unchanged(fake_mpi_bin, monkeypatch):
    """Caller-provided CFLAGS/LDFLAGS keep working on top of a serial build."""
    write, _ = fake_mpi_bin
    custom_cc = write('mycc', "echo 'mycc 13.0'\n")

    monkeypatch.setenv('CC', str(custom_cc))
    monkeypatch.setenv('CFLAGS', '-DMY_CFLAG=1')
    monkeypatch.setenv('LDFLAGS', '-L/my/extra/lib')

    with switchconfig(compiler='custom'):
        cc = configuration['compiler'].__new_with__(platform=ANYCPU)
        assert str(custom_cc) == cc.CC
        assert '-DMY_CFLAG=1' in cc.cflags
        assert '-L/my/extra/lib' in cc.ldflags
