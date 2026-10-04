; Objects, machines and the game logic in Chuckie Egg 2, ZX Spectrum.
; SkoolKit control-file entries for the routines and tables in docs/research/objects.md.
; Use alongside a generated control file and the other subsystem files, e.g.
;   sna2skool.py -H -c build/auto.ctl -c disasm/objects.ctl build/ce2.z80
; Only addresses no other disasm/*.ctl claims are defined here (monsters.ctl leaves
; &9515, &96B1 and &A560 to this file with 'i' entries).
;
; ---------------------------------------------------------------- thing tables
; 256 "things" in four parallel 256-byte arrays, index i in the low byte:
; 0-&28 portable objects, &29-&39 fixed machine parts, &3A-&FF bonus items.
@ $6600 label=THING_ROOM
b $6600 Thing table: room of thing i (1-120); bit 7 set = not in the world (carried, used up or not yet made)
D $6600 Entries 0-&28 are copied from #R$5B00 at every new egg (#R$9A80), which then sets bit 7 on &27-&36 and clears it on the rest.
@ $6700 label=THING_ROW
b $6700 Thing table: character row (0-23) of thing i's top-left cell; only 0-&28 change in play
@ $6800 label=THING_COL
b $6800 Thing table: character column (0-31) of thing i's top-left cell; only 0-&28 change in play
@ $6900 label=THING_TYPE
b $6900 Thing table: type of thing i, an index into #R$6A00
@ $6A00 label=THING_TYPES
b $6A00 Type table: 3 bytes a type (ink 0-7, graphic number for #R$8A98, kind); types 0-&42 used
D $6A00 Kind: bit 7 clear = bonus item worth kind x 100 points; &80-&89 = portable, name (kind AND 15) + 1 in #R$999E; &C0 inert, &C1 power lever, &C2 LIFT sign. The graphic bytes of types 0-8 (the toy parts and the toy) are rewritten for every egg by #R$9B08.
B $6A00,201,3
;
; ---------------------------------------------------------------- game start
@ $7743 label=NEW_GAME
c $7743 New game: egg = start egg, 5 lives, score 0, then start an egg
D $7743 Jumped to from the menu. #R$7763 is the entry for every following egg.
N $7763 Next egg (also from the eggs-delivered screen): room 1, egg number +1, Harry jumping off the truck.
@ $7763 label=NEXT_EGG
N $779B Reset the objects, machines and monsters for this egg.
N $77A4 The truck drives in.
N $77AA Set up room 1's contents.
@ $77B9 label=MAIN_LOOP
c $77B9 Main loop: three frames an iteration
D $77B9 Harry moves once an iteration (#R$80B6); the object cycler (#R$7F01), the monsters (#R$8C0A) and Harry's contact checks (#R$936B) run twice; the train (#R$8EE8) and the lift (#R$90F0) once.
N $77CF Leaving the room: #R$A48B is the room delta, with the railway loop 80+1 = 71 and 71-1 = 80.
N $7838 Standing or on a ladder on arrival: the restart point (#R$A46B) becomes this room.
;
; ---------------------------------------------------------------- contact with things
@ $9515 label=COLLECT_BONUS
c $9515 Harry touches the current thing (#R$A402): bonus item, or a portable/fixed thing (#R$956B)
D $9515 A bonus item (kind bit 7 clear) is taken on contact: gone for this egg, kind x 100 x egg points, plus two random digits 0-7 in the tens and units.
@ $956B label=TAKE
c $956B TAKE pressed while touching a portable thing: pick it up, or put it in the basket being carried
D $956B Kind bit 6 set (fixed thing) goes to #R$95F0. Needs TAKE (bit 6 of #R$A48A) and the latch #R$A562 clear. The girder (&25) is never taken; the ladder (&26) only when Harry is standing (state 1).
N $958C Carrying something: only a basket &20+g takes thing i when i/8 = g (g = 0 toy parts, 1 milk, 2 cocoa, 3 sugar), counting it in #R$A567+g.
N $95BC Hands empty: name to the status bar, remember the thing and its height. Taking the toy back off the egg maker clears factory bit 3.
N $95DF Out of the world, its cells cleared, its image erased, latch set.
@ $95F0 label=FIXED_THING
N $95F0 Fixed things: kind AND 7 = 1 power lever, 2 LIFT sign, else nothing.
@ $95FF label=LEVER
N $95FF The lever: moving left (dx &A45C negative) switches the power off, otherwise on.
@ $9606 label=POWER_ON
c $9606 Power on: factory bit 0, green lamp and lever shown, make the toy or the egg if they were waiting
D $9606 The restart point becomes #R$962F (room 115, row 21, column 30).
@ $962F label=POWER_RESTART
b $962F Harry's restart record after switching the power on (26 bytes, as #R$A46B)
@ $9649 label=POWER_OFF
c $9649 Power off: factory bit 0 cleared, red lamp and lever shown, the train back to room 74
@ $9663 label=LIFT_SIGN
c $9663 Touching the LIFT sign in room 105 swaps it for OUT OF ORDER (thing i-3) for the rest of the egg
;
; ---------------------------------------------------------------- dropping
@ $96B1 label=DROP
c $96B1 TAKE pressed while carrying: drop the thing at Harry's feet; into a hopper if it is the right one
D $96B1 Called twice an iteration from #R$936B after the contact test. Hands empty goes to the girder (#R$9934). The thing goes in Harry's left column when he faces left (+&0D non-zero), else his right column, bottom row level with his feet; refused if any cell it would cover has a non-zero type.
N $96D9 Place it; if #R$9B24 says a cell was occupied, take it back out and give up.
N $9715 Dropped: in this room, hands empty, latch set.
N $972C The toy goes to #R$985B.
N $9731 Anything under its left column: it stays. Otherwise, in columns 9-23 of a hopper room with the right thing, it falls in.
N $9752 Room 33 milk (or basket &21), 51 cocoa (&22), 95 toy parts (&20), 110 sugar (&23).
@ $9796 label=DROP_FALLS
N $9796 Falls: out of the world, its cells cleared, its record copied to the falling record #R$A546, dy = -2.
@ $97BA label=FALLING
c $97BA Move the falling thing down 2 pixels; on landing (on a cell boundary, any non-zero cell under it) deliver it
@ $97FA label=DELIVER
c $97FA A thing has landed in its hopper: count it; eight of a kind fills the vat
R $97FA A Thing index
N $9801 A basket: add its count (#R$A567+g) to the vat's.
N $9810 One ingredient: add 1. Toy parts go to #R$9872.
N $981D Exactly 8: FULL! sign (thing &30+g), factory bit 4+g, 10,000 x egg points, an extra life, then the egg check.
@ $985B label=TOY_PLACED
c $985B The toy dropped in room 48 with Harry in column 16 or right: it is on the egg maker (factory bit 3)
@ $9872 label=PART_DELIVERED
c $9872 A toy part fell into the toy maker: show its light (thing &29+part), count it
@ $9883 label=TOY_BASKET
c $9883 The toy-parts basket fell into the toy maker: show the lights of every part out of the world, add its count
@ $989E label=TOY_CHECK
c $989E Make the toy if the power is on, it is not made yet and 8 parts are in
D $989E Hides the eight lights, puts the toy (thing &27) in room 95, factory bit 1, 20,000 x egg points, an extra life; in room 95 the lights are overprinted with black spaces.
@ $98F2 label=EGG_CHECK
c $98F2 Make the egg if power, toy made, toy on the egg maker and the three vats are full (factory OR 4 = &EF)
D $98F2 Factory bit 4, the egg (thing &28) appears in room 48, the toy goes, 20,000 x egg points, an extra life.
@ $9934 label=GIRDER
c $9934 TAKE with empty hands in room 96, standing on the girder: swing it to its other place
D $9934 The girder (&25) lies at row 13, column 10 (factory bit 2 clear) or bridges the gap at row 14, column 19 (bit 2 set). Harry is left falling.
@ $9986 label=SET_CARRYING
c $9986 Put name A (0-10) from #R$999E in the status bar's carrying string and print it
R $9986 A Name number
;
; ---------------------------------------------------------------- room set-up and the egg
@ $99F6 label=ROOM_THINGS
c $99F6 Room set-up: mark the cells of every portable thing (0-&28) in this room in the cell-type map
D $99F6 Called by #R$7913 after the monsters. Things are drawn later, one at a time, by #R$7F01 and the interrupt.
@ $9A10 label=THING_CELLS
c $9A10 XOR the cells under portable thing L with &40 (&41 girder, &42 ladder); note any non-zero cell met
D $9A10 Also fills IY+0 to IY+&0D of the record at IY from the thing's position and type.
R $9A10 HL &6600 + thing index (preserved)
R $9A10 IY Sprite record to fill (#R$A402)
R $9A10 O:(#R$9B24) The last non-zero cell type met (0 = all cells were empty)
@ $9A80 label=EGG_INIT
c $9A80 Reset everything for a new egg: things, factory, counts, monsters, toy graphics, train
N $9AD2 Active monsters: indices 1 to (&83 + &19 x min(egg, 5)) AND &FF, minus one: 155, 180, 205, 230, then all 255.
@ $9B08 label=TOY_GFX
c $9B08 Point types 0-8 at this egg's toy: graphics &25, &2E, &37 or &40 onwards for eggs 1, 2, 3, 4 (then again)
@ $9B23 label=CELL_HIT
b $9B23 Unused byte, then #R$9A10's result
B $9B23,1 Unused
@ $9B24 label=CELL_HIT_TYPE
B $9B24,1 Last non-zero cell type met by #R$9A10
@ $9BD1 label=CLEAR_VISITED
c $9BD1 Clear the visited bit of every room's first-visit bonus (#R$A380)
;
; ---------------------------------------------------------------- variables
@ $A380 label=ROOM_BONUS
b $A380 Room first-visit bonus, rooms 0-120: hundreds of points x egg; bit 7 = visited this egg
D $A380 Added by #R$A107 when the room is drawn.
@ $A560 label=CARRIED
b $A560 What Harry carries and the factory counts
B $A560,1 Thing carried (&FF = nothing)
B $A561,1 Its height in rows (the drop puts its bottom level with Harry's feet)
B $A562,1 TAKE latch: 10 after a take or drop, cleared when the key is let go
B $A563,4 Delivered: toy parts, milk, cocoa, sugar (8 of one fills it)
B $A567,4 Basket contents: toy parts (&20), milk (&21), cocoa (&22), sugar (&23)
