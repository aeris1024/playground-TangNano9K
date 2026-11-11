# Tang Nano 9K board definition

- Part: `GW1NR-LV9QN88PC6/I5`, version C (`GW1NR-9C`).
- Oscillator: 27 MHz, pin 52, bank 1 at 3.3 V (LVCMOS33).
- LED1..LED6: pins 10, 11, 13, 14, 15, 16; active low.
- LED bank 3 is powered at 1.8 V. Use LVCMOS18, not LVCMOS33.
- Programmer: `USB Debugger A`, cable index 4; USB location is discovered.
- Expected JTAG IDCODE: `0x1100481B`. The scan can report both `GW1N-9C` and
  `GW1NR-9C` for this ID; the physical board determines the exact variant.
- SRAM programming by default, Gowin Programmer operation 2.
- Explicit `--flash`: embedded Flash erase/program, operation 5, JTAG 2.5 MHz.
  Enabled by `programmer_flash_operation = 5` in board.toml.
  The on-board external SPI Flash is not used for this operation.
- No Primer 25K CPU/READY/DONE GPIO options are enabled for this sample.

The device version comes from the official
[project file](https://github.com/sipeed/TangNano-9K-example/blob/main/led/9K_LED_project.gprj).
Pin assignments and bank voltages follow the official
[schematic](https://dl.sipeed.com/fileList/TANG/Nano%209K/2_Schematic/Tang_Nano_9k_3672_Schematic.pdf)
and [LED constraints](https://github.com/sipeed/TangNano-9K-example/blob/main/led/src/9K_LED_project.cst).
