module audio_port #(
    parameter integer WINDOW_CYCLES = 27000,
    parameter integer STARTUP_CYCLES = 3072000,
    parameter integer SWAP_EDGES = 0
) (
    input wire sys_clk, reference_clk, adc_data, enable_18, enable_33,
    output wire adc_mclk, adc_bclk, adc_lrclk, pdm_data_18, pdm_data_33,
    output wire locked, running, fault, activity
);
    wire reference_global;
`ifdef __ICARUS__
    assign reference_global = reference_clk;
`else
    BUFG reference_buffer (.I(reference_clk), .O(reference_global));
`endif
    wire good, present, reset_audio, ready;
    wire [7:0] phase;
    clock_channel #(.WINDOW_CYCLES(WINDOW_CYCLES), .STARTUP_CYCLES(STARTUP_CYCLES)) domain (
        .sys_clk(sys_clk), .reference_clk(reference_clk), .audio_clk(adc_mclk),
        .locked(locked), .clock_good(good), .clock_present(present),
        .reset_audio(reset_audio), .ready(ready), .phase(phase),
        .bclk(adc_bclk), .lrclk(adc_lrclk)
    );
    wire reset_chain = reset_audio || !ready;
    wire v0, v1, v2, v3;
    wire signed [23:0] l0, r0, l1, r1, l2, r2, l3, r3;
    wire clip1, clip2, clip3;
    i2s_receive receive (.clk(adc_mclk), .bclk(adc_bclk), .reset(reset_audio), .ready(ready),
        .adc_data(adc_data), .phase(phase), .sample_valid(v0), .pcm_l(l0), .pcm_r(r0));
    halfband_stereo #(.STAGE(0), .TAPS(95), .PERIOD(256)) fir1 (
        .clk(adc_mclk), .reset(reset_chain), .in_valid(v0), .in_l(l0), .in_r(r0),
        .out_valid(v1), .out_l(l1), .out_r(r1), .clipped(clip1));
    halfband_stereo #(.STAGE(1), .TAPS(31), .PERIOD(128)) fir2 (
        .clk(adc_mclk), .reset(reset_chain), .in_valid(v1), .in_l(l1), .in_r(r1),
        .out_valid(v2), .out_l(l2), .out_r(r2), .clipped(clip2));
    halfband_stereo #(.STAGE(2), .TAPS(15), .PERIOD(64)) fir3 (
        .clk(adc_mclk), .reset(reset_chain), .in_valid(v2), .in_l(l2), .in_r(r2),
        .out_valid(v3), .out_l(l3), .out_r(r3), .clipped(clip3));
    audio_meter signal_detector (.clk(adc_mclk), .reset(reset_chain),
        .sample_valid(v0), .left_sample(l0), .right_sample(r0), .pwm(activity));
    reg overflow;
    wire full, empty, two_available, pop;
    wire [47:0] data;
    reg [2:0] read_release;
    stereo_fifo fifo (.write_reset(reset_chain), .read_reset(!read_release[2]), .write_clk(adc_mclk), .write_valid(v3),
        .write_data({l3, r3}), .full(full), .read_clk(reference_global),
        .read_pop(pop), .read_data(data), .empty(empty), .two_available(two_available));
    always @(posedge adc_mclk or posedge reset_chain) begin
        if (reset_chain) overflow <= 0;
        else if (v3 && full) overflow <= 1;
    end
    always @(posedge reference_global or posedge reset_chain) begin
        if (reset_chain) read_release <= 0;
        else read_release <= {read_release[1:0], 1'b1};
    end
    wire lb, rb, underflow, backend_clip;
    // The live-clock silence generator runs even while the PLL is starting.
    reg silence = 0;
    always @(posedge reference_global or negedge present) begin
        if (!present) silence <= 0;
        else silence <= ~silence;
    end
    pdm_backend backend (.clk(reference_global), .reset(!read_release[2]),
        .empty(empty), .two_available(two_available), .read_data(data), .read_pop(pop),
        .left_bit(lb), .right_bit(rb), .running(running),
        .underflow(underflow), .clipped(backend_clip));
    wire raw_18, raw_33;
    pdm_ddr #(.SWAP_EDGES(SWAP_EDGES)) transmitter_18 (.clk(reference_global), .clear(!present || !enable_18),
        .left_bit(read_release[2] ? lb : silence),
        .right_bit(read_release[2] ? rb : silence), .data(raw_18));
    pdm_ddr #(.SWAP_EDGES(SWAP_EDGES)) transmitter_33 (.clk(reference_global), .clear(!present || !enable_33),
        .left_bit(read_release[2] ? lb : silence),
        .right_bit(read_release[2] ? rb : silence), .data(raw_33));
    assign pdm_data_18=raw_18;
    assign pdm_data_33=raw_33;
    assign fault = clip1 || clip2 || clip3 || overflow || underflow || backend_clip;
endmodule
