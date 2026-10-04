#!/usr/bin/env node
// Frame time: the cycles of work between the main loop's waits for VSync.
// Each of a pass's three stretches must fit in a frame (40,000 cycles,
// interrupts included) for the pass to take 3 frames, as the original's
// always does; what's left before the next VSync is the slack. Harry stood
// somewhere safe in each room (tools/perf.mjs's spot), idle, or with
// --move walking, jumping and climbing on a cycle of held keys. Passes with
// a room change or a death are left out; after a death he is put back
// (three deaths end the room). Lives aren't topped up, so the game may end
// and restart on the way.
//
//   node tools/frametime.mjs [--move] [--passes n] [--spots n] [--all] [--disc build/test.ssd] [rooms...]
//
// --spots n measures each room from n spots spread across its safe ones
// (one, the middle one, by default).
//
// Prints rooms whose worst stretch leaves under 4,000 cycles (--all: every
// room), then the worst stretch over all. Stretch 1 runs from the third
// wait (the end of the last pass) to the first, 2 from the first to the
// second, 3 from the second to the third.
import { readFileSync, existsSync } from "fs";
import { startBeeb } from "./beeb.mjs";

const FRAME = 40000;
const args = process.argv.slice(2);
const flag = (name) => { const i = args.indexOf(`--${name}`); if (i < 0) return false; args.splice(i, 1); return true; };
const opt = (name, dflt) => { const i = args.indexOf(`--${name}`); if (i < 0) return dflt; const v = args[i + 1]; args.splice(i, 2); return v; };
const move = flag("move");
const all = flag("all");
const passes = parseInt(opt("passes", move ? "48" : "20"));
const disc = opt("disc", "build/test.ssd");     // its symbols beside it
const nspots = parseInt(opt("spots", "1"));
const wanted = args.map(Number);

// Cells with two empty cells over a solid floor (tools/fuzz.py's rule): n
// of them spread through the room, the middle one for n = 1.
function spots(room, n) {
    const path = `build/bbcrooms/room_${String(room).padStart(3, "0")}.bin`;
    if (!existsSync(path)) return [];
    const t = readFileSync(path).subarray(1536, 2304);
    const spots = [];
    for (let row = 2; row < 21; row++)
        for (let col = 0; col < 31; col++) {
            const c = row * 32 + col;
            if ([0, 1].every((d) => t[c + d] === 0 && t[c + 32 + d] === 0) && t[c + 64] & 1 && t[c + 65] & 1) spots.push([row, col]);
        }
    return spots.length ? [...Array(n).keys()].map((k) => spots[Math.floor((k + 0.5) * spots.length / n)]) : [];
}

// Held keys for each pass of --move, a phase every 8 passes: right, a jump
// right, left, a jump left, up, down.
const PHASES = [["P"], ["P", "SPACE"], ["O"], ["O", "SPACE"], ["Q"], ["A"]];
const keysFor = (pass) => PHASES[Math.floor(pass / 8) % PHASES.length];

const b = await startBeeb({ disc, symbols: disc.replace(/\.ssd$/, ".json"), bootUntil: "game_loop" });
const LOOP = b.addr("game_loop"), WAIT = b.addr("wait_vsync"), WAITED = WAIT + 6;
if ((await b.peek(WAITED)) !== 0x60) throw new Error("wait_vsync's RTS isn't at wait_vsync + 6");

let held = new Set();
async function hold(keys) {
    for (const k of held) if (!keys.includes(k)) await b.keyUp(k);
    for (const k of keys) if (!held.has(k)) await b.keyDown(k);
    held = new Set(keys);
}

// Run to the next of the three breakpoints: [kind, cycle count].
async function next() {
    for (;;) {
        const r = await b.cycles(4e6);
        if (!r.registers) continue;
        const pc = r.registers.pc;
        const kind = pc === LOOP ? "L" : pc === WAIT ? "E" : pc === WAITED ? "R" : null;
        if (kind) return [kind, r.registers.elapsed_cycles];
    }
}

// Put Harry at cell in room (tools/beeb.mjs's teleport) and let the room
// settle. Game over (lives aren't topped up here) restarts the game on the
// way, so check, and try again a few times.
async function enter(room, cell) {
    await b.clearBreakpoints();
    for (let tries = 0; tries < 8; tries++) {
        await b.teleport(room, cell);
        for (let i = 0; i < 3; i++) await b.runUntil("game_loop", 30);
        if ((await b.peek("room")) === room) return true;
    }
    return false;
}

const results = [];
const rooms = (wanted.length ? wanted : [...Array(120).keys()].map((i) => i + 1))
    .flatMap((r) => spots(r, nspots).map((s) => [r, s]));
for (const [room, [row, col]] of rooms) {
    const cell = row * 32 + col;
    const worst = [0, 0, 0], frames = {};
    let counted = 0, deaths = 0, pass = 0, entered = false;
    // Passes from Harry put in the room until a death, then again from the
    // start (at most three times).
    while (pass < passes && deaths < 3) {
        if (!(await enter(room, cell))) break;
        entered = true;
        await b.write("lives", [5]);
        await b.breakpoint(LOOP); await b.breakpoint(WAIT); await b.breakpoint(WAITED);
        // At game_loop: run the passes, logging every event.
        let [kind, t] = await next();
        while (kind !== "L") [kind, t] = await next();
        let prev = null;            // the last pass: its events, and whether it counts
        let start = { room: await b.peek("room"), lives: 5, vsyncs: await b.peek("vsyncs") };
        for (; pass < passes; pass++) {
            if (move) await hold(keysFor(pass));
            const ev = [];
            for (;;) {
                [kind, t] = await next();
                if (kind === "L") break;
                ev.push([kind, t]);
            }
            const end = { room: await b.peek("room"), lives: await b.peek("lives"), vsyncs: await b.peek("vsyncs") };
            const ok = ev.map((e) => e[0]).join("") === "ERERER" && end.room === start.room && end.lives === start.lives;
            if (ok) {
                const d = (end.vsyncs - start.vsyncs + 256) % 256;
                frames[d] = (frames[d] ?? 0) + 1;
                counted++;
                const seg = [prev?.ok ? ev[0][1] - prev.ev[5][1] : 0, ev[2][1] - ev[1][1], ev[4][1] - ev[3][1]];
                for (let i = 0; i < 3; i++) worst[i] = Math.max(worst[i], seg[i]);
            }
            prev = { ok, ev };
            start = end;
            if (end.lives !== 5) { deaths++; pass++; break; }
        }
        await hold([]);
        await b.clearBreakpoints();
    }
    if (!entered) { results.push({ room, row, col, skipped: true }); continue; }
    results.push({ room, row, col, counted, worst, frames, deaths, last: await b.peek("room") });
}
const fmt = (n) => String(n).padStart(6);
let overall = 0, overallRoom = 0;
for (const r of results) {
    if (r.skipped) { console.log(`room ${String(r.room).padStart(3)}: not measured (couldn't put Harry there)`); continue; }
    const w = Math.max(...r.worst);
    if (w > overall) { overall = w; overallRoom = r.room; }
    if (all || FRAME - w < 4000)
        console.log(`room ${String(r.room).padStart(3)}${nspots > 1 ? ` at ${r.row},${r.col}` : ""}: stretches ${r.worst.map(fmt).join(" ")}  slack ${fmt(FRAME - w)}  ` +
            `passes by frames ${JSON.stringify(r.frames)} (${r.counted} counted${r.deaths ? `, ${r.deaths} deaths` : ""})${r.last !== r.room ? ` ended in room ${r.last}` : ""}`);
}
const over = results.filter((r) => !r.skipped && Math.max(...r.worst) > FRAME).length;
console.log(`${move ? "moving" : "idle"}: worst stretch ${overall} cycles (room ${overallRoom}), slack ${FRAME - overall}; ${over} rooms over a frame`);
await b.close(); process.exit(0);
