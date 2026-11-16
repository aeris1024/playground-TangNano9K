create_clock -name sys_clk -period 37.037 [get_ports {sys_clk}]
# Boot-latched mode selection: model both external roots and both PLL masters.
# A/B are asynchronous; the 1.8 V and 3.3 V modes are mutually exclusive.
# BCLK constraints target the nets so the internal ADC capture registers are timed.
create_clock -name pdm_a_18 -period 325.521 [get_ports {pdm_clk_a_18}]
create_generated_clock -name selected_a_18 -source [get_ports {pdm_clk_a_18}] -master_clock pdm_a_18 -divide_by 1 -add [get_nets {reference_a}]
create_generated_clock -name audio_a_18 -source [get_nets {reference_a}] -master_clock selected_a_18 -multiply_by 4 -add [get_pins {port_a/domain/clock_source/pll/CLKOUT}]
create_generated_clock -name adc_bclk_a_18 -source [get_pins {port_a/domain/clock_source/pll/CLKOUT}] -master_clock audio_a_18 -divide_by 4 -add [get_nets {adc_bclk_a}]
create_generated_clock -name adc_lrclk_a_18 -source [get_pins {port_a/domain/clock_source/pll/CLKOUT}] -master_clock audio_a_18 -divide_by 256 -add [get_ports {adc_lrclk_a}]
set_input_delay -clock adc_bclk_a_18 -clock_fall -add_delay -max 50.0 [get_ports {adc_data_a}]
set_input_delay -clock adc_bclk_a_18 -clock_fall -add_delay -min -10.0 [get_ports {adc_data_a}]
set_output_delay -clock pdm_a_18 -add_delay -max 20 [get_ports {pdm_data_a_18}]
set_output_delay -clock pdm_a_18 -add_delay -min 0 [get_ports {pdm_data_a_18}]
set_output_delay -clock pdm_a_18 -clock_fall -add_delay -max 20 [get_ports {pdm_data_a_18}]
set_output_delay -clock pdm_a_18 -clock_fall -add_delay -min 0 [get_ports {pdm_data_a_18}]
create_clock -name pdm_a_33 -period 325.521 [get_ports {pdm_clk_a_33}]
create_generated_clock -name selected_a_33 -source [get_ports {pdm_clk_a_33}] -master_clock pdm_a_33 -divide_by 1 -add [get_nets {reference_a}]
create_generated_clock -name audio_a_33 -source [get_nets {reference_a}] -master_clock selected_a_33 -multiply_by 4 -add [get_pins {port_a/domain/clock_source/pll/CLKOUT}]
create_generated_clock -name adc_bclk_a_33 -source [get_pins {port_a/domain/clock_source/pll/CLKOUT}] -master_clock audio_a_33 -divide_by 4 -add [get_nets {adc_bclk_a}]
create_generated_clock -name adc_lrclk_a_33 -source [get_pins {port_a/domain/clock_source/pll/CLKOUT}] -master_clock audio_a_33 -divide_by 256 -add [get_ports {adc_lrclk_a}]
set_input_delay -clock adc_bclk_a_33 -clock_fall -add_delay -max 50.0 [get_ports {adc_data_a}]
set_input_delay -clock adc_bclk_a_33 -clock_fall -add_delay -min -10.0 [get_ports {adc_data_a}]
set_output_delay -clock pdm_a_33 -add_delay -max 20 [get_ports {pdm_data_a_33}]
set_output_delay -clock pdm_a_33 -add_delay -min 0 [get_ports {pdm_data_a_33}]
set_output_delay -clock pdm_a_33 -clock_fall -add_delay -max 20 [get_ports {pdm_data_a_33}]
set_output_delay -clock pdm_a_33 -clock_fall -add_delay -min 0 [get_ports {pdm_data_a_33}]
create_clock -name pdm_b_18 -period 325.521 [get_ports {pdm_clk_b_18}]
create_generated_clock -name selected_b_18 -source [get_ports {pdm_clk_b_18}] -master_clock pdm_b_18 -divide_by 1 -add [get_nets {reference_b}]
create_generated_clock -name audio_b_18 -source [get_nets {reference_b}] -master_clock selected_b_18 -multiply_by 4 -add [get_pins {port_b/domain/clock_source/pll/CLKOUT}]
create_generated_clock -name adc_bclk_b_18 -source [get_pins {port_b/domain/clock_source/pll/CLKOUT}] -master_clock audio_b_18 -divide_by 4 -add [get_nets {adc_bclk_b}]
create_generated_clock -name adc_lrclk_b_18 -source [get_pins {port_b/domain/clock_source/pll/CLKOUT}] -master_clock audio_b_18 -divide_by 256 -add [get_ports {adc_lrclk_b}]
set_input_delay -clock adc_bclk_b_18 -clock_fall -add_delay -max 50.0 [get_ports {adc_data_b}]
set_input_delay -clock adc_bclk_b_18 -clock_fall -add_delay -min -10.0 [get_ports {adc_data_b}]
set_output_delay -clock pdm_b_18 -add_delay -max 20 [get_ports {pdm_data_b_18}]
set_output_delay -clock pdm_b_18 -add_delay -min 0 [get_ports {pdm_data_b_18}]
set_output_delay -clock pdm_b_18 -clock_fall -add_delay -max 20 [get_ports {pdm_data_b_18}]
set_output_delay -clock pdm_b_18 -clock_fall -add_delay -min 0 [get_ports {pdm_data_b_18}]
create_clock -name pdm_b_33 -period 325.521 [get_ports {pdm_clk_b_33}]
create_generated_clock -name selected_b_33 -source [get_ports {pdm_clk_b_33}] -master_clock pdm_b_33 -divide_by 1 -add [get_nets {reference_b}]
create_generated_clock -name audio_b_33 -source [get_nets {reference_b}] -master_clock selected_b_33 -multiply_by 4 -add [get_pins {port_b/domain/clock_source/pll/CLKOUT}]
create_generated_clock -name adc_bclk_b_33 -source [get_pins {port_b/domain/clock_source/pll/CLKOUT}] -master_clock audio_b_33 -divide_by 4 -add [get_nets {adc_bclk_b}]
create_generated_clock -name adc_lrclk_b_33 -source [get_pins {port_b/domain/clock_source/pll/CLKOUT}] -master_clock audio_b_33 -divide_by 256 -add [get_ports {adc_lrclk_b}]
set_input_delay -clock adc_bclk_b_33 -clock_fall -add_delay -max 50.0 [get_ports {adc_data_b}]
set_input_delay -clock adc_bclk_b_33 -clock_fall -add_delay -min -10.0 [get_ports {adc_data_b}]
set_output_delay -clock pdm_b_33 -add_delay -max 20 [get_ports {pdm_data_b_33}]
set_output_delay -clock pdm_b_33 -add_delay -min 0 [get_ports {pdm_data_b_33}]
set_output_delay -clock pdm_b_33 -clock_fall -add_delay -max 20 [get_ports {pdm_data_b_33}]
set_output_delay -clock pdm_b_33 -clock_fall -add_delay -min 0 [get_ports {pdm_data_b_33}]
set_clock_groups -asynchronous -group [get_clocks {sys_clk}] -group [get_clocks {pdm_a_18 selected_a_18 audio_a_18 adc_bclk_a_18 adc_lrclk_a_18 pdm_a_33 selected_a_33 audio_a_33 adc_bclk_a_33 adc_lrclk_a_33}] -group [get_clocks {pdm_b_18 selected_b_18 audio_b_18 adc_bclk_b_18 adc_lrclk_b_18 pdm_b_33 selected_b_33 audio_b_33 adc_bclk_b_33 adc_lrclk_b_33}]
set_clock_groups -exclusive -group [get_clocks {pdm_a_18 selected_a_18 audio_a_18 adc_bclk_a_18 adc_lrclk_a_18 pdm_b_18 selected_b_18 audio_b_18 adc_bclk_b_18 adc_lrclk_b_18}] -group [get_clocks {pdm_a_33 selected_a_33 audio_a_33 adc_bclk_a_33 adc_lrclk_a_33 pdm_b_33 selected_b_33 audio_b_33 adc_bclk_b_33 adc_lrclk_b_33}]
# Only the first Gray-pointer synchronizer flops are asynchronous endpoints.
# Subsequent synchronizer stages, FIFO data paths and both audio datapaths stay timed.
set_false_path -to [get_pins {port_a/fifo/wg_r1*/D port_a/fifo/rg_w1*/D port_b/fifo/wg_r1*/D port_b/fifo/rg_w1*/D}]

# Only asynchronous CLEAR inputs of the reference-domain reset-release synchronizers.
# Their data chain and the downstream FIFO read registers remain timed.
set_false_path -to [get_pins {port_a/read_release*/CLEAR port_b/read_release*/CLEAR}]

# Keep the ADC input and BCLK-to-MCLK handoff visible in the timing report.
# These paths are timed normally, without multicycle or false-path exceptions.
report_timing -setup -from [get_ports {adc_data_a adc_data_b}] -max_paths 16
report_timing -hold -from [get_ports {adc_data_a adc_data_b}] -max_paths 16
report_timing -setup -from_clock [get_clocks {adc_bclk_a_18 adc_bclk_a_33 adc_bclk_b_18 adc_bclk_b_33}] -max_paths 16
report_timing -hold -from_clock [get_clocks {adc_bclk_a_18 adc_bclk_a_33 adc_bclk_b_18 adc_bclk_b_33}] -max_paths 16
