# CHUCKIE EGG 2 — BBC Micro port
#
#   make          assemble build/ce2.ssd
#   make run      boot it in jsbeeb and grab a screenshot
#   make fetch    download the Spectrum original into original/
#   make zx       load the original's tape into build/ce2.z80 (SkoolKit)
#   make venv     the Python tools' environment (.venv: SkoolKit, Pillow)

BARON   ?= $(firstword $(wildcard ../baron/build/src/baron) baron)
PYTHON  ?= .venv/bin/python
TARGET   = build/ce2.ssd
SYMBOLS  = build/symbols.json
SOURCES  = $(wildcard src/*.6502)

.PHONY: all run fetch zx venv clean

all: $(TARGET)

# The symbol dump is how the test tools find the game's variables.
$(TARGET): $(SOURCES) | build
	$(BARON) -o $(TARGET) --title CHUCKIE2 --opt 3 --warn 2 --symbols $(SYMBOLS) -v -log0 build/listing.txt src/main.6502
	@grep -E '^code' build/listing.txt || true

build:
	mkdir -p build

run: $(TARGET)
	node tools/play.mjs '3,!run' shots/ --disc $(TARGET)

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
