# Optimising this code: what the fleet learnt

In October 2026 nine agents went through the source looking for bytes
and cycles, and two smaller rounds followed (the journal has them). A byte
saved in main RAM is a byte more of CE2S's room cache, and room for new
things such as the music. This is what kept coming up, and it applies
anywhere. The findings themselves went in as commits.

## How to look

Earlier squeezes aimed at a number, such as a cache big enough for a
pair of rooms or clawing back what a fix cost, and stopped when they
reached it, with the big structural moves done and the rest skimmed. The
fleet found several times as much, nearly all of it 1-5 bytes at a time,
each a proof about one instruction. What made the difference:

1. **Be exhaustive.** Every routine was read a dozen instructions at a
   time, with the same questions asked of each. Split the code so that
   each reader owns a few hundred lines and can afford to be thorough.
2. **Search with a checklist** (the sections below). Test each line
   against each pattern instead of waiting to notice something.
3. **Give the reader the measuring loop**: build, read the arena's size,
   and run the exact oracles (`screencmp`, `make passes`, `roomcmp`).
   Proving a carry is known is only worth it if a test catches you when
   you're wrong. With the tests to hand, go round again until a round
   finds little.
4. **Question the data as well as the code.** The biggest single win came
   from asking who reads each resident table, and when. A table read only
   on entering a room can go into the records, a run of numbers can be a
   range, and a format change can leave a table redundant.
5. **Shared structures collide.** Tables that several readers reshape
   (`band_ula`, the frame table, the scratch zero page, the reader's slot)
   need one owner, or the readers have to take turns.

## Space first, where it counts

- **Every byte of main-RAM code or data is a byte of CE2S's cache.**
  Shared code comes first, as it helps both editions. Measure the arena
  (`make STREAM=1` prints it) with a fixed `BUILD=`, because the stamp's
  length moves it byte for byte.
- **Alignment can swallow a saving.** A table that must stay within a
  page moves when the code before it shrinks, and a pad to keep it there
  can make a saving vanish or double. `band_ula` once had such a pad; it
  now starts the `Code` section, where nothing before it changes.
  `spread_lo` and `spread_rev` keep to one page by an `ASSERT`.
- **Data only room set-up reads belongs in the rooms' records** rather
  than resident (palettes, band maps, monster types). The records are the
  overlay system. Data read everywhere stays resident.
- **After a format change, look for what it left redundant**, as group
  headers kept every frame's number after the lookup stopped using it.
  Look too for the limits it can hit: `room_len4`'s byte overflowed when
  room 120's record grew (decision 42).
- **Recompute rather than store** when it's cheap and rare, as item
  lengths are worked out from `room_len4`. Drop flags that duplicate other
  state: `ld_on` was only ever `fdc_state` not 0.
- **Look for slack in every fixed region** as well as the code: the tail
  of the fixed zero page and of LowState, the bytes the MOS's IRQ entry
  leaves at the top of page 0, page 1 under a stack measured again, and
  variables a round leaves unused. A variable moved into zero page saves
  its bytes of main RAM and a byte at every access except `abs,Y`, since
  `LDA` and `STA` have no `zp,Y` (`LDX` and `STX` do, and `STX zp,Y`
  replaces `PHA : TXA : STA abs,Y : PLA`). Swap by use: a test-only
  variable gave its zero-page byte to one used often.
- **Recursion hides from a measured stack.** A routine that recurses on
  its data only goes deep when the data does: the original's `add_score`
  went a level deeper for each carried digit. Bound it from the code, or
  make it a loop (decision 40).

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
- **Always-taken branches confuse baron's allocator.** It follows both
  ways, so at the end of a `{ }` scope it thinks control falls into the
  next routine ("No free zero-page byte", "held live across recursion").
  Put `ZA_UNREACHABLE` after the branch, which prunes the fall-through for
  no bytes.
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
- `tools/screencmp.mjs`, run on the old disc against the new, catches
  frame differences the passes don't log. It skips the rooms where it
  finds nowhere to stand Harry, rooms 1-4 among them.
- Targeted fuzz against the original (`fuzz.run_case` with a start
  state) for ropes, ladders and lifts, which random walks barely reach.
- A state dump against the base build (bands, palettes, frame tables)
  when a big edit fails: `roomcmp` doesn't see IRQ or palette state.
- IRQ changes: time each palette write relative to VSync, not
  screenshots; retune in whole microseconds.
- Pure logic such as the cache can be run side by side on a 6502 core,
  with the arenas padded to the same size, as jsbeeb's random walks
  diverge on timing alone. (That pass's `m6502.py` and `cachediff.py`
  weren't committed.)
- A `;` comment in the middle of a colon-separated line swallows the
  rest of the line, silently.
- A copy loop ending `DEX : BPL` copies one byte once its count passes
  128: the reader's slot grew past it and CE2S crashed at its first read.
- Room-change times on the B (`roomwait.mjs`) move with any change to
  the reader's timing even when the cache's logic is unchanged, because a
  background read misses a revolution when its next sector's command
  comes late. Prove the logic on the 6502 core first (equal arenas, and a
  small arena to reach the give-up path), then compare the times. The
  Master's 1770 times agree to the millisecond.
- Give scratch worktrees unique names, and never `pkill -f` a pattern
  another run might share.
