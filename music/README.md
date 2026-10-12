# The in-game music

`la-poule.mid` is Jean-Philippe Rameau's *La Poule*, from the *Nouvelles
suites de pièces de clavecin* (Paris, c. 1728), as a MIDI file by Pierre
Gouin (Les Éditions Outremontaises, Montréal, 2014), an urtext edition
from a facsimile of the original publication. It is from IMSLP
(`PMLP19132-Rameau_5.4_La_Poule.mid`) and is licensed under
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).

`tools/mkmusic.py` arranges it for the BBC's sound chip, three voices from
the harpsichord's six, as `src/data/music.bin` and `src/data/music.6502`
(decision 46). Those two files are an adaptation of Gouin's, so they are
under CC BY-SA 4.0 too, credited to him, not under the port's MIT licence.
