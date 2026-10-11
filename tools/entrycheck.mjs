#!/usr/bin/env node
// Where Harry is first drawn on entering a room, on the original and the
// port, which must agree. make passes compares Harry's state, not the
// drawing, so it can't see a frame drawn that the original never shows
// (issue #2: the original's room set-up empties its draw list, so on the
// pass that changes room Harry isn't drawn at all).
//
//   node tools/entrycheck.mjs
//
// Each case walks Harry off a room's edge at row 21 (and once with the key
// let go as the room changes). After the room changes, at every wait for a
// frame (the original's HALTs, the port's wait_vsync, where each draws),
// the lit x extent of the screen's lines 166-178 near the edge he enters
// by is taken; the extents seen, in order, must be the same on both, the
// first being the room without him. tools/entrylog.py is the original's
// half. Exits non-zero on a difference.
import { execFileSync } from "child_process";
import { startBeeb, KEYS } from "./beeb.mjs";

// room, row, col, face, key, the x range to look at, and 1 to let go.
const CASES = [
    "2,21,2,4,left,224,255,0",      // a left exit: room 2 to 1
    "2,21,2,4,left,224,255,1",      // ... stopping there
    "1,21,29,0,right,0,31,0",       // a right exit: room 1 to 2
    "1,21,29,0,right,0,31,1",       // ... stopping there
];
const LINES = [166, 178];           // (inclusive)
const WAITS = 300;                  // enough to cross the room's edge
const SEEN = 4;                     // extents compared

const zx = JSON.parse(execFileSync(".venv/bin/python", ["tools/entrylog.py", ...CASES], { encoding: "utf8" }));

// The lit x extent of the lines between x0 and x1: MODE 1, a pixel's high
// bit in a byte's top nibble, its low bit in the bottom one.
function extent(screen, x0, x1) {
    let lo = null, hi = null;
    for (let y = LINES[0]; y <= LINES[1]; y++)
        for (let x = x0; x <= x1; x++) {
            const b = screen[(y >> 3) * 0x200 + (x >> 2) * 8 + (y & 7)];
            if (b & (0x88 >> (x & 3))) {
                lo = Math.min(lo ?? x, x);
                hi = Math.max(hi ?? x, x);
            }
        }
    return lo === null ? null : [lo, hi];
}

async function runCase(b, c) {
    const [room, row, col, face, key, x0, x1, stop] = c.split(",");
    const k = KEYS[key];
    await b.runUntil("game_loop");
    await b.teleport(+room, +row * 32 + +col, 0, 0, 1, +face);
    await b.keyDown(k);
    await b.breakpoint("wait_vsync");
    const seen = [];
    for (let n = 0; n < WAITS && seen.length < SEEN; n++) {
        const r = await b.cycles(4e6);
        if (r.registers?.pc !== b.addr("wait_vsync")) throw new Error(`${c}: never reached wait_vsync`);
        if ((await b.peek("room")) === +room) continue;
        if (stop === "1") await b.keyUp(k);
        const e = extent(await b.read(0x5000, 0x3000), +x0, +x1);
        if (!seen.length || JSON.stringify(seen.at(-1)) !== JSON.stringify(e)) seen.push(e);
    }
    await b.clearBreakpoints();
    await b.keyUp(k);
    return seen;
}

const show = (seen) => seen.map((e) => (e ? `${e[0]}-${e[1]}` : "none")).join(", ");
let failed = false;
const b = await startBeeb({ disc: "build/test.ssd", symbols: "build/test.json", bootUntil: "game_loop" });
try {
    for (const [i, c] of CASES.entries()) {
        const bbc = await runCase(b, c);
        const same = JSON.stringify(bbc) === JSON.stringify(zx[i]);
        failed ||= !same;
        console.log(`${c}: ${same ? "same" : "DIFFERS"}: Spectrum ${show(zx[i])}${same ? "" : `; BBC ${show(bbc)}`}`);
    }
} finally {
    await b.close();
}
process.exit(failed ? 1 : 0);
