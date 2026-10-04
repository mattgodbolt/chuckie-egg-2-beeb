# The original

*Chuckie Egg 2* (A&F Software, 1985) for the 48K ZX Spectrum, as preserved
by [Spectrum Computing](https://spectrumcomputing.co.uk/entry/959/) (ZXDB
entry 959). Nothing here but this file and `SHA256SUMS` is committed: the
tape, maps, screens and text are not ours to redistribute.

    make fetch      # tools/fetch_original.sh: download and check them
    make zx         # simulate loading the tape: build/ce2.z80

| File | What it is |
|---|---|
| `ChuckieEgg2.tap` | The release the port is made from (ZXDB's TAP; the data blocks are identical to the TZX's) |
| `Chuckie Egg 2.tzx` | Andrew Barker's TZX of the original A&F release |
| `ChuckieEgg2.png`, `_Colour.png`, `_Mono.png`, `_2.gif` | Full maps, 10 x 12 rooms of 256 x 176 pixels |
| `ChuckieEgg2.scr`, `ChuckieEgg2.gif` | Loading screen, an in-game screenshot |
| `ChuckieEgg2.txt` | The inlay text |
| `ChuckieEgg2.pok` | POKEs: lives, start screen, immunity — useful addresses |
| `ChuckieEgg2.ay` | The music, as an AY file |
