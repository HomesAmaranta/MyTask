---
name: "mytask-worker-gpu"
description: "Guide for using MyTask with MLX workers and GPUs. Invoke when assigning tasks to workers, checking GPUs, or debugging worker dispatch."
---

# MyTask Worker GPU Skill

这个文档记录 `mytask` 如何连接 MLX worker、发现 GPU、查询 GPU 上的任务，以及如何排查任务没有分配到预期 worker/GPU 的问题。

## 适用场景

- 需要把 `mytask` 任务自动派发到 worker GPU。
- 需要查看当前有哪些 worker 和 GPU。
- 需要查看每张 GPU 上正在跑哪些 `mytask` 任务。
- 需要判断任务为什么没有跑满所有 GPU。
- 需要手动登录某个 worker 验证 GPU 环境。

## 核心概念

- `master` 通常不一定有 GPU，worker 内才可能有 GPU。
- `mytask gpus` 显示的是平台当前能看到的 worker GPU。
- `mytask workers` 显示的是 `mytask` 实际用于调度的 worker 池。
- 只有出现在 `mytask workers` 调度池里的 worker，才会被 `mytask` 自动派发任务。
- 调度最小单位是 GPU，不是 worker。槽位格式是 `worker_id:gpu_index`。
- 多种 GPU 同时空闲时，调度优先级是 H100 优先，其他 GPU 其次，A100 最后。
- 所有任务默认按单卡任务处理，派发时会注入 `CUDA_VISIBLE_DEVICES=<gpu_index>`。

## 常用命令

查看平台当前 worker 和 GPU，快速模式：

```bash
/mlx_devbox/users/fengyuebo/playground/MyTask/mytask gpus
```

输出示例：

```text
WORKER        GPU
1061703       index=0 type=H100-SXM-80GB
1061707       index=0 type=H100-SXM-80GB
1064182       index=0 type=H100-SXM-80GB
1064182       index=1 type=H100-SXM-80GB
1064182       index=2 type=H100-SXM-80GB
1064182       index=3 type=H100-SXM-80GB
```

查看每张 GPU 上当前 running 的 `mytask` 任务号：

```bash
/mlx_devbox/users/fengyuebo/playground/MyTask/mytask gpu-tasks
```

输出示例：

```text
WORKER        GPU         GPU_TYPE          RUNNING_TASKS
1061707       0           H100-SXM-80GB     75
1061703       0           H100-SXM-80GB     76
1064182       0           H100-SXM-80GB     -
```

查看当前 `mytask` 调度池：

```bash
/mlx_devbox/users/fengyuebo/playground/MyTask/mytask workers
```

标记你确认可用、但深度探测失败的 worker：

```bash
/mlx_devbox/users/fengyuebo/playground/MyTask/mytask trust-workers 1064182
```

取消所有 trusted worker：

```bash
/mlx_devbox/users/fengyuebo/playground/MyTask/mytask trust-workers off
```

查看每张 GPU 的并行任务数：

```bash
/mlx_devbox/users/fengyuebo/playground/MyTask/mytask parallel
```

查看空闲 GPU 判定阈值：

```bash
/mlx_devbox/users/fengyuebo/playground/MyTask/mytask gpu-policy
```

## 快速模式和深度模式

`mytask gpus` 默认是快速模式。

快速模式只调用：

```bash
/opt/tiger/mlx_deploy/mlxc worker list
```

快速模式不会：

- 进入 worker。
- 执行 `torch.cuda` 深度探测。
- 查询 GPU 空闲显存。
- 判断 GPU 是否真的可调度。

快速模式适合快速查看当前平台有哪些 worker/GPU。

深度模式：

```bash
/mlx_devbox/users/fengyuebo/playground/MyTask/mytask gpus --detail
```

深度模式会对 worker 执行：

```bash
/opt/tiger/mlx_deploy/mlxc worker login <worker_id> -- python -c '<probe code>'
```

worker 内部会执行：

```python
import torch
torch.cuda.is_available()
torch.cuda.device_count()
torch.cuda.mem_get_info(gpu_index)
torch.cuda.get_device_properties(gpu_index)
```

深度模式可以显示：

- GPU index
- GPU 型号
- 显存空闲比例
- 探测来源 `source=torch`

深度模式较慢，因为它需要逐个 worker login。

## 自动发现 Worker

开启自动发现：

```bash
/mlx_devbox/users/fengyuebo/playground/MyTask/mytask workers auto
```

开启后：

- 配置会写入 `MyTask/data/config.json`。
- 后续 daemon 每轮调度会调用 `mlxc worker list`。
- 新出现的 worker 会自动加入候选调度池。
- 已关闭且不再出现在 `worker list` 的 worker 不会继续接收新任务。

查看是否已开启自动发现：

```bash
/mlx_devbox/users/fengyuebo/playground/MyTask/mytask workers
```

自动发现模式会显示：

```text
worker_dispatch: on
worker_source: auto
workers: ...
```

## 手动指定 Worker

如果只想使用指定 worker：

```bash
/mlx_devbox/users/fengyuebo/playground/MyTask/mytask workers 1061703 1061707
```

如果只想使用 H100 worker，可以指定：

```bash
/mlx_devbox/users/fengyuebo/playground/MyTask/mytask workers 1061703 1061707 1064182
```

如果 A100 也可以使用，可以开启：

```bash
/mlx_devbox/users/fengyuebo/playground/MyTask/mytask workers auto
```

注意：`auto` 会包含 `mlxc worker list` 返回的所有 worker，包括 A100。

## 并行度规则

查看并行度：

```bash
/mlx_devbox/users/fengyuebo/playground/MyTask/mytask parallel
```

设置每张 GPU 的并行任务数：

```bash
/mlx_devbox/users/fengyuebo/playground/MyTask/mytask parallel 1
```

worker 派发模式下，`parallel` 表示每张 GPU 的并行任务数。

例子：

- `parallel=1`
- `1061703` 有 1 张 GPU
- `1061707` 有 1 张 GPU
- `1064182` 有 4 张 GPU

则最多同时 running：

```text
1 + 1 + 4 = 6 个任务
```

## 空闲 GPU 判定

查看当前策略：

```bash
/mlx_devbox/users/fengyuebo/playground/MyTask/mytask gpu-policy
```

默认策略：

```text
gpu_policy: util<30 free>70%
```

含义：

- 当前 torch-only 探测拿不到 GPU 利用率，所以调度主要使用空闲显存比例。
- GPU 空闲显存比例必须大于 `70%`。
- `util<30` 保留在配置展示里，但 torch 探测下利用率显示为 `unknown`。

设置策略：

```bash
/mlx_devbox/users/fengyuebo/playground/MyTask/mytask gpu-policy 30 70
```

调度时会通过 `torch.cuda` 深度探测 GPU，只有满足空闲显存策略的 GPU 才会接收新任务。多个候选 GPU 同时可用时，优先派到 H100，A100 最后使用。

如果某些 worker 你已经确认可以执行训练，但 `mlxc worker login ... torch.cuda` 探测失败，可以用 `trust-workers` 标记。被标记的 worker 会在探测失败时根据 `worker list` 的 GPU 数量和型号生成候选卡，并参与调度。这个模式不会真实读取显存空闲，只适合你明确知道这些卡可用的场景。

## 提交任务

进入项目目录后提交：

```bash
cd /mlx_devbox/users/fengyuebo/playground/TIGER/gr
/mlx_devbox/users/fengyuebo/playground/MyTask/mytask retrain_causal_tiger.sh -m "causal tiger Beauty"
```

查看队列：

```bash
/mlx_devbox/users/fengyuebo/playground/MyTask/mytask show -w
```

查看 GPU 上的任务：

```bash
/mlx_devbox/users/fengyuebo/playground/MyTask/mytask gpu-tasks
```

查看某个任务日志：

```bash
/mlx_devbox/users/fengyuebo/playground/MyTask/mytask log <task_id>
```

查看某个任务详情：

```bash
/mlx_devbox/users/fengyuebo/playground/MyTask/mytask info <task_id>
```

## 手动登录 Worker

推荐使用 `mlxc worker login`，不要直接裸 `ssh`。

登录并执行命令：

```bash
/opt/tiger/mlx_deploy/mlxc worker login 1061707 -- /usr/bin/python - <<'PY'
import torch
print(torch.cuda.is_available(), torch.cuda.device_count())
for i in range(torch.cuda.device_count()):
    free_b, total_b = torch.cuda.mem_get_info(i)
    print(i, torch.cuda.get_device_name(i), round(free_b * 100 / total_b, 2))
PY
```

在指定 worker 上手动执行命令：

```bash
/opt/tiger/mlx_deploy/mlxc worker login 1061707 -- bash -lc '
cd /mlx_devbox/users/fengyuebo/playground/TIGER/gr
bash test_retrain_causal_tiger_decoder_only.sh
'
```

## status=probe_unavailable

如果看到：

```text
1061703       index=0 type=H100-SXM-80GB status=probe_unavailable
```

含义是：

- `mlxc worker list` 能看到这个 worker 和 GPU。
- 但深度探测失败了。
- 也就是 `mlxc worker login <id> -- python -c ... torch.cuda` 没成功。

这不一定代表 GPU 坏了，可能是：

- worker 正在启动或关闭。
- `mlxc worker login` 临时失败。
- worker 内 `/usr/bin/python` 无法导入 torch 或 torch 看不到 CUDA。
- CUDA runtime 环境没加载好。
- worker 能被平台列出，但当前不能实际执行命令。

调度器不会把任务派发到深度探测失败的 GPU。

## 为什么只跑了两个任务

如果 `mytask gpus` 显示很多 GPU，但 `mytask` 只跑了两个任务，先检查：

```bash
/mlx_devbox/users/fengyuebo/playground/MyTask/mytask workers
```

如果输出类似：

```text
worker_dispatch: on
worker_source: configured
workers: 1061707 1061703
```

说明调度池只有两个 worker。

即使 `mytask gpus` 能看到更多 worker/GPU，调度器也只会使用 `mytask workers` 里配置的 worker。

解决方式：

```bash
/mlx_devbox/users/fengyuebo/playground/MyTask/mytask workers auto
```

或手动指定更多 worker：

```bash
/mlx_devbox/users/fengyuebo/playground/MyTask/mytask workers 1061703 1061707 1064182
```

## 排查清单

查看所有 GPU：

```bash
/mlx_devbox/users/fengyuebo/playground/MyTask/mytask gpus
```

查看调度池：

```bash
/mlx_devbox/users/fengyuebo/playground/MyTask/mytask workers
```

查看 running 任务分布：

```bash
/mlx_devbox/users/fengyuebo/playground/MyTask/mytask gpu-tasks
```

查看 pending/running 队列：

```bash
/mlx_devbox/users/fengyuebo/playground/MyTask/mytask show -w
```

查看 GPU 空闲阈值：

```bash
/mlx_devbox/users/fengyuebo/playground/MyTask/mytask gpu-policy
```

深度探测某个 worker：

```bash
/mlx_devbox/users/fengyuebo/playground/MyTask/mytask gpus --detail 1061707
```

手动测试 worker：

```bash
/opt/tiger/mlx_deploy/mlxc worker login 1061707 -- /usr/bin/python - <<'PY'
import socket
import torch
print(socket.gethostname())
print(torch.cuda.is_available(), torch.cuda.device_count())
for i in range(torch.cuda.device_count()):
    free_b, total_b = torch.cuda.mem_get_info(i)
    print(i, torch.cuda.get_device_name(i), round(free_b * 100 / total_b, 2))
PY
```
