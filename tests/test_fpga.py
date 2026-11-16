from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
import subprocess
import argparse
import contextlib
import dataclasses
import io


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "fpga.py"
SPEC = importlib.util.spec_from_file_location("fpga_cli", MODULE_PATH)
assert SPEC and SPEC.loader
fpga = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = fpga
SPEC.loader.exec_module(fpga)


class FpgaCliTests(unittest.TestCase):
    def make_project(self, root: Path, *, extra_design_key: str = "") -> None:
        board_dir = root / "boards" / "test_board"
        design_dir = root / "designs" / "001_test"
        (design_dir / "rtl").mkdir(parents=True)
        (design_dir / "constraints").mkdir()
        (design_dir / "sim").mkdir()
        board_dir.mkdir(parents=True)
        (board_dir / "board.toml").write_text(
            'name = "test_board"\ndevice = "TEST-PART"\ndevice_version = "A"\n'
            'clock_hz = 100\nprogrammer_device = "TEST-DEVICE"\nprogrammer_idcode = "0x12345678"\n'
            'programmer_cable = "USB Debugger A"\nprogrammer_cable_index = 4\n'
            'use_sspi_as_gpio = false\nuse_i2c_as_gpio = false\nuse_cpu_as_gpio = false\n'
            'use_ready_as_gpio = false\nuse_done_as_gpio = false\n',
            encoding="utf-8",
        )
        (design_dir / "rtl" / "top.sv").write_text("module top; endmodule\n", encoding="utf-8")
        (design_dir / "constraints" / "top.cst").write_text("// test\n", encoding="utf-8")
        (design_dir / "sim" / "tb.sv").write_text("module tb; endmodule\n", encoding="utf-8")
        (design_dir / "design.toml").write_text(
            'name = "001_test"\nboard = "test_board"\ntop = "top"\n'
            'sources = ["rtl/top.sv"]\nconstraints = ["constraints/top.cst"]\n'
            f'testbench = "sim/tb.sv"\n{extra_design_key}',
            encoding="utf-8",
        )

    def test_repository_manifest_loads(self) -> None:
        designs = fpga.discover_designs(MODULE_PATH.parents[1])
        self.assertEqual(
            set(designs),
            {"001_blink", "002_dual_pll", "003_analog2pdm", "004_pdm_tone", "005_analog2pdm_1v8", "006_analog2pdm_select"},
        )
        self.assertEqual(designs["001_blink"].top, "top")

    def test_timing_report_accepts_zero_violations(self) -> None:
        with tempfile.TemporaryDirectory(dir=MODULE_PATH.parents[1] / "build") as directory:
            path = Path(directory) / "timing.html"
            path.write_text("<td>Numbers of Setup Violated Endpoints</td><td>0</td>"
                            "<td>Numbers of Hold Violated Endpoints</td><td>0</td>", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(fpga.validate_timing_report(path), {"setup": 0, "hold": 0})

    def test_timing_report_rejects_violations_even_if_tool_succeeded(self) -> None:
        with tempfile.TemporaryDirectory(dir=MODULE_PATH.parents[1] / "build") as directory:
            path = Path(directory) / "timing.html"
            path.write_text("Numbers of Setup Violated Endpoints 0\nNumbers of Hold Violated Endpoints 6", encoding="utf-8")
            with self.assertRaisesRegex(fpga.FpgaError, "Timing failed"):
                fpga.validate_timing_report(path)

    def test_unrecognized_timing_report_is_not_treated_as_success(self) -> None:
        with tempfile.TemporaryDirectory(dir=MODULE_PATH.parents[1] / "build") as directory:
            path = Path(directory) / "timing.html"
            path.write_text("Timing report is unavailable", encoding="utf-8")
            with self.assertRaisesRegex(fpga.FpgaError, "Could not read"):
                fpga.validate_timing_report(path)

    def test_unknown_manifest_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=MODULE_PATH.parents[1] / "build") as directory:
            root = Path(directory)
            self.make_project(root, extra_design_key='unexpected = true\n')
            with self.assertRaisesRegex(fpga.FpgaError, "unknown key"):
                fpga.discover_designs(root)

    def test_missing_referenced_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=MODULE_PATH.parents[1] / "build") as directory:
            root = Path(directory)
            self.make_project(root)
            (root / "designs" / "001_test" / "rtl" / "top.sv").unlink()
            with self.assertRaisesRegex(fpga.FpgaError, "referenced file not found"):
                fpga.discover_designs(root)

    def test_common_source_is_allowed_but_other_escape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=MODULE_PATH.parents[1] / "build") as directory:
            root = Path(directory)
            self.make_project(root)
            common = root / "common" / "rtl"
            common.mkdir(parents=True)
            (common / "shared.sv").write_text("module shared; endmodule\n", encoding="utf-8")
            manifest = root / "designs" / "001_test" / "design.toml"
            text = manifest.read_text(encoding="utf-8")
            manifest.write_text(
                text.replace(
                    'sources = ["rtl/top.sv"]',
                    'sources = ["rtl/top.sv", "../../common/rtl/shared.sv"]',
                ),
                encoding="utf-8",
            )
            design = fpga.discover_designs(root)["001_test"]
            self.assertIn((common / "shared.sv").resolve(), design.sources)

            outside = root / "outside.sv"
            outside.write_text("module outside; endmodule\n", encoding="utf-8")
            manifest.write_text(
                manifest.read_text(encoding="utf-8").replace(
                    '"../../common/rtl/shared.sv"', '"../../outside.sv"'
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(fpga.FpgaError, "design directory or common"):
                fpga.discover_designs(root)

    def test_environment_tool_override_has_priority(self) -> None:
        with tempfile.TemporaryDirectory(dir=MODULE_PATH.parents[1] / "build") as directory:
            executable = Path(directory) / "custom-gw_sh.exe"
            executable.touch()
            resolved = fpga.resolve_tool("gowin", {"TANG_GOWIN_SH": str(executable), "PATH": ""})
            self.assertEqual(resolved, executable.resolve())

    def test_tcl_quote_normalizes_windows_paths(self) -> None:
        self.assertEqual(fpga.tcl_quote(r"C:\Program Files\Gowin\file.sv"), "{C:/Program Files/Gowin/file.sv}")

    def test_generated_tcl_contains_sources_and_device(self) -> None:
        design = fpga.get_design("001_blink")
        board = fpga.load_board(design.board_name)
        text = fpga.generate_gowin_tcl(design, board, Path("C:/build folder"))
        self.assertIn(board.device, text)
        self.assertIn("-device_version {C}", text)
        self.assertIn("-force", text)
        self.assertNotIn("set_option -use_sspi_as_gpio", text)
        self.assertNotIn("set_option -use_i2c_as_gpio", text)
        self.assertNotIn("set_option -use_cpu_as_gpio", text)
        self.assertNotIn("set_option -use_ready_as_gpio", text)
        self.assertNotIn("set_option -use_done_as_gpio", text)
        self.assertIn("import_files -file", text)
        self.assertIn("run all", text)
        self.assertIn("{C:/build folder/gowin_project}", text)

    def test_program_command_uses_gowin_sram_mode(self) -> None:
        board = fpga.load_board("tang_nano_9k")
        command = fpga.program_command(
            Path("programmer_cli.exe"), board, Path("blink.fs"), "201745"
        )
        self.assertEqual(
            command,
            [
                "programmer_cli.exe",
                "--device",
                "GW1NR-9C",
                "--run",
                "2",
                "--fsFile",
                "blink.fs",
                "--cable-index",
                "4",
                "--location",
                "201745",
            ],
        )

    def test_flash_command_targets_embedded_flash_at_2_5_mhz(self) -> None:
        board = fpga.load_board("tang_nano_9k")
        command = fpga.program_command(
            Path("programmer_cli.exe"), board, Path("blink.fs"), "201745", flash=True
        )
        self.assertEqual(command, [
            "programmer_cli.exe", "--device", "GW1NR-9C", "--run", "5",
            "--fsFile", "blink.fs", "--cable-index", "4", "--location", "201745",
            "--frequency", "2.5MHz",
        ])

    def test_board_without_flash_opt_in_is_rejected(self) -> None:
        board = dataclasses.replace(fpga.load_board("tang_nano_9k"), programmer_flash_operation=None)
        with self.assertRaisesRegex(fpga.FpgaError, "not enabled"):
            fpga.program_command(Path("programmer"), board, Path("blink.fs"), "1", flash=True)

    def test_flash_manifest_rejects_external_operations_and_wrong_device(self) -> None:
        for device, operation in (("GW1NR-9C", "8"), ("GW5A-25A", "5"), ("GW1NR-9C", "true")):
            with self.subTest(device=device, operation=operation), tempfile.TemporaryDirectory(dir=MODULE_PATH.parents[1] / "build") as directory:
                root = Path(directory)
                self.make_project(root)
                path = root / "boards/test_board/board.toml"
                text = path.read_text(encoding="utf-8").replace("TEST-DEVICE", device)
                path.write_text(text + f"programmer_flash_operation = {operation}\n", encoding="utf-8")
                with self.assertRaisesRegex(fpga.FpgaError, "only operation 5"):
                    fpga.load_board("test_board", root)

    def test_parser_defaults_to_sram_and_requires_explicit_flash_flag(self) -> None:
        self.assertFalse(fpga.make_parser().parse_args(["program", "001_blink"]).flash)
        self.assertTrue(fpga.make_parser().parse_args(["program", "001_blink", "--flash"]).flash)

    def test_flash_program_keeps_sram_log_and_checks_programmer_completion(self) -> None:
        cases = ((0, "Finished.\n", True), (1, "Finished.\n", False),
                 (0, "Finished, but wakes up failed\n", False),
                 (0, "Error: write failed\nFinished.\n", False),
                 (0, "Programming... 100%\n", False))
        for code, output, success in cases:
            with self.subTest(code=code, output=output), tempfile.TemporaryDirectory(dir=MODULE_PATH.parents[1] / "build") as directory:
                build = Path(directory)
                design_dir = build / "001_blink"
                design_dir.mkdir()
                (design_dir / "001_blink.fs").write_bytes(b"test bitstream")
                sram_log = design_dir / "program.log"
                sram_log.write_text("previous SRAM result", encoding="utf-8")
                result = subprocess.CompletedProcess([], code, output, "")
                with patch.object(fpga, "BUILD_DIR", build), patch.object(fpga, "require_tool", return_value=Path("programmer")), patch.object(fpga, "discover_programmer_location", return_value=("1", "ID: 0x1100481B")), patch.object(fpga, "_capture", return_value=result) as capture, contextlib.redirect_stdout(io.StringIO()):
                    args = argparse.Namespace(design="001_blink", flash=True)
                    if success:
                        self.assertEqual(fpga.command_program(args), 0)
                    else:
                        with self.assertRaisesRegex(fpga.FpgaError, "Programming failed"):
                            fpga.command_program(args)
                self.assertEqual(sram_log.read_text(encoding="utf-8"), "previous SRAM result")
                self.assertIn(f"exit_code={code}", (design_dir / "program_flash.log").read_text(encoding="utf-8"))
                self.assertEqual(capture.call_args.kwargs["timeout"], 300)

    def test_flash_program_does_not_start_without_bitstream(self) -> None:
        with tempfile.TemporaryDirectory(dir=MODULE_PATH.parents[1] / "build") as directory, patch.object(fpga, "BUILD_DIR", Path(directory)), patch.object(fpga, "require_tool") as require:
            with self.assertRaisesRegex(fpga.FpgaError, "Bitstream not found"):
                fpga.command_program(argparse.Namespace(design="001_blink", flash=True))
            require.assert_not_called()

    def test_programmer_timeout_retains_partial_log(self) -> None:
        with tempfile.TemporaryDirectory(dir=MODULE_PATH.parents[1] / "build") as directory:
            log = Path(directory) / "program_flash.log"
            timeout = subprocess.TimeoutExpired("programmer", 300, output=b"Erasing Flash...", stderr=b"")
            with patch.object(fpga, "_capture", side_effect=timeout):
                with self.assertRaisesRegex(fpga.FpgaError, "timed out"):
                    fpga._run(["programmer"], fpga.ROOT, log, timeout=300)
            self.assertIn("Erasing Flash...", log.read_text(encoding="utf-8"))
            self.assertIn("TIMEOUT", log.read_text(encoding="utf-8"))

    def test_programmer_locations_are_filtered_and_sorted(self) -> None:
        output = (
            " Cable found:  USB Debugger A/0/201746/null (USB location:201746)\n"
            " Cable found:  Other Cable/0/10/null (USB location:10)\n"
            " Cable found:  USB Debugger A/1/0/null (USB location:201745)\n"
        )
        self.assertEqual(
            fpga._parse_programmer_locations(output, "USB Debugger A"),
            ["201745", "201746"],
        )

    @staticmethod
    def scan_output(idcode="0x1100481B", count=1):
        return subprocess.CompletedProcess([], 0,
            f"Name: GW1N-9C GW1NR-9C (One of them)\nID: {idcode}\n{count} device(s) found!", "")

    def test_discovery_skips_wrong_device_and_timeout(self) -> None:
        cables = subprocess.CompletedProcess([], 0,
            "Cable found: USB Debugger A/0/1/null (USB location:1)\n"
            "Cable found: USB Debugger A/1/2/null (USB location:2)\n"
            "Cable found: USB Debugger A/2/3/null (USB location:3)", "")
        replies = [cables, self.scan_output("0xDEADBEEF"),
                   subprocess.TimeoutExpired("programmer", 5), self.scan_output()]
        with patch.dict(os.environ, {}, clear=True), patch.object(fpga, "_capture", side_effect=replies):
            location, _ = fpga.discover_programmer_location(Path("programmer"), fpga.load_board("tang_nano_9k"))
        self.assertEqual(location, "3")

    def test_discovery_rejects_multiple_matching_targets(self) -> None:
        cables = subprocess.CompletedProcess([], 0,
            "Cable found: USB Debugger A/0/1/null (USB location:1)\n"
            "Cable found: USB Debugger A/1/2/null (USB location:2)", "")
        with patch.dict(os.environ, {}, clear=True), patch.object(fpga, "_capture", side_effect=[cables, self.scan_output(), self.scan_output()]):
            with self.assertRaisesRegex(fpga.FpgaError, "Multiple matching"):
                fpga.discover_programmer_location(Path("programmer"), fpga.load_board("tang_nano_9k"))

    def test_discovery_rejects_multi_device_chain(self) -> None:
        cables = subprocess.CompletedProcess([], 0,
            "Cable found: USB Debugger A/0/1/null (USB location:1)", "")
        with patch.dict(os.environ, {}, clear=True), patch.object(fpga, "_capture", side_effect=[cables, self.scan_output(count=2)]):
            with self.assertRaisesRegex(fpga.FpgaError, "No single"):
                fpga.discover_programmer_location(Path("programmer"), fpga.load_board("tang_nano_9k"))

    def test_location_override_still_checks_idcode(self) -> None:
        cables = subprocess.CompletedProcess([], 0,
            "Cable found: USB Debugger A/0/1/null (USB location:1)", "")
        with patch.dict(os.environ, {"TANG_PROGRAMMER_LOCATION": "1"}, clear=True), patch.object(fpga, "_capture", side_effect=[cables, self.scan_output("0xDEADBEEF")]):
            with self.assertRaisesRegex(fpga.FpgaError, "No single"):
                fpga.discover_programmer_location(Path("programmer"), fpga.load_board("tang_nano_9k"))

    def test_localized_tool_error_preserves_exit_status(self) -> None:
        message = "アクセスが拒否されました。"
        result = subprocess.CompletedProcess([], 1, b"", message.encode("cp932"))
        with patch.object(fpga.subprocess, "run", return_value=result), patch.object(fpga.locale, "getpreferredencoding", return_value="cp932"):
            captured = fpga._capture(["programmer"])
        self.assertEqual(captured.returncode, 1)
        self.assertEqual(captured.stderr, message)

    def test_targeted_clean_preserves_other_designs(self) -> None:
        with tempfile.TemporaryDirectory(dir=MODULE_PATH.parents[1] / "build") as directory:
            build = Path(directory) / "build"
            first = build / "001_first"
            second = build / "002_second"
            first.mkdir(parents=True)
            second.mkdir()
            (first / "result.fs").touch()
            (second / "result.fs").touch()
            os.chmod(first / "result.fs", stat.S_IREAD)
            removed = fpga.clean_outputs(build, "001_first", False)
            self.assertEqual(removed, [first.resolve()])
            self.assertFalse(first.exists())
            self.assertTrue(second.exists())

    def test_clean_all_recreates_build_marker(self) -> None:
        with tempfile.TemporaryDirectory(dir=MODULE_PATH.parents[1] / "build") as directory:
            build = Path(directory) / "build"
            (build / "001_first").mkdir(parents=True)
            fpga.clean_outputs(build, None, True)
            self.assertTrue((build / ".gitkeep").is_file())


if __name__ == "__main__":
    unittest.main()
