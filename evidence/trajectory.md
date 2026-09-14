# MPI 波场检查点的原子持久化与进程重启

> **Workspace:** /Users/huangding/Documents/new-SWE/09142/project-03

---

**User**

在使用 MPICH 的集群上编译第一个带 MPI 的 Devito 算子时，编译器探测会在读取 mpi 启动器版本后直接拒绝继续，研究人员只能手工改写工具链参数。请为 MPI 编译器探测补上对 MPICH 的可用路径：从对应的编译器包装器读取编译与链接信息，正确处理带引号的路径、重复参数和空字段，把解析出的选项送入 JIT 工具链并纳入编译缓存签名；未知发行版、探测命令不可执行或输出无法解析时要保留明确的失败原因，并允许调用方已经显式提供的编译器选项继续按原方式工作。探测结果在同一作业内应保持稳定，第一次失败不能污染后续成功探测或缓存，非 MPI 编译、OpenMPI 和 Spectrum MPI 的既有路径以及串行算子结果不得改变。

**Assistant**

toolName: view_folder

status: success

/Users/huangding/Documents/new-SWE/09142/project-03

这是 Devito 代码库。让我先查看 MPI 编译器探测相关的核心文件。

toolName: todo_write

status: success

Todos updated: 7 items

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/devito/arch/archinfo.py

archinfo.py 中没有 MPI 探测逻辑。让我查看 compiler.py，这是工具链核心。

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/devito/arch/compiler.py

现在我找到了关键代码。让我查看 `memoized_func` 实现、缓存签名机制以及相关测试。

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/devito/tools/memoization.py

toolName: search_by_regex

status: success

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/tests/test_arch.py

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/conftest.py

toolName: search_by_regex

status: success

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/devito/operator/operator.py

toolName: search_by_regex

status: success

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/devito/tools/abc.py

toolName: search_by_regex

status: success

toolName: search_by_regex

status: success

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/devito/operator/operator.py

toolName: search_by_regex

status: success

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/devito/ir/iet/nodes.py

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/devito/parameters.py

让我查看 codepy 的缓存机制，确认工具链是如何进入缓存签名的。

toolName: Shell

status: success

toolName: Shell

status: success

toolName: search_by_regex

status: success

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/devito/arch/__init__.py

toolName: web_search

status: success

toolName: view_files

status: success

filePath: /var/folders/0t/yzgz_m2x48ddb2nk2jnw95nh0000gn/T/trae/toolcall-output/2b95160e-3060-45d5-87f9-2e56f58f9c27.txt

codepy 缓存签名来自 `toolchain.abi_id()`。让我查看 codepy toolchain 的 abi_id 实现。

toolName: web_search

status: failed

toolName: Shell

status: success

toolName: search_by_regex

status: success

toolName: search_by_regex

status: success

toolName: Shell

status: success

toolName: Shell

status: success

实际约束安装的是 codepy 2023.1。让我下载该版本查看其 GCCToolchain 与缓存键。

toolName: Shell

status: success

toolName: Shell

status: success

toolName: Shell

status: success

toolName: search_by_regex

status: success

toolName: Shell

status: success

toolName: search_by_regex

status: success

让我参考上游 Devito 是否已有相关修复以及实际 MPICH 包装器的输出格式。

toolName: web_search

status: success

MPICH 的 `-compile_info`/`-link_info` 确认可用。让我查看 MPICH 包装器的实际输出格式，确认首个 token 及引号处理。

toolName: Shell

status: success

toolName: Shell

status: success

toolName: Shell

status: success

toolName: Shell

status: success

toolName: view_files

status: success

filePath: /tmp/mpicc.txt

toolName: Shell

status: success

toolName: Shell

status: success

toolName: Shell

status: success

toolName: view_files

status: success

filePath: /tmp/mpich-4.2.3/src/env/mpicc.sh.in

现在我完全掌握了 MPICH 包装器的输出格式。让我对比上游 Devito 当前的 compiler.py，看官方是否已有类似修复可供参考。

toolName: Shell

status: success

toolName: Shell

status: success

toolName: Shell

status: success

toolName: Shell

status: success

toolName: Shell

status: success

让我查看现有缓存测试与 MPI 测试，了解既有的行为约束。

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/tests/test_caching.py

toolName: search_by_regex

status: success

让我查看几个关键依赖：异常类、filter_ordered、以及是否有代码清理这些 memoized 缓存。

toolName: search_by_regex

status: success

toolName: search_by_regex

status: success

toolName: search_by_regex

status: success

toolName: search_by_regex

status: success

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/devito/tools/utils.py

toolName: todo_write

status: success

Todos updated: 7 items

toolName: search_by_regex

status: success

现在开始实现。先确认项目支持的 Python 版本（`errors=` 参数兼容性）以及 Cuda/Hip 分支的完整上下文。

toolName: search_by_regex

status: success

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/devito/exceptions.py

现在实现核心修改。先更新导入与两个探测函数：

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/devito/arch/compiler.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/devito/arch/compiler.py

changes: undefined

现在替换旧的 `sniff_mpi_distro` 和 `sniff_mpi_flags`，并插入 MPICH 解析辅助函数：

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/devito/arch/compiler.py

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/devito/arch/compiler.py

changes: undefined

现在接入工具链：在 `Compiler.__init__` 中初始化 `mpi_probe`，并添加 `abi_id` 覆盖。

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/devito/arch/compiler.py

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/devito/arch/compiler.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/devito/arch/compiler.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/devito/arch/compiler.py

changes: undefined

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/devito/arch/compiler.py

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/devito/arch/compiler.py

changes: undefined

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/devito/arch/compiler.py

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/devito/arch/compiler.py

changes: undefined

核心实现完成。先做语法检查和解析逻辑的快速验证：

toolName: todo_write

status: success

Todos updated: 7 items

toolName: Shell

status: success

默认 Python 缺少依赖。查找带依赖的环境：

toolName: Shell

status: success

toolName: Shell

status: success

toolName: Shell

status: success

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/requirements.txt

toolName: Shell

status: success

toolName: Shell

status: success

解析逻辑正确——`-L/path` 粘合形式应保持为单个 token，是我的测试预期写错了。修正后继续验证：

toolName: Shell

status: success

解析层全部通过。现在用伪造的包装器脚本做端到端验证：

toolName: Shell

status: success

端到端探测全部通过。现在验证工具链集成与缓存签名：

toolName: Shell

status: success

toolName: Shell

status: success

功能正常，第一次脚本中是串行工具链那一步有异常。单独定位：

toolName: Shell

status: success

toolName: search_by_regex

status: success

关键发现：codepy 2023.1 的 `GCCToolchain.abi_id()` 已包含 `self._cmdline([])`。查看 `_cmdline` 构成：

toolName: view_files

status: success

filePath: /Users/huangding/.pyenv/versions/3.11.9/lib/python3.11/site-packages/codepy/toolchain.py

codepy 2023.1 的 `GCCToolchain.abi_id()` 已通过 `_cmdline([])` 把全部 cflags/ldflags 纳入缓存签名。再确认约束允许的最低版本 codepy 2019.1 是否同样如此：

toolName: Shell

status: success

toolName: Shell

status: success

已确认：自 codepy 2019.1 起，cflags/ldflags 就通过 `_cmdline([])` 自动进入 `abi_id()` 缓存签名。自定义标记是冗余的，且会让 MPICH 路径与 OpenMPI 路径结构不一致。按最小改动原则移除自定义 `abi_id`/`mpi_probe`，让 MPICH 标志走与 OpenMPI 完全相同的既有签名机制：

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/devito/arch/compiler.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/devito/arch/compiler.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/devito/arch/compiler.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/devito/arch/compiler.py

changes: undefined

现在查看与原始文件的完整差异：

toolName: Shell

status: success

toolName: Shell

status: success

差异仅在导入和探测函数本身。现在验证标志自动进入 `abi_id` 缓存签名、且不同 MPI 安装产生不同签名：

toolName: Shell

status: success

toolName: Shell

status: success

隔离运行正常。把之前的脚本落盘定位具体失败行：

toolName: Write

status: success

filePath: /tmp/check_toolchain.py

changes: undefined

toolName: Shell

status: success

`-I/opt/mpich2` 不在 GNU 自定义编译器的 abi 中是正确的——GNU/Clang 走 `mpicc` 包装器直连（OpenMPI 同理），探测仅服务于 Cuda/Hip。探索性验证全部通过。现在编写正式的 pytest 测试套件：

toolName: todo_write

status: success

Todos updated: 7 items

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/tests/test_arch.py

changes: undefined

编辑出现错误，立即修复文件头部：

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/tests/test_arch.py

changes: undefined

现在在测试文件末尾追加 MPI 探测测试套件：

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/tests/test_arch.py

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/tests/test_arch.py

changes: undefined

修正测试脚本中的 shell 续行（双引号内 `\`+换行会吞掉空格导致 token 粘连）及未使用变量：

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/tests/test_arch.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/tests/test_arch.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/tests/test_arch.py

changes: undefined

现在运行整个测试文件：

toolName: Shell

status: success

一个测试失败：非可执行包装器未抛错。手动复现调查（注意 POSIX `execvpe` 在首个候选 EACCES 时会继续搜索 PATH）：

toolName: Shell

status: success

本机装有真实 MPICH 5.0.1（`/opt/homebrew/bin/mpicc`），POSIX 在假包装器不可执行时继续沿 PATH 找到了真包装器。改用绝对路径调用以精确测试“不可执行”场景：

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/tests/test_arch.py

changes: undefined

toolName: Shell

status: success

全部通过。本机正好装有真实 MPICH 5.0.1，用真实包装器做实地验证：

toolName: Shell

status: success

真实 MPICH 5.0.1 输出与实现假设完全一致。端到端验证真实探测：

toolName: Shell

status: success

toolName: Shell

status: success

toolName: Shell

status: success

toolName: Shell

status: success

mpi4py 已链接真实 MPICH 5.0.1。运行真实的 Devito MPI 算子 JIT 编译与执行（双进程，标题场景）：

toolName: Write

status: success

filePath: /tmp/mpich_smoke.py

changes: undefined

toolName: Shell

status: success

toolName: Shell

status: success

toolName: Shell

status: success

真实 MPICH 双进程 JIT 编译与执行成功。现在做回归检查：lint、相关测试与一个真实算子编译冒烟：

toolName: Shell

status: success

toolName: Shell

status: success

修复 ruff 问题：改用 `capture_output=True`，测试脚本长行用引号内续行（保留前导空格），以及 Yoda 条件：

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/devito/arch/compiler.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/devito/arch/compiler.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/tests/test_arch.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/tests/test_arch.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/tests/test_arch.py

changes: undefined

重新运行 ruff 与测试：

toolName: Shell

status: success

toolName: Shell

status: success

toolName: Shell

status: success

本地 ruff 0.15.2 的默认格式化规则与项目配置不同（连未改动的导入都要求改）。查看项目的 ruff 配置：

toolName: Shell

status: success

项目仅强制 `ruff check`（已通过），不强制 format。现在跑串行算子 JIT 冒烟和真实 MPICH 下的仓库 MPI 测试：

toolName: Shell

status: success

toolName: Shell

status: success

toolName: Write

status: success

filePath: /tmp/serial_smoke.py

changes: undefined

toolName: Shell

status: success

toolName: Shell

status: success

串行与真实 MPICH 并行测试均通过。检查文档中是否提到该旧限制需要同步：

toolName: search_by_regex

status: success

做最终代码审查，通读修改后的探测模块：

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/devito/arch/compiler.py

toolName: GetDiagnostics

status: success

toolName: GetDiagnostics

status: success

toolName: Shell

status: success

全部通过。最后审查完整差异：

toolName: Shell

status: success

toolName: Shell

status: success

生产代码改动严格限定在 `import shlex` 与 MPI 探测块，工具链类零改动。最后通读一遍最终实现：

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/devito/arch/compiler.py

补一个防御性细节：未知分支二次探测若恰遇环境变化，reason 可能为 None：

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-03/devito/arch/compiler.py

changes: undefined

toolName: Shell

status: success

toolName: todo_write

status: success

Todos updated: 7 items

已完成。改动只涉及两个文件，生产代码改动严格限定在 [compiler.py](file:///Users/huangding/Documents/new-SWE/09142/project-03/devito/arch/compiler.py) 的 MPI 探测块。

## 修改内容

**[devito/arch/compiler.py](file:///Users/huangding/Documents/new-SWE/09142/project-03/devito/arch/compiler.py)**

1. **MPICH 可用探测路径**（[sniff_mpi_flags](file:///Users/huangding/Documents/new-SWE/09142/project-03/devito/arch/compiler.py#L372-L416)）：识别为 `MPICH` 后，从对应包装器（尊重 `mpicc`/`mpicxx` 参数）读取信息——现代包装器优先用 `-show-compile-info`/`-show-link-info` 分离编译与链接选项；旧版包装器（仅支持 `-show`，所有 MPICH 版本通用）自动回退，并按选项族启发式分区。
2. **健壮解析**：用 `shlex` 正确处理**带引号（含空格）的路径**；把 `-I dir`、`-Xlinker -rpath` 等按"原子参数"分组后保序去重，因此重复的 `-Xlinker ... -Xlinker ...` 不会被错误合并；**空字段**（`''`、连续空白）一律丢弃；引号不配对时抛出含原始行的明确错误。
3. **明确的失败原因**：未知发行版（携带 launcher 探测原因）、显式不支持的发行版（如 IntelMPI 指名）、包装器不可执行、非零退出、空输出、输出无法解析，统一抛 `CompilationError` 并说明命令与原因，取代原来的裸 `NotImplementedError`。
4. **作业内稳定且失败不污染**：成功探测才写入进程内缓存，失败（含 `unknown`）绝不缓存——后加载 MPI 模块后再次探测可以成功；每次返回**全新可变列表**，nvcc 路径 `remove('-pthread')` 等调用方修改不会污染缓存或后续探测；失败发生在工具链构造前，不会留下 JIT 缓存条目。
5. **缓存签名**：解析选项与 OpenMPI 一样 extend 进 `cflags`/`ldflags`，自动进入 codepy 既有的 `GCCToolchain.abi_id()`（`_cmdline` 含全部 flags，已核实约束内 codepy 2019.1–2023.1 均如此）构成的 JIT 校验和——不同 MPICH 安装产生不同签名。
6. **不变项**：OpenMPI/Spectrum MPI 的 `--showme` 分支逐字保留；`sniff_mpi_distro` 仍返回字符串契约（conftest 依赖），且 launcher 缺失/失败时不再抛裸异常而是返回 `'unknown'`；GNU/Clang（直连 mpicc）、串行算子、`CC/CXX/MPICC/CFLAGS/LDFLAGS` 显式选项全部零改动。

**[tests/test_arch.py](file:///Users/huangding/Documents/new-SWE/09142/project-03/tests/test_arch.py)**：新增 16 个测试，覆盖现代/旧版 MPICH、引号/重复/空字段、包装器参数选择、稳定性与变更隔离、失败不缓存、不可执行、不可解析、OpenMPI 行为对照、nvcc/hipcc 工具链接入与缓存签名、显式用户选项。

## 验证

- `pytest tests/test_arch.py` 20/20 通过，`ruff check` 干净；
- 本机真实 **MPICH 5.0.1** 下探测结果正确（`-I.../include` 与 `-L.../lib -lmpi -lpmpi` 分离）；
- `mpiexec -n 2` 下真实 Devito MPI 算子 JIT 编译并执行成功，`tests/test_mpi.py` 抽测 11 项通过；
- 串行算子 JIT、`test_cinterface`、`test_environment` 均通过，无回归。
