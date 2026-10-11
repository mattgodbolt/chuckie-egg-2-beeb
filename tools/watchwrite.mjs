#!/usr/bin/env node
// Catch a stray write: Harry walks about at random (tools/roomwait.mjs's
// walk) with write breakpoints on bytes that should never change (Harry's
// frames and the tiles), and the first write stops it with the PC, the
// registers, the room and the stack.
//
//   node tools/watchwrite.mjs [secs=300] [--seed n] [--room r] [--disc d --symbols s]
import { readFileSync } from "fs";
import { startBeeb, KEYS } from "./beeb.mjs";

const args = process.argv.slice(2);
const opt = (name, dflt) => { const i = args.indexOf(`--${name}`); return i < 0 ? dflt : args.splice(i, 2)[1]; };
let seed = parseInt(opt("seed", "1"));
const startRoom = parseInt(opt("room", "0"));
const disc = opt("disc", "build/test.ssd"), symbols = opt("symbols", "build/test.json");
const secs = parseFloat(args[0] ?? "300");
const rand = () => ((seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x80000000);

const b = await startBeeb({ disc, symbols, bootUntil: "game_loop" });
const watched = [];
for (const [sym, n] of [["harry_gfx", 0x120], ["tiles", 0x100]])
    for (let o = 4; o < n; o += 24) watched.push(b.addr(sym) + o);
const moves = [[KEYS.right], [KEYS.left], [KEYS.right, KEYS.jump], [KEYS.left, KEYS.jump], [KEYS.up], [KEYS.down], [KEYS.down], ["SHIFT", KEYS.right], ["SHIFT", KEYS.left]];
let held = [], t = 0, hit = null;
try {
    await b.write("cheat", [0xB8]);
    if (startRoom) {
        const m = readFileSync(`build/bbcrooms/room_${String(startRoom).padStart(3, "0")}.bin`).subarray(1536, 2304);
        const spots = [];
        for (let row = 2; row < 21; row++)
            for (let col = 0; col < 31; col++) {
                const c = row * 32 + col;
                if ([0, 1].every((d) => m[c + d] === 0 && m[c + 32 + d] === 0) && m[c + 64] & 1 && m[c + 65] & 1) spots.push(c);
            }
        await b.teleport(startRoom, spots[spots.length >> 1]);
    }
    let lastRoom = -1;
    const base = b.addr("harry_gfx"), golden = await b.read(base, 0x200);
    const intact = async () => (await b.read(base, 0x200)).every((x, i) => x === golden[i]);
    while (t < secs && !hit) {
        const keys = moves[Math.floor(rand() * moves.length)];
        for (const k of held) if (!keys.includes(k)) await b.keyUp(k);
        for (const k of keys) if (!held.includes(k)) await b.keyDown(k);
        held = keys;
        const left = 1 + rand() * 2;
        t += left;
        for (const a of watched) await b.breakpoint(a, "write");
        const r = await b.run(left);
        await b.clearBreakpoints();
        const room = await b.peek("room");
        if (room !== lastRoom) { process.stdout.write(`${room} `); lastRoom = room; }
        if (r.cycles_run < left * 2e6 - 10) hit = JSON.parse(await b.regs());
        else if (!(await intact())) { console.log("\ncorrupt, no breakpoint hit"); hit = JSON.parse(await b.regs()); }
    }
    if (hit) {
        const sp = hit.s ?? hit.sp;
        console.log(`\nwrite at t=${t.toFixed(1)}s room ${await b.peek("room")}:`, hit);
        console.log("stack", (await b.read(0x100 + ((sp + 1) & 0xff), 16)).map((x) => x.toString(16)).join(" "));
        await b.shot("shots/watchwrite.png");
    } else console.log("\nno stray write");
} finally {
    await b.close();
}
process.exit(0);
