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
Main RAM has about 3K free, sideways RAM about 190 bytes.

## Waiting on Matt

1. **Footsteps** (for-review 8): the Spectrum's two-cycle click doesn't
   carry on the SN76489. A next step that needs no decision: find how the
   BBC *Chuckie Egg* makes its footfall (its disc, jsbeeb's sound capture
   while Harry walks), then offer it and a couple of variants by ear.
2. **Checkpoints** (for-review 13): the original's rule (a checkpoint
   only on entering walking or on a ladder) is kept; a change would be a
   decision.
3. **A run on a real Master** (for-review 11).
4. **The train's rumble** (for-review 7): close enough?

## In hand

- **Sprite frames trimmed and shared** (an agent is on it): the empty top
  and bottom lines of monster and lift frames, and the 15 frames that are
  mirror images of others, measured earlier at about 1.4K of sideways RAM.
  It must keep every screen identical and every pass within 3 frames.

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
- **Sideways RAM headroom**: about 190 bytes, until the sprite work lands.
  Anything new for the bank (footstep tunes, more text) wants that first.
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
