# tpustat

`tpustat` is the TPU equivalent of the `gpustat` workflow:

- `nvidia-smi` -> `gpustat`
- `google-smi` -> `tpustat`

It turns the verbose TPU table into a compact one-line-per-device view, while still supporting JSON output, watch mode, and richer process details when needed. By default it uses the local `google_smi` Python package and falls back to `google-smi --json`.

```text
t1v-n-a839d305-w-0  Thu Mar 12 01:58:21 2026  [TPU v6e x8]
[0] TPU v6e          |   0.0% |   406 / 31995 MiB | python(406M)
```

## Install

```bash
# install from GitHub
pip install git+https://github.com/bzantium/tpustat.git

# or install locally for development
pip install -e .
```

## Quick Start

```bash
# compact default view
tpustat

# include bus / NUMA / IOMMU / PCIe details
tpustat --show-all

# show explicit process fields
tpustat -c -u -p

# machine-readable output
tpustat --json

# refresh continuously
tpustat -i
tpustat -i 0.5

# generate shell completion
tpustat --print-completion bash
tpustat --print-completion zsh
```

## What’s Different From `google-smi`

- One-line `gpustat`-style layout instead of a full boxed table
- Per-process display optimized for quick scanning
- Direct `/proc/*/fd` process-owner scanning to enrich TPU process attribution
- Optional fallback to `google-smi --json` when the Python collector is unavailable

## Notes

- `--show-all` expands device and process detail for each TPU line.
- `--tpuname-width` controls TPU name truncation in the compact view.
- `--no-processes` suppresses process information entirely.
- Color output follows TTY detection unless overridden with `--force-color` or `--no-color`.
