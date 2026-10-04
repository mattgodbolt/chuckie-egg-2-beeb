# Journal

What worked, what I found, what went wrong — in the order it happened.

## 2026-10-04: setting up

### Looking around first

- **Sibling projects.** `../beeb-scorched-earth` is the template for the
  repo: baron, a `Makefile`, `tools/beeb.mjs` (a client for the published
  `jsbeeb-mcp` server over stdio) and `tools/play.mjs` (key scripts with
  `!shot` capture points), `CLAUDE.md` holding the gotchas. `../daredevil-demis`
  and `../frogman` taught the same habits in beebasm: dump state rather than
  squint at screenshots; keep the OS out of the game loop; hook IRQ1V
  for vsync. `../pipeline-disasm` is the disassembly-to-baron discipline.
- **kieranhj/beeb-port-kit** is the method from two C64 ports (Paradroid,
  Edge Grinder). The rules I'm taking: *the original is the specification*
  (transcribe its tables and logic, don't reinvent); *measure, don't
  recall*; *one layer at a time, visible in the emulator*; *verify against
  the buffer, not the screenshot*; *decisions are numbered and written
  down* (`docs/decisions.md`). Its baseline machine is a Model B with
  16K of sideways RAM, and it warns RAM is tight for the whole port.
  Normally decisions are agreed with the owner first; here I've been
  asked to make the calls myself, so each one is written down with its
  reason, for review.

### The original

- Spectrum Computing (ZXDB 959) has the tape (TAP and TZX), four full maps,
  the inlay text, a POK file and the AY music. None of it is committed:
  `tools/fetch_original.sh` downloads it and checks `original/SHA256SUMS`.
- **The tape is trivial**: a one-line BASIC loader (`CLEAR 65520`, a couple
  of POKEs, `LOAD ""CODE`) and one 48,896-byte block loaded at 16384 — over
  the screen, the system variables and the BASIC program itself. No
  protection. SkoolKit's `tap2sna.py` simulates the load and stops with
  the game running at `PC = &60C2`.
- **The maps are 10 x 12 rooms of 256 x 176 pixels**: 22 character rows of
  playfield. In the game, the top two rows are the status bar (SCORE,
  CARRYING, LIVES).
- **The POK file names addresses**: lives at 41978, the start screen
  (1-120) at 41982, immunity at 35369. Free landmarks for the disassembly.

### Tools

- No Spectrum emulator was installed, and no pip. A project venv made with
  `uv` holds SkoolKit 10.1 and Pillow (`make venv`).
- `tools/zx.py` drives the original on SkoolKit's C Z80 simulator with the
  same script language as `tools/play.mjs`: keys by Spectrum name, `!shot`,
  `>snapshot`, pokes and peeks, run-to-address, and an execution map. It
  runs about 15 times real time: the instructions, the menu and the
  first room took 0.6 seconds.

![The original, first room](img/zx-first-room.png)

### Memory, first look

A rough survey of the loaded 48K by 1K block (zero bytes, distinct bytes,
entropy, ASCII):

| Range | Looks like |
|---|---|
| `&5B00-&6AFF` | the instructions text (~3K) |
| `&6B00-&A2FF` | code, with tables (~14K) |
| `&A300-&AAFF` | mostly zero: workspace |
| `&AB00-&DEFF` | 6-byte records, repeating patterns: room data? (~13K) |
| `&DF00-&FEFF` | sparse, bitmap-like: graphics (~8K) |

So the original is about 38K of code and data. A Model B with a 12K screen
has about 17K left above `&0E00`, plus odd pages below it. That decides
the target machine more than anything else will, so it waits for the
disassembly to say exactly what is code and what is data.

### Colour, first look

Measured on the full map (`ChuckieEgg2.png`), counting the colours of each
room and of each character row:

- Rooms use 3 to 7 colours: 4 rooms use 3, 27 use 4, 46 use 5, 35 use 6,
  8 use 7.
- Character rows: 92% of them use 4 colours or fewer, 7% use 5, under 1%
  use 6 or more. Only 55 of the 120 rooms fit in 4 colours on *every* row.
- Only 7 of 84,480 cells on the map have more than two colours (where the
  map's author drew sprites over the scenery), so it is a clean attribute
  picture: one paper and one ink per cell.

### The screen geometry

First BBC program (`src/main.6502`): `!BOOT` selects MODE 1, then the CRTC
is narrowed to 64 columns by 24 rows (R1 = 64, R6 = 24) at `&5000`, with R2
and R7 moved to keep the centre where MODE 1's is (R2 = 90, R7 = 30: the
display's centre lands 70 character times after hsync and 168 lines after
vsync, as in MODE 1). That is exactly the Spectrum's 256 x 192 in MODE 1's
pixels, 12K, and a character row is 512 bytes, so moving down a row is
adding 2 to the high byte.

A frame on the outermost pixels shows all four edges; the default palette
comes out as expected (logical 1 = `&0F` red, 2 = `&F0` yellow).

![Geometry test](img/geometry-test.png)

The picture sits low in jsbeeb's screenshot, but that is the screenshot's
crop: by the arithmetic it is centred exactly as MODE 1 is.

Baron 0.4.2 has `ASSERT` built in: the port kit's `MACRO ASSERT` shim is
now a "Reserved macro name" error.
