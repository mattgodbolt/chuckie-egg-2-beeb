; Chuckie Egg 2 (ZX Spectrum, A&F 1985): front end, input, sound and text.
; SkoolKit control-file entries for docs/research/frontend.md. Only addresses
; in that scope; merge with the other subsystems' .ctl files.

; ---------------------------------------------------------------------------
; Start-up and instructions (overwritten by the room maps once play starts)

b $5E6F Leftover partial copy of the instructions code at #R$60C2
D $5E6F Never executed: a stale copy of the first 358 bytes of #R$60C2 (&60C2-&6227) that the tape image happens to contain, followed by zeros. Overwritten by the room maps.
B $5E6F,358,8
S $5FD5,237 Zeros

@ $60C2 label=START
c $60C2 Entry point: title page and two instruction pages
D $60C2 The tape load returns here (ERR_SP points at &A488, which holds &60C2 on the tape), in IM 1 on the loader's stack at &A48A. Text goes through RST &10 to the stream in #R$65FD: 2 = screen, 3 = ZX Printer.
  $60C2 Black border, white on black, clear the screen.
  $60C5 Title page.
T $60C8,83,n3:28:n3:21:n3:24:n1
C $611B Wait for a key (LAST_K).
  $6127 'P' (CAPS SHIFT + P) and a ZX Printer on port &FB (bit 6 low)?
  $6131 Then send the two text pages to the printer instead of the screen.
  $6136 Page 1.
T $613C,599,30:n1,61:n1,62:n1,12:n1,59:n1,31:n1,31:n1,31:n1,10:n1,30:n1,29:n1,30:n1,30:n1,30:n1,18:n1,31:n1,30:n1,26:n1
C $6393 Wait 10 frames and a key, clear the screen.
  $6396 Page 2.
T $6399,541,31:n1,30:n1,31:n1,25:n1,29:n1,28:n1,27:n1,27:n1,29:n1,30:n1,11:n1,61:n1,27:n1,26:n1,28:n1,12:n1,25:n1,26:n2,18:n1
C $65B6 Wait 10 frames and a key, clear the screen, then the menu.

@ $65BC label=PRINT_INSTR
c $65BC Print the inline string after the CALL through RST &10
D $65BC Opens the stream in #R$65FD (ROM CHAN-OPEN), then prints bytes until &FF. Control codes are the ROM's (&16 = AT row,col; &0D = newline); lines wrap at 32 columns.

@ $65CC label=WAIT_KEY_CLS
c $65CC Wait 10 frames, wait for a key, then clear the screen
@ $65DD label=CLS_INSTR
  $65DD Black border; ATTR_P = ATTR_T = 7.
  $65E8 AT 0,0 on the current stream.
T $65EB,4,n4
C $65EF Clear pixels and attributes to 0.

@ $65FD label=INSTR_STREAM
b $65FD Stream for the instructions: 2 = screen, 3 = printer

; ---------------------------------------------------------------------------
; Start-up proper

@ $7698 label=INIT
c $7698 One-time start-up after the instructions
D $7698 ERR_SP points at &A488: from here on a ROM error report restarts at &7698.
  $769F The byte at &FFFF (outside the tape image: normally 0) is a developer cheat byte; kept in &A3FC.
@ $76AB label=APPLY_CHEATS
  $76AB A = cheat byte. 0: nothing. &A0-&BF: bits 0-2 = starting egg - 1, bit 3 = CAPS + left/right changes room, bit 4 = infinite lives. Anything else: PLEASE TRY AGAIN and reset.
  $76BF Clear pixels, attributes 7.
T $76C5,22,n5:16:n1
C $76DB Wait 150 frames, then reset the Spectrum.
  $76E4 Starting egg - 1.
  $76EB Bit 3: NOP out the JP at #R$78D5 to enable the room skip.
  $76FB Bit 4: NOP out DEC (HL) at &8A7D (lives).
@ $7703 label=INIT2
  $7703 Stack at &FFF0. IM 2 vector table &FE00-&FF00 = &FD, JP &7ED9 at &FDFD, I = &FE.
  $7721 Back up the 3 x 41 bytes at &6600, &6700, &6800 (object tables) to &5B00; &9A80 restores them at every new game.
  $773C No game in progress (lives = 0), then the menu.

; ---------------------------------------------------------------------------
; Input

@ $78C1 label=READ_KEYS
c $78C1 Read the eight control keys into &A48A
D $78C1 For each (port high byte, mask, code) entry of #R$A42C in turn, shift in 1 if the key is down. The first entry ends up in bit 7: 7 abort, 6 take/drop, 5 save, 4 up, 3 down, 2 left, 1 right, 0 jump.
@ $78D5 label=ROOM_SKIP_GATE
  $78D5 JP #R$7902; NOPped by cheat byte bit 3.
  $78D8 CAPS SHIFT held with left/right: change room by -1/+1 (-3 with both), wrapping 1-120, and redraw.
@ $7902 label=KEY_ACTIONS
  $7902 Abort: straight back to the menu (no high-score check).
  $7908 Save: save the game to tape, then carry on.

@ $9CC2 label=READ_KEMPSTON
c $9CC2 Read the Kempston joystick (port &1F) into &A3FB
D $9CC2 Called after each of the main loop's three HALTs. A reading of 0 or &1B-&FF (no interface: floating bus) clears &A3FB; otherwise the joystick bits are remapped to the key bits (right 1, left 2, down 3, up 4, fire 0) and ANDed in, so a direction counts only if it was held at all three reads.
@ $9CE7 label=MERGE_KEMPSTON
c $9CE7 OR the joystick bits into the control byte, re-arm &A3FB with &1F


@ $A42C label=KEY_TABLE
b $A42C Control keys: 8 x (port high byte, mask, code)
D $A42C In bit order 7 to 0: abort 0, take/drop 1, save S, up Q, down A, left O, right P, jump SYMBOL SHIFT. The code is only used to refuse duplicates when redefining (&80 CAPS, &81 SYM SH, &82 SPACE, &83 ENTER; the default jump entry says &82 though it is SYMBOL SHIFT). Saved with the game.
B $A42C,24,3
B $A444,1 Cleared with the table by #R$9CF8


; ---------------------------------------------------------------------------
; Text output

@ $7DE1 label=CLS_PIXELS
c $7DE1 Clear the screen's pixels (not the attributes)

@ $7E34 label=AT
c $7E34 Set the print position: C = row, B = column
D $7E34 Sets DF_CC (screen) and &7F84 (attribute address).
@ $7E51 label=PRINT
c $7E51 Print the inline string after the CALL in the ROM font
D $7E51 Codes: &16 r c = AT; &00-&15 a = set attribute a (ATTR_P; the code byte itself is ignored, 1 in practice); &17-&FE = character through CHARS; &FF = end. Switches CHARS to the ROM font (#R$A15C) and back to the tiles (#R$A165).
@ $7E65 label=PRINT_CODE
@ $7E71 label=PRINT_ROOM_CHAR
  $7E71 Room-text entry: also records the attribute and the code (bit 7 set) in the room maps.
@ $7E91 label=PRINT_CHAR
  $7E91 Print character A from CHARS at DF_CC in attribute ATTR_P, advance one column.

@ $A0F7 label=FILL_ATTRS
c $A0F7 Fill all 768 attributes with A (and set ATTR_P)

@ $A15C label=FONT_ROM
c $A15C CHARS = &3C00: the Spectrum ROM font (glyphs &20-&7F at &3D00)
@ $A165 label=FONT_TILES
c $A165 CHARS = &73B8: the tile set (tiles &20 up at &74B8)

@ $A097 label=WAIT14
c $A097 Wait 14 frames
@ $A09D label=NAME_COL
b $A09D Name entry: column and row of the cursor

; ---------------------------------------------------------------------------
; Status bar

@ $A0BD label=ADD_SCORE
c $A0BD Add A to score digit BC (0 = most significant) and redraw it
D $A0BD Carries into the digit above; a carry out of digit 0 is lost. Digits are drawn straight from the ROM font to row 1, column BC (attributes untouched).
@ $A0E2 label=DRAW_ROM_GLYPH
c $A0E2 Draw ROM-font character A at screen address HL

@ $A107 label=DRAW_SCORE
c $A107 Status bar: print the score; first visit to a room scores its bonus
D $A107 Ten digits at row 1, column 0, leading zeros in the first five shown as spaces. Then if bit 7 of &A380+room is clear, set it and add (its value) x (egg number) to the hundreds digit.
T $A10A,6,n6
@ $A2B9 label=DRAW_LIVES
c $A2B9 Status bar: lives, min(lives, 9) x tile &56 then tile &37 (blank) at row 1, column 22
@ $A2DD label=EXTRA_LIFE
c $A2DD Add a life (at most 255) and redraw them
@ $A36E label=DRAW_CARRYING
c $A36E Status bar: what Harry carries, an 8-character name at row 1, column 12
D $A36E The name inside the string is overwritten from #R$999E. Saved with the game.
T $A371,14,n5:8:n1

@ $999E label=OBJECT_NAMES
t $999E Names shown under CARRYING, 11 x 8 characters
T $999E,88,8

; ---------------------------------------------------------------------------
; Menu, redefine keys, high scores

@ $9BDC label=MENU
c $9BDC The menu: high scores, P/R/L/S
D $9BDC Also where abort, game over, a failed load or save, and a finished redefine land.
T $9BF9,157,n5:14:n3:18:n3:20:n3:15:n3:19:n6:3:n3:8:n3:4:n3:6:n3:3:n3:8:n1
@ $9C96 label=MENU_LOOP
C $9C96 Wait for a key: r, p, l, s (lower case only: LAST_K).
@ $9CB6 label=WAIT_LAST_K
c $9CB6 Wait for a key: clear LAST_K, HALT until it is non-zero

@ $9CF8 label=REDEFINE
c $9CF8 Redefine the eight keys
D $9CF8 Prompts in screen order up, down, left, right, jump, take/drop, abort, save; each waits 14 frames, then for a key that is not already taken.
T $9D0E,18,n3:14:n1
C $9D20 Clear the key table.
T $9D34,21,n3:17:n1
C $9D49
T $9D53,21,n3:17:n1
C $9D68
T $9D72,21,n3:17:n1
C $9D87
T $9D91,21,n3:17:n1
C $9DA6
T $9DB0,21,n3:17:n1
C $9DC5
T $9DCF,21,n3:17:n1
C $9DE4
T $9DEE,21,n3:17:n1
C $9E03
T $9E0D,21,n3:17:n1
C $9E22 Wait 28 frames, back to the menu.

@ $9E2D label=HISCORE_CHECK
c $9E2D Game over: enter the high-score table if the score beats an entry
D $9E2D Compares the score with each entry from the top; the first one it strictly beats is where it goes.
@ $9E65 label=HISCORE_INSERT
c $9E65 Insert the score, take the name
D $9E65 Moves the entries below down 20 bytes, copies the score, fills the name with dots. Name entry: any character &20-&7E (as LAST_K gives it: lower case unless CAPS), DELETE (CAPS + 0) rubs out, ENTER finishes; at most 10 characters; no visible cursor.
T $9E9B,16,n5:10:n1
@ $9F37 label=DRAW_HISCORES
c $9F37 Draw the high-score table (rows 0-13)
T $9F44,47,n5:12:n5:24:n1
C $9F73 Ten rows through RST &10: space, name, "..", 10 digits, space.
T $9FA8,28,n3:24:n1
@ $A56B label=HISCORES
b $A56B High-score table: 10 x (10-character name, 10 digits 0-9)
B $A56B,200,c10:10

@ $9FC5 label=SCAN_KEY
c $9FC5 Wait for a key; return its code from #R$A06F, B = port high byte, C = row reading
@ $9FEB label=CAPTURE_KEY
c $9FEB Take one key definition into the table entry at IX, and print its name
T $A039,6,5:n1
C $A03F
T $A048,7,6:n1
C $A04F
T $A058,5,4:n1
C $A05D
T $A067,6,5:n1
C $A06D
@ $A06F label=KEY_CODES
b $A06F Key codes by half-row (&7FFE first), 5 keys each, bit 0 first
D $A06F &80 CAPS SHIFT, &81 SYMBOL SHIFT, &82 SPACE, &83 ENTER, else ASCII.
B $A06F,40,5

; ---------------------------------------------------------------------------
; Load and save

@ $A16E label=SAVE
c $A16E Save the game (and the high-score table) to tape
D $A16E Five headerless blocks (flag &FF) through the ROM's SA-BYTES, with a 0.9 s pause between them. Blocks 2-5 are XORed with the game's random number generator seeded &7B7B7B7B (#R$A09F) while they are saved. A failed save (BREAK) goes to the menu.
@ $A1F6 label=SAVE_BLOCK
c $A1F6 Save DE bytes from IX with the ROM's SA-BYTES (data pilot), returning through #R$A203
@ $A203 label=TAPE_RET
c $A203 Tape return: black border; carry clear (failed) goes to the menu
@ $A20F label=PAUSE
c $A20F Pause: 65536 x 50 T-states (0.92 s)
@ $A21B label=LOAD
c $A21B Load a saved game (or table)
D $A21B The first block must match #R$A34C in its first 10 bytes. If the loaded lives (&A3FA) is 0 the menu comes back (a table); otherwise play resumes in the saved room.
@ $A2A2 label=LOAD_BLOCK
c $A2A2 Load DE bytes to IX with the ROM's LD-BYTES (entered at &056B), returning through #R$A203
@ $A09F label=CIPHER
c $A09F XOR BC bytes at HL with the random number generator, seeded &7B7B7B7B
@ $A34C label=SAVE_ID
b $A34C Save-file identity block (17 bytes; the first 10 are checked)
@ $A35D label=LOAD_ID
b $A35D Buffer the identity block is loaded into

@ $9B25 label=MASTER_TAPE
c $9B25 Dead code: the developers' tape mastering routine
D $9B25 Saves the BASIC loader "CHUCK 2" and the 48,896-byte code block. Never called.
B $9B6D,17 Header for "CHUCK 2"
B $9B7E,66 The BASIC loader
B $9BC0,17 Header for the code block

; ---------------------------------------------------------------------------
; Game over, eggs delivered

@ $8A8A label=GAME_OVER
c $8A8A Game over: yellow-on-black, clear, high-score entry, menu
@ $948A label=EGGS_DELIVERED
c $948A Eggs delivered screen
D $948A Black screen, "EGGS DELIVERED:-" and the egg number (A3F9, up to two digits) at row 11, wait for a key, next egg from room 1.
T $9495,22,n5:16:n1

; ---------------------------------------------------------------------------
; Sound

@ $92E7 label=NOISE
c $92E7 Train noise: if &91B5 is set, put bit 4 of the next random number on the speaker
D $92E7 Called nine times per three-frame pass of the main loop.
@ $92F4 label=MOVE_SOUND
c $92F4 Harry's movement click: pick the pitch from his state, two cycles of a square wave
D $92F4 State &A487: 7 (jump) uses step &A485, 0 uses &A486, others a fixed pitch. Called twice per pass of the main loop while Harry's dx/dy (&A45C/&A45D) is non-zero.
@ $9337 label=TONE
c $9337 Square wave: L = pitch (half period 4L + 115 T-states), H = 0, DE + 1 = cycles
@ $A2EB label=DEATH_TUNE
c $A2EB Life lost: play 16 notes through the ROM's BEEPER
D $A2EB POKE 41707,201 (RET here) is the POK file's "no music on death".
@ $A30C label=DEATH_NOTES
w $A30C Death tune: 16 x (BEEPER HL = pitch, DE = cycles)
W $A30C,64,4
