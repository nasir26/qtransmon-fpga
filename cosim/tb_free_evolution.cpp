// qtransmon-fpga | Author: Nasir Ali, C-DAC Noida
//
// M2 cosim driver (V5, partial: free evolution only) for free_evolution_engine.v.
// Loads an initial per-level state from two hex files (re/im, one two's-complement
// value per line -- see rtl/rom/hexio.py, which both rtl/rom/gen_roms.py and
// cosim/run_v5_cosim.py use so the RTL and Python sides agree on the bit format),
// steps the engine N_STEPS times, and writes the final state back out the same way.
// Verilator stands in for Vivado xsim here (not available in any environment this
// project has run in -- see docs/validation.md); it is explicitly named as an
// acceptable cosim tool in CLAUDE.md's own repo layout (section 4: "cosim/
// Verilator/xsim harness").
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#include <vector>

#include "Vfree_evolution_engine.h"
#include "verilated.h"

static std::vector<uint32_t> read_hex_file(const std::string &path) {
    std::ifstream f(path);
    if (!f) {
        fprintf(stderr, "cannot open %s\n", path.c_str());
        exit(1);
    }
    std::vector<uint32_t> values;
    std::string line;
    while (std::getline(f, line)) {
        if (line.empty()) continue;
        values.push_back(static_cast<uint32_t>(std::stoul(line, nullptr, 16)));
    }
    return values;
}

int main(int argc, char **argv) {
    if (argc != 6) {
        fprintf(stderr,
                "usage: %s state_in_re.hex state_in_im.hex n_steps "
                "state_out_re.hex state_out_im.hex\n",
                argv[0]);
        return 1;
    }
    Verilated::commandArgs(argc, argv);

    const std::string in_re_path = argv[1];
    const std::string in_im_path = argv[2];
    const int n_steps = std::atoi(argv[3]);
    const std::string out_re_path = argv[4];
    const std::string out_im_path = argv[5];

    const auto in_re = read_hex_file(in_re_path);
    const auto in_im = read_hex_file(in_im_path);
    if (in_re.size() != in_im.size()) {
        fprintf(stderr, "state_in_re/state_in_im length mismatch\n");
        return 1;
    }
    const int n_levels = static_cast<int>(in_re.size());

    Vfree_evolution_engine top;

    auto tick = [&]() {
        top.clk = 0;
        top.eval();
        top.clk = 1;
        top.eval();
    };

    top.rst = 1;
    top.load_en = 0;
    top.step = 0;
    tick();
    top.rst = 0;

    for (int i = 0; i < n_levels; ++i) {
        top.load_en = 1;
        top.load_addr = i;
        top.load_re = in_re[i];
        top.load_im = in_im[i];
        tick();
    }
    top.load_en = 0;

    top.step = 1;
    for (int s = 0; s < n_steps; ++s) {
        tick();
    }
    top.step = 0;

    // "%04x" assumes a 16-bit DATA_WIDTH, true for all three Q-formats in
    // physics/fixed_point.py's Q_FORMATS today (Q1.15/Q2.14/Q4.12 each sum to 16
    // bits); a differently-sized future format would need this width made a runtime
    // argument instead of hardcoded here.
    std::ofstream out_re_f(out_re_path);
    std::ofstream out_im_f(out_im_path);
    for (int i = 0; i < n_levels; ++i) {
        top.read_addr = i;
        top.eval();  // combinational read
        char buf[16];
        snprintf(buf, sizeof(buf), "%04x", static_cast<unsigned>(top.read_re) & 0xFFFFu);
        out_re_f << buf << "\n";
        snprintf(buf, sizeof(buf), "%04x", static_cast<unsigned>(top.read_im) & 0xFFFFu);
        out_im_f << buf << "\n";
    }

    top.final();
    return 0;
}
