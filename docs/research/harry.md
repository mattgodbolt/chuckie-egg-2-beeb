# Harry, the player character

How Hen House Harry moves, collides, changes rooms and dies in the Spectrum
original. Addresses are the running game's. "Verified" means it was checked
by running the original on SkoolKit's simulator (scripts in
`build/research/harry/`, named in brackets); everything else is read from the
disassembly and says so. The routines are labelled in `disasm/harry.ctl`.

Notation: *row*, *col* are character cells (0-23, 0-31; rows 0-1 are the
status bar, the room is rows 2-23); *yf* is the pixel line inside the cell
(0-7); *xf* is "x fine", the position inside the cell in 2-pixel steps (0-3).
`T(off)` is the cell-type byte at Harry's top-left cell plus `off`, where
`off` = 32 per row down + 1 per column right (routine `&8841`). `dy` is
positive **up**.

## 1. Timing

- The main loop (`&77B9`-`&78BE`) has **three `HALT`s per iteration** and
  calls Harry's update `&80B6` once, so Harry moves at 50/3 = 16.7 updates a
  second. Every speed below is per iteration; divide by 3 for per frame.
- Measured: 3.000 frames per iteration over 150-300 iterations in rooms 1,
  7, 50 and 99; 3.106 in room 2 and 3.065 in rooms 27/47, where some
  iterations overrun into a fourth frame (busy rooms) [`timing.py`,
  `timing2.py`].
- Order inside an iteration: keyboard `&78C1` (sampled **once** per
  iteration) → Kempston merge `&9CE7` → Harry `&80B6` → room change
  (`&77CF`) → footstep sound `&92F4` → HALT 1 (the IM 2 handler `&7ED9`
  erases and redraws Harry: list at `&A41C` holds only Harry here) → lift
  `&90F0`, monsters → HALT 2 → sprite collision `&936B` (monsters, objects)
  → HALT 3 → `&936B` again → loop.
- Kempston (`&9CC2`, after each HALT) ANDs port 31 into `&A3FB`, so a
  direction counts only if held at all three samples; it is ORed into the
  control byte at the start of the *next* iteration (one iteration of
  latency, verified [`t_kemp.py`]). Kempston R/L/D/U/F map to control bits
  1/2/3/4/0.

## 2. The record (26 bytes at `&A451`, IY)

Template at `&89E5` (copied to `&A451` and to the checkpoint `&A46B` at game
start, `&776F`): `a4 df 46 5a 46 50 02 01 01 06 00 00 00 00 00 00 01 01 01 07
00 00 00 00 00 00`. The same 26-byte layout is used by the monsters and the
lift (`&A52C`); the sprite code (`&7FC9` erase, `&8063` draw) reads it.

| Off | Addr | Template | Meaning |
|---|---|---|---|
| +00/01 | `&A451` | `&DFA4` | pointer to the current frame's pixel rows (frame header + 2) |
| +02/03 | `&A453` | `&5A46` | attribute address of the top-left cell, `&5800 + 32·row + col` (row 18, col 6). The maps are at fixed offsets from it: tile map +`&0800`, cell types +`&0B00`, background attributes +`&0500` |
| +04/05 | `&A455` | `&5046` | screen address of the top pixel line: low byte = +02, high = `&40 | (row & &18) | yf` |
| +06 | `&A457` | 2 | frame height in cells (always 2: Harry is 16 lines) |
| +07 | `&A458` | 1 | frame width in bytes: 1 when xf = 0 or climbing, else 2 |
| +08 | `&A459` | 1 | momentum: horizontal direction of a jump or slope (-1/0/+1) |
| +09 | `&A45A` | 6 | ink colour (yellow); `&8063` ORs it into the attributes he covers |
| +0A | `&A45B` | 0 | xf (0-3); on ladders/ropes the climbing animation phase instead |
| +0B | `&A45C` | 0 | dx this iteration (-1/0/+1; ±2 for one step when walking off an edge) |
| +0C | `&A45D` | 0 | dy this iteration, pixels, + = up |
| +0D | `&A45E` | 0 | facing / frame base: 0 right, 4 left, 8 climbing |
| +0E/0F | `&A45F` | | old attribute address (for the erase) |
| +10/11 | `&A461` | | old height, old width |
| +12 | `&A463` | 1 | checkpoint room (written just before the checkpoint copy) |
| +13 | `&A464` | 7 | checkpoint state |
| +14/15 | `&A465` | 0 | unused by Harry (the lift keeps its start position here) |
| +16/17 | `&A467` | | old frame pointer |
| +18/19 | `&A469` | | old screen address |

`&884D` copies +00..07 to the "old" fields before every move. Other
variables: `&A487` state, `&A485` jump count, `&A486` fall counter, `&A48A`
control byte, `&A48B` room delta, `&A3FA` lives, `&A3FE` room, `&A560`
carried object (`&FF` = none), `&A46B` checkpoint record.

**Position.** x = 8·col + 2·xf (not on ladders/ropes, where the frames are
unshifted and x = 8·col); y = 8·row + yf. Only the column, row, yf and xf
matter to the logic; the addresses are the Spectrum's way of holding them.
(Verified: the decoded positions match the screen in every experiment.)

## 3. Sprite frames

Table `&89FF`: 12 pointers, index = facing (+0D) + xf (+0A), set in `&887E`
via `&8BDE`. Each frame is `height(2), width(1|2)`, then 16 rows of `width`
bytes, row-major, drawn by ORing (`&8063`). 294 bytes at `&DFA2-&E0C7`.

| Index | Addr | w | Picture |
|---|---|---|---|
| 0-3 | `&DFA2`, `&DFB4`, `&DFD6`, `&DFF8` | 1,2,2,2 | facing right, shifted 0/2/4/6 px; the four are also the walk cycle (different legs) |
| 4-7 | `&E01A`, `&E02C`, `&E04E`, `&E070` | 1,2,2,2 | facing left, same |
| 8, 10 | `&E092` | 1 | climbing, both feet down |
| 9 | `&E0A4` | 1 | climbing, one arm up |
| 11 | `&E0B6` | 1 | climbing, other arm up |

Animation is therefore position-driven: walking cycles through 0-3 (4-7) as
xf advances; climbing a ladder shows frame 8 + yf/2 (computed before the
move, so it lags one step); on a rope the phase is yf & 3 and only changes
while up is held. Facing is set from dx when walking, starting a jump, and
riding a lift; it is not changed while falling, jumping or on slopes.

## 4. States

`&A487`, dispatched through `&8A17` after the jump test.

| State | Handler | Meaning |
|---|---|---|
| 0 | `&82B2` | falling |
| 1 | `&8113` | walking/standing on a platform (type bit 0) |
| 2 | `&81B0` | on a slippery pipe (type `&20`) |
| 3 | `&81BA` | on a ladder |
| 4 | `&8249` | on a rope |
| 5 | `&86EF` | walking up a slope |
| 6 | `&873A` | sliding down a slope |
| 7 | `&832A` | jumping |
| 8 | `&876D` | riding a lift |

## 5. Cell types (`&6300`, read through `&8841`)

What each bit means to Harry, from the masks the code uses, with the counts
over all 120 rooms (from the room oracle `build/rooms/`):

| Bit | Value | Meaning |
|---|---|---|
| 0 | `&01` | solid: floor to stand on, wall, ceiling |
| 1 | `&02` | ladder (also chains drawn as ladders, e.g. room 27 col 16) |
| 2 | `&04` | `/` slope (tiles `&55` surface, `&39` fill below) |
| 3 | `&08` | `\` slope (tiles `&54` surface, `&38` fill below) |
| 4 | `&10` | rope: slide down only |
| 5 | `&20` | slippery pipe: holds Harry only while he walks |
| 6 | `&40` | never tested by Harry's code |
| 7 | `&80` | deadly (tested wherever a cell is examined, see below) |

| Value | Cells | Rooms | Tiles | Effect |
|---|---|---|---|---|
| `&00` | 72,709 | all | | empty |
| `&01` | 13,471 | 120 | many | solid |
| `&02` | 3,434 | 105 | `&33`, `&34`, `&2F` | ladder; you fall through it unless climbing |
| `&03` | 170 | 73 | `&34` | ladder cell that is also a floor (the floor row of a ladder) |
| `&04` | 542 | 33 | `&55`, `&39` | `/` slope |
| `&08` | 214 | 19 | `&54`, `&38` | `\` slope |
| `&10` | 140 | 9 (8, 18, 33, 60, 70, 80, ...) | `&35` | rope |
| `&20` | 888 | 20 (27-29, 37-39, ...) | `&36`, `&20-&23` | slippery pipe |
| `&21` | 12 | 7 | `&2A`, `&2B` | pipe end on a wall: solid, but landing on it does not change the state (quirk of `&87FD`) |
| `&22` | 13 | 8 | `&34` | ladder through a pipe |
| `&80` | 535 | 32 | `&37`, `&30`, `&5A`, `&3E`, `&5B` | deadly |
| others | 1-3 each | | mostly `&38` | `&05 &09 &0A &0C &11 &2B &2D &30 &4C &4E &6D &81 &86 &90 &93 &A7 &A9 &AF &C8 &CA &D0 &E9 &EB &F1`: ORed overlaps (hoppers, slope ends); treat by bits |

Masks used:

| Mask | Bits | Used for |
|---|---|---|
| `&21` | solid, pipe | floor under the feet when walking (`&81A4`), landing on Harry's own column (`&83F2`), wall at leg height (`&86D3`), walls in the air (`&8699`), ladder step-off floor (`&81CE`), slope bottom (`&875E`) |
| `&2D` | solid, slopes, pipe | wall at head height (`&86C2`), ceiling (`&838C`), landing on the right-hand column (`&85AC`), support under a slope (`&8720`), above a ladder top (`&823B`) |
| `&12` | ladder, rope | can start climbing; passes through ceilings |
| `&0C` | slopes | start walking up a slope; slope at head height in the air |
| `&02` | ladder | ladder continues (climbing) |
| `&10` | rope | rope continues below |
| `&01` | solid | head crushed (lift), state choice |
| `&80` | deadly | `OR A: JP M,&8A29` at every ceiling, landing, wall and lift test; *not* in the walking floor test |

Slope direction comes from the **tile map** (`T - &300`), not the type:
`&55`/`&39` are `/`, `&54`/`&38` are `\`.

Verified: falling onto row 8 of room 7 (type `&80`) kills [`t_deadly.py`];
standing still on room 27's pipe falls through it, walking does not
[`t_pipe3.py`]; type `&02` without `&01` is fallen through (room 1's ladder
shaft) [`t_ladder.py`].

## 6. Pseudocode

Faithful to the code order; labels are those in `disasm/harry.ctl`.

```
HarryUpdate (&80B6):                      ; once per iteration
  if state != 0: fallcnt = 0
  k = &A48A                               ; bit 4 up, 3 down, 2 left, 1 right, 0 jump
  dx = right(k) - left(k)
  dy = 2*up(k) - 2*down(k)
  if state != 0 and state != 7 and jump(k): goto StartJump
  goto HarryStates[state]                 ; &8A17

StWalk (&8113):                           ; state 1
  if dx != 0: face = (1 - dx) * 2         ; 0 right, 4 left
  if xf != 0: goto WalkMid
  if dy < 0:  t = T(&40) & &12            ; cell under the feet
              if t: goto StartClimb
              dy = 0
  elif dy > 0: t = T(0) & &12             ; head cell
              if t: goto StartClimb
              dy = 0
  if dx != 0: WallCheck()
  goto Move
StartClimb (&8143):
  face = 8; state = (t == &02) ? 3 : 4; dx = 0; goto Move
WalkMid (&8172):
  dy = 0
  if xf != 2 or dx == 0: goto Move
  c = (dx + 1) >> 1                       ; 1 going right, 0 going left
  if T(&20 + c) & &0C:                    ; slope at leg height ahead
      state = 5; mom = dx; dy = 2; goto Move
  if T(&40 + c) & &21: goto Move          ; floor ahead
  goto WalkOff

StPipe (&81B0):                           ; state 2
  if dx == 0: goto WalkOff                ; standing still: fall through
  goto StWalk

WalkOff (&829A):
  cnt = 0; state = 0; fallcnt = 0
  dx = dx * 2; dy = -4; goto FallCount    ; one 4x4 step with no collision test

StFall (&82B2):                           ; state 0
  dx = 0; dy = -4
FallCount (&82BA):
  fallcnt++                               ; POKE 33469,0 removes this
  if dx != 0: goto Move
  goto VCollide

StRope (&8249):                           ; state 4
  dy = (dy >> 1, arithmetic) - 2          ; up -1, none -2, down -3
  if dy == -1: xf = yf & 3                ; animation only while up held
  ; fall into StLadder
StLadder (&81BA):                         ; state 3
  if yf == 0 and dx != 0:
      t = T(&40) & &21
      if t:                               ; floor under the feet: step off
          dy = 0; state = (t & 1) ? 1 : 2
          face = (1 - dx) * 2; xf = 0
          goto StWalk                     ; and walk this same iteration
  if state == 4: goto RopeTail
  xf = yf >> 1                            ; climbing frame
  dx = 0
  if dy == 0: goto Move
  if dy < 0:
      if not (T(&40) & &02): dy = 0       ; no ladder under the feet: stop
      goto Move
  if yf != 0: goto Move                   ; up, mid-cell: keep going
  if not (T(0) & &02): dy = 0; goto Move  ; head cell is not ladder: stop
  t = T(-&20)                             ; cell above the head
  if (t & &2D) and not (t & &02): dy = 0
  goto Move
RopeTail (&8262):
  if yf >= 5 and not (T(&60) & &10):      ; rope ends below the feet
      dy = yf - 8; state = 0; fallcnt = 1; dx = 0; xf = 0
      goto FallCount
  dx = 0; goto Move

StartJump (&82CB):
  if state == 4 and dx == 0: goto StRope  ; can't jump straight off a rope
  if state == 6: dx = mom                 ; jump in the slide direction
  if state == 3 or state == 4: xf = 0
  state = 7
  if dx != 0: face = (1 - dx) * 2
  cnt = 0; fallcnt = 0; mom = dx
  if &20 <= carried < &24: cnt = 3        ; heavy object: lower jump
StJump (&832A):                           ; state 7
  dx = mom
  cnt++
  if cnt >= 22: state = 0; fallcnt = 5; goto StFall
  dy = JumpArc[cnt - 1]                   ; &89CF
  ; fall into VCollide

VCollide (&8355):
  E = yf; D = xf + dx + 1                 ; D-1 = xf after the move, unwrapped
  if dy > 0:                              ; rising
      if E - dy >= 0: goto LadderGrab     ; head stays in the same cell row
      if ((D - 1) & 3) != 0:              ; will straddle two columns
          t = T(-&20 + 1); if t & &80: die
          if t & &2D: goto HitCeiling
      t = T(-&20); if t & &80: die
      if (t & &2D) == 0 or (t & &12): goto LadderGrab
  HitCeiling (&8397):
      if cnt == 1: dy = 0; goto Descend   ; ceiling right on the head: no jump
      dy = E                              ; rise to the top of this cell only
      if cnt < 11: cnt = 11               ; and start the way down
      goto LadderGrab
  Descend (&83FA):                        ; dy <= 0
      if lift present (&A534 != 0): LiftLandCheck   ; may goto Move
      c = (xf >> 1) & 1
      off = &20 + c + (E != 0 ? &20 : 0)  ; cell holding the feet's lowest line
      tile = Tile(off)
      if tile == &39: goto Snap39
      if tile == &38: goto Snap38
      if tile == &54 or tile == &55: goto SnapSurface
  LandTest (&83D4):
      A = E - dy                          ; yf after the move, unwrapped
      if A == 0: off = &40                ; aligned: test under the feet
      elif A < 8: goto LadderGrab         ; feet stay inside the cell: no test
      else: off = &60                     ; feet enter the next row
      if D < 4:
          t = T(off); if t & &80: die
          if t & &21: goto Land
      if D >= 3:
          t = T(off + 1); if t & &80: die
          if t & &2D: goto Land
      goto LadderGrab
  Land (&8570):
      dy = (E == 0) ? 0 : E - 8           ; finish exactly on the surface
      SetStanding(t)                      ; &87FD
      if fallcnt >= 15: die
      fallcnt = 0
      if face == 8: xf = 0; face = 0
  LadderGrab (&85B4):
      if (xf == 0 or face == 8) and not (&20 <= carried < &24)
         and (k & &18) and cnt != 1:
          t = T(0) & &12
          if t:
              if t == &02: s = 3
              elif T(&40) & &10: s = 4
              else: s = 0                 ; (a dead store of dy = -4 here)
              state = s; dx = 0; dy = E & 1; face = 8
  HeadSlope (&8614):
      if T(0) & &0C: cnt = 16; dx = 0; mom = 0; goto Move
  SideWalls (&862D):
      C = E - dy
      p = cell(row, col); if C < 0: p -= 32 elif C >= 8: p += 32
      n = (C & 7) ? 3 : 2                 ; rows the sprite will cover
      if dx > 0 or (dx == 0 and xf == 1):
          if ColumnBlocked(p + 1, n): dx = -1; mom = -mom
      elif dx < 0 or (dx == 0 and xf == 3):
          if xf == 0: p -= 1
          if ColumnBlocked(p, n): dx = 1; mom = -mom
      goto Move

ColumnBlocked(p, n) (&8699):              ; n cells downwards
  repeat n: t = [p]; if t & &80: die; if t & &21: return true; p += 32
  return false

WallCheck() (&86AC):                      ; walking, xf == 0
  t = T(dx); if t & &80: die              ; column ahead, head row (8-bit add)
  if t & &2D:
      if state == 5: dx = -mom; goto StSlopeUp (abandons the caller)
      dx = 0; return
  t = T(&20 + dx); if t & &80: die        ; leg row
  if t & &21: dx = 0
  return

StSlopeUp (&86EF):                        ; state 5
  if mom != dx:                           ; uphill key released or reversed
      mom = -mom; dx = mom; dy = -2; state = 6; goto Move
  dy = 2
  if xf != 0: goto Move
SlopeAligned (&871B):
  if (T(&40) & &2D) == 0: state = 0; goto StFall
  WallCheck()
  if state == 5: goto Move
  goto SlopeEnd
StSlide (&873A):                          ; state 6
  dx = mom; dy = -2
  if xf == 0: goto SlopeAligned
SlopeEnd (&874B):
  if yf != 0: goto Move
  t = T(&40 + ((mom + 1) >> 1))
  if t & &21: SetStanding(t); dy = 0
  goto Move

SetSlopeState(tile) (&87E8):
  if tile is &54/&38 (\):  if mom < 0: state = 5 else: mom = 1;  state = 6
  if tile is &55/&39 (/):  if mom > 0: state = 5 else: mom = -1; state = 6
SetStanding(t) (&87FD):
  t &= &21; if t == &01: state = 1 elif t == &20: state = 2   ; &21: unchanged

SnapSurface (&84C0):                      ; tile &54/&55 under the feet
  xf = 0; SaveOld(); col += c (attr low byte only)
  dx = 0; dy = 0; face &= ~8; yf = 4      ; same row
  SetSlopeState(tile); goto MoveNoSave
Snap39 (&84F8):                           ; '/' fill
  xf = 2; SaveOld(); col += c - 1; up one row, yf = 0
  dx = dy = 0; face &= ~8; SetSlopeState(tile); goto MoveNoSave
Snap38 (&8535):                           ; '\' fill
  xf = &38 (sic); SaveOld(); col += c; up one row, yf = 0
  dx = dy = 0; face &= ~8; SetStanding... no: SetSlopeState(tile); goto MoveNoSave
  ; ApplyDelta then makes xf = &38 & 3 = 0 and, since &38 >= 4, col += 1

Move (&887E): SaveOld()                   ; &884D
MoveNoSave (&8881):
  ApplyDelta()                            ; &8E94
  SetFrame(HarryFrames, face + xf)        ; &8BDE, table &89FF
  Edges()                                 ; see section 10

ApplyDelta() (&8E94):
  t = xf + dx; xf = t & 3
  if t < 0: col -= 1 elif t >= 4: col += 1   ; attr low byte only
  move the screen address up dy lines (dy > 0, &7FA3) or down -dy (&7FB6)
  recompute the attribute high byte from it
```

Sizes: `&80B6-&8A97` is 2,530 bytes for all of the above plus death:
dispatcher `&80B6` 93, walk 157, pipe 10, ladder 143, rope 25 + 56, walk-off
24, fall 25, jump start/step/rise `&82CB` 265, land test 38, descend (lift
test, slope snaps) `&83FA` 374, land 45, right column/ladder grab/head
slope/side walls `&859D` 252, column test 19, wall test + slope up 142,
slide 51, lift ride `&876D` 123, slope state 21, standing state 19,
`&8810`/`&8827` 49, cell lookup 12, save old 49, move + edges `&887E` 319,
row up/down 18, tables `&89CF-&8A28` 90 (arc 22, template 26, frames 24,
states 18), death `&8A29` 111. Also needed: ApplyDelta `&8E94` 84, SetFrame
`&8BDE` 31, screen line up/down `&7FA3`/`&7FB6` 38, the room-change code in
the main loop `&77CF-&7856` 136, and the frames 294 bytes.

## 7. Walking, falling, jumping (numbers)

All verified unless marked.

- **Walk**: 2 px per iteration (0.67 px/frame); stopping and starting are
  instant [`walk.py`]. A wall is detected only when cell-aligned (xf 0): head
  row mask `&2D`, leg row `&21`, so slopes at leg height don't block
  [`t_wall.py`].
- **Walking off an edge**: at xf 2 the code looks at the floor cell ahead
  (half of Harry already over it); with none (mask `&21`) the next step is
  4 px across and 4 px down with no collision test, then a plain fall
  [`t_ladder.py`, `t_synth2.py`].
- **Fall**: 4 px per iteration (1.33 px/frame), straight down, keys
  ignored. The fall counter `&A486` counts falling iterations (the landing
  one included); landing with `fallcnt >= 15` kills. From rest or walking
  off, a drop of 7 cells (56 px) is safe and 8 cells (64 px) kills
  [`t_fall.py`, `t_walkoff.py`]. After a full jump the counter starts at 5,
  so landing up to 48 px below the take-off is safe and 52 px kills
  [`t_jumpfall.py`]. On a lift the limit is 20 (read, not tested).
- **Jump** (SYMBOL SHIFT, control bit 0): from any state except falling and
  jumping, the same iteration the key is seen; holding the key re-jumps on
  the iteration after landing [`t_jump.py`]. The arc is the table at `&89CF`,
  one entry per iteration (dy, + = up), count 1-21:

  | count | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8-11 | 12 | 13 | 14 | 15 | 16 | 17-21 |
  |---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
  | dy | 4 | 4 | 3 | 2 | 1 | 1 | 1 | 0 | -1 | -1 | -1 | -2 | -3 | -4 |
  | height | 4 | 8 | 11 | 13 | 14 | 15 | 16 | 16 | 15 | 14 | 13 | 11 | 8 | 4, 0, -4, -8, -12 |

  Then (count 22) a fall with the counter at 5. The 22nd table byte is never
  used. On flat ground he lands on the 18th iteration (54 frames), 36 px
  along. Peak 16 px: exactly two cells, so a ledge two cells up can be
  reached, and only by being over it during the four level iterations (8-11),
  when the side-wall test covers just two rows [`t_synth2.py`: lands at
  count 8].
- Horizontal speed in a jump is 2 px per iteration, fixed at take-off as the
  momentum (+08); the keys are ignored until he lands [`t_jump.py`].
  Carrying object `&20-&23` starts the arc at count 3 (5 px high; read only).
- **Hitting things while jumping:** a ceiling ends the rise at the top of
  the current cell and jumps the count to 11 [`t_synth.py`]; a ceiling
  directly on the head on the first step means no jump at all
  [`t_ceiling.py`]; a wall reverses dx and the momentum (a bounce)
  [`t_diag.py`, x=104]; a slope at head height kills the rise and the
  momentum (count 16, dx 0; read only); ladders and ropes are grabbed if up
  or down is held and xf is 0 [`t_rope.py`]; deadly cells kill.

## 8. Ladders, ropes, slopes, pipes, lifts

- **Getting on a ladder** from walking needs xf 0 (cell-aligned) and up with
  a ladder in the head cell, or down with one under the feet; holding up or
  down while walking past catches it on the aligned step. In the air the
  same needs up/down held, xf 0, and not the first jump step [`t_ladder.py`].
  Type `&02` gives state 3; `&10` (or `&12`) state 4.
- **Climbing**: 2 px per iteration up or down, left/right ignored
  [`t_ladder.py`]. Down stops when the cell under the feet is not ladder;
  up stops when, cell-aligned, the head cell is not ladder (or the cell
  above it is solid and not ladder). A ladder through a floor has an extra
  ladder cell above the floor and the floor cell is `&03`, so Harry stops
  with his feet on the floor and can step off: stepping off needs yf 0, a
  direction, and `&21` under the feet; he walks on the same iteration
  [`t_ladexit.py`]. Room 1's ladder (all `&02`, sticking up two cells)
  cannot be walked off at the top at all, only jumped off [`t_ladder2.py`].
- **Ropes** (state 4) can't be climbed: Harry slides down 1 px per iteration
  holding up, 2 with nothing, 3 holding down [`t_rope.py`]. When the rope
  ends below him he drops (fall counter 1). Jumping off needs a direction;
  jump alone just slides.
- **Slopes**: walking into a slope at leg height (checked at xf 2) starts
  state 5, climbing (2, 2) px per iteration while the uphill key is held;
  releasing or reversing it, or a wall at head height, turns it into a
  slide (state 6) [`t_diag.py`]. Sliding is (2, 2) per iteration, keys
  ignored, until the feet are cell-aligned over a floor; jump works and uses
  the slide direction. Landing on a slope from a fall snaps Harry onto it
  (`SnapSurface` puts yf at 4) and picks 5 or 6 from the momentum, which then
  usually becomes a slide [`t_diag.py`, `t_diagedge.py`]. At the top Harry
  drops the last 4 px onto the floor [`t_diagedge2.py`].
- **Slippery pipes** (type `&20`, state 2): he can walk along them; the
  first iteration without left/right he falls through (fall counter
  restarts) [`t_pipe3.py`]. This is the instructions' "some pipes are more
  slippery than others"; ordinary platforms are `&01`.
- **Lifts** (`&90E0`: rooms 26 and 55 type 1, 34 and 104 type 2; record
  `&A52C`, width +07; moving only while `&A48C` bit 0 is set): falling or
  jumping onto one (horizontal overlap, top within a 6-px window) gives
  state 8; Harry then moves by the lift's dy (2 px per iteration), walks with
  the in-air side-wall test, and steps off either end at xf 2 walking
  outwards (falls). A solid cell at his head while riding kills (crushed).
  Leaving a room in state 8 turns into a jump (state 7, count 0, momentum
  +1). Verified: landing, riding down, stepping off the right end in room 34
  with the bit poked on [`t_lift2.py`]; the rest is read.
- **Monsters that bounce** (flag bit 2 of a monster's +12, `&94E5`): Harry
  is thrown into state 7 at count 2 with a random momentum (-1/0/+1) and
  facing (seen in room 27 [`t_pipe.py`]). Flag bit 1 kills.
- Rooms 71-80 (`&9440`): Harry dies if his top-left cell is in rows 0-7
  (the region above the yellow line in that corridor). Read only.

## 9. Respawn, death, lives

- **Checkpoint**: on entering a room, if the state is then 1 (walking) or 3
  (ladder), +12 = room, +13 = state, and the whole record is copied to
  `&A46B` (`&7838`). Otherwise the previous checkpoint stays, which may be
  in an earlier room [`t_death.py`: entering room 2 falling kept room 1's].
- **Death** (`&8A29`, reached by `JP` from every test): death tune `&A2EB`
  (about 117 frames), record ← checkpoint, room ← +12, state ← +13, count,
  fall counter, controls and the Kempston accumulator cleared, the carried
  object dropped (`&A560 < &27`: bit 7 of `&6600+obj` cleared, `&9986`,
  `&A560 = &FF`), `&6725 = &0D`, `&6825 = &0A`, `&A48C` bit 2 cleared,
  lives `&A3FA` decremented; at 0, game over (`&A0F7`, `&7DE1`, `&9E2D`,
  `&9BDC`), else the room is redrawn and set up (`&7913`) and the main loop
  restarts [`t_death.py`, `t_deadly.py`: lives 5 → 4, back at the entry
  point].
- Game start (`&7763`): room 1, record from the template, state 7, count 0:
  Harry jumps out of the truck at (48, 144) to the right and lands at
  (90, 168) [`t_jump.py`].
- POK file: 33469 (`&82BD`) fall any height ✓, 35369 (`&8A29` = RET)
  immunity ✓ (deaths then just end Harry's update), 35453 (`&8A7D`) no life
  lost ✓, 41978 = `&A3FA` lives, 41982 = `&A3FE` room. 35459 (`&8A83`) is
  the high byte of `CALL &7913` in this version, not a lives counter: that
  poke must be for another release.

## 10. Room edges (`&8890-&89BC`, after the move)

| Edge | Condition | Harry reappears | `&A48B` |
|---|---|---|---|
| right | col = 31 and dx > 0 | col 0, xf 2 (x 4), same row | +1 (room 80 → 71) |
| left | col = 0, xf = 0, dx < 0 | col 30, xf 3 (x 246) | -1 (room 71 → 80) |
| top | row ≤ 1 | row 21, yf 4 (y 172), same x | -10 |
| bottom | row ≥ 21, yf ≥ 4 and dy < 0 | row 2, yf 0 (y 16) | +10 |

Verified: right x 246 → 248 → 4 [`t_ladder2.py`]; left 2 → 0 → 246
[`t_edges.py`]; down 168 → 172 → 16 and up 16 → 14 → 172 [`t_ladder.py`].
The vertical mapping loses the sub-cell offset (both directions round).
Slope fix-ups: crossing the right edge in state 5 also moves up a row and to
col 1, yf 0 (read only); the top edge in state 5 adds 2·dx to col and dx to
xf, the bottom edge in state 6 adds 3·dx to col and dx to xf [verified,
`t_diagedge2.py`/`t_diagedge3.py`]. Those leave xf at 4 or -1 for one
iteration, so the frame index is one off (frame 4 or 3) for that one
drawing: an original glitch. Left-edge slope crossings get no fix-up.

After the new room is set up (`&7801`): state 8 becomes a jump; unless the
move was upwards, the cell under the feet (`T(&40 + xf/2)`) sets state 1/2
if it is a floor and not a ladder/rope; then the checkpoint rule above.

## 11. Things to carry into the port

- The logic needs only (col, row, yf, xf); the record's screen and
  attribute addresses can be replaced, but a few quirks come from the
  Spectrum address arithmetic and would need deliberate copying (numbered
  decisions): `Snap39`/`Snap38` move up a row by subtracting 32 from
  (screen high & `&F8`, attr low), which gives yf 7 instead of 0 when it
  crosses a screen third (rows 7/8, 15/16); column moves are 8-bit adds to
  the attribute low byte.
- `T(off)` is a 16-bit add of an 8-bit offset to the attribute address, so
  `T(dx)` with dx = -1 at col 0 reads the previous row's col 31 (no wrap
  check). Harmless in practice (the edge code moves him first).

## 12. Open questions

- Which objects are `&20-&23` (the heavy ones that shorten jumps and stop
  mid-air ladder grabs)? Objects agent; they are the hopper ingredients
  dropped in rooms `&21`, `&33`, `&5F`, `&6E` (`&9752`).
- Lift landing window and crush, rope with no rope below at grab time,
  `Snap38`, the right-edge state-5 fix-up and type `&21` landings are read
  from the code, not exercised.
- The footstep/jump/fall sound `&92F4` (pitch from state, count and fall
  counter) is left to the sound research.
- Exact frame accounting of the occasional fourth frame in busy rooms
  (which part of the loop overruns).
