# CHUCKIE EGG 2 — BBC Micro port
#
#   make          assemble build/ce2.ssd
#   make run      boot it in jsbeeb and grab a screenshot
#   make rooms    check every room the BBC draws against the original's
#   make wip      rebuild from a clean tree and copy the disc to
#                 chuckie-egg-2-wip.ssd, which the README links
#   make fetch    download the Spectrum original into original/
#   make zx       load the original's tape into build/ce2.z80 (SkoolKit)
#   make disasm   the original's disassembly with the research's labels,
#                 build/ce2.skool (from disasm/*.ctl)
#   make venv     the Python tools' environment (.venv with SkoolKit, Pillow)

BARON   ?= $(firstword $(wildcard ../baron/build/src/baron) baron)
PYTHON  ?= .venv/bin/python
TARGET   = build/ce2.ssd
SYMBOLS  = build/symbols.json
SOURCES  = $(wildcard src/*.6502 src/data/*)
WIP      = chuckie-egg-2-wip.ssd
# Stamped into !BOOT, so a disc says what it is: UTC build time and the
# commit, with + if the tree (the WIP disc itself aside) had changes.
BUILD   := $(shell date -u '+%Y-%m-%d %H:%M UTC') $(shell git rev-parse --short HEAD 2>/dev/null || echo NOGIT)$(shell git diff --quiet HEAD -- . ':(exclude)$(WIP)' 2>/dev/null || echo +)

.PHONY: all run rooms wip fetch zx disasm venv clean

all: $(TARGET)

# The symbol dump is how the test tools find the game's variables.
$(TARGET): $(SOURCES) | build
	$(BARON) -D 'BUILD="$(BUILD)"' -o $(TARGET) --title CHUCKIE2 --opt 3 --warn 2 --symbols $(SYMBOLS) -v -log0 build/listing.txt src/main.6502
	@grep -E '^(code|sideways) ' build/listing.txt || true

build:
	mkdir -p build

run: $(TARGET)
	node tools/play.mjs '3,!run' shots/ --disc $(TARGET)

# The room viewer: the same program with -D VIEWER=1, which steps through
# the rooms instead of playing.
VIEWER = build/viewer.ssd
$(VIEWER): $(SOURCES) | build
	$(BARON) -D VIEWER=1 -D 'BUILD="$(BUILD) viewer"' -o $(VIEWER) --title CHUCKIE2 --opt 3 --symbols build/viewer.json src/main.6502

rooms: $(VIEWER) build/rooms/room_120.bin
	node tools/roomcheck.mjs
	python3 tools/roomcmp.py

# The oracle: every room drawn by the original's own code, from a snapshot
# of a game just started.
build/rooms/room_120.bin: build/zx_start.z80
	$(PYTHON) tools/zxrooms.py --snap build/zx_start.z80

build/zx_start.z80: build/ce2.z80
	$(PYTHON) tools/zx.py '3,SPACE:tap,1,SPACE:tap,1,SPACE:tap,1,P:tap,3,>start' build/zx_ --snap build/ce2.z80

# Always from a clean tree, so the stamp names the commit the disc holds.
wip:
	@git diff --quiet HEAD -- . ':(exclude)$(WIP)' || { echo "commit first: the stamp would say +"; exit 1; }
	rm -f $(TARGET)
	$(MAKE) $(TARGET)
	cp $(TARGET) $(WIP)

fetch:
	tools/fetch_original.sh

zx: build/ce2.z80

# The research's control files, merged (monsters.ctl's `i` lines only mark
# where its blocks end, and would clash with the others').
disasm: build/ce2.skool

build/ce2.skool: build/ce2.z80 $(wildcard disasm/*.ctl)
	rm -rf build/ctl && mkdir -p build/ctl
	for f in disasm/*.ctl; do grep -v '^i' $$f > build/ctl/$$(basename $$f); done
	.venv/bin/sna2skool.py -H -c build/ctl build/ce2.z80 > $@

build/ce2.z80: original/ChuckieEgg2.tap | build
	.venv/bin/tap2sna.py original/ChuckieEgg2.tap $@

original/ChuckieEgg2.tap:
	tools/fetch_original.sh

venv:
	uv venv .venv && uv pip install --python .venv/bin/python skoolkit pillow

clean:
	rm -rf build
