# For review

Calls made while working autonomously that Matt may want to change, and
things parked for discussion. The reasoning for each is in
`docs/decisions.md`.

1. **BBC-appropriate keys** (decision 7). The Spectrum's keys are in for
   now (Q/A/O/P, SPACE for SYMBOL SHIFT's jump, 1 take/drop, 0 abort, S
   save), and the menu can redefine them. To discuss once Matt has played
   it a bit (his call to wait): BBC-style defaults (Z/X and :/?, RETURN or
   SPACE to jump?).
2. **Sideways RAM** (decision 8). A stock Model B can't hold it: the
   data is a 16K bank, and main RAM has about 3K free beside the game.
   The game wants a B with 16K of sideways RAM, a B+128 or a Master.
   jsbeeb's default B has RAM in banks 0-7, so the browser link works.
3. **Harry's colour** (decisions 6, 18 and 24): yellow, except white in
   the 18 rooms where white shows at least 2 points more of the room in
   its own colour; yellow things there turn white with him. The cut-off
   is `WHITE_GAIN` in tools/mkrooms.py.
4. **Colours** (decisions 2, 15 and 24): four a band, up to two bands
   below the status bar, and no split where an object crossing it would
   change colour (room 1's ladder is blue top to bottom, where the
   original's is red: the grass and the sign's post take the colours
   there). 99.48% of pixels show in their own colour; the worst rooms are
   106 (94%), 105 (95%) and 70 (96%). More colours per split would need
   more horizontal blank than there is (Rich TW asked for more splits:
   measured, they gained little).
5. **Text in the MOS font** (decision 4), not the Spectrum ROM's.
6. **A MODE 7 instructions loader** (Matt's idea): done as MENU
   (decision 13), which holds the whole front end.
7. **The train's rumble** (decision 12). The original toggles the beeper
   from its RNG nine times a pass; the port plays the SN76489's white
   noise, shifted about 150 times a second, while the train is noisy. The
   RNG calls stay where they were, so the game's random sequence matches.
   The character is close; is it close enough?
8. **Footsteps** (Matt, on the first sound build: "will need work but it's
   a start"). The Spectrum's two-cycle tick doesn't carry well on the
   SN76489. Consider the more melodic footfall of *Chuckie Egg* 1's BBC
   version instead of copying the Spectrum click.
9. **The front end** (decisions 13 and 23). Saves and loads ask for a
   filename below the disc's catalogue, offering the last one used. ESCAPE
   from the save key in play carries on with the game (the original's
   abort of a tape save abandons it). A disc error (write protected, disc
   full, bad name) shows on the bottom row and the name is asked for again.
   The menu's last line shows the build; the original's row 23 said
   JOYSTICK COMPATIBLE and now offers the instructions again. A name can be
   typed in lower case (the original took lower case unless CAPS was held).
10. **BREAK during play** comes back to the menu (decision 22). Matt: not
   a big deal, as lots of games didn't; it was cheap by then.
11. **The Master** is supported again (decision 16), checked only in
   jsbeeb: worth a run on Matt's real Master. If a ROM on it claims HAZEL
   `&D000-&D6FF`, the reset snapshot will need to move (to shadow RAM,
   driven from HAZEL).
12. **Speed**: the original keeps to 3 frames a pass everywhere, and now
   so does the port, idle and moving: the longest stretch between two
   waits for VSync (`tools/frametime.mjs`) is 25,700 cycles idle and
   28,500 moving, of a frame's 40,000 (it was 44,800 and 48,400, with 2
   and 9 rooms taking 4 frames for some passes). Decision 20 (frames
   stored a column at a time) is part of it. Left: the movement tick
   still waits out its two cycles, as the original's beeper loop did (up
   to 2,900 cycles in each of the first two stretches while Harry moves);
   ending the tone from the interrupt would free that, if the
   interrupt's sound write can be kept from breaking into the game's.
13. **Checkpoints.** The original takes one only when Harry enters a room
    walking or on a ladder, so a room entered by a jump or a fall (room 4
    from room 3, for one) sends him back further on a death. The port
    keeps that. Changing it would be a numbered decision; say if you want
    it.
