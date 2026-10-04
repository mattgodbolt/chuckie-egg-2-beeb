#!/bin/sh
# Fetch the Spectrum original and its reference material from Spectrum
# Computing (ZXDB entry 959) into original/, and check them against
# original/SHA256SUMS. Not committed: they are not ours to redistribute.
set -e
cd "$(dirname "$0")/../original"
SC=https://spectrumcomputing.co.uk
get() { [ -f "$2" ] || curl -sfL "$1" -o "$2"; }
getzip() {
    [ -f "$2" ] && return
    curl -sfL "$1" -o fetch.zip && unzip -o -q fetch.zip "$2" && rm fetch.zip
}
getzip "$SC/zxdb/sinclair/entries/0000959/ChuckieEgg2.tap.zip" ChuckieEgg2.tap
getzip "$SC/pub/sinclair/games/c/ChuckieEgg2.tzx.zip" "Chuckie Egg 2.tzx"
getzip "$SC/pub/sinclair/music/ay/games/c/ChuckieEgg2.ay.zip" ChuckieEgg2.ay
get "$SC/pub/sinclair/games-info/c/ChuckieEgg2.txt" ChuckieEgg2.txt
get "$SC/pub/sinclair/games-maps/c/ChuckieEgg2.png" ChuckieEgg2.png
get "$SC/pub/sinclair/games-maps/c/ChuckieEgg2_Colour.png" ChuckieEgg2_Colour.png
get "$SC/pub/sinclair/games-maps/c/ChuckieEgg2_Mono.png" ChuckieEgg2_Mono.png
get "$SC/pub/sinclair/games-maps/c/ChuckieEgg2_2.gif" ChuckieEgg2_2.gif
get "$SC/pub/sinclair/screens/load/c/scr/ChuckieEgg2.scr" ChuckieEgg2.scr
get "$SC/pub/sinclair/screens/in-game/c/ChuckieEgg2.gif" ChuckieEgg2.gif
get "$SC/zxdb/sinclair/pokes/c/Chuckie%20Egg%202%20(1985)(A'n'F%20Software).pok" ChuckieEgg2.pok
sha256sum -c SHA256SUMS
