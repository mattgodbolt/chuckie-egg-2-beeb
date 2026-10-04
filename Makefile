# CHUCKIE EGG 2 — BBC Micro port
#
#   make          assemble build/ce2.ssd
#   make run      boot it in jsbeeb and grab a screenshot
#   make rooms    check every room the BBC draws against the original's
#   make wip      copy the built disc to chuckie-egg-2-wip.ssd, which the
#                 README links for playing in the browser
#   make fetch    download the Spectrum original into original/
#   make zx       load the original's tape into build/ce2.z80 (SkoolKit)
#   make venv     the Python tools' environment (.venv with SkoolKit, Pillow)

BARON   ?= $(firstword $(wildcard ../baron/build/src/baron) baron)
PYTHON  ?= .venv/bin/python
TARGET   = build/ce2.ssd
SYMBOLS  = build/symbols.json
SOURCES  = $(wildcard src/*.6502 src/data/*)

.PHONY: all run rooms wip fetch zx venv clean

all: $(TARGET)

# The symbol dump is how the test tools find the game's variables.
$(TARGET): $(SOURCES) | build
	$(BARON) -o $(TARGET) --title CHUCKIE2 --opt 3 --warn 2 --symbols $(SYMBOLS) -v -log0 build/listing.txt src/main.6502
	@grep -E '^code &' build/listing.txt || true

build:
	mkdir -p build

run: $(TARGET)
	node tools/play.mjs '3,!run' shots/ --disc $(TARGET)

rooms: $(TARGET) build/rooms/room_120.bin
	node tools/roomcheck.mjs
	python3 tools/roomcmp.py

# The oracle: every room drawn by the original's own code, from a snapshot
# of a game just started.
build/rooms/room_120.bin: build/zx_start.z80
	$(PYTHON) tools/zxrooms.py --snap build/zx_start.z80

build/zx_start.z80: build/ce2.z80
	$(PYTHON) tools/zx.py '3,SPACE:tap,1,SPACE:tap,1,SPACE:tap,1,P:tap,3,>start' build/zx_ --snap build/ce2.z80

wip: $(TARGET)
	cp $(TARGET) chuckie-egg-2-wip.ssd

fetch:
	tools/fetch_original.sh

zx: build/ce2.z80

build/ce2.z80: original/ChuckieEgg2.tap | build
	.venv/bin/tap2sna.py original/ChuckieEgg2.tap $@

original/ChuckieEgg2.tap:
	tools/fetch_original.sh

venv:
	uv venv .venv && uv pip install --python .venv/bin/python skoolkit pillow

clean:
	rm -rf build
