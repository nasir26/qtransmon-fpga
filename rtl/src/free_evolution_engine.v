// qtransmon-fpga | Author: Nasir Ali, C-DAC Noida
//
// Free-evolution phase-rotation engine (M2, partial: free evolution only, the RWA
// drive term is not implemented yet). Implements CLAUDE.md section 3 fact 1/2: free
// evolution under H = hbar*w01*(a_dag*a + 1/2) is an exact per-level diagonal phase
// rotation, O(N), so every one of the N_LEVELS lanes below runs the same one-cycle
// complex-multiply recurrence independently and in parallel:
//
//     (re + i*im) <- (re + i*im) * (rot_re[n] - i*rot_im[n])
//
// where rot_re[n]/rot_im[n] = cos/sin(w01*(n+1/2)*dt), generated at build time into
// rot_re_rom.hex / rot_im_rom.hex by rtl/rom/gen_roms.py from config/default.yaml
// (CLAUDE.md section 7: never hand-typed). N_LEVELS/DATA_WIDTH/FRAC_BITS/ADDR_WIDTH
// come from the generated rom_params.vh, so the fixed-point format sweep (M1,
// physics/fixed_point.py) and this RTL always agree with the same config.
//
// The rotator ROM is stored at a wider precision (ROM_DATA_WIDTH/ROM_FRAC_BITS) than
// the state itself (DATA_WIDTH/FRAC_BITS). This is the fix for a V5 regression found
// when both shared one width: the dominant error source over 10,000 steps was the
// ROM's quantized rotation *angle* -- a small, fixed per-step frequency error that
// compounds ~linearly with step count, not per-step state rounding (verified in
// Python before this was written; see docs/validation.md). Widening only the ROM costs
// a fixed, small amount of extra BRAM (N_LEVELS entries regardless of width) and keeps
// the committed state storage format unchanged.
//
// State is exposed as a simple N_LEVELS-deep addressed register file (load_*/read_*)
// rather than a single wide flattened bus, both to keep the cosim testbench simple and
// because it maps naturally onto a BRAM/URAM-backed state store later. This first pass
// updates all N_LEVELS lanes combinationally in parallel every `step` cycle -- correct
// and simple (CLAUDE.md section 11: clarity over cleverness), not yet resource-optimal;
// serializing lanes over a shared multiplier to save DSPs is a later M2 decision once
// V5 passes on the full (free + drive) datapath.
`include "rom_params.vh"

module free_evolution_engine (
    input  wire                          clk,
    input  wire                          rst,

    input  wire                          load_en,
    input  wire [`ADDR_WIDTH-1:0]        load_addr,
    input  wire signed [`DATA_WIDTH-1:0] load_re,
    input  wire signed [`DATA_WIDTH-1:0] load_im,

    input  wire                          step,

    input  wire [`ADDR_WIDTH-1:0]        read_addr,
    output wire signed [`DATA_WIDTH-1:0] read_re,
    output wire signed [`DATA_WIDTH-1:0] read_im
);

    localparam N_LEVELS       = `N_LEVELS;
    localparam DATA_WIDTH     = `DATA_WIDTH;
    localparam FRAC_BITS      = `FRAC_BITS;
    localparam ADDR_WIDTH     = `ADDR_WIDTH;
    localparam ROM_DATA_WIDTH = `ROM_DATA_WIDTH;
    localparam ROM_FRAC_BITS  = `ROM_FRAC_BITS;
    localparam PROD_WIDTH     = DATA_WIDTH + ROM_DATA_WIDTH;
    localparam SUM_WIDTH      = PROD_WIDTH + 1;

    reg signed [ROM_DATA_WIDTH-1:0] rot_re_rom [0:N_LEVELS-1];
    reg signed [ROM_DATA_WIDTH-1:0] rot_im_rom [0:N_LEVELS-1];

    initial begin
        $readmemh("rtl/rom/rot_re_rom.hex", rot_re_rom);
        $readmemh("rtl/rom/rot_im_rom.hex", rot_im_rom);
    end

    reg signed [DATA_WIDTH-1:0] state_re [0:N_LEVELS-1];
    reg signed [DATA_WIDTH-1:0] state_im [0:N_LEVELS-1];

    localparam signed [SUM_WIDTH-1:0] SAT_HI = (1 <<< (DATA_WIDTH-1)) - 1;
    localparam signed [SUM_WIDTH-1:0] SAT_LO = -(1 <<< (DATA_WIDTH-1));

    genvar i;
    generate
        for (i = 0; i < N_LEVELS; i = i + 1) begin : LANES
            wire signed [ROM_DATA_WIDTH-1:0] rr = rot_re_rom[i];
            wire signed [ROM_DATA_WIDTH-1:0] ri = rot_im_rom[i];

            // one rounding step on the full sum, matching physics/fixed_point.py's
            // quantize(re*rot_re + im*rot_im, ...) -- not two separate roundings.
            // state (DATA_WIDTH, Q.FRAC_BITS) x rom (ROM_DATA_WIDTH, Q.ROM_FRAC_BITS)
            // -> product is scaled by 2^(FRAC_BITS+ROM_FRAC_BITS); shifting back down
            // by ROM_FRAC_BITS (not FRAC_BITS) leaves it at the state's own scale.
            wire signed [PROD_WIDTH-1:0] prod_rr_re = state_re[i] * rr;
            wire signed [PROD_WIDTH-1:0] prod_ri_im = state_im[i] * ri;
            wire signed [PROD_WIDTH-1:0] prod_rr_im = state_im[i] * rr;
            wire signed [PROD_WIDTH-1:0] prod_ri_re = state_re[i] * ri;

            wire signed [SUM_WIDTH-1:0] sum_re = prod_rr_re + prod_ri_im;
            wire signed [SUM_WIDTH-1:0] sum_im = prod_rr_im - prod_ri_re;

            // round-to-nearest, ties away from zero (differs from numpy's round-half-
            // to-even used in the M1 Python model, but ties only occur at exact
            // fractional-grid coincidences, which cos/sin of an irrational angle never
            // hits -- negligible for V5's infidelity budget).
            wire signed [SUM_WIDTH-1:0] rounded_re = (sum_re + (1 <<< (ROM_FRAC_BITS-1))) >>> ROM_FRAC_BITS;
            wire signed [SUM_WIDTH-1:0] rounded_im = (sum_im + (1 <<< (ROM_FRAC_BITS-1))) >>> ROM_FRAC_BITS;

            wire signed [DATA_WIDTH-1:0] sat_re =
                (rounded_re > SAT_HI) ? SAT_HI[DATA_WIDTH-1:0] :
                (rounded_re < SAT_LO) ? SAT_LO[DATA_WIDTH-1:0] :
                rounded_re[DATA_WIDTH-1:0];
            wire signed [DATA_WIDTH-1:0] sat_im =
                (rounded_im > SAT_HI) ? SAT_HI[DATA_WIDTH-1:0] :
                (rounded_im < SAT_LO) ? SAT_LO[DATA_WIDTH-1:0] :
                rounded_im[DATA_WIDTH-1:0];

            always @(posedge clk) begin
                if (rst) begin
                    state_re[i] <= {DATA_WIDTH{1'b0}};
                    state_im[i] <= {DATA_WIDTH{1'b0}};
                end else if (load_en && (load_addr == i[ADDR_WIDTH-1:0])) begin
                    state_re[i] <= load_re;
                    state_im[i] <= load_im;
                end else if (step) begin
                    state_re[i] <= sat_re;
                    state_im[i] <= sat_im;
                end
            end
        end
    endgenerate

    assign read_re = state_re[read_addr];
    assign read_im = state_im[read_addr];

endmodule
