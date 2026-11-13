// Peak meter after 1/2 headroom gain; logarithmic 2 dB steps, no multipliers.
module audio_meter #(parameter integer RELEASE_FRAMES=9, PWM_DIVIDER=48) (
input wire clk, reset, sample_valid, input wire signed [23:0] left_sample,right_sample, output wire pwm);
wire [23:0] ml=left_sample[23] ? -left_sample : left_sample;
wire [23:0] mr=right_sample[23] ? -right_sample : right_sample;
wire [23:0] magnitude=ml>mr ? ml:mr;
reg [7:0] target;
always @* begin target=0;
if(magnitude >= 24'd4194) target=8'd1;
if(magnitude >= 24'd5280) target=8'd9;
if(magnitude >= 24'd6648) target=8'd17;
if(magnitude >= 24'd8369) target=8'd26;
if(magnitude >= 24'd10536) target=8'd34;
if(magnitude >= 24'd13264) target=8'd43;
if(magnitude >= 24'd16698) target=8'd51;
if(magnitude >= 24'd21021) target=8'd60;
if(magnitude >= 24'd26464) target=8'd68;
if(magnitude >= 24'd33317) target=8'd77;
if(magnitude >= 24'd41943) target=8'd85;
if(magnitude >= 24'd52803) target=8'd94;
if(magnitude >= 24'd66475) target=8'd102;
if(magnitude >= 24'd83687) target=8'd111;
if(magnitude >= 24'd105356) target=8'd119;
if(magnitude >= 24'd132636) target=8'd128;
if(magnitude >= 24'd166978) target=8'd136;
if(magnitude >= 24'd210213) target=8'd144;
if(magnitude >= 24'd264643) target=8'd153;
if(magnitude >= 24'd333165) target=8'd161;
if(magnitude >= 24'd419430) target=8'd170;
if(magnitude >= 24'd528031) target=8'd178;
if(magnitude >= 24'd664752) target=8'd187;
if(magnitude >= 24'd836873) target=8'd195;
if(magnitude >= 24'd1053561) target=8'd204;
if(magnitude >= 24'd1326355) target=8'd212;
if(magnitude >= 24'd1669782) target=8'd221;
if(magnitude >= 24'd2102131) target=8'd229;
if(magnitude >= 24'd2646426) target=8'd238;
if(magnitude >= 24'd3331653) target=8'd246;
if(magnitude >= 24'd4194303) target=8'd255;
end
reg [7:0] level;
localparam integer RW=$clog2(RELEASE_FRAMES+1), PW=$clog2(PWM_DIVIDER+1);
reg [RW-1:0] release_count;
reg [PW-1:0] pwm_div;
reg [7:0] pwm_count;
assign pwm=(level==255) || (pwm_count<level);
always @(posedge clk or posedge reset) begin
if(reset) begin level<=0; release_count<=0; pwm_div<=0; pwm_count<=0; end
else begin
if(pwm_div==PWM_DIVIDER-1) begin pwm_div<=0; pwm_count<=pwm_count+1'b1; end else pwm_div<=pwm_div+1'b1;
if(sample_valid) begin
if(target>=level) begin level<=target; release_count<=0; end
else if(release_count==RELEASE_FRAMES-1) begin level<=level-1'b1; release_count<=0; end
else release_count<=release_count+1'b1;
end end end endmodule
