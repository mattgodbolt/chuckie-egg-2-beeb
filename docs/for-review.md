# For review

Calls made while working autonomously that Matt may want to change, and
things parked for discussion. The reasoning for each is in
`docs/decisions.md`.

1. **BBC-appropriate keys** (decision 7). The Spectrum's keys are in for
   now (Q/A/O/P, SPACE for SYMBOL SHIFT's jump, 1 take/drop, 0 abort, S
   save), and the menu can redefine them. To discuss once Matt has played
   it a bit (his call to wait): BBC-style defaults (Z/X and :/?, RETURN or
   SPACE to jump?).
2. **Sideways RAM** (decision 8). A stock Model B can't hold it: about 20K
   more is needed against 4.5K free. The game wants a B with 16K of
   sideways RAM, a B+128 or a Master. jsbeeb's default B has RAM in banks
   0-7, so the browser link still works.
3. **Harry's colour** (decisions 6 and 18): yellow, except white in the 13
   rooms where white shows at least 2 points more of the room in its own
   colour; yellow things there turn white with him. The cut-off is
   `WHITE_GAIN` in tools/mkrooms.py (0.5 points: 24 rooms, 99.64%).
4. **Colour substitutions** (decision 2): rooms with more than four colours
   lose some. The worst: room 5 83%, room 48 88%, rooms 70, 51 and 24 about
   92% of pixels in their own colour. **Planned**: Rich Talbot-Watkins
   suggested more palette splits down the screen where they help (and
   pointed out the first room viewer had no yellow for Harry, since fixed by
   decision 6). Measured on the map earlier: a palette per character row,
   with paper and yellow held fixed, shows 99.6% of pixels in their own
   colour, against 97.8% now. The status bar's split shows the timing can
   be held; a split between two playfield rows has content on both sides,
   so it must change logical 1 and 2 in a horizontal blank. To be costed
   as a colour layer once the game plays. Rich TW again: raster colours a
   few times down the screen would also change non-character colours and
   look more authentic; baron's `examples/colours/` shows the technique.
   Done as decision 15 (one colour per band, up to two splits a room);
   more colours per split would need more blank time than there is.
5. **Text in the MOS font** (decision 4), not the Spectrum ROM's.
6. **A MODE 7 instructions loader** (Matt's idea). The original loaded
   from tape, so its instructions were part of the game: shown once at
   start-up, then overwritten by the first room (1,511 bytes,
   `docs/research/frontend.md` section 9). On the BBC they can be a
   separate MODE 7 program that shows the instructions and loads the game,
   saving that memory in the game itself. Planned for the loader layer.
7. **The train's rumble** (decision 12). The original toggles the beeper
   from its RNG nine times a pass; the port plays the SN76489's white
   noise, shifted about 150 times a second, while the train is noisy. The
   RNG calls stay where they were, so the game's random sequence matches.
   The character is close; is it close enough?
8. **Footsteps** (Matt, on the first sound build: "will need work but it's
   a start"). The Spectrum's two-cycle tick doesn't carry well on the
   SN76489. Consider the more melodic footfall of *Chuckie Egg* 1's BBC
   version instead of copying the Spectrum click.
9. **The front end** (decision 13). One save slot, "CEGAME", on the game
   disc (a write-protected disc gives the DFS's error, then the menu). The
   menu's last line shows the build; the original's row 23 said JOYSTICK
   COMPATIBLE and now offers the instructions again. A name can be typed
   in lower case (the original took lower case unless CAPS was held).
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
