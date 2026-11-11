module top #(
    parameter integer HALF_PERIOD_CYCLES = 13_500_000
) (
    input  wire       clk,
    output wire [5:0] led
);
    localparam integer COUNTER_WIDTH =
        (HALF_PERIOD_CYCLES <= 1) ? 1 : $clog2(HALF_PERIOD_CYCLES);

    reg [COUNTER_WIDTH-1:0] counter = {COUNTER_WIDTH{1'b0}};
    reg led_on = 1'b0;

    // LED1..LED6 are active low. Keep LED2..LED6 off.
    assign led = {5'b11111, ~led_on};

    always @(posedge clk) begin
        if (counter == HALF_PERIOD_CYCLES - 1) begin
            counter <= {COUNTER_WIDTH{1'b0}};
            led_on <= ~led_on;
        end else begin
            counter <= counter + 1'b1;
        end
    end
endmodule
