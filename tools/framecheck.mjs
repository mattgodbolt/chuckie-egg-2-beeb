#!/usr/bin/env node
// Every room's monsters run for a while with the missing-frame trap armed:
// in the tests' build, sprite_frame stops at frame_missing if a room shows
// a frame none of its graphics groups gave (rooms.6502's room_load,
// tools/mkrecords.py). Harry is dropped into each room with infinite
// lives, so he dies there over and over and the room is entered again.
//
//   node tools/framecheck.mjs [first=1] [last=120] [--secs 8]
//
// (Four runs over a quarter of the rooms each take about 5 minutes.)
// Exits non-zero if a room trips the trap.
import { startBeeb } from "./beeb.mjs";

const args = process.argv.slice(2);
const at = args.indexOf("--secs");
const secs = at < 0 ? 8 : parseFloat(args.splice(at, 2)[1]);
const first = parseInt(args[0] ?? "1"), last = parseInt(args[1] ?? "120");
const b = await startBeeb({ disc: "build/test.ssd", symbols: "build/test.json", bootUntil: "game_loop" });
const trap = b.addr("frame_missing");
const bad = [];
try {
    await b.write("cheat", [0xB8]);     // decision 27: infinite lives (and the room skip)
    for (let room = first; room <= last; room++) {
        await b.teleport(room, 3 * 32 + 16, 0, 0, 0, 0);    // row 3, falling
        await b.breakpoint(trap);
        await b.run(secs);
        await b.clearBreakpoints();
        if (JSON.parse(await b.regs()).pc === trap) {
            bad.push(room);
            console.log(`room ${room}: a frame no group gave`);
            break;                      // the game is stuck there
        }
    }
} finally {
    await b.close();
}
console.log(bad.length ? `missing frames: room ${bad[0]}` : `rooms ${first}-${last}: every frame shown came from the room's groups`);
process.exit(bad.length ? 1 : 0);
