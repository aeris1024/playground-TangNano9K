`timescale 1ns/1ps

module blink_checker #(
    parameter integer HALF_PERIOD = 4
) (
    input wire clk,
    output reg done = 1'b0
);
    wire [5:0] led;
    integer cycle;
    reg expected_on;

    top #(.HALF_PERIOD_CYCLES(HALF_PERIOD)) dut (.clk(clk), .led(led));

    initial begin
        #1;
        if (led !== 6'b111111) begin
            $display("TEST 001_blink ... FAIL initial LEDs (half=%0d)", HALF_PERIOD);
            $fatal(1);
        end
        for (cycle = 1; cycle <= HALF_PERIOD * 8; cycle = cycle + 1) begin
            @(posedge clk);
            #1;
            expected_on = (cycle / HALF_PERIOD) % 2;
            if (led !== {5'b11111, ~expected_on}) begin
                $display("TEST 001_blink ... FAIL half=%0d cycle=%0d led=%b",
                         HALF_PERIOD, cycle, led);
                $fatal(1);
            end
        end
        done = 1'b1;
    end
endmodule

module tb_top;
    reg clk = 1'b0;
    wire [2:0] done;
    always #5 clk = ~clk;

    // Exercise minimum width, power-of-two and non-power-of-two counters.
    blink_checker #(.HALF_PERIOD(1)) c1 (.clk(clk), .done(done[0]));
    blink_checker #(.HALF_PERIOD(4)) c4 (.clk(clk), .done(done[1]));
    blink_checker #(.HALF_PERIOD(5)) c5 (.clk(clk), .done(done[2]));

    initial begin
        wait (&done);
        $display("TEST 001_blink ... PASS");
        $finish;
    end
    initial begin
        #10000;
        $display("TEST 001_blink ... FAIL timeout");
        $fatal(1);
    end
endmodule
