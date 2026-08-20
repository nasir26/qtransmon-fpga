# CLAUDE.md

Operating contract for Claude Code in this repository. Read this fully before touching
any file. If an instruction here conflicts with a request in the chat, say so explicitly
rather than silently picking one.

Author: Nasir Ali, C-DAC Noida.

---

## 1. What this project is

A hardware-accelerated simulator for superconducting-qubit circuit Hamiltonians on a
Xilinx Alveo U55C, built along two independent routes that are compared against each
other:

- **Direct route.** A native-Verilog datapath that propagates the truncated bosonic
  state vector directly, exploiting the fact that the Hamiltonians involved are diagonal
  plus bidiagonal in their natural bases, so every operator application is O(N).
- **Circuit route.** The same physics encoded onto qubits and simulated as a gate-based
  circuit on the existing `fpga_rtl` statevector backend.

A machine-learned coarse-step propagator sits on top of the direct route, replacing K
fine Trotter steps with one inference.

The scientific deliverable is the crossover study: for matched accuracy, where does each
route win, in wall-clock time, in FPGA resources, and in qubit count.

## 2. Physics, stated once, authoritatively

Everything in this repo derives from these. Any constant appearing in code must trace
back to one of them.

Linear LC oscillator (starting point, `mode=lc`):

    H = Q^2/(2C) + (1/2)*C*w01^2*Phi^2
    w01 = 1/sqrt(L*C),  Z0 = sqrt(L/C)
    Q   = i*sqrt(hbar/(2*Z0))*(a_dag - a)
    Phi =   sqrt(hbar*Z0/2)*(a_dag + a)
    =>  H = hbar*w01*(a_dag*a + 1/2)

Transmon (`mode=transmon`):

    H = 4*E_C*(n - n_g)^2 - E_J*cos(phi),   [phi, n] = i
    E_C = e^2/(2*C_sigma),  E_J = I_c*phi_0

Duffing reduction (`mode=duffing`):

    H ~= hbar*w01*a_dag*a + (alpha/2)*a_dag*a_dag*a*a
    w01 = (sqrt(8*E_J*E_C) - E_C)/hbar,  alpha = -E_C/hbar

Drive, from the voltage source in the original circuit:

    H_d(t) = -(C_d/C_sigma)*V(t)*Q,  V(t) = V0*cos(w_d*t)
    RWA form: H = hbar*delta*a_dag*a + (hbar*Omega/2)*(a + a_dag),  delta = w01 - w_d

Frame (lab or rotating) is a config flag, never a hardcoded assumption.

## 3. The structural facts that drive every design decision

These are the reason this project is cheap in hardware. Do not write code that ignores
them, and do not "generalize" them away into a dense matrix-vector product.

1. In the Fock basis, `a|n> = sqrt(n)|n-1>` and `a_dag|n> = sqrt(n+1)|n+1>`. The
   Hamiltonian is diagonal; the drive is strictly bidiagonal. O(N) per step, with
   `sqrt(n)` coefficients in a BRAM ROM.
2. Free evolution under `a_dag*a` is an exact diagonal phase rotation. Fock populations
   are invariant. This is a built-in correctness oracle, and it must be checked in CI.
3. The Kerr term is diagonal. It costs one extra ROM of `n*(n-1)/2`. Nearly free.
4. In the charge basis, `cos(phi)` is exactly the charge-shift operator, so the transmon
   Hamiltonian is tridiagonal. The transmon datapath is a small extension of the LC
   datapath, not a rewrite.
5. In the binary qubit encoding, the number operator is `sum_k 2^k*(I - Z_k)/2`, so
   digitized free evolution is exact, zero Trotter error, and costs exactly m RZ gates.
6. Charge and phase are related by an exact QFT on a truncated periodic lattice. This is
   why the split-operator construction is exact per term and the Josephson nonlinearity
   collapses to a single diagonal phase oracle.

If a proposed change makes any of 1 to 6 no longer hold, stop and flag it.

## 4. Repository layout

    physics/          golden model (NumPy), QuTiP cross-check, analytic references
    ml/               dataset generation, training, QAT, fixed-point weight export
    rtl/              native Verilog kernel, testbenches, ROM generators
    hls/              host shell and data movement ONLY, never compute
    cosim/            Verilator/xsim harness comparing RTL against golden per-step
    circuit/          encodings, Pauli decomposition, Trotter and QFT builders
    circuit/backend/  FPGAStatevectorBackend integration
    bench/            latency, throughput, resource, fidelity reports
    bench/crossover/  the direct-vs-circuit comparison study
    config/           single source of truth for physical parameters
    docs/             full derivation, HLD, LLD
    paper/            Journal of Supercomputing manuscript

## 5. Build order, gated

Do not start a milestone until the previous one passes its tests. Report status against
this list at the start of every session.

    M0  golden model + validations V1-V4
    M1  fixed-point Python model, Q-format sweep
    M2  RTL Trotter datapath + cosim (V5)
    M3  ML dataset generation + training (V6)
    M4  QAT + weight export
    M5  NN inference block in RTL
    M6  integration, benchmarking, docs
    M7  circuit encoders + round-trip tests
    M8  Construction A (Pauli/Trotter) on a software backend
    M9  Construction B (QFT split-operator)
    M10 both constructions on FPGAStatevectorBackend (V11)
    M11 transmon + multi-mode (dispersive readout)
    M12 crossover study + paper results

## 6. Validation gates (CI must run all of these)

    V1  Truncated spectrum matches hbar*w01*(n + 1/2) to 1e-10 for n < N-2
    V2  Free evolution: |c_n|^2 exactly constant, phases linear in t
    V3  Coherent state traces the classical LC trajectory, Mandel Q = 0
    V4  Resonant drive on |0> gives |alpha(t)| = Omega*t/2
    V5  RTL vs golden: infidelity < 1e-4 after 10,000 fixed-point steps
    V6  ML surrogate: mean infidelity < 1e-3 on 1,000 held-out trajectories
    V7  Wigner function matches QuTiP
    V8  Encoded free evolution exact to FP64 (RZ-only, zero Trotter error)
    V9  Constructions A and B agree with the direct engine: < 1e-6 harmonic,
        < 1e-4 transmon
    V10 Trotter error scales as dt^2 (first order) and dt^3 (second order), exponent
        confirmed by fit
    V11 All circuits run end to end on FPGAStatevectorBackend and match Aer to FP64
    V12 Transmon: E_01 matches sqrt(8*E_J*E_C) - E_C to 1%; charge dispersion decays
        exponentially in sqrt(E_J/E_C)
    V13 DRAG reduces |2> leakage by >= 1 order of magnitude versus a bare Gaussian

Truncation guard: if population in the top two Fock levels exceeds 1e-6, the run is
invalid. Fail loudly, do not silently continue.

## 7. Hardware and numerical conventions

- Target: Alveo U55C, Vitis/Vivado flow.
- Compute kernels are **native Verilog**. HLS is permitted only for the host-side data
  movement shell. Never move compute into HLS to save effort.
- Fixed point: default Q2.14 for amplitudes, set by `localparam`, swept over
  Q1.15 / Q2.14 / Q4.12 with fidelity and DSP/LUT cost reported for each.
- The state vector for N <= 64 lives in URAM/BRAM. Do not touch HBM for the state.
  HBM is for trajectory snapshot streaming and batched parameter sweeps only.
- Pipeline the bidiagonal/tridiagonal update to II = 1.
- ROMs (`sqrt(n)`, `n*(n-1)/2`, per-level phase increments) are generated at build time
  from `config/`, never hand-typed.
- P parallel engines for parameter sweeps, P configurable; report trajectories/second.
- Default physical parameters live in `config/default.yaml`: w01/2pi = 5 GHz,
  Z0 = 50 Ohm, dt = 1 ps, Omega/2pi = 50 MHz, E_J/E_C = 60.

## 8. Environment notes

- `iverilog` is not installed on the target machine. RTL simulation uses **Vivado xsim**.
- Encrypted Xilinx FP IP is not available in simulation; use behavioral FP64 models in
  `rtl/sim/fp64_sim_models.v`, mirroring the approach already proven in prior work.
- HBM word addressing: 16-byte words, address bits [15:4].
- Known prior pitfalls to avoid re-discovering: HBM AXI port naming, `dbg_hub` clock
  needing an explicit BUFG, unused AXI port tie-offs.

## 9. Interaction with the `fpga_rtl` backend

The circuit route targets the existing native-Verilog statevector simulator: FP64,
8 HBM banks, 29-qubit maximum, Qiskit `BackendV2` subclass `FPGAStatevectorBackend`,
no CPU fallback, 17-gate basis.

- Compile every circuit down to that basis. If a construction needs a gate outside it,
  decompose explicitly and record the decomposition cost. Never assume a gate exists.
- Inside the `fpga_rtl` repo, the names "Qniverse" and "NQM" must not appear. The sole
  identifiers there are Nasir Ali and C-DAC Noida, and every new file carries:
      // FPGA Quantum Statevector Simulator | Author: Nasir Ali, C-DAC Noida
- Treat `fpga_rtl` as an external dependency. Do not refactor it to suit this project;
  if it needs a change, raise it separately.

## 10. Honesty rules (non-negotiable)

- **Never write a number into a table, plot, README, or the paper that did not come from
  a run that actually executed.** Unmeasured entries stay as `TBD`. If asked for results
  that do not exist yet, say they do not exist.
- Where ML does not help, say so. For the purely harmonic case the exact propagator is
  analytic, so the surrogate there is a methodology testbed, not a speedup. The claim
  only becomes real in the transmon/Duffing case, and only at matched fidelity.
- If the crossover study shows the circuit route losing for a single mode, report that.
  A negative result cleanly measured is publishable; a flattering one is not.
- Report quantization-induced fidelity loss separately from surrogate-induced fidelity
  loss. Do not merge them into one number.
- Failure-mode analysis is mandatory for the ML sections: state where the surrogate
  degrades (large Omega, large detuning, high photon number).

## 11. Style

- Every numerical constant traces to a physical parameter. No magic numbers.
- Prefer clarity over cleverness in RTL. This code will be read and extended by a human.
- Python: type hints, `numpy` for the golden model, `pytest` for all validations, no
  notebook-only logic.
- Commit messages: imperative mood, one logical change each, referencing the milestone
  (`M2: pipeline bidiagonal update to II=1`).
- Do not add dependencies without saying why in the commit message.
- Docstrings on physics functions cite the equation from section 2 they implement.

## 12. Session protocol

1. State which milestone you are on and what the last passing gate was.
2. Propose the plan before writing code for anything spanning more than one file.
3. Run the validation suite after every change that touches physics or RTL.
4. End by reporting: tests passed, tests failed, what is now `TBD`, next step.
