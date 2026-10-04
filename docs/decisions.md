# Decisions

Every place the port departs from the original, or the BBC forces a choice
the original never had to make. Numbered, dated, with the reason. A decision
is only reversed by a new row that says why.

| # | Date | Decision | Why |
|---|---|---|---|
| 1 | 2026-10-04 | **Screen: MODE 1 pixels, CRTC narrowed to 256 x 192** (64 columns x 24 rows, 12K at `&5000`) | The Spectrum's exact geometry, pixel for pixel, so the map and every graphic carry over unscaled. MODE 2's 8 colours would cost half the horizontal resolution (160 pixels can't hold 256), and the one-pixel ropes and brick patterns are the look of the game. MODE 1's pixels are close to the Spectrum's shape. 12K instead of 20K, and 512-byte rows make the address arithmetic cheap. How to fit the colours into four is decision 2, still open. |
