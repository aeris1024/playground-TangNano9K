module pdm_backend (
    input wire clk, reset,
    input wire empty, two_available,
    input wire [47:0] read_data,
    output wire read_pop,
    output wire left_bit, right_bit,
    output wire running,
    output reg underflow,
    output wire clipped
);
    reg started;
    reg [2:0] tick;
    reg idle;
    wire l, r, clip_l, clip_r;
    assign read_pop = started && tick == 0 && !empty;
    assign running = started;
    assign left_bit = started ? l : idle;
    assign right_bit = started ? r : idle;
    assign clipped = clip_l || clip_r;
    always @(posedge clk or posedge reset) begin
        if (reset) begin started <= 0; tick <= 0; idle <= 0; underflow <= 0; end
        else begin
            idle <= ~idle;
            if (!started) begin
                tick <= 0;
                if (two_available) started <= 1;
            end else begin
                tick <= tick + 1'b1;
                if (tick == 0 && empty) begin underflow <= 1; started <= 0; end
            end
        end
    end
    cic_sigma left (.clk(clk), .reset(reset || !started), .input_valid(read_pop),
                    .pcm(read_data[47:24]), .pdm(l), .clipped(clip_l));
    cic_sigma right (.clk(clk), .reset(reset || !started), .input_valid(read_pop),
                     .pcm(read_data[23:0]), .pdm(r), .clipped(clip_r));
endmodule
