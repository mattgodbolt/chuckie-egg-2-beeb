# Optimising this code: what the fleet learnt

Nine agents went through the source in October 2026 looking for bytes
and cycles (a byte saved in main RAM is a byte more of CE2S's room cache,
and room for new things like music). This is what kept coming up, to
apply anywhere. The findings themselves went in as commits.

## How to look (why this pass found three times the earlier ones)

Earlier squeezes were aimed at a number (the cache past 1,021; claw back
what a fix cost) and stopped when it was reached: the big structural
moves, a skim of the rest. This pass found about 1,200 bytes in ~9K of
resident code, nearly all of it 1-5 bytes at a time, each a proof about
one instruction. What made the difference:

1. **Exhaustive, not opportunistic.** Every routine, a dozen instructions
   at a time, each asked the same questions. Split the code so each
   reader owns a few hundred lines and can afford to be thorough.
2. **A checklist to search with** (the sections below): test each line
   against each pattern, rather than waiting to notice something.
3. **The measuring loop in the reader's hands**: build, read the arena,
   run the exact oracles (`screencmp`, `make passes`, `roomcmp`). Proving
   a carry is known is only worth it if a test catches you when you're
   wrong; with them, go round again until a round finds little.
4. **Question the data, not just the code.** The biggest single win came
   from asking of every resident table who reads it and when: only on
   room entry (into the records), a run of numbers (a range, not a
   table), or left behind by a format change (now redundant).
5. **Shared structures collide.** Tables several passes reshape
   (`band_ula`, the frame table, the scratch zero page, the reader's slot)
   need one owner, or the passes run one after another.

## Space first, where it counts

- **Every byte of main-RAM code or data is a byte of CE2S's cache.**
  Shared code first: it helps both editions. Measure the arena
  (`make STREAM=1` prints it) with a fixed `BUILD=`, as the stamp's
  length moves it byte for byte.
- **Savings are quantised by alignment pads.** `band_ula` mustn't cross
  a page, so main.6502 pads 0-11 bytes before it: a saving can vanish or
  double depending on where the code ends. Tables that must stay within a
  page (`spread_lo`, `spread_rev`, `band_ula`) move when code before them
  shrinks; put them first, where nothing earlier changes.
- **Data only room set-up reads belongs in the rooms' records**, not
  resident (palettes, band maps, monster types). The records are the
  overlay system. Data read everywhere stays resident.
- **After a format change, look for what it left redundant** (group
  headers kept every frame's number after the lookup stopped using it),
  and for the limits it can hit (`room_len4`'s 1,024-byte cap).
- **Recompute rather than store** when it's cheap and rare (item lengths
  from `room_len4`), and drop flags that duplicate other state (`ld_on`
  was `fdc_state` not 0).

- **Look for slack in every fixed region**, not just the code: the fixed
  zero page's tail, LowState's tail, the bytes the MOS's IRQ entry leaves
  at the top of page 0, page 1 under a stack measured again, and the
  variables a round leaves unused. A variable moved into zero page saves
  its bytes of main RAM and a byte at every access but `abs,Y` (`LDA`/`STA`
  have no `zp,Y`; `LDX`/`STX` do, and `STX zp,Y` replaces
  `PHA : TXA : STA abs,Y : PLA`). Swap by use: a test-only variable gave
  its saved zero-page byte to one used often.
- **A table's place can make pads go away for good**: `band_ula`, which
  mustn't cross a page, now starts the `Code` section.
- **Recursion hides from a measured stack**: a routine that recurses on
  the data (`add_score`, a level a carried digit) only goes deep when the
  data does. Bound it from the code, or make it a loop.

## Flags and registers already known

- **The carry is often known.** After `CMP` and an untaken `BNE`, C is
  set; after `ASL` or `ADC` of small values, clear; after `LSR` and an
  untaken `BCC`, set. So `CLC : ADC #k` becomes `ADC #k-1` with C set, or
  `LDA #const`; `SEC : SBC #k` becomes `SBC #k-1` with C clear (`SBC`
  with C clear takes one more). Comment each reliance: `(C clear: ...)`.
- **Move a loop's `CLC` into the rare carry path** (`INC hi : CLC`).
- **A is known too**: after `AND : BNE` falls through it's 0, so
  `STA x` needs no `LDA #0`, and a `BEQ` there is always taken.
- **Return status in a flag the last instruction already sets** (N from
  `LDY` of a small value, Z from `INC` of a nonzero one) rather than
  `CLC`/`SEC` and an RTS each. `STA`/`STX` set no flags: check which
  instruction set the flag before trusting it. And check that a caller
  reads it at all: neither of `item_add`'s read its carry.
- **Prove a borrow or carry can't happen** before keeping a 16-bit
  fix-up: a nonzero column means a nonzero low byte.
- **Look for dead saves and reloads**: X saved around calls that keep
  it, `LDX m_cur` where every caller has it in X already, scratch copies
  of permanent zero page (`vE` was always `h_yf`), stores no path reads.

## Layout and control flow

- **Change nothing until it fits**: a search that undoes its own work on
  failure (`item_add` dropping items, then putting them back from the
  stack) costs pushes and pops on every path; work in scratch and commit
  at the end.
- **Fall through instead of jumping**: order routines so one falls into
  the next (`truck_strips` into `draw_strips`, `noise` into `rng`). Turn
  `JSR x : RTS` into `JMP x`. Inline routines with one caller.
- **Branch to a nearby `JMP common`** rather than writing another JMP.
  Baron's scoped labels (`BNE wipe_lights.done`) let routines share an
  RTS.
- **Always-taken branches confuse baron's allocator**: it follows both
  ways, so at the end of a `{ }` scope it thinks control falls into the
  next routine ("No free zero-page byte", "held live across recursion").
  Use `JMP` there, or put the branch where its fall-through is harmless.
- **Jump tables**: put the second entry's code right after the first
  JMP.

## Data and addressing

- **No pointer copies of zero-page records**: `(zp),Y` and `(zp,X)`
  read through them directly (`LDA (3,X)` for a sprite record).
- **Pass pointers in X:A** and let the callee store them.
- **Keep pointers as addresses**, not indices a routine adds a base to
  on every call (`tcell`).
- **Split interleaved word tables into lo/hi tables** a byte index can
  address: no `ASL`, no page-crossing branch, no `PHP`/`PLP`.
- **Parallel arrays a fixed stride apart** let one routine serve two
  (`abs,Y` with Y = X or X+NM, guarded by an `ASSERT`); end loops with
  `CPX #k*NI : BCC`; strided tables become parallel arrays with a
  `DEX : BPL` search.
- **Page-aligned maps**: `ORA #HI(map)` instead of `CLC : ADC` when the
  page's low bits are clear (`ASSERT` it), or self-modify the high byte
  and `LDY cell`; range-check the 16-bit address instead of computing a
  row number.
- **Store what the readers use**: `band_cmaps` holds pixel bytes, not
  colours every reader looked up.
- **AND/ORA/EOR instead of ADC/SBC** when bits don't overlap
  (`AND #&FC : CMP #&20` for &20-&23); `LSR` then `EOR` tests two
  adjacent codes, keeping which in the carry; OR the cells together when
  only "any blocked" matters.
- **Single-bit read-modify-writes**: `LSR : ASL` clears bit 0,
  `LSR : SEC : ROL` sets it, `INC` sets a bit known to be clear.
- **Templates and a copy loop** for many stores to a block.
- **`ZA_DISCARD`** instead of zeroing variables to please the allocator;
  but zero-page autos in anything reachable from `wait_vsync` stack on
  its deepest caller.

## Loops

- **Count down to 0** (`DEY : BPL`) and offset the base pointer instead
  of comparing with an end.
- **Hoist invariants** out of searches, start at -1 with `INY` at the
  top, precompute per call rather than per row.

## Comments

- **No figures the build computes** in comments or docs (addresses,
  sizes, the pool's reach, the stack's depth, free bytes): name the
  symbol, `ASSERT` the property, or point at the dated decision. A
  saving moves every such figure, so a copied one is wrong at once.

## Testing changes like these

- `make check` and `make check STREAM=1`, on the B and the Master: a
  saving in main RAM changes CE2S's cache, so check both editions. If
  CE2S fails, pad the arena back with `SKIP n` before `code_end` to tell
  a patch bug from a cache-size one.
- `tools/screencmp.mjs` old disc against new catches frame differences
  the passes don't log (it finds nowhere to stand Harry in rooms 1-4 and
  71, so those compare nothing).
- Targeted fuzz against the original (`fuzz.run_case` with a start
  state) for ropes, ladders and lifts, which random walks barely reach.
- A state dump against the base build (bands, palettes, frame tables)
  when a big edit fails: `roomcmp` doesn't see IRQ or palette state.
- IRQ changes: time each palette write relative to VSync, not
  screenshots; retune in whole microseconds.
- Pure logic (the cache) can be run side by side on a 6502 core
  (`m6502.py`, `cachediff.py` from that pass), with the arenas padded to
  the same size: jsbeeb's random walks diverge on timing alone.
- A `;` comment in the middle of a colon-separated line swallows the
  rest of the line, silently.
- A copy loop ending `DEX : BPL` copies one byte once its count passes
  128: the reader's slot grew past it and CE2S crashed at its first read.
- Room-change times on the B (`roomwait.mjs`) move with any change to
  the reader's timing, the cache's logic unchanged: a background read
  misses a revolution when its next sector's command comes late. Prove
  the logic on the 6502 core first (`cachediff`, equal arenas, and a
  small arena to reach the give-up path), then compare the times; the
  Master's (1770) agree to the millisecond.
- Give scratch worktrees unique names, and never `pkill -f` a pattern
  another run might share.
