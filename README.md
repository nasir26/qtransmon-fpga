# qtransmon-fpga

FPGA-accelerated simulation of superconducting circuit Hamiltonians, from the quantized
LC oscillator through to the driven transmon, along two independent routes that are
measured against each other:

1. **Direct bosonic datapath.** Native Verilog on a Xilinx Alveo U55C, exploiting the
   diagonal-plus-bidiagonal structure of the Hamiltonian in the Fock and charge bases so
   that each time step is O(N) rather than O(N^2).
2. **Gate-based circuit route.** The same physics encoded onto qubits and simulated as a
   quantum circuit on an existing native-Verilog FP64 statevector backend, using both a
   Pauli/Trotter construction and a QFT split-operator construction.

A machine-learned coarse-step propagator sits on top of route 1, replacing K fine Trotter
steps with a single quantized inference.

The point of the project is the **crossover study**: at matched accuracy, which route
wins, at what truncation, and at how many coupled modes.

## Physics implemented

| Mode | Hamiltonian |
| --- | --- |
| `lc` | `H = Q^2/(2C) + (1/2) C w01^2 Phi^2  =  hbar w01 (a†a + 1/2)` |
| `transmon` | `H = 4 E_C (n - n_g)^2 - E_J cos(phi)` |
| `duffing` | `H = hbar w01 a†a + (alpha/2) a†a†aa` |

with a capacitively coupled drive `H_d = -(C_d/C_sigma) V(t) Q`, in either the lab frame
or the rotating frame.

## Status

No benchmark or fidelity results have been produced yet. Every table in `bench/` and
every results cell in `paper/` is marked `TBD` until a run actually produces the number.
See `CLAUDE.md` section 10.

Milestones: see `CLAUDE.md` section 5. Current: **M0 passing** (`lc` mode golden model,
V1-V4 green under `physics/tests/`; `transmon`/`duffing` remain gated to M11). Next: M1
(fixed-point Python model, Q-format sweep).

## Layout

    physics/   golden model and analytic references
    ml/        dataset generation, training, quantization-aware training, weight export
    rtl/       native Verilog kernel, testbenches, ROM generators
    hls/       host shell and data movement only
    cosim/     RTL vs golden model co-simulation harness
    circuit/   qubit encodings, circuit builders, statevector backend integration
    bench/     performance, resource, and fidelity reports
    config/    single source of truth for physical parameters
    docs/      derivations, HLD, LLD
    paper/     Journal of Supercomputing manuscript

## Requirements

- Vivado / Vitis (xsim for RTL simulation; `iverilog` is not used)
- Xilinx Alveo U55C
- Python 3.10+, NumPy, QuTiP, Qiskit, PyTorch

## Author

Nasir Ali, C-DAC Noida.

## License

MIT. See `LICENSE`.
