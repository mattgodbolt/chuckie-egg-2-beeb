# Memory map

Where things go, and why. The addresses of the port's own regions live in
the source (`src/memory.6502`, the `SECTION`s in `src/main.6502` and
`src/pages.6502`) and their live figures in the build's output and
`build/symbols.json`: this file names them rather than copying their
numbers, which would go stale. The addresses it does give are the
constraints the layout has to fit around, set by the OS and the hardware.

## What the layout has to keep out of

| Range | What fixes it |
|---|---|
| `&00D0` | a Master's VDU status, read by its soft BREAK (decision 22) |
| `&00FC` | the OS's IRQ entry saves A here |
| `&0236-&03FF` | the OS's workspace beyond the vectors and page 3, which a soft BREAK reads on either machine (decision 22); the vectors below are reset on every BREAK, so tables can go over them |
| `&080C-&083F` | the OS's sound workspace, rewritten by its 100Hz interrupt until `init_system` stops it |
| `&0D00-&0D1F` | the NMI routine's space (`NMI_AREA`): the streaming edition's disc reader (docs/streaming.md) |
| `&0D9F-&0DFF` | a Master's extended vectors, read by its soft BREAK (decision 22) |
| `&7C00-&7FFF` | MODE 7's screen, where `MENU` runs between games |
| `&8000-&BFFF` | the sideways RAM bank (CE2's data: decisions 8, 13, 28) |
| `&C000-&C2FF` | OS 1.20's font, read in place for text (decisions 4, 14) |

## The port's regions

- **Zero page:** baron's allocator pool (`ZA_POOL`, below `ZP_FIXED`),
  then `ZeroPage` (the permanent state and LowState's most used variables)
  up to `DATA_BANK_ZP` (the data bank's number, from `MENU`), then
  `Scratch` (the OS's until the game owns the interrupts). `MENU` keeps
  to `mz_*` (`&70` up), which the OS leaves to a program.
- **Page 1:** `Page1` (`thing_init` and small tables) below the stack;
  the stack is 64 bytes (decision 19).
- **Page 2:** small tables over the vectors, and the game's IRQ1V.
- **`Maps`:** the attribute, tile and cell-type maps, 768 bytes each.
- **`LowState`:** monsters, the checkpoint, score, lives (the part up to
  `low_state_end` is the saved state).
- **`Code`:** code and data, loaded above the DFS's workspace and copied
  down (`main.6502`); in CE2S the room cache (`Cache`) follows it to `CODE_TOP`.
- **The screen** (`screen`): 256 x 192 in MODE 1's pixels (decision 1).

Between games (decision 13), `MENU` runs from the `Menu` section in
MODE 7, loading `CE2DATA` to copy into the bank when the bank doesn't hold
this build's. The game's state block (`SAVE_HDR`, then the regions from
`STATE`; the high scores are `CE2HI`'s, decision 38) sits above anything
`CE2` loads over (checked by the build) and below MODE 7's screen, so it
survives the reset, `MENU` and the game's reload. CE2S keeps its mailbox
at `MB_STREAM`, under the screen, and `MENU` leaves a copy at `MB_XFER`
for its loader to put back (docs/streaming.md).

Pages 1 and 2 are the OS's until the game owns the interrupts
(`install_irq`) and reads the keyboard itself (`key_down`, straight from
the System VIA): from then on the game makes no OS calls. Their tables
load after the code in the `CE2` file and `copy_os_pages` puts them in
place (`pages.6502`), only where a soft BREAK doesn't look.

The game's start-up (`startup.6502`: the screen, the interrupts, the
tables, a new game or a resumed one) runs once per load from the loader,
in screen memory, and is overwritten by the first room's `cls`.

## The budget against a stock Model B (2026-10-04)

Historical: the reasoning behind decision 8. What the rest of the game needed, at the Spectrum's sizes (6502 code is
usually no smaller than Z80), from `docs/research/*.md`:

| Item | Bytes |
|---|---|
| Harry: code and helpers | 2,820 |
| Harry's frames | 294 |
| Monsters, machines, sprite engine: code | 2,667 |
| Monster table and types | 1,232 |
| Monster, truck, train and lift graphics | 7,472 |
| Object sprites | 1,256 |
| Sprite pointer tables | 474 |
| Objects, machines and egg logic (to be measured) | ~2,500 |
| Sound | ~230 |
| In-play front end (keys, score, lives, eggs delivered) | ~810 |
| **Total** | **~19,750** |

Free: 4,563 bytes under the screen, perhaps 1-1.5K more from OS pages
(`&0D00`, the bottom of the stack, `&0200-&03FF` once the OS is finished
with). Short by about 14K. Hence decision 8: a 16K sideways RAM bank for
the data (packed rooms 7,770 + monster graphics 7,472 = 15,242), and the
code and the hottest tables in main RAM.
