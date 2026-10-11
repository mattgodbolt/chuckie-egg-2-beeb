#!/bin/sh
cd "$(dirname "$0")"
${BARON:-../../../../baron/build/src/baron} -o nmit.ssd --opt 3 --warn 2 --symbols nmit.json -v -log0 nmit.lst nmi8271.6502 && python3 mkimg.py nmit.ssd nmit40.ssd
${BARON:-../../../../baron/build/src/baron} -o nmiw.ssd --opt 3 --warn 2 --symbols nmiw.json -v -log0 nmiw.lst nmi1770.6502 && python3 mkimg.py nmiw.ssd nmiw40.ssd
${BARON:-../../../../baron/build/src/baron} -o dtest.ssd --opt 3 --warn 2 --symbols dtest.json -v -log0 dtest.lst dtest.6502 && python3 mkimg.py dtest.ssd dtest40.ssd
