`timescale 1ns/1ps
module tb_top;
reg sys=0, ca=0, cb=0;
always #18.518518519 sys=~sys;
always #162.760416667 ca=~ca;
initial begin #73; forever #162.923339973 cb=~cb; end
wire qa,qb; wire [5:0] led;
top #(.WINDOW_CYCLES(2700),.STARTUP_CYCLES(128)) dut (
.sys_clk(sys),.pdm_clk_a(ca),.pdm_clk_b(cb),.adc_data_a(1'b0),.adc_data_b(1'b1),
.adc_mclk_a(),.adc_bclk_a(),.adc_lrclk_a(),.adc_mclk_b(),.adc_bclk_b(),.adc_lrclk_b(),
.pdm_data_a(qa),.pdm_data_b(qb),.led(led));
defparam dut.port_a.receive.GAP_FRAMES=16;
defparam dut.port_b.receive.GAP_FRAMES=16;
defparam dut.port_a.receive.FIRST_TONE=1;
defparam dut.port_b.receive.FIRST_TONE=1;
// Independent fast source check verifies all six frequencies against real sine.
reg fast=0; always #5 fast=~fast;
reg rst=1; wire v; wire signed [23:0] l,r;
i2s_receive #(.TONE_FRAMES(960),.GAP_FRAMES(16)) source (
.clk(fast),.reset(rst),.ready(1'b1),.adc_data(1'b1),.phase(8'd225),.sample_valid(v),.pcm_l(l),.pcm_r(r));
integer ti,n,step,angle,expected; real x;
initial begin
 repeat(3) @(negedge fast); rst=0;
 for(ti=0;ti<6;ti=ti+1) begin
  case(ti) 0:step=1; 1:step=10; 2:step=50; 3:step=100; 4:step=150; 5:step=200; endcase
  repeat(16) begin @(negedge fast); if(l!==0 || r!==0 || !v) $fatal(1,"gap"); end
  angle=0;
  for(n=0;n<960;n=n+1) begin
   @(negedge fast);
   x=$sin(6.283185307179586*angle/480)*8388607*0.12589254117941673;
   expected=$rtoi(x>=0 ? x+0.5 : x-0.5); expected=expected>>>1;
   if(l!==r || $abs($signed(l)-expected)>1 || !v) $fatal(1,"tone %d sample %d",ti,n);
   angle=(angle+step)%480;
  end
 end
end
integer i; real sa=0, caa=0, sb=0, cbb=0, aa,ab;
initial begin
 #2500000;
 if(led!==6'b100100) $fatal(1,"status %b",led);
 fork
  begin
   for(i=0;i<6144;i=i+1) begin
    @(negedge ca);
    if(qa!==0 && qa!==1) $fatal(1,"X A");
    sa=sa+(qa ? 1.0:-1.0)*$sin(6.283185307179586*i/3072);
    caa=caa+(qa ? 1.0:-1.0)*$cos(6.283185307179586*i/3072);
   end
  end
  begin : check_b
   integer j;
   for(j=0;j<6144;j=j+1) begin
    @(negedge cb);
    if(qb!==0 && qb!==1) $fatal(1,"X B");
    sb=sb+(qb ? 1.0:-1.0)*$sin(6.283185307179586*j/3072);
    cbb=cbb+(qb ? 1.0:-1.0)*$cos(6.283185307179586*j/3072);
   end
  end
 join
 aa=2*$sqrt(sa*sa+caa*caa)/6144; ab=2*$sqrt(sb*sb+cbb*cbb)/6144;
 if(aa<0.057 || aa>0.069 || ab<0.057 || ab>0.069) $fatal(1,"PDM amplitude %f %f",aa,ab);
 if(led!==6'b100100) $fatal(1,"fault %b",led);
 $display("TEST 004_pdm_tone ... PASS amplitude A=%f B=%f",aa,ab); $finish;
end
initial begin #10000000; $fatal(1,"timeout"); end
endmodule
