# Next steps

Where it stands (2026-10-04): the whole game plays, on a Model B with 16K
of sideways RAM and on a Master 128. Every room draws as the original's
does (120 of 120, pixel for pixel in its four colours a band), and 20
scenarios replay pass by pass identically on the original and the port,
through moving, jumping, ladders, lifts, the train, deaths, checkpoints,
the toy and egg makers and an egg's delivery. The front end is MODE 7:
instructions, high scores and names, redefined keys, saves and loads to
disc under a name, BREAK back to the menu. `make check` runs it all, and
the sound chip's bytes too; `make check MODEL=Master` on the Master.
Main RAM has about 2.9K free, sideways RAM about 1.6K.

## Waiting on Matt

Nothing: what's left in docs/for-review.md is the details of the cheats,
if Matt wants any changed.

Settled after Matt's play: a real Master ("works a treat ... loading and
saving and all"), the footsteps and the life-lost tune ("now
perfect"), the train's rumble ("passable for now"), the keys, Harry white where he is, the checkpoints (the
original's rule stays), room 1's ladder, saving and loading.

## A stock Model B edition? (Matt's moon shot)

[docs/stock-b.md](stock-b.md), an exploratory study (not current): not
from memory alone (about 2K short even with a 1-bit screen), but a disc
edition fits with about 1K spare, loading each room's data from disc as
Harry enters: room changes of about 1.0s, or 0.4s with the drive kept
spinning. Parked for the future as
[issue #1](https://github.com/mattgodbolt/chuckie-egg-2-beeb/issues/1).
Ruled out: a B+ edition, a ROM edition, the Electron.

## Worth doing, no decision needed

- **More pass-by-pass coverage.** `make fuzz` (random walks in random
  rooms against the original) has run seeds 1-4; more seeds, and
  variants that start Harry carrying things or with the factory's flags
  set, would reach the vats, the hoppers and the lifts more often.
  Scenarios still to add: a basket filled and emptied into a hopper, the
  toy made with the power on, the train killing Harry.
- **The movement tick from the interrupt** (for-review 12): the tick
  waits out its two cycles as the original's beeper loop did, up to 2,900
  cycles in each of the first two stretches of a pass while Harry moves.
  Ending the tone from the interrupt would free them; the interrupt's
  sound write must not break into one of the game's.
- **More from the sprite frames**, if the bank fills again (journal,
  decision 26): each column's own empty lines (about 660 bytes, but
  columns of different lengths in the inner loops), Harry's mirror frames
  (118, but the collision test reads his pixels).
- **The front end's text** is the original's word for word, including
  "Don't forget to enter the competition", long closed. Leave it, as the
  original is the specification, unless Matt says otherwise.

## Done this round

- BBC keys by default (decision 25): Z X : /, RETURN, TAB, R, S.
- The README has screenshots, how to play and a licence; the disc is
  `chuckie-egg-2.ssd` (`make disc`).
- BREAK in play comes back to the menu (decision 22).
- Sound fixed: the keyboard was clearing bit 7 of every byte the chip got;
  `make sound` now checks the bytes.
- Redefining keys catches quick presses; the high-score name isn't asked
  for again after CTRL-BREAK.
- No palette split cuts an object in two colours (decision 24): room 1's
  ladder is one colour.
- Saves and loads ask for a filename, with the disc listed (decision 23).
- Sprite frames packed (decision 26): monsters', lifts' and objects'
  empty lines left out, 15 mirror images drawn from their twins; 1,427
  bytes of sideways RAM back, every screen the same.
