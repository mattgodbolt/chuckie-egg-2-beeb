; Chuckie Egg 2 (ZX Spectrum, A&F 1985): monsters, sprite engine, graphics
; data and frame timing. SkoolKit control-file entries for
; docs/research/monsters.md. Only addresses in that scope; merge with the
; other subsystems' .ctl files. Generated in part by
; build/research/monsters/genctl.py (the graphics blocks).
; 'i' entries only mark where this scope's blocks end (the next address
; belongs to another subsystem): drop them when merging. The shared helpers
; &7FA3, &7FB6, &8841, &884D, &89BD, &89C6, &8BDE, &8E94, Harry's frame
; table &89FF and his sprites &DFA2-&E0C7 are in harry.ctl.

; ---------------------------------------------------------------------------
; Monster definitions

@ $6B00 label=MON_ROOM
b $6B00 Monster table, column 1 of 4: room of each of the 256 entries
D $6B00 Entry e is a monster in room (&6B00+e) & &7F at row (&6C00+e), column (&6D00+e), of type (&6E00+e). Bit 7 set = disabled. #R$9A80 enables entries 1..min(130 + 25*egg, 255) and disables the rest and entry 0 at the start of each egg; the room 2 dog event (#R$8D4D) enables entry 0 and disables entry 1.
B $6B00,256,16
@ $6C00 label=MON_ROW
b $6C00 Monster table, column 2: starting character row (0-23)
B $6C00,256,16
@ $6D00 label=MON_COL
b $6D00 Monster table, column 3: starting character column (0-31)
B $6D00,256,16
@ $6E00 label=MON_TYPE
b $6E00 Monster table, column 4: type (0-51), indexes #R$6F00
B $6E00,256,16
@ $6F00 label=MON_TYPES
b $6F00 Monster types: 52 x (ink, base frame, flags, speed)
D $6F00 Byte 0: ink (0-7). Byte 1: base frame, an index into the sprite pointer table #R$91B7. Byte 2: flags: bit 7 fast (2 steps, 2-frame animation), 6 vertical, 5 needs no floor/rope, 4 respawn when blocked (instead of turning), 3 starts left/down (specials: see #R$8DD5), 2 bounces Harry, 1 kills Harry, 0 stationary. Byte 3: bits 0-4 delay (moves every delay+1 ticks), bit 7 special (forms, waits, then rises or falls: #R$8DD5); bits 5-6 are that state at run time.
B $6F00,208,4

; ---------------------------------------------------------------------------
; Sprite engine

@ $7ED9 label=IM2_HANDLER
c $7ED9 IM 2 frame interrupt: erase and redraw the sprites in the draw list
D $7ED9 Reached through the vector table #R$FE00 (I = &FE) and the JP at #R$FDFD. Interrupts are only ever enabled at the main loop's EI:NOP:HALT, so no registers are saved. For each pointer in the list at #R$A41C (ends at a high byte of 0): erase the sprite at its old position (#R$7FC9) and draw it at its new one (#R$8063). Then redraw (OR) the current object #R$A402 if it has one (attribute high byte, &A405, non-zero).
@ $7F01 label=NEXT_OBJECT
c $7F01 Choose the next object in this room to keep redrawn
D $7F01 Called twice a pass. Scans at most 128 entries of the object table (room bytes at &6600) after the one in (#R$A400) for one in this room, and loads it into the sprite record #R$A402, which the interrupt then ORs onto the screen every frame until the next call. This round robin repairs objects that sprites erased (erasing restores only the tile map). None found: &A405 = 0.
@ $7F4F label=DRAW_STRIP
c $7F4F Draw a 1-byte-wide sprite by overwriting (truck and train strips)
D $7F4F IY = record. Paints the ink (IY+9) into IY+6 attribute rows from (IY+2), then copies 8 x IY+6 bytes from (IY+0) down the screen from (IY+4), replacing what was there. Width is assumed to be 1.
b $7F84 Room drawer workspace and command table (not this scope: see docs/research.md); here only to end #R$7F4F
@ $7FC9 label=ERASE_SPRITE
c $7FC9 Erase a sprite at its old position, restoring the room from the maps
D $7FC9 IY = record. Uses the 'old' fields (+&0E attribute address, +&10 height, +&11 width, +&16 image, +&18 screen address) that #R$884D copies. Attributes: height (+1 if the old screen address is not on a character row boundary) rows of width cells are copied from the attribute map (&5D00, H + 5), stopping below row 23. Pixels, column by column: screen = (screen AND NOT image) OR tile pixel, the tile taken from the tile map (&6000): codes with bit 7 set from the ROM font &3C00, others from the tile font &73B8. Pixels of other sprites under the erased image are lost.
@ $8017 label=ERASE_LOOP
@ $8063 label=DRAW_SPRITE
c $8063 Draw a sprite at its new position: OR, ink only
D $8063 IY = record. Attributes: height (+1 if the screen address is not on a character row boundary) rows of width cells get (attr AND &F8) OR ink: paper, bright and flash stay the room's. Pixels: 8 x height rows of width bytes from the image (row-major), ORed onto the screen from (IY+4). No clipping.
i $80B6
@ $8A98 label=OBJECT_SPRITES
b $8A98 Object sprite pointers: 73 entries (#R$6FD0)
D $8A98 Indexed by byte 1 of an object type record (&6A00 + 3 x type). Entries &25-&48 are the four toys' parts, 9 per toy (motorbike, car, boat, jet); #R$9B08 picks one set per egg.
W $8A98,146,2

; ---------------------------------------------------------------------------
; Monsters at run time

@ $8B2A label=SETUP_MONSTERS
c $8B2A Room entry: set up this room's monster records
D $8B2A Empties the draw list, then for every enabled entry of the monster table (#R$6B00) in this room fills a 26-byte record at #R$A490 + 26 x n (#R$8B5D) and counts them in #R$A48F. Rooms 1 and 111 then draw the truck (#R$9011).
@ $8B5D label=SETUP_MONSTER
c $8B5D Fill monster record IY from table entry L (C = records so far)
D $8B5D +&14/&15 = start row/column, +2..+5 from them (#R$7E34). From the type (#R$6F00): +9 ink, +&0D base frame, +&12 flags, +&13 speed. +8 = C + 1 (staggers the first moves), +&0A = 0. Step: 1 (2 if fast), negated if flag bit 3; vertical (flag 6): dy = 2 x step, dx = 0; else dx = step, dy = 0. Then the frame (#R$8E70) and IY += 26. Nothing is drawn until the first move.
@ $8BFD label=NEXT_RECORD
c $8BFD IY += 26
@ $8C0A label=MONSTERS_TICK
c $8C0A Tick every monster; build the draw list of those that moved
D $8C0A Called twice a pass (3 frames). IX walks the list at #R$A41C; #R$8C2C appends each record that moved; the list ends with &0000.
@ $8C2C label=MONSTER_TICK
c $8C2C Tick one monster (IY): count down, then move, turn or respawn
D $8C2C Calls the RNG (#R$918A) first, every tick, whether or not the monster moves. +8 is decremented; while it is >= 0 nothing happens (and the monster is not redrawn). Then +8 = speed AND &1F and: special (speed bit 7) #R$8DD5; stationary (flag 0) #R$8E51; vertical (flag 6) #R$8CC6; otherwise horizontal: only on a character boundary (+&0A = 0) look at the column ahead over the sprite's height: any cell type bit other than bit 1 (AND &FD) blocks, as does the screen edge; then, unless flag 5, the cell below-ahead must have bit 0 or 5 (AND &21). Blocked: respawn (#R$8D4D) if flag 4, else dx = -dx. Then save the old fields, move, choose the frame and append to the list (#R$8E59).
@ $8CC6 label=MON_VERTICAL
@ $8CD3 label=MON_VCHECK
@ $8D3C label=MON_VBLOCKED
@ $8D4D label=MON_RESPAWN
@ $8DD5 label=MON_SPECIAL
@ $8E51 label=MON_STATIC
@ $8E59 label=MON_MOVE
@ $8E5C label=MON_MOVE_NOSAVE
@ $8E70 label=MON_FRAME
c $8E70 Choose a monster's frame: base + sub-position (+4 facing left, halved if fast)

; ---------------------------------------------------------------------------
; Machines: the truck, the train, the lifts

@ $8EE8 label=MACHINES
c $8EE8 Once a pass: run the train (rooms 71-80), refresh the truck (rooms 1, 111)
D $8EE8 #R$A48C bit 0 (power on) advances the train: #R$A48E counts 0-63 across a room (4 pixels a step), then #R$A48D moves on, 80 wrapping to 71. In the train's room the train is 5 strips of 3 x 1 characters at row 5 (sprites &47-&4B, or &4C-&50 on odd counts), the column behind it restored from the maps; its front shows at column 0 of the next room once the count reaches &37. The train makes a noise (#R$91B5) while power is on.
@ $8FA5 label=RESTORE_CELLS
c $8FA5 Redraw B cells down from row C, column D, from the attribute and tile maps
@ $8FC1 label=DRAW_STRIPS
c $8FC1 Draw B strips (sprites C, C+1, ...) side by side at row E, column D, ink A (IY = record)
@ $8FED label=TRUCK_REFRESH
c $8FED Rooms 1 and 111: redraw one of the truck's 7 strips a pass (#R$91B6 cycles 0-6)
@ $9011 label=TRUCK_DRAW
c $9011 Rooms 1 and 111: draw the truck, strips &7C-&82, at column 0, row 16 (room 1) or 17 (room 111)
@ $9028 label=TRUCK_ARRIVES
c $9028 New game: the truck drives in from the left, 4 pixels every 10 frames
@ $904E label=WAIT10
c $904E Wait 10 frames (EI:HALT)
@ $9059 label=TRUCK_LEAVES
c $9059 Egg delivered: the truck drives off to the left
@ $9088 label=SETUP_LIFT
c $9088 Room entry: set up the lift record #R$A52C from #R$90E0, if this room has one
@ $90E0 label=LIFTS
b $90E0 Lifts: 4 x (room, row, column, type)
D $90E0 Type 1 (rooms 26, 55): a short bar (sprite &96) rising from the bottom and starting again. Type 2 (rooms 34, 104): a long platform (sprite &97); one row lower until the power is on.
B $90E0,16,4
@ $90F0 label=RUN_LIFT
c $90F0 Once a pass: move and redraw the lift (drawn here, not by the interrupt)

; ---------------------------------------------------------------------------
; Random numbers, sprite table

@ $918A label=RANDOM
c $918A Random number: 32-bit shift register at #R$91B1
D $918A V = the four bytes at &91B1 big-endian; V = V << 1 | (bit 30 XOR bit 27); returns A = V >> 24 (the new &91B1).
@ $91B1 label=RNG_STATE
b $91B1 Random number state (the tape has "9090")
@ $91B5 label=NOISE_FLAG
b $91B5 Non-zero: #R$92E7 clicks the speaker at random (the running train)
@ $91B6 label=TRUCK_STRIP
b $91B6 Next truck strip to refresh (0-6)
@ $91B7 label=SPRITES
b $91B7 Sprite pointers: 152 entries (monsters, truck, train, lifts)
D $91B7 Each sprite: height in characters, width in bytes, then 8 x height rows of width bytes. Sprites at #R$E0C8 to #R$FDF7.
W $91B7,304,2

; ---------------------------------------------------------------------------
; Collisions

i $92E7
@ $936B label=HARRY_CHECKS
c $936B Twice a pass: collisions (#R$937D), then object handling
@ $937D label=COLLIDE
c $937D Pixel collision: is anything on the screen inside Harry's 8-pixel window that isn't Harry or the room?
D $937D For every byte of Harry's image: (screen AND NOT (image OR tile pixel OR mask)) non-zero means a hit (#R$940A). The mask ignores the pixels outside Harry's 8-pixel-wide window when his frame is 2 bytes wide: the left 2 x sub (+&0A) pixels of the first column, the rest of the second.
@ $93B5 label=COLLIDE_LOOP
@ $940A label=COLLIDE_HIT
  $940A A hit: find what Harry's character box overlaps (#R$968C, #R$9674). The current object first (#R$9515), then each monster in record order (#R$94E5): the first one decides.
  $9440 No monster: rooms 71-80 with Harry's top in screen rows 0-7 (the train) kill.
  $9453 Room 111, Harry left of column 7 carrying the egg (&28): egg delivered.
@ $94E5 label=MONSTER_CONTACT
  $94E5 Flag bit 1: Harry dies (#R$8A29). Bit 2: Harry is knocked back (state 7, random direction). Neither: nothing.
i $9515
@ $9674 label=BOX_OVERLAP
c $9674 Carry clear if Harry's box (D', E', H', L') overlaps this one (D, E, H, L)
@ $968C label=CHAR_BOX
c $968C Character box of record IY: D = left column, E = right, H = top row, L = bottom
D $968C From the attribute address and the frame's width and height; a sprite that is not on a character row boundary still counts only height rows.

; ---------------------------------------------------------------------------
; Workspace

i $96B1
@ $A402 label=OBJECT_REC
b $A402 Sprite record of the object being kept redrawn (#R$7F01); 26 bytes
@ $A41C label=DRAW_LIST
b $A41C Draw list for the interrupt: record pointers, ended by a high byte of 0
D $A41C [Harry] for the first frame of a pass (set at &77C2), then the monsters that moved (#R$8C0A) for the second and third.
i $A42C
@ $A48C label=FACTORY
b $A48C Factory flags (bit 0: power on: the train runs, the lifts move)
@ $A48D label=TRAIN_ROOM
b $A48D The train's room (71-80)
@ $A48E label=TRAIN_POS
b $A48E The train's position in its room (0-63, 4 pixels a step)
@ $A48F label=MON_COUNT
b $A48F Number of monsters in this room
@ $A490 label=MON_RECS
b $A490 Monster records: 5 x 26 bytes (the table never puts more than 4 in a room)
@ $A512 label=STRIP_REC
b $A512 Sprite record used to draw the truck and the train strips
@ $A52C label=LIFT_REC
b $A52C Sprite record of the lift (+8, &A534: type, 0 = none)
@ $A546 label=FALLING_REC
b $A546 Sprite record of a dropped object falling (+8: object, &FF = none)
i $A560

; ---------------------------------------------------------------------------
; Interrupt vector

@ $FDFD label=IM2_JUMP
c $FDFD JP #R$7ED9 (written at start-up by &7703)
@ $FE00 label=IM2_TABLE
b $FE00 IM 2 vector table: 257 bytes of &FD, written at start-up (zeros on the tape)
B $FE00,257,16
i $FF01

; ---------------------------------------------------------------------------
; Graphics

@ $6FD0 label=OBJECT_GFX
b $6FD0 Object sprites (73 pointers at #R$8A98; 1,256 bytes)
D $6FD0 Each: height in characters, width in bytes, then 8 x height rows of width bytes (row-major), drawn by OR.
B $6FD0,2,2 Object sprite &0F: 4 x 3
B $6FD2,96,3
B $7032,2,2 Object sprite &0E,&3F: 2 x 4
B $7034,64,4
B $7074,2,2 Object sprite &00,&37: 1 x 1
B $7076,8,1
B $707E,2,2 Object sprite &01,&38: 1 x 1
B $7080,8,1
B $7088,2,2 Object sprite &02,&39: 1 x 1
B $708A,8,1
B $7092,2,2 Object sprite &03,&3A: 1 x 1
B $7094,8,1
B $709C,2,2 Object sprite &04,&3B: 1 x 1
B $709E,8,1
B $70A6,2,2 Object sprite &05,&3C: 1 x 1
B $70A8,8,1
B $70B0,2,2 Object sprite &06,&3D: 1 x 1
B $70B2,8,1
B $70BA,2,2 Object sprite &07,&3E: 1 x 1
B $70BC,8,1
B $70C4,2,2 Object sprite &2D: 2 x 4
B $70C6,64,4
B $7106,2,2 Object sprite &25: 1 x 1
B $7108,8,1
B $7110,2,2 Object sprite &26: 1 x 1
B $7112,8,1
B $711A,2,2 Object sprite &27: 1 x 1
B $711C,8,1
B $7124,2,2 Object sprite &28: 1 x 1
B $7126,8,1
B $712E,2,2 Object sprite &29: 1 x 1
B $7130,8,1
B $7138,2,2 Object sprite &2A: 1 x 1
B $713A,8,1
B $7142,2,2 Object sprite &2B: 1 x 1
B $7144,8,1
B $714C,2,2 Object sprite &2C: 1 x 1
B $714E,8,1
B $7156,2,2 Object sprite &36: 2 x 4
B $7158,64,4
B $7198,2,2 Object sprite &2E: 1 x 1
B $719A,8,1
B $71A2,2,2 Object sprite &2F: 1 x 1
B $71A4,8,1
B $71AC,2,2 Object sprite &30: 1 x 1
B $71AE,8,1
B $71B6,2,2 Object sprite &31: 1 x 1
B $71B8,8,1
B $71C0,2,2 Object sprite &32: 1 x 1
B $71C2,8,1
B $71CA,2,2 Object sprite &33: 1 x 1
B $71CC,8,1
B $71D4,2,2 Object sprite &34: 1 x 1
B $71D6,8,1
B $71DE,2,2 Object sprite &35: 1 x 1
B $71E0,8,1
B $71E8,2,2 Object sprite &48: 2 x 4
B $71EA,64,4
B $722A,2,2 Object sprite &40: 1 x 1
B $722C,8,1
B $7234,2,2 Object sprite &41: 1 x 1
B $7236,8,1
B $723E,2,2 Object sprite &42: 1 x 1
B $7240,8,1
B $7248,2,2 Object sprite &43: 1 x 1
B $724A,8,1
B $7252,2,2 Object sprite &44: 1 x 1
B $7254,8,1
B $725C,2,2 Object sprite &45: 1 x 1
B $725E,8,1
B $7266,2,2 Object sprite &46: 1 x 1
B $7268,8,1
B $7270,2,2 Object sprite &47: 1 x 1
B $7272,8,1
B $727A,2,2 Object sprite &15: 2 x 1
B $727C,16,1
B $728C,2,2 Object sprite &16: 1 x 1
B $728E,8,1
B $7296,2,2 Object sprite &17: 1 x 2
B $7298,16,2
B $72A8,2,2 Object sprite &18: 2 x 1
B $72AA,16,1
B $72BA,2,2 Object sprite &19: 1 x 1
B $72BC,8,1
B $72C4,2,2 Object sprite &1A: 2 x 1
B $72C6,16,1
B $72D6,2,2 Object sprite &1B: 1 x 2
B $72D8,16,2
B $72E8,2,2 Object sprite &1C: 1 x 2
B $72EA,16,2
B $72FA,2,2 Object sprite &1D: 1 x 2
B $72FC,16,2
B $730C,2,2 Object sprite &1E: 2 x 1
B $730E,16,1
B $731E,2,2 Object sprite &1F: 2 x 1
B $7320,16,1
B $7330,2,2 Object sprite &20: 1 x 2
B $7332,16,2
B $7342,2,2 Object sprite &21: 1 x 2
B $7344,16,2
B $7354,2,2 Object sprite &14: 3 x 4
B $7356,96,4
B $73B6,2,2 Object sprite &13: 1 x 4
B $73B8,32,4
B $73D8,2,2 Object sprite &0C: 1 x 5
B $73DA,40,5
B $7402,2,2 Object sprite &0D: 5 x 1
B $7404,40,1
B $742C,2,2 Object sprite &0A: 2 x 1
B $742E,16,1
B $743E,2,2 Object sprite &08: 2 x 1
B $7440,16,1
B $7450,2,2 Object sprite &0B: 1 x 2
B $7452,16,2
B $7462,2,2 Object sprite &09: 2 x 1
B $7464,16,1
B $7474,2,2 Object sprite &11: 1 x 1
B $7476,8,1
B $747E,2,2 Object sprite &12: 1 x 1
B $7480,8,1
B $7488,2,2 Object sprite &10: 1 x 1
B $748A,8,1
B $7492,2,2 Object sprite &22: 1 x 2
B $7494,16,2
B $74A4,2,2 Object sprite &23: 1 x 1
B $74A6,8,1
B $74AE,2,2 Object sprite &24: 1 x 1
B $74B0,8,1
@ $74B8 label=TILES
b $74B8 Tile font: tiles &20-&5B, 8 bytes each (CHARS = &73B8 while drawing rooms)
D $74B8 Tiles &31, &3B, &3C, &3D and &56 appear in no room; &56 is the lives icon (#R$A2B9).
B $74B8,480,8
i $7698

@ $E0C8 label=SPRITE_GFX
b $E0C8 Sprites: the monsters, truck, train and lifts (#R$91B7); Harry's are just before, at #R$DFA2
D $E0C8 Each: height in characters, width in bytes, then 8 x height rows of width bytes (row-major). A monster's frames are poses already shifted right by 0, 2, 4, 6 pixels (0 and 4 for fast monsters), widening by a byte when they need to.
B $E0C8,2,2 Sprite &08 (dog running): 4 x 5
B $E0CA,160,5
B $E16A,2,2 Sprite &09 (dog running): 4 x 5
B $E16C,160,5
B $E20C,2,2 Sprite &0A (dog running): 4 x 6
B $E20E,192,6
B $E2CE,2,2 Sprite &0B (dog running): 4 x 6
B $E2D0,192,6
B $E390,2,2 Sprite &0C (dog sitting): 4 x 4
B $E392,128,4
B $E412,2,2 Sprite &00 (bird): 2 x 3
B $E414,48,3
B $E444,2,2 Sprite &01 (bird): 2 x 3
B $E446,48,3
B $E476,2,2 Sprite &02 (bird): 2 x 3
B $E478,48,3
B $E4A8,2,2 Sprite &03 (bird): 2 x 4
B $E4AA,64,4
B $E4EA,2,2 Sprite &04 (bird): 2 x 3
B $E4EC,48,3
B $E51C,2,2 Sprite &05 (bird): 2 x 3
B $E51E,48,3
B $E54E,2,2 Sprite &06 (bird): 2 x 3
B $E550,48,3
B $E580,2,2 Sprite &07 (bird): 2 x 4
B $E582,64,4
B $E5C2,2,2 Sprite &0D (hedgehog): 1 x 4
B $E5C4,32,4
B $E5E4,2,2 Sprite &0E (hedgehog): 1 x 4
B $E5E6,32,4
B $E606,2,2 Sprite &0F (hedgehog): 1 x 5
B $E608,40,5
B $E630,2,2 Sprite &10 (hedgehog): 1 x 5
B $E632,40,5
B $E65A,2,2 Sprite &11 (hedgehog): 1 x 4
B $E65C,32,4
B $E67C,2,2 Sprite &12 (hedgehog): 1 x 4
B $E67E,32,4
B $E69E,2,2 Sprite &13 (hedgehog): 1 x 5
B $E6A0,40,5
B $E6C8,2,2 Sprite &14 (hedgehog): 1 x 5
B $E6CA,40,5
B $E6F2,2,2 Sprite &15 (toy soldier): 4 x 2
B $E6F4,64,2
B $E734,2,2 Sprite &16 (toy soldier): 4 x 2
B $E736,64,2
B $E776,2,2 Sprite &17 (toy soldier): 4 x 2
B $E778,64,2
B $E7B8,2,2 Sprite &18 (toy soldier): 4 x 2
B $E7BA,64,2
B $E7FA,2,2 Sprite &19,&1B (vacuum cleaner): 3 x 4
B $E7FC,96,4
B $E85C,2,2 Sprite &1A,&1C (vacuum cleaner): 3 x 4
B $E85E,96,4
B $E8BE,2,2 Sprite &1D (trainer): 2 x 3
B $E8C0,48,3
B $E8F0,2,2 Sprite &1E (trainer): 2 x 4
B $E8F2,64,4
B $E932,2,2 Sprite &1F (trainer): 2 x 3
B $E934,48,3
B $E964,2,2 Sprite &20 (trainer): 2 x 4
B $E966,64,4
B $E9A6,2,2 Sprite &21 (skate): 2 x 3
B $E9A8,48,3
B $E9D8,2,2 Sprite &22 (skate): 2 x 4
B $E9DA,64,4
B $EA1A,2,2 Sprite &23 (skate): 2 x 3
B $EA1C,48,3
B $EA4C,2,2 Sprite &24 (skate): 2 x 4
B $EA4E,64,4
B $EA8E,16,8 Unreferenced
B $EA9E,2,2 Sprite &25 (snail): 2 x 4
B $EAA0,64,4
B $EAE0,2,2 Sprite &26 (snail): 2 x 4
B $EAE2,64,4
B $EB22,2,2 Sprite &28 (snail): 2 x 4
B $EB24,64,4
B $EB64,2,2 Sprite &27 (snail): 2 x 4
B $EB66,64,4
B $EBA6,2,2 Sprite &29 (crocodile): 2 x 4
B $EBA8,64,4
B $EBE8,2,2 Sprite &2A (crocodile): 2 x 4
B $EBEA,64,4
B $EC2A,2,2 Sprite &2B (crocodile): 2 x 5
B $EC2C,80,5
B $EC7C,2,2 Sprite &2C (crocodile): 2 x 5
B $EC7E,80,5
B $ECCE,2,2 Sprite &2D (crocodile): 2 x 4
B $ECD0,64,4
B $ED10,2,2 Sprite &2E (crocodile): 2 x 4
B $ED12,64,4
B $ED52,2,2 Sprite &2F (crocodile): 2 x 5
B $ED54,80,5
B $EDA4,2,2 Sprite &30 (crocodile): 2 x 5
B $EDA6,80,5
B $EDF6,2,2 Sprite &31 (icicle): 2 x 1
B $EDF8,16,1
B $EE08,2,2 Sprite &32 (icicle): 2 x 1
B $EE0A,16,1
B $EE1A,2,2 Sprite &33 (icicle): 3 x 1
B $EE1C,24,1
B $EE34,2,2 Sprite &34 (icicle): 3 x 1
B $EE36,24,1
B $EE4E,2,2 Sprite &35,&37 (spider): 2 x 3
B $EE50,48,3
B $EE80,2,2 Sprite &36 (spider): 2 x 3
B $EE82,48,3
B $EEB2,2,2 Sprite &38 (spider): 2 x 3
B $EEB4,48,3
B $EEE4,2,2 Sprite &39 (dinosaur on scooter): 7 x 8
B $EEE6,448,8
B $F0A6,2,2 Sprite &3A (dinosaur on scooter): 7 x 9
B $F0A8,504,9
B $F2A0,2,2 Sprite &3B (rat): 1 x 4
B $F2A2,32,4
B $F2C2,2,2 Sprite &3C (rat): 1 x 5
B $F2C4,40,5
B $F2EC,2,2 Sprite &3D (rat): 1 x 4
B $F2EE,32,4
B $F30E,2,2 Sprite &3E (rat): 1 x 5
B $F310,40,5
B $F338,2,2 Sprite &3F (bubble): 1 x 1
B $F33A,8,1
B $F342,2,2 Sprite &40 (bubble): 1 x 1
B $F344,8,1
B $F34C,2,2 Sprite &41 (bubble): 1 x 1
B $F34E,8,1
B $F356,2,2 Sprite &42 (bubble): 1 x 1
B $F358,8,1
B $F360,2,2 Sprite &43 (drip): 1 x 1
B $F362,8,1
B $F36A,2,2 Sprite &44 (drip): 1 x 1
B $F36C,8,1
B $F374,2,2 Sprite &45 (drip): 1 x 1
B $F376,8,1
B $F37E,2,2 Sprite &46 (drip): 2 x 1
B $F380,16,1
B $F390,2,2 Sprite &47 (train strip): 3 x 1
B $F392,24,1
B $F3AA,2,2 Sprite &48 (train strip): 3 x 1
B $F3AC,24,1
B $F3C4,2,2 Sprite &49 (train strip): 3 x 1
B $F3C6,24,1
B $F3DE,2,2 Sprite &4A (train strip): 3 x 1
B $F3E0,24,1
B $F3F8,2,2 Sprite &4B (train strip): 3 x 1
B $F3FA,24,1
B $F412,2,2 Sprite &4C (train strip): 3 x 1
B $F414,24,1
B $F42C,2,2 Sprite &4D (train strip): 3 x 1
B $F42E,24,1
B $F446,2,2 Sprite &4E (train strip): 3 x 1
B $F448,24,1
B $F460,2,2 Sprite &4F (train strip): 3 x 1
B $F462,24,1
B $F47A,2,2 Sprite &50 (train strip): 3 x 1
B $F47C,24,1
B $F494,2,2 Sprite &51 (cloud): 2 x 3
B $F496,48,3
B $F4C6,2,2 Sprite &52 (cloud): 2 x 3
B $F4C8,48,3
B $F4F8,2,2 Sprite &53 (cloud): 2 x 4
B $F4FA,64,4
B $F53A,2,2 Sprite &54,&55,&56,&57 (steam): 2 x 4
B $F53C,64,4
B $F57C,2,2 Sprite &58,&5A (monkey): 2 x 3
B $F57E,48,3
B $F5AE,2,2 Sprite &59 (monkey): 2 x 3
B $F5B0,48,3
B $F5E0,2,2 Sprite &5B (monkey): 2 x 4
B $F5E2,64,4
B $F622,2,2 Sprite &5C,&5E (monkey): 2 x 3
B $F624,48,3
B $F654,2,2 Sprite &5D (monkey): 2 x 3
B $F656,48,3
B $F686,2,2 Sprite &5F (monkey): 2 x 4
B $F688,64,4
B $F6C8,2,2 Sprite &60,&61,&62,&63 (elephant): 2 x 2
B $F6CA,32,2
B $F6EA,2,2 Sprite &64,&65,&66,&67 (elephant): 2 x 2
B $F6EC,32,2
B $F70C,2,2 Sprite &68 (car): 2 x 3
B $F70E,48,3
B $F73E,2,2 Sprite &69 (car): 2 x 4
B $F740,64,4
B $F780,2,2 Sprite &6A (car): 2 x 4
B $F782,64,4
B $F7C2,2,2 Sprite &6B (car): 2 x 4
B $F7C4,64,4
B $F804,2,2 Sprite &6C (car): 2 x 3
B $F806,48,3
B $F836,2,2 Sprite &6D (car): 2 x 4
B $F838,64,4
B $F878,2,2 Sprite &6E (car): 2 x 4
B $F87A,64,4
B $F8BA,2,2 Sprite &6F (car): 2 x 4
B $F8BC,64,4
B $F8FC,2,2 Sprite &70,&74 (spring): 3 x 1
B $F8FE,24,1
B $F916,2,2 Sprite &71,&75 (spring): 3 x 2
B $F918,48,2
B $F948,2,2 Sprite &72,&76 (spring): 2 x 2
B $F94A,32,2
B $F96A,2,2 Sprite &73,&77 (spring): 3 x 2
B $F96C,48,2
B $F99C,2,2 Sprite &78,&79 (bat): 1 x 2
B $F99E,16,2
B $F9AE,2,2 Sprite &7A,&7B (bat): 1 x 2
B $F9B0,16,2
B $F9C0,2,2 Sprite &7C,&7D,&7E,&83,&84 (truck strip): 7 x 1
B $F9C2,56,1
B $F9FA,2,2 Sprite &7F (truck strip): 7 x 1
B $F9FC,56,1
B $FA34,2,2 Sprite &80 (truck strip): 7 x 1
B $FA36,56,1
B $FA6E,2,2 Sprite &81 (truck strip): 7 x 1
B $FA70,56,1
B $FAA8,2,2 Sprite &82 (truck strip): 7 x 1
B $FAAA,56,1
B $FAE2,2,2 Sprite &85 (truck strip): 7 x 1
B $FAE4,56,1
B $FB1C,2,2 Sprite &86 (truck strip): 7 x 1
B $FB1E,56,1
B $FB56,2,2 Sprite &87 (truck strip): 7 x 1
B $FB58,56,1
B $FB90,2,2 Sprite &88 (truck strip): 7 x 1
B $FB92,56,1
B $FBCA,2,2 Sprite &89 (truck strip): 7 x 1
B $FBCC,56,1
B $FC04,2,2 Sprite &8A (tortoise): 1 x 2
B $FC06,16,2
B $FC16,2,2 Sprite &8B (tortoise): 1 x 3
B $FC18,24,3
B $FC30,2,2 Sprite &8C (tortoise): 1 x 2
B $FC32,16,2
B $FC42,2,2 Sprite &8D (tortoise): 1 x 3
B $FC44,24,3
B $FC5C,2,2 Sprite &8E (ostrich): 2 x 2
B $FC5E,32,2
B $FC7E,2,2 Sprite &8F (ostrich): 2 x 2
B $FC80,32,2
B $FCA0,2,2 Sprite &90 (ostrich): 2 x 3
B $FCA2,48,3
B $FCD2,2,2 Sprite &91 (ostrich): 2 x 3
B $FCD4,48,3
B $FD04,2,2 Sprite &92 (ostrich): 2 x 2
B $FD06,32,2
B $FD26,2,2 Sprite &93 (ostrich): 2 x 2
B $FD28,32,2
B $FD48,2,2 Sprite &94 (ostrich): 2 x 3
B $FD4A,48,3
B $FD7A,2,2 Sprite &95 (ostrich): 2 x 3
B $FD7C,48,3
B $FDAC,2,2 Sprite &97 (lift platform): 1 x 7
B $FDAE,56,7
B $FDE6,2,2 Sprite &96 (lift bar): 1 x 2
B $FDE8,16,2
S $FDF8,5 Zeros
