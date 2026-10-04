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

The original's code is about 14K and its graphics about 8K (to be pinned
down by the research in `docs/research/`); against 5K free, the budget is
the problem to solve next.
