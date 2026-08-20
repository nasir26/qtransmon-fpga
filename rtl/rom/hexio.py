"""Two's-complement <-> real-valued hex file I/O shared by ROM generation and the M2
cosim harness (cosim/run_v5_cosim.py), so the RTL <-> Python numeric convention is
defined in exactly one place. Format: one line per level, data_width/4 hex digits,
the raw two's-complement bit pattern -- directly $readmemh-compatible.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np


def real_to_hex_lines(values_real: np.ndarray, frac_bits: int, data_width: int) -> list:
    """Caller must have already quantized/saturated values_real to the target Q-format
    (see physics.fixed_point.quantize); this only packs the bit pattern."""
    scale = 2**frac_bits
    ints = np.round(values_real * scale).astype(np.int64)
    mask = (1 << data_width) - 1
    hex_digits = data_width // 4
    return [format(int(v) & mask, f"0{hex_digits}x") for v in ints]


def write_hex_file(path: Path, values_real: np.ndarray, frac_bits: int, data_width: int) -> None:
    path.write_text("\n".join(real_to_hex_lines(values_real, frac_bits, data_width)) + "\n")


def read_hex_file_as_real(path: Path, frac_bits: int, data_width: int) -> np.ndarray:
    lines = [line.strip() for line in path.read_text().splitlines() if line.strip()]
    ints = np.array([int(line, 16) for line in lines], dtype=np.int64)
    sign_bit = 1 << (data_width - 1)
    ints = np.where(ints & sign_bit, ints - (1 << data_width), ints)
    return ints.astype(float) / (2**frac_bits)
