# Front end, input, sound and text

Everything outside play itself: start-up, instructions, menu, redefine keys,
joystick, load/save, high scores, game over, the eggs-delivered screen, the
status bar, every sound and every string. Addresses are the running game's.
SkoolKit entries for all of it: `disasm/frontend.ctl`.

How each fact was checked:

- **[run]**: by running the original on SkoolKit's simulator, usually with
  a throwaway script in `build/research/frontend/` (named in brackets).
  Sound was measured by logging every `OUT` to port `&FE` with its T-state
  and PC (`snd.py`, `death.py`).
- **[code]**: read from the disassembly only.

The execution map from all these runs is `build/exec_frontend.map` (3,554
addresses: the original `build/exec.map` plus menu, redefine, play, death,
game over, save/load and eggs-delivered runs).

## Summary

| Thing | Where | Size | How it works |
|---|---|---|---|
| Instructions | `&60C2-&65FD` | 1,340 | 3 pages, ROM font, printed with RST `&10`. Overwritten when play starts, so you only see them once |
| Menu | `&9BDC-&9CC1` | 230 | high-score table, then P / R / L / S, read from `LAST_K` |
| Keys | `&78C1`, table `&A42C` | 82 + 25 | 8 keys: abort, take/drop, save, up, down, left, right, jump. No pause |
| Kempston | `&9CC2-&9CF7` | 54 | always read and ORed in with the keys; no menu option |
| Save / load | `&A16E-&A2B8` | 331 + 30 + 34 | 5 headerless tape blocks, 1,320 bytes: the whole game state, the keys and the high-score table, XORed with the game's random numbers |
| High scores | table `&A56B`, code `&9E2D-&9FC4` | 200 + 408 | 10 x (10-character name, 10 digits) |
| Sound | `&92E7-&936A`, `&A2EB-&A34B` | 132 + 97 | 3 sounds: a movement click, the train's noise, and the life-lost tune. No sound anywhere else |
| Fonts | `&3C00` (ROM), `&73B8` (tiles) | 768 ROM | all text uses the **Spectrum ROM font**. The tile set only gives the lives icon |
| Completion | `&948A` | 91 | "EGGS DELIVERED:- n", then the next egg. There is no ending and no competition code |

## 1. Start-up

### How the tape starts it [run]

At `&60C2` the snapshot has `SP = &A48A`, interrupts on, IM 1, and
`ERR_SP` (`&5C3D`) = `&A488`, which holds `&60C2` on the tape. Presumably the load
ends through the ROM's error exit (`LD SP,(ERR_SP): RET`), which pops
`&60C2`: that would be the auto-start (inferred from the registers, not
traced). Until `&7703` the game runs on that stack, below
`&A48A`, over game variables that are set up later.

### Instructions, `&60C2` [run]

```
60C2  CLS_INSTR (&65DD): border 0, ATTR_P = ATTR_T = 7, AT 0,0 on stream (&65FD),
      clear pixels AND attributes to 0
      PRINT_INSTR (&65BC) title page            ; CHAN-OPEN (&65FD), RST &10 until &FF
611B  wait for LAST_K <> 0 (HALT loop; no initial delay)
      if LAST_K = 'P' (&50: CAPS SHIFT + P) and IN (&FB) bit 6 = 0 (ZX Printer present):
          (&65FD) = 3                          ; both text pages go to the printer
6136  CLS_INSTR; page 1
6393  WAIT_KEY_CLS (&65CC): 10 HALTs, wait for LAST_K, CLS_INSTR; page 2
65B6  WAIT_KEY_CLS; JP &7698
```

- `&65FD` = 2 (screen) or 3 (printer). The stream byte is only used here.
- Text uses ROM control codes: `&16 r c` = AT, `&0D` = newline. Lines wrap
  at 32 columns. The ROM font prints in ATTR_T = 7 (white on black). The
  rest of the screen is attribute 0.
- Printer, tested [run] (`printer.py`): with no printer (port `&FB` reads
  `&FF`) CAPS SHIFT + P does nothing. With port `&FB` bit 6 low, `&65FD`
  becomes 3, the two pages go to port `&FB` (82,280 writes under an
  emulated encoder), the screen stays black, and each page still waits for
  a key. Whether the last line, which has no `&0D`, ever leaves the
  printer buffer is **unverified**.
- `&5E6F-&5FD4` holds a stale copy of the first 358 bytes of `&60C2`, then
  zeros up to `&60C1`. It is never executed [code].

The screens as displayed (OCR of the screen against the ROM font, `ocr.py`):

```
Title page (rows 9, 11, 13):
  CHUCKIE EGG 2  INSTRUCTIONS!          (AT 9,2)
     PRESS ANY KEY TO VIEW              (AT 11,5)
    CAPS/SHIFT-P TO PRINTOUT            (AT 13,4)

Page 1 (rows 0-20):
Harry has to make a giant egg,
to do this he must collect from
around the fun factory, cocoa
milk and sugar. Eight of each of
these must be dropped into the
correct vat.
To add to the confusion each egg
must contain a toy kit. The
eight parts of this can also be
found in the factory. These are
cyan and must be dropped in the
toy maker.
Once you have completed an egg
you must take it to dispatch.
You will then be able to start
on the next egg, but this time
you will have more monsters to
contend with...!!!
You may use a joystick or if
you prefer you can define your
own keys for playing with.

Page 2 (rows 0-20):
The game contains a save option
which can be used at any time,
you will be able to select your
own key for this purpose.
The game is designed to be an
arcade/adventure in the true
sense. So remember that you
will find items that can be
moved from place to place and
then used to get out of tricky
situations.
A couple of hints, you find most
factories need power to work.
You only have two hands for
carrying things unless...!
Some pipes are more slippery
than others.
Don't forget to enter the
competition. Have fun.....

Henhouse Harry....
```

The raw strings rely on the 32-column wrap: there is no space at a wrap
point, so the bytes read "each ofthese", "each eggmust", "find
mostfactories". "joystick or if" is followed by 3 padding spaces, and
"Have fun....." by `&0D &0D`.

| String | Address | Bytes |
|---|---|---|
| Title page | `&60C8` | 83 |
| Page 1 | `&613C` | 599 |
| Page 2 | `&6399` | 541 |
| AT 0,0 (in CLS_INSTR) | `&65EB` | 4 |

### One-time initialisation, `&7698` [run]

```
7698  DI; (&A488) = &7698         ; from now on a ROM error report restarts here
      A = (&FFFF); (&A3FC) = A    ; cheat byte, see below
76AB  APPLY_CHEATS(A)
7703  SP = &FFF0
      &FE00-&FF00 = &FD (257 bytes); &FDFD = JP &7ED9; I = &FE   ; IM 2 table (IM 2 is
                                                                ; selected only in play)
      copy 41 bytes each from &6600, &6700, &6800 to &5B00, &5B29, &5B52
                                  ; initial object tables, restored by &9A80 at every new game
      (&A3FA) = 0                 ; lives = 0: no game in progress
      JP MENU (&9BDC)
```

**The cheat byte at `&FFFF`** [run]. The tape image ends at `&FEFF`, so
`&FFFF` is whatever was there before: the bottom row of UDG "U", normally 0.
`APPLY_CHEATS` (`&76AB`) is also called again after every load, with the
saved copy at `&A3FC`.

| `&FFFF` | Effect |
|---|---|
| `&00` | none (the normal case) |
| `%101xxxxx` | bits 0-2: starting egg - 1 (`&A3FD`). Bit 3: `&78D5-&78D7` = NOP, which turns on CAPS SHIFT + left/right to change room (±1, wrapping 1-120; both keys give -3). Bit 4: `&8A7D` = NOP, infinite lives (the POK file's 35453,0) |
| anything else | screen attribute 7, "PLEASE TRY AGAIN" at 12,8, border 0, 150 HALTs (3 s), then `JP 0`: the Spectrum resets |

Checked: `&BA` gives egg 3 and a working CAPS + P room skip. `&11` gives
PLEASE TRY AGAIN, then a reset. It is probably a developers' or testers'
switch. The port can leave it out (a decision).

### New game, `&7743` (for reference; game logic) [code]

Egg `&A3F9` = `&A3FD`, then +1. Lives `&A3FA` = 5. Score `&A445-&A44E` = 0.
Carrying name = "NOTHING " (`&999E` copied to `&A376`). Room 1. Harry's
record comes from `&89E5`. Then `&9A80` (clear the room-visited flags,
restore the object tables) and the truck drives in (`&9028`: 14 steps of
10 frames, 2.8 s), then IM 2 and the main loop.

## 2. The menu, `&9BDC` [run]

```
9BDC  FILL_ATTRS(6); border 0; CLS_PIXELS; CHAN-OPEN 2; IM 1; EI; IY = &5C3A
      DRAW_HISCORES (&9F37)
      PRINT (&7E51) the menu text (157 bytes at &9BF9)
9C96  loop: A = WAIT_LAST_K (&9CB6)      ; clear LAST_K, HALT until non-zero
        'r' -> REDEFINE (&9CF8); JP MENU
        'p' -> new game (&7743)
        'l' -> LOAD (&A21B)
        's' -> SAVE (&A16E); EI; loop     ; no redraw after a save
```

Only lower case works (`LAST_K` in L mode): with CAPS held, P is ignored.
Abort, game over, a failed save or load and a finished redefine all come
back to `&9BDC`. The menu does not touch lives, so after an abort the
aborted game is still in memory, and S in the menu saves it as a game that
L can resume [code].

Screen (OCR, `ocr.py`; `DRAW_HISCORES` covers rows 0-13):

```
 0|           HIGH  SCORES               attr &06 (yellow on black)
 2|     ........................         row 2 and row 13: 24 spaces, attr &0E (yellow on blue)
 3|      A&F.........0000000000          rows 3-12: " " name ".." 10 digits " ", attr &0E,
 ..                                       col 5-28
12|      A&F.........0000000000
15|  P TO PLAY GAME         ©A&F          left: attr &07; right: attr &04 (green)
16|                       SOFTWARE
17|  R TO REDEFINE KEYS     1985
19|  L TO LOAD SAVED GAME  BY THE
20|                          AnF          ("AnF" is literally the string)
22|                       R&D TEAM
23|  JOYSTICK COMPATIBLE
```

`DRAW_HISCORES` fills every attribute with `&47` first, so the unused
cells are bright white on black.

## 3. Controls

### The key table, `&A42C` [run]

There are 8 entries of 3 bytes (port high byte, mask, code), plus a 25th
byte that is cleared along with them. `READ_KEYS` (`&78C1`) builds `&A48A`,
with the first entry in bit 7. A bit is 1 while its key is down.

| Bit | Entry | Default | Port | Mask | Code | Use |
|---|---|---|---|---|---|---|
| 7 | `&A42C` | `0` | `&EF` | 1 | `'0'` | **abort**: `JP &9BDC` at once, with no confirmation and no high-score check (`&7902`) |
| 6 | `&A42F` | `1` | `&F7` | 1 | `'1'` | **take/drop** (read at `&9570`, game logic) |
| 5 | `&A432` | `S` | `&FD` | 2 | `'S'` | **save**: `CALL SAVE` at once, no prompt, then play carries on (`&7908`) |
| 4 | `&A435` | `Q` | `&FB` | 1 | `'Q'` | up |
| 3 | `&A438` | `A` | `&FD` | 1 | `'A'` | down |
| 2 | `&A43B` | `O` | `&DF` | 2 | `'O'` | left |
| 1 | `&A43E` | `P` | `&DF` | 1 | `'P'` | right |
| 0 | `&A441` | SYMBOL SHIFT | `&7F` | 2 | `&82` | jump |

- The code byte is only used by redefine to refuse duplicates. The
  default jump entry has `&82` (the SPACE code) although its port and mask
  are SYMBOL SHIFT. That is harmless, because redefine clears the table
  first.
- The key table is part of the saved game, so a load also brings back the
  saved keys [code].
- **There is no pause key**. The only keyboard reads in play are
  `&78C1`, the cheat's CAPS check at `&78DA`, and `&9CC3` (Kempston). All
  `IN` instructions in RAM were enumerated: `&78C8`, `&78DA`, `&9CC3`,
  `&9FCB`, `&A2AD` [code].

```
78C1 READ_KEYS: C = 1
     for each entry: A = IN(port<<8 | &FE) AND mask; carry = (A == 0); RL C   ; 8 times
78D5 JP &7902                     ; NOP NOP NOP if cheat bit 3: CAPS + left/right changes room
7902 if bit 7: JP MENU            ; abort
     if bit 5: CALL SAVE
     (&A48A) = C
```

### Kempston, `&9CC2` and `&9CE7` [code; mapping run-checked]

Nothing selects the joystick: it is read all the time and merged with the
keys. That is all "JOYSTICK COMPATIBLE" means.

```
9CC2 READ_KEMPSTON (after each of the main loop's 3 HALTs: &7871, &789C, &78B5):
     A = IN(&1F)
     if A = 0 or A >= &1B: (&A3FB) = 0; return
     b = ((A AND &0F) << 1) OR (A bit 4 ? 1 : 0)   ; right->1 left->2 down->3 up->4 fire->0
     (&A3FB) = (&A3FB) AND b
9CE7 MERGE_KEMPSTON (once per loop, after READ_KEYS, &77BC):
     (&A48A) |= (&A3FB); (&A3FB) = &1F
```

So a joystick direction counts only if all three reads in a pass of the
loop saw it, and a read of 0 cancels everything. I infer that this is a
guard against the floating bus when no interface is fitted (port `&1F`
then returns screen bytes or `&FF`). `&8A51` clears `&A3FB` on death.
Checked [run]: Kempston right walks Harry right and fire jumps; the AND
and the `&1B` threshold are read from the code only.

### Redefine keys, `&9CF8` [run] (`zx.py ... R, Q, Q, A, ENTER, ...`)

```
IM 1; border 0; CLS_PIXELS; FILL_ATTRS(5)          ; cyan on black
PRINT AT 4,9 "REDEFINE  KEYS"
clear &A42C-&A444
for (prompt row, entry) in (7 UP &A435)(9 DOWN &A438)(11 LEFT &A43B)(13 RIGHT &A43E)
                           (15 JUMP &A441)(17 TAKE/DROP &A42F)(19 ABORT &A42C)(21 SAVE &A432):
    PRINT AT row,7 "PRESS xxxx KEY..."               ; 17 characters, so the name lands at column 24
    CAPTURE_KEY (&9FEB):
      repeat: wait 14 frames; SCAN_KEY (&9FC5)       ; loops until a key is down
              until its code is not in any entry's code byte
      entry = (port high byte, NOT(row reading OR &E0), code)
      print the name: the character itself (ROM font), or ENTER / SYM SH / CAPS / SPACE
wait 28 frames; DI; back to MENU
```

- `SCAN_KEY` scans half-rows `&7F, &BF, &DF, &EF, &F7, &FB, &FD, &FE`, bit
  0 first, and takes the code from `&A06F` (40 bytes, `"\x82\x81MNB\x83LKJHPOIUY09876"
  "12345QWERTASDFG\x80ZXCV"`). It returns B = port high byte and C = the row
  reading.
- If two keys in the same half-row are down, the mask gets both bits, and
  the key then counts as pressed only while both are down [code].
- There is no key-release wait: the 14-frame wait plus the duplicate check
  stop one press from filling two slots. Any key can be used, CAPS and
  SYMBOL SHIFT included.
- Verified: a repeated Q was refused, and ENTER, SPACE, CAPS and SYM SH
  were taken and shown by name. The table read back
  `7f 04 4d | 7f 02 81 | bf 04 4b | fb 01 51 | fd 01 41 | bf 01 83 | 7f 01 82 | fe 01 80`.

## 4. Load and save [run] (`saveload.py`, `realsave.py`, `savebreak.py`)

In play and in the menu ("S TO SAVE TABLE"), S runs the same routine,
`SAVE` (`&A16E`). It **saves everything**: the game state, the keys and the
high-score table.

| # | Block | Bytes | Contents |
|---|---|---|---|
| 1 | `&A34C` | 17 | identity block `02 07 01 'PETE' 00 06 00 00 00 00 00 00 00 00 00` (plain) |
| 2 | `&A36E-&A632` | 709 | ciphered: carrying routine and name (`&A36E`), room bonus and visited flags `&A380-&A3F8`, egg `&A3F9`, lives `&A3FA`, `&A3FB`, cheat byte `&A3FC`, start egg `&A3FD`, room `&A3FE`, the variables `&A3FF-&A42B`, keys `&A42C`, score `&A445`, Harry `&A451`, restart record `&A46B`, the variables and sprite records up to `&A56A`, high scores `&A56B` |
| 3 | `&6B00` | 256 | ciphered: game state (used by `&8B3B`, `&8D82`, `&9AE6`) |
| 4 | `&6600` | 297 | ciphered: the object tables `&6600-&6728` |
| 5 | `&6800` | 41 | ciphered: object table |

1,320 bytes in all.

- Each block goes out headerless with flag `&FF`, through the ROM's
  SA-BYTES entered at `&04D0` with the data pilot (`HL = &0C98`). The game
  pushes its own return, `&A203`, which sets the border black and, on carry
  clear (BREAK), goes `SP = &FFF0`, `JP MENU`. So the ROM's SA/LD-RET, with
  its "D BREAK" report, is never reached.
- There is no prompt and no message. The ROM's leader stripes in the border
  are the only feedback.
- Between blocks, `PAUSE` (`&A20F`) does 65,536 x 50 T-states (0.92 s).
  A real save from the menu takes 21.4 s, with blocks starting at 0.0, 3.1,
  10.1, 14.5 and 19.2 s.
- Holding SPACE during the save aborts it, back to the menu. From play this
  abandons the game, but the state stays in memory, so S in the menu can
  still save it.
- **Cipher** `&A09F`: seed the random number generator (`&91B1-&91B4`)
  with `&7B7B7B7B`, then XOR each byte with the next random number
  (`&918A`). Each ciphered block is XORed before saving and again after,
  and each call reseeds, so every block uses the same keystream. One side
  effect matters if the port keeps the original's random numbers: after any
  save or load the generator is in a fixed state, `5D 00 07 B1` (measured).
- **Load** (`&A21B`): read block 1 into `&A35D` and compare its first 10
  bytes with `&A34C` (a mismatch goes to the menu). Then read blocks 2-5
  through `LD_BLOCK` (`&A2A2`). That routine copies the start of the ROM's
  LD-BYTES (with `IN A,(&FE)` where the ROM has `OUT (&FE),A`, so the
  border is not set first) and jumps to `&056B`. Each block is deciphered.
  Then `APPLY_CHEATS(&A3FC)`.
  - If lives = 0 (a save made after game over or at power-on), the menu
    comes back and only the table (plus keys) has changed.
  - Otherwise: `SP = &FFF0`, DI, IM 2, draw the room (`&7920`), `&99F6`,
    `&9B08`, `JP &77B9` into the main loop. There is no truck intro.
- With no tape, the load waits for ever; SPACE gives up and returns to the
  menu.
- Checked: blocks captured at `&04D0` and fed back at `&056B` restored room,
  lives and score, and play resumed.
- `&9B25-&9BD0` is the developers' tape mastering routine. It writes the
  "CHUCK 2" BASIC loader and the 48,896-byte code block (header
  `CODE 16384,49152`). It is dead code: nothing calls it [code].

## 5. High scores, game over, completion

### Table `&A56B` [run]

The table is 10 entries of 20 bytes: a 10-character ASCII name, then 10
digits, each a value 0-9 with the most significant first (the same format
as the score at `&A445`). The default entries are `"A&F......."` with a
score of 0. The table is part of the saved game.

### Game over [run] (`gameover.py`, `gameover0.py`)

Every death goes through `&8A29` (13 jumps to it, `&8389-&94E9`): the life-lost tune (2.16 s), restore
Harry from the restart record, then `DEC (&A3FA)`. At 0:

```
8A8A  FILL_ATTRS(6); CLS_PIXELS          ; black screen; there is no "GAME OVER" text
      HISCORE_CHECK (&9E2D); JP MENU
```

The menu loop is reached 121 frames after the death when the score does
not qualify.

```
9E2D HISCORE_CHECK: IM 1; CHAN-OPEN 2
     for entry 1..10 (B = 10..1): compare the score with the entry digit by digit
         if score > entry: HISCORE_INSERT; return     ; strictly greater: a tie goes below
9E65 HISCORE_INSERT:
     move the entries from this one down by 20 bytes (the 10th drops off)
     copy the score in; fill the name with 10 dots
     DRAW_HISCORES; PRINT {ATTR &0F}{AT 21,11}"ENTER NAME"
     row = 13 - B (self-modifying SUB at &9EB5), column 6; C = 10 characters left
     loop on LAST_K:
       &0C (DELETE = CAPS + 0): if C < 10: back one column, put back a '.'
       &0D (ENTER): return
       &20-&7E and C > 0: store, print at the cursor, next column
```

There is no visible cursor. Letters come in lower case unless CAPS is held,
because that is how `LAST_K` gives them. The name is printed by RST `&10` in
ATTR_T `&0E` (yellow on blue). Checked: typing M, A, T, DELETE, T, ENTER
stored `"mat......."` with score 0000012340 in entry 1.

### Eggs delivered: the only "completion" [run] (`egg.py`)

In room 111 (`&6F`) with the conditions at `&9440-&9463`, the game adds
3 x egg to the ten-thousands digit and gives an extra life. Then:

```
9485  IM 1; truck drives off (&9059: 14 steps x 10 frames)
948A  FILL_ATTRS(0); CLS_PIXELS
      PRINT {AT 11,7}{ATTR 6}"EGGS DELIVERED:-"
      AT 11,24: egg number (&A3F9) in decimal, tens digit only if non-zero
      wait for LAST_K; JP &7763         ; next egg: room 1, egg + 1
```

**There is no end and no code for the competition.** The search covered
every string in RAM and every print routine call site: all `CALL &7E51`,
`CALL &65BC` and `CALL &7E91` sites, and the 28 RST `&10` bytes, each
accounted for. The egg counter just keeps climbing. From egg 100 the tens
digit would print as `:` and beyond, because it is not range-checked
[code]. The competition must have been run outside the game (the instruction
text only says "Don't forget to enter the competition").

## 6. Status bar (rows 0-1, drawn by the room drawer) [run]

| What | Where | Code | Font, attribute |
|---|---|---|---|
| `SCORE  CARRYING  LIVES` | row 0, col 5 | `&7982` (28-byte string `&7985`) | ROM, `&07` |
| score: 10 digits, leading zeros among the first five shown as spaces | row 1, col 0-9 | `DRAW_SCORE` `&A107` | ROM, `&07` |
| one digit changing | row 1, col n | `ADD_SCORE` `&A0BD` adds A to digit BC with carry (a carry out of digit 0 is lost) and redraws from `&3C00` directly (`&A0E2`), attributes untouched | ROM |
| carrying | row 1, col 12-19 | `&A36E`: a routine holding an inline string whose 8-character name at `&A376` is copied from `&999E` | ROM, `&07` |
| lives: min(lives, 9) icons, then a blank | row 1, col 22 on | `DRAW_LIVES` `&A2B9`: tile `&56`, then tile `&37` | tiles, `&07` |

- `EXTRA_LIFE` (`&A2DD`) adds a life (at most 255) and redraws.
- Lives icon, tile `&56` at `&7668`: `10 38 10 38 38 38 10 18`. Tile
  `&37` is blank.
- `DRAW_SCORE` also scores a room's first visit: if bit 7 of
  `&A380 + room` is clear, set it and add (value) x egg to the hundreds
  digit. Seen: room 2 on egg 3 gave 300.
- After the digits it executes `LD (CHARS),HL` with HL = `&A44F`: a
  harmless slip, put right by `&A36E` straight after [code].
- Object names `&999E`, 11 x 8 = 88 bytes:
  `NOTHING ` `TOY PART` `  MILK  ` ` COCOA  ` ` SUGAR  ` `A BONE  ` ` GIRDER `
  ` LADDER ` `THE TOY!` `THE EGG!` ` BASKET `.

## 7. Sound

There are three sounds and nothing else [code + run]. RAM has eight
`OUT (&FE),A` instructions. Six only set the border: `&65DE`, `&76B8`,
`&793A` (the room drawer's border, bit 4 always 0), `&9BE2`, `&9D01`,
`&A205`. Two make sound: `&92F1` and `&9357`. There is no `OUT (C)`. The
only ROM sound call is `CALL &03B5` (BEEPER) at `&A301`. So the menus,
instructions, pick-ups, machines and egg delivery are silent. That follows
from the enumeration; the logged runs (walking, jumping, egg delivery, the
train, death) saw nothing else.

Sound is not driven by the interrupt. Both in-play sounds are called from
the main loop (`&77B9-&78BE`, one pass = 3 HALTs = 3 frames), right after
`DI`, so nothing interrupts them. The IM 2 handler (`&7ED9`) makes no
sound.

### 7.1 Movement click: `MOVE_SOUND` `&92F4` and `TONE` `&9337` [run]

Each pass of the main loop calls it twice: at `&7860`, and at `&787D` just
after the first HALT. It only plays while Harry's velocity word
`&A45C/&A45D` (dx, dy: record offsets 11 and 12) is non-zero, i.e. while he
moves. The cadence measured: clicks in frames k and k+1 of every 3, the
second about 13,000 T-states (3.7 ms) after the interrupt.

```
92F4 MOVE_SOUND:                         ; called with HL = &0101
     s = (&A487)                         ; Harry's movement state
     if s = 7: a = 2*(&A485) + 42; if (&A485) < 10: a = -a     ; jump step
     elif s = 0: a = 2*(&A486) + 50                            ; fall counter
     else: n = (s+1) >> 1; if n = 2: n = 6; a = -16*n
     L0 = (a + 1) AND &FF; TONE(L0, H = 0, DE = 1)
9337 TONE: 2 square-wave cycles (high, low, high, low), starting with a short lead-in.
     High half = 4*L0 + 115 T, low half = 4*L0 + 113 T (H, an outer loop count, is always 0 here)
```

So f = 3,546,900 / (8·L0 + 228) Hz, two cycles per click: a 0.4-1.2 ms
"tick" whose pitch follows Harry's state. These were measured: state 7 at
steps 1-21, state 0 at 6-7, and state 1 (walking), each to the T-state. The
other rows come from the formula and are **unverified by run**. The state
meanings belong to the movement research. The SN76489 column uses
N = 125000 / f (the BBC's 4 MHz clock).

| Case | L0 | High/low half (T) | f (Hz) | SN76489 N | Click (ms) |
|---|---|---|---|---|---|
| state 7 (jump), `&A485` = 1 ... 9 | 213 ... 197 (-2 a step) | 967/965 ... 903/901 | 1836 ... 1966 | 68 ... 64 | 1.09 ... 1.02 |
| state 7, `&A485` = 10 ... 22 | 63 ... 87 (+2 a step) | 367/365 ... 463/461 | 4845 ... 3839 | 26 ... 33 | 0.41 ... 0.52 |
| state 0, `&A486` = n | 51 + 2n | 319+8n / 317+8n | 3546900/(636+16n) | 22 for n=0, 26 for n=6 | 0.36 + |
| state 1, 2 (1 = walking, measured) | 241 | 1079/1077 | 1645 | 76 | 1.22 |
| state 3, 4 | 161 | 759/757 | 2340 | 53 | 0.85 |
| state 5, 6 | 209 | 951/949 | 1867 | 67 | 1.07 |
| state 8 | 193 | 887/885 | 2002 | 62 | 1.00 |

So a jump ticks low (about 1.85 kHz, rising) for its first 9 steps, then
jumps to about 4.8 kHz and falls. `&9334` (`JP &9300`) is unreachable.

### 7.2 Train noise: `NOISE` `&92E7` [run]

```
92E7 NOISE: if (&91B5) <> 0: OUT (&FE), RANDOM() AND &10     ; RANDOM = &918A
```

It is called 9 times per main-loop pass: `&77CC`, `&7867`, `&7880`,
`&788C`, `&7892`, `&789F`, `&78A8`, `&78B8`, and once from `&8FA1`. The
flag `&91B5` is cleared once per pass (`&8EE8`, called from `&7883`). It is
set at `&8F9E` when the train (sprite record `&A512`, room `&A48D` cycling
71-80) is drawn in the current room while the power is on (`&A48C` bit 0).
So the result is a random square wave at about 150 samples a second, about
71 level changes a second (measured: 442 samples and 210 changes in 147
frames), held between samples: a low crackle or rumble.

Every call advances the game's random number generator (a 32-bit LFSR at
`&91B1`, seed `"9090"`; feedback is bit 6 XOR bit 3 of `&91B1`; the sample
is bit 4 of `&91B1` after the shift). So the noise changes the game's
random sequence. Shown by poking power on and the train's room, then CAPS
+ P into room 71 with the cheat byte's room skip. On the BBC the nearest
match is probably SN76489 white noise clocked from tone channel 2 at a low
rate (a decision).

### 7.3 Life lost tune: `DEATH_TUNE` `&A2EB` [run] (`death.py`)

`&8A29` calls it first thing on every death. The POK "No music on death",
41707,201, is a `RET` at `&A2EB`. It plays 16 notes from `&A30C` (4 bytes
each: `HL`, `DE` for the ROM's BEEPER) in IM 1, with interrupts off
throughout, so all sprites freeze. Then IM 2. Measured on the simulator, a
BEEPER half period is 4·HL + 118 T and a note is 2·DE + 1 half periods. The
notes follow each other with only about 0.1 ms between them.

| # | `HL` | `DE` | f (Hz, measured) | Note | Duration (ms) | SN76489 N |
|---|---|---|---|---|---|---|
| 1 | 2233 | 39 | 195.96 | G3 | 201.6 | 638 |
| 2 | 1988 | 22 | 219.76 | A3 | 102.4 | 569 |
| 3 | 2233 | 39 | 195.96 | G3 | 201.6 | 638 |
| 4 | 2505 | 17 | 174.93 | F3 | 100.0 | 715 |
| 5 | 2654 | 33 | 165.22 | E3 | 202.8 | 757 |
| 6 | 3345 | 13 | 131.39 | C3 | 102.8 | 951 |
| 7 | 2980 | 29 | 147.32 | D3 | 200.2 | 848 |
| 8 | 3544 | 12 | 124.07 | B2 | 100.7 | 1007 |
| 9 | 3345 | 78 | 131.39 | C3 | 597.5 | 951 |
| 10 | 2245 | 6 | 194.93 | G3 | 33.3 | 641 |
| 11 | 2980 | 7 | 147.32 | D3 | 50.9 | 848 |
| 12 | 2655 | 8 | 165.16 | E3 | 51.5 | 757 |
| 13 | 2506 | 9 | 174.86 | F3 | 54.3 | 715 |
| 14 | 2233 | 10 | 195.96 | G3 | 53.6 | 638 |
| 15 | 1772 | 12 | 246.11 | B3 | 50.8 | 508 |
| 16 | 1673 | 13 | 260.42 | C4 | 51.8 | 480 |

In rhythm (crotchet = 200 ms): G A G F E C D B | C (long) | G D E F G B C,
2.16 s in total. At the real 3.5469 MHz clock it is in tune to within 9
cents. With the ROM manual's 3.5 MHz formula it comes out about 23 cents
flat. Every note fits the SN76489's 10-bit range (B2 needs N = 1007 ≤ 1023).

`original/ChuckieEgg2.ay` ("Chuckie Egg 2 - Life Lost (Beeper)", ripped by
Pawel Ochman) is exactly `&A2EB-&A34B` byte for byte, plus a stand-in for
the ROM BEEPER. It is this tune and nothing more.

## 8. Text

### Printing routines [run]

- **`PRINT` `&7E51`**: prints the string inline after the CALL; the game's
  own printer, not the ROM's.
  - Codes: `&16 r c` = AT row r, column c (`&7E34` sets DF_CC and the
    attribute pointer `&7F84`). `&00-&15 a` = attribute a, into ATTR_P;
    the code byte is ignored and is 1 in every string. `&17-&FE` =
    character via CHARS. `&FF` = end.
  - It switches CHARS to the ROM font on entry and back to the tiles on
    exit.
  - `&7E91` prints one character: 8 bytes from CHARS + 8·code to DF_CC,
    and ATTR_P to the attribute.
  - `&7E71` is the room drawer's entry, which also records the cell in the
    room maps.
- **`PRINT_INSTR` `&65BC`**: the same idea through the ROM's RST `&10`,
  for the instructions.
- RST `&10` (ROM, ATTR_T) also prints the high-score rows, the name entry
  and the egg number.
- `FILL_ATTRS` `&A0F7`: all 768 attributes = A, ATTR_P = A.
  `CLS_PIXELS` `&7DE1`: `&4000-&57FF` = 0.

### Fonts [run]

- `FONT_ROM` `&A15C` sets CHARS = `&3C00`: **the Spectrum ROM font**
  (glyphs `&20-&7F` at `&3D00-&3FFF`, 768 bytes, with © at `&7F`). Every
  piece of text uses it: instructions, menu, redefine, high scores, name
  entry, status bar, eggs delivered, PLEASE TRY AGAIN, and the room signs
  (command `&02` calls `&A15C` and `&A165` around its text at
  `&7B1E` and `&7B2F`).
  - Verified by OCR: every text cell on the menu, instruction and table
    screens matched the ROM glyphs exactly.
  - The instructions use `` !',-./2ACDEFGHIKNOPRSTUVWYabcdefghijklmnoprstuvwxy``.
  - The name entry accepts any `&20-&7E`, so the port needs all 95 glyphs
    (plus ©). Whether that means copying the ROM font (Amstrad's) or using
    a lookalike is a decision.
- `FONT_TILES` `&A165` sets CHARS = `&73B8`: the tile set. Outside room
  drawing, only the lives icon (`&56`) and blank (`&37`) use it.

### Every string

These use the `&7E51` format unless noted; each includes its `&FF`.

| Address | Bytes | Text (codes in braces) |
|---|---|---|
| `&60C8` | 83 | title page (RST `&10` format) |
| `&613C` | 599 | instructions page 1 (RST `&10`) |
| `&6399` | 541 | instructions page 2 (RST `&10`) |
| `&65EB` | 4 | `{AT 0,0}` (RST `&10`) |
| `&76C5` | 22 | `{AT 12,8}{ATTR 7}PLEASE TRY AGAIN` |
| `&7985` | 28 | `{AT 0,5}{ATTR 7}SCORE  CARRYING  LIVES` |
| `&9495` | 22 | `{AT 11,7}{ATTR 6}EGGS DELIVERED:-` |
| `&98E0` | 17 | `{AT 21,9}{ATTR 0}4 spaces{AT 22,9}4 spaces` (erases 4 x 2 cells in room 95; game logic) |
| `&9BF9` | 157 | the menu (see 2) |
| `&9D0E` | 18 | `{AT 4,9}REDEFINE  KEYS` |
| `&9D34`, `&9D53`, `&9D72`, `&9D91`, `&9DB0`, `&9DCF`, `&9DEE`, `&9E0D` | 8 x 21 | `{AT r,7}` + `PRESS UP KEY.....`, `PRESS DOWN KEY...`, `PRESS LEFT KEY...`, `PRESS RIGHT KEY..`, `PRESS JUMP KEY...`, `PRESS TAKE/DROP..`, `PRESS ABORT KEY..`, `PRESS SAVE KEY...` (r = 7, 9 ... 21) |
| `&9E9B` | 16 | `{ATTR &0F}{AT 21,11}ENTER NAME` |
| `&9F44` | 47 | `{AT 0,11}{ATTR 6}HIGH  SCORES{AT 2,5}{ATTR &0E}` + 24 spaces |
| `&9FA8` | 28 | `{AT 13,5}` + 24 spaces |
| `&A039`, `&A048`, `&A058`, `&A067` | 6, 7, 5, 6 | `ENTER`, `SYM SH`, `CAPS`, `SPACE` |
| `&A10A` | 6 | `{AT 1,0}{ATTR 7}` |
| `&A371` | 14 | `{AT 1,12}{ATTR 7}` + 8-character carrying name |
| `&999E` | 88 | object names (not `&FF` terminated) |
| `&A06F` | 40 | key codes (see 3) |
| `&A56B` | 200 | high-score names and digits |

In total: 1,227 bytes of instruction text and 567 bytes of `&7E51` strings,
plus 88 of object names.

## 9. Sizes

| Range | Bytes | What | Needed |
|---|---|---|---|
| `&60C2-&65FD` | 1,340 | instructions: 112 code, 1,223 text, 4 AT, 1 stream byte | once, at start-up |
| `&7698-&7742` | 171 | start-up: cheat byte (about 90 with PLEASE TRY AGAIN), IM 2 table, object backup | once |
| `&9BDC-&9CC1` | 230 | menu (157 of it the string) | between games |
| `&9CF8-&9E2C` | 309 | redefine keys (186 strings) | between games |
| `&9FC5-&A096` | 210 | key scan, capture, key names, code table | between games |
| `&9E2D-&9F36` | 266 | high-score insert, name entry | after game over |
| `&9F37-&9FC4` | 142 | high-score table display | between games |
| `&A56B-&A632` | 200 | high-score table (data) | always (persistent) |
| `&A16E-&A2B8` | 331 | save, load, tape glue, pause | menu and play (S key) |
| `&A09F-&A0BC` | 30 | cipher | with save/load |
| `&A34C-&A36D` | 34 | save identity, load buffer | with save/load |
| `&A097-&A09E` | 8 | wait 14 frames, name-entry cursor | front end |
| `&8A8A-&8A97` | 14 | game over | play |
| `&948A-&94E4` | 91 | eggs-delivered screen (22 string) | play |
| `&78C1-&7912` | 82 | key reader, cheat room skip, abort/save | play |
| `&9CC2-&9CF7` | 54 | Kempston | play |
| `&A42C-&A444` | 25 | key table (data) | always |
| `&A0BD-&A106` | 74 | score add/draw digit, ROM-glyph draw, attribute fill | play |
| `&A107-&A15B` | 85 | score print and room bonus | play |
| `&A2B9-&A2EA` | 50 | lives display, extra life | play |
| `&A36E-&A37F` | 18 | carrying display (string inside) | play |
| `&999E-&99F5` | 88 | object names | play |
| `&92E7-&936A` | 132 | movement click and train noise | play |
| `&A2EB-&A34B` | 97 | life-lost tune (33 code, 64 notes) | play |
| `&7DE1-&7DEE`, `&7E34-&7ED8`, `&A15C-&A16D` | 14 + 165 + 18 | CLS, text printer, font switch (shared with the room drawer) | always |
| `&9B25-&9BD0` | 172 | dead: tape mastering | never |
| `&5E6F-&60C1` | 595 | dead: stale copy, then zeros | never |
| ROM `&3D00-&3FFF` | 768 | the font all text uses | always |

Totals: everything listed is 4,450 bytes of game RAM, of which 172 is dead
(the 595 bytes before `&60C2` are not counted).

- **Start-up only**: 1,511 bytes, a natural separate loader on the BBC:
  the Spectrum itself throws the instructions away when the first room is
  drawn.
- **Between games**: about 1,560 bytes (menu, redefine, high-score entry
  and display, key capture, save/load, cipher), plus the 200-byte table
  that must persist. On the BBC this could be an overlay loaded into the
  room-map area when play ends, if the table and keys are kept resident
  (a decision).
- **In play**: about 810 bytes of code and data, plus the shared printer.
- **ROM services the port must replace**:
  - the font (768 bytes);
  - RST `&10` and CHAN-OPEN (printing; stream 3 = printer);
  - the IM 1 keyboard routine giving `LAST_K` (ASCII, lower case unless
    CAPS, `&0C` DELETE, `&0D` ENTER, auto-repeat);
  - BEEPER;
  - SA-BYTES and LD-BYTES (tape; on the BBC, files);
  - the ZX Printer driver.

## 10. Open questions

- What `&A487` states 2-6 and 8 mean, and so which movement clicks a
  player hears (ladder? pipe?): see the movement research. The pitch per
  state is above.
- Whether the printer dump's last line ("Henhouse Harry....", no
  newline) ever prints on a real ZX Printer.
- Who "PETE" is (the save identity block): probably the programmer.
  Cosmetic.
