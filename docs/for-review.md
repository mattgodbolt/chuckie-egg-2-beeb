# For review

Calls made while working autonomously that Matt may want to change, and
things parked for discussion. The reasoning for each is in
`docs/decisions.md`.

## Open

Nothing open.

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
- **The train's rumble** (decision 12): the SN76489's white noise,
  shifted about 150 times a second while the train is in Harry's room
  with the power on, for the original's beeper clicks (the RNG calls
  stay where they were). "Passable for now."
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
- **The Master** (decision 16): played on Matt's real Master, "works a
  treat ... loading and saving and all". (If a ROM there ever claims
  HAZEL `&D000-&D6FF`, the reset snapshot would need to move.)
- **What it runs on** (decisions 8 and 16): a Model B with 16K of sideways
  RAM, or a Master 128. A stock-B edition is parked for the future as
  [issue #1](https://github.com/mattgodbolt/chuckie-egg-2-beeb/issues/1)
  ([docs/stock-b.md](stock-b.md), exploratory). Ruled out: a B+ edition, a
  ROM edition, the Electron.
- **No joystick** (decision 17).
- **The developers' cheats** (decision 27): f0 for the room skip and
  infinite lives together, f1-f8 the starting egg, a flashing banner;
  documented in the README though not on the menu; -3 from rooms 1-2
  wrapping to 118-119; no PLEASE TRY AGAIN; a loaded game keeps its saved
  cheats; cheat games may enter the high-score table. All kept, and with
  the cheats on the status bar shows the room number. "All good."
- **Text in the BBC's own font** (decision 4), read from the MOS ROM, not
  the Spectrum ROM's: the status bar, the room signs and the EGGS
  DELIVERED screen. "Definitely beeb font."

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
