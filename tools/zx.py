#!/usr/bin/env python3
"""Run the Spectrum original headless, on SkoolKit's Z80 simulator.

    .venv/bin/python tools/zx.py '<script>' [prefix] [--snap build/ce2.z80] [--map FILE]

The Spectrum counterpart of tools/play.mjs: the same script language, so a
behaviour can be checked on the original and on the port with one script.
Steps, comma-separated:

    1.5            run 1.5 seconds (50 frames a second)
    f10            run exactly 10 frames
    SPACE:tap      press and release (0.1s); SPACE:0.5 holds for 0.5s
    Q:down / Q:up  hold or release a key
    !name          screenshot to <prefix>name.png (the 256x192 screen, 2x)
    >name          save a .z80 snapshot to <prefix>name.z80
    ?addr:n        print n bytes at addr (decimal, &hex or 0xhex)
    =addr:v1/v2    poke bytes
    @addr          run until PC reaches addr (gives up after 30s)

Keys are the Spectrum's own names: A-Z, 0-9, SPACE, ENTER, CAPS, SYM, and
KL KR KU KD KF for a Kempston joystick.

Needs the project venv (SkoolKit, Pillow): see README.md.
"""
import argparse
import sys

from PIL import Image
from skoolkit import CSimulator
from skoolkit.simulator import Simulator
from skoolkit.simutils import PC, T, from_snapshot, get_state
from skoolkit.snapshot import Snapshot, write_snapshot

FRAME = 69888  # T-states in a 48K frame

# Half-row (the address line that selects it, A8..A15) and bit, per key.
MATRIX = [
    ["CAPS", "Z", "X", "C", "V"],
    ["A", "S", "D", "F", "G"],
    ["Q", "W", "E", "R", "T"],
    ["1", "2", "3", "4", "5"],
    ["0", "9", "8", "7", "6"],
    ["P", "O", "I", "U", "Y"],
    ["ENTER", "L", "K", "J", "H"],
    ["SPACE", "SYM", "M", "N", "B"],
]
KEYS = {k: (row, bit) for row, ks in enumerate(MATRIX) for bit, k in enumerate(ks)}
KEMPSTON = {"KR": 1, "KL": 2, "KD": 4, "KU": 8, "KF": 16}

N, B = 0xD7, 0xFF
PALETTE = [(0, 0, 0), (0, 0, N), (N, 0, 0), (N, 0, N), (0, N, 0), (0, N, N), (N, N, 0), (N, N, N),
           (0, 0, 0), (0, 0, B), (B, 0, 0), (B, 0, B), (0, B, 0), (0, B, B), (B, B, 0), (B, B, B)]


def parse_num(s):
    s = s.strip()
    if s.startswith("&"):
        return int(s[1:], 16)
    return int(s, 0)


def screen_image(mem, scale=2):
    """The display as the Spectrum shows it (flash drawn unflashed)."""
    im = Image.new("RGB", (256, 192))
    px = im.load()
    for y in range(192):
        row = 16384 + ((y & 0xC0) << 5) + ((y & 7) << 8) + ((y & 0x38) << 2)
        for cx in range(32):
            attr = mem[22528 + (y // 8) * 32 + cx]
            bright = (attr & 0x40) >> 3
            ink = PALETTE[(attr & 7) | bright]
            paper = PALETTE[((attr >> 3) & 7) | bright]
            b = mem[row + cx]
            for bit in range(8):
                px[cx * 8 + bit, y] = ink if b & (0x80 >> bit) else paper
    if scale != 1:
        im = im.resize((256 * scale, 192 * scale), Image.NEAREST)
    return im


class Spectrum:
    def __init__(self, snap, exec_map=None):
        snapshot = Snapshot.get(snap)
        cls = CSimulator or Simulator
        self.sim = from_snapshot(cls, snapshot, config={"fast_djnz": False, "fast_ldir": False})
        self.sim.set_tracer(self)
        self.rows = [0] * 8
        self.kempston = 0
        self.border = snapshot.border
        self.outfe = snapshot.outfe  # get_state() wants it for a snapshot
        self.exec_map = exec_map

    @property
    def mem(self):
        return self.sim.memory

    # Called by the simulator for IN.
    def read_port(self, registers, port):
        if port & 1 == 0:
            sel = (port >> 8) ^ 0xFF
            v = 0
            for i in range(8):
                if sel & (1 << i):
                    v |= self.rows[i]
            return (v ^ 0xFF) & 0xBF  # bit 6 is the EAR input: silence
        if port & 0xFF == 0x1F:
            return self.kempston
        return 0xFF

    def write_port(self, registers, port, value, offset):
        if port & 1 == 0:
            self.border = value & 7
            self.outfe = value

    def run_tstates(self, n, stop=None):
        regs = self.sim.registers
        end = regs[T] + n
        self.sim.trace(regs[PC], stop, 0, end, 1, None, self.exec_map, None, None, None)
        return regs[PC]

    def frames(self, n):
        self.run_tstates(n * FRAME)

    def key(self, name, down):
        if name in KEMPSTON:
            bit = KEMPSTON[name]
            self.kempston = (self.kempston | bit) if down else (self.kempston & ~bit)
            return
        row, bit = KEYS[name]
        if down:
            self.rows[row] |= 1 << bit
        else:
            self.rows[row] &= ~(1 << bit)

    def save(self, path):
        ram, registers, state, machine = get_state(self.sim)
        write_snapshot(path, ram, registers, state, machine)


def run_script(spec, script, prefix):
    for raw in script.split(","):
        step = raw.strip()
        if not step:
            continue
        if step.startswith("!"):
            path = f"{prefix}{step[1:]}.png"
            screen_image(spec.mem).save(path)
            print("SHOT", path)
        elif step.startswith(">"):
            path = f"{prefix}{step[1:]}.z80"
            spec.save(path)
            print("SNAP", path)
        elif step.startswith("?"):
            addr, _, n = step[1:].partition(":")
            a = parse_num(addr)
            data = [spec.mem[a + i] for i in range(int(n or "1"))]
            print(addr, " ".join(f"{b:02x}" for b in data))
        elif step.startswith("="):
            addr, _, vals = step[1:].partition(":")
            a = parse_num(addr)
            for i, v in enumerate(vals.split("/")):
                spec.mem[a + i] = parse_num(v) & 0xFF
        elif step.startswith("@"):
            target = parse_num(step[1:])
            pc = spec.run_tstates(30 * 50 * FRAME, stop=target)
            print("BREAK", step[1:], "hit" if pc == target else "timeout")
        elif step[0] == "f" and step[1:].isdigit():
            spec.frames(int(step[1:]))
        elif step.replace(".", "", 1).isdigit():
            spec.run_tstates(round(float(step) * 50 * FRAME))
        else:
            key, _, action = step.partition(":")
            action = action or "tap"
            if action == "down":
                spec.key(key, True)
            elif action == "up":
                spec.key(key, False)
            else:
                secs = 0.1 if action == "tap" else float(action)
                spec.key(key, True)
                spec.run_tstates(round(secs * 50 * FRAME))
                spec.key(key, False)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("script")
    ap.add_argument("prefix", nargs="?", default="shots/zx_")
    ap.add_argument("--snap", default="build/ce2.z80")
    ap.add_argument("--map", help="write the addresses executed, one per line, to FILE")
    args = ap.parse_args()
    exec_map = set() if args.map else None
    spec = Spectrum(args.snap, exec_map)
    run_script(spec, args.script, args.prefix)
    if args.map:
        with open(args.map, "w") as f:
            for a in sorted(exec_map):
                f.write(f"{a:04X}\n")
        print("MAP", args.map, len(exec_map))


if __name__ == "__main__":
    sys.exit(main())
