# The in-game music

`tools/mkmusic.py` arranges a MIDI file for the BBC's sound chip's three
tone channels, writing `src/data/music.bin` and `src/data/music.6502`
(decisions 46 to 48). It also writes the harmonised life-lost tune that
plays with the music on (decision 49), from the original's notes. Those two files are an adaptation of the MIDI file they were made
from, under its licence and credited to its author, not under the port's
MIT licence.

## In the game: the Sugar Plum Fairy

`sugar-plum.mid` is the *Danse de la Fée-Dragée* (the Dance of the Sugar
Plum Fairy) from Tchaikovsky's *The Nutcracker*, Op. 71a (1892), arranged
for four flutes and alto flute by Charles A Johnson (2023), as a MIDI file.
It is from IMSLP (file #870701, `PMLP3607-Sugarplum.mid`, uploaded by
Clsmaestro) and is licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

    python3 tools/mkmusic.py --midi music/sugar-plum.mid --bass-top 67 --tempo 1.05

## Not in the game: La Poule

`la-poule.mid` is Jean-Philippe Rameau's *La Poule*, from the *Nouvelles
suites de pièces de clavecin* (Paris, c. 1728), as a MIDI file by Pierre
Gouin (Les Éditions Outremontaises, Montréal, 2014), an urtext edition
from a facsimile of the original publication. It is from IMSLP
(`PMLP19132-Rameau_5.4_La_Poule.mid`) and is licensed under
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). The game
played it first (decision 46).

    python3 tools/mkmusic.py --midi music/la-poule.mid --bass-top 59
