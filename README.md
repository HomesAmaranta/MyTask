# mytask

简单的本地顺序任务调度器。提交 shell 脚本到队列，后台 daemon 一个接一个执行，记录日志，可随时查看和终止。

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
```

## 行为

- **严格顺序**：同一时间只跑一个任务，前一个结束才启动下一个。
- **后台执行**：每个任务在独立进程组里运行，方便整组 kill。
- **自动 daemon**：提交时若 daemon 不在则自动拉起；空闲 5 分钟后自动退出，下次提交再重启。
- **崩溃恢复**：daemon 重启时会把上次残留的 `running` 任务标为 `failed` 或 `orphaned`。

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
