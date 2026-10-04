#!/usr/bin/env node
// Frames per main-loop pass in every room the original runs in 3: Harry
// stood somewhere safe (from the room dumps make rooms writes), 20 passes
// counted after 3 to settle; rooms where he dies are skipped. Prints the
// rooms over 3 frames, with how many passes took each number of frames.
//
//   node tools/perf.mjs
import { readFileSync, existsSync } from "fs";
import { startBeeb } from "./beeb.mjs";
// A cell with two empty cells over a solid floor (tools/fuzz.py's rule).
function spot(room) {
    const path = `build/bbcrooms/room_${String(room).padStart(3, "0")}.bin`;
    if (!existsSync(path)) return null;
    const t = readFileSync(path).subarray(1536, 2304);
    const spots = [];
    for (let row = 2; row < 21; row++)
        for (let col = 0; col < 31; col++) {
            const c = row * 32 + col;
            if ([0, 1].every((d) => t[c + d] === 0 && t[c + 32 + d] === 0) && t[c + 64] & 1 && t[c + 65] & 1) spots.push([row, col]);
        }
    return spots.length ? spots[spots.length >> 1] : null;
}
const b = await startBeeb({ disc: "build/test.ssd", symbols: "build/test.json", bootUntil: "game_loop" });
const rows = [];
const wanted = process.argv.slice(2).map(Number);
const spots = (wanted.length ? wanted : [...Array(120).keys()].map((i) => i + 1))
    .map((r) => [r, spot(r)]).filter(([, s]) => s).map(([r, [row, col]]) => [r, row, col]);
for (const [room, row, col] of spots) {
    // Teleport (game.6502's test hook) to row 21, column 1 if possible; then
    // let the room settle and count frames over 20 passes.
    const cell = row * 32 + col;
    await b.write("dbg_start", [cell & 255, cell >> 8, 0, 0, 1, 0]);
    await b.write("dbg_room", [room]);
    for (let i = 0; i < 3; i++) await b.runUntil("game_loop", 20);
    await b.write("lives", [5]);
    const hist = {};
    let prev = await b.peek("vsyncs");
    for (let i = 0; i < 20; i++) {
        await b.runUntil("game_loop", 20);
        const v = await b.peek("vsyncs");
        const d = (v - prev + 256) % 256;
        hist[d] = (hist[d] ?? 0) + 1;
        prev = v;
    }
    const moved = (await b.peek("room")) !== room;
    if ((await b.peek("lives")) !== 5) { rows.push([room, 0, -1]); continue; }  // died: no measure
    const fpp = Object.entries(hist).reduce((t, [d, n]) => t + d * n, 0) / 20;
    rows.push([room, fpp, await b.peek("m_count"), JSON.stringify(hist), moved]);
    await b.write("lives", [5]);
}
for (const [r, f, m, h, moved] of rows) if (f > 3.0) console.log(`room ${r}: ${f.toFixed(2)} frames a pass (${m} monsters) passes by frames ${h}${moved ? " ROOM CHANGED" : ""}`);
console.log(`${rows.filter((r) => r[2] < 0).length} rooms not measured (Harry died)`);
console.log(`worst ${Math.max(...rows.map((r) => r[1])).toFixed(2)} frames a pass over ${rows.length} rooms`);
await b.close(); process.exit(0);
