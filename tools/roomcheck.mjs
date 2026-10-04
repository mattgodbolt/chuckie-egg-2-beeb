#!/usr/bin/env node
// Draw every room in the BBC room viewer and dump what it drew, for
// tools/roomcmp.py to compare against the original's (build/rooms).
//
//   node tools/roomcheck.mjs [first=1] [last=120]
//
// Writes build/bbcrooms/room_NNN.bin: the attribute, tile and type maps
// (768 bytes each), then the 12K screen; and build/mosfont.bin.
import { mkdirSync, writeFileSync } from "fs";
import { startBeeb } from "./beeb.mjs";

const first = parseInt(process.argv[2] ?? "1");
const last = parseInt(process.argv[3] ?? "120");
mkdirSync("build/bbcrooms", { recursive: true });
const b = await startBeeb({ disc: "build/ce2.ssd", bootSecs: 4 });
try {
    // Text is drawn from the MOS font (decision 4): the comparison needs it.
    writeFileSync("build/mosfont.bin", Buffer.from(await b.read(0xc000, 0x300)));
    for (let r = first; r <= last; r++) {
        await b.write("room", [r]);
        let ok = false;
        for (let i = 0; i < 50 && !ok; i++) {
            await b.frames(2);
            ok = (await b.peek("shown")) === r;
        }
        // shown is set before drawing starts: give the drawer time to finish.
        await b.frames(20);
        const maps = await b.read("attr_map", 768 * 3);
        const scr = await b.read(0x5000, 0x3000);
        writeFileSync(`build/bbcrooms/room_${String(r).padStart(3, "0")}.bin`, Buffer.from([...maps, ...scr]));
        if (!ok) console.log("room", r, "never shown");
    }
} finally {
    await b.close();
}
process.exit(0);
