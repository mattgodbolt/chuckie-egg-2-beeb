# For review

Calls made while working autonomously that Matt may want to change, and
things parked for discussion. The reasoning for each is in
`docs/decisions.md`.

1. **BBC-appropriate keys** (decision 7). The Spectrum's keys are in for
   now (Q/A/O/P, SPACE for SYMBOL SHIFT's jump, 1 take/drop, 0 abort, S
   save), at Matt's request. To discuss: BBC-style defaults (Z/X and :/?,
   RETURN or SPACE to jump?), and whether the original's redefine-keys
   screen covers it.
2. **Sideways RAM** (decision 8). A stock Model B can't hold it: about 20K
   more is needed against 4.5K free. The game wants a B with 16K of
   sideways RAM, a B+128 or a Master. jsbeeb's default B has RAM in banks
   0-7, so the browser link still works.
3. **Yellow in every room** (decision 6), so Harry is always yellow; it
   costs some scenery colour (room 5's white pipes are yellow).
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
10. **BREAK during play** isn't caught: the OS's page 2 holds the game's
   tables then, so the reset that follows may misbehave. CTRL-BREAK, then
   SHIFT-BREAK, gets back to the menu. Making BREAK return to the menu
   cleanly would mean keeping `&0258` and `&027F-&029B` free of tables.
11. **The Master**: the game's reset doesn't come back to `MENU` there yet
   (MOS 3.20's start-up options and workspace differ from OS 1.20's).
