module pdm_ddr #(
    parameter integer SWAP_EDGES = 0
) (
    input wire clk, clear,
    input wire left_bit, right_bit,
    output wire data
);
    wire d0 = SWAP_EDGES ? right_bit : left_bit;
    wire d1 = SWAP_EDGES ? left_bit : right_bit;
`ifdef __ICARUS__
    // Match the vendor ODDRC pipeline, not an idealized zero-latency DDR mux.
    reg a0 = 0, a1 = 0, a2 = 0;
    reg b0 = 0, b1 = 0, b2 = 0;
    always @(posedge clk or posedge clear) begin
        if (clear) begin a0 <= 0; a1 <= 0; b0 <= 0; b1 <= 0; b2 <= 0; end
        else begin a0 <= d0; a1 <= a0; b0 <= d1; b1 <= b0; b2 <= b1; end
    end
    always @(negedge clk or posedge clear) begin
        if (clear) a2 <= 0;
        else a2 <= a1;
    end
    assign data = clk ? a2 : b2;
`else
    ODDRC output_cell (.CLK(clk), .CLEAR(clear), .D0(d0), .D1(d1),
                       .TX(1'b0), .Q0(data), .Q1());
`endif
endmodule
