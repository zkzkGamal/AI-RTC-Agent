"""
conftest.py
────────────
Pretty animated pytest terminal output.
No dependencies beyond pytest — uses ANSI escape codes directly.
"""

import itertools
from pathlib import Path
import sys
import threading
import time
import pytest

MCP_ROOT = Path(__file__).resolve().parents[1]
if str(MCP_ROOT) not in sys.path:
    sys.path.insert(0, str(MCP_ROOT))

RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"

BLACK   = "\033[30m"
RED     = "\033[91m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
BLUE    = "\033[94m"
MAGENTA = "\033[95m"
CYAN    = "\033[96m"
WHITE   = "\033[97m"

BG_BLACK  = "\033[40m"
BG_RED    = "\033[41m"
BG_GREEN  = "\033[42m"

IS_TTY = sys.stdout.isatty()

_OUTCOMES   = {}  
_DURATIONS  = {}  
_START_TIME = None
_COUNTS     = {"passed": 0, "failed": 0, "skipped": 0, "error": 0}


def _c(text: str, *codes: str) -> str:
    """Wrap text in ANSI codes (no-op if not a TTY)."""
    if not IS_TTY:
        return text
    return "".join(codes) + text + RESET


def _label(item) -> str:
    doc = getattr(item.obj, "__doc__", None)
    if doc:
        return doc.strip().splitlines()[0].rstrip(".")
    return item.name.replace("_", " ")


def _module(item) -> str:
    parts = item.nodeid.split("::")
    return parts[0].replace("tests/", "").replace(".py", "") if parts else ""


def _bar(passed: int, failed: int, skipped: int, total: int, width: int = 30) -> str:
    """Render a colour-coded progress bar."""
    if total == 0:
        return ""
    p = int((passed  / total) * width)
    f = int((failed  / total) * width)
    s = int((skipped / total) * width)
    rest = width - p - f - s

    bar = (
        _c("█" * p,    GREEN)   +
        _c("█" * f,    RED)     +
        _c("█" * s,    YELLOW)  +
        _c("░" * rest, DIM)
    )
    return f"[{bar}]"


class _Spinner:
    FRAMES  = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    COLORS  = [CYAN, BLUE, MAGENTA, CYAN]

    def __init__(self, label: str, module: str):
        self.label    = label
        self.module   = module
        self._stop    = threading.Event()
        self._thread  = None
        self._t_start = time.monotonic()

    def _color_frame(self, frame: str, idx: int) -> str:
        return _c(frame, self.COLORS[idx % len(self.COLORS)], BOLD)

    def start(self):
        time.sleep(0.75)

        if not IS_TTY:
            mod = f"{_c(self.module, DIM)} " if self.module else ""
            print(f"  {_c('→', CYAN)} {mod}{self.label}", flush=True)
            return

        frames  = itertools.cycle(enumerate(self.FRAMES))
        mod_str = f"{_c(self.module + ' /', DIM, CYAN)} " if self.module else ""

        def _animate():
            while not self._stop.is_set():
                idx, frame = next(frames)
                elapsed = time.monotonic() - self._t_start
                timer   = _c(f" {elapsed:.1f}s", DIM)
                line    = f"  {self._color_frame(frame, idx)} {mod_str}{self.label}{timer}"
                sys.stdout.write(f"\r{line}  ")
                sys.stdout.flush()
                time.sleep(0.08)

        self._thread = threading.Thread(target=_animate, daemon=True)
        self._thread.start()

    def stop(self, outcome: str, duration: float):
        self._stop.set()
        if self._thread:
            self._thread.join()

        icons = {
            "passed":  ("✔", GREEN,  "PASS"),
            "failed":  ("✘", RED,    "FAIL"),
            "skipped": ("◌", YELLOW, "SKIP"),
            "error":   ("⚠", RED,    "ERR "),
        }
        icon, color, tag = icons.get(outcome, ("?", WHITE, "??? "))

        tag_str  = _c(f" {tag} ", color, BOLD, BG_BLACK)
        icon_str = _c(icon, color, BOLD)
        dur_str  = _c(f"{duration:.2f}s", DIM)
        mod_str  = f"{_c(self.module + ' /', DIM, CYAN)} " if self.module else ""

        if IS_TTY:
            clear = "\r" + " " * 72 + "\r"
            sys.stdout.write(clear)
            sys.stdout.write(f"  {icon_str} {tag_str} {mod_str}{self.label}  {dur_str}\n")
            sys.stdout.flush()
        else:
            print(f"  [{tag}] {self.label}  ({dur_str})", flush=True)


def _print_header(session):
    total  = session.testscollected
    border = _c("─" * 60, DIM)

    print()
    print(f"  {_c('⚡ AI-RTC-Agent', CYAN, BOLD)}  {_c('test suite', DIM)}")
    print(f"  {border}")
    print(f"  {_c(f'{total} tests collected', DIM)}")
    print(f"  {border}")
    print()


def _print_footer():
    total    = sum(_COUNTS.values())
    elapsed  = time.monotonic() - _START_TIME if _START_TIME else 0
    border   = _c("─" * 60, DIM)

    p = _COUNTS["passed"]
    f = _COUNTS["failed"]
    s = _COUNTS["skipped"]
    e = _COUNTS["error"]

    bar = _bar(p, f, s, total)

    passed_str  = _c(f"{p} passed",  GREEN,  BOLD) if p else _c(f"{p} passed",  DIM)
    failed_str  = _c(f"{f} failed",  RED,    BOLD) if f else _c(f"{f} failed",  DIM)
    skipped_str = _c(f"{s} skipped", YELLOW, BOLD) if s else _c(f"{s} skipped", DIM)
    time_str    = _c(f"{elapsed:.2f}s", DIM)

    overall     = _c(" PASSED ", GREEN, BOLD, BG_BLACK) if f == 0 and e == 0 \
                  else _c(" FAILED ", RED,   BOLD, BG_BLACK)

    print()
    print(f"  {border}")
    print(f"  {bar}  {passed_str}  {failed_str}  {skipped_str}  {_c('in', DIM)} {time_str}")
    print(f"  {overall}")
    print()


def pytest_configure(config):
    config.option.capture = "no"


def pytest_sessionstart(session):
    global _START_TIME
    _START_TIME = time.monotonic()


def pytest_collection_finish(session):
    _print_header(session)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    spinner = _Spinner(_label(item), _module(item))
    t_start = time.monotonic()
    spinner.start()

    yield

    duration = time.monotonic() - t_start
    outcome  = _OUTCOMES.get(item.nodeid, "failed")
    _COUNTS[outcome] = _COUNTS.get(outcome, 0) + 1
    spinner.stop(outcome, duration)

    return True


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report  = outcome.get_result()
    if report.when == "call":
        _OUTCOMES[item.nodeid] = report.outcome


def pytest_sessionfinish(session, exitstatus):
    _print_footer()


def pytest_report_teststatus(report, config):
    if report.when != "call":
        return "", "", ""
    return report.outcome, "", ""
