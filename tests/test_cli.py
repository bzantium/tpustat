from __future__ import annotations

import json

import pytest

from tpustat import cli
from tpustat.core import TPUStatCollection, _normalize_snapshot


@pytest.fixture
def stats(monkeypatch, raw_snapshot):
    monkeypatch.setattr("tpustat.core._scan_device_owners", lambda devices, chip_type_name: {})
    return TPUStatCollection(_normalize_snapshot(raw_snapshot))


def test_cli_json_output(monkeypatch, capsys, stats):
    monkeypatch.setattr(cli.TPUStatCollection, "new_query", classmethod(lambda cls, id=None, debug=False: stats))

    exit_code = cli.main(["--json"])
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["chip_type_name"] == "v6e"
    assert payload["devices"][0]["index"] == 0


def test_cli_text_output(monkeypatch, capsys, stats):
    monkeypatch.setattr(cli.TPUStatCollection, "new_query", classmethod(lambda cls, id=None, debug=False: stats))

    exit_code = cli.main(["-c", "-p", "--no-color"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "python/1234(512M)" in captured.out


def test_cli_show_all_expands_flags(monkeypatch, capsys, stats):
    monkeypatch.setattr(cli.TPUStatCollection, "new_query", classmethod(lambda cls, id=None, debug=False: stats))

    exit_code = cli.main(["--show-all", "--no-color"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "0000:00:04.0" in captured.out
    assert "/1234" in captured.out


def test_cli_reports_query_errors(monkeypatch, capsys):
    def blow_up(cls, id=None, debug=False):
        raise RuntimeError("collector exploded")

    monkeypatch.setattr(cli.TPUStatCollection, "new_query", classmethod(blow_up))

    exit_code = cli.main(["--no-color"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "collector exploded" in captured.err


def test_cli_rejects_json_watch(monkeypatch):
    monkeypatch.setattr(
        cli.TPUStatCollection,
        "new_query",
        classmethod(lambda cls, id=None, debug=False: TPUStatCollection(_normalize_snapshot({
            "tool_version": "0.1.0",
            "libtpu_version": "0.0.17",
            "chip_type_name": "v6e",
            "num_chips": 0,
            "driver_version": "vfio-pci",
            "devices": [],
            "processes": [],
        }))),
    )

    with pytest.raises(SystemExit):
        cli.main(["--json", "-i", "1"])


def test_parser_has_completion_flag(capsys):
    parser = cli.build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--print-completion", "bash"])
    captured = capsys.readouterr()

    assert exc.value.code == 0
    assert "tpustat" in captured.out
    assert "complete " in captured.out or "#compdef tpustat" in captured.out
