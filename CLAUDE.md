# CHUCKIE EGG 2 (BBC Micro port) — notes for Claude Code

A port of A&F Software's *Chuckie Egg 2* (ZX Spectrum 48K, 1985) to the BBC
Micro, in 6502 assembly built with [baron](https://github.com/waitingforvsync/baron)
and tested in a headless jsbeeb through its MCP server. The Spectrum original
runs headless too, on SkoolKit's Z80 simulator, so the two can be compared.

- `docs/journal.md`: how it got here, in order. Add to it as you go.
- `docs/research.md`: what the original is and how it works.
- `docs/decisions.md`: every call the port makes that the original didn't,
  numbered, with the reason. Nothing is changed from the original quietly.

## The rules (from kieranhj/beeb-port-kit)

1. **The original is the specification.** Find what the Spectrum code does
   and transcribe it: its tables, constants and logic, verbatim where the
   hardware allows. When the BBC forces a change, port the original's
   *decision*, not just its effect. The map stays identical.
2. **Deviations are numbered decisions** in `docs/decisions.md`.
3. **One layer at a time**, working and visible in the emulator before the
   next one starts.
4. **Measure, don't recall.** Set the registers in jsbeeb, look, read memory
   back. "Verify against the buffer, not the screenshot."

## Commands

```sh
make            # assemble build/ce2.ssd (+ build/symbols.json, build/listing.txt)
make run        # boot it in jsbeeb, screenshot to shots/run.png
make fetch      # download the original into original/ (not committed)
make zx         # load the tape into build/ce2.z80
make venv       # .venv with SkoolKit and Pillow (needs uv)
```

Baron is expected at `../baron/build/src/baron` or on the PATH.

## Testing

- Three discs: `build/ce2.ssd` (the release: `!BOOT` runs `MENU`, the
  front end), `build/test.ssd` (`-D DIRECT=1`: `MENU` goes straight into a
  game; the tools use it, with `build/test.json`) and `build/viewer.ssd`.
- `make front` (`tools/frontcheck.mjs`) drives the front end on the
  release disc. `MENU` (`&1900-&27FF`) shares addresses with the game's
  code: once the game has run, put breakpoints only on game routines
  above `&2800`, and recognise `MENU` by its text in MODE 7's screen
  memory. Not by the build stamp: the OS prints that too, echoing
  `!BOOT`'s first line.

- `node tools/play.mjs '<script>' shots/prefix_ [--disc build/test.ssd]`:
  the BBC. Steps: a number waits seconds, `f10` frames, `SPACE:tap`,
  `LEFT:down`/`LEFT:up`, `!name` screenshots, `#name` dumps the screen,
  `?sym:n` peeks, `=sym:v1/v2` pokes, `@label` runs to a label. Symbols come
  from `build/symbols.json`.
- `.venv/bin/python tools/zx.py '<script>' shots/zx_`: the Spectrum, same
  language (Spectrum key names, `KL KR KU KD KF` for Kempston, `>name` saves
  a snapshot, `--map FILE` logs executed addresses).
- `python3 tools/grid.py out.png cols a.png b.png ...` tiles screenshots.

## The screen

MODE 1's pixels with the CRTC narrowed to 256 x 192 (R1 = 64, R6 = 24) at
`&5000-&7FFF`: the Spectrum's geometry exactly. A character row is 512
bytes, so row r starts at `screen + r * &200`. In a byte, a pixel's high bit
is in the top nibble and its low bit in the bottom one: colour 1 = `&0F`,
2 = `&F0`, 3 = `&FF` for four pixels.

The game sets MODE 1 in the hardware (`init_system`): `MENU` leaves the OS
in MODE 7, and an OS mode change would clear the state block at `&5F00`.

## Checks

**`make check` before every commit, and read its output.** (Once, a commit
claimed a check that hadn't run.) `make check MODEL=Master` runs it all on
a Master 128 too (decision 16); do that after touching start-up, the
handoff, the front end or anything paged.

- `.venv/bin/python tools/zxrooms.py` draws every room with the original's
  code (the oracle, `build/rooms`); `node tools/roomcheck.mjs` dumps the
  BBC's; `python3 tools/roomcmp.py` compares maps and pixels. Run all three
  after touching the room drawer, the palettes or the tile drawing.
- `make passes` replays `tests/scenarios.txt` (keys held over main-loop
  passes) on the original and the port and compares Harry's state every
  pass. Add a scenario for any movement or game logic that lands.
- `tools/mkrooms.py`, `tools/packrooms.py` and `tools/mkgfx.py` regenerate
  `src/data/` from the original. The build never runs them; their output
  is committed.
- Loading takes 4.6s: tools run to a symbol after booting
  (`startBeeb({bootUntil})`, `play.mjs --until`), never a guessed wait.
  The same for any wait in a test: run to the label that means "done"
  (`runUntil`). Fixed waits have twice let a test report a bug that wasn't.
- `tools/lint_labels.py` runs with every build and fails on a local label
  that shadows a global (one made egg_init rewrite its own code).
- Long-lived state goes in the fixed zero page or `LowState`
  (`memory.6502`), never in baron's pool: the death path resets the stack
  and jumps back into the main loop.

## OS workspace

- The maps live in `&0400-&0CFF`. The OS's 100Hz interrupt rewrites
  `&080C-&083F` (sound workspace) even when silent; `init_system` stops the
  System VIA timer interrupt that drives it.

## Baron gotchas met so far

- `ASSERT` is built in (0.4.2): don't define the port kit's macro.
- `FOR n = 0..15` (inclusive), not BeebASM's `FOR n, 0, 15`.
- A zero-page array is `ZA_AUTO 8, name`, indexed with `ZA_INDEXEDBY` after
  the access; eight `ZA_AUTO1`s aren't contiguous.

## Reading the original

- Z80 handlers that `PUSH AF`/`PUSH DE` and pop in the other order swap
  registers: read the pops, not the names. (A run's tile is its command byte.)
