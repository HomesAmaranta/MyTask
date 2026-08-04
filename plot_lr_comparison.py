#!/usr/bin/env python3
"""Plot per-target EMA IC curves across different learning rates."""

import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

LOG_FILES = {
    0.0005: '/home/ybfeng/project/mytask/data/logs/2026-05-12/339.log',
    0.001:  '/home/ybfeng/project/mytask/data/logs/2026-05-12/336.log',
    0.002:  '/home/ybfeng/project/mytask/data/logs/2026-05-12/338.log',
    0.003:  '/home/ybfeng/project/mytask/data/logs/2026-05-13/340.log',
}

STEP_PATTERN = re.compile(r'step (\d+)/\d+')
TARGET_PATTERN = re.compile(
    r'\[ema per-target (ic|mse)\]\s+'
    r't0=([\-\d.eE+]+)\s*\|\s*t1=([\-\d.eE+]+)\s*\|\s*t2=([\-\d.eE+]+)\s*\|\s*t3=([\-\d.eE+]+)\s*\|\s*t4=([\-\d.eE+]+)'
)


def parse_log(path):
    steps_ic, steps_mse = [], []
    ics = {i: [] for i in range(5)}
    mses = {i: [] for i in range(5)}
    current_step = None
    with open(path) as f:
        for line in f:
            m = STEP_PATTERN.search(line)
            if m:
                current_step = int(m.group(1))
            m = TARGET_PATTERN.search(line)
            if m and current_step is not None:
                kind = m.group(1)
                vals = [float(m.group(i + 2)) for i in range(5)]
                if kind == 'ic':
                    steps_ic.append(current_step)
                    for i in range(5):
                        ics[i].append(vals[i])
                else:
                    steps_mse.append(current_step)
                    for i in range(5):
                        mses[i].append(vals[i])
    return steps_ic, ics, steps_mse, mses


# Parse all logs
data = {}
for lr, path in LOG_FILES.items():
    steps_ic, ics, steps_mse, mses = parse_log(path)
    data[lr] = (steps_ic, ics, steps_mse, mses)

colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']

# --- IC plot ---
fig, axes = plt.subplots(1, 5, figsize=(28, 5), sharey=False)
for t_idx in range(5):
    ax = axes[t_idx]
    for (lr, (steps_ic, ics, _, _)), color in zip(sorted(data.items()), colors):
        ax.plot(steps_ic, ics[t_idx], label=f'lr={lr}', color=color, linewidth=0.8, alpha=0.85)
    ax.set_title(f'Target {t_idx} (t{t_idx})', fontsize=13)
    ax.set_xlabel('Step')
    if t_idx == 0:
        ax.set_ylabel('EMA per-target IC')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
fig.suptitle('Learning Rate Comparison: EMA per-target IC vs Step', fontsize=15, y=1.02)
plt.tight_layout()
out_ic = '/home/ybfeng/project/mytask/lr_comparison_ic.png'
fig.savefig(out_ic, dpi=150, bbox_inches='tight')
print(f'Saved to {out_ic}')

# --- MSE plot ---
fig2, axes2 = plt.subplots(1, 5, figsize=(28, 5), sharey=False)
for t_idx in range(5):
    ax = axes2[t_idx]
    for (lr, (_, _, steps_mse, mses)), color in zip(sorted(data.items()), colors):
        ax.plot(steps_mse, mses[t_idx], label=f'lr={lr}', color=color, linewidth=0.8, alpha=0.85)
    ax.set_title(f'Target {t_idx} (t{t_idx})', fontsize=13)
    ax.set_xlabel('Step')
    if t_idx == 0:
        ax.set_ylabel('EMA per-target MSE')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.set_yscale('log')
    ax.set_ylim(top=5e-4)
fig2.suptitle('Learning Rate Comparison: EMA per-target MSE vs Step', fontsize=15, y=1.02)
plt.tight_layout()
out_mse = '/home/ybfeng/project/mytask/lr_comparison_mse.png'
fig2.savefig(out_mse, dpi=150, bbox_inches='tight')
print(f'Saved to {out_mse}')
