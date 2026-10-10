# mytask

简单任务调度器。提交 shell 脚本到队列，后台 daemon 按并发数执行，记录日志，可随时查看和终止；在 MLX Workspace 中可按 GPU 空闲状态自动派发到 worker。

## 安装

把脚本软链到 PATH 里任意目录，例如：

```bash
ln -s /Path/to/MyTask/mytask ~/miniconda3/envs/test_npm/bin/mytask
```

无第三方依赖，只要有 Python 3 即可。

## 使用

| 命令 | 说明 |
| --- | --- |
| `mytask <script.sh> [args...]` | 提交任务，首次提交会自动拉起后台 daemon |
| `mytask show` | 列出所有任务和 daemon 状态 |
| `mytask log <id>` | 打印某任务的完整日志 |
| `mytask kill <id>` | pending 任务直接取消；running 任务给整个进程组发 SIGTERM |
| `mytask parallel [N]` | 查看或设置并发数；本地模式为总并发，worker 模式为每张 GPU 的并发 |
| `mytask workers [off\|auto\|ID...]` | 查看、关闭、自动发现或指定 GPU worker 派发 |
| `mytask trust-workers [off\|ID...]` | 标记可信 worker；深度探测失败时仍允许按 `worker list` 派发 |
| `mytask gpus [--detail] [ID...]` | 查询当前 worker GPU；默认快速模式只读 `worker list`，`--detail` 用 `torch.cuda` 查显存 |
| `mytask gpu-tasks [ID...]` | 查询每张 GPU 的型号和当前 running 的任务号 |
| `mytask gpu-policy [UTIL FREE]` | 查看或设置空闲 GPU 阈值，默认 `util<30 free>70%` |
| `mytask clear` | 清掉已完成的任务记录（日志文件保留） |
| `mytask stop-daemon` | 停掉后台 daemon |

示例：

```bash
mytask train.sh
mytask eval.sh --ckpt last
mytask show
mytask log 2
mytask kill 3
mytask kill 3-11
mytask workers 1061707 1061703
mytask trust-workers 1064182
mytask gpus
mytask gpus --detail
mytask gpu-tasks
mytask gpu-policy 30 70
```

## 行为

- **并发控制**：`mytask parallel N` 控制 queued 任务并发数，默认 1；本地模式下表示总并发，worker 派发模式下表示每张 worker GPU 的并发数。
- **后台执行**：每个任务在独立进程组里运行，方便整组 kill。
- **自动 daemon**：提交时若 daemon 不在则自动拉起；空闲 5 分钟后自动退出，下次提交再重启。
- **崩溃恢复**：daemon 重启时会把上次残留的 `running` 任务标为 `failed` 或 `orphaned`。
- **Worker 派发**：开启 `mytask workers ...` 后，daemon 会通过 `mlx worker login <id> -- ...` 和 `torch.cuda` 探测每个 worker 内的每张 GPU；当前按空闲显存比例高于 `FREE` 判定可用，空闲候选中优先选择 H100，A100 最后选择，并通过 `CUDA_VISIBLE_DEVICES=<gpu_index>` 绑定单卡；没有空闲卡时任务保持 `pending`。`trust-workers` 标记的 worker 在探测失败时也会按 `worker list` 参与调度。

## 数据目录

所有状态都在脚本同目录的 `data/` 下：

```
mytask/
├── mytask              # 主脚本
└── data/
    ├── tasks.json      # 任务队列与状态
    ├── tasks.lock      # 队列读写锁
    ├── daemon.pid      # daemon 进程号
    ├── daemon.lock     # daemon 单例锁
    ├── daemon.log      # daemon 自身日志
    └── logs/
        └── <id>.log    # 每个任务的输出日志
```

## 任务日志格式

每个任务的日志包含元信息和合并后的 stdout/stderr：

```
=== task 1 ===
cmd: bash /tmp/train.sh
cwd: /home/me/proj
submitted: 2026-04-29T10:30:52
started:   2026-04-29T10:30:52
=== output ===
... 脚本输出 ...

=== finished: 2026-04-29T10:30:54 exit=0 ===
```

## 任务状态

| 状态 | 含义 |
| --- | --- |
| `pending` | 排队中，等待执行 |
| `running` | 正在执行 |
| `done` | 正常结束（exit=0） |
| `failed` | 非零退出或被 kill |
| `cancelled` | 在 pending 阶段被取消 |
| `orphaned` | daemon 重启时发现上次残留的进程仍在 |
