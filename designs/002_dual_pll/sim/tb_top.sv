`timescale 1ns/1ps
module tb_top;
    reg sys_clk = 0;
    reg pdm_clk_a = 0, pdm_clk_b = 0;
    reg run_a = 1, run_b = 1;
    wire ma, mb, ba, bb, la, lb;
    wire [5:0] led;
    integer count_a = 0, count_b = 0;
    integer before_a, before_b;
    always #18.518518519 sys_clk = ~sys_clk;
    always #162.597818848 if (run_a) pdm_clk_a = ~pdm_clk_a; else pdm_clk_a = 0;
    initial begin
        #73;
        forever #162.923339973 if (run_b) pdm_clk_b = ~pdm_clk_b; else pdm_clk_b = 0;
    end
    top #(.WINDOW_CYCLES(2700), .STARTUP_CYCLES(128)) dut (
        .sys_clk(sys_clk), .pdm_clk_a(pdm_clk_a), .pdm_clk_b(pdm_clk_b),
        .adc_mclk_a(ma), .adc_bclk_a(ba), .adc_lrclk_a(la),
        .adc_mclk_b(mb), .adc_bclk_b(bb), .adc_lrclk_b(lb), .led(led)
    );
    always @(posedge ma) count_a = count_a + 1;
    always @(posedge mb) count_b = count_b + 1;
    initial begin
        #250000;
        if (led !== 6'b0) $fatal(1, "TEST 002_dual_pll ... FAIL initial lock/ready");
        before_a = count_a;
        repeat (40) @(posedge pdm_clk_a);
        if (count_a - before_a < 155 || count_a - before_a > 165)
            $fatal(1, "TEST 002_dual_pll ... FAIL A ratio");
        before_b = count_b;
        repeat (40) @(posedge pdm_clk_b);
        if (count_b - before_b < 155 || count_b - before_b > 165)
            $fatal(1, "TEST 002_dual_pll ... FAIL B ratio");
        run_a = 0;
        before_b = count_b;
        #30000;
        if (led[2:0] !== 3'b111 || led[5:3] !== 3'b000 || count_b <= before_b)
            $fatal(1, "TEST 002_dual_pll ... FAIL A stop affects B");
        run_a = 1;
        #250000;
        if (led !== 0) $fatal(1, "TEST 002_dual_pll ... FAIL A restart");
        run_b = 0;
        before_a = count_a;
        #30000;
        if (led[5:3] !== 3'b111 || led[2:0] !== 3'b000 || count_a <= before_a)
            $fatal(1, "TEST 002_dual_pll ... FAIL B stop affects A");
        run_b = 1;
        #250000;
        if (led !== 0) $fatal(1, "TEST 002_dual_pll ... FAIL B restart");
        $display("TEST 002_dual_pll ... PASS");
        $finish;
    end
    initial begin
        #2000000;
        $fatal(1, "TEST 002_dual_pll ... FAIL timeout");
    end
endmodule
