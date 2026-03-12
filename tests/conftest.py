from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def sample_raw_snapshot() -> dict:
    return {
        "tool_version": "0.1.0",
        "libtpu_version": "0.0.17",
        "chip_type_name": "v6e",
        "num_chips": 2,
        "driver_version": "vfio-pci",
        "devices": [
            {
                "device_id": 0,
                "chip_name": "TPU v6e",
                "bus_id": "0000:00:04.0",
                "numa_node": 0,
                "iommu_group": 0,
                "pcie_gen": "",
                "pcie_width": "x0",
                "power_draw_w": 10.0,
                "power_cap_w": 100.0,
                "hbm_used_mib": 512.0,
                "hbm_total_mib": 32768.0,
                "duty_cycle_pct": 42.5,
            },
            {
                "device_id": 1,
                "chip_name": "TPU v6e",
                "bus_id": "0000:00:05.0",
                "numa_node": 0,
                "iommu_group": 1,
                "pcie_gen": "",
                "pcie_width": "x0",
                "power_draw_w": 0.0,
                "power_cap_w": 0.0,
                "hbm_used_mib": 0.0,
                "hbm_total_mib": 32768.0,
                "duty_cycle_pct": 0.0,
            },
        ],
        "processes": [
            {
                "device_id": 0,
                "pid": 1234,
                "process_name": "python",
                "process_type": "C",
                "memory_usage_mib": 512,
            }
        ],
    }


@pytest.fixture
def raw_snapshot() -> dict:
    return sample_raw_snapshot()
