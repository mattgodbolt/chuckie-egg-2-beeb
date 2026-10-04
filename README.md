# Chuckie Egg 2 for the BBC Micro

A port of A&F Software's *Chuckie Egg 2* (1985) from the 48K ZX Spectrum to
the BBC Micro, in 6502 assembly.

### ▶ [**Try the work in progress in your browser**](https://bbc.xania.org/?disc=https://raw.githubusercontent.com/mattgodbolt/chuckie-egg-2-beeb/main/chuckie-egg-2-wip.ssd&autoboot)

That link boots [`chuckie-egg-2-wip.ssd`](chuckie-egg-2-wip.ssd), the latest
work-in-progress disc, in [jsbeeb](https://github.com/mattgodbolt/jsbeeb).

**Status: playable.** Harry, the monsters, the objects (taking, dropping,
the vats, the toy and egg makers), the truck, the train and the lifts all run
as the original's code does, checked pass by pass against the original,
through all 120 rooms. Sound: the movement tick, the train's rumble and the
life-lost tune. The front end is the original's, in MODE 7: instructions,
the menu with the high-score table, **P** play, **R** redefine keys, **L**
load and **S** save (one saved game, `CEGAME`, on the disc), **I** the
instructions again. Keys in play are the Spectrum's until redefined:
**O** left, **P** right, **Q** up, **A** down, **SPACE** jump, **1**
take/drop, **S** save, **0** abort. The menu's bottom line (and `*TYPE
!BOOT`) shows when the disc was built and from which commit.

It needs a BBC Model B with 16K of sideways RAM; the browser link above
provides one. (A Master runs the game, but its return to the menu after a
game doesn't work yet.)

See [docs/journal.md](docs/journal.md) for the story so far,
[docs/research.md](docs/research.md) for what the original is, and
[docs/decisions.md](docs/decisions.md) for the calls the port makes.

## Building

Needs [baron](https://github.com/waitingforvsync/baron) (looked for at
`../baron/build/src/baron`, else on the PATH), node, and for the Python tools
[uv](https://github.com/astral-sh/uv).

```sh
npm install     # the jsbeeb MCP client the test tools use
make venv       # SkoolKit and Pillow, for the tools that read the original
make fetch      # download the original from Spectrum Computing
make            # build/ce2.ssd
make run        # boot it headless and screenshot it
```

The original's tape, maps and text are not in this repository; `make fetch`
downloads them and checks their hashes.

## Credits

*Chuckie Egg 2* is © 1985 A&F Software. This port is by Matt Godbolt and
Claude.
