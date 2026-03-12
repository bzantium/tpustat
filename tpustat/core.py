from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from io import StringIO
from typing import Any, Iterable, Sequence

import psutil


def _fmt_int(value: float | int | None, fallback: str = "??") -> str:
    if value is None:
        return fallback
    return str(int(value))


def _fmt_pct(value: float | int | None, fallback: str = "??") -> str:
    if value is None:
        return fallback
    return f"{float(value):.1f}%"


def _shorten(text: str, width: int) -> str:
    if width <= 0:
        return ""
    if len(text) <= width:
        return text.ljust(width)
    if width <= 3:
        return text[:width]
    return (text[: width - 3] + "...").ljust(width)


@dataclass
class TPUProcess:
    device_id: int
    pid: int | None
    process_name: str
    process_type: str = "C"
    memory_usage_mib: int = 0
    username: str | None = None
    command: str | None = None

    def display(
        self,
        *,
        show_user: bool,
        show_cmd: bool,
        show_pid: bool,
    ) -> str:
        parts: list[str] = []
        if show_user and self.username:
            parts.append(self.username)
        if show_cmd:
            parts.append(self.command or self.process_name or "?")
        base = ":".join(parts)
        if not base:
            base = self.process_name or "pid"
        if show_pid and self.pid is not None:
            base = f"{base}/{self.pid}"
        return f"{base}({self.memory_usage_mib}M)"


@dataclass
class TPUDevice:
    index: int
    name: str
    bus_id: str
    numa_node: int
    iommu_group: int
    power_draw_w: float
    power_cap_w: float
    hbm_used_mib: float
    hbm_total_mib: float
    duty_cycle_pct: float
    processes: list[TPUProcess] = field(default_factory=list)

    def print_to(
        self,
        fp: StringIO | Any,
        *,
        show_cmd: bool = False,
        show_user: bool = False,
        show_pid: bool = False,
        no_processes: bool = False,
        show_all: bool = False,
        tpuname_width: int = 16,
        color: bool = False,
        eol_char: str = os.linesep,
    ) -> Any:
        line = format_device_line(
            self,
            show_cmd=show_cmd,
            show_user=show_user,
            show_pid=show_pid,
            no_processes=no_processes,
            show_all=show_all,
            tpuname_width=tpuname_width,
            color=color,
        )
        fp.write(line)
        fp.write(eol_char)
        return fp


@dataclass
class TPUSnapshot:
    hostname: str
    query_time: datetime
    tool_version: str
    libtpu_version: str
    chip_type_name: str
    num_chips: int
    driver_version: str
    devices: list[TPUDevice]
    processes: list[TPUProcess]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["query_time"] = self.query_time.isoformat()
        return payload


class Ansi:
    RESET = "\033[0m"
    CYAN = "\033[36m"
    BLUE = "\033[34m"
    GREEN = "\033[32m"
    BOLD_GREEN = "\033[1;32m"
    YELLOW = "\033[33m"
    BOLD_YELLOW = "\033[1;33m"
    MAGENTA = "\033[35m"
    GRAY = "\033[90m"
    BOLD = "\033[1m"


def _paint(text: str, code: str, enabled: bool) -> str:
    if not enabled:
        return text
    return f"{code}{text}{Ansi.RESET}"


def _processes_for_display(
    device: TPUDevice,
    *,
    show_cmd: bool,
    show_user: bool,
    show_pid: bool,
) -> str:
    if not device.processes:
        return "idle"
    return " ".join(
        process.display(show_cmd=show_cmd, show_user=show_user, show_pid=show_pid)
        for process in device.processes
    )


def format_device_line(
    device: TPUDevice,
    *,
    show_cmd: bool = False,
    show_user: bool = False,
    show_pid: bool = False,
    no_processes: bool = False,
    show_all: bool = False,
    tpuname_width: int = 16,
    color: bool = False,
) -> str:
    left = _paint(f"[{device.index}]", Ansi.CYAN, color)
    name = _paint(_shorten(device.name, tpuname_width), Ansi.BLUE, color)
    util = _paint(f"{_fmt_pct(device.duty_cycle_pct):>6}", Ansi.BOLD_GREEN, color)
    mem_used = _paint(f"{_fmt_int(device.hbm_used_mib):>5}", Ansi.BOLD_YELLOW, color)
    mem_total = _paint(f"{_fmt_int(device.hbm_total_mib):>5}", Ansi.YELLOW, color)

    sections = [f"{left} {name} | {util} | {mem_used} / {mem_total} MiB"]
    if show_all:
        sections.append(f"{device.bus_id} | NUMA {device.numa_node} | IOMMU {device.iommu_group}")
    if not no_processes:
        proc_text = _processes_for_display(
            device,
            show_cmd=show_cmd,
            show_user=show_user,
            show_pid=show_pid,
        )
        sections.append(_paint(proc_text, Ansi.GRAY, color))
    return " | ".join(sections)


class TPUStatCollection(Sequence[TPUDevice]):
    def __init__(self, snapshot: TPUSnapshot):
        self.snapshot = snapshot
        self.devices = snapshot.devices

    def __getitem__(self, index: int) -> TPUDevice:
        return self.devices[index]

    def __len__(self) -> int:
        return len(self.devices)

    @classmethod
    def new_query(cls, id: str | None = None, debug: bool = False) -> "TPUStatCollection":
        snapshot = query_snapshot(debug=debug)
        if id:
            wanted = {int(part.strip()) for part in id.split(",") if part.strip()}
            snapshot.devices = [device for device in snapshot.devices if device.index in wanted]
            snapshot.processes = [proc for proc in snapshot.processes if proc.device_id in wanted]
        return cls(snapshot)

    def print_json(self, fp: Any) -> None:
        json.dump(self.snapshot.to_dict(), fp, indent=2)
        fp.write(os.linesep)

    def print_formatted(
        self,
        fp: Any,
        *,
        show_cmd: bool = False,
        show_user: bool = False,
        show_pid: bool = False,
        no_processes: bool = False,
        show_all: bool = False,
        show_header: bool = True,
        force_color: bool = False,
        no_color: bool = False,
        tpuname_width: int = 16,
        eol_char: str = os.linesep,
    ) -> None:
        color = should_use_color(force_color=force_color, no_color=no_color, stream=fp)
        if show_header:
            fp.write(format_header(self.snapshot, color=color))
            fp.write(eol_char)
        if not self.devices:
            fp.write("No TPUs detected.")
            fp.write(eol_char)
            return
        for device in self.devices:
            device.print_to(
                fp,
                show_cmd=show_cmd,
                show_user=show_user,
                show_pid=show_pid,
                no_processes=no_processes,
                show_all=show_all,
                tpuname_width=tpuname_width,
                color=color,
                eol_char=eol_char,
            )


def should_use_color(*, force_color: bool, no_color: bool, stream: Any) -> bool:
    if no_color:
        return False
    if force_color:
        return True
    if os.environ.get("NO_COLOR"):
        return False
    return bool(getattr(stream, "isatty", lambda: False)())


def format_header(snapshot: TPUSnapshot, *, color: bool = False) -> str:
    ts = snapshot.query_time.astimezone().strftime("%a %b %d %H:%M:%S %Y")
    host = _paint(snapshot.hostname, Ansi.BOLD, color)
    chip = _paint(f"[TPU {snapshot.chip_type_name} x{snapshot.num_chips}]", Ansi.CYAN, color)
    return f"{host}  {ts}  {chip}"


def query_snapshot(*, debug: bool = False) -> TPUSnapshot:
    raw = _collect_snapshot_raw()
    return _normalize_snapshot(raw, debug=debug)


def _collect_snapshot_raw() -> dict[str, Any]:
    raw = _collect_from_google_smi_api()
    if raw is not None:
        return raw
    raw = _collect_from_google_smi_cli()
    if raw is not None:
        return raw
    raise RuntimeError("Unable to collect TPU data from google_smi or google-smi.")


def _collect_from_google_smi_api() -> dict[str, Any] | None:
    try:
        from google_smi.collector import collect_snapshot
    except Exception:
        return None
    try:
        snapshot = collect_snapshot()
    except Exception:
        return None
    return asdict(snapshot)


def _collect_from_google_smi_cli() -> dict[str, Any] | None:
    if shutil.which("google-smi") is None:
        return None
    completed = subprocess.run(
        ["google-smi", "--json"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "google-smi failed")
    return json.loads(completed.stdout)


def _normalize_snapshot(raw: dict[str, Any], *, debug: bool = False) -> TPUSnapshot:
    devices = []
    for entry in raw.get("devices", []):
        index = int(entry.get("device_id", 0))
        devices.append(
            TPUDevice(
                index=index,
                name=str(entry.get("chip_name", "TPU")),
                bus_id=str(entry.get("bus_id", "unknown")),
                numa_node=int(entry.get("numa_node", 0)),
                iommu_group=int(entry.get("iommu_group", 0)),
                power_draw_w=float(entry.get("power_draw_w", 0.0) or 0.0),
                power_cap_w=float(entry.get("power_cap_w", 0.0) or 0.0),
                hbm_used_mib=float(entry.get("hbm_used_mib", 0.0) or 0.0),
                hbm_total_mib=float(entry.get("hbm_total_mib", 0.0) or 0.0),
                duty_cycle_pct=float(entry.get("duty_cycle_pct", 0.0) or 0.0),
            )
        )

    process_map = _build_process_map(raw, devices, debug=debug)
    processes = [proc for device_processes in process_map.values() for proc in device_processes]
    for device in devices:
        device.processes = sorted(
            process_map.get(device.index, []),
            key=lambda proc: (
                proc.pid is None,
                proc.pid or 0,
                proc.process_name,
            ),
        )

    return TPUSnapshot(
        hostname=platform.node(),
        query_time=datetime.now(timezone.utc),
        tool_version=str(raw.get("tool_version", "unknown")),
        libtpu_version=str(raw.get("libtpu_version", "unknown")),
        chip_type_name=str(raw.get("chip_type_name", "unknown")),
        num_chips=int(raw.get("num_chips", len(devices))),
        driver_version=str(raw.get("driver_version", "unknown")),
        devices=devices,
        processes=processes,
    )


def _normalize_process(raw: dict[str, Any]) -> TPUProcess:
    pid = raw.get("pid")
    process = TPUProcess(
        device_id=int(raw.get("device_id", 0)),
        pid=int(pid) if pid is not None else None,
        process_name=str(raw.get("process_name", "?")),
        process_type=str(raw.get("process_type", "C")),
        memory_usage_mib=int(raw.get("memory_usage_mib", 0) or 0),
    )
    if process.pid is not None:
        _enrich_process(process)
    if not process.command:
        process.command = process.process_name
    return process


def _build_process_map(
    raw: dict[str, Any],
    devices: list[TPUDevice],
    *,
    debug: bool = False,
) -> dict[int, list[TPUProcess]]:
    process_map: dict[int, list[TPUProcess]] = {}
    seen: set[tuple[int, int | None, str]] = set()

    for entry in raw.get("processes", []):
        process = _normalize_process(entry)
        key = (process.device_id, process.pid, process.process_name)
        if key not in seen:
            process_map.setdefault(process.device_id, []).append(process)
            seen.add(key)

    try:
        owner_map = _scan_device_owners(devices, chip_type_name=str(raw.get("chip_type_name", "")))
    except Exception:
        if debug:
            raise
        owner_map = {}

    for device in devices:
        for pid in owner_map.get(device.index, []):
            process = TPUProcess(
                device_id=device.index,
                pid=pid,
                process_name="pid",
                memory_usage_mib=int(device.hbm_used_mib),
            )
            _enrich_process(process)
            if not process.command:
                process.command = process.process_name
            key = (process.device_id, process.pid, process.command or process.process_name)
            if key in seen:
                continue
            process_map.setdefault(process.device_id, []).append(process)
            seen.add(key)

    return process_map


def _scan_device_owners(devices: list[TPUDevice], *, chip_type_name: str) -> dict[int, list[int]]:
    path_to_index = _device_paths(devices, chip_type_name=chip_type_name)
    owners: dict[int, set[int]] = {device.index: set() for device in devices}
    pattern = re.compile(r"^/proc/(\d+)/fd/\d+$")
    for link in _iter_proc_fd_links():
        try:
            target = os.readlink(link)
        except FileNotFoundError:
            continue
        device_index = path_to_index.get(target)
        if device_index is None:
            continue
        match = pattern.fullmatch(link)
        if match:
            owners[device_index].add(int(match.group(1)))
    return {index: sorted(pids) for index, pids in owners.items() if pids}


def _iter_proc_fd_links() -> Iterable[str]:
    for proc_name in os.listdir("/proc"):
        if not proc_name.isdigit():
            continue
        fd_dir = os.path.join("/proc", proc_name, "fd")
        try:
            for fd_name in os.listdir(fd_dir):
                yield os.path.join(fd_dir, fd_name)
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue


def _device_paths(devices: list[TPUDevice], *, chip_type_name: str) -> dict[str, int]:
    path_to_index: dict[str, int] = {}
    uses_vfio = chip_type_name.lower() in {"v5e", "v5p", "v6e", "v7x"}
    for device in devices:
        if uses_vfio:
            path_to_index[f"/dev/vfio/{device.index}"] = device.index
            path_to_index[f"/dev/vfio/{device.iommu_group}"] = device.index
        else:
            path_to_index[f"/dev/accel{device.index}"] = device.index
    return path_to_index


def _enrich_process(process: TPUProcess) -> None:
    try:
        ps_process = psutil.Process(process.pid)
        process.username = ps_process.username()
        cmdline = ps_process.cmdline()
        if cmdline:
            process.command = os.path.basename(cmdline[0])
    except (psutil.Error, FileNotFoundError, PermissionError):
        return


def clear_screen(stream: Any) -> None:
    stream.write("\033[H\033[J")
    stream.flush()


def move_cursor_home(stream: Any) -> None:
    stream.write("\033[H")


def clear_to_end(stream: Any) -> None:
    stream.write("\033[J")


def hide_cursor(stream: Any) -> None:
    stream.write("\033[?25l")


def show_cursor(stream: Any) -> None:
    stream.write("\033[?25h")
