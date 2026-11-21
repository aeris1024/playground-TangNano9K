# Shared components

`rtl/audio_pll.sv` and `rtl/clock_channel.sv` are used by `002_dual_pll`.
They provide independent x4 PLLs, input-clock monitoring,
synchronized reset release and ADC startup delay. The Icarus PLL model is
functional only; physical routing and timing must be checked with Gowin.
