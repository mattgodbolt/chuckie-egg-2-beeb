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

### The room format, and an oracle for it

- The room drawer is `&7920`. Rooms are a small bytecode: a background
  attribute, then commands — runs of one tile, capped runs (pipes), pipe
  bends, diagonals, hoppers, blocks, text, single tiles — until `&00`.
  Every tile placed also goes into three 768-byte maps (attribute, tile,
  cell type) that the rest of the game reads. Details in
  `docs/research.md`.
- `tools/zxrooms.py` calls the original's drawer for each room in turn
  (restore a snapshot, poke the room number, push a sentinel return
  address, run to it) and keeps the screen and the three maps: 120 rooms
  in two seconds. Stitched together they are the published map, minus
  the sprites. That is the oracle: whatever the BBC draws for a room gets
  compared against it.
- All 120 rooms parse: 13,633 bytes, average 114 a room. As one block it
  packs to 7,156 bytes with zlib and 6,256 with lzma; but the game needs
  one room at a time, so the packing has to allow that.
- Matt, mid-session: *"At a push, we could go 'Beeb with sideways RAM' or
  BBC Master. but try to fit this in a beeb first."* Decision 3.

### The rooms on the BBC: 120 of 120

- **Colour, measured.** `tools/colourstats.py` scores colour schemes on the
  oracle's pixels: four colours per room shows 99.5% of pixels in their own
  colour (pixel counts are dominated by paper); changing palette per
  character row would show 99.95%. Per-room palettes win on cost: no
  timing-critical interrupt every 8 lines, and sprites keep their colour.
  Decision 2. `tools/mkrooms.py` picks each room's four by brute force
  under two rules: ink and paper stay distinct in every cell, and every
  colour stays distinct from the background (so sprites in any colour show).
  A first version mapped colours the room data doesn't use to any free slot
  (room 1 sent yellow, Harry's colour, to blue); a small prior weight on
  every colour sends them to their nearest neighbour instead.
- **The drawer is a transcription**, handler by handler, of the original's,
  keeping its two pointers (attribute/screen and cell type) as cell numbers
  so its quirks come out the same. One gift from the narrowed screen: with
  16-byte cells and 512-byte rows, cell *n* is at `screen + 16n`.
- **Text uses the MOS font** at `&C000` (decision 4): the Spectrum's ROM font
  isn't ours to copy, and reading the BBC's costs nothing.
- `tools/roomcheck.mjs` pokes each room number into the viewer, dumps the
  three maps and the screen; `tools/roomcmp.py` compares them with the
  oracle: maps byte for byte, and every playfield pixel in the colour its
  room's palette gives the Spectrum's.
- **Bug 1: the OS was writing into my tile map.** The maps live in OS
  workspace pages (`&0400-&0CFF`), and the tile map's middle page is
  `&0800`, the OS's sound workspace. Measured: 27 bytes in `&080C-&083F`
  change every second with no sound playing — the 100Hz interrupt's sound
  processing. Stopping the System VIA's timer interrupt stopped it (negative
  INKEY scans the keyboard itself, so it still works). The game will own
  the interrupts outright anyway, as the port kit does.
- **Bug 2: a run's tile and type were the wrong way round.** The run
  handler pushes the command byte, then two data bytes, and pops them
  crosswise: the *command* is the tile (`&2C-&5F`, which is the font's
  range) and the last byte is the type. The tile and type maps disagreed
  in exactly mirrored cells, which made it obvious.
- After those, **all 120 rooms match**. The viewer (Z/X or the cursor keys
  step through rooms) is 16,768 bytes with the room data raw: 128 bytes
  under the screen.

![Spectrum (left) and BBC (right): rooms 11, 27, 70 and 96](img/rooms-zx-vs-bbc.png)

Room 70 is the worst for colour (91.4% of pixels in their own colour):
its red and yellow brickwork comes out magenta and yellow.

### Packing the rooms

- General-purpose compression doesn't see the rooms' structure. Per-room
  ZX02 (the port kit's packer) took 13,633 bytes to 10,220; a shared
  dictionary of whole rooms, which ZX02's `skip` allows, only to 9,671.
- Measured instead: a room averages 2.7 distinct brushes (tile, attribute,
  type); those fields repeat from one record to the next about 80% of the
  time; positions and lengths carry 4.2-5 bits of entropy each, close to
  their fixed widths. So `tools/packrooms.py` writes a bit stream per room:
  a prefix code for the command class (a run is one bit), move-to-front
  lists for attribute, tile and type, fixed widths for the rest, fields in
  the bytecode's own order so the unpacker emits each as it goes. 7,770
  bytes, round trip checked for every room. Decision 5.
- **One record in the whole game says column 32** (room 33). The original's
  arithmetic carries it into row 12, column 0; it is packed as that, and
  the round trip compares against the room with that record normalised.
- `src/unpack.6502` turns a room back into the original's bytecode in a
  385-byte buffer and the transcribed drawer draws from it, unchanged.
  Still 120 of 120 against the oracle; 5,103 bytes free under the screen
  where there were 128.
- Baron: `ZA_INDEXEDBY` belongs to the instruction just before it, so an
  indexed load and store on one line need a line each; and it didn't like
  `mtf-1,X` (Argument out of domain): index from the array's own address.
- Matt asked for a work-in-progress disc in the repo, linked from the
  README so the current state can be seen in a browser: `make wip`
  copies the build to `chuckie-egg-2-wip.ssd`.
- **How long a room takes**, by breakpoint pairs on the cycle counter
  (`read_registers`' `elapsed_cycles`): palette and screen clear 137K cycles
  (the clear alone is 68 ms: an `STA (p),Y` loop over 12K), unpack 33-76K,
  draw 105-246K; 275-446K in all, 0.14-0.22 s. The Spectrum's drawer takes
  96-140 ms for the same rooms (T-states in SkoolKit, uncontended). Fine for
  flipping screens; an unrolled clear would win back ~37 ms if needed.
- `docs/memory-map.md` started: with the rooms packed, 5,103 bytes are free
  under the screen. The original's code is ~14K and its graphics ~8K, so
  the memory budget is the next problem.

### The interrupts, and a palette split for the status bar

- The status bar is white text on black; many rooms have neither in their
  four colours. So rows 0-1 get their own palette: `src/irq.6502` now owns
  IRQ1V outright (after the port kit's `lib/irq.6502`: both VIAs silenced
  but VSync and the User VIA's T1). At VSync it writes the status bar's
  palette and starts T1; when T1 fires it writes the room's: logical 1-3
  first, during the last scanline of row 1 (blank in an upper-case font),
  then logical 0, aimed at the horizontal blank before row 2.
- **Measured, by making the status paper red** and finding where the red
  stops in jsbeeb's screenshots (4 screen pixels per scanline here). First
  try: 188 pixels into line 14. MODE 1 runs with interlace sync on, which
  moves VSync half a line in alternate fields — a 32 µs swing against a
  32 µs blank — so R8 is now 0, as `*TV 0,1` would set. After that the
  switch point held to within 8 pixels (1 µs, the interrupt latency)
  frame to frame. Retuned: `SPLIT_T1 = 83 * SL - 2 + 46` puts the red on
  exactly lines 0-15 in every frame sampled, with the logical-0 writes
  about 4.5 µs into the blank and done 11.5 µs before row 2.
- jsbeeb only. The port kit's experience is that raster timing wants
  checking on a second emulator (b2) and on hardware; noted for later.
- With the OS's interrupt gone, OSBYTE 129's negative INKEY still reads
  the keys in the viewer: it scans the matrix itself.

### Research: the front end, controls and sound

Four research agents were set going on the disassembly at once (Harry;
objects and game logic; monsters, sprites and graphics; front end and
sound), each writing its own `docs/research/*.md` and a SkoolKit control
file in `disasm/`. The front-end one came back first
(`docs/research/frontend.md`). What changes the plan:

- **Three sounds in the whole game**: Harry's movement click, the train's
  noise and the life-lost tune. Menus, pick-ups, eggs: silent. Easy work
  for the SN76489.
- **The main loop runs in 3-frame passes.**
- **No pause key**; the eight keys are abort, take/drop, save, the four
  directions and jump.
- **Saving writes the whole game state** (1,320 bytes, XORed with the
  random number generator) to tape, at any time, from play or the menu.
- **There is no ending**: delivering an egg shows "EGGS DELIVERED:- n" and
  starts the next with more monsters. No competition code anywhere.
- **Sizes**: 1,511 bytes run once at start-up (the instructions), about
  1,560 between games (menu, redefine, high scores, save/load), 810 in
  play. The start-up and between-games code can live outside the
  resident game on the BBC.
- A hidden cheat: a byte at `&FFFF`, outside the tape image and normally
  0, of the form `%101xxxxx` gives a starting egg, a room skip and
  infinite lives; anything else non-zero prints PLEASE TRY AGAIN and
  resets the Spectrum.

### The status bar, and what a MODE 1 palette entry really is

- `src/status.6502` draws the status bar as the original's drawer does
  (`docs/research/frontend.md` §6): `SCORE  CARRYING  LIVES` on row 0, the
  score, the carried object's name and the lives icons (tile `&56`) on
  row 1, all white on black, i.e. logical 1 on 0 in the status palette.
- **The lives icons' feet came out blue**: the icon uses its eighth line,
  so row 1's last scanline isn't blank, and the room's logical 1 was being
  written during it. Fix: change fewer entries at the split, since only
  the entries the status bar can show need to wait for it.
- **Then the letters had coloured pixels in them**, which showed my model
  of the palette entries was wrong. The ULA builds the entry number from
  bits 7, 5, 3 and 1 of a shift register that moves one bit a pixel. With
  a byte's bits `p0h p1h p2h p3h p0l p1l p2l p3l`, pixels 0 and 1 take
  entry bits 2 and 0 from the pixel *two to the right*; pixels 2 and 3
  take one low bit from two to the left and a 1 shifted in. So white on
  black uses logical 0 and 1 beside "neighbours" 0, 1 *and 3*: six
  entries, not four. Now VSync writes the other ten with the room's
  colours, and T1 writes just the six (24 µs) in the blank before row 2.
- Swept the timer across the window with a red status paper
  (`-D SPLIT_SWEEP=n`): the switch is clean from offset 84 to 108 (µs)
  and late at 112; `SPLIT_ADJ = 96` sits in the middle.
- Baron: `IF NOT(DEFINED(X)) : X = ...` never settles (the definition
  flips the test between passes); an override needs its own name.

### Research: Harry

The Harry agent's write-up is `docs/research/harry.md`. The facts the
engine will be built on:

- Harry updates once every **3 frames** (three HALTs a loop; measured
  3.000 in quiet rooms, up to 3.1 in busy ones).
- Walk 2 px an update; fall 4; ladders 2; ropes only slide down (1, 2 or 3
  px by the keys); slopes 2 across and 2 up or down, climbing only while
  the uphill key is held; lifts 2.
- The jump is a table (`&89CF`): 4,4,3,2,1,1,1,0,0,0,0,-1,-1,-1,-2,-3,-4...;
  16 px high, 36 px long on the flat; the direction is fixed at take-off.
- A fall kills if the fall counter reaches 15: from rest, 7 cells is safe
  and 8 kills.
- Cell-type bits: `&01` solid, `&02` ladder, `&04`/`&08` the two slopes,
  `&10` rope, `&20` a pipe that only holds you while you walk ("some pipes
  are more slippery than others"), `&80` deadly.
- His code is 2,530 bytes on the Spectrum, plus ~290 of helpers and 294 of
  sprite frames.

### Build stamp

Matt asked for the build date, time and commit in `!BOOT`, to tell old
discs apart: the Makefile passes `-D BUILD="2026-10-04 14:26 UTC 777ab7a"`
(a `+` after the SHA if the tree had changes) and `!BOOT`'s first line is
`*| CHUCKIE EGG 2 <stamp>`, so `*TYPE !BOOT` shows it. `make wip` refuses a
dirty tree and the disc goes in its own commit, so its stamp names the
commit holding its code.

### Research: monsters, sprites, graphics — and the memory verdict

`docs/research/monsters.md` (with sheets of every sprite in
`docs/research/img/`) settles how the original draws: sprites are ORed
on, setting only the ink of the cells they cover; erasing clears the old
image's bits and ORs back the tile pixels from the tile map, attributes
from the attribute map. Positions are 2-pixel steps with pre-shifted
frames, so nothing shifts at draw time. The main loop is exactly three
frames, always: Harry moves once and is drawn in frame 1; monsters tick
twice and are drawn in frames 2 and 3. At most four monsters a room; 52
types; later eggs enable more table entries (more monsters, none faster).

And its numbers decide the machine. The graphics alone are 9.5K
(monsters, truck, train and lifts 7.5K; objects 1.3K; Harry 0.3K; tiles
0.5K). With everything else the game needs ~20K more than is placed so
far, against 4.5K free under the screen. A stock Model B could only do it
by loading each room's data from disc on the way in, with a pause and the
drive's noise on every screen; so, decision 8, as Matt allowed: a Model B
with 16K of sideways RAM.

Measured in jsbeeb with a probe (page each bank, flip `&8000`, see if it
sticks): the Model B models have RAM in banks 0-7, the Master in 4-7. So
the README's browser link keeps working.

Keys (decision 7): Matt wants the Spectrum's for now — "the spectrum ones
work and are authentic" — with BBC-appropriate ones for later discussion
(`docs/for-review.md`, which lists every call made autonomously that he
may want to revisit). SPACE stands in for SYMBOL SHIFT. Measured in jsbeeb's
`keyboard_state`: 1 is internal key 48, 0 is 39.

Yellow is now one of every room's four colours (decision 6), so Harry is
always yellow; about a point of scenery colour lost on average.

### Sideways RAM, in practice

- The disc now holds three programs: `SWLOAD` loads `CE2DATA` (a 16K image
  assembled at `&8000`) to `&3000`, finds the highest bank that is RAM and
  had no ROM at start-up (ROM type byte 0), copies the image in and
  `*RUN`s `CE2` over itself. `CE2` finds the bank again by the magic at its
  start and leaves it paged in for good (`romsel` and the OS's copy `&F4`
  both): the data reads as ordinary memory at `&8000`.
- The packed rooms moved there: 12,228 bytes free in main RAM, 7,839 in
  the bank.
- **The Master drew garbage for text**: decision 4 read OS 1.20's font
  straight from `&C000`, which isn't where MOS 3.20 keeps it. Now
  `copy_font` reads characters 32-127 through OSWORD 10 into the bank at
  start-up, before the interrupts are taken: the machine's own font, on a
  B or a Master. Checked on both in jsbeeb; 120 of 120 rooms still match.

### Research: objects and game logic

`docs/research/objects.md` completes the set. Everything that isn't
scenery or a monster is one of 256 "things" (room, row, column, type, in
four parallel 256-byte arrays): 41 portable (8 toy parts, 8 each of milk,
cocoa and sugar, 4 baskets, bone, girder, ladder, the toy, the egg), 17
machine parts, 198 bonus items. The game: fill three vats with 8 of each
ingredient, make the toy from 8 parts with the power on, set the toy on
the egg maker with the vats full, deliver the egg to the truck in room
111. Each step scores (10,000-30,000 x the egg number) and gives a life;
the next egg resets the factory, enables more monsters and changes the
toy. The "unless..." of "you only have two hands" is the basket, which
gathers any number of one ingredient (and makes jumps lower).
