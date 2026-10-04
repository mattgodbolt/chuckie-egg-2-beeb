#!/usr/bin/env node
// What each call in the main loop costs: a breakpoint on every JSR (and
// tail JMP) in game_loop and the parts it calls for each frame
// (draw_frame, contact_pass), read from build/listing.txt; Harry put in a
// room as tools/perf.mjs does; the cycles from each call to the next logged
// over some passes. Prints each call's average and worst (those over 100
// cycles), and each stretch's (wait to wait) worst.
//
//   node tools/passcost.mjs room row col [passes] [--keys P,SPACE] [--disc build/test.ssd]
//
// (Another disc's symbols and listing are beside it: name.json, listing.txt.)
import { readFileSync } from "fs";
import { startBeeb } from "./beeb.mjs";

const args = process.argv.slice(2);
const ki = args.indexOf("--keys");
const keys = ki >= 0 ? args.splice(ki, 2)[1].split(",") : [];
const di = args.indexOf("--disc");
const disc = di >= 0 ? args.splice(di, 2)[1] : "build/test.ssd";
const [room, row, col, n] = args.map(Number);
const passes = n || 20;

// The calls in a block of the listing, from its label to its first line
// that leaves it for good (a JMP to a routine, or an RTS).
const listing = readFileSync(disc.replace(/[^/]*$/, "listing.txt"), "utf8").split("\n");
const addr = (l) => parseInt(l.trim().split(/\s+/)[0], 16);
function calls(label) {
    const start = listing.findIndex((l) => new RegExp(`^\\s+[0-9A-F]{4}\\s+\\.${label}$`).test(l));
    if (start < 0) throw new Error(`no ${label} in build/listing.txt`);
    const out = [];
    for (let i = start + 1; i < listing.length; i++) {
        const m = listing[i].match(/^\s+([0-9A-F]{4})\s+(?:[0-9A-F]{2} )+\s+(JSR|JMP|RTS)\s*(\w*)/);
        if (!m) continue;
        if (m[2] === "RTS") break;
        out.push([parseInt(m[1], 16), m[3]]);
        if (m[2] === "JMP") break;
    }
    return { start: addr(listing[start]), out };
}
// (change_room and teleport are only called in passes that aren't counted)
const skip = ["change_room", "teleport"];
const stops = new Map();
for (const block of ["game_loop", "draw_frame", "contact_pass"])
    for (const [a, name] of calls(block).out) if (!skip.includes(name)) stops.set(a, name);
const LOOP = calls("game_loop").start;

const b = await startBeeb({ disc, symbols: disc.replace(/\.ssd$/, ".json"), bootUntil: "game_loop" });
if (b.addr("game_loop") !== LOOP) throw new Error("build/listing.txt is from another build");
await b.teleport(room, row * 32 + col);
for (let i = 0; i < 3; i++) await b.runUntil("game_loop", 20);
await b.write("lives", [5]);
for (const k of keys) await b.keyDown(k);

for (const a of [...stops.keys(), LOOP]) await b.breakpoint(a);
async function next() {
    for (;;) {
        const r = await b.cycles(4e6);
        if (r.registers && (stops.has(r.registers.pc) || r.registers.pc === LOOP)) return [r.registers.pc, r.registers.elapsed_cycles];
    }
}
let [pc, t] = await next();
while (pc !== LOOP) [pc, t] = await next();
let ref = null, sum = [], worst = [], counted = 0, lastTail = null, inRoom = await b.peek("room");
const stretch = [0, 0, 0];
for (let p = 0; p < passes; p++) {
    const times = [[pc, t]];
    for (;;) {
        [pc, t] = await next();
        times.push([pc, t]);
        if (pc === LOOP) break;
    }
    // A pass with a room change or a death isn't counted.
    const seq = times.slice(1, -1).map((x) => x[0]).join();
    const lives = await b.peek("lives"), now = await b.peek("room");
    if (lives !== 5) await b.write("lives", [5]);
    if (lives !== 5 || now !== inRoom || (ref && seq !== ref.seq)) { inRoom = now; lastTail = null; continue; }
    if (!ref) {
        ref = { seq, names: times.slice(1, -1).map((x) => stops.get(x[0])) };
        sum = ref.names.map(() => 0); worst = ref.names.map(() => 0);
    }
    counted++;
    // times[i + 1] is call i's stop; it runs to the next stop.
    ref.names.forEach((_, i) => {
        const c = times[i + 2][1] - times[i + 1][1];
        sum[i] += c; worst[i] = Math.max(worst[i], c);
    });
    const waits = ref.names.map((name, i) => (name === "wait_vsync" ? i + 1 : -1)).filter((i) => i >= 0);
    const at = (i) => times[i][1];
    if (lastTail !== null) stretch[0] = Math.max(stretch[0], lastTail + at(waits[0]) - at(0));
    stretch[1] = Math.max(stretch[1], at(waits[1]) - at(waits[0] + 1));
    stretch[2] = Math.max(stretch[2], at(waits[2]) - at(waits[1] + 1));
    lastTail = times[times.length - 1][1] - at(waits[2] + 1);
}
console.log(`room ${room}: ${counted} passes counted`);
if (ref) ref.names.forEach((name, i) => {
    if (name === "wait_vsync") { console.log("  ---- wait_vsync"); return; }
    if (worst[i] < 100) return;
    console.log(`  ${name.padEnd(16)} avg ${String(Math.round(sum[i] / counted)).padStart(6)}  worst ${String(worst[i]).padStart(6)}`);
});
console.log(`  stretches worst: ${stretch.join(" ")}`);
await b.close(); process.exit(0);
