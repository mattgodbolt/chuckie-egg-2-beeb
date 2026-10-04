# Memory map (BBC Model B)

Measured from the build's listing and symbols. Take live figures from the
build output (`code &0E00-&xxxx (N bytes free)`), never from this file.

## The machine, as the port uses it

| Range | Size | Use |
|---|---|---|
| `&0000-&008F` | 144 | zero page, baron's allocator (`ZA_POOL`) |
| `&0090-&00FF` | 112 | the OS's (OSBYTE and friends still get called) |
| `&0100-&01FF` | 256 | stack |
| `&0200-&03FF` | 512 | OS vectors and workspace |
| `&0400-&06FF` | 768 | attribute map |
| `&0700-&09FF` | 768 | tile map (`&0800-&083F` is the OS's sound workspace: the 100Hz interrupt is stopped so it stays put) |
| `&0A00-&0CFF` | 768 | cell-type map |
| `&0D00-&0DFF` | 256 | free once the disc is done with (DFS NMI workspace) |
| `&0E00-&4FFF` | 16,896 | code and data (copied down from `&1900` after `*TAPE`) |
| `&5000-&7FFF` | 12,288 | screen: 256 x 192, MODE 1 pixels (decision 1) |

## Code and data, 2026-10-04 (the room viewer)

| From | What | Bytes |
|---|---|---|
| `&0E00` | system, screen (palettes, tile drawing), room drawer, unpacker, viewer | 2,438 |
| `&0F8C` | colour bytes and nibble-spreading tables | 276 |
| `&1786` | room palettes (4 bytes a room) | 480 |
| `&1966` | packed room offsets | 240 |
| `&1A56` | packed rooms (decision 5) | 7,770 |
| `&38B0` | tile font, `&20-&5B` | 480 |
| `&3A90` | room buffer (the largest room unpacked) | 385 |
| `&3C11` | end: **5,103 bytes free** | |

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
