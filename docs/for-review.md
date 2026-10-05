# For review

Calls made while working autonomously that Matt may want to change, and
things parked for discussion. The reasoning for each is in
`docs/decisions.md`.

## Open

1. **The train's rumble** (decision 12). The original toggles the beeper
   from its RNG nine times a pass; the port plays the SN76489's white
   noise, shifted about 150 times a second, while the train is noisy. The
   RNG calls stay where they were, so the game's random sequence matches.
   Is the character close enough? It sounds only while the train is in
   Harry's room with the power on. The quickest way to hear it: f0 on the
   menu for the cheats, then SHIFT with left (from room 1) down to room
   115, jump right past the generator's lever for the power, and skip on
   to the railway: the train starts each egg in room 74 and moves on a
   room every 64 passes, about 4 seconds.
2. **A run on a real Master** (decision 16): checked only in jsbeeb, with
   DFS and with ADFS. If a ROM on Matt's Master claims HAZEL
   `&D000-&D6FF`, the reset snapshot will need to move (to shadow RAM,
   driven from HAZEL).
3. **The developers' cheats** (decision 27), which Matt asked for; the
   details were my calls:
   - f0 turns on the room skip and infinite lives together, and f1-f8
     then choose the starting egg; nothing on the menu mentions them, but
     the README does.
   - The banner reads "CHEATS  SHIFT+LEFT/RIGHT  EGG n", flashing red.
   - -3 (both keys) from rooms 1 and 2 wraps to 118 and 119, where the
     Spectrum went on to rooms 254 and 255, past its room table.
   - The original's PLEASE TRY AGAIN, for a malformed cheat byte, is left
     out (MENU only makes good ones).
   - A loaded game keeps the cheats it was saved with, as well as the
     menu's, as the Spectrum never undid a cheat once applied.
4. **Text in the MOS font** (decision 4), not the Spectrum ROM's: the
   status bar, the room signs and the EGGS DELIVERED screen.

## Settled

Matt's verdicts after playing, and calls he has made:

- **Keys** (decision 25): his BBC layout by default: Z X : /, RETURN
  jump, TAB take/drop, R abort, S save. "Keys are perfect."
- **Harry's colour** (decisions 6, 18 and 24): yellow, except white in the
  18 rooms where white shows at least 2 points more of the room in its own
  colour (`WHITE_GAIN` in tools/mkrooms.py). "Looks good to me."
- **Colours** (decisions 2, 15 and 24): four a band, up to two splits
  below the status bar, never where an object crossing the split would
  change colour. Room 1's ladder is blue top to bottom (the original's is
  red): "ladder colour is great". 99.48% of pixels show in their own
  colour; the worst rooms are 106 (94%), 105 (95%) and 70 (96%). More
  colours per split would need more horizontal blank than there is, and
  more splits gained little when measured (Rich TW asked).
- **Footsteps and the life-lost tune** (decision 12): once the keyboard
  stopped clearing bit 7 of every sound byte, "footstep sound is now
  perfect. no need to change ... as is the sound for the death".
- **The front end** (decisions 13 and 23): MENU in MODE 7 holds it all
  (it began as Matt's MODE 7 loader idea). Saves and loads ask for a
  filename below the disc's catalogue, offering the last one used; ESCAPE
  from the save key in play carries on with the game (the original's tape
  abort abandons it); a disc error shows on the bottom row and asks again.
  The menu's last line shows the build, and row 23 offers the
  instructions where the original said JOYSTICK COMPATIBLE. "Load/save
  worked great."
- **BREAK in play** comes back to the menu (decision 22): "not a big
  deal" to Matt, but it was cheap by then.
- **Checkpoints**: the original takes one only when Harry enters a room
  walking or on a ladder, so a room entered by a jump or a fall sends him
  back further on a death. Kept: "I must have misremembered".
- **What it runs on** (decisions 8 and 16): a Model B with 16K of sideways
  RAM, or a Master 128. A stock-B edition is parked for the future as
  [issue #1](https://github.com/mattgodbolt/chuckie-egg-2-beeb/issues/1)
  ([docs/stock-b.md](stock-b.md), exploratory). Ruled out: a B+ edition, a
  ROM edition, the Electron.
- **No joystick** (decision 17).

## For information

- **Speed**: the original keeps to 3 frames a pass everywhere, and so does
  the port, idle and moving. The longest stretch between two waits for
  VSync (`tools/frametime.mjs`) is about 24,400 cycles idle and 27,800
  moving, of a frame's 40,000 (it was 44,800 and 48,400 before decisions
  20 and 26). There's more to have if it's ever wanted: the movement tick
  still waits out its two cycles, as the original's beeper loop did (up to
  2,900 cycles in each of the first two stretches while Harry moves);
  ending the tone from the interrupt would free that.
- **Room**: about 2.8K of main RAM and 1.6K of sideways RAM free.
