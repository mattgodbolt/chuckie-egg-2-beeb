#!/usr/bin/env node
// The streaming edition's cache, traced in play: every room drawn, every
// item read (ahead, or waited for) and every sector, as Harry walks about at
// random from a room (tools/roomwait.mjs's walk). Run with CE2_STREAM=1.
//
//   node tools/cachetrace.mjs [secs=60] [--seed n] [--room r]
import { readFileSync } from "fs";
import { startBeeb, KEYS } from "./beeb.mjs";

const args = process.argv.slice(2);
const opt = (name, dflt) => { const i = args.indexOf(`--${name}`); return i < 0 ? dflt : parseInt(args.splice(i, 2)[1]); };
let seed = opt("seed", 1);
const startRoom = opt("room", 0);
const secs = parseFloat(args[0] ?? "60");
const rand = () => ((seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x80000000);

const b = await startBeeb({ disc: "build/test.ssd", symbols: "build/test.json", bootUntil: "game_loop" });
const at = { draw: b.addr("draw_room"), add: b.addr("item_add"), now: b.addr("read_now"), sector: b.addr("sector_start"), find: b.addr("find_body") };
const name = (id) => (id & 0x80 ? `g${id & 0x7f}` : `r${id + 1}`);
const moves = [[KEYS.right], [KEYS.left], [KEYS.right, KEYS.jump], [KEYS.left, KEYS.jump], [KEYS.up], [KEYS.down]];
let held = [], line = [], t = 0, waiting = false;
const flush = () => { if (line.length) console.log(line.join(" ")); line = []; };
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
    while (t < secs) {
        const keys = moves[Math.floor(rand() * moves.length)];
        for (const k of held) if (!keys.includes(k)) await b.keyUp(k);
        for (const k of keys) if (!held.includes(k)) await b.keyDown(k);
        held = keys;
        let left = 1 + rand() * 2;
        t += left;
        while (left > 0) {
            for (const a of Object.values(at)) await b.breakpoint(a);
            const r = await b.run(left);
            await b.clearBreakpoints();
            left -= r.cycles_run / 2e6;
            const regs = JSON.parse(await b.regs());
            const pc = regs.pc;
            const ms = ((secs - left) * 0).toFixed(0);
            if (pc === at.find) { flush(); line.push(`[${(t - left).toFixed(1)}s] enter r${regs.a}:`); }
            else if (pc === at.now) line.push("WAIT");
            else if (pc === at.add) line.push(`${(await b.peek("ia_ahead")) ? "ahead" : "now"}:${name(regs.a)}`);
            else if (pc === at.sector) line.push("s");
            else if (pc !== at.draw) break;
            await b.cycles(1);
        }
    }
    flush();
} finally {
    await b.close();
}
process.exit(0);
