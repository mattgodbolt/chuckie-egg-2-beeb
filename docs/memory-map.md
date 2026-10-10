# Memory map (BBC Model B)

Measured from the build's listing and symbols. Take live figures from the
build output (`code &0E00-&xxxx (N bytes free)`), never from this file.

## The machine, as the port uses it

| Range | Size | Use |
|---|---|---|
| `&0000-&0027` | 40 | zero page, baron's allocator (`ZA_POOL`): the game uses `&00-&1F` (`MENU` keeps to `&70-&78`, which the OS leaves it) |
| `&0028-&008E` | 103 | zero page, the game's permanent state and LowState's most used variables (`memory.6502`) |
| `&008F` | 1 | the data bank's number, from `MENU` |
| `&0090-&00FB` | 108 | zero page, the game's scratch variables (`Scratch`): the OS's until the game owns the interrupts; `&00D0` (a Master's VDU status) is left alone for a soft BREAK (decision 22) |
| `&00FC` | 1 | the OS's IRQ entry saves A here |
| `&00FD-&00FF` | 3 | free: neither MOS's IRQ entry touches them |
| `&0100-&01BF` | 192 | `thing_init` and small tables (page 1, copied in at start-up) |
| `&01C0-&01FF` | 64 | stack: the deepest measured is `&01EA` |
| `&0200-&0203` | 4 | free (USERV, BRKV) |
| `&0204-&0205` | 2 | IRQ1V: the game's handler |
| `&0206-&0235` | 48 | small tables, over the OS's vectors (page 2; every reset puts the vectors back) |
| `&0236-&03FF` | 458 | the OS's, untouched: what a soft BREAK reads, on either machine (decision 22) |
| `&0400-&06FF` | 768 | attribute map |
| `&0700-&09FF` | 768 | tile map |
| `&0A00-&0CFF` | 768 | cell-type map |
| `&0D00-&0D9E` | 159 | `LowState`: monsters, checkpoint, score, lives |
| `&0D9F-&0DFF` | 97 | the OS's, untouched: a Master's extended vectors, which its soft BREAK reads (decision 22) |
| `&0E00-&4FFF` | 16,896 | code and data (copied down from `&1900`) |
| `&5000-&7FFF` | 12,288 | screen: 256 x 192, MODE 1 pixels (decision 1) |
| `&8000-&BFFF` | 16,384 | sideways RAM: the mailbox, the palettes and bands, packed rooms, sprites, the tile font (decisions 8, 13, 21) |
| `&C000-&C2FF` | 768 | OS 1.20's font, read in place for text (decisions 4, 14) |

Between games (decision 13): `MENU` runs from `&1900` (below `&3000`) in MODE 7 (screen
`&7C00`), loading `CE2DATA` at `&3000` to copy into the bank when the bank
doesn't hold this build's. The game's state block is at `&5F00-&67A9`
(256 bytes of header, keys and high scores for a saved game, then the
regions from `&6000`): above anything `CE2` loads over (checked by the
build), below MODE 7's screen, so it survives the reset, `MENU` and the
game's reload.

Pages 1 and 2 are the OS's until the game owns the interrupts
(`install_irq`) and reads the keyboard itself (`key_down`, straight from
the System VIA): from then on the game makes no OS calls. Their tables
load after the code in the `CE2` file and `copy_os_pages` puts them in
place (`pages.6502`), only where a soft BREAK doesn't look: below the
stack, and over page 2's vectors.

The game's start-up (`startup.6502`: the screen, the interrupts, the
tables, a new game or a resumed one) runs once per load from the loader,
in screen memory, and is overwritten by the first room's `cls`.

## Code and data, 2026-10-04 (machines in)

Historical (before the front end and decisions 19-22 moved things about);
approximate, by each file's first label:

| From | What | Bytes |
|---|---|---|
| `&0E12` | system, swram, irq | 395 |
| `&0F9D` | screen | 358 |
| `&1103` | room drawer | 1,162 |
| `&158D` | status bar | 420 |
| `&1731` | room unpacker (streaming) | 560 |
| `&1961` | sprites | 563 |
| `&1B94` | Harry | 2,056 |
| `&239C` | monsters | 1,180 |
| `&2838` | collisions | 647 |
| `&2ABF` | objects | 2,023 |
| `&32A6` | machines: truck, train, lifts | 1,120 |
| `&3706` | game loop, deaths, keys | 900 |
| `&3A8A` | room palettes, packed room offsets | 720 |
| `&3D5A` | Harry's and the sprites' frame pointers | 328 |
| `&3EA2` | monster table | 1,024 |
| `&42A2` | object frame pointers, things, visits | 1,291 |
| `&47AD` | object graphics | 1,256 |
| `&4C95` | tile font | 480 |
| `&4E75` | end: 395 bytes free (before the front end; now 251) | |

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
