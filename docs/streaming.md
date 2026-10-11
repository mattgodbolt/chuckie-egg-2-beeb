# A stock Model B edition: rooms streamed from disc in the background

> **The plan, 2026-10-10.** Steps 1 and 2 are built (decisions 28, 29):
> CE2S plays, waiting for each room. It replaces
> `docs/stock-b.md`'s recommendation (OSWORD &7F on entering a room, a
> second's pause each time) with the variant that study ranked last for
> work and first for feel: our own NMI-driven disc driver, reading while
> the game plays, with a cache of rooms. Tracked as
> [issue #1](https://github.com/mattgodbolt/chuckie-egg-2-beeb/issues/1).

The challenge: the game on a regular 32K Model B, with no sideways RAM,
using the bitshifters' tricks. What Matt asked for:

- **Two editions from one source**: the sideways-RAM edition as now, and
  the streaming edition. A choice of either, on the same disc.
- **Both play on a Model B and on a Master 128**, because Matt plays on
  his real Master. On a Master the streaming edition keeps to the stock
  B's memory, so playing it there tests the B edition. It uses the
  Master's 1770 instead of the B's 8271.
- **Room changes as quick as now**: rooms cached, and the neighbours of
  the room Harry is in loaded before he reaches them.

## What was found

Three studies, scripts and outputs in [`tools/stockb/`](../tools/stockb/):
a survey of the known tricks, the budget and room graph re-measured on
build `8c630c6` (`budget_stream.py`, `graph.py`, `cache.py`), and a working
driver (`tools/stockb/nmi/`, its `REPORT.md` has the code and tables).

### The tricks

- **quicdisc** is scarybeasts' asynchronous raw-FDC track reader
  ([scarybeasts/misc](https://github.com/scarybeasts/misc/tree/master/quicdisc)):
  calls return at once, an NMI routine at `&0D00` takes the bytes, and it
  detects the 8271, a B's 1770 board or a Master's 1770 by poking their
  registers. His `sampstream` in the same repository double-buffers track
  reads under a playing sample, which is the shape of a prefetch. His note
  from real hardware: turn off the 8271's head unload, which was "super
  picky" about starting again.
- Eben Upton's [beebgame](https://github.com/ebenupton/beebgame) (MIT) has
  a synchronous 8271 and 1770 driver, NMI stub at `&0D00`.
- The other bitshifters productions (Bad Apple, STNICCC) and Paradroid
  read through the DFS (OSWORD &7F), and wait.
- scarybeasts' advice on Kieran's 1942 NMI routine, and Tom Seddon's: save
  A in the operand of an `LDA #` at the end (`STA restore+1` ...
  `LDA #0`), 6 cycles and no zero-page byte; read one 256-byte sector a
  command, so the routine needn't carry into the next page. 128-byte
  sectors would spread the cost thinner, but an `.ssd` can't hold them
  (only HFE, SCP, FSD can), so MMFS and most emulators couldn't load the
  disc. The plan keeps 256-byte sectors on a plain `.ssd`.

### The driver works, in jsbeeb, on both machines

One binary, the controller chosen at start-up. After that, no OS or DFS
call; the foreground loop keeps running and every VSync and timer
interrupt is taken during reads; every sector checked against a tagged
disc. 445 bytes (could be trimmed). The NMI routine is the same for both
controllers but for the data register (`&FE84` on the 8271, `&FE2B` on
the Master's 1770), 35 cycles a byte of the 128 between bytes:

```
&0D00  STA restore+1   ; A kept in the LDA # below
       LDA &FE84       ; patched to &FE2B on a Master
dst    STA &3000       ; the page patched for each read
       INC dst+1
       BEQ last        ; the 256th byte: the next NMI is the command's end
restore LDA #0
       RTI
```

| | 8271 (B) | 1770 (Master) |
|---|---|---|
| CPU taken during a sector | 24% | 24% |
| A sector, warm; a whole track | 19.8ms; one revolution | the same |
| Seek, per track | 24ms (the DFS's step), 6ms possible | 6ms |
| A cold read | 236ms | 1.3s (the motor's spin-up) |
| After 3s idle, kept alive each second | 28ms | 29ms |

Lessons it paid for: the 8271 needs its mode register set for no DMA and
its bad-track registers cleared; it latches "not ready", which only a Read
Drive Status clears; an unload count of 0 hangs a B for good; the result
must be read before the next command (the 6502's NMI is edge-triggered).
The 1770 can't seek within a read, and its motor stops after 9 idle
revolutions unless a Force Interrupt restarts the count.

jsbeeb is close to the chip (its 8271 follows the reverse-engineered
microcode) but kinder: commands accepted instantly, no CRC errors, no
track skew, rotation locked to emulated time. Real hardware is the test
that counts: Matt's Master, and a B if one can be found.

### The budget

- Main RAM has **2,766** bytes free; the sideways bank holds **14,784**.
  The DFS needs nothing once we drive the controller (the old plan spent
  82 bytes keeping it alive). Moving the bank's resident part (tile font,
  Harry's frames, `setup_bands`, colour maps, unpacker tables) down, and
  the monster table out into the records, leaves **~1,580 bytes for a
  cache**, **~1,940** with two small moves (monster types into the
  records; MENU keeping the high scores in a file). A B-only memory map
  could add 337 (page 3, `&0D9F-&0DEF`: BREAK on a B leaves them alone,
  measured), but then the Master wouldn't test the B's budget, so not at
  first.
- **The rooms are less connected than assumed**: 288 exits, at most 4 a
  room, 2.4 on average, all ±1 and ±10 except 80 ↔ 71. A death goes back
  to the checkpoint room after a 2.2s tune, which is time to load it.
- **A room's data splits into a body and its graphics.** A body (packed
  room, palette and bands, monster entries, which graphics) is 73 bytes on
  average, 194 at most. The graphics are 30 groups (one per monster
  graphic, and the truck, train, lift and the sitting dog), shared between
  rooms, 963 bytes at most (the dinosaur). A room change fetches 3.5
  sectors on average.
- **Cache size against rooms with all their neighbours ready:**

  | Cache | Rooms always ready |
  |---|---|
  | 1,582 | 109 of 120 |
  | 1,940 | 118 (114 with a sector free for the read in flight) |
  | 2,304 | 120 |

  Those that miss (rooms 1, 2, 8, 19, 56, 69 at 1,940) are rooms beside
  the truck, the dog, the dinosaur's room: the neighbour Harry is heading
  for is loaded first, so a miss needs him to turn back towards a far
  exit within a second or so.
- **The CPU has room**: the slowest stretch between waits for VSync,
  Harry moving, is 27,892 cycles of the 40,000 in a three-frame pass; a
  frame's worth of sector adds 9,472.

### The palette splits are the hard part

An NMI can arrive just as the interrupt is about to write a split's
colours, delaying it by up to 18us; the split windows have 12us to spare
late as set now. During a load, a band's first scan line could show its
left end in the old colours for a frame. Neither controller can be paused
mid-sector, and the disc isn't locked to the frame. To try, in order:
setting both splits at the early edge of their windows (20us to spare,
tight), only while a read is in flight; choosing when reads start, since
each sector's 20ms of NMIs is known in advance; accepting the rest as a
part-line glitch for a frame, only while loading.

## The design

- **One records file, `CE2REC`**: every room body and graphics group,
  packed, with a small index. The sideways edition loads it whole into the
  bank (it replaces most of `CE2DATA`) and always finds what it wants; the
  streaming edition reads the sectors holding an item. One format, so the
  sideways edition proves it.
- **The cache** (streaming edition): one arena of ~1.6-1.9K in main RAM,
  holding bodies and groups packed from the bottom; a read lands at the
  top in whole sectors, then is trimmed. A table of ~16 entries (item,
  address, length, state, last use). Compacted only when an allocation
  fails with no read in flight, re-pointing the current room's frames.
- **What it wants**: the current room's body and groups, and every
  neighbour's. The body of the room Harry is in stays (a death redraws
  it).
- **Prefetch**: the driver is stepped from the VSync interrupt, so loading
  carries on through the death tune and the next-egg screen. Each pass
  orders the neighbours: first the one behind the exit Harry is nearest or
  moving towards (or below, falling), then the rest by distance. A read
  under way is never abandoned. Evict the least recently used item nobody
  wanted needs.
- **A miss** (Harry reaches a room not yet loaded, or a resumed game, or
  the cheat's room skip): the old room stays on screen and the load is
  waited for: ~0.2-0.5s warm on either machine, ~1.3s on a Master with the
  motor stopped. A read error is retried; a disc taken out shows a message
  in the status bar until it is put back.
- **The drive**: kept going while there are reads to do, then let rest
  after ~3s, so it is quiet while Harry stays in a room. (Whether to keep
  it spinning all game is a choice to make on hardware, by ear.)
- **The editions on the disc**: `CE2` and `CE2S` (built with `-D
  STREAM=1`), `MENU`, `CE2REC`. MENU runs `CE2` when it finds sideways
  RAM, `CE2S` otherwise, and a hidden key on the menu forces `CE2S`, so a
  Master or a B with sideways RAM can play it. MENU tells the game which
  controller (OSBYTE 0: a B or a Master) and where `CE2REC` starts (from
  the catalogue, so `*COMPACT` doesn't break it).
- **Not supported by the streaming edition**: MMFS (it has no disc
  controller to drive; a machine with MMFS and sideways RAM plays `CE2`),
  and 1770 boards in a B other than at Acorn's addresses, until someone
  asks. A Gotek works, as it stands in for the drive.

## Steps

Each one working, checked and committed before the next. Every
compromise becomes a numbered decision.

1. **The records, in the sideways edition.** `tools/mkrecords.py` writes
   `CE2REC` from `src/data/`. The game finds a room's body, monsters and
   graphics through it: the monster table splits into the bodies (the
   egg's limit becomes a comparison with an entry's index, the dog's sit
   a flag), frame pointers are filled in when a room is entered, and the
   resident data moves down to main RAM. Proved by `roomcmp`, `screencmp`
   and `make passes`: nothing on screen or in play changes.
2. **The driver in the game**, behind `-D STREAM=1`: LowState moves up
   from `&0D00` for the NMI routine; the bank goes; a blocking fetch into
   a single buffer first, so every room change waits. MENU's choice of
   edition and its hand-over of the controller and the file. `make check
   STREAM=1` on both machines.
3. **The cache and the prefetch.** Measure misses over the scenarios and
   random walks; tune the order.
4. **The splits.** Measure the glitch with reads in flight
   (`tools/screencmp.mjs` can't see it; a scan-line probe in jsbeeb can),
   and try the mitigations above.
5. **The drive's behaviour and errors**: rest and keep-alive, retries,
   the disc taken out.
6. **Real hardware**: Matt's Master, with a Gotek and with a real drive;
   a Model B if one turns up.
