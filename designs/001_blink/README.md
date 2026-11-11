# 001_blink

LED1 blinks at 1 Hz (0.5 s on, 0.5 s off). LED2..LED6 remain off.
The active-low LEDs use LVCMOS18 in the 1.8 V bank. No external components,
PLL or button inputs are needed.

`top.sv` divides the on-board 27 MHz clock by 13,500,000 for each half period.
The counter and LED state use FPGA register initialization.

Run from the repository root:

```powershell
.\fpga.ps1 doctor
.\fpga.ps1 sim 001_blink
.\fpga.ps1 build 001_blink
.\fpga.ps1 program 001_blink
```

The testbench checks every cycle for initial off state, active-low polarity,
toggle interval and the five constant-off LEDs, using half periods of 1, 4 and
5 cycles. Success prints `TEST 001_blink ... PASS`; failures call `$fatal(1)`.

SRAM programming is volatile. Reapply `program` after a power cycle.

To replace the design stored in embedded Flash for power-on boot:

```powershell
.\fpga.ps1 program 001_blink --flash
```

This uses operation 5 (embedded Flash erase/program) at JTAG 2.5 MHz.
After success, disconnect and reconnect power without another `program` call,
then check LED1. Power-cycle boot confirmation is recorded separately from
successful programming. The external SPI Flash is not modified.
