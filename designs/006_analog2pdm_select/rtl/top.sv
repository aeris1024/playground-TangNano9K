module top #(
    parameter integer BOOT_CYCLES=270000,
    parameter integer WINDOW_CYCLES = 27000,
    parameter integer STARTUP_CYCLES = 3072000,
    parameter integer SWAP_EDGES_A = 0,
    parameter integer SWAP_EDGES_B = 0,
    parameter integer BLINK_HALF_CYCLES = 6750000
) (
    input wire sys_clk, mode_select, pdm_clk_a_18, pdm_clk_b_18, pdm_clk_a_33, pdm_clk_b_33,
    input wire adc_data_a, adc_data_b,
    output wire adc_mclk_a, adc_bclk_a, adc_lrclk_a, pdm_data_a_18, pdm_data_a_33,
    output wire adc_mclk_b, adc_bclk_b, adc_lrclk_b, pdm_data_b_18, pdm_data_b_33,
    output wire [5:0] led
);
    reg [1:0] mode_sync=0;
    reg [$clog2(BOOT_CYCLES+1)-1:0] boot_count=0;
    reg use_3v3=0,mode_valid=0;
    always @(posedge sys_clk) begin
      mode_sync<={mode_sync[0],mode_select};
      if(!mode_valid) begin
        if(boot_count==BOOT_CYCLES-1) begin use_3v3<=mode_sync[1];mode_valid<=1;end
        else boot_count<=boot_count+1'b1;
      end
    end
    wire reference_a=mode_valid ? (use_3v3 ? pdm_clk_a_33:pdm_clk_a_18):1'b0;
    wire reference_b=mode_valid ? (use_3v3 ? pdm_clk_b_33:pdm_clk_b_18):1'b0;
    wire la, ra, fa, lb, rb, fb, activity_a, activity_b;
    audio_port #(.WINDOW_CYCLES(WINDOW_CYCLES), .STARTUP_CYCLES(STARTUP_CYCLES), .SWAP_EDGES(SWAP_EDGES_A)) port_a (
        .sys_clk(sys_clk), .reference_clk(reference_a), .adc_data(adc_data_a),
        .adc_mclk(adc_mclk_a), .adc_bclk(adc_bclk_a), .adc_lrclk(adc_lrclk_a),
        .pdm_data_18(pdm_data_a_18), .pdm_data_33(pdm_data_a_33), .enable_18(mode_valid && !use_3v3), .enable_33(mode_valid && use_3v3), .locked(la), .running(ra), .fault(fa), .activity(activity_a));
    audio_port #(.WINDOW_CYCLES(WINDOW_CYCLES), .STARTUP_CYCLES(STARTUP_CYCLES), .SWAP_EDGES(SWAP_EDGES_B)) port_b (
        .sys_clk(sys_clk), .reference_clk(reference_b), .adc_data(adc_data_b),
        .adc_mclk(adc_mclk_b), .adc_bclk(adc_bclk_b), .adc_lrclk(adc_lrclk_b),
        .pdm_data_18(pdm_data_b_18), .pdm_data_33(pdm_data_b_33), .enable_18(mode_valid && !use_3v3), .enable_33(mode_valid && use_3v3), .locked(lb), .running(rb), .fault(fb), .activity(activity_b));
    reg [5:0] status_sync1 = 0, status_sync2 = 0;
    always @(posedge sys_clk) begin
        status_sync1 <= {fb, rb, lb, fa, ra, la};
        status_sync2 <= status_sync1;
    end
    reg [1:0] activity_sync1 = 0, activity_sync2 = 0;
    localparam integer BLINK_WIDTH = $clog2(BLINK_HALF_CYCLES + 1);
    reg [BLINK_WIDTH-1:0] blink_count = 0;
    reg blink = 0;
    always @(posedge sys_clk) begin
        activity_sync1 <= {activity_b, activity_a};
        activity_sync2 <= activity_sync1;
        if (blink_count == BLINK_HALF_CYCLES - 1) begin
            blink_count <= 0;
            blink <= ~blink;
        end else blink_count <= blink_count + 1'b1;
    end
    wire show_a = status_sync2[2] ? blink : (status_sync2[1] && activity_sync2[0]);
    wire show_b = status_sync2[5] ? blink : (status_sync2[4] && activity_sync2[1]);
    assign led = ~{show_b, status_sync2[4:3], show_a, status_sync2[1:0]};
endmodule
