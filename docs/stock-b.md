# Chuckie Egg 2 on a stock 32K Model B: what it would take

> **Exploratory, not current.** A feasibility study measured on 2026-10-04
> against build `25a57fd`. The code has moved on since and the figures
> will drift; nothing here is planned or built. A stock-B edition is
> tracked as [issue #1](https://github.com/mattgodbolt/chuckie-egg-2-beeb/issues/1),
> for the future; re-measure before relying on any of it.

Research for the "moon shot": the game on a Model B with no sideways RAM.
An exploratory agent measured it on the build of `25a57fd` and in jsbeeb
2.3.1 (the version `npx jsbeeb-mcp` runs, which models the 8271's step,
settle and head-load times, the motor's spin-up and 300rpm rotation). The
scripts and their output are in [`tools/stockb/`](../tools/stockb/) (listed
at the end). Figures marked ~ are estimates; the rest are measured.

Since then the developers' cheats (decision 27) have taken 61 bytes of main
RAM (2,889 free became 2,828), which comes off the spare figures below.

## The answer

**Not from memory alone.** Off the screen, the game needs about 32.4K and a
Model B has 20.5K beside the 12K screen. The rooms are already at their
entropy (ZX02 takes 7% more off them), and the sprites compress by about
40% at best. Even with a 1-bit screen (6K back) and every packing idea
counted, including the speculative ones, it is still about 2K short. That
leaves cutting the original's content, which rule 1 rules out.

**From disc, yes.** If each room's constant data is loaded from disc on
entering the room (its packed room, palette and bands, monster entries and
the sprite frames its monsters use), the game fits a stock B with about 1K
of main RAM to spare. The screen, colours, rooms, graphics and rules stay
exactly as they are now. **What it costs is the room change.** The
Spectrum's takes 0.10-0.14s and the port's now takes 0.18-0.32s. Streamed,
it would take about 1.0s, because the DFS lets the drive spin down after
2.4s and players stay longer than that in most rooms. With the drive kept
spinning all game it would take about 0.4s. Either way you hear the drive
at every room change, and the disc has to stay in the drive.

## 1. Where the bytes are

From `build/listing.txt` and `build/symbols.json` (`budget.py`,
`budget.out`):

| Main RAM `&0E00-&4FFF` (16,896) | Bytes |
|---|---|
| Code: system 32, irq 179, screen 380, rooms 803, status 334, unpack 472, sprite 769, harry 1,857, monsters 1,022, collide 558, objects 1,434, machines 752, sound 258, handoff 202, game 629 | 9,681 |
| Data: frame pointers 328, monster table 1,024, object frame pointers 146, things 1,024, visits 121, thing types 201, monster types 208, death tune 48, band variables 69, object graphics 1,157 | 4,326 |
| Free | **2,889** |

| Sideways bank (16,384) | Bytes |
|---|---|
| Magic and build stamp | 35 |
| Mailbox (keys, high scores, filename, the OS bytes a BREAK keeps) | 225 |
| `setup_bands` (code) | 210 |
| Band records 148, colour maps 28 | 176 |
| Room palettes | 120 |
| Packed rooms (decision 21) | 6,845 |
| Packed lengths 120, unpacker's tier and vocabulary tables 233 | 353 |
| Sprite frames (decision 26): Harry 294, the rest 6,045 | 6,339 |
| Tile font | 480 |
| Total (1,601 free) | **14,783** |

**Shortfall on a stock B: 14,783 - 2,889 = 11,894 bytes.** Everything else
is taken already: zero page, page 1 below the stack, page 2's vectors, the
maps in `&0400-&0CFF`, LowState at `&0D00`. What's left of pages 2 and 3
and `&0D9F-&0DFF` is kept for BREAK (decision 22).

### What has to stay resident, and what is per room

- **Has to stay resident** in any plan: the code; the 256 things, the
  visits and the thing types (they change, and objects travel between
  rooms); the object graphics (a carried object goes from room to room);
  Harry's frames; the tile font; the unpacker's tables; `setup_bands`.
- **Constant and per room**, so it could be streamed or unpacked on entry:
  the packed room (14-190 bytes), its palette and bands (4 + 3 a split),
  its monster entries (at most 4 over all eggs, 4 bytes each) and their
  types, and the sprite frames those monsters, the truck, the train or a
  lift can show. That last part is the big one.

**Per-room sprite sets** (`roomsprites.py`, packed as decision 26 packs
them, with each mirror's twin in the same set). The frames a monster can
show follow `choose_frame`: right base+0..3, left base+4..7 (FAST +0,1 and
+2,3); RESPAWN monsters never turn; vertical movers and specials use
base+0..3; plus room 2's sitting dog and room 120's stopped dinosaur.

| Room | Packed | What |
|---|---|---|
| 120 | 956 | the dinosaur on its scooter: 2 frames, 450 + 506 |
| 111 | 854 | truck strips 580 + monsters |
| 2 | 842 | the dog: 4 running frames + sitting |
| 1 | 815 | truck strips + bird |
| 89 | 708 | 24 frames |
| 66 | 691 | 20 frames |
| mean / median | 263 / 264 | 10 rooms have none |

All 152 frames come to 6,045. The biggest room needs 956, the biggest room
together with its neighbours 2,045 (room 110).

## 2. The ideas, measured

### 2.1 Per-room records from disc (the one that works)

**The records** (`records.py`, `records.out`): each room's packed room,
sprite frames, frame list (3 bytes a frame), monster entries, palette and
bands.

- 120 records, 43,848 bytes in all. The largest is room 120 at 1,017
  bytes, so a **1K buffer** holds any room.
- Each record starting on a sector boundary: 228 sectors (23 tracks). 42
  rooms take 1 sector, 54 take 2, 18 take 3 and 6 take 4. With MENU and
  CE2, that fits a 40-track single-sided disc with room for saved games.
- In room order, neighbouring rooms are at most 3 tracks apart (1.0 on
  average). 96 of the 229 neighbouring pairs share a track.
- Every room's frames, packed as a set, unpack to the original's (checked
  by the script).

**Keeping the DFS alive for it** (`discprobe*.mjs`, outputs alongside).
Raw sector reads through OSWORD &7F on DFS 1.20, measured byte by byte:

| What | OSWORD &7F | OSFILE (for comparison) |
|---|---|---|
| NMI area | copies 27 bytes of NMI code to `&0D00-&0D1A` on every call | `&0D00-&0D4D` |
| `&0E00-&0FFF` (catalogue) | not needed | needed |
| Page `&10` | writes `&1073` and `&1080`, needs `&10D6`. Something in `&1081-&108F` is where it thinks the head is: spoil it and the read still works, but 400ms slower | writes `&1000-&103F` and more |
| `&1100-&18FF` (file buffers) | not needed | not needed |
| Zero page | writes `&A7 &B1 &B8 &BC-&BD` (DFS) and `&E7 &EC &EF-&F1 &FA-&FC` (MOS) | also `&B0-&CE` |
| Stack | 50 bytes | 46 bytes |
| Page 2 | of the vectors, only WORDV (`&020C`) must be the MOS's; the rest of `&0206-&0235` can hold tables. `&0236-&02FF` is needed | |
| Page 3, `&0D9F-&0DEF` | free (filled with junk, the read still works) | |
| `&0DF0-&0DFF` (ROM workspace table) | needed | |
| Interrupts | works with the game's own IRQ1V handler and the System VIA's interrupts off except VSync. The handler took all 32 VSyncs during a 632ms read, so the frame interrupt keeps running through a load | |

So the game can keep the DFS alive for raw reads at a small cost:

- a 2-byte hole for WORDV in page 2;
- LowState moved up to `&0D1B`, using the B's extended-vector area (a
  Model B-only build);
- about 48 bytes of page `&10` kept clear;
- 32 more bytes of stack;
- nothing live in the scratch zero page across the call. That is already
  so at room entry, provided the load comes before `draw_room` and
  `setup_bands`.

The 31-file limit of the DFS catalogue rules out a file per room. One file
of records, read by sector, avoids it. MENU (with the OS alive) can read
the catalogue to find where that file starts and pass that to the game, so
a `*COMPACT` doesn't break it.

**What a load costs.** Measured in jsbeeb with the DFS's own 8271
settings: step `&0C`, settle `&0A`, head load/unload `&C8`, so the head
unloads after 12 revolutions (2.4s). The records were laid out as above
from track 9, and a 20-step random walk between neighbouring rooms was read
in the game's interrupt set-up (`discprobe5.mjs`):

| Drive | Time in each room | Load per room: mean (range) |
|---|---|---|
| DFS default | 1.5s | 187ms (109-540) |
| DFS default | 5s | **769ms** (643-904): spin-up and head load every time |
| Head kept loaded (Specify, unload count `&F`) | 1.5s | 166ms (111-232) |
| Head kept loaded | 5s | **196ms** (31-292): rotational latency, plus a seek |

For comparison (`roomtime.mjs`), `enter_room` (draw and set up) takes
175-315ms now, 234ms on average over 15 rooms. The original's set-up takes
4.8-7.2 frames, 96-144ms (research, monsters.md). A streamed room change
would therefore take about **1.0s** with the DFS's settings and a normal
stay in a room, or about **0.4s** with the head kept loaded. jsbeeb's
dwell times land on whole revolutions, so its rotational latency repeats.
On real hardware it is uniform over 0-200ms, with about the same mean.

**The budget** (`budget_disc.py`, `budget_disc.out`), against the 2,889
bytes free then:

| | Bytes |
|---|---|
| + tile font, Harry's frames, `setup_bands`, colour maps, unpacker tables (from the bank) | 1,245 |
| + record buffer | 1,024 |
| + ~ loader: the OSWORD &7F call and retry, the frame-pointer patching, the monster entries | 250 |
| + record start sectors (a byte a room) | 120 |
| + what the game must keep of the mailbox (keys, RNG, flags, the OS bytes a BREAK keeps) | 45 |
| + high-score table and filename | 170 |
| + the DFS's needs: WORDV hole 2, stack 32, page `&10` ~48 (LowState into `&0D9F-&0DEF`: 0) | 82 |
| - monster table: each room's entries go in its record. The dog's swap becomes a flag, and the egg's limit is a comparison with the entry's index, which the record keeps | -1,014 |
| - ~ the bank's paging | -15 |
| **Net** | **1,907: 982 bytes left** (921 after the cheats) |
| Options: page 3 (free during a read; whether BREAK on a B leaves it alone needs checking, see decision 11) 256; monster types into the records 188; high scores kept on disc by MENU 170; start sectors as 2 bits a room 90 | up to ~1,690 left |

**Variants:**

- **Drive kept spinning.** Issue a Specify with an unload count of `&F` on
  entering play, at no cost in bytes. Loads drop from ~0.77s to ~0.2s,
  but the drive runs for the whole game: noise, and the head on the disc.
  It is 8271-specific. A 1770 (B+, 1770 DFS upgrades) stops its motor
  after 9 idle revolutions by itself, so there every load is cold.
- **Cache the previous room** with a second 1K buffer, taken from the
  spare: going back through the door you came in by is instant. The spare
  is just big enough for it.
- **Own 8271 driver and prefetch.** An NMI-driven read the game starts and
  doesn't wait for, issued when Harry nears an exit, into the second
  buffer. Most room changes would then be as quick as now. It costs ~250
  bytes of driver plus the second buffer, which is more than the spare
  without page 3 and the options. It works only on an 8271, not on a 1770
  or MMFS (a Gotek replaces only the drive, so it would work there). And
  it takes NMIs during play: about 20% of the CPU for each 16ms sector,
  which the slack covers (the worst stretch moving is 27,800 of 40,000
  cycles). An NMI landing in a band split's 8 writes would put the split a
  line late for a frame, and the writes have only about 2us to spare. It
  is the most work of the variants.

### 2.2 A 1-bit screen (MODE 4's pixels at 256 x 192)

**Bytes.** 6,144 from the screen, which becomes `&6800-&7FFF`. Then:

- ~500 of colour code and tables: `set_room_palette` 59, `set_logical`
  30, `attr_colours` 42, `cell_colours` 15, `cell_band` 18, the spread
  tables 32, the 2-bit halves in `draw_sprite` and `erase_image`, the
  palettes 120, the band data 176. It is less if bands stay.
- The attribute map is no longer needed for drawing, which frees 768 of OS
  workspace for tables.

About 7.4K in all.

**Colour** (`mono.py`, `mono.out`, scored like `tools/colourstats.py` on
the oracle's rooms; a cell may be drawn inverted when that shows more):

| Scheme | Scenery pixels in their own colour | Ink pixels only | Worst room |
|---|---|---|---|
| Now: 4 colours, bands (decision 24) | 99.48% | (~96%: 4 colours a room without bands score 99.50% and 96.0%) | |
| Black and white | 51.7% (many rooms have coloured paper) | | 0% |
| 2 colours a room | 94.3% | 70.5% | room 5, 79.8% |
| 2 colours in up to 3 bands (2 splits, as now) | 96.5% | | room 5, 84.4% |
| Logical 0 a room, logical 1 per character row (22 interrupts a frame, 8 ULA writes each) | 96.4% | 82.4% | room 5, 84.4% |

The figures for all pixels flatter it, since most pixels are paper. A
third of the scenery's detail changes colour with 2 colours a room. And
**every sprite takes its band's or row's ink**: Harry isn't yellow, and the
monsters and objects lose their colours. One side effect goes the other
way: the collision test would read a 1-bit screen as the original reads
its own, so decision 10's blind spot goes.

**Alone it doesn't close the gap**: see the waterfall in section 3. It is
also the most work of any idea: every drawing routine, the colour tools
(`mkrooms.py`) and the room checks.

### 2.3 Compression in RAM

ZX02 on each file (`ztrial.py`, `ztrial.out`):

| Data | Bytes | ZX02 |
|---|---|---|
| Sprite frames (packed, decision 26) | 6,339 | 3,894 (61%) |
| Sprite frames as the original stores them | 7,766 | 4,694 (60%) |
| Packed rooms | 6,845 | 6,364 (93%): no gain |
| Object graphics | 1,157 | 772 (67%) |
| Things | 1,024 | 877 (86%) |
| Monster table | 1,024 | 896 (88%) |
| Tile font | 480 | 350 (73%) |
| Visits | 121 | 78 |
| Thing types | 201 | 186 |

**Sprites unpacked per room.** A room needs random access by monster
graphic, so each graphic is compressed on its own. The 26 monster groups
come to 5,226 → 3,698 and the machine strips to 840 → 422. Resident that
is 4,120 compressed, plus a 956-byte buffer, the depacker (131 bytes, from
the port kit's notes) and a group index (~52): ~5,260 against 6,045 now,
**about 790 bytes back**. It is weak, because the biggest room's set (the
dinosaur) is a sixth of all the frames. Unpacking ~1K takes ~27ms at the
kit's 54 cycles a byte.

**Pre-shifted frames.** 16 of the 128 distinct frames are exact 2, 4 or 6
pixel shifts of another frame: the car's six, the hedgehog's, the dog's,
the spring's, the tortoise's and the ostrich's (976 raw bytes). Made at
room entry they'd save ~350 more. The rest are separate poses, as research
says: the walk cycle *is* the four offsets.

Objects (772 compressed) would need a cache of the room's object frames,
which change as things are carried in. ~300, speculative.

### 2.4 Scavenging

- **A Model B-only build**: page 3 (256) and `&0D9F-&0DEF` (81) are only
  kept for the Master's BREAK (decision 22). Page 3 is free during a disc
  read (measured). Whether OS 1.20's BREAK leaves page 3 alone needs
  re-checking: decision 11 used it before 22.
- **The mailbox**: the magic (35) goes, and of the mailbox's 225 the game
  needs 45 during play. The high-score table (150) and the filename (20)
  could live on disc, written by MENU.
- **Code**: two code-size passes have already taken 2K. Another might find
  ~300, not to be counted on.
- **MENU taking more**: the game's own text is ~180 bytes (the status
  labels, the carried things' names, "EGGS DELIVERED"). The rest of the
  game is play. ~100-200 at most.

### 2.5 Half measures that don't fit

- **Rooms only from disc** (sprites resident): ~7.2K back less the buffer
  and loader, so still **~4-5K short** with the monster table in the
  records.
- **Sprites only from disc** (rooms resident): ~6K back, so still **~6K
  short**.

## 3. The shortfall after each idea

**Without a disc**, applied cumulatively from 11,894:

| Step | Saves | Left short |
|---|---|---|
| Magic, and the mailbox trimmed (high scores on disc via MENU) | 215 | 11,679 |
| Model B only: page 3, `&0D9F-&0DEF` | 337 | 11,342 |
| Sprites ZX02-packed per graphic, unpacked per room | 786 | 10,556 |
| ~ Pre-shifted frames made at room entry | 350 | ~10,200 |
| ~ Code cuts | 300 | ~9,900 |
| MODE 4 pixels: a 6K screen | 6,144 | ~3,760 |
| ~ 1-bit drawing: colour code and tables | 500 | ~3,260 |
| Attribute map unused (768 of OS workspace takes tables) | 768 | ~2,490 |
| ~ Object graphics packed, with a cache | 300 | ~2,190 |
| ~ MENU takes the egg's text | 150 | **~2,040 short** |

**With per-room records from disc**, MODE 1 as now: **982 left** (921
after the cheats), and 1,238 with page 3 (section 2.1).

## 4. Ranked

| Approach | Bytes on a stock B | Fidelity | Speed and feel | Work (what it touches) |
|---|---|---|---|---|
| **Per-room records from disc** (OSWORD &7F) | fits, ~1.0-1.2K spare | none: rooms, graphics, colours, rules unchanged | room change ~1.0s (0.4s with the drive spinning); drive noise; disc stays in | a record builder (from `packrooms.py`, `mkgfx.py`, `mkrooms.py`), a loader, `setup_monsters` and the frame pointers, the memory map (LowState, page `&10`, the stack), MENU (no bank, find the file), handoff and state, the test tools |
| + drive kept spinning | 0 | none | pause ~0.2s on average, ~0.3s at worst | a Specify call |
| + previous-room cache | ~1K (the spare) | none | instant when going back | small |
| + own 8271 driver and prefetch | ~1.3K (more than the spare without page 3) | none | most changes as now | driver and prediction; 8271 only; NMIs in play |
| 1-bit screen, everything resident | ~2K short even with all of section 3 | colour: 94-96.5% of scenery pixels, 70-82% of ink; sprites in the band's colour | faster drawing | every drawing routine, the colour tools and checks |
| In-RAM packing alone | ~1.5-2.5K back | none | +~30ms at room entry | sprite unpacking, the group index |
| Rooms or sprites alone from disc | 4-6K short | | | |

## 5. What each compromise changes from the original

Each would be a numbered decision:

- **Rooms, their monsters and their sprite frames load from disc on
  entering a room** (a stock-B edition: revises 3 and 8 for that edition).
  The original changes rooms in 0.1-0.14s, silently. This takes ~1.0s, or
  ~0.4s with the drive spinning, with the drive heard. The disc must stay
  in the drive during play, so a load can fail. That is a state the
  original never has, which needs a message and a retry (in the status
  bar, say).
- **OS calls at room entry** (revises 11): one OSWORD &7F per room.
  Nothing visible, but it fixes the memory constraints of section 2.1.
- (Optional) **The drive spins all game**: shorter pauses, constant drive
  noise.
- (Optional) **Own disc driver**: 8271 machines only.
- (Not recommended) **A 1-bit screen**: colour per room or band, sprites in
  their band's colour. It revises decisions 1, 2, 15, 18 and 24, and still
  doesn't fit without cutting content.

A small mitigation for the pause's look: load before `cls`, so the old
room stays on screen during the load and then the new one is drawn, as
now.

## 6. Other machines

Matt has ruled out a B+ edition, a ROM (EPROM) edition and the Electron;
they're kept here only as the study found them.

- **A 16K EPROM in a free ROM socket of a B** (a stock B has two free
  sockets). Every byte in the bank is constant except the 225-byte
  mailbox, which can move to main RAM. So it fits with no compromise at
  all. It isn't stock, though: someone has to burn an EPROM or fit a ROM
  board. Emulators load it as a sideways ROM.
- **B+ (64K)**: 12K of paged RAM at `&8000-&AFFF`. The bank's 14,783 would
  need ~2.5K moved to main RAM: it fits, with ~0.4K spare. To check: that
  MOS 2.0 keeps the font at `&C000`, as decision 14 relies on, and the
  1770. Its shadow RAM doesn't help, as user code can't reach it (only
  code in `&C000-&DFFF` can).
- **B+128 and every Master** have sideways RAM already (decisions 8, 16).
- **Electron: no.** It has no 6845, so there is no 256 x 192 window: its
  MODE 1 is 20K, its MODE 4 10K at 320 x 256. Its CPU reads RAM at 1MHz
  and stalls during the display in MODEs 0-3. It has no VIA timers for the
  palette splits and no SN76489.
- **A cassette-only B: no.** It has nothing to stream from.

## 7. Recommendation

It is feasible as a **disc edition**, and only that way.

**The stock-B edition** would be:

- the same MODE 1 screen, colours, bands, rooms, monsters and rules;
- CE2DATA replaced by one file of 120 per-room records (228 sectors, room
  order), read with OSWORD &7F on entering each room;
- a 1K buffer; the tile font, Harry's frames, the unpacker's tables and
  `setup_bands` in main RAM;
- the monster table split into the records;
- the DFS kept just alive enough: WORDV, `&0D00-&0D1A`, a few bytes of
  page `&10`, and 50 bytes of stack;
- MENU passing on where the file starts.

It fits with ~1K to spare. The cost is the room change: ~1.0s, or ~0.4s
with the drive spinning. Build it from the same source under a flag, and
keep the sideways-RAM edition as the one that plays like the original.

If it's wanted, start with steps that don't need a disc:

1. Make `records.py` a real tool. Have the sideways-RAM build read rooms,
   monsters and frames from per-room records held in the bank, which
   proves the format against `roomcmp`, `screencmp` and `make passes`.
2. Add the OSWORD &7F loader and the memory moves under the flag. Measure
   it in jsbeeb and on a real B.
3. Choose whether the drive spins.
4. Only then consider the prefetching driver.

## Files

In [`tools/stockb/`](../tools/stockb/). They were written against
`25a57fd`; run them from the repository root after `make` (the Python with
`.venv/bin/python` where it uses SkoolKit), and run `mkdisc.py` before the
disc probes (it writes `tools/stockb/disc.ssd`, not committed).

| File | What |
|---|---|
| `budget.py`, `budget.out` | module-by-module sizes from the listing and symbols |
| `budget_disc.py`, `budget_disc.out` | the stock-B budget with per-room records |
| `ztrial.py`, `ztrial.out` | ZX02 on each data file |
| `roomsprites.py`, `roomsprites.out` | per-room sprite sets, room + neighbours, pre-shifted frames, per-group ZX02 |
| `records.py`, `records.out`, `records.idx` | per-room record sizes and the disc layout (room order); frames checked to unpack |
| `mono.py`, `mono.out` | colour cost of 1-bit schemes on the oracle's rooms |
| `mkdisc.py` | a 40-track test disc, each sector tagged with (track, sector) |
| `discprobe.mjs`, `discprobe.out` | OSWORD &7F and OSFILE footprints, warm and cold timings |
| `gen_probe2.py`, `discprobe2.mjs`, `discprobe2.out` | the DFS's byte in page `&10`, its 8271 settings, head kept loaded |
| `discprobe3.mjs`, `discprobe3.out` | OSWORD &7F in the game's conditions (IRQ1V, page 2, LowState, code around page `&10`) |
| `discprobe4.mjs`, `discprobe4.out` | the speed-sensitive byte in `&1081-&108F` (two runs, the script holds the second's regions) |
| `discprobe5.mjs`, `discprobe5.out` | a random walk loading real record sizes: DFS default and head kept loaded, 1.5s and 5s a room |
| `discprobe6.mjs`, `discprobe6.out` | page 3, `&0236-&02FF`, `&0D9F-&0DEF`, `&0DF0-&0DFF` |
| `roomtime.mjs`, `roomtime.out` | the port's `enter_room` time now |
