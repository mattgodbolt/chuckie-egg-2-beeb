# Memory map (BBC Model B)

Measured from the build's listing and symbols. Take live figures from the
build output (`code &0E00-&xxxx (N bytes free)`), never from this file.

## The machine, as the port uses it

| Range | Size | Use |
|---|---|---|
| `&0000-&005F` | 96 | zero page, baron's allocator (`ZA_POOL`) |
| `&0060-&008F` | 48 | zero page, the game's permanent state (`memory.6502`) |
| `&0090-&00F2` | 99 | zero page, the game's scratch variables (`Scratch`): the OS's until the game owns the interrupts |
| `&00FC` | 1 | the OS's IRQ entry saves A here |
| `&0100-&017F` | 128 | `thing_init` (page 1, copied in at start-up) |
| `&0180-&01FF` | 128 | stack |
| `&0200-&0235` | 54 | OS vectors (IRQ1V is the game's) |
| `&0236-&02FF` | 202 | `thing_types` (page 2) |
| `&0300-&03FF` | 256 | `mon_types` (page 3) |
| `&0400-&06FF` | 768 | attribute map |
| `&0700-&09FF` | 768 | tile map |
| `&0A00-&0CFF` | 768 | cell-type map |
| `&0D00-&0DEB` | 236 | `LowState`: monsters, objects, machines, checkpoint, score, lives |
| `&0E00-&4FFF` | 16,896 | code and data (copied down from `&1900`) |
| `&5000-&7FFF` | 12,288 | screen: 256 x 192, MODE 1 pixels (decision 1) |
| `&8000-&BFFF` | 16,384 | sideways RAM: the mailbox, packed rooms, sprites, the font (decisions 8, 13) |

Between games (decision 13): `MENU` runs at `&1900-&27FF` in MODE 7 (screen
`&7C00`), loading `CE2DATA` at `&3000` to copy into the bank when the bank
doesn't hold this build's. The game's state block is at `&5F00-&6772`
(256 bytes of header, keys and high scores for a saved game, then the
regions from `&6000`): above anything `CE2` loads over (checked by the
build), below MODE 7's screen, so it survives the reset, `MENU` and the
game's reload.

Pages 1-3 are the OS's until the game owns the interrupts (`install_irq`)
and reads the keyboard itself (`key_down`, straight from the System VIA):
from then on the game makes no OS calls. Their tables load after the code
in the `CE2` file and `copy_os_pages` puts them in place.

## Code and data, 2026-10-04 (machines in)

Approximate, by each file's first label:

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

What the rest of the game needs, at the Spectrum's sizes (6502 code is
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
