from __future__ import annotations

from io import StringIO
import os

from tpustat.core import (
    TPUStatCollection,
    _device_paths,
    _normalize_snapshot,
    _normalize_pcie_text,
    _scan_device_owners,
    format_device_line,
    format_header,
)


def _no_device_owners(devices, chip_type_name):
    del devices, chip_type_name
    return {}


def test_normalize_snapshot_attaches_processes(monkeypatch, raw_snapshot):
    monkeypatch.setattr("tpustat.core._scan_device_owners", _no_device_owners)
    snapshot = _normalize_snapshot(raw_snapshot, debug=False)

    assert snapshot.num_chips == 2
    assert len(snapshot.devices) == 2
    assert snapshot.devices[0].processes[0].pid == 1234
    assert snapshot.devices[1].processes == []


def test_format_device_line_default(monkeypatch, raw_snapshot):
    monkeypatch.setattr("tpustat.core._scan_device_owners", _no_device_owners)
    snapshot = _normalize_snapshot(raw_snapshot, debug=False)

    line = format_device_line(snapshot.devices[0], show_cmd=True, show_pid=True)

    assert "[0]" in line
    assert "TPU v6e" in line
    assert "42.5%" in line
    assert "512 / 32768 MiB" in line
    assert "python/1234(512M)" in line


def test_format_device_line_show_all(monkeypatch, raw_snapshot):
    monkeypatch.setattr("tpustat.core._scan_device_owners", _no_device_owners)
    snapshot = _normalize_snapshot(raw_snapshot, debug=False)

    line = format_device_line(snapshot.devices[0], show_all=True)

    assert "0000:00:04.0" in line
    assert "NUMA 0" in line
    assert "IOMMU 0" in line
    assert "PCIe n/a" in line


def test_collection_print_formatted(monkeypatch, raw_snapshot):
    monkeypatch.setattr("tpustat.core._scan_device_owners", _no_device_owners)
    snapshot = _normalize_snapshot(raw_snapshot, debug=False)
    stats = TPUStatCollection(snapshot)
    buf = StringIO()

    stats.print_formatted(buf, show_cmd=True, show_pid=True, force_color=False, no_color=True)
    output = buf.getvalue()

    assert "TPU v6e x2" in output
    assert "python/1234(512M)" in output
    assert "idle" in output


def test_format_header_contains_chip_summary(monkeypatch, raw_snapshot):
    monkeypatch.setattr("tpustat.core._scan_device_owners", _no_device_owners)
    snapshot = _normalize_snapshot(raw_snapshot, debug=False)

    header = format_header(snapshot)

    assert "[TPU v6e x2]" in header
    assert "vfio-pci" not in header


def test_format_device_line_respects_name_width(monkeypatch, raw_snapshot):
    monkeypatch.setattr("tpustat.core._scan_device_owners", _no_device_owners)
    snapshot = _normalize_snapshot(raw_snapshot, debug=False)

    line = format_device_line(snapshot.devices[0], tpuname_width=6)

    assert "TPU..." in line


def test_device_paths_include_vfio_and_iommu(monkeypatch, raw_snapshot):
    monkeypatch.setattr("tpustat.core._scan_device_owners", _no_device_owners)
    snapshot = _normalize_snapshot(raw_snapshot, debug=False)

    path_map = _device_paths(snapshot.devices, chip_type_name=snapshot.chip_type_name)

    assert path_map["/dev/vfio/0"] == 0
    assert path_map["/dev/vfio/1"] == 1


def test_scan_device_owners(monkeypatch, raw_snapshot):
    monkeypatch.setattr("tpustat.core._scan_device_owners", _no_device_owners)
    snapshot = _normalize_snapshot(raw_snapshot)

    monkeypatch.setattr("tpustat.core._iter_proc_fd_links", lambda: ["/proc/2000/fd/7", "/proc/2001/fd/8"])

    def fake_readlink(path: str) -> str:
        return {
            "/proc/2000/fd/7": "/dev/vfio/0",
            "/proc/2001/fd/8": "/dev/vfio/1",
        }[path]

    monkeypatch.setattr(os, "readlink", fake_readlink)

    owners = _scan_device_owners(snapshot.devices, chip_type_name=snapshot.chip_type_name)

    assert owners == {0: [2000], 1: [2001]}


def test_normalize_pcie_text_hides_invalid_placeholders():
    assert _normalize_pcie_text("Unknown", "x0") == ("", "")
    assert _normalize_pcie_text("", "x255") == ("", "")
    assert _normalize_pcie_text("Gen5", "x16") == ("Gen5", "x16")
