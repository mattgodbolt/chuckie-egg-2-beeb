# Next steps

The port is finished. The whole game plays on a Model B with sideways RAM,
on a stock 32K Model B (CE2S, which streams its rooms from the disc), and
on a Master 128, all from the same disc. Every room draws as the
original's does, scripted play matches the original pass by pass, and the
sideways RAM edition has music. `make check` tests all of it, and CI runs
it for both editions on both machines. The GitHub issues are all closed.

What's left is optional. None of it needs a decision before it can start,
and none of it is planned.

## If anyone picks it up again

- **More pass-by-pass coverage.** `make fuzz` runs random walks in random
  rooms on both machines. More seeds would help, and so would variants
  that start Harry carrying things or with the factory's flags set, so
  that the walks reach the vats, the hoppers and the lifts more often.
  Some scenarios are still missing: a basket filled and emptied into a
  hopper, the toy made with the power on, and the train killing Harry.
- **The movement tick from the interrupt.** The footstep tick waits out
  its two cycles of tone, as the original's beeper loop did. Ending the
  tone from the VSync interrupt would give those cycles back. The music
  already shows how to share the chip safely (`mu_busy`, decision 46).
- **Lower bass notes.** The tone channels can't go below B2, so the
  music's bass goes up an octave under that. Toggling a channel's volume
  from a timer interrupt can fake lower notes, as other BBC games do.
- **Vibrato on the tune's voice.** The flute has some; the chime's
  octave-up first frame (decision 48) would need to work with it.
- **Music in CE2S.** That edition has no memory to spare for it now.

## Left as the original had it

The front end's text is the original's word for word, including "Don't
forget to enter the competition", which closed long ago. The original is
the specification, so it stays.
