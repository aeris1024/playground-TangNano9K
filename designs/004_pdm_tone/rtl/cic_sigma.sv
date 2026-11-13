// Third-order CIC interpolator (R=8, gain=64) and second-order error-feedback
// one-bit modulator. All arithmetic is signed; the CIC wraps at 36 bits.
module cic_sigma (
    input wire clk, reset, input_valid,
    input wire signed [23:0] pcm,
    output reg pdm,
    output reg clipped
);
    reg signed [35:0] comb_x, comb_d1, comb_d2;
    reg signed [35:0] i1, i2, i3;
    reg signed [31:0] error1, error2;
    wire signed [35:0] extended_pcm = {{12{pcm[23]}}, pcm};
    wire signed [35:0] d1 = extended_pcm - comb_x;
    wire signed [35:0] d2 = d1 - comb_d1;
    wire signed [35:0] d3 = d2 - comb_d2;
    wire signed [35:0] ni1 = i1 + (input_valid ? d3 : 36'sd0);
    wire signed [35:0] ni2 = i2 + ni1;
    wire signed [35:0] ni3 = i3 + ni2;
    wire signed [35:0] normalized = (ni3 + 36'sd32 - (ni3 < 0 ? 36'sd1 : 36'sd0)) >>> 6;
    wire signed [23:0] sample = normalized > 8388607 ? 24'sh7fffff :
                               normalized < -8388608 ? 24'sh800000 : normalized[23:0];
    wire signed [33:0] e1 = {{2{error1[31]}}, error1};
    wire signed [33:0] e2 = {{2{error2[31]}}, error2};
    wire signed [33:0] input_sample = {{10{sample[23]}}, sample};
    wire signed [33:0] u = input_sample - (e1 <<< 1) + e2;
    wire signed [33:0] quantized = u >= 0 ? 34'sd8388608 : -34'sd8388608;
    wire signed [33:0] next_error = quantized - u;
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            comb_x <= 0; comb_d1 <= 0; comb_d2 <= 0;
            i1 <= 0; i2 <= 0; i3 <= 0;
            error1 <= 0; error2 <= 0;
            pdm <= 0; clipped <= 0;
        end else begin
            if (input_valid) begin comb_x <= extended_pcm; comb_d1 <= d1; comb_d2 <= d2; end
            i1 <= ni1; i2 <= ni2; i3 <= ni3;
            if (normalized > 8388607 || normalized < -8388608) clipped <= 1;
            if (next_error > 34'sd2147483647 || next_error < -34'sd2147483648) begin
                error1 <= 0; error2 <= 0; pdm <= 0; clipped <= 1;
            end else begin
                error2 <= error1;
                error1 <= next_error[31:0];
                pdm <= u >= 0;
            end
        end
    end
endmodule
