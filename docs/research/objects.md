# Objects, machines and the game logic

Scope: the things lying about the factory (objects, machine parts, bonus
items), taking and dropping, the basket, the machines and the whole
egg-production sequence, scoring, lives, game over and completion, and
every piece of code that tests the room number. Addresses are the running
game's. SkoolKit entries: `disasm/objects.ctl`. Where another file already
covers something in detail it is summarised here and pointed to:
`monsters.md` (the sprite engine, the object round robin's drawing side,
the train, truck and lift *motion*, the monster that eats the bone),
`harry.md` (Harry's states and record, death), `frontend.md` (status-bar
drawing, eggs-delivered screen, save/load, cheats).

How each fact was checked:

- **[run: x]**: by running the original on SkoolKit's simulator with the
  throwaway script `build/research/objects/x.py` (all start from
  `build/research/objects/start.z80`, a copy of `shots/zx_start.z80`, with
  the POK file's immunity poke `&8A29` = `RET` unless death was the test).
  `harness.py` there has the helpers, including a teleport that does what
  the game's own room-select cheat does (set the room, `JP &77FE`).
- **[code]**: read from the disassembly only.

Execution map of all the runs: `build/exec_objects.map` (about 4,000 addresses).
A linear listing of all the code reachable from the entry points, the IM 2
handler and the two jump tables is `build/research/objects/code.lst`
(made by `zdis.py`/`mkctl.py` there).

## Summary

| Thing | Where | Bytes | In one line |
|---|---|---|---|
| Thing table | `&6600-&69FF` | 1,024 | 256 things x (room+flag, row, column, type), parallel arrays, index = low byte |
| Type table | `&6A00-&6AC8` | 201 | 67 types x (ink, graphic, kind) |
| Initial positions | `&5B00-&5B7A` | 123 | copy of rooms/rows/columns of things 0-`&28`, made once at boot |
| Names | `&999E-&99F5` | 88 | 11 x 8 characters, `NOTHING` ... `BASKET` |
| Object graphics | `&6FD0-&74B7`, pointers `&8A98-&8B29` | 1,256 + 146 | 64 images, 73 pointers (see `monsters.md` 8) |
| Room visit bonus | `&A380-&A3F8` | 121 | per room: hundreds of points, bit 7 = visited this egg |
| Carry and factory counts | `&A560-&A56A` | 11 | carried thing, its height, TAKE latch, 4 delivered counts, 4 basket counts |
| Factory flags | `&A48C` | 1 | power, toy made, girder, toy on egg maker, egg made, 3 vats full |
| Contact with a thing | `&9515-&9673` | 351 | bonus pick-up, take, basket, power lever, LIFT sign |
| Drop and delivery | `&96B1-&9985` | 725 | drop, hopper fall, counting, toy, egg, girder |
| Room set-up / footprint | `&99F6-&9A7F` | 138 | mark portable things' cells in the cell-type map |
| New egg | `&9A80-&9B22`, `&9BD1-&9BDB` | 174 | reset things, flags, counts, monsters, toy graphics, train |
| Game start / next egg | `&7743-&77B8` | 118 | |

The game in one paragraph: 8 milk, 8 cocoa and 8 sugar must each be
dropped into their hopper (rooms 33, 51, 110), and the 8 toy parts into
the toy maker (room 95). With the generator on (lever in room 115) the
toy maker makes the toy; Harry carries it onto the egg maker (room 48);
with power and all three vats full the egg appears; Harry carries it to
the truck at dispatch (room 111). Then everything is reset for the next
egg with more monsters and a different toy. There is no end. Each of the
six big events gives an extra life and points times the egg number.

## 1. The thing table

### 1.1 Layout [run: dumps; code]

Everything that is not scenery, a monster or a machine is a **thing**:
256 entries in four parallel 256-byte arrays, so thing *i* is
`&6600+i`, `&6700+i`, `&6800+i`, `&6900+i` (the code walks them with
`INC H`). `(&A400)` holds `&66xx`, the thing last picked by the round
robin.

| Array | Meaning |
|---|---|
| `&6600+i` | room 1-120; **bit 7 set = not in the world** (carried, used up, not yet made, or the off/on twin of a machine part). Every room test compares the whole byte, so a hidden thing matches no room |
| `&6700+i` | row 0-23 of its top-left character cell (screen rows; the playfield is 2-23) |
| `&6800+i` | column 0-31 |
| `&6900+i` | type, index into `&6A00` (3 bytes a type) |

| Index | What | How it behaves |
|---|---|---|
| `&00-&28` (41) | **portable objects**: 8 toy parts, 8 milk, 8 cocoa, 8 sugar, 4 baskets, bone, girder, ladder, the toy, the egg | can be taken and dropped; only these change room/row/column, only these mark the cell-type map (`&99F6`) |
| `&29-&39` (17) | **machine parts**: 8 toy-part lights, 3 FULL! signs, generator lamp and lever (two of each: on/off twins), LIFT and OUT OF ORDER signs | fixed; shown/hidden through bit 7 |
| `&3A-&FF` (198) | **bonus items**: fruit, tools, crowns, keys... | taken on contact for points, gone for the rest of the egg |

The mutable state is exactly what the save game stores [code, `&A1BA`]:
`&6600-&6728` (all 256 rooms + the rows of 0-`&28`) and `&6800-&6828`.

**Initial positions.** The tape image holds the start positions in place.
Start-up (`&7703`, once) copies `&6600-&6628`, `&6700-&6728`,
`&6800-&6828` to `&5B00`, `&5B29`, `&5B52` (123 bytes, over the
already-shown instructions text), and every new egg (`&9A80`) copies them
back. Things `&29-&FF` never move, so are not copied.

### 1.2 Types and kinds [code; run: names seen in the status bar]

`&6A00 + 3t`: **ink** (0-7, replaces the ink of the cells it is drawn on),
**graphic** (index into the pointer table `&8A98`), **kind**:

| Kind | Meaning |
|---|---|
| `&01-&7F` (bit 7 clear) | bonus item worth kind x 100 x egg points (+ random tens and units). Used: 1, 2, 3, 4, 5, 7, 10, 15, 20 |
| `&80-&89` | portable; status-bar name = (kind AND 15) + 1 in `&999E`: `&80` TOY PART, `&81` MILK, `&82` COCOA, `&83` SUGAR, `&84` A BONE, `&85` GIRDER, `&86` LADDER, `&87` THE TOY!, `&88` THE EGG!, `&89` BASKET |
| `&C0` | fixed, inert (lights, lamps, FULL!, OUT OF ORDER) |
| `&C1` | fixed, the power lever |
| `&C2` | fixed, the LIFT sign |

Names `&999E` (8 bytes each, index 0-10): `NOTHING ` `TOY PART`
`  MILK  ` ` COCOA  ` ` SUGAR  ` `A BONE  ` ` GIRDER ` ` LADDER `
`THE TOY!` `THE EGG!` ` BASKET `.

**Graphics.** Pointer table `&8A98` (73 words) to images in the common
sprite format: height in rows, width in bytes, then height x 8 lines of
width bytes, top line first. All of them lie in `&6FD0-&74B7` (1,256
bytes, 64 distinct images). Rendered: `docs/research/img/object-sprites.png`
(by the monsters agent). Objects are always on character cells.

**The toy changes every egg** [run: deliver.py]. `&9B08` rewrites the
graphic byte of types 0-8 (the eight part types and the toy) to
`base + t` with base = `&1C + 9 x (((egg - 1) AND 3) + 1)`: egg 1
`&25-&2D` motorbike, 2 `&2E-&36` car, 3 `&37-&3F` boat, 4 `&40-&48` jet,
then again. Pointers `&00-&07`/`&0E` alias the boat.

### 1.3 The portable objects, as at the start of every egg [run: dump]

Rows and columns are of the top-left cell; "gfx h x w" is rows x columns.
Most sit on a floor; the bone in room 11 hangs in mid-air.

| # | name | room | row | col | type | gfx h x w | ink |
|---|---|---|---|---|---|---|---|
| &00 | TOY PART | 82 | 11 | 30 | &00 | &25 1x1 | cyan |
| &01 | TOY PART | 83 | 14 | 2 | &01 | &26 1x1 | cyan |
| &02 | TOY PART | 83 | 6 | 20 | &02 | &27 1x1 | cyan |
| &03 | TOY PART | 83 | 15 | 29 | &03 | &28 1x1 | cyan |
| &04 | TOY PART | 92 | 22 | 2 | &04 | &29 1x1 | cyan |
| &05 | TOY PART | 92 | 17 | 4 | &05 | &2A 1x1 | cyan |
| &06 | TOY PART | 93 | 10 | 2 | &06 | &2B 1x1 | cyan |
| &07 | TOY PART | 93 | 8 | 29 | &07 | &2C 1x1 | cyan |
| &08 | MILK | 24 | 4 | 3 | &09 | &08 2x1 | white |
| &09 | MILK | 26 | 11 | 30 | &09 | &08 2x1 | white |
| &0A | MILK | 34 | 16 | 21 | &09 | &08 2x1 | white |
| &0B | MILK | 35 | 5 | 2 | &09 | &08 2x1 | white |
| &0C | MILK | 36 | 9 | 8 | &09 | &08 2x1 | white |
| &0D | MILK | 36 | 5 | 29 | &09 | &08 2x1 | white |
| &0E | MILK | 45 | 3 | 4 | &09 | &08 2x1 | white |
| &0F | MILK | 46 | 6 | 15 | &09 | &08 2x1 | white |
| &10 | COCOA | 12 | 7 | 14 | &0A | &09 2x1 | red |
| &11 | COCOA | 21 | 10 | 25 | &0A | &09 2x1 | red |
| &12 | COCOA | 22 | 16 | 5 | &0A | &09 2x1 | red |
| &13 | COCOA | 31 | 17 | 2 | &0A | &09 2x1 | red |
| &14 | COCOA | 32 | 8 | 19 | &0A | &09 2x1 | red |
| &15 | COCOA | 41 | 21 | 28 | &0A | &09 2x1 | red |
| &16 | COCOA | 42 | 4 | 5 | &0A | &09 2x1 | red |
| &17 | COCOA | 53 | 21 | 6 | &0A | &09 2x1 | red |
| &18 | SUGAR | 86 | 21 | 30 | &0B | &0A 2x1 | white |
| &19 | SUGAR | 87 | 4 | 25 | &0B | &0A 2x1 | white |
| &1A | SUGAR | 88 | 21 | 28 | &0B | &0A 2x1 | white |
| &1B | SUGAR | 89 | 3 | 30 | &0B | &0A 2x1 | white |
| &1C | SUGAR | 97 | 3 | 3 | &0B | &0A 2x1 | white |
| &1D | SUGAR | 98 | 7 | 29 | &0B | &0A 2x1 | white |
| &1E | SUGAR | 99 | 15 | 2 | &0B | &0A 2x1 | white |
| &1F | SUGAR | 100 | 9 | 1 | &0B | &0A 2x1 | white |
| &20 | BASKET (toy parts) | 94 | 22 | 9 | &42 | &24 1x1 | yellow |
| &21 | BASKET (milk) | 24 | 22 | 26 | &42 | &24 1x1 | yellow |
| &22 | BASKET (cocoa) | 42 | 21 | 19 | &42 | &24 1x1 | yellow |
| &23 | BASKET (sugar) | 108 | 22 | 27 | &42 | &24 1x1 | yellow |
| &24 | A BONE | 11 | 5 | 29 | &0C | &0B 1x2 | white |
| &25 | GIRDER | 96 | 13 | 10 | &0D | &0C 1x5 | green |
| &26 | LADDER | 109 | 18 | 27 | &0E | &0D 5x1 | green |
| &27 | THE TOY! | 95, hidden | 21 | 1 | &08 | &2D 2x4 (per egg) | yellow |
| &28 | THE EGG! | 48, hidden | 19 | 4 | &0F | &0F 4x3 | yellow |

The index encodes the job: `i >> 3` is 0 toy part, 1 milk, 2 cocoa,
3 sugar (4 and 5 for the rest), and basket `&20 + g` serves group *g*.

### 1.4 The machine parts [run: dump, screenshots]

| # | room | row | col | type | gfx | ink | kind | at egg start | role |
|---|---|---|---|---|---|---|---|---|---|
| &29-&2C | 95 | 21 | 9-12 | &00-&03 | toy parts 1-4, 1x1 | cyan | &80 | hidden | toy maker: light for part 0-3 |
| &2D-&30 | 95 | 22 | 9-12 | &04-&07 | toy parts 5-8, 1x1 | cyan | &80 | hidden | light for part 4-7 |
| &31 | 33 | 16 | 15 | &41 | &22 "FULL!" 1x2 | blue | &C0 | hidden | milk vat full |
| &32 | 51 | 17 | 14 | &41 | &22 "FULL!" 1x2 | blue | &C0 | hidden | cocoa vat full |
| &33 | 110 | 15 | 13 | &41 | &22 "FULL!" 1x2 | blue | &C0 | hidden | sugar vat full |
| &34 | 115 | 14 | 15 | &10 | &10 lamp 1x1 | green | &C0 | hidden | generator on |
| &35 | 115 | 3 | 15 | &11 | &12 lever right 1x1 | white | &C1 | hidden | lever, on position |
| &36 | 105 | 8 | 5 | &15 | &14 "OUT OF ORDER" 3x4 | black | &C0 | hidden | lift sign, after |
| &37 | 115 | 14 | 15 | &12 | &10 lamp 1x1 | red | &C0 | shown | generator off |
| &38 | 115 | 3 | 15 | &13 | &11 lever left 1x1 | white | &C1 | shown | lever, off position |
| &39 | 105 | 9 | 5 | &14 | &13 "LIFT" 1x4 | black | &C2 | shown | lift sign, before |

The part lights sit in the black opening of the toy maker (rows 20-22,
columns 8-13 of room 95) and use the part types, so they show this egg's
toy. Their kind `&80` would make them takeable, but the toy maker's cells
there are solid (type `&01`), so Harry's box never overlaps them [code].

### 1.5 The type table [code; run: render]

Graphic names are descriptions of the pictures.

| type | ink | gfx | kind | meaning |
|---|---|---|---|---|
| &00-&07 | cyan | &25-&2C toy part (per egg) | &80 | TOY PART |
| &08 | yellow | &2D the toy (per egg) | &87 | THE TOY! |
| &09 | white | &08 milk bottle | &81 | MILK |
| &0A | red | &09 cocoa tin | &82 | COCOA |
| &0B | white | &0A sugar bag | &83 | SUGAR |
| &0C | white | &0B bone | &84 | A BONE |
| &0D | green | &0C girder | &85 | GIRDER |
| &0E | green | &0D ladder | &86 | LADDER |
| &0F | yellow | &0F egg | &88 | THE EGG! |
| &10 | green | &10 lamp | &C0 | inert |
| &11 | white | &12 lever (right) | &C1 | lever |
| &12 | red | &10 lamp | &C0 | inert |
| &13 | white | &11 lever (left) | &C1 | lever |
| &14 | black | &13 "LIFT" | &C2 | LIFT sign |
| &15 | black | &14 "OUT OF ORDER" | &C0 | inert |
| &16 | yellow | &1B lemon | &0A | 1000 |
| &17 | white | &1B lemon | &05 | 500 |
| &18 | yellow | &18 banana | &02 | 200 |
| &19 | green | &18 banana | &01 | 100 |
| &1A | white | &1C wrapped sweet | &05 | 500 |
| &1B | red | &1C wrapped sweet | &07 | 700 |
| &1C | yellow | &1C wrapped sweet | &0A | 1000 |
| &1D | white | &21 screwdriver | &01 | 100 |
| &1E | yellow | &21 screwdriver | &02 | 200 |
| &1F | red | &21 screwdriver | &03 | 300 |
| &20 | white | &1D crown | &05 | 500 |
| &21 | red | &1D crown | &0A | 1000 |
| &22 | cyan | &1D crown | &0F | 1500 |
| &23 | yellow | &1D crown | &14 | 2000 |
| &24 | white | &1E ring | &05 | 500 |
| &25 | red | &1E ring | &07 | 700 |
| &26 | green | &1E ring | &0A | 1000 |
| &27 | yellow | &1E ring | &0F | 1500 |
| &28 | red | &15 strawberry | &03 | 300 |
| &29 | green | &15 strawberry | &02 | 200 |
| &2A | green | &16 apple | &03 | 300 |
| &2B | red | &16 apple | &05 | 500 |
| &2C | yellow | &16 apple | &04 | 400 |
| &2D | white | &1F hammer | &02 | 200 |
| &2E | cyan | &1F hammer | &03 | 300 |
| &2F | black | &1F hammer | &04 | 400 |
| &30 | red | &1F hammer | &05 | 500 |
| &31 | yellow | &19 cheese | &02 | 200 |
| &32 | blue | &19 cheese | &04 | 400 |
| &33 | red | &19 cheese | &05 | 500 |
| &34 | white | &20 spanner | &02 | 200 |
| &35 | cyan | &20 spanner | &03 | 300 |
| &36 | black | &20 spanner | &04 | 400 |
| &37 | red | &20 spanner | &05 | 500 |
| &38 | green | &1A bottle | &02 | 200 |
| &39 | red | &1A bottle | &03 | 300 |
| &3A | yellow | &1A bottle | &04 | 400 |
| &3B | cyan | &1A bottle | &05 | 500 |
| &3C | green | &17 feather | &01 | 100 |
| &3D | blue | &17 feather | &02 | 200 |
| &3E | cyan | &17 feather | &03 | 300 |
| &3F | white | &23 key | &05 | 500 |
| &40 | yellow | &23 key | &0A | 1000 |
| &41 | blue | &22 "FULL!" | &C0 | inert |
| &42 | yellow | &24 basket | &89 | BASKET |

The **keys** of the instructions are only bonus items (types `&3F`,
`&40`): no code tests for a key, and there are no doors [code: no other
use of the kind or the types]. Black-ink things (OUT OF ORDER, some
hammers and spanners) are drawn in black over whatever paper their cells
have.

### 1.6 The bonus items [run: dump]

198 items, all present at the start of every egg (`&9A80` clears bit 7 of
`&37-&FF`), 1,057 hundreds in all (105,700 x egg). By room,
`index(row,col,type)`:

```
  4: 3A(13,1,1B) 3B(5,25,2C)            5: 3C(11,22,3E)
  6: 3D(22,5,2A) 3E(18,13,34)           7: 3F(10,10,18) 40(4,25,17)
  8: 41(3,5,17)                         9: 42(3,13,2A) 43(22,28,1A)
 10: 44(9,8,24) 45(22,15,34)           11: 46(11,12,28) 47(22,28,2A)
 12: F1(9,28,3F)                       13: 48(5,1,23) 49(22,21,2B) EF(3,28,3F)
 14: 4A(4,29,3A) 4B(22,21,1A) F3(13,6,3F)
 15: 4C(5,20,18) 4D(14,16,2D) 4E(8,29,3C)
 16: 4F(12,12,1A) 50(8,28,3E)          17: 51(9,19,24) 52(9,28,31)
 18: 53(6,18,31) 54(22,1,22)           19: 55(7,28,1C) 56(20,24,1D)
 20: 57(8,16,2C) 58(22,1,20)           21: 59(3,12,28) 5A(21,1,2D)
 23: 5B(7,6,16) 5C(14,18,3C) EE(3,27,40)
 24: 5D(3,17,3E)                       25: 5E(9,13,31) 5F(9,28,16) FB(18,4,40)
 26: 60(10,3,31) ED(5,28,22) F5(18,14,3F)
 27: 61(16,2,17) 62(20,1,35)           28: 63(19,4,2D) 64(20,18,1F)
 29: 65(12,3,18) 66(12,14,28) 67(20,20,2B)
 31: 68(10,1,3E)   32: 69(16,24,24)    33: 6A(22,28,1C)   34: 6B(13,1,3C)
 35: 6C(18,28,17)  36: 6D(6,1,23)      37: 6E(12,28,37)
 38: 6F(11,19,37) 70(15,3,2E) 71(22,2,23)
 39: 72(14,18,20)  40: 73(10,9,1B)     41: FE(22,29,23)   42: 74(21,1,3B)
 43: 75(11,9,28)   44: 76(22,1,1A) F6(13,16,40)
 45: 77(7,1,23) 78(19,5,2A)            46: 79(7,21,23) 7A(15,11,25)
 47: 7B(16,6,2A) 7C(15,14,18) 7D(15,22,28)
 48: 7E(22,23,31)  49: 7F(17,7,35) 80(9,11,31) 81(21,29,2D)
 50: 82(14,29,2A) 83(17,8,31)          52: 84(21,10,31)   53: 85(10,26,2A)
 54: 86(12,15,18) 87(16,29,2A)         55: 88(17,1,34) 89(11,29,39)
 56: 8A(7,4,21) 8B(7,28,1E)            57: 8C(6,5,21) F4(13,10,40)
 58: 8D(6,27,1A) 8E(11,19,3A)          59: 8F(16,20,24)   60: 90(16,11,35)
 61: 91(5,4,2A) 92(22,1,21)            62: 93(17,1,2A) FC(5,21,38)
 63: 94(8,12,31) 95(18,12,2D) FD(10,25,40)
 64: 96(3,30,27) 97(22,1,1A) EB(22,28,20)
 65: 98(22,1,1D) 99(11,23,34)          66: 9A(7,6,28) 9B(8,10,31) 9C(8,14,2A)
 67: 9D(5,17,2B) 9E(21,1,28) 9F(22,28,23)
 68: F2(16,20,40)  69: A0(5,19,3E) A1(22,1,20)            70: A2(22,28,23)
 71: A3(21,11,25)  72: A4(10,12,3A) A5(16,12,2B)          73: A6(11,13,1B) A7(22,13,20)
 74: A8(21,20,24)  75: A9(10,17,28) AA(16,11,25)          77: AB(15,15,22) AC(10,15,21)
 78: AD(21,16,19)  79: AE(10,27,3A) AF(17,28,1D)          80: B0(22,15,3E) B1(22,28,2C)
 81: B2(3,3,2C) B3(5,6,19) B4(5,25,37) FA(22,20,40)
 82: B5(7,13,17) B6(16,8,16) B7(21,28,24)
 83: B8(9,3,17) B9(21,1,19) F0(6,30,3F)
 84: BA(12,17,2C) EC(16,1,2C)          85: BB(5,14,28) F8(22,1,40)
 86: BC(17,10,30)  87: BD(11,25,2A)    88: BE(17,18,2C) BF(17,20,2A)
 89: C0(17,23,2A)  90: C1(21,29,2D)    91: C2(6,16,2C) C3(11,16,18)
 92: C4(10,14,1B)  93: C5(6,16,17) C6(17,2,17)            94: FF(22,27,22)
 95: C7(6,27,31)   96: C8(12,28,3A)    97: C9(22,11,1A)   98: CA(12,20,2A) CB(16,8,28)
 99: CC(15,25,37) CD(17,29,20)         100: CE(14,14,2B) CF(20,21,37)
101: D0(17,2,18) D1(17,10,2F) D2(13,27,1C)
102: D3(10,1,18) D4(17,27,37)          103: D5(6,28,17)   104: D6(12,6,2C)
105: D7(11,15,27) F9(22,27,40)         107: D8(13,28,37) F7(22,13,40)
108: D9(17,10,1E) DA(6,20,35)          109: DB(12,0,34) DC(21,15,3A)
111: DD(22,25,21)  112: DE(7,8,2C) DF(19,14,28) E0(11,25,3A)
113: E1(12,7,1A) E2(6,26,34)           114: E3(22,8,1D)
115: E4(22,5,2C) E5(21,24,19)          116: E6(21,15,24)  117: E7(22,14,1A)
118: E8(17,20,2C)  119: E9(21,12,29)   120: EA(22,11,23)
```

Entries `&EB-&FF` are not in room order (apparently added later); nothing
depends on the order.

## 2. Getting things on the screen and into the cell map

### 2.1 Footprints: `&99F6` (26 bytes) and `&9A10` (112 bytes) [run: ladder.py, girder.py]

Things are not in the room data. On room entry (`&7913`: draw, monsters,
**`&99F6`**, lift), every portable thing (0-`&28` only) in this room has
its cells marked in the cell-type map `&6300`, which is what makes a
dropped ladder climbable, a girder walkable and every object an obstacle
(masks in `harry.md` 5 and `monsters.md` 4.3: anything but bit 1 blocks).

```
room_things:                         ; &99F6
  for i in 0..&28: if (&6600+i) == room: thing_cells(i)   ; IY = &A402
  (&A405) = 0                        ; leave no object selected
thing_cells(i):                      ; &9A10, HL = &6600+i preserved
  hit = 0                            ; &9B24
  x = &40; if i == &26: x = &42 (ladder); if i == &25: x = &41 (girder)
  row, col = (&6700+i), (&6800+i)
  IY+2,3 = &5800 + 32*row + col; IY+4,5 = screen address    ; &7E34
  t = (&6900+i); IY+9 = ink[t]; IY+D = gfx[t]
  IY+0,1, IY+6 (h), IY+7 (w) from &8A98[gfx]               ; &8BDE
  for each of the h x w cells c at &6300 + 32*row + col:
    if c != 0: hit = c
    c = c XOR x
```

The same routine places (XOR in) and removes (XOR out) a thing, and
`hit` (`&9B24`) tells the drop code whether any cell was already taken.
Measured: the ladder's five cells read `&42`, `&00` after taking it,
`&42` again where it was dropped, and Harry climbed it; the cell under
Harry on the girder read `&41`.

### 2.2 Drawing: the round robin [run: popin.py; details in monsters.md 7.1]

`&99F6` draws nothing. `&7F01` (twice a main-loop pass) moves `(&A400)`
to the next thing whose room byte equals the room (any of the 256) and
loads it into the record `&A402` (position, ink `IY+9`, kind `IY+&12`,
graphic `IY+&0D`, image); the IM 2 handler ORs that one thing onto the
screen every frame (`&7EF4`: `IF (&A405) THEN CALL &8063`). So on entry
the things appear one by one over the first frames (measured: room 24's
milk after 1 frame, the rest a few frames later), and a thing erased by a
passing sprite comes back on its next turn. Only the current thing
(`&A402`) can be touched (3.1).

## 3. Contact, taking and dropping

### 3.1 Touching: `&937D`, `&940A` [code; monsters.md 5 has it verified]

Twice a pass, after the pixel test finds anything on the screen inside
Harry's box that is neither Harry nor scenery, `&940A` asks what Harry's
character box overlaps, in order: **the current thing** `&A402` (if any,
`&9515`), then the monsters, then the room tests (railway, dispatch:
5.5, 5.10). The boxes are whole character cells (`&968C`, `&9674`).

### 3.2 Bonus items and the take: `&9515` (86 bytes), `&956B` (148 bytes) [run: bonus_score.py, take_milk.py, ladder.py, basket.py]

```
touch_thing:                          ; &9515, IY = &A402, i = (&A400) low
  k = IY+&12                          ; kind
  if k bit 7 == 0:                    ; bonus item: no key needed
    (&6600+i) |= &80                  ; gone for this egg
    repeat egg times:                 ; (&A3F9)
      a = k
      if a >= 10: a -= 10; add_score(1, digit 6)   ; +1000
      add_score(a, digit 7)           ; hundreds (a may be 10: one carry)
    add_score(random() AND 7, digit 8)  ; tens
    add_score(random() AND 7, digit 9)  ; units
    erase the thing's image (&8BDE, &884D, &7FC9)
    return
  if k bit 6: goto fixed_thing        ; &95F0, 3.6
take:                                 ; &956B
  if not TAKE (bit 6 of &A48A): return
  if (&A562) != 0: return             ; latch: one action per press
  if i == &25: return                 ; the girder is never taken
  if i == &26 and Harry state (&A487) != 1: return   ; ladder: standing only
  c = (&A560)
  if c != &FF:                        ; hands full
    if not (&20 <= c < &24): return   ; only a basket takes more
    if (i >> 3) + &20 != c: return    ; and only its own kind
    (&A567 + c - &20) += 1            ; no limit
  else:
    set_carrying((k AND 15) + 1)      ; &9986: name to the status bar
    (&A560) = i; (&A561) = IY+6       ; its height
    if i == &27: (&A48C) bit 3 = 0    ; toy lifted off the egg maker
  (&6600+i) |= &80                    ; out of the world, room byte kept
  thing_cells(i)                      ; its cells cleared
  erase its image (&884D, &7FC9)
  (&A562) = 10
```

With `&A0BD`'s single carry this is always k x 100 per egg (k = 20 adds
1 to the thousands and 10 to the hundreds). Measured, kind 3: +324 on
egg 1, +924 on egg 3, +3,624 on egg 12 (the random tens and units were 2 and 4 each time: the same
random state).

Taking works in any of Harry's states (jumping, climbing) except for the
ladder; dropping needs state 1 (walking/standing).

### 3.3 Dropping: `&96B1` (265 bytes) [run: take_milk.py, milk_hopper.py, drop_column.py, ladder.py]

Called twice a pass, right after the contact test, so a TAKE press is
first offered to the current thing (3.2) and only then becomes a drop.

```
drop:                                 ; &96B1
  if (&A562) != 0:                    ; latch
    if TAKE held: return
    (&A562) = 0
  if not TAKE: return
  if (&A54E) < &80: return            ; something is still falling
  if (&A487) != 1: return             ; Harry must be walking/standing
  i = (&A560)
  if i == &FF: goto girder            ; &9934 (5.7): hands empty
  D,E,H,L = Harry's box: left col, right col, top row, bottom row  ; &968C
  col = (IY+&0D of Harry != 0) ? D : E   ; facing left: left column
  row = L - (&A561) + 1               ; its bottom level with Harry's feet
  save old row/col; (&6700+i) = row; (&6800+i) = col
  thing_cells(i)                      ; IY = &A402
  if hit: thing_cells(i); restore row/col; return   ; refused, still carried
  (&6600+i) = room                    ; bit 7 clear: in the world
  set_carrying(0)                     ; NOTHING
  (&A562) = 10; (&A560) = &FF
  if i == &27: goto toy_placed        ; &985B (5.4)
  ; gravity exists only for hoppers:
  if cell (&6300 + IY attr + 32*h) != 0: return   ; under its LEFT column
  c = IY attr AND 31                  ; its left column
  if c < 9 or c >= 24: return
  g = i >> 3
  room 33:  ok = i == &21 or g == 1   ; milk
  room 51:  ok = i == &22 or g == 2   ; cocoa
  room 95:  ok = i == &20 or g == 0   ; toy parts
  room 110: ok = i == &23 or g == 3   ; sugar
  other rooms: ok = false
  if not ok: return                   ; it stays where it is, even in mid-air
falls:                                ; &9796
  IY+8 = i; (&6600+i) |= &80; thing_cells(i)   ; out of the world
  copy &A402..&A40F to &A546          ; the falling record
  (&A551) = 0; (&A552) = &FE          ; dx 0, dy -2 (down)
```

Harry's box is 1 column wide when he is on a character boundary and 2
when between (his record `IY+7`), so the facing only matters between
cells. Measured: refused on a ladder column (cells `&02`) with either
facing; placed at Harry's column on an empty floor; in room 33, facing
left half over the gap, the milk fell into the hopper.

A dropped thing never falls anywhere else: dropped off a ledge it hangs
in the air until taken again [code]. Only the left column is checked for
support, even for the 5-wide girder or 4-wide toy [code].

### 3.4 Falling into a hopper: `&97BA` (64 bytes) [run: falling.py]

```
falling:                              ; &97BA, every contact pass (twice a pass)
  IY = &A546; if IY+8 >= &80: return
  if screen line of IY == 0 and cell under its left column (32*h below) != 0:
    erase; deliver(IY+8) (&97FA); IY+8 = &FF; return
  save old; move by dx,dy (&8E94); erase old; draw  ; 2 pixels a call
```

Measured: the milk from row 8 moved 2 pixels a call, 4 a pass (8 pixels
per 6 frames), and was delivered when its bottom reached the hopper's top
cell (`&80`/edge types) at row 13.

### 3.5 Carrying and the basket [run: basket.py, basket_jump.py, death_drop.py]

- One thing at a time (`&A560`, its height `&A561`). With hands full,
  TAKE on another thing does nothing and the same press drops what is
  carried (3.3) — except with a basket.
- **"Unless..." is the basket.** Four baskets, `&20-&23`, one per group.
  Carrying basket `&20+g`, TAKE on a thing of group *g* puts it in the
  basket: the thing leaves the world, `&A567+g` counts it, the name stays
  `BASKET`. No capacity limit. Measured: basket `&21` took milk `&08`
  (count 1, milk hidden).
- Because the drop runs on the same press, with a basket a TAKE next to
  an item either collects it (if the item is the round robin's current
  thing at that pass) or drops the basket (if there is room for it). In
  practice the drop is often refused because the item itself occupies
  the drop cell, and holding TAKE then collects it [run: basket.py, a
  3-frame press did neither, a 20-frame press collected].
- Carrying a basket also hampers Harry (`harry.md`): the jump starts at
  arc count 3 (measured: 5 pixels high instead of 16), and the mid-jump
  ladder grab at `&85C3` is skipped [code].
- A basket delivered into its hopper adds its count to the vat (5.1).
- Death (`&8A29`): if `&A560 < &27` the thing goes back to the world at
  the place it was taken from (its room/row/column were never changed),
  name NOTHING, hands empty. The toy and the egg stay carried. The girder
  goes back to its start (`&6725` = 13, `&6825` = 10, `&A48C` bit 2 = 0).
  Measured for milk `&08`, basket `&21` (back in room 24), toy `&27` and
  egg `&28` (still carried).

### 3.6 Fixed things: `&95F0` [run: power_lever.py, lift_sign.py]

Kind `&C0` + (kind AND 7): 1 = power lever (5.3), 2 = LIFT sign (5.8),
others nothing. No key needed; it acts on every contact pass.

## 4. The factory state

`&A48C`, the factory flags (all 0 at every new egg):

| Bit | Set by | Meaning |
|---|---|---|
| 0 | `&9606` lever / cleared `&9649` | power on (generator) |
| 1 | `&989E` | toy made |
| 2 | `&9934` / cleared on death and `&9934` | girder in the gap (room 96) |
| 3 | `&985B` / cleared `&95D7` | toy on the egg maker |
| 4 | `&98F2` | egg made |
| 5, 6, 7 | `&97FA` | milk, cocoa, sugar vat full |

Counts `&A563-&A566`: toy parts, milk, cocoa, sugar delivered.
`&A567-&A56A`: basket contents (toy parts, milk, cocoa, sugar).

Power drives: the toy maker and egg maker (bit 0 tested), the train
(moves only with power), the lifts in rooms 26, 55, 34, 104 (move only
with power; the type 2 lift also sits a row lower without it), and the
train's noise. Nothing else [code: every read of `&A48C` listed in 9].

## 5. The machines and the egg sequence

### 5.1 The hoppers (vats): `&97FA` (97 bytes) [run: milk_hopper.py, vat_full.py, basket.py, empty_basket.py]

| Hopper | Room | Accepts | FULL! sign |
|---|---|---|---|
| MILK | 33 | milk `&08-&0F`, basket `&21` | `&31`, row 16 col 15 |
| COCOA | 51 | cocoa `&10-&17`, basket `&22` | `&32`, row 17 col 14 |
| SUGAR | 110 | sugar `&18-&1F`, basket `&23` | `&33`, row 15 col 13 |
| TOY MAKER | 95 | parts `&00-&07`, basket `&20` | lights `&29-&30` |

The thing must be released over the hopper: its left column in 9-23 with
an empty cell under it (3.3).

```
deliver(i):                           ; &97FA
  if i < &20:
    g = i >> 3
    if g == 0: goto part_delivered    ; &9872
    n = 1
  elif i == &20: goto toy_basket      ; &9883
  else: g = i - &20; n = (&A567 + g)  ; a basket: its contents
  (&A563 + g) += n
  if (&A563 + g) != 8: return         ; exactly 8
  (&6630 + g) bit 7 = 0               ; FULL! appears
  (&A48C) |= &10 << g                 ; bits 5, 6, 7
  repeat egg times: add_score(1, digit 5)   ; 10,000 x egg
  extra_life (&A2DD); egg_check (&98F2)
```

Measured: 7 + 1 milk gave FULL!, +10,000, lives 5 → 6, flags `&20`; a
basket holding 8 milk did the same; one milk alone just counted 1, no
points; one cocoa into room 51 and one sugar into room 110 (dropped from
the right-hand end of the row-9 platform, facing right) counted 1 each
[run: other_hoppers.py]. **Quirk:** the test is "equals 8 after adding", so an *empty*
basket dropped into an already full vat awards the 10,000 x egg and the
life again (measured: lives 5 → 6, +10,000). Each basket can do it once
(it is used up).

### 5.2 The toy maker (room 95): `&9872`, `&9883`, `&989E` [run: toy_egg.py]

```
part_delivered:                       ; &9872, i = 0-7
  (&6629 + i) bit 7 = 0               ; its light comes on
  (&A563) += 1; goto toy_check
toy_basket:                           ; &9883
  for k in 0..7: if (&6600+k) bit 7: (&6629+k) bit 7 = 0   ; every part out of the world
  (&A563) += (&A567); goto toy_check
toy_check:                            ; &989E, also from power-on
  if not power or toy made or (&A563) != 8: return
  lights &6629-&6630 hidden; (&6627) bit 7 = 0   ; THE TOY! in room 95, row 21, col 1
  (&A48C) bit 1 = 1
  repeat egg times: add_score(2, digit 5)   ; 20,000 x egg
  extra_life
  if room == 95: print {AT 21,9}{ATTR 0}"    "{AT 22,9}"    "   ; wipe the lights' pixels
```

Measured: the eighth part with the power off lit its light and counted 8
but made nothing; switching the power on made the toy (flags `&03`,
+20,000, a life); the toy (motorbike on egg 1) was standing at row 21,
columns 1-4, in front of the machine. The toy-parts basket holding 8,
dropped in with the power on, made the toy at once (+20,000, a life), and
the black print left the opening plain black [run: other_hoppers.py,
toy_blank.py].

### 5.3 The generator (room 115): `&95FF` (7), `&9606` (41), `&9649` (26) [run: power_lever.py]

The lever (`&38` off / `&35` on, row 3 column 15) hangs above the gap
between the platforms at row 7. Jumping across touches it:

```
lever:                                ; &95FF
  if Harry's dx (&A45C) < 0: goto power_off
power_on:                             ; &9606 (dx 0 or right)
  (&A48C) bit 0 = 1
  show &34, &35 (green lamp, lever right); hide &37, &38
  toy_check; egg_check
  copy &962F → &A46B                  ; restart point: room 115, row 21, col 30, standing
power_off:                            ; &9649
  (&A48C) bit 0 = 0
  show &37, &38; hide &34, &35
  (&A48D) = 74; (&A48E) = 6           ; the train back to its start (&9AFD)
```

Measured: jumping right across set flags bit 0, swapped the four things
and set the restart record; jumping back left cleared it and put the
train at room 74, position 6.

### 5.4 The egg maker (room 48): `&985B` (23), `&98F2` (66) [run: toy_egg.py, egg_cells.py]

```
toy_placed:                           ; &985B, the toy was just dropped
  if room != 48 or Harry's column (&A453 AND 31) < 16: return
  (&A48C) bit 3 = 1; egg_check
egg_check:                            ; &98F2, also after a vat fills and on power-on
  if ((&A48C) OR 4) != &EF: return    ; power, toy made, toy placed, 3 vats; not egg made
  (&6628) bit 7 = 0                   ; THE EGG! in room 48, row 19, col 4
  (&A48C) bit 4 = 1
  (&6627) bit 7 = 1                   ; the toy is used up
  repeat egg times: add_score(2, digit 5)   ; 20,000 x egg
  extra_life
  if room == 48: thing_cells(&27); erase the toy   ; with IY = &A402
```

"PLACE TOY HERE" is on the right; the toy only has to be *dropped* (it
stays where it lands) with Harry at column 16 or right. Taking it back
clears bit 3. Measured: dropped at column 17 with the vat bits poked:
flags `&FB`, +20,000, a life, the egg (4 x 3) at row 19 columns 4-6.

**Quirk:** the egg (and the toy, if made while Harry is in room 95) gets
no cell footprint until the room is re-entered, since only `&99F6` marks
cells (measured: the egg's 12 cells were 0). Taking it before leaving
then XORs `&40` *into* those cells, leaving invisible obstacles until the
room is redrawn [code].

### 5.5 Dispatch (room 111) and the next egg: `&9453-&94E4` [run: deliver.py]

In the contact path (3.1), when nothing else was hit:

```
  if room == 111 and Harry's column < 7 and (&A560) == &28:   ; touching the truck
    erase Harry
    repeat egg times: add_score(3, digit 5)   ; 30,000 x egg
    extra_life
    truck drives off (&9059, monsters.md 6.1)
    black screen, {AT 11,7}"EGGS DELIVERED:-" and the egg number (&A3F9) at column 24
    wait for a key; JP &7763          ; next egg
```

The truck's strips are sprite pixels, so walking left into it is the
contact. Measured: +30,000, lives 7 → 8, "EGGS DELIVERED:- 1", then
room 1, egg 2, score and lives kept, all things back at their start,
flags 0, counts 0, carrying NOTHING, toy graphics `&2E-&36`, 180 monsters
enabled, train at 74/6.

### 5.6 What a new egg resets: `&9A80` (136 bytes) [run: deliver.py; code]

```
egg_init:                             ; from &7763 (new game and next egg)
  clear bit 7 of &A380-&A3F8          ; &9BD1: every room's visit bonus again
  copy &5B00 → &6600-&6628, &6700-&6728, &6800-&6828
  set_carrying(0)
  &6600-&6626 bit 7 = 0; &6627-&6636 bit 7 = 1; &6637-&66FF bit 7 = 0
  (&A48C) = 0; (&A562) = 0; (&A560) = &FF; (&A54E) = &FF
  &A563-&A56A = 0
  n = (&83 + &19 * min(egg, 5)) AND &FF
  &6B00..&6B00+n-1 bit 7 = 0; the rest (and &6B00) bit 7 = 1
                                      ; monsters 1..n-1: 155, 180, 205, 230, then all 255
  (&91B6) = 4                         ; truck strip counter
  toy_gfx (&9B08)                     ; this egg's toy
  (&A48D) = 74; (&A48E) = 6           ; train
```

So "more monsters" is only more entries of the monster table enabled
(details in `monsters.md` 3.2); the rest of the factory is the same every
egg except the toy's look.

### 5.7 The girder (room 96): `&9934` (82 bytes) [run: girder.py]

The girder `&25` cannot be carried. Standing on it with empty hands and
pressing TAKE swings it between two places:

```
girder:                               ; &9934, from drop with hands empty
  if room != 96: return
  if cell under Harry's left foot (attr + 64) != &41: return
  IY = &A402; thing_cells(&25); erase it
  (&A487) = 0; (&A486) = 0            ; Harry falls
  if (&A48C) bit 2 == 0: row, col = 14, 19; bit 2 = 1   ; into the gap in the floor
  else:                  row, col = 13, 10; bit 2 = 0   ; lying on the floor
  thing_cells(&25)
```

Measured: on the girder at row 13 it moved to row 14 column 19, filling
the 5-cell gap in the row-14 floor; pressed again while standing on it
there, it went back and Harry fell through the gap. Death puts it back
(3.5).

### 5.8 The LIFT (room 105): `&9663` (17 bytes) [run: lift_sign.py]

The LIFT box is scenery. Touching its label (`&39`, "LIFT" in black at
row 9 column 5) hides it and shows `&36` (thing − 3), an "OUT OF ORDER"
sign over the box, for the rest of the egg. That is all: a joke.

### 5.9 The ladder and the bone [run: ladder.py, dog.py, dog_cells.py]

- **Ladder `&26`** (room 109): taken only while standing; dropped, its
  five cells become `&42` and Harry climbs it like any ladder.
- **Bone `&24`** (room 11): nothing in the objects' code uses it. The
  dog (monster entry 1, room 2, `monsters.md` 4.6) sits for good the
  first time it is blocked, by the room's edge, a gap or an object, and
  that same code sets `(&6624)` = 0, deleting the bone *wherever it is*,
  and toggles the bone's footprint at the bone's row/column in the
  current room's cell map. Measured with the bone untouched in room 11:
  the dog walked to column 0 in about 9 s and sat, `(&6624)` became 0, and
  cells (5, 29-30) of room 2 became `&40` (invisible obstacles until the
  room is redrawn). So dropping the bone in the dog's path works (the
  object blocks it: [code]), but so does waiting.

### 5.10 Other machines [code; motion verified in monsters.md 6]

- **Lifts** (`&9088` set-up, 88 bytes; `&90F0` per pass, 154 bytes;
  table `&90E0`: room 26 (row 23, col 7, type 1), 55 (23, 23, 1), 34
  (4, 15, 2), 104 (4, 17, 2)). Type 1 is a 2-wide bar rising 2 pixels a
  pass from row 23 to row 3 and starting again; type 2 a 7-wide platform
  that goes down while Harry rides it (state 8) and back up to row 4.
  Neither moves without power [run: lifts.py, lift_speed.py: room 26's
  bar sat at row 23 with the power off and rose 2 pixels a pass with it
  on; the type 2 ones sat at row 5 off, row 4 on].
- **Train** (`&8EE8`): rooms 71-80 in a loop, half a column a pass, only
  with power; touching it (any contact while Harry's top row is 0-7 in
  rooms 71-80, `&9440`) kills.
- **Truck** (rooms 1 and 111): drives in at every egg (`&9028`), leaves
  on delivery (`&9059`); it is the dispatch target.
- **MIXER** (room 38) and **BOILER** (room 106) are scenery: no code
  tests those rooms, and their only things are bonus items.

### 5.11 The whole sequence, in order of dependencies

1. Collect 8 milk, 8 cocoa, 8 sugar (singly or in their baskets) and drop
   them into hoppers 33, 51, 110: each vat at 8 → FULL!, 10,000 x egg, a
   life.
2. Collect the 8 toy parts into the toy maker (95).
3. Generator on (115). With 8 parts and power: the toy, 20,000 x egg, a
   life. (Order of 2 and 3 free.)
4. Carry the toy to room 48 and drop it at column 16 or right. With power
   and the three vats full: the egg, 20,000 x egg, a life. (Order of 1
   and 4 free; the egg appears when the last condition is met.)
5. Carry the egg (4 x 3) to the truck in room 111: 30,000 x egg, a life,
   "EGGS DELIVERED", next egg.

Switching the power off later changes nothing already made.

## 6. Scoring, lives, game over

### 6.1 Score [run: as listed]

Ten digits, one per byte, `&A445` (most significant) to `&A44E`, cleared
by `&7743`. `add_score(A, digit BC)` = `&A0BD`: adds A to that digit,
one carry rippled up (lost past digit 0), each changed digit redrawn at
row 1, column BC (ROM font, `frontend.md` 6).

| Event | Points | Life | Where |
|---|---|---|---|
| First visit of a room this egg | `&A380`+room (0-10) x 100 x egg | | `&A139` |
| Bonus item | kind x 100 x egg + rnd(0-7) x 10 + rnd(0-7) | | `&9515` |
| A vat reaches 8 | 10,000 x egg | +1 | `&984E` |
| Toy made | 20,000 x egg | +1 | `&98CE` |
| Egg made | 20,000 x egg | +1 | `&9916` |
| Egg delivered | 30,000 x egg | +1 | `&9478` |

"x egg" is a loop of `&A3F9` additions. Nothing else scores. Measured:
rooms 11, 24, 33 gave 100, 200, 1,000 on egg 1.

Room visit values, `&A380 + room` (room 0 unused; room 1 is 0):

```
rooms  1-10:  0  1 10  1  3  2  1  3  2  3
rooms 11-20:  1  4  2  2  2  1  1  2  4  3
rooms 21-30:  2  1  3  2  2  2  7  6  5  5
rooms 31-40:  3  1 10  1  1  3  8  4  3  1
rooms 41-50:  2  1  6  2  2  4 10  2  1  4
rooms 51-60: 10  3  2  1  3  5  3  2  1  4
rooms 61-70:  2  2  3  2  3  5  3  2  1 10
rooms 71-80:  1  1  1  1  1  1  1  1  1  2
rooms 81-90:  1  5  6  2  2  4  3  3  2  1
rooms 91-100: 4  4  3  2  2  1  3  2  1  3
rooms 101-110: 5  6  3  2  2  1  2  3  1 10
rooms 111-120: 10 3  5 10 10  2  2  2  3 10
```

376 hundreds in all per egg. The visited bit (bit 7) is set when the
room is drawn, cleared for every room at each new egg.

### 6.2 Lives [run: vat_full.py, deliver.py, death_drop.py]

`&A3FA`: 5 at a new game (kept between eggs). +1 for each of the six
events of an egg (three vats, toy, egg, delivery) (`&A2DD`, at most 255); there is no score threshold. Death
(`&8A29`, `harry.md`): restore the restart record, return the carried
thing (3.5), reset the girder, lives − 1; 0 → game over (`&8A8A`: high
score check `&9E2D`, then the menu). The display shows at most 9.

### 6.3 Completion

None. The egg number `&A3F9` (1 at a new game, or the cheat's start egg)
counts up forever: monsters stop increasing after egg 5, the toys repeat
every 4, the points per event keep growing with the egg number. The
eggs-delivered screen is the only reward; there is no competition code in
the program [code; frontend.md agrees].

## 7. The status bar [run: screenshots; drawing in frontend.md 6]

| What | Where | Routine |
|---|---|---|
| `SCORE  CARRYING  LIVES` | row 0, col 5 | inline string at `&7982` in the room drawer |
| score, 10 digits, leading zeros of the first five as spaces | row 1, col 0-9 | `&A107` (85 bytes), which also adds the room's first-visit bonus |
| carried thing's name, 8 characters | row 1, col 12-19 | `&A36E` (18 bytes): an inline print whose text `&A376-&A37D` is overwritten by `&9986` (24 bytes) from `&999E` |
| lives: min(lives, 9) icons (tile `&56`) then one blank (tile `&37`) | row 1, col 22 on | `&A2B9` (36 bytes) |

All in attribute 7, text in the ROM font. The three routines run every
time a room is drawn; `set_carrying` reprints the name on take/drop;
`add_score` redraws digits as they change; `&A2DD` redraws the lives. The
basket's contents are never shown.

## 8. The per-room set-up

`&7913` = draw the room `&7920` (which also draws the status bar), then:

- **`&8B2A`** (180 bytes + helpers): monsters. Fills a 26-byte record at
  `&A490 + 26n` for every enabled monster table entry in this room
  (`&6B00-&6FFF`), count in `&A48F`; in rooms 1 and 111 also draws the
  truck (`&9011`). All monster scope: `monsters.md` 3.
- **`&99F6`**: objects, their cell footprints only (2.1).
- **`&9088`**: the lift of this room, if any (`&90E0`), record `&A52C`
  (5.10).

On a saved game being loaded, only `&7920`, `&99F6` and `&9B08` are run
before the main loop [code, `&A296`].

## 9. Every test of the room number, and everything else room-specific

| Where | Room(s) | What |
|---|---|---|
| `&77D7-&77FE` | 80 → 71, 71 → 80 | railway loop when leaving a room (`harry.md`) |
| `&78E0-&78FF` | 0 → 120, 121 → 1 | room-select cheat (CAPS SHIFT + left/right), live only if the boot byte at `&FFFF` enables it (`frontend.md` 1) |
| `&8B4F` | 1, 111 | draw the truck on entry |
| `&8D50-&8DA4` | 120, 2 | monster "blocked" event: room 120 the monster stops and changes frame; room 2 the dog sits and the bone is deleted (5.9; `monsters.md` 4.6) |
| `&8F0F-&8F4B` | 1, 111; 71-80 | truck refresh instead of the train; train drawing in its room and neighbours |
| `&9088` table `&90E0` | 26, 55, 34, 104 | lifts |
| `&9440` | 71-80 | contact with Harry's top in rows 0-7: death (the train) |
| `&9453` | 111 | dispatch (5.5) |
| `&9752-&9795` | 33, 51, 95, 110 | hoppers (5.1) |
| `&985B` | 48 | toy on the egg maker (5.4) |
| `&98D7` | 95 | wipe the part lights' pixels when the toy is made |
| `&9920` | 48 | remove the toy when the egg is made |
| `&9934` | 96 | girder (5.7) |
| `&A139` | all | first-visit bonus from `&A380` |
| thing table | 95, 33, 51, 110, 115, 105, 48 | machine parts, toy and egg (1.4) |

Every use of `&A48C`: `&8EEC`, `&8F96` (train), `&90B3`,
`&90F9` (lifts), `&95D7`, `&9606`, `&9649`, `&983D`, `&9869`, `&989E`,
`&98BC`, `&98F2`, `&9959`, `&996B`, `&997A`, `&9ABB`, `&8A75`.

## 10. Game start and per-egg flow [run: deliver.py; code]

```
new_game:                             ; &7743, from the menu
  (&A3F9) = (&A3FD)                   ; start egg - 1, normally 0
  (&A3FA) = 5; score = 0; carrying name = NOTHING
next_egg:                             ; &7763, also after a delivery
  room = 1; (&A3F9) += 1
  draw room 1 (&7920)
  Harry's record and restart record = &89E5 (room 1, row 18, col 6, state 7: jumping off the truck)
  (&A487) = 7; (&A485) = 0; draw list empty; no object selected
  egg_init (&9A80)
  IM 1; HALT; truck arrives (&9028); IM 2
  draw list = Harry; &8B2A; &99F6; &9088
  main loop &77B9
```

The main loop (`&77B9-&78C0`, three frames a pass; `monsters.md` 1 has
the timing): keys, Harry, room change (`&77CF`), then train `&8EE8`, lift
`&90F0`, round robin `&7F01`, monsters `&8C0A`, contact + drop +
falling (`&936B` = `&937D`, `&96B1`, `&97BA`) twice, round robin twice,
monsters twice.

## 11. Memory budget (what a port must carry for this scope)

| Item | Bytes |
|---|---|
| Thing table (`&6600-&69FF`) | 1,024 (the room array is the only fully mutable one; rows/columns of 0-`&28` mutable) |
| Initial positions (`&5B00`) | 123 |
| Type table | 201 |
| Names | 88 |
| Room visit bonus | 121 |
| Object images + pointers | 1,256 + 146 |
| Lift table | 16 |
| Restart record after power-on (`&962F`) | 26 |
| Variables (`&A560-&A56A`, `&A48C`, `&A445-&A44E`, `&A3F9`, `&A3FA`, `&9B24`) | 25 |
| Code: contact/take `&9515-&9673` | 351 (incl. the 26-byte record) |
| Code: drop/deliver/toy/egg/girder/name `&96B1-&999D` | 749 |
| Code: footprints `&99F6-&9A7F` | 138 |
| Code: egg init, toy gfx, visited `&9A80-&9B22`, `&9BD1-&9BDB` | 174 |
| Code: new game / next egg `&7743-&77B8` | 118 |
| Code: delivery `&9453-&94E4` (incl. 22 bytes of inline text) | 146 |

About 4.7K in all, of which 3.0K is data (1.4K of it images). The
thing table could shrink: the 198 bonus items never move (rows/columns/types could be packed or kept
per room), and only bit 7 of their room bytes changes.

## 12. Things the port has to decide (quirks transcribed as found)

1. Empty basket into a full vat re-awards 10,000 x egg and a life (5.1).
2. The dog sits the first time it is blocked, even with no bone, and the
   bone is deleted from wherever it is, with a two-cell phantom obstacle
   in room 2 (5.9).
3. The egg (and a toy made while Harry watches) has no footprint until
   re-entry; taking it first leaves phantom `&40` cells (5.4).
4. With a basket, TAKE near an item can drop the basket instead (3.5).
5. Dropped things only fall into the right hopper; elsewhere they float.
6. The toy can be dropped anywhere in room 48 right of column 16, and its
   support is not checked; only the left column of any dropped thing is.
7. Things appear one per frame or so after entering a room (round robin).

## 13. Open questions

- The type 2 lift's descent with Harry on it, and Harry's state 8, are
  read from code only (here and in `monsters.md`).
- The fall ends on the first non-zero cell under the thing, which need
  not be the hopper (in room 95 columns 9-14 land on the toy maker's
  body): it is counted as delivered all the same [code]. Whether any
  reachable drop point in the four rooms misses the hopper or machine was
  not checked.
- The basket's mid-jump ladder restriction is from code only.
