# Chuckie Egg 2 (ZX Spectrum) — how the original works

Everything here was found by reading the disassembly and checking it by
running the original (`tools/zx.py`, `tools/zxrooms.py`). Addresses are the
running game's (the tape loads one block at 16384 and the game starts at
`&60C2`). This file is the overview, the memory map and the room format;
the detail is in four write-ups, each made by a research agent working on
the disassembly and checked by experiment:

- [Harry](research/harry.md): movement, physics, cell types, room edges,
  death and respawn.
- [Objects and game logic](research/objects.md): the 256 things, taking
  and dropping, baskets, the machines and the egg sequence, scoring.
- [Monsters, sprites, graphics](research/monsters.md): the sprite engine,
  the monster table and movement, collision, truck, train, lifts, frame
  timing, a graphics inventory.
- [Front end, controls, sound, text](research/frontend.md): instructions,
  menu, keys, save/load, high scores, the three sounds, every string.

SkoolKit control files for each are in `disasm/`.

## The tape

- Block 1: BASIC `CHUCK 2` (66 bytes, one line):
  `CLEAR VAL "65520": POKE VAL "23624",VAL "0": POKE VAL "23693",VAL "0":
  OUT (VAL "254"),VAL "0": CLS : LOAD ""CODE`
- Block 2: `CODE 16384,49152` header, but the data block is 48,896 bytes:
  it loads over the screen, the system variables and the BASIC program,
  and the game is running when the load returns (`PC = &60C2` in SkoolKit's
  simulated load). No protection.

## Memory map (running game)

| Range | What |
|---|---|
| `&4000-&5AFF` | screen and attributes |
| `&5B00-&5CFF` | object start positions (copied at boot, `&5B00`), system variables |
| `&5D00-&65FF` | three 768-byte maps (32 x 24, one byte a cell) the room drawer fills: `&5D00` attributes, `&6000` tile codes (bit 7 set for text), `&6300` cell types. The instructions (`&60C2-&65FD`) are here at load and run once |
| `&6600-&6AFF` | the 256 "things" (objects, machine parts, bonus items): room, row, column, type, four 256-byte arrays; 67 types at `&6A00` ([objects](research/objects.md)) |
| `&6B00-&6FCF` | the monster table and 52 monster types ([monsters](research/monsters.md)) |
| `&6FD0-&74B7` | object sprites |
| `&7698-&A2FF` | code and tables |
| `&73B8` | CHARS while drawing rooms: tile *c*'s 8 bytes are at `&73B8 + 8c`. Tiles used are `&20` up, so the tile font starts at `&74B8` |
| `&7F84-&7F89` | room drawer state: attribute pointer, cell-type pointer, room data pointer |
| `&7F8A` | room command jump table (`&00-&0A`) |
| `&A300-&AAFF` | variables and workspace (see below) |
| `&A96A` | room pointer table: room *r* (1-120) at `&A96A + 2r` |
| `&AA5C-&DFA1` | room data, 13,633 bytes for 120 rooms (avg 114), in no particular room order; one unused 4-byte gap at `&B902` |
| `&DFA2-&FDF7` | Harry, monster, truck, train and lift sprites (7,766 bytes) |
| `&FE00-&FF00` | the IM 2 table, built at start-up |

### Variables found so far

| Address | Meaning |
|---|---|
| `&A3FE` | current room, 1-120 (the POK file's "screen" poke is 41982 = `&A3FE`) |
| `&A3FF` | room drawer: set while drawing text (tile codes go in the tile map with bit 7 set) |
| `&A3F9`, `&A3FA` | set at game start (`&A3FA` = 5: lives?) |
| `&A41C` | pointer to Harry's record in play |
| `&A42C` | control keys: 8 entries of (port high byte, mask, ASCII) — see below |
| `&A451` | Harry's record, 26 bytes, addressed through IY; initialised from `&89E5`, and copied to `&A46B` on entering a room (the restart point) |
| `&A487`, `&A485` | set to 7 and 0 at game start |
| `&A48A` | the control byte the key reader builds |
| `&A48B` | room change on leaving: added to `&A3FE` (+-1, +-10), with a special case: 80 + 1 = 71 and 71 - 1 = 80 |
| `&5C8D` (ATTR_P) | the room drawer's current attribute |
| `&5C84` (DF_CC) | the room drawer's screen address |
| `&5C36` (CHARS) | the room drawer's font |

## Controls

`&78C1` reads eight keys from the table at `&A42C` into one byte at `&A48A`,
first key in bit 7. Defaults (port high byte, mask, ASCII):

| Bit | Key | Use |
|---|---|---|
| 7 | `0` | abort, back to the menu (`&9BDC`) |
| 6 | `1` | take / drop |
| 5 | `S` | save the game to tape (`&A16E`) |
| 4 | `Q` | up |
| 3 | `A` | down |
| 2 | `O` | left |
| 1 | `P` | right |
| 0 | SYMBOL SHIFT | jump |

`&9CC3` reads the Kempston port (31).

## The main loop

`&7743` starts a game: room 1, Harry's record from `&89E5`. Then per room
`&7913` draws it (`&7920`) and sets up its contents (`&8B2A` monsters,
`&99F6` object cells, `&9088` the lift), and the loop at `&77B9` runs,
**exactly three frames a pass**: keys `&78C1`, Kempston `&9CE7`, Harry
`&80B6`, room change, the footstep click; HALT, in which the IM 2 handler
`&7ED9` erases and redraws the sprites on the draw list; the lift and the
monsters; HALT; collisions `&936B`; HALT; collisions again.

## The room format

The room drawer at `&7920`:

1. Room *r*'s data is at `(&A96A + 2r)`. Byte 0 is the room's attribute:
   its ink bits set the border, its paper is the background (every cell
   starts with paper = ink = that paper colour).
2. The screen is cleared, the attribute map (`&5D00`) filled with the
   background, the tile map (`&6000`) with `&37`, the type map (`&6300`)
   with 0. The status bar (rows 0-1) is printed.
3. Then commands until `&00`. Every tile placed writes the current
   attribute to the screen and to the attribute map, its code to the tile
   map, its 8 bytes from the tile font to the screen, and ORs the command's
   command's *type* byte into the type map.

| Command | Bytes | Meaning |
|---|---|---|
| `&00` | 1 | end of room (the handler returns out of the drawer) |
| `&01` | 7 | `01 attr row col h w type`: a w x h block of tile `&37` |
| `&02` | 4 + n + 1 | `02 attr row col text... 80`: text, in the text font, tile codes stored with bit 7 set |
| `&03`-`&06` | 5 | `0n attr row col type`: pipe bends, fixed shapes from tiles `&20-&27` |
| `&07` | 6 | `07 attr row col rows width`: a hopper, a funnel narrowing each row (tiles `&37-&3A`, and the paper and ink swapped inside) |
| `&08` | 6 | `08 attr row col len type`: a diagonal going up to the right (tiles `&55`, `&39`) |
| `&09` | 6 | `09 attr row col len type`: a diagonal going down to the right (tiles `&54`, `&38`) |
| `&0A` | 6 | `0A attr tile row col type`: one tile |
| `&20-&2B` | 7 | `cmd attr row col len ends type`: a capped run (pipes): end tiles `&20 + (ends >> 4)` and `&20 + (ends & 15)`, middle `&22` across or `&23` down; `len` bit 7 = vertical |
| `&2C-&5F` | 6 | `cmd attr row col len type`: a run of one tile; `len` bit 7 = vertical. The command byte itself is the tile (the handler pushes the command, then the last two bytes, and pops them crosswise) |
| `&60`+ | | not a command: the drawer restarts the game |

Commands used across all 120 rooms: 1,587 runs, 232 capped runs, 193
single tiles, 49 + 24 diagonals, 32 texts, 21 blocks, 21 bends, 5 hoppers.

`tools/zxrooms.py` runs the original's drawer for every room and keeps the
screen and the three maps (`build/rooms/room_NNN.bin`) as the oracle for any
re-implementation. Stitched together, its output is the published map
exactly, minus the sprites and objects (the truck, the birds), which are
not part of the room data.
