# 分布式索引交换的消息隔离与失败回收

> **Workspace:** /Users/huangding/Documents/new-SWE/09142/project-02

---

**User**

两个独立的 MPI 线程同时对同一个分布式 Data 视图做索引读取和赋值时，偶尔会把一次请求的头部当成另一条消息解析，表现为结果错位、阻塞或下一次交换收到残留数据。请修正 Devito 分布式索引的通信生命周期，使每个 ExchangePlan 的 get、put 及结构化重分布都能在并发、嵌套和连续调用中获得隔离且可复用的通信标识，并让请求头、payload、self-rank 快路径和真实点对点消息始终配对；同一 communicator 上同时存在不同 Data、不同索引计划或不同 dtype 时不得互相消费消息，计划复用不能把上次调用的请求状态带入下一次。遇到越界或重复目标时，各 rank 仍须先形成一致错误再退出，不得留下未完成的非阻塞发送；传输失败后重新建立计划或执行另一种 get/put 应能恢复，串行与 MPI=full 的既有全局索引、广播赋值和 dtype 映射行为继续兼容。

**Assistant**

toolName: view_folder

status: success

/Users/huangding/Documents/new-SWE/09142/project-02

toolName: todo_write

status: success

Todos updated: 6 items

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/plan.py

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/transport.py

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/redistribution.py

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/exchange.py

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/layout.py

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/__init__.py

toolName: search_by_regex

status: success

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/data.py

现在查看 MPI 基础设施与测试，理解线程模型和既有测试约定。

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/mpi/__init__.py

toolName: search_by_regex

status: success

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/tests/test_data.py

toolName: search_by_regex

status: success

toolName: search_by_regex

status: success

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/tools/threading.py

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/mpi/distributed.py

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/tests/test_data.py

让我查看是否有针对 distributed 引擎的直接测试，以及 MPI 环境是否可用。

toolName: search_by_regex

status: success

toolName: Shell

status: success

toolName: Shell

status: success

toolName: Shell

status: success

环境中没有 MPI，先继续静态分析。查看 selection 层与 conftest 的并行机制。

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/selection.py

toolName: search_by_regex

status: success

toolName: search_by_regex

status: success

toolName: search_by_regex

status: success

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/mpi/distributed.py

让我查看 git 历史，了解这个分布式索引引擎的演进背景。

toolName: Shell

status: success

toolName: Shell

status: success

toolName: Shell

status: success

设计前还需确认 devito 其他 MPI 消息使用的 tag 范围，避免与新的动态 tag 空间冲突。

toolName: search_by_regex

status: success

toolName: search_by_regex

status: success

toolName: search_by_regex

status: success

toolName: search_by_regex

status: success

设计已成型。开始实现前，先确认 Decomposition 的结构（channel key 需要全局确定的内容）。

toolName: todo_write

status: success

Todos updated: 6 items

toolName: search_by_regex

status: success

需要确认 Data 是否携带可在各 rank 间一致区分不同数组的身份（如 name 或 Function 反向引用）。

toolName: search_by_regex

status: success

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/data.py

需要让不同 Data 数组获得跨 rank 一致的身份。查看 Function 的 Data 分配与视图链。

toolName: search_by_regex

status: success

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/types/dense.py

toolName: search_by_regex

status: success

检查 `mpi4py_mapper` 工具的位置与内容。

toolName: search_by_regex

status: success

现在开始实现。首先重写 transport.py：

toolName: Write

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/transport.py

changes: undefined

transport 完成。现在更新 plan.py：

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/plan.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/plan.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/plan.py

changes: undefined

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/plan.py

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/plan.py

changes: undefined

现在替换 helpers/get/put 部分（错误共识、channel、get、put）：

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/plan.py

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/plan.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/plan.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/plan.py

changes: undefined

现在更新 `sparse_push` 并添加 channel key 构造函数：

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/plan.py

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/plan.py

changes: undefined

更新 exchange.py 传入数据身份：

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/exchange.py

changes: undefined

更新 redistribution.py：

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/redistribution.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/redistribution.py

changes: undefined

`redistribute_set` 的 LAND 门控也是无 tag 集合通信，并发时同样会错配。改为通过 channel 信封做 P2P 一致表决：

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/redistribution.py

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/redistribution.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/redistribution.py

changes: undefined

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/redistribution.py

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/redistribution.py

changes: undefined

注意：`gcoords` 是各 rank 本地拥有的坐标（跨 rank 不同），不能入 key——改用全局 affine selection 与 source 全局形状：

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/plan.py

changes: undefined

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/redistribution.py

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/redistribution.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/redistribution.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/redistribution.py

changes: undefined

现在给 Data 添加跨 rank 顺序一致的分配身份：

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/data.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/data.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/data.py

changes: undefined

检查 plan.py 是否还有遗留的 MPI 引用，并整体复核：

toolName: search_by_regex

status: success

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/__init__.py

changes: undefined

现在搭建可运行环境验证语法与串行测试：

toolName: todo_write

status: success

Todos updated: 7 items

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

串行 numpy 路径正常（引擎仅在 decomposed 时启用）。先运行已有的非并行测试，然后构造一个线程内共享内存的仿真 MPI 验证新协议：

toolName: Shell

status: success

串行测试通过。现在构建仿真 MPI（多线程共享内存，严格按 (source, tag) 匹配 + 请求取消语义）来端到端验证新协议。先看 Decomposition 的构造方式：

toolName: search_by_regex

status: success

关键发现：同一 plan 的 get 和 put 也必须使用不同 channel——否则各 rank 本地 get/put 交错顺序不同会导致 seq 位置上调用类型错配。修正：

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/plan.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/plan.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/plan.py

changes: undefined

现在编写一个仿真 MPI 验证脚本（共享内存、严格 (src,dst,tag) 匹配、线程即 rank），端到端验证并发隔离、错误共识与恢复：

toolName: Write

status: success

filePath: /tmp/devito_mpi_sim.py

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

toolName: StopCommand

status: success

toolName: Shell

status: success

toolName: Shell

status: success

找到根因：高级索引的 selection 是**各 rank 本地**的索引数组，不能进入跨 rank 的 channel key。channel 身份应为 (目标数据 uid, 操作类型)——header 自描述路由，跨 rank 配对任意计划都是安全的：

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/plan.py

changes: undefined

门控 channel 也不能依赖各 rank 本地的数组值（回退路径可能含数组索引）。改为基于结构的 rank 无关摘要：

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/redistribution.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/redistribution.py

changes: undefined

toolName: Shell

status: success

通信已正确完成——是仿真脚本本身初始化为 0 而非 -1。修正脚本：

toolName: Shell

status: success

toolName: view_files

status: success

filePath: /tmp/devito_mpi_sim.py

toolName: edit_file_search_replace

status: success

filePath: /tmp/devito_mpi_sim.py

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

并发压力测试的**测试脚本**有 bug：value 用本地数组按全局索引取值（越界/错位）。应始终用全局规范数组生成 values。修正：

toolName: view_files

status: success

filePath: /tmp/devito_mpi_sim.py

toolName: edit_file_search_replace

status: success

filePath: /tmp/devito_mpi_sim.py

changes: undefined

toolName: Shell

status: success

toolName: Shell

status: success

toolName: Shell

status: success

toolName: Shell

status: success

并发压力测试通过。运行完整仿真套件（含错误共识/恢复、tag 隔离、replicated payload）：

toolName: Shell

status: success

等待期间确认 Function 分配 Data 时确实传入 distributor（uid 赋值前提）：

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/types/dense.py

toolName: Shell

status: success

toolName: Shell

status: success

toolName: Shell

status: success

toolName: view_files

status: success

filePath: /tmp/devito_mpi_sim.py

恢复后的 get 挂起。查看所有 rank 线程的完整栈与队列状态：

toolName: Shell

status: success

toolName: Shell

status: success

单个 rank 挂起而其余完成——典型的 tag/seq 不一致。直接插桩打印各 rank 的 channel key 与 tag：

toolName: Shell

status: success

标签一致但仍有单 rank 挂起。在仿真器中加入等待超时转储，检查消息表状态：

toolName: Shell

status: success

仍是测试脚本断言错误（恢复 put 只写一个点，另一位置为 -1），3 个 rank 因断言异常退出导致 rank3 空等。修正期望值：

toolName: edit_file_search_replace

status: success

filePath: /tmp/devito_mpi_sim.py

changes: undefined

toolName: Shell

status: success

等待期间，用 ruff 检查改动文件的风格与语法：

toolName: Shell

status: success

toolName: Shell

status: success

toolName: Shell

status: success

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/transport.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/plan.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/transport.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/transport.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/transport.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/transport.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/transport.py

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

toolName: Shell

status: success

toolName: Shell

status: success

sed 破坏了脚本结构，直接写内联复现脚本：

toolName: Shell

status: success

toolName: Shell

status: success

toolName: Shell

status: success

toolName: Shell

status: success

直接复现完全正常。重新运行完整脚本（join 已缩短，失败会快速暴露）：

toolName: Shell

status: success

toolName: Shell

status: success

等待全量仿真完成期间，先完整复核 transport.py 最终版：

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/transport.py

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/redistribution.py

toolName: Shell

status: success

等待期间，向仓库测试添加并发回归测试。先看 test_data.py 的导入和并行标记：

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/tests/test_data.py

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/tests/test_data.py

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/tests/test_data.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/tests/test_data.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/tests/test_data.py

changes: undefined

toolName: Shell

status: success

toolName: Shell

status: success

replicated 测试在前置测试后才挂起。二分定位干扰来源：

toolName: Shell

status: success

toolName: Shell

status: success

第二次运行挂起——与进程状态/时序有关。直接在双跑场景中 dump 标签与消息表：

toolName: Shell

status: success

toolName: view_files

status: success

filePath: /tmp/devito_mpi_sim.py

又是测试脚本 bug：replicated 场景每个 rank 都用了 `[7,0]` 的 selection，但非 0 rank 的 vals 为空。修正为 rank 条件化 idx：

toolName: edit_file_search_replace

status: success

filePath: /tmp/devito_mpi_sim.py

changes: undefined

toolName: Shell

status: success

全部通过。补充结构化重分布（`redistribute_set._push` 路径）的仿真测试：

toolName: edit_file_search_replace

status: success

filePath: /tmp/devito_mpi_sim.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /tmp/devito_mpi_sim.py

changes: undefined

toolName: Shell

status: success

结构化重分布通过。跑完整 test_data.py 与 lint：

toolName: Shell

status: success

toolName: Shell

status: success

toolName: Shell

status: success

环境性失败（无 mpi4py）， pristine 代码同样失败。确认非并行测试全部通过：

toolName: Shell

status: success

尝试安装真实 MPI（Homebrew mpich + mpi4py）以运行实际并行测试：

toolName: Shell

status: success

toolName: Shell

status: success

mpi4py 可用（exit 时的 OFI Finalize 警告是 mpich 本机网络环境问题）。运行真实 4-rank 并行测试：

toolName: Shell

status: success

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/conftest.py

直接用 mpiexec 复现真实并行场景查看错误：

toolName: Write

status: success

filePath: /tmp/devito_mpi_check.py

changes: undefined

toolName: Shell

status: success

真实 MPI 下功能正常。pytest 失败可能来自 MPICH Finalize 的 OFI 报错导致退出码非零。查看 conftest 如何判定与输出：

toolName: search_by_regex

status: success

toolName: Shell

status: success

确认是本机 libfabric 环境问题（`FI_PROVIDER=tcp` 即正常），与补丁无关。带该环境变量重跑并行测试：

toolName: Shell

status: success

既有 8 个高级索引测试全部通过。新并发测试失败，直接 mpiexec 复现查看原因：

toolName: Write

status: success

filePath: /tmp/devito_mpi_conc.py

changes: undefined

toolName: Shell

status: success

toolName: Shell

status: success

toolName: Shell

status: success

原因是 `Query_thread()` 在 Grid 触发 MPI 初始化之前调用。调整测试顺序：

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/tests/test_data.py

changes: undefined

toolName: Shell

status: success

toolName: edit_file_search_replace

status: success

filePath: /tmp/devito_mpi_conc.py

changes: undefined

toolName: Shell

status: success

toolName: Shell

status: success

toolName: Shell

status: success

toolName: Shell

status: success

读到错误值是因为测试数据初始为 0，reader 可能在 writer 首次写入前读取——初始化竞争，不是协议问题（仿真中预初始化了）。测试前先本地规范初始化：

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/tests/test_data.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /tmp/devito_mpi_conc.py

changes: undefined

toolName: Shell

status: success

真实 MPI 并发通过。重复运行确认无 flake，然后跑 pytest 全套高级索引：

toolName: Shell

status: success

toolName: Shell

status: success

全部通过。运行完整 TestDataDistributed（含结构化重分布、广播赋值回退路径）：

toolName: Shell

status: success

全部 43 个测试通过。再以 `DEVITO_MPI=full` 验证关键路径：

toolName: Shell

status: success

toolName: search_by_regex

status: success

验证 dtype 映射（float32/float16 线类型）在真实 MPI 下的 get/put：

toolName: Write

status: success

filePath: /tmp/devito_mpi_dtype.py

changes: undefined

toolName: Shell

status: success

toolName: edit_file_search_replace

status: success

filePath: /tmp/devito_mpi_dtype.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /tmp/devito_mpi_dtype.py

changes: undefined

toolName: Shell

status: success

TimeFunction 变体是我脚本构造问题（save/time_order 分配细节，pytest 的 time-window 测试已覆盖该引擎路径）。去掉该段，确认 float32/float16：

toolName: edit_file_search_replace

status: success

filePath: /tmp/devito_mpi_dtype.py

changes: undefined

toolName: Shell

status: success

核心路径全部验证。最终通读 plan.py 确认无遗留：

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/plan.py

为严格保证“先达成一致错误、再退出”，put 不应在共识前用用户 value 构造 rows（形状错误的 value 会在个别 rank 提前抛不同异常）。让错误情况下 rows 延迟/跳过：

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/plan.py

changes: undefined

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/plan.py

changes: undefined

重新验证仿真套件与真实 MPI 错误测试：

toolName: Shell

status: success

toolName: Shell

status: success

最终 lint 与串行回归：

toolName: Shell

status: success

全部通过。put 重构后再完整跑一遍 4-rank 全套 TestDataDistributed：

toolName: Shell

status: success

再以 6 个 rank 验证（不规则 rank 数）：

toolName: Shell

status: success

更新 redistribution 模块级 docstring（原描述提到 collective LAND）：

toolName: view_files

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/redistribution.py

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/redistribution.py

changes: undefined

toolName: search_by_regex

status: success

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/__init__.py

changes: undefined

`channel_key` 的 `gcoords` 参数已无人使用，删除以免留下死接口：

toolName: edit_file_search_replace

status: success

filePath: /Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/plan.py

changes: undefined

toolName: Shell

status: success

toolName: todo_write

status: success

Todos updated: 7 items

toolName: Shell

status: success

修复完成并通过真实 MPI 验证。以下是完整说明。

## 根因分析

旧实现在并发（同 comm 上两个线程各自驱动 get/put）下有四处结构性缺陷：

1. **固定 tag（41–44，transport 默认 0）**：所有 `ExchangePlan`、get/put、结构化重分布共用；两个并发 get（或两个 put）的请求头/载荷互相匹配，于是"一次请求的头部被当成另一条消息解析"，不同 Data、不同 dtype 同样串流。
2. **无 tag 的集合通信**：`Reduce_scatter_block` 用来发现接收数量，错误共识用 `allreduce/allgather`。集合通信在同一 comm 上不按 tag 匹配，多线程并发时各 rank 的线程胜出顺序不同，指示器向量跨调用错配 → 计数错误 → `Probe` 永久阻塞；`redistribute_set` 的 `LAND` 门控同理。
3. **请求无生命周期管理**：`Isend` 只在成功路径 `Waitall`；任一 rank 中途异常，未完成的发送留在 MPI 队列里，被**下一次**调用的 `Probe` 收到（"下一次交换收到残留数据"）。
4. **计划复用无逐调用状态**：固定 tag + 悬挂请求使缓存复用的计划把上次状态带入下次。

## 修复方案

- **`Channel` 通信身份**（[transport.py](file:///Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/transport.py)）：按内容（blake2b：全局 shape、全局分解边界、稳定数组身份、操作种类）在各 rank 独立导出相同 key；get 与 put 分通道。[data.py](file:///Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/../data.py) 为分布式分配新增跨 rank 顺序一致的 `_dist_uid`（SPMD 同序构造），切片/转置视图自动继承——同形同分解的不同 Data 也不会共用通道。
- **隔离且可复用、逐调用全新**：`with channel(comm)` 每次绑定递增序号与 4 个全新 tag（信封/载荷 × 请求头/值）；通道对象只含 hash、`RLock` 和计数器，**不持有任何请求/缓冲区**——复用不携带旧状态，传输失败后下一次调用天然用新 tag 恢复。同通道并发由 `RLock` 串行，不同通道完全并行（嵌套调用即不同通道）。
- **纯点对点两阶段协议**（彻底去掉无 tag 集合）：每对 rank 每阶段交换一个固定 4×int64 信封 `[元素数, 错误码, itemsize, magic]`，先全部 post Irecv 再 Isend，无死锁且每 rank 确切知道收 `nprocs-1` 个信封；载荷严格按信封承诺稀疏点对点。self-rank 走本地快路径，键与线上消息完全一致。
- **防串流与清理**：信封 magic + itemsize 校验拒绝跨上下文消息；任何异常经 `_drain_requests` 取消/等待/释放所有未完成请求，不留悬挂非阻塞发送。
- **一致错误退出**：越界/重复错误码随信封全员汇聚；判定有错后所有 rank **先把空载荷阶段跑完**再统一抛 `ValueError`（保留 `"rank r: ..."` 文本），且用户 value 在共识通过后才构造——先形成一致错误再退出，无残留请求。
- **结构化重分布**（[redistribution.py](file:///Users/huangding/Documents/new-SWE/09142/project-02/devito/data/distributed/redistribution.py)）：门控改为独立 gate channel 的 P2P 表决（key 只用跨 rank 一致的结构信息），push 用 `(目标,源,affine,source shape)` 独立通道。

## 验证

- 串行：`tests/test_data.py` 非并行 89 passed。
- 自写线程内仿真 MPI（严格 `(src,dst,tag)` 匹配）：基础 1D/2D、**2 线程×4 rank 并发 30 轮（同计划 get+put、不同 Data/dtype）**、单 rank 越界/重复的一致报错与失败后恢复、逐调用 tag 新鲜度、replicated 载荷、结构化重分布，全部通过。
- 真实 MPICH 5.0.1 + mpi4py（THREAD_MULTIPLE）：`TestDataDistributed` **43/43**（mode=4）；新增并发回归测试在 mode=4、mode=6 下多次稳定通过；`DEVITO_MPI=full` 同样验证；float32/float16（wire dtype 映射）get/put 正确。

新增测试：[test_advanced_indexing_concurrent_threads](file:///Users/huangding/Documents/new-SWE/09142/project-02/tests/test_data.py#L1044-L1106)。未提交 commit；验证用的 `.venv/` 是未跟踪目录，可随时删除。
