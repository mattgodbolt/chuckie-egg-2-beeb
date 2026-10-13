# A stock Model B edition: rooms streamed from disc in the background

> **Built.** This began as the plan of 2026-10-10 and is now CE2S, the
> streaming edition (decision 29, and the decisions after it that name
> CE2S), which plays on a 32K Model B and on a Master without touching
> sideways RAM. It closed
> [issue #1](https://github.com/mattgodbolt/chuckie-egg-2-beeb/issues/1).
> It replaced `docs/stock-b.md`'s recommendation (OSWORD &7F on entering a
> room, a second's pause each time) with the variant that study ranked
> last for work and first for feel: our own NMI-driven disc reader, reading
> while the game plays, with a cache of rooms. The findings below are the
> studies the plan was made from; [As built](#as-built) is what the code
> does now.

The challenge was to get the game onto a regular 32K Model B, with no
sideways RAM, using the bitshifters' tricks. Matt asked for two editions
from one source, the sideways-RAM edition as it was and a streaming one,
both on the same disc. Both had to play on a Model B and on a Master 128,
because Matt plays on a real Master. On a Master the streaming edition
keeps to the stock B's memory, so playing it there tests the B edition,
and it drives the Master's 1770 instead of the B's 8271. And room changes
had to stay as quick as they were, which meant caching rooms and loading
the neighbours of Harry's room before he reaches them.

## What was found

There were three studies, with their scripts and outputs in
[`tools/stockb/`](../tools/stockb/): a survey of the known tricks, the
budget and room graph re-measured on build `8c630c6` (`budget_stream.py`,
`graph.py`, `cache.py`), and a working prototype driver
(`tools/stockb/nmi/`, whose `REPORT.md` has the code and tables). The
figures in this section are from those studies, on 2026-10-10.

### The tricks

- **quicdisc** is scarybeasts' asynchronous raw-FDC track reader
  ([scarybeasts/misc](https://github.com/scarybeasts/misc/tree/master/quicdisc)).
  Its calls return at once, an NMI routine at `&0D00` takes the bytes, and
  it tells the 8271, a B's 1770 board and a Master's 1770 apart by poking
  their registers. The same repository's `sampstream`
  double-buffers track reads under a playing sample, which is the shape of
  a prefetch. A note there from real hardware says to turn off the 8271's head
  unload, which was "super picky" about starting again.
- Eben Upton's [beebgame](https://github.com/ebenupton/beebgame) (MIT) has
  a synchronous 8271 and 1770 driver, with its NMI stub at `&0D00`.
- The other bitshifters productions (Bad Apple, STNICCC) and Paradroid
  read through the DFS with OSWORD &7F, and wait.
- scarybeasts and Tom Seddon both advised on Kieran's 1942 NMI routine.
  Save A in the operand of an `LDA #` at the end (`STA restore+1` ...
  `LDA #0`), which costs 6 cycles and no zero-page byte, and read one
  256-byte sector a command so the routine needn't carry into the next
  page. 128-byte sectors would spread the cost thinner, but an `.ssd` can't
  hold them (only HFE, SCP and FSD can), so MMFS and most emulators
  couldn't load the disc. The edition keeps 256-byte sectors on a plain
  `.ssd`.

### The prototype works, in jsbeeb, on both machines

It is one binary, with the controller chosen at start-up. After that it
makes no OS or DFS call, the foreground loop keeps running, and every VSync
and timer interrupt is taken during reads. Every sector was checked against
a tagged disc. The NMI routine is the same for both controllers except for
the data register (`&FE84` on the 8271, `&FE2B` on the Master's 1770), and
takes 35 of the 128 cycles between bytes:

```
&0D00  STA restore+1   ; A kept in the LDA # below
       LDA &FE84       ; patched to &FE2B on a Master
dst    STA &3000       ; the page patched for each read
       INC dst+1
       BEQ last        ; the 256th byte: the next NMI is the command's end
restore LDA #0
       RTI
```

(The game's own routine, in `startup.6502`, has grown a count of the bytes
wanted so that it stores a sector straight into place: decision 35.)

| | 8271 (B) | 1770 (Master) |
|---|---|---|
| CPU taken during a sector | 24% | 24% |
| A sector, warm; a whole track | 19.8ms; one revolution | the same |
| Seek, per track | 24ms (the DFS's step), 6ms possible | 6ms |
| A cold read | 236ms | 1.3s (the motor's spin-up) |
| After 3s idle, kept alive each second | 28ms | 29ms |

It paid for some lessons. The 8271 needs its mode register set for no DMA
and its bad-track registers cleared. It latches "not ready", which only a
Read Drive Status clears, an unload count of 0 hangs a B for good, and its
result must be read before the next command, because the 6502's NMI is
edge-triggered. The 1770 can't seek within a read, and its motor stops
after 9 idle revolutions unless a Force Interrupt restarts the count.

jsbeeb is close to the chip (its 8271 follows the reverse-engineered
microcode), but kinder than the real thing: it accepts commands instantly
and has no CRC errors, no track skew, and rotation locked to emulated time.
Real hardware is the test that counts.

### The budget

- Main RAM had 2,766 bytes free and the sideways bank held 14,784. The DFS
  needs nothing once the game drives the controller itself (the old plan
  spent 82 bytes keeping it alive). Moving the bank's resident part down
  (the tile font, Harry's frames, `setup_bands`, the colour maps and the
  unpacker's tables), and moving the monster table out into the records,
  would leave about 1,580 bytes for a cache. Two small moves would make it
  about 1,940: the monster types into the records (decision 37) and the
  high scores kept in a file by MENU (decisions 38 and 41). A B-only
  memory map could add 337 more from page 3 and `&0D9F-&0DEF`, which BREAK
  on a B leaves alone, but then the Master wouldn't test the B's budget.
- The rooms are less connected than had been assumed. There are 288 exits,
  at most 4 a room and 2.4 on average, all of them ±1 and ±10 except
  80 ↔ 71. A death goes back to the checkpoint room after a 2.2s tune,
  which is time enough to load it.
- A room's data splits into a body and its graphics. A body (the packed
  room, palette and bands, monster entries, and which graphics it uses)
  is 73 bytes on average and 194 at most. The graphics are 30 groups, one
  per monster graphic plus the truck, the train, the lifts and the sitting
  dog, shared between rooms and up to 963 bytes (the dinosaur). A room
  change would fetch 3.5 sectors on average.
- The cache's size against the rooms that would have all their neighbours
  ready:

  | Cache | Rooms always ready |
  |---|---|
  | 1,582 | 109 of 120 |
  | 1,940 | 118 (114 with a sector free for the read in flight) |
  | 2,304 | 120 |

  At 1,940 the ones that miss (rooms 1, 2, 8, 19, 56 and 69) are beside
  the truck, the dog or the dinosaur's room. The neighbour Harry is
  heading for is loaded first, so a miss needs him to turn back towards a
  far exit within a second or so.
- The CPU has room. The slowest stretch between waits for VSync, with
  Harry moving, was 27,892 cycles of a frame's 40,000, and a frame's worth
  of sector adds 9,472.

### The palette splits are the hard part

An NMI can arrive just as the interrupt is about to write a split's
colours and delay it by up to 18us, while the split windows had 12us to
spare on the late side. So during a load a band's first scan line could
show its left end in the old colours for a frame. Neither controller can
be paused mid-sector, and the disc isn't locked to the frame. The ideas, in
the order to try them, were to set both splits at the early edge of their
windows while a read is in flight (20us to spare, which is tight), to
choose when reads start, since each sector's 20ms of NMIs is known in
advance, and otherwise to accept a part-line glitch for a frame while
loading.

## As built

- **The files.** The plan had one records file, `CE2REC`, for both
  editions. As built, CE2 keeps the per-room records in the bank, loaded
  from `CE2DATA` (decision 28), and CE2S reads them from `CE2ROOM`
  (`src/data/roomrecs.bin`), where each room's body and graphics groups are
  together, so a room is one read (decision 35). Each record starts a
  sector and none crosses a track. A graphics group shared by several rooms
  is on the disc once for each. CE2S's records also carry what only room
  set-up reads: the monster types, palettes and band maps (decision 37),
  and the fixed things' graphics, types and places (decisions 42-44).
  `tools/ssdmerge.py` puts `CE2ROOM` on the disc as it is, starting on a
  track.
- **The cache** (`src/disc.6502`) holds whole rooms in one arena, the
  main RAM between the code and the mailbox, with a small table of room,
  address and last use. On entering a room `arrange` sorts the rooms by
  when they were last used, through screen memory with the display
  blanked, so that the room being entered is at the bottom and the oldest
  at the top. Room for a read is made by dropping rooms from the top, never
  one this visit uses, so nothing the game points into moves while it
  plays (decision 34).
- **Reading ahead** happens while the game waits for VSync (`wait_vsync`
  calls `disc_tick`). It takes the room behind the exit Harry is nearest
  or heading for first: the distance to each exit is shortened when he
  faces it, and halved upwards when he's climbing or downwards when he's
  falling. Then it takes the room's other neighbours, if they fit. What it
  finds or reads is kept for the visit, so Harry turning about doesn't read
  two rooms over and over.
- **A miss** happens when Harry reaches a room that isn't in, or on a
  resumed game, or with the cheats' room skip. The game waits for the read
  with the display blanked (decision 31), where the plan had the old room
  stay on screen.
- **The toy** (decision 45): only this egg's toy's nine pictures are in
  main RAM, in `toy_slot`. The four toys' blocks are items in `CE2ROOM`
  from `TOY_ITEM` on, placed first on the disc so that a new egg's read and
  room 1's are on the same track. `toy_load` reads the egg's block with the
  cache's own reader (`item_place`, `fdc_read`, `disc_wait`), the game
  waiting, when an egg starts and when a saved game carries on. It lands
  outside the arena, so no room is dropped.
- **The drive** isn't kept going. Matt found it running all game "super
  annoying" (decision 35), so the 8271's head unloads after 14 idle
  revolutions and the 1770 stops its motor by itself. A read that starts
  from cold pays for that, more so on the Master.
- **Errors.** A sector that fails is read again. On the 8271, "not ready"
  gets a Read Drive Status and half a second's wait before the next try (a
  B makes a drive ready only on the second index pulse after selecting
  it), and any other error seeks to track 0 first, as the head may not be
  where the 8271 thinks. The plan's message in the status bar for a disc
  taken out wasn't built.
- **The editions on the disc**: `MENU`, `CE2`, `CE2DATA`, `CE2S` (the same
  source with `-D STREAM=1`), `CE2ROOM` and `CE2HI`. MENU runs `CE2` when
  it finds sideways RAM and `CE2S` otherwise. With sideways RAM, D on the
  menu switches to `CE2S` (decision 32), so a Master can play it. MENU tells
  the game which controller to drive (OSBYTE 0 says whether it's a B or a
  Master) and the track `CE2ROOM` starts on, from the catalogue so that
  `*COMPACT` doesn't break it, and refuses to start if the file has moved
  off a track's start. CE2S keeps its mailbox at the top of main RAM
  (`MB_STREAM`; `docs/memory-map.md`).
- **Not supported**: MMFS, which has no disc controller to drive (a
  machine with MMFS and sideways RAM plays `CE2`), and 1770 boards in a B,
  which the game doesn't look for. A Gotek works, as it stands in for the
  drive.

## The steps

Each was to be working, checked and committed before the next, with every
compromise a numbered decision.

1. **The records, in the sideways edition** (decision 28). Done. The game
   finds a room's body, monsters and graphics through the records, and
   the resident data moved down to main RAM. `roomcmp`, `screencmp` and
   `make passes` showed nothing on screen or in play changed.
2. **The reader in the game**, behind `-D STREAM=1` (decision 29). Done.
   LowState moved up from `&0D00` to leave room for the NMI routine, the
   bank went, and MENU chooses the edition and hands over the controller
   and the file. `make check STREAM=1` runs on both machines, and CI runs
   it too.
3. **The cache and reading ahead** (decisions 31, 34 and 35). Done, and
   then made bigger by later decisions that moved data out of main RAM
   (36-45).
4. **The splits.** Not done: the glitch with reads in flight hasn't been
   measured (`tools/screencmp.mjs` can't see it, though a scan-line probe
   in jsbeeb could), and none of the mitigations above is in.
5. **The drive's behaviour and errors.** Partly done, as above: the drive
   rests, reads are retried, and the 8271's not-ready and lost-head cases
   recover. There is no message for a disc taken out.
6. **Real hardware.** The 1770 reader waits after each command because a
   real WD1770's status isn't valid straight away, which jsbeeb doesn't
   model (decision 34). CE2 has run on Matt's real Master (the journal's
   "On a real Master"); this file has no record of CE2S on real hardware.
