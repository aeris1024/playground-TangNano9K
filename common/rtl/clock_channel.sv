module clock_channel #(
    parameter integer WINDOW_CYCLES = 27000,
    parameter integer STARTUP_CYCLES = 3072000,
    parameter integer STOP_CYCLES = 216
) (
    input wire sys_clk,
    input wire reference_clk,
    output wire audio_clk,
    output wire locked,
    output wire clock_good,
    output reg clock_present,
    output wire reset_audio,
    output wire ready,
    output wire [7:0] phase,
    output wire bclk,
    output wire lrclk
);
    initial clock_present = 1'b0;
    reg good_state = 1'b0;
    reg ready_state = 1'b0;
    reg [7:0] phase_state = 8'b0;
    assign clock_good = good_state;
    assign ready = ready_state;
    assign phase = phase_state;
    localparam integer EXPECTED_EDGES = (WINDOW_CYCLES * 3072) / 27000;
    localparam integer EDGE_MARGIN = EXPECTED_EDGES / 100 + 2;
    reg [2:0] reference_sync = 3'b0;
    reg [15:0] window_count = 16'b0;
    reg [15:0] edge_count = 16'b0;
    reg [15:0] silent_count = 16'b0;
    wire reference_rising = reference_sync[1] && !reference_sync[2];

    always @(posedge sys_clk) begin
        reference_sync <= {reference_sync[1:0], reference_clk};
        if (reference_rising) begin
            silent_count <= 0;
            clock_present <= 1'b1;
            edge_count <= edge_count + 1'b1;
        end else if (silent_count < STOP_CYCLES) begin
            silent_count <= silent_count + 1'b1;
        end
        if (silent_count >= STOP_CYCLES) begin
            good_state <= 1'b0;
            clock_present <= 1'b0;
        end
        if (window_count == WINDOW_CYCLES - 1) begin
            window_count <= 0;
            edge_count <= 0;
            good_state <= (edge_count >= EXPECTED_EDGES - EDGE_MARGIN)
                       && (edge_count <= EXPECTED_EDGES + EDGE_MARGIN)
                       && (silent_count < STOP_CYCLES);
        end else window_count <= window_count + 1'b1;
    end

    audio_pll clock_source (.reference_clk(reference_clk), .reset(!clock_good),
                            .audio_clk(audio_clk), .locked(locked));
    wire reset_request = !clock_good || !locked;
    reg [2:0] release_sync = 3'b0;
    always @(posedge audio_clk or posedge reset_request) begin
        if (reset_request) release_sync <= 3'b0;
        else release_sync <= {release_sync[1:0], 1'b1};
    end
    assign reset_audio = !release_sync[2];
    reg [21:0] startup_count = 22'b0;
    always @(posedge audio_clk or posedge reset_audio) begin
        if (reset_audio) begin
            phase_state <= 0;
            startup_count <= 0;
            ready_state <= 1'b0;
        end else begin
            phase_state <= phase + 1'b1;
            if (startup_count < STARTUP_CYCLES) startup_count <= startup_count + 1'b1;
            else ready_state <= 1'b1;
        end
    end
    assign bclk = phase[1];
    assign lrclk = phase[7];
endmodule
