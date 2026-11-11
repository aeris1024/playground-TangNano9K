# Agent instructions

This repository is a hardware playground for the Tang Nano 9K. Keep each
experiment self-contained under `designs/<name>` and use `design.toml` as the
only public design-discovery interface.

## Required workflow

Run commands in this order and stop on the first failure. Diagnose and fix the
failure before continuing:

```powershell
.\fpga.ps1 doctor
.\fpga.ps1 sim <design>
.\fpga.ps1 build <design>
.\fpga.ps1 program <design>
```

- Prefer CLI output and logs over driving the Gowin GUI.
- `program` defaults to Gowin Programmer operation 2 for volatile SRAM.
- Explicit `program --flash` uses board-defined operation 5 to erase/program
  embedded Flash at 2.5 MHz. External SPI Flash is not a supported target.
- Record Flash transfer success separately from user-observed power-cycle boot.
- Verify the target IDCODE before programming; do not pick an arbitrary USB cable.
- Do not claim hardware success without a successful programmer exit and a
  user-observed LED/UART/result signal.
- Treat missing tools or disconnected hardware as an environment failure.
- Generated files belong under `build/` and must not be committed.
- Only promote RTL into `common/` after at least two designs use it.
- Add a self-checking testbench with machine-readable PASS/FAIL for every design
  where simulation is meaningful.
- Update README.md and its roadmap when adding a numbered design.
- Nano 9K uses a 27 MHz clock on pin 52. LEDs are active low on pins
  10, 11, 13, 14, 15, 16, in the 1.8 V bank (LVCMOS18).

Run the CLI unit tests after changing manifests or tooling:

```powershell
python -m unittest discover -s tests -v
```
