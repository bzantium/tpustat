# tpustat

`tpustat` is a small TPU status CLI in the same spirit as `gpustat`:

- `nvidia-smi` -> `gpustat`
- `google-smi` -> `tpustat`

It prefers the local `google_smi` Python package when present, then falls back to `google-smi --json`.

## Usage

```bash
tpustat
tpustat --show-all
tpustat --show-cmd --show-user --show-pid
tpustat --tpuname-width 12
tpustat --json
tpustat -i 1
tpustat --print-completion bash
```

## Notes

- `--show-all` expands the process fields in addition to bus-level device details.
- Process ownership is merged from `google-smi` output and direct `/proc/*/fd` device-owner scanning.
- If `google_smi` cannot be imported, `tpustat` falls back to `google-smi --json`.

## Installation

```bash
pip install -e .
tpustat --help
```

## Shell Completion

```bash
tpustat --print-completion bash
tpustat --print-completion zsh
```
