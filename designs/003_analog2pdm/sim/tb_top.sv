`timescale 1ns/1ps
module pcm1808_model #(
    parameter [23:0] LEFT = 24'h400000,
    parameter [23:0] RIGHT = 24'he00000
) (
    input wire bclk, lrclk, reset,
    output reg data = 0
);
    reg previous_lr = 0;
    integer slot = 0;
    reg [23:0] word;
    always @(negedge bclk or posedge reset) begin
        if (reset) begin
            data = 0; previous_lr = 0; slot = 0;
        end else begin
        #10; // PCM1808 permitted falling-edge data delay.
        if (lrclk != previous_lr) slot = 0;
        else slot = (slot + 1) % 32;
        previous_lr = lrclk;
        word = lrclk ? RIGHT : LEFT;
        data = slot >= 1 && slot <= 24 ? word[24-slot] : 1'b0;
        end
    end
endmodule

module tb_top;
    reg sys_clk = 0, ca = 0, cb = 0;
    reg run_a = 1, run_b = 1;
    realtime b_half_period = 162.923339973;
    wire ma, ba, la, mb, bb, lb, da, db, qa, qb;
    wire [5:0] led;
    integer al, ar, bl, br, n;
    reg [23:0] observed_l;
    always #18.518518519 sys_clk = ~sys_clk;
    always #162.597818848 if (run_a) ca = ~ca; else ca = 0;
    initial begin
        #73;
        forever #(b_half_period) if (run_b) cb = ~cb; else cb = 0;
    end
    top #(.WINDOW_CYCLES(2700), .STARTUP_CYCLES(128), .SWAP_EDGES_B(1)) dut (
        .sys_clk(sys_clk), .pdm_clk_a(ca), .pdm_clk_b(cb), .adc_data_a(da), .adc_data_b(db),
        .adc_mclk_a(ma), .adc_bclk_a(ba), .adc_lrclk_a(la), .pdm_data_a(qa),
        .adc_mclk_b(mb), .adc_bclk_b(bb), .adc_lrclk_b(lb), .pdm_data_b(qb), .led(led)
    );
    pcm1808_model adc_a (.bclk(ba), .lrclk(la), .reset(dut.port_a.reset_audio), .data(da));
    pcm1808_model #(.LEFT(24'hc00000), .RIGHT(24'h200000)) adc_b (.bclk(bb), .lrclk(lb), .reset(dut.port_b.reset_audio), .data(db));
    always @(negedge ma) begin
        if (dut.port_a.v0 && (dut.port_a.l0 !== 24'h200000 || dut.port_a.r0 !== 24'hf00000))
            $fatal(1, "TEST 003_analog2pdm ... FAIL I2S A sign/slot L=%h R=%h", dut.port_a.l0, dut.port_a.r0);
    end
    always @(negedge mb) begin
        if (dut.port_b.v0 && (dut.port_b.l0 !== 24'he00000 || dut.port_b.r0 !== 24'h100000))
            $fatal(1, "TEST 003_analog2pdm ... FAIL I2S B sign/slot");
    end
    task check_a;
        begin
            al = 0; ar = 0;
            for (n=0; n<4096; n=n+1) begin
                @(negedge ca); al = al + qa;
                @(posedge ca); ar = ar + qa;
            end
            if (al < 2520 || al > 2600 || ar < 1750 || ar > 1830)
                $fatal(1, "TEST 003_analog2pdm ... FAIL A densities L=%0d R=%0d", al, ar);
        end
    endtask
    task check_b;
        begin
            bl = 0; br = 0;
            for (n=0; n<4096; n=n+1) begin
                @(negedge cb); bl = bl + qb;
                @(posedge cb); br = br + qb;
            end
            // B explicitly swaps L/R to test the configurable edge mapping.
            if (bl < 2264 || bl > 2344 || br < 1496 || br > 1576)
                $fatal(1, "TEST 003_analog2pdm ... FAIL B densities L=%0d R=%0d", bl, br);
        end
    endtask
    initial begin
        #2200000;
        if (led !== 6'b100100) $fatal(1, "TEST 003_analog2pdm ... FAIL lock/run/fault %b", led);
        check_a();
        check_b();
        run_a = 0;
        #30000;
        if (qa !== 0 || led[1:0] !== 2'b11 || led[4:3] !== 0)
            $fatal(1, "TEST 003_analog2pdm ... FAIL A stop isolation");
        check_b();
        run_a = 1;
        #2200000;
        check_a();
        run_b = 0;
        #30000;
        if (qb !== 0 || led[4:3] !== 2'b11 || led[1:0] !== 0)
            $fatal(1, "TEST 003_analog2pdm ... FAIL B stop isolation");
        check_a();
        run_b = 1;
        #2200000;
        if (led !== 6'b100100) $fatal(1, "TEST 003_analog2pdm ... FAIL restart %b", led);
        b_half_period = 177.154195;
        #250000;
        if (led[4:3] !== 2'b11 || led[1:0] !== 0)
            $fatal(1, "TEST 003_analog2pdm ... FAIL unsupported 2.8224 MHz");
        bl=0; br=0;
        for(n=0;n<256;n=n+1) begin
            @(negedge cb); bl=bl+qb;
            @(posedge cb); br=br+qb;
        end
        if(bl!=128 || br!=128) $fatal(1,"TEST 003_analog2pdm ... FAIL live-clock silence");
        check_a();
        $display("TEST 003_analog2pdm ... PASS");
        $finish;
    end
    initial begin
        #25000000;
        $fatal(1, "TEST 003_analog2pdm ... FAIL timeout");
    end
endmodule
