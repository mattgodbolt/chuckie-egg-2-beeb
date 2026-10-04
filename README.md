# Chuckie Egg 2 for the BBC Micro

A port of A&F Software's *Chuckie Egg 2* (1985) from the 48K ZX Spectrum to
the BBC Micro, in 6502 assembly.

**Status: just started.** The screen geometry is settled and the original is
being taken apart. See [docs/journal.md](docs/journal.md) for the story so
far, [docs/research.md](docs/research.md) for what the original is, and
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
