#!/usr/bin/env node
// How long room changes take in play: Harry walks about at random (keys
// held a second or two at a time, infinite lives), and every room change
// is timed from change_room to the main loop going on. For the streaming
// edition's cache and reading ahead (docs/streaming.md): run it with
// CE2_STREAM=1 and without, and compare.
//
//   node tools/roomwait.mjs [secs=120] [--seed n] [--room r]
//
// --room starts Harry in room r, standing where tools/screencmp.mjs would
// put him (build/bbcrooms, from make rooms).
import { readFileSync } from "fs";
import { startBeeb, KEYS } from "./beeb.mjs";

const args = process.argv.slice(2);
const opt = (name, dflt) => { const i = args.indexOf(`--${name}`); return i < 0 ? dflt : parseInt(args.splice(i, 2)[1]); };
let seed = opt("seed", 1);
const startRoom = opt("room", 0);
const secs = parseFloat(args[0] ?? "120");
const rand = () => ((seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x80000000);

const b = await startBeeb({ disc: "build/test.ssd", symbols: "build/test.json", bootUntil: "game_loop" });
const CHANGE = b.addr("change_room"), LOOP = b.addr("game_loop");
const READ = "read_now" in b.syms ? b.addr("read_now") : 0;
const moves = [[KEYS.right], [KEYS.left], [KEYS.right, KEYS.jump], [KEYS.left, KEYS.jump], [KEYS.up], [KEYS.down]];
const changes = [];
let held = [];
try {
    await b.write("cheat", [0xB8]);     // decision 27: infinite lives
    if (startRoom) {
        // Standing on the middle one of the room's floor cells with two free
        // above (screencmp.mjs's spot).
        const t = readFileSync(`build/bbcrooms/room_${String(startRoom).padStart(3, "0")}.bin`).subarray(1536, 2304);
        const spots = [];
        for (let row = 2; row < 21; row++)
            for (let col = 0; col < 31; col++) {
                const c = row * 32 + col;
                if ([0, 1].every((d) => t[c + d] === 0 && t[c + 32 + d] === 0) && t[c + 64] & 1 && t[c + 65] & 1) spots.push(c);
            }
        if (!spots.length) throw new Error(`room ${startRoom}: nowhere to stand Harry`);
        await b.teleport(startRoom, spots[spots.length >> 1]);
        await b.runUntil("game_loop", 20);
    }
    let t = 0;
    while (t < secs) {
        const keys = moves[Math.floor(rand() * moves.length)];
        for (const k of held) if (!keys.includes(k)) await b.keyUp(k);
        for (const k of keys) if (!held.includes(k)) await b.keyDown(k);
        held = keys;
        let left = 1 + rand() * 2;      // seconds of these keys
        t += left;
        while (left > 0) {
            await b.breakpoint(CHANGE);
            const r = await b.run(left);
            await b.clearBreakpoints();
            left -= r.cycles_run / 2e6;
            if (JSON.parse(await b.regs()).pc !== CHANGE) break;
            const from = await b.peek("room");
            // (The streaming edition: a stop at read_now means a miss.)
            let cycles = 0, miss = false;
            for (;;) {
                await b.breakpoint(LOOP);
                if (READ) await b.breakpoint(READ);
                const w = await b.run(10);
                await b.clearBreakpoints();
                cycles += w.cycles_run;
                if (JSON.parse(await b.regs()).pc !== READ || !READ) break;
                miss = true;
                await b.cycles(1);
            }
            changes.push({ from, to: await b.peek("room"), ms: cycles / 2000, miss });
            left -= cycles / 2e6;
        }
    }
} finally {
    await b.close();
}
const ms = changes.map((c) => c.ms).sort((a, b) => a - b);
const pct = (p) => ms[Math.min(ms.length - 1, Math.floor(p * ms.length))].toFixed(0);
console.log(changes.map((c) => `${c.from}->${c.to} ${c.ms.toFixed(0)}${c.miss ? " miss" : ""}`).join("  "));
console.log(`${process.env.CE2_STREAM ? "streaming" : "sideways RAM"}: ${changes.length} room changes, ` +
    `median ${pct(0.5)}ms, 90% ${pct(0.9)}ms, worst ${ms[ms.length - 1].toFixed(0)}ms, ` +
    `over 400ms: ${ms.filter((m) => m > 400).length}` + (READ ? `, read while waiting: ${changes.filter((c) => c.miss).length}` : ""));
process.exit(0);
