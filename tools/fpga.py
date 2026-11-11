#!/usr/bin/env python3
"""CLI for the Tang Nano 9K FPGA playground."""

from __future__ import annotations

import argparse
import dataclasses
import html
import os
import locale
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tomllib
from typing import Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
DESIGNS_DIR = ROOT / "designs"
BOARDS_DIR = ROOT / "boards"
BUILD_DIR = ROOT / "build"

DESIGN_KEYS = {"name", "board", "top", "sources", "constraints", "testbench"}
BOARD_KEYS = {
    "name",
    "device",
    "device_version",
    "clock_hz",
    "programmer_device",
    "programmer_idcode",
    "programmer_flash_operation",
    "programmer_cable",
    "programmer_cable_index",
    "use_sspi_as_gpio",
    "use_i2c_as_gpio",
    "use_cpu_as_gpio",
    "use_ready_as_gpio",
    "use_done_as_gpio",
}


class FpgaError(RuntimeError):
    """Expected user-facing CLI failure."""


@dataclasses.dataclass(frozen=True)
class Board:
    name: str
    device: str
    device_version: str
    clock_hz: int
    programmer_device: str
    programmer_idcode: str
    programmer_flash_operation: int | None
    programmer_cable: str
    programmer_cable_index: int
    use_sspi_as_gpio: bool
    use_i2c_as_gpio: bool
    use_cpu_as_gpio: bool
    use_ready_as_gpio: bool
    use_done_as_gpio: bool
    manifest: Path


@dataclasses.dataclass(frozen=True)
class Design:
    name: str
    board_name: str
    top: str
    sources: tuple[Path, ...]
    constraints: tuple[Path, ...]
    testbench: Path
    manifest: Path


@dataclasses.dataclass(frozen=True)
class ToolSpec:
    label: str
    env_var: str | None
    commands: tuple[str, ...]


TOOLS = {
    "gowin": ToolSpec("Gowin shell", "TANG_GOWIN_SH", ("gw_sh.exe", "gw_sh")),
    "programmer": ToolSpec(
        "Gowin Programmer",
        "TANG_GOWIN_PROGRAMMER",
        ("programmer_cli.exe", "programmer_cli"),
    ),
    "iverilog": ToolSpec("Icarus Verilog", "TANG_IVERILOG", ("iverilog.exe", "iverilog")),
    "vvp": ToolSpec("Icarus runtime", None, ("vvp.exe", "vvp")),
}


def _read_toml(path: Path) -> dict[str, object]:
    try:
        with path.open("rb") as stream:
            return tomllib.load(stream)
    except FileNotFoundError as exc:
        raise FpgaError(f"Configuration file not found: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise FpgaError(f"Invalid TOML in {path}: {exc}") from exc


def _required_string(data: Mapping[str, object], key: str, path: Path) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise FpgaError(f"{path}: '{key}' must be a non-empty string")
    return value


def _string_list(data: Mapping[str, object], key: str, path: Path) -> tuple[str, ...]:
    value = data.get(key)
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
        raise FpgaError(f"{path}: '{key}' must be a non-empty list of strings")
    return tuple(value)


def _reject_unknown(data: Mapping[str, object], allowed: set[str], path: Path) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise FpgaError(f"{path}: unknown key(s): {', '.join(unknown)}")


def _resolve_files(
    base: Path, entries: Iterable[str], manifest: Path, root: Path
) -> tuple[Path, ...]:
    resolved: list[Path] = []
    allowed_roots = (base.resolve(), (root / "common").resolve())
    for entry in entries:
        candidate = (base / entry).resolve()
        if not any(candidate.is_relative_to(allowed) for allowed in allowed_roots):
            raise FpgaError(
                f"{manifest}: path must stay in the design directory or common/: {entry}"
            )
        if not candidate.is_file():
            raise FpgaError(f"{manifest}: referenced file not found: {entry}")
        resolved.append(candidate)
    return tuple(resolved)


def load_board(name: str, root: Path = ROOT) -> Board:
    manifest = root / "boards" / name / "board.toml"
    data = _read_toml(manifest)
    _reject_unknown(data, BOARD_KEYS, manifest)
    clock_hz = data.get("clock_hz")
    if not isinstance(clock_hz, int) or isinstance(clock_hz, bool) or clock_hz <= 0:
        raise FpgaError(f"{manifest}: 'clock_hz' must be a positive integer")
    use_sspi_as_gpio = data.get("use_sspi_as_gpio")
    use_i2c_as_gpio = data.get("use_i2c_as_gpio")
    use_cpu_as_gpio = data.get("use_cpu_as_gpio")
    use_ready_as_gpio = data.get("use_ready_as_gpio")
    use_done_as_gpio = data.get("use_done_as_gpio")
    programmer_cable_index = data.get("programmer_cable_index")
    flash_operation = data.get("programmer_flash_operation")
    if flash_operation is not None and (
        type(flash_operation) is not int or flash_operation != 5
        or data.get("programmer_device") != "GW1NR-9C"
    ):
        raise FpgaError(
            f"{manifest}: only operation 5 (embedded Flash) on GW1NR-9C is supported"
        )
    if not all(
        isinstance(value, bool)
        for value in (
            use_sspi_as_gpio,
            use_i2c_as_gpio,
            use_cpu_as_gpio,
            use_ready_as_gpio,
            use_done_as_gpio,
        )
    ):
        raise FpgaError(
            f"{manifest}: dual-purpose GPIO settings must be booleans"
        )
    if not isinstance(programmer_cable_index, int) or isinstance(programmer_cable_index, bool):
        raise FpgaError(f"{manifest}: 'programmer_cable_index' must be an integer")
    board = Board(
        name=_required_string(data, "name", manifest),
        device=_required_string(data, "device", manifest),
        device_version=_required_string(data, "device_version", manifest),
        clock_hz=clock_hz,
        programmer_device=_required_string(data, "programmer_device", manifest),
        programmer_idcode=_required_string(data, "programmer_idcode", manifest),
        programmer_flash_operation=flash_operation,
        programmer_cable=_required_string(data, "programmer_cable", manifest),
        programmer_cable_index=programmer_cable_index,
        use_sspi_as_gpio=use_sspi_as_gpio,
        use_i2c_as_gpio=use_i2c_as_gpio,
        use_cpu_as_gpio=use_cpu_as_gpio,
        use_ready_as_gpio=use_ready_as_gpio,
        use_done_as_gpio=use_done_as_gpio,
        manifest=manifest,
    )
    if board.name != name:
        raise FpgaError(f"{manifest}: board name '{board.name}' does not match directory '{name}'")
    return board


def load_design(manifest: Path, root: Path = ROOT) -> Design:
    data = _read_toml(manifest)
    _reject_unknown(data, DESIGN_KEYS, manifest)
    base = manifest.parent.resolve()
    sources = _resolve_files(base, _string_list(data, "sources", manifest), manifest, root)
    constraints = _resolve_files(base, _string_list(data, "constraints", manifest), manifest, root)
    testbench_entry = _required_string(data, "testbench", manifest)
    testbench = _resolve_files(base, (testbench_entry,), manifest, root)[0]
    design = Design(
        name=_required_string(data, "name", manifest),
        board_name=_required_string(data, "board", manifest),
        top=_required_string(data, "top", manifest),
        sources=sources,
        constraints=constraints,
        testbench=testbench,
        manifest=manifest,
    )
    if design.name != manifest.parent.name:
        raise FpgaError(
            f"{manifest}: design name '{design.name}' does not match directory '{manifest.parent.name}'"
        )
    load_board(design.board_name, root)
    return design


def discover_designs(root: Path = ROOT) -> dict[str, Design]:
    manifests = sorted((root / "designs").glob("*/design.toml"))
    designs: dict[str, Design] = {}
    for manifest in manifests:
        design = load_design(manifest, root)
        if design.name in designs:
            raise FpgaError(f"Duplicate design name '{design.name}' in {manifest}")
        designs[design.name] = design
    return designs


def get_design(name: str, root: Path = ROOT) -> Design:
    designs = discover_designs(root)
    try:
        return designs[name]
    except KeyError as exc:
        choices = ", ".join(designs) if designs else "none"
        raise FpgaError(f"Unknown design '{name}'. Available designs: {choices}") from exc


def _existing_executable(value: str | os.PathLike[str]) -> Path | None:
    candidate = Path(value).expanduser()
    if candidate.is_file():
        return candidate.resolve()
    found = shutil.which(str(value))
    return Path(found).resolve() if found else None


def _gowin_roots() -> tuple[Path, ...]:
    return (
        Path("C:/Gowin"),
        Path("C:/Program Files/Gowin"),
        Path("C:/Program Files (x86)/Gowin"),
        Path("D:/Tools/Gowin"),
    )


def _gowin_fallbacks() -> Iterable[Path]:
    roots = _gowin_roots()
    for root in roots:
        if root.is_dir():
            candidates = root.glob("**/IDE/bin/gw_sh.exe")
            yield from sorted(
                candidates,
                key=lambda path: ("education" in str(path).lower(), str(path).lower()),
                reverse=True,
            )


def _programmer_fallbacks() -> Iterable[Path]:
    for root in _gowin_roots():
        if root.is_dir():
            yield from sorted(root.glob("**/Programmer/bin/programmer_cli.exe"), reverse=True)


def _iverilog_fallbacks(command: str) -> Iterable[Path]:
    for root in (Path("C:/Tools/iverilog"), Path("D:/Tools/iverilog")):
        yield root / "bin" / command


def resolve_tool(key: str, environ: Mapping[str, str] | None = None) -> Path | None:
    environ = os.environ if environ is None else environ
    spec = TOOLS[key]
    if spec.env_var and environ.get(spec.env_var):
        return _existing_executable(environ[spec.env_var])
    for command in spec.commands:
        resolved = _existing_executable(command)
        if resolved:
            return resolved
    if key == "gowin":
        return next((path.resolve() for path in _gowin_fallbacks() if path.is_file()), None)
    if key == "programmer":
        return next((path.resolve() for path in _programmer_fallbacks() if path.is_file()), None)
    if key == "iverilog":
        fallback = next(
            (path.resolve() for path in _iverilog_fallbacks("iverilog.exe") if path.is_file()),
            None,
        )
        if fallback:
            return fallback
    if key == "vvp":
        iverilog = resolve_tool("iverilog", environ)
        if iverilog:
            sibling = iverilog.with_name("vvp.exe" if os.name == "nt" else "vvp")
            if sibling.is_file():
                return sibling.resolve()
        return next(
            (path.resolve() for path in _iverilog_fallbacks("vvp.exe") if path.is_file()),
            None,
        )
    return None


def require_tool(key: str) -> Path:
    path = resolve_tool(key)
    if path:
        return path
    spec = TOOLS[key]
    hint = f" Set {spec.env_var} or add it to PATH." if spec.env_var else " Add it to PATH."
    raise FpgaError(f"{spec.label} was not found.{hint} Run '.\\fpga.ps1 doctor' for details.")


def tcl_quote(path: Path | str) -> str:
    text = str(path).replace("\\", "/").replace("}", "\\}")
    return "{" + text + "}"


def generate_gowin_tcl(design: Design, board: Board, output_dir: Path) -> str:
    project_dir = output_dir / "gowin_project"
    lines = [
        "# Generated by tools/fpga.py; do not edit.",
        (
            f"create_project -name {design.name} -dir {tcl_quote(project_dir)} "
            f"-pn {tcl_quote(board.device)} -device_version {tcl_quote(board.device_version)} "
            "-force"
        ),
    ]
    for source in design.sources:
        lines.append(f"import_files -file {tcl_quote(source)}")
    for constraint in design.constraints:
        lines.append(f"import_files -file {tcl_quote(constraint)}")
    lines.extend([
        f"set_option -top_module {tcl_quote(design.top)}",
        "set_option -verilog_std sysv2017",
    ])
    # New projects retain the device defaults for unused dual-purpose pins.
    # GW5A-specific options must not be emitted for this GW1NR device.
    for option in ("use_sspi_as_gpio", "use_i2c_as_gpio", "use_cpu_as_gpio",
                   "use_ready_as_gpio", "use_done_as_gpio"):
        if getattr(board, option):
            lines.append(f"set_option -{option} 1")
    lines.append("run all")
    return "\n".join(lines) + "\n"


def program_operation(board: Board, flash: bool) -> int:
    if not flash:
        return 2
    if board.programmer_flash_operation != 5 or board.programmer_device != "GW1NR-9C":
        raise FpgaError(f"Embedded Flash programming is not enabled for board '{board.name}'")
    return board.programmer_flash_operation


def program_command(
    executable: Path, board: Board, bitstream: Path, location: str, *, flash: bool = False
) -> list[str]:
    command = [
        str(executable),
        "--device",
        board.programmer_device,
        "--run",
        str(program_operation(board, flash)),
        "--fsFile",
        str(bitstream),
        "--cable-index",
        str(board.programmer_cable_index),
        "--location",
        location,
    ]
    if flash:
        command.extend(["--frequency", "2.5MHz"])
    return command


def _run(command: Sequence[str], cwd: Path, log: Path | None = None, timeout: int | None = None) -> int:
    try:
        result = _capture(command, timeout=timeout, cwd=cwd)
    except subprocess.TimeoutExpired as exc:
        if log:
            output = _decode_output(exc.stdout or b"") + _decode_output(exc.stderr or b"")
            log.parent.mkdir(parents=True, exist_ok=True)
            log.write_text(output + f"\nTIMEOUT after {timeout} seconds\n", encoding="utf-8")
        raise FpgaError(f"Command timed out after {timeout} seconds: {command[0]}") from exc
    output = (result.stdout or "") + (result.stderr or "")
    if log:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(output, encoding="utf-8", errors="replace")
    if output:
        print(output, end="" if output.endswith("\n") else "\n")
    return result.returncode


def command_list(_: argparse.Namespace) -> int:
    designs = discover_designs()
    if not designs:
        print("No designs found.")
        return 0
    for design in designs.values():
        print(f"{design.name}\tboard={design.board_name}\ttop={design.top}")
    return 0


def _version(path: Path, arguments: Sequence[str]) -> tuple[bool, str]:
    try:
        result = _capture([str(path), *arguments], timeout=10)
    except (FpgaError, subprocess.TimeoutExpired):
        return False, "version unavailable"
    output = ((result.stdout or "") + (result.stderr or "")).strip().splitlines()
    return result.returncode == 0, output[0] if output else "version unavailable"


def _programmer_version(path: Path) -> tuple[bool, str]:
    try:
        result = _capture([str(path), "--help"], timeout=10)
    except (FpgaError, subprocess.TimeoutExpired):
        return False, "version unavailable"
    output = (result.stdout or "") + (result.stderr or "")
    for line in output.splitlines():
        if "Version V" in line:
            return result.returncode == 0, line.strip()
    first_line = next((line.strip() for line in output.splitlines() if line.strip()), "version unavailable")
    return False, first_line


def _decode_output(data: bytes) -> str:
    # Gowin can mix English and Windows-localized errors. Never let decoding
    # hide the actual exit code or turn an environment error into a traceback.
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode(locale.getpreferredencoding(False), errors="replace")


def _capture(
    command: Sequence[str], timeout: int | None = None, cwd: Path = ROOT
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            list(command), cwd=cwd, stdin=subprocess.DEVNULL,
            capture_output=True, timeout=timeout, check=False,
        )
    except OSError as exc:
        raise FpgaError(f"Could not start {command[0]}: {exc}") from exc
    return subprocess.CompletedProcess(
        result.args, result.returncode,
        _decode_output(result.stdout or b""), _decode_output(result.stderr or b""),
    )


def _parse_programmer_locations(output: str, cable_name: str) -> list[str]:
    locations: set[str] = set()
    pattern = re.compile(
        r"Cable found:\s+(.+?)/\d+/\d+/.*?\(USB location:\s*(\d+)\)"
    )
    for match in pattern.finditer(output):
        if match.group(1).strip() == cable_name:
            locations.add(match.group(2))
    return sorted(locations, key=int)


def discover_programmer_location(programmer: Path, board: Board) -> tuple[str, str]:
    try:
        cables = _capture([str(programmer), "--scan-cables", "F"], timeout=10)
    except subprocess.TimeoutExpired as exc:
        raise FpgaError("Gowin Programmer timed out while listing USB cables") from exc
    cable_output = (cables.stdout or "") + (cables.stderr or "")
    if cables.returncode != 0:
        raise FpgaError(f"Gowin Programmer could not list USB cables: {cable_output.strip()}")
    locations = _parse_programmer_locations(cable_output, board.programmer_cable)
    if not locations:
        raise FpgaError(f"No '{board.programmer_cable}' cable was found")

    preferred = os.environ.get("TANG_PROGRAMMER_LOCATION")
    if preferred:
        if preferred not in locations:
            raise FpgaError(f"USB location {preferred} is not connected")
        locations = [preferred]
    matches: list[tuple[str, str]] = []
    diagnostics: list[str] = []
    for location in locations:
        scan_command = [
            str(programmer), "--scan", "--cable-index",
            str(board.programmer_cable_index), "--location", location,
        ]
        try:
            scan = _capture(scan_command, timeout=5)
        except subprocess.TimeoutExpired:
            diagnostics.append(f"{location}: scan timed out")
            continue
        scan_output = (scan.stdout or "") + (scan.stderr or "")
        device_count = re.search(r"(\d+) device\(s\) found!", scan_output)
        ids = re.findall(r"\bID:\s*(0x[0-9a-fA-F]+)", scan_output)
        if (scan.returncode == 0 and device_count and device_count.group(1) == "1"
                and len(ids) == 1 and ids[0].lower() == board.programmer_idcode.lower()
                and re.search(r"(?<![\w-])" + re.escape(board.programmer_device)
                              + r"(?![\w-])", scan_output)):
            matches.append((location, scan_output))
        else:
            diagnostics.append(f"{location}: unexpected target: {scan_output.strip()}")
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise FpgaError(
            "Multiple matching FPGA targets; set TANG_PROGRAMMER_LOCATION to one of: "
            + ", ".join(location for location, _ in matches)
        )
    raise FpgaError(
        f"No single {board.programmer_device} target with ID {board.programmer_idcode} "
        f"was found. " + "; ".join(diagnostics)
    )


def command_doctor(_: argparse.Namespace) -> int:
    board = load_board("tang_nano_9k")
    print(f"Python\tOK\t{sys.version.split()[0]}\t{Path(sys.executable).resolve()}")
    print(f"Board\tOK\t{board.device}\tclock={board.clock_hz} Hz")
    missing = False
    resolved: dict[str, Path] = {}
    version_args = {"gowin": ("-version",), "iverilog": ("-V",), "vvp": ("-V",)}
    for key in ("gowin", "programmer", "iverilog", "vvp"):
        path = resolve_tool(key)
        if path:
            usable, version = (
                _programmer_version(path) if key == "programmer" else _version(path, version_args[key])
            )
            status = "OK" if usable else "FAIL"
            print(f"{TOOLS[key].label}\t{status}\t{path}\t{version}")
            if usable:
                resolved[key] = path
            else:
                missing = True
        else:
            missing = True
            env_hint = f" ({TOOLS[key].env_var})" if TOOLS[key].env_var else ""
            print(f"{TOOLS[key].label}\tMISSING\tinstall it or configure PATH{env_hint}")

    programmer = resolved.get("programmer")
    if programmer:
        print(f"Hardware\tCHECK\tprobing {board.programmer_device} with Gowin Programmer...")
        try:
            location, scan_output = discover_programmer_location(programmer, board)
        except FpgaError as exc:
            print(f"Hardware\tFAIL\t{exc}")
            return 1
        print(f"Hardware\tOK\t{board.programmer_device} ID={board.programmer_idcode} at USB location {location}")
    else:
        print("Hardware\tSKIP\tGowin Programmer is unavailable")
    return 1 if missing else 0


def command_sim(args: argparse.Namespace) -> int:
    design = get_design(args.design)
    iverilog = require_tool("iverilog")
    vvp = require_tool("vvp")
    output_dir = BUILD_DIR / design.name / "sim"
    output_dir.mkdir(parents=True, exist_ok=True)
    executable = output_dir / "simulation.vvp"
    compile_command = [str(iverilog), "-g2012", "-o", str(executable)]
    compile_command.extend(str(path) for path in design.sources)
    compile_command.append(str(design.testbench))
    if _run(compile_command, ROOT, output_dir / "compile.log", timeout=30) != 0:
        raise FpgaError(f"Simulation compile failed; see {output_dir / 'compile.log'}")
    if _run([str(vvp), str(executable)], ROOT, output_dir / "run.log", timeout=30) != 0:
        raise FpgaError(f"Simulation failed; see {output_dir / 'run.log'}")
    return 0


def command_build(args: argparse.Namespace) -> int:
    design = get_design(args.design)
    board = load_board(design.board_name)
    gowin = require_tool("gowin")
    output_dir = BUILD_DIR / design.name
    output_dir.mkdir(parents=True, exist_ok=True)
    stable_bitstream = output_dir / f"{design.name}.fs"
    if stable_bitstream.exists():
        os.chmod(stable_bitstream, stat.S_IWRITE | stat.S_IREAD)
        stable_bitstream.unlink()
    generated_project = output_dir / "gowin_project"
    if not generated_project.resolve().is_relative_to(BUILD_DIR.resolve()):
        raise FpgaError(f"Generated project escapes build/: {generated_project}")
    if generated_project.exists():
        try:
            shutil.rmtree(generated_project, onerror=_remove_readonly)
        except OSError as exc:
            raise FpgaError(
                f"Failed to replace generated Gowin project under {generated_project}: {exc}"
            ) from exc
    script = output_dir / "build.tcl"
    script.write_text(generate_gowin_tcl(design, board, output_dir), encoding="utf-8")
    log = output_dir / "build.log"
    if _run([str(gowin), str(script)], output_dir, log, timeout=600) != 0:
        raise FpgaError(f"Gowin build failed; see {log}")

    reports = list(generated_project.rglob("*_tr_content.html"))
    if len(reports) != 1:
        raise FpgaError(f"Expected one Gowin timing report, found {len(reports)}; see {log}")
    validate_timing_report(reports[0])

    stable_bitstream = output_dir / f"{design.name}.fs"
    candidates = list(generated_project.rglob("*.fs"))
    if not candidates:
        raise FpgaError(f"Gowin completed but produced no .fs bitstream; see {log}")
    generated = max(candidates, key=lambda path: path.stat().st_mtime_ns)
    if stable_bitstream.exists():
        os.chmod(stable_bitstream, stat.S_IWRITE | stat.S_IREAD)
    try:
        shutil.copyfile(generated, stable_bitstream)
    except OSError as exc:
        raise FpgaError(f"Failed to normalize bitstream at {stable_bitstream}: {exc}") from exc
    print(f"BITSTREAM\t{stable_bitstream}")
    print(f"BUILD LOG\t{log}")
    return 0


def validate_timing_report(path: Path) -> dict[str, int]:
    """Do not publish a stable bitstream when PnR exits zero with timing failures."""
    content = html.unescape(re.sub(r"<[^>]+>", " ", path.read_text(encoding="utf-8")))
    counts: dict[str, int] = {}
    for kind in ("Setup", "Hold"):
        match = re.search(r"Numbers of " + kind + r" Violated Endpoints\s+(\d+)", content)
        if not match:
            raise FpgaError(f"Could not read {kind.lower()} violation count from {path}")
        counts[kind.lower()] = int(match.group(1))
    if any(counts.values()):
        raise FpgaError(f"Timing failed: setup={counts['setup']}, hold={counts['hold']}; see {path}")
    print("TIMING\tPASS\tsetup=0 hold=0")
    return counts


def command_program(args: argparse.Namespace) -> int:
    design = get_design(args.design)
    board = load_board(design.board_name)
    bitstream = BUILD_DIR / design.name / f"{design.name}.fs"
    if not bitstream.is_file():
        raise FpgaError(
            f"Bitstream not found: {bitstream}. Run '.\\fpga.ps1 build {design.name}' first."
        )
    operation = program_operation(board, args.flash)
    programmer = require_tool("programmer")
    location, scan_output = discover_programmer_location(programmer, board)
    print(scan_output.strip())
    mode = "EMBEDDED FLASH (erase and program)" if args.flash else "SRAM"
    print(f"PROGRAM MODE\t{mode} (Gowin Programmer operation {operation})")
    print(f"PROGRAM CABLE\t{board.programmer_cable} at USB location {location}")
    log = BUILD_DIR / design.name / ("program_flash.log" if args.flash else "program.log")
    command = program_command(programmer, board, bitstream, location, flash=args.flash)
    result = _run(command, ROOT, log, timeout=300 if args.flash else 120)
    output = log.read_text(encoding="utf-8")
    with log.open("a", encoding="utf-8") as stream:
        stream.write(f"\nCLI target: {board.programmer_device} ID={board.programmer_idcode} USB={location}\n")
        stream.write(f"CLI mode: {mode}; operation={operation}; exit_code={result}\n")
    # Some Programmer failures can return zero. Require its normal completion
    # line too; 'Finished, but wakes up failed' must not be reported as success.
    if (result != 0 or not re.search(r"^\s*Finished\.\s*$", output, re.MULTILINE)
            or re.search(r"\bfailed\b|\berror\s*:", output, re.IGNORECASE)):
        raise FpgaError(
            f"Programming failed; see {log}. Check the USB cable, on-board debugger firmware, and Windows driver."
        )
    print(f"PROGRAM RESULT\tPASS\t{mode}")
    print(f"PROGRAM LOG\t{log}")
    if args.flash:
        print("POWER-CYCLE CHECK\tpending user observation")
    return 0


def clean_outputs(build_dir: Path, design_name: str | None, clean_all: bool) -> list[Path]:
    build_root = build_dir.resolve()
    targets = [build_root] if clean_all else [build_root / str(design_name)]
    removed: list[Path] = []
    for target in targets:
        resolved = target.resolve()
        if not clean_all:
            try:
                resolved.relative_to(build_root)
            except ValueError as exc:
                raise FpgaError(f"Refusing to clean outside build directory: {resolved}") from exc
            if resolved == build_root:
                raise FpgaError("Refusing to remove the build root without --all")
        if resolved.exists():
            try:
                shutil.rmtree(resolved, onerror=_remove_readonly)
            except OSError as exc:
                raise FpgaError(f"Failed to clean generated files under {resolved}: {exc}") from exc
            removed.append(resolved)
    if clean_all:
        build_root.mkdir(parents=True, exist_ok=True)
        (build_root / ".gitkeep").write_bytes(b"\n")
    return removed


def _remove_readonly(function: object, path: str, _: object) -> None:
    os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
    function(path)  # type: ignore[operator]


def command_clean(args: argparse.Namespace) -> int:
    if args.all:
        if args.design:
            raise FpgaError("Specify either a design or --all, not both")
    elif not args.design:
        raise FpgaError("Specify a design or use --all")
    elif args.design not in discover_designs():
        raise FpgaError(f"Unknown design '{args.design}'")
    removed = clean_outputs(BUILD_DIR, args.design, args.all)
    if removed:
        for path in removed:
            print(f"REMOVED\t{path}")
    else:
        print("Nothing to clean.")
    return 0


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="list available designs")
    list_parser.set_defaults(handler=command_list)

    doctor_parser = subparsers.add_parser("doctor", help="diagnose tools and connected hardware")
    doctor_parser.set_defaults(handler=command_doctor)

    for name, help_text, handler in (
        ("sim", "simulate a design with Icarus Verilog", command_sim),
        ("build", "build a design with Gowin EDA", command_build),
    ):
        command_parser = subparsers.add_parser(name, help=help_text)
        command_parser.add_argument("design")
        command_parser.set_defaults(handler=handler)

    program_parser = subparsers.add_parser("program", help="program a generated bitstream")
    program_parser.add_argument("design")
    program_parser.add_argument(
        "--flash", action="store_true",
        help="erase and program the board's embedded Flash (persistent across power cycles)"
    )
    program_parser.set_defaults(handler=command_program)

    clean_parser = subparsers.add_parser("clean", help="remove generated build files")
    clean_parser.add_argument("design", nargs="?")
    clean_parser.add_argument("--all", action="store_true", help="remove all generated build files")
    clean_parser.set_defaults(handler=command_clean)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = make_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except FpgaError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("ERROR: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
