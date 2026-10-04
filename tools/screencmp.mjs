#!/usr/bin/env node
// Two builds side by side, compared screen for screen: for checking that a
// change to the drawing (or anything else) leaves every pixel as it was.
// Both machines get the same rooms and keys (tools/frametime.mjs's spots
// and --move cycle), and at every wait for VSync in the main loop the
// screen and Harry's state must be the same on both.
//
//   node tools/screencmp.mjs old.ssd new.ssd [--passes n] [--idle] [rooms...]
//
// Each disc's symbols are beside it (.json). Exits non-zero on a difference.
import { readFileSync, existsSync, mkdtempSync } from "fs";
import { tmpdir } from "os";
import { join } from "path";
import { startBeeb } from "./beeb.mjs";

const args = process.argv.slice(2);
const flag = (name) => { const i = args.indexOf(`--${name}`); if (i < 0) return false; args.splice(i, 1); return true; };
const opt = (name, dflt) => { const i = args.indexOf(`--${name}`); if (i < 0) return dflt; const v = args[i + 1]; args.splice(i, 2); return v; };
const idle = flag("idle");
const passes = parseInt(opt("passes", "24"));
const [discA, discB, ...rest] = args;
const wanted = rest.map(Number);

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
const PHASES = [["P"], ["P", "SPACE"], ["O"], ["O", "SPACE"], ["Q"], ["A"]];
const keysFor = (pass) => (idle ? [] : PHASES[Math.floor(pass / 4) % PHASES.length]);

const dir = mkdtempSync(join(tmpdir(), "screencmp-"));
const boot = (disc) => startBeeb({ disc, symbols: disc.replace(/\.ssd$/, ".json"), bootUntil: "game_loop" });
let machines = await Promise.all([boot(discA), boot(discB)]);
let held = machines.map(() => new Set());
// Both machines afresh: after a death, as the two may not be at the same
// point in the game when the next room's hook runs (a death loop keeps it
// from running, and the faster build gets further in the time allowed).
async function reboot() {
    await Promise.all(machines.map((b) => b.close()));
    machines = await Promise.all([boot(discA), boot(discB)]);
    held = machines.map(() => new Set());
}
async function hold(i, keys) {
    const b = machines[i];
    for (const k of held[i]) if (!keys.includes(k)) await b.keyUp(k);
    for (const k of keys) if (!held[i].has(k)) await b.keyDown(k);
    held[i] = new Set(keys);
}
// Run machine b to the next stop: wait_vsync's entry or game_loop.
async function next(b) {
    const stops = [b.addr("wait_vsync"), b.addr("game_loop")];
    for (;;) {
        const r = await b.cycles(4e6);
        if (r.registers && stops.includes(r.registers.pc)) return r.registers.pc === stops[0] ? "wait" : "loop";
    }
}
const STATE = ["h_cell", "h_cell+1", "h_yf", "h_xf", "h_state", "room", "lives"];
async function snapshot(b, i, n) {
    const path = join(dir, `${i}_${n}.bin`);
    await b.call("save_memory", { session_id: b.session_id, address: 0x5000, length: 0x3000, path });
    const state = [];
    for (const s of STATE) {
        const [name, off] = s.split("+");
        state.push(await b.peek(b.addr(name) + (off ? +off : 0)));
    }
    return { screen: readFileSync(path), state };
}

// Put Harry at cell in room on both machines (the same writes at the same
// point in the game, so they stay in step).
async function enter(room, cell) {
    for (const b of machines) {
        await b.clearBreakpoints();
        await b.teleport(room, cell);
        for (let i = 0; i < 3; i++) await b.runUntil("game_loop", 30);
    }
    return (await machines[0].peek("room")) === room && (await machines[1].peek("room")) === room;
}

let events = 0, failed = false, deaths = 0;
const rooms = (wanted.length ? wanted : [...Array(120).keys()].map((i) => i + 1)).map((r) => [r, spot(r)]).filter(([, s]) => s);
outer: for (const [room, [row, col]] of rooms) {
    const cell = row * 32 + col;
    process.stderr.write(`room ${room} `);
    if (!(await enter(room, cell))) { console.log(`room ${room}: couldn't put Harry there`); await reboot(); continue; }
    for (const b of machines) {
        await b.breakpoint("wait_vsync");
        await b.breakpoint("game_loop");
    }
    const lives = await machines[0].peek("lives");
    let pass = 0;
    while (pass < passes) {
        const where = await Promise.all(machines.map((b) => next(b)));
        if (where[0] !== where[1]) { console.log(`room ${room} pass ${pass}: one machine at ${where[0]}, the other at ${where[1]}`); failed = true; break outer; }
        if (where[0] === "loop") {
            // A death ends the room, and both machines start again.
            if ((await machines[0].peek("lives")) !== lives) { deaths++; await reboot(); continue outer; }
            pass++;
            for (let i = 0; i < 2; i++) await hold(i, keysFor(pass));
            continue;
        }
        const [a, b] = await Promise.all(machines.map((m, i) => snapshot(m, i, events)));
        events++;
        const diffs = [];
        for (let k = 0; k < a.screen.length; k++) if (a.screen[k] !== b.screen[k]) diffs.push(k);
        if (diffs.length || a.state.join() !== b.state.join()) {
            console.log(`room ${room} pass ${pass}: ${diffs.length} screen bytes differ` +
                (diffs.length ? ` (first at &${(0x5000 + diffs[0]).toString(16)})` : "") +
                `; state ${a.state.join(",")} vs ${b.state.join(",")}`);
            failed = true;
            break outer;
        }
    }
    for (let i = 0; i < 2; i++) await hold(i, []);
}
console.log(`${failed ? "DIFFERENT" : "same"}: ${events} screens compared over ${rooms.length} rooms (${deaths} ended by a death)`);
await Promise.all(machines.map((b) => b.close()));
process.exit(failed ? 1 : 0);
