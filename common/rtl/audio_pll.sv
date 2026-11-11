`timescale 1ns/1ps

// Two instances use the same ratios but never share a clock or feedback path.
module audio_pll (
    input wire reference_clk,
    input wire reset,
    output wire audio_clk,
    output wire locked
);
`ifdef __ICARUS__
    // Functional model only: this is not a jitter or physical routing model.
    realtime previous_edge = 0.0;
    realtime measured_period = 325.520833333;
    realtime interval;
    integer good_edges = 0;
    reg model_locked = 1'b0;
    reg model_clk = 1'b0;
    always @(posedge reference_clk or posedge reset) begin
        if (reset) begin
            good_edges = 0;
            model_locked = 1'b0;
            previous_edge = 0.0;
        end else begin
            interval = $realtime - previous_edge;
            if (previous_edge != 0.0 && interval > 300.0 && interval < 350.0)
                measured_period = interval;
            previous_edge = $realtime;
            if (good_edges < 16) good_edges = good_edges + 1;
            if (good_edges == 16) model_locked = 1'b1;
        end
    end
    always begin
        #(measured_period / 8.0);
        if (reset || !model_locked) model_clk = 1'b0;
        else model_clk = ~model_clk;
    end
    assign audio_clk = model_clk;
    assign locked = model_locked;
`else
    rPLL #(
        .FCLKIN("3.072"), .IDIV_SEL(0), .FBDIV_SEL(3), .ODIV_SEL(64),
        .DYN_IDIV_SEL("false"), .DYN_FBDIV_SEL("false"), .DYN_ODIV_SEL("false"),
        .CLKFB_SEL("internal"), .CLKOUT_BYPASS("false"),
        .CLKOUTP_BYPASS("false"), .CLKOUTD_BYPASS("false"),
        .DYN_DA_EN("false"), .PSDA_SEL("0000"), .DUTYDA_SEL("1000"),
        .CLKOUT_FT_DIR(1'b1), .CLKOUTP_FT_DIR(1'b1),
        .CLKOUT_DLY_STEP(0), .CLKOUTP_DLY_STEP(0),
        .DYN_SDIV_SEL(2), .CLKOUTD_SRC("CLKOUT"), .CLKOUTD3_SRC("CLKOUT"),
        .DEVICE("GW1NR-9C")
    ) pll (
        .CLKIN(reference_clk), .CLKFB(1'b0), .RESET(reset), .RESET_P(1'b0),
        .FBDSEL(6'b0), .IDSEL(6'b0), .ODSEL(6'b0),
        .PSDA(4'b0), .DUTYDA(4'b0), .FDLY(4'b0),
        .CLKOUT(audio_clk), .LOCK(locked), .CLKOUTP(), .CLKOUTD(), .CLKOUTD3()
    );
`endif
endmodule
