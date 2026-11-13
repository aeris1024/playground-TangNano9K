// Eight stereo words bridge the phase of a PLL-derived clock to its original
// reference. There is no data path between port A and port B.
module stereo_fifo (
    input wire reset,
    input wire write_clk, write_valid,
    input wire [47:0] write_data,
    output wire full,
    input wire read_clk, read_pop,
    output wire [47:0] read_data,
    output wire empty, two_available
);
    reg [47:0] memory [0:7];
    reg [3:0] wp, rp, wg, rg;
    reg [3:0] rg_w1, rg_w2, wg_r1, wg_r2;
    wire [3:0] wp_next = wp + 1'b1;
    wire [3:0] wp_next_gray = (wp_next >> 1) ^ wp_next;
    wire [3:0] read_write_binary = {wg_r2[3], ^wg_r2[3:2], ^wg_r2[3:1], ^wg_r2};
    assign full = wg == {~rg_w2[3:2], rg_w2[1:0]};
    assign empty = rg == wg_r2;
    assign two_available = (read_write_binary - rp) >= 4'd2;
    assign read_data = memory[rp[2:0]];
    always @(posedge write_clk) begin
        if (!reset && write_valid && !full) memory[wp[2:0]] <= write_data;
    end
    always @(posedge write_clk or posedge reset) begin
        if (reset) begin wp <= 0; wg <= 0; rg_w1 <= 0; rg_w2 <= 0; end
        else begin
            rg_w1 <= rg; rg_w2 <= rg_w1;
            if (write_valid && !full) begin wp <= wp_next; wg <= wp_next_gray; end
        end
    end
    always @(posedge read_clk or posedge reset) begin
        if (reset) begin rp <= 0; rg <= 0; wg_r1 <= 0; wg_r2 <= 0; end
        else begin
            wg_r1 <= wg; wg_r2 <= wg_r1;
            if (read_pop && !empty) begin
                rp <= rp + 1'b1;
                rg <= ((rp + 4'd1) >> 1) ^ (rp + 4'd1);
            end
        end
    end
endmodule
