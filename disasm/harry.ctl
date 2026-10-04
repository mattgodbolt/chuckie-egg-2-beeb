; Harry (the player character) in Chuckie Egg 2, ZX Spectrum.
; SkoolKit control-file entries for the routines and tables in docs/research/harry.md.
; Use alongside a generated control file, e.g.
;   sna2skool.py -H -c build/auto.ctl -c disasm/harry.ctl build/ce2.z80
; (sna2ctl's text detection puts 't' blocks at &89E7 and &DFA4 inside the template and
; the sprites; '-I TextMinLengthData=5' on sna2ctl avoids that.)
; Record fields: IY = &A451, see docs/research/harry.md for the full layout.
;
; ---------------------------------------------------------------- helpers
@ $7FA3 label=ScrUp
c $7FA3 Move a screen address up one pixel line
D $7FA3 Used by #R$8E94 (APPLY_DELTA), once per pixel of upward movement.
R $7FA3 HL Screen address (updated)
@ $7FB6 label=ScrDown
c $7FB6 Move a screen address down one pixel line
R $7FB6 HL Screen address (updated)
;
; ---------------------------------------------------------------- the update
@ $80B6 label=HarryUpdate
c $80B6 Harry: turn the control byte into dx/dy, start a jump, dispatch on the state
D $80B6 Called once per main-loop iteration (three frames) from #R$77BF. The state is #R$A487; the handlers are in the table at #R$8A17.
N $80B6 The fall counter #R$A486 only survives while falling (state 0).
C $80C2,24 dx (IY+&0B) = right (bit 1) - left (bit 2).
C $80DD,19 dy (IY+&0C) = 2*up (bit 4) - 2*down (bit 3); positive is up.
N $80F0 Jump (bit 0, SYMBOL SHIFT) starts from any state except falling (0) and jumping (7).
N $8101 Jump through the state table.
@ $8113 label=StWalk
c $8113 State 1: walking on a platform (also entered from state 2 while moving)
D $8113 Climbing starts only when cell-aligned (xfine 0). At xfine 2 the cells ahead are checked: a slope at leg level starts state 5, no floor (mask &21) walks off the edge.
@ $8143 label=StartClimb
@ $8168 label=WalkMove
@ $8172 label=WalkMid
@ $81B0 label=StPipe
c $81B0 State 2: on a slippery pipe (type &20): standing still falls through it
@ $81BA label=StLadder
c $81BA State 3: on a ladder (state 4 joins at the step-off test)
D $81BA Steps off sideways only when cell-aligned vertically with a floor (mask &21) under the feet. Climbs 2 pixels an iteration; the animation phase (IY+&0A) is yfine/2.
@ $81F3 label=LadderNoExit
@ $8230 label=ClimbStop
@ $8249 label=StRope
c $8249 State 4: on a rope: always slides down (1, 2 or 3 pixels with up, nothing, down)
@ $8262 label=RopeTail
c $8262 Rope: fall off when the rope ends below the feet
@ $829A label=WalkOff
c $829A Walk off an edge: fall with dx doubled and 4 pixels down, no collision test this iteration
@ $82B2 label=StFall
c $82B2 State 0: falling 4 pixels an iteration
@ $82BA label=FallCount
N $82BD POKE 33469,0 (NOP the INC) is the "fall any height" cheat.
@ $82CB label=StartJump
c $82CB Start a jump (state 7), then the per-iteration jump step
D $82CB Momentum (IY+&08) is fixed at take-off. Carrying object &20-&23 starts the arc at count 3 (a lower jump).
@ $832A label=StJump
N $832A State 7 enters here every iteration: count #R$A485 indexes the arc at #R$89CF.
@ $8355 label=VCollide
N $8355 Vertical collision for falling, jumping and stepping off a lift. E = yfine, D = xfine + dx + 1.
@ $837B label=CeilCol
@ $8397 label=HitCeiling
@ $83BA label=CeilColRight
@ $83D4 label=LandTest
c $83D4 Landing test: only when the feet reach a new cell row (or are already aligned)
@ $83FA label=Descend
c $83FA Moving down or level: lift landing, slope snapping, then the landing test
@ $8489 label=SlopeSnap
@ $84C0 label=SnapSurface
@ $84F8 label=Snap39
@ $8535 label=Snap38
@ $8570 label=Land
c $8570 Land on cell (HL): align the feet to the cell top, choose state 1/2, fall-death check
N $857E Death when the fall counter is 15 or more.
@ $859D label=LandRight
c $859D Landing test on the right-hand column (mask &2D), then ladder grab, head slope, side walls
@ $85B4 label=LadderGrab
N $85B4 Grab a ladder or rope while jumping or falling: xfine 0 (or climbing frame), not carrying &20-&23, up or down held, not on the first jump step.
@ $8614 label=HeadSlope
N $8614 A slope at head height ends the rise: count 16, no horizontal movement.
@ $862D label=SideWalls
N $862D Side walls in the air: blocked moves bounce (dx and momentum reversed).
@ $8699 label=ColumnBlocked
c $8699 Test B cells downwards from HL for a wall (mask &21); bit 7 kills
R $8699 HL Type-map address
R $8699 B Number of cells
@ $86AC label=WallCheck
c $86AC Walking wall test at col+dx: head row mask &2D, leg row mask &21; bit 7 kills
@ $86EF label=StSlopeUp
c $86EF State 5: walking up a slope while the uphill key is held; otherwise slide
@ $871B label=SlopeAligned
@ $873A label=StSlide
c $873A State 6: sliding down a slope, (2, 2) pixels an iteration
@ $874B label=SlopeEnd
c $876D State 8: riding a lift (record at #R$A52C)
@ $876D label=StLift
D $876D Moves with the lift's dy (#R$A538); crushed if the head cell is solid; steps off at either end when xfine is 2 and walking outwards.
@ $87E8 label=SetSlopeState
c $87E8 Choose state 5 (uphill) or 6 (slide) from the slope tile in A and the momentum
@ $87FD label=SetStanding
c $87FD Set the state from the type of the cell stood on: &01 -> 1, &20 -> 2, &21 unchanged
@ $8810 label=SlopeBack
@ $8827 label=SlopeFwd
@ $8841 label=CellType
c $8841 Type-map byte at Harry's top-left cell + A (A = &20 per row down)
R $8841 A Offset; on return the type byte, HL its address
@ $884D label=SaveOld
c $884D Copy frame pointer, addresses and size to the "old" fields (+&0E-+&11, +&16-+&19) for the erase
@ $887E label=Move
c $887E Apply dx/dy, pick the sprite frame, handle the room edges
@ $8881 label=MoveNoSave
@ $8909 label=EdgeTop
@ $8957 label=EdgeBottom
@ $89B8 label=NoEdge
@ $89BD label=RowDown
c $89BD HL += 32 (one cell row down)
@ $89C6 label=RowUp
c $89C6 HL -= 32 (one cell row up)
@ $89CF label=JumpArc
b $89CF Jump arc: dy per iteration, positive up, entry count-1 (count 1-21 used)
B $89CF,22,11
@ $89E5 label=HarryTemplate
b $89E5 Harry's record at the start of a game (26 bytes, copied to #R$A451 and #R$A46B)
@ $89FF label=HarryFrames
w $89FF Sprite frame table, index facing (0/4/8) + xfine; each frame is (height, width, rows)
W $89FF,24,8
@ $8A17 label=HarryStates
w $8A17 State handlers for #R$A487 (0 fall, 1 walk, 2 pipe, 3 ladder, 4 rope, 5 slope up, 6 slide, 7 jump, 8 lift)
W $8A17,18,9
@ $8A29 label=HarryDies
c $8A29 Harry dies: tune, restore the checkpoint, drop the carried object, lose a life
N $8A29 POKE 35369,201 (RET) is the "immunity" cheat.
N $8A7D POKE 35453,0 (NOP the DEC) gives infinite lives.
@ $8A8A label=GameOver
@ $8BDE label=SetFrame
c $8BDE Look up frame A in the table at HL: sets height (+6), width (+7) and the data pointer (+0/+1)
@ $8E94 label=ApplyDelta
c $8E94 Add dx to xfine (carrying into the column) and move dy pixel lines up (+) or down (-)
;
; ---------------------------------------------------------------- data
@ $A451 label=HarryRec
g $A451 Harry's record (IY): see docs/research/harry.md
B $A451,26,2,2,2,1,1,1,1,1,1,1,1,2,1,1,1,1,2,2,2
@ $A46B label=HarryCheckpoint
g $A46B Checkpoint copy of Harry's record, restored on death
B $A46B,26,8
@ $A485 label=JumpCount
g $A485 Jump count (index into #R$89CF + 1)
@ $A486 label=FallCount
g $A486 Fall counter: iterations spent falling; 15 kills on landing (20 on a lift)
@ $A487 label=HarryState
g $A487 Harry's state (0-8), see #R$8A17
@ $DFA2 label=HarrySprites
b $DFA2 Harry's sprite frames (10 distinct, 294 bytes): right x4 shifts, left x4, climbing x3
