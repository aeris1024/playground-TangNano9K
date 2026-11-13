# Shared components

`rtl/audio_pll.sv` and `rtl/clock_channel.sv` are shared by `002_dual_pll` and
`003_analog2pdm`. They provide independent x4 PLLs, input-clock monitoring,
synchronized reset release and ADC startup delay. The Icarus PLL model is
functional only; physical routing and timing must be checked with Gowin.

Keep audio DSP local to `003_analog2pdm` until a second design uses it.

`rtl/audio_meter.sv`は003/004共用の対数ピーク音量・減衰・1 kHz PWM回路です。
