// One shared multiplier per stage handles both channels. Synchronous history
// storage has no reset: valid_frames masks unwritten samples after every reset.
module halfband_stereo #(
    parameter integer STAGE = 0,
    parameter integer TAPS = 95,
    parameter integer PERIOD = 256
) (
    input wire clk, reset, in_valid,
    input wire signed [23:0] in_l, in_r,
    output reg out_valid,
    output reg signed [23:0] out_l, out_r,
    output reg clipped
);
    localparam integer TERMS = (TAPS + 1) / 2;
    localparam integer FIRST = 2 * TERMS + 4;
    localparam integer DELAY = (TAPS - 3) / 4;
    reg signed [23:0] history [0:127];
    reg [5:0] write_ptr;
    reg [6:0] valid_frames;
    reg [8:0] tick;
    reg active;
    reg signed [23:0] input_l, input_r;
    reg signed [49:0] acc_l, acc_r;
    reg signed [23:0] center_l, center_r;

    wire issue = active && tick >= 2 && tick < 2 + 2 * TERMS;
    wire center_issue = active && (tick == 2 + 2 * TERMS || tick == 3 + 2 * TERMS);
    wire [8:0] tap_offset = tick - 9'd2;
    wire [5:0] tap_index = tap_offset[6:1];
    wire channel = issue ? tick[0] : (tick == 3 + 2 * TERMS);
    wire [5:0] age = issue ? tap_index : DELAY;
    wire [5:0] read_ptr = write_ptr - age;
    wire [6:0] read_address = {read_ptr, channel};
    wire signed [17:0] coefficient;
    halfband_coeff #(.STAGE(STAGE)) rom (.index(tap_index), .coefficient(coefficient));
    reg signed [23:0] ram_q;
    reg signed [17:0] coeff_q;
    reg valid_q, center_q, channel_q, zero_q;
    wire signed [23:0] sample_q = zero_q ? 24'sd0 : ram_q;
    wire signed [41:0] product = sample_q * coeff_q;

    // Separate process permits simple dual-port BSRAM inference.
    always @(posedge clk) begin
        if (!reset && active && tick == 0) history[{write_ptr, 1'b0}] <= input_l;
        else if (!reset && active && tick == 1) history[{write_ptr, 1'b1}] <= input_r;
        ram_q <= history[read_address];
    end

    function automatic signed [23:0] rounded(input signed [49:0] value);
        reg signed [49:0] scaled;
        begin
            scaled = (value + 50'sd32768 - (value < 0 ? 50'sd1 : 50'sd0)) >>> 16;
            if (scaled > 8388607) rounded = 24'sh7fffff;
            else if (scaled < -8388608) rounded = 24'sh800000;
            else rounded = scaled[23:0];
        end
    endfunction
    function automatic overflow(input signed [49:0] value);
        begin
            overflow = value > 50'sd549755781119 || value < -50'sd549755846655;
        end
    endfunction

    always @(posedge clk or posedge reset) begin
        if (reset) begin
            write_ptr <= 63;
            valid_frames <= 0;
            tick <= 0;
            active <= 0;
            input_l <= 0; input_r <= 0;
            acc_l <= 0; acc_r <= 0;
            center_l <= 0; center_r <= 0;
            coeff_q <= 0;
            valid_q <= 0; center_q <= 0; channel_q <= 0; zero_q <= 1;
            out_valid <= 0; out_l <= 0; out_r <= 0; clipped <= 0;
        end else begin
            out_valid <= 0;
            valid_q <= issue;
            center_q <= center_issue;
            channel_q <= channel;
            zero_q <= age >= valid_frames;
            coeff_q <= coefficient;
            if (valid_q) begin
                if (channel_q) acc_r <= acc_r + product;
                else acc_l <= acc_l + product;
            end
            if (center_q) begin
                if (channel_q) center_r <= sample_q;
                else center_l <= sample_q;
            end
            if (active) begin
                if (tick == FIRST) begin
                    out_l <= rounded(acc_l);
                    out_r <= rounded(acc_r);
                    out_valid <= 1;
                    if (overflow(acc_l) || overflow(acc_r)) clipped <= 1;
                end
                if (tick == FIRST + PERIOD / 2) begin
                    out_l <= center_l;
                    out_r <= center_r;
                    out_valid <= 1;
                end
                if (tick == PERIOD - 1) active <= 0;
                else tick <= tick + 1'b1;
            end
            if (in_valid) begin
                input_l <= in_l; input_r <= in_r;
                write_ptr <= write_ptr + 1'b1;
                if (valid_frames < 64) valid_frames <= valid_frames + 1'b1;
                acc_l <= 0; acc_r <= 0;
                tick <= 0;
                active <= 1;
            end
        end
    end
endmodule
