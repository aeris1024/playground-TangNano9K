module i2s_receive (
    input wire clk, bclk, reset, ready, adc_data,
    input wire [7:0] phase,
    output reg sample_valid,
    output reg signed [23:0] pcm_l, pcm_r
);
    reg adc_sample;
    always @(posedge bclk) adc_sample <= adc_data;
    reg [23:0] shift;
    reg signed [23:0] left_hold;
    wire [4:0] slot = phase[6:2];
    wire [23:0] completed = {shift[22:0], adc_sample};
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            shift <= 0; left_hold <= 0;
            pcm_l <= 0; pcm_r <= 0; sample_valid <= 0;
        end else begin
            sample_valid <= 0;
            // Consume the BCLK capture one MCLK later; slot zero is the I2S delay.
            if (phase[1:0] == 2 && slot >= 1 && slot <= 24) begin
                shift <= completed;
                if (slot == 24) begin
                    if (!phase[7]) left_hold <= $signed(completed);
                    else if (ready) begin
                        pcm_l <= left_hold >>> 1;
                        pcm_r <= $signed(completed) >>> 1;
                        sample_valid <= 1;
                    end
                end
            end
        end
    end
endmodule
