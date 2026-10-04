#!/usr/bin/env node
// A sampling profiler: Harry put in a room, then the PC sampled every 397
// cycles and charged to the nearest game label (MENU's labels, which share
// addresses with the game's code, left out).
//
//   node tools/sample.mjs room row col [samples]
import { startBeeb } from "./beeb.mjs";
const [room, row, col, n] = process.argv.slice(2).map(Number);
const b = await startBeeb({ disc: "build/test.ssd", symbols: "build/test.json", bootUntil: "game_loop" });
await b.teleport(room, row * 32 + col);
for (let i = 0; i < 4; i++) await b.runUntil("game_loop", 20);
await b.clearBreakpoints();
import { readFileSync } from "fs";
const menu = new Set(["src/menu.6502", "src/data/front.6502"].flatMap((f) =>
    [...readFileSync(f, "utf8").matchAll(/^\.([a-z_0-9]+)/gm)].map((m) => m[1])));
const syms = Object.entries(b.syms).filter(([k, v]) => typeof v === "number" && !k.includes(".") && v >= 0x0e00 && v < 0xc000 && !menu.has(k))
    .sort((a, b) => a[1] - b[1]);
const routine = (a) => { let lo = 0, hi = syms.length - 1, best = "?"; while (lo <= hi) { const m = (lo + hi) >> 1; if (syms[m][1] <= a) { best = syms[m][0]; lo = m + 1; } else hi = m - 1; } return a >= 0xc000 ? "OS" : best; };
const hist = {};
for (let i = 0; i < (n || 3000); i++) {
    const r = await b.cycles(397);
    const pc = r.registers?.pc ?? JSON.parse((await b.call("read_registers", { session_id: b.session_id })).content[0].text).pc;
    const name = routine(pc);
    hist[name] = (hist[name] ?? 0) + 1;
}
const total = Object.values(hist).reduce((a, b) => a + b, 0);
for (const [k, v] of Object.entries(hist).sort((a, b) => b[1] - a[1]).slice(0, 22)) console.log(`${(100 * v / total).toFixed(1).padStart(5)}%  ${k}`);
await b.close(); process.exit(0);
