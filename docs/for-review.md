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
   92% of pixels in their own colour. A per-row palette change could fix
   those rooms if they look wrong in play.
5. **Text in the MOS font** (decision 4), not the Spectrum ROM's.
6. **A MODE 7 instructions loader** (Matt's idea). The original loaded
   from tape, so its instructions were part of the game: shown once at
   start-up, then overwritten by the first room (1,511 bytes,
   `docs/research/frontend.md` section 9). On the BBC they can be a
   separate MODE 7 program that shows the instructions and loads the game,
   saving that memory in the game itself. Planned for the loader layer.
