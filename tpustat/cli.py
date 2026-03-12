from __future__ import annotations

import argparse
import signal
import sys
import time
from io import StringIO

try:
    import shtab
except ImportError:
    from tpustat import _shtab as shtab

from tpustat import __version__
from tpustat.core import (
    TPUStatCollection,
    clear_screen,
    clear_to_end,
    hide_cursor,
    show_cursor,
)


def print_tpustat(*, json: bool = False, **kwargs: object) -> None:
    stream = kwargs.pop("stream", sys.stdout)
    color_stream = kwargs.pop("color_stream", stream)
    debug = bool(kwargs.pop("debug", False))
    stats = TPUStatCollection.new_query(id=kwargs.pop("id", None), debug=debug)
    if json:
        stats.print_json(stream)
    else:
        stats.print_formatted(stream, color_stream=color_stream, **kwargs)


def _render_frame(**kwargs: object) -> str:
    buf = StringIO()
    print_tpustat(stream=buf, color_stream=sys.stdout, **kwargs)
    return buf.getvalue()


def _write_tty_frame(stream: object, frame: str, previous_line_count: int) -> int:
    lines = frame.splitlines()
    stream.write("\033[H")
    for line in lines:
        stream.write("\033[2K")
        stream.write(line)
        stream.write("\n")
    for _ in range(max(0, previous_line_count - len(lines))):
        stream.write("\033[2K\n")
    clear_to_end(stream)
    return len(lines)


def loop_tpustat(interval: float, **kwargs: object) -> int:
    is_tty = bool(getattr(sys.stdout, "isatty", lambda: False)())
    previous_line_count = 0
    try:
        if is_tty:
            clear_screen(sys.stdout)
            hide_cursor(sys.stdout)
        while True:
            if is_tty:
                frame = _render_frame(**kwargs)
                previous_line_count = _write_tty_frame(sys.stdout, frame, previous_line_count)
            else:
                print_tpustat(**kwargs)
            sys.stdout.flush()
            time.sleep(interval)
    except KeyboardInterrupt:
        return 0
    finally:
        if is_tty:
            show_cursor(sys.stdout)
            sys.stdout.flush()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser("tpustat")
    shtab.add_argument_to(parser)
    parser_color = parser.add_mutually_exclusive_group()
    parser_color.add_argument("--force-color", "--color", action="store_true", help="Force colored output")
    parser_color.add_argument("--no-color", action="store_true", help="Disable colored output")
    parser.add_argument("--id", help="Target a specific TPU index or comma-separated indices")
    parser.add_argument("-a", "--show-all", action="store_true", help="Show bus, NUMA, and IOMMU details")
    parser.add_argument("-c", "--show-cmd", action="store_true", help="Display process command names")
    parser.add_argument("-u", "--show-user", action="store_true", help="Display process owners")
    parser.add_argument("-p", "--show-pid", action="store_true", help="Display process IDs")
    parser.add_argument("--tpuname-width", type=nonnegative_int, default=16, help="Width used for TPU names")
    parser.add_argument("--json", action="store_true", help="Print snapshot data as JSON")
    parser.add_argument("-i", "--interval", "--watch", nargs="?", type=float, default=0, help="Refresh continuously")
    parser.add_argument("--no-header", dest="show_header", action="store_false", default=True, help="Suppress the header")
    parser.add_argument("--no-processes", action="store_true", help="Do not display process information")
    parser.add_argument("--debug", action="store_true", help="Show full errors when TPU data collection fails")
    parser.add_argument("-v", "--version", action="version", version=f"tpustat {__version__}")
    return parser


def nonnegative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("Only non-negative integers are allowed.")
    return parsed


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    try:
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except Exception:
        pass

    parser = build_parser()
    args = parser.parse_args(argv)
    if hasattr(args, "print_completion"):
        delattr(args, "print_completion")
    if args.show_all:
        args.show_cmd = True
        args.show_user = True
        args.show_pid = True

    if args.interval is None:
        args.interval = 1.0
    if args.interval and args.interval > 0:
        if args.json:
            parser.error("--json and --interval/-i cannot be used together")
        interval = max(0.1, args.interval)
        kwargs = vars(args)
        kwargs.pop("interval", None)
        return loop_tpustat(interval=interval, **kwargs)

    kwargs = vars(args)
    kwargs.pop("interval", None)
    try:
        print_tpustat(**kwargs)
    except Exception as exc:
        sys.stderr.write("Error while querying TPU devices. Use --debug for details.\n")
        sys.stderr.write(f"{exc}\n")
        if args.debug:
            raise
        return 1
    return 0
