# Operator 执行前的跨内存层预算守卫

> **Workspace:** /Users/huangding/Documents/new-SWE/09142/project-01

---

**User**

在批量生成并运行大型有限差分算子前，研究人员希望先给这次执行设定主机或设备内存上限，避免惰性分配、临时数组和 MPI 局部数据在真正启动内核后才把作业拖垮。请在 Devito 的 Operator 执行入口加入可选的内存预算控制：调用方可以分别为 host、device 或统一总量提供预算，系统在解析运行时参数、计算 Function/Array/映射数据占用和确定 MPI 局部份额后，在首次分配或提交生成内核前给出包含实际估算与预算的稳定异常并阻止执行；预算未提供时保持现有惰性分配、自动调优、memmap 和错误传播。预算检查必须与运行时替换的 Function、TimeFunction、SparseFunction、临时数组以及 device 可见性保持一致，MPI 各 rank 的结果要形成一致的成功或失败决定；预检查失败、设备查询失败和真正内核错误要能区分，失败后同一个 Operator 用更高预算或不启用预算重试时不得携带上一次的分配或状态，既有 estimate_memory、apply、序列化和非预算调用继续保持兼容。

**Assistant**

toolName: view_folder

status: success

/Users/huangding/Documents/new-SWE/09142/project-01

这是 Devito 代码库。让我先深入了解 Operator 执行入口、参数解析、内存估算等核心机制。

toolName: todo_write

status: success

Todos updated: 5 items

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/core/operator.py

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/operator/operator.py

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/operator/operator.py

现在我理解了执行主流程。让我并行查看异常体系、内存层定义、`MemoryEstimate`、参数处理与设备查询相关代码。

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/exceptions.py

toolName: search_by_regex

status: success

toolName: search_by_regex

status: success

toolName: search_by_regex

status: success

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/types/utils.py

toolName: search_by_regex

status: success

toolName: search_by_regex

status: success

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/types/dense.py

toolName: search_by_regex

status: success

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/types/dense.py

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/tests/test_operator.py

现在查看设备查询、可用性 API、配置项以及 SparseFunction 的参数处理。

toolName: search_by_regex

status: success

toolName: search_by_regex

status: success

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/arch/archinfo.py

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/arch/archinfo.py

toolName: search_by_regex

status: success

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/mpi/__init__.py

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/types/sparse.py

toolName: search_by_regex

status: success

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/mpi/distributed.py

让我查看几个剩余关键点：checkpointing 的内存报告钩子、SparseTimeFunction 的 estimate 路径、异常的导出方式。

toolName: search_by_regex

status: success

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/types/sparse.py

toolName: search_by_regex

status: success

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/tools/utils.py

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/arch/archinfo.py

toolName: search_by_regex

status: success

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/conftest.py

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/tests/test_mpi.py

研究阶段基本完成。让我确认运行环境与“Allocating”日志来源，以便测试断言预检查不触发分配。

toolName: search_by_regex

status: success

toolName: Shell

status: success

toolName: Shell

status: success

toolName: Shell

status: success

toolName: view_folder

status: success

/Users/huangding/Documents/new-SWE/09142/project-01/environment

toolName: Shell

status: success

toolName: Shell

status: success

toolName: Shell

status: success

环境缺少依赖。我用 Python 3.11 创建虚拟环境并安装 Devito 依赖（无需 Docker）。

toolName: Shell

status: success

toolName: Shell

status: success

环境就绪。让我确认几个工具函数的导出，然后开始实现。

toolName: search_by_regex

status: success

toolName: search_by_regex

status: success

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/tools/__init__.py

现在设计已清晰。让我查看 `humanbytes` 的导入路径惯例，然后开始编码。

toolName: search_by_regex

status: success

toolName: todo_write

status: success

Todos updated: 5 items

首先添加新的异常类型：

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/exceptions.py

changes: undefined

现在在 Operator 执行入口实现预算逻辑。先更新导入和模块级辅助：

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/operator/operator.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/operator/operator.py

changes: undefined

现在重构 `estimate_memory` 共用一个无分配参数构建入口，并加入预算预检查方法：

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/operator/operator.py

changes: undefined

现在加入预检查方法，并改造 `apply`：

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/operator/operator.py

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/operator/operator.py

changes: undefined

现在在 `apply` 中接入预检查，并补充文档：

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/operator/operator.py

changes: undefined

核心实现完成。先进行快速冒烟测试：

toolName: Shell

status: success

串行核心逻辑正确。现在测试设备查询失败路径、override 一致性、稀疏函数与临时数组计入：

toolName: Shell

status: success

设备查询路径可用，但失败原因消息不够友好。优化错误信息的稳定性：

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/operator/operator.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/operator/operator.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/operator/operator.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/operator/operator.py

changes: undefined

现在后台安装 mpich + mpi4py 用于 MPI 一致性验证，同时准备测试：

toolName: Shell

status: success

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/tests/test_operator.py

趁安装进行，查看 pickle 测试惯例，然后编写测试套件：

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/tests/test_pickle.py

toolName: Shell

status: success

toolName: search_by_regex

status: success

toolName: search_by_regex

status: success

pickle 惯例清楚了。现在编写正式测试，先看 test_operator.py 末尾：

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/tests/test_operator.py

toolName: search_by_regex

status: success

现在给测试文件加入新的测试类。先更新导入：

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/tests/test_operator.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/tests/test_operator.py

changes: undefined

toolName: search_by_regex

status: success

现在添加完整的串行测试类：

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/tests/test_operator.py

changes: undefined

运行新增测试类：

toolName: Shell

status: success

26 个串行测试全部通过。现在安装 mpi4py 并验证 MPI 一致性：

toolName: Shell

status: success

toolName: Shell

status: success

toolName: Shell

status: success

MPI 可用。给 test_mpi.py 添加跨 rank 一致性测试：

toolName: Shell

status: success

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/tests/test_mpi.py

changes: undefined

直接用 mpiexec 运行 MPI 一致性测试：

toolName: Shell

status: success

4 ranks 下通过。再验证 2 ranks，并直接观察跨 rank 失败时的异常消息：

toolName: Shell

status: success

toolName: Shell

status: success

toolName: Shell

status: success

toolName: Shell

status: success

heredoc 通过 mpiexec 传递不可靠，改为脚本文件：

toolName: Write

status: success

filePath: /tmp/devito_mpi_budget_check.py

changes: undefined

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

之前的 heredoc 残留任务可能造成干扰，先停止它并等待当前任务：

toolName: StopCommand

status: success

toolName: Shell

status: success

toolName: Shell

status: success

发现一个边界问题：各 rank 传入不同预算时决策可能不一致导致挂起。需求要求“各 rank 形成一致决定”，我先终止挂起任务，将**违规判定标志也纳入跨 rank 归约**：

toolName: StopCommand

status: success

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/operator/operator.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/operator/operator.py

changes: undefined

现在重跑串行测试，再用“各 rank 预算不同”的挂起场景验证：

toolName: Shell

status: success

toolName: Shell

status: success

toolName: Shell

status: success

toolName: Shell

status: success

发现判定仍不够保守：本地标志基于本地份额，rank1 用小预算看不到 rank0 的大份额。需要两轮归约——先同步全局最大占用，再据此计算本地违规标志并同步。重写该段：

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/operator/operator.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/operator/operator.py

changes: undefined

toolName: Shell

status: success

两轮归约后，即使各 rank 预算不一致也能一致失败且无分配，随后重试成功。重跑 pytest MPI 测试（2/4 ranks）：

toolName: Shell

status: success

全部通过。现在做回归验证：既有 `TestEstimateMemory` 与整个 test_operator.py：

toolName: Shell

status: success

toolName: Shell

status: success

趁回归运行，检查 lint 配置并对改动文件运行 ruff：

toolName: Shell

status: success

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/operator/operator.py

changes: undefined

toolName: Shell

status: success

toolName: Shell

status: success

CI 只运行 `ruff check --preview`（不强制 format）。以相同方式验证：

toolName: Shell

status: success

回归运行期间，检查代码库中是否有以位置参数调用 `apply` 或重写它的地方：

toolName: search_by_regex

status: success

toolName: Shell

status: success

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/checkpointing/checkpoint.py

有一个并行测试 `test_new_distributor[1]` 失败——它由 conftest 拉起 mpiexec。先看失败详情，判断是否环境问题：

toolName: Shell

status: success

失败是 macOS 上 MPICH/libfabric 的 finalize 报错（`bridge103` nic），与改动无关。用 `FI_PROVIDER=tcp` 重跑该并行测试验证：

toolName: Shell

status: success

环境问题确认。补充一个 device 可见性（CUDA_VISIBLE_DEVICES 映射）测试：

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/tests/test_operator.py

changes: undefined

toolName: Shell

status: success

运行额外回归套件（pickle/autotuner/data），设置 FI_PROVIDER 避免环境噪音：

toolName: Shell

status: success

等待回归期间，完整复查最终的预检查方法：

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/devito/operator/operator.py

实现复查完毕。查看额外回归套件结果：

toolName: Shell

status: success

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-01/tests/test_docstrings.py

toolName: Shell

status: success

autotuner 出现 5 个编译错误。确认是否我的改动导致——用 git stash 在干净树上复现：

toolName: Shell

status: success

toolName: Shell

status: success

确认 5 个 autotuner 失败在干净树上同样存在（Apple clang 不兼容编译参数），与本次改动无关。清理测试产物并确认来源：

toolName: search_by_regex

status: success

toolName: delete_file

status: success

最后通过 conftest 的真实 `parallel` 标记机制（CI 方式，含子 mpiexec）验证新 MPI 测试：

toolName: Shell

status: success

全部通过。更新进度并做最终诊断检查：

toolName: todo_write

status: success

Todos updated: 5 items

toolName: GetDiagnostics

status: success

toolName: GetDiagnostics

status: success

toolName: Shell

status: success

已完成。在 Devito 的 Operator 执行入口加入了可选的内存预算控制，默认行为完全不变。

## 用法

```python
# 统一总量预算（字节）
op.apply(memory_limit=8 * 1024**3)

# 分层预算：host / device 可任意组合，也可加 total
op.apply(memory_limit={'host': 4 * 1024**3, 'device': 16 * 1024**3})

# 也接受 numpy 整数；MemoryEstimate（host/device 映射）可直接传入
op(memory_limit=np.int64(...))   # __call__ 同样支持
```

## 执行时序与判定

预检查在 [apply()](file:///Users/huangding/Documents/new-SWE/09142/project-01/devito/operator/operator.py#L1203-L1277) 的**最前面**执行，早于 JIT 编译、惰性分配、autotuning 和内核提交。核心逻辑在 [_check_memory_budget](file:///Users/huangding/Documents/new-SWE/09142/project-01/devito/operator/operator.py#L1052-L1202)：

1. 用与 `estimate_memory` 完全相同的**无分配路径**（[_memory_estimate_arguments](file:///Users/huangding/Documents/new-SWE/09142/project-01/devito/operator/operator.py#L1076-L1085)，即 `_prepare_arguments(estimate_memory=True)`）解析运行时参数，因此自动覆盖：运行时替换的 Function / TimeFunction / SparseFunction、稀疏插值表、C-land 临时数组（CIRE 等堆数组）、memmap 双份占用，以及每个 rank 的 MPI局部分区份额。
2. Device 平台会经 `_physical_deviceid` 解析 `CUDA_VISIBLE_DEVICES` 可见性并查询空闲显存；预算同时给出每层系统可用量作为报告信息。
3. 估算超限时抛出 [MemoryBudgetExceeded](file:///Users/huangding/Documents/new-SWE/09142/project-01/devito/exceptions.py#L70-L126)，稳定携带 `estimate`（host/device/total，字节）、`budget`、`available`、`layers`、`op_name`。

## 三类错误可区分

- **预检查失败**：`MemoryBudgetExceeded`（基类 `MemoryPrecheckError`），内核从未提交；
- **设备查询失败**：[DeviceQueryError](file:///Users/huangding/Documents/new-SWE/09142/project-01/devito/exceptions.py#L129-L158)，无驱动/设备不可见或查询抛错（如编排节点无 GPU）时抛出，与预算超支分开；
- **真正内核错误**：仍是既有 `ExecutionError`，二者无继承关系。
- 非法 `memory_limit`（负数、浮点、未知层名等）抛既有 `InvalidArgument`。

## MPI 一致性

采用**两轮 Allreduce**（MAX 占用/状态、MIN 可用量，再 MAX 违规判定）：即使各 rank 局部分区大小不同（实测 2 rank：680 B vs 612 B）、甚至预算参数不一致，所有 rank 也会基于同一个跨 rank 保守估算得到**一致的成功/失败决定**，不会出现部分 rank 进入内核交换而挂起；某 rank 估算/查询异常也会先同步再统一抛出。

## 重试与兼容性

- 失败的预检查不触碰数据、不触发编译、不写 `op._state`（已用日志 `"Allocating"`、`_data is None`、`_lib is None` 验证）；同一 Operator 用更高预算或不带预算重试不会携带上次状态。
- `memory_limit=None`（默认）时代码路径与历史完全一致；`estimate_memory` 仅抽出共用入口、行为不变；pickle 序列化/反序列化后预算检查仍有效。

## 改动文件

- [devito/exceptions.py](file:///Users/huangding/Documents/new-SWE/09142/project-01/devito/exceptions.py)：新增 `MemoryPrecheckError` / `MemoryBudgetExceeded` / `DeviceQueryError`。
- [devito/operator/operator.py](file:///Users/huangding/Documents/new-SWE/09142/project-01/devito/operator/operator.py)：预算归一化 [_normalize_memory_limit](file:///Users/huangding/Documents/new-SWE/09142/project-01/devito/operator/operator.py#L66-L113)、预检查方法、`apply(memory_limit=None)` 及文档。
- [tests/test_operator.py](file:///Users/huangding/Documents/new-SWE/09142/project-01/tests/test_operator.py#L2594-L2882)：新增 `TestMemoryBudget`（27 个串行用例）。
- [tests/test_mpi.py](file:///Users/huangding/Documents/new-SWE/09142/project-01/tests/test_mpi.py#L3697-L3740)：新增 2/4 rank 一致性测试。

## 验证结果

- 新增 27 个串行测试 + 2/4 rank MPI 测试全部通过；
- `TestEstimateMemory` 72 项、整个 `test_operator.py` 261 项通过（唯一失败是本机 MPICH libfabric finalize 的环境问题，加 `FI_PROVIDER=tcp` 即过）；`test_pickle.py`/`test_data.py` 全部通过；
- `test_autotuner.py` 的 5 个编译失败在未改动的干净树上同样存在（Apple clang 不支持 `-fdenormal-fp-math=ieee` 等标志），与本次改动无关；
- `ruff check --preview` 无告警。
