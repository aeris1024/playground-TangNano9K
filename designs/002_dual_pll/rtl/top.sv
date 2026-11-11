module top #(
    parameter integer WINDOW_CYCLES = 27000,
    parameter integer STARTUP_CYCLES = 3072000
) (
    input wire sys_clk,
    input wire pdm_clk_a,
    input wire pdm_clk_b,
    output wire adc_mclk_a, adc_bclk_a, adc_lrclk_a,
    output wire adc_mclk_b, adc_bclk_b, adc_lrclk_b,
    output wire [5:0] led
);
    wire lock_a, lock_b, good_a, good_b, ready_a, ready_b;
    clock_channel #(.WINDOW_CYCLES(WINDOW_CYCLES), .STARTUP_CYCLES(STARTUP_CYCLES)) domain_a (
        .sys_clk(sys_clk), .reference_clk(pdm_clk_a), .audio_clk(adc_mclk_a),
        .locked(lock_a), .clock_good(good_a), .reset_audio(), .ready(ready_a), .phase(),
        .bclk(adc_bclk_a), .lrclk(adc_lrclk_a)
    );
    clock_channel #(.WINDOW_CYCLES(WINDOW_CYCLES), .STARTUP_CYCLES(STARTUP_CYCLES)) domain_b (
        .sys_clk(sys_clk), .reference_clk(pdm_clk_b), .audio_clk(adc_mclk_b),
        .locked(lock_b), .clock_good(good_b), .reset_audio(), .ready(ready_b), .phase(),
        .bclk(adc_bclk_b), .lrclk(adc_lrclk_b)
    );
    assign led = ~{good_b, ready_b, lock_b, good_a, ready_a, lock_a};
endmodule
