#!/usr/bin/env node
// What each call to some routines costs, from entry to return: Harry put in
// a room as tools/perf.mjs does, then for some passes every call to the
// named routines timed (a breakpoint at the entry, another at the return
// address read off the stack). Prints each routine's calls: count, average,
// worst, and the worst call's frame header (height, width) if it was
// handed one in sp_frame.
//
//   node tools/callcost.mjs room row col passes routine...
import { startBeeb } from "./beeb.mjs";

const [room, row, col, passes, ...names] = process.argv.slice(2);
const b = await startBeeb({ disc: "build/test.ssd", symbols: "build/test.json", bootUntil: "game_loop" });
const cell = +row * 32 + +col;
await b.teleport(+room, cell);
for (let i = 0; i < 3; i++) await b.runUntil("game_loop", 20);
const entries = new Map(names.map((n) => [b.addr(n), n]));
const LOOP = b.addr("game_loop");
const stats = Object.fromEntries(names.map((n) => [n, { n: 0, sum: 0, worst: 0, frame: "" }]));
async function run() {
    for (;;) {
        const r = await b.cycles(4e6);
        if (r.registers) return r.registers;
    }
}
for (const a of [...entries.keys(), LOOP]) await b.breakpoint(a);
let done = 0;
while (done < +passes) {
    const r = await run();
    if (r.pc === LOOP) { done++; continue; }
    const name = entries.get(r.pc);
    if (!name) continue;
    const [lo, hi] = await b.read(0x101 + r.s, 2);
    const ret = ((hi << 8) | lo) + 1;
    const frame = await b.read(await b.peekw("sp_frame"), 2);
    const t0 = r.elapsed_cycles;
    // Run to the return, ignoring other stops (nested calls aren't timed).
    await b.breakpoint(ret);
    let r2;
    do r2 = await run(); while (!(r2.pc === ret && r2.s === r.s + 2));
    await b.clearBreakpoints();
    for (const a of [...entries.keys(), LOOP]) await b.breakpoint(a);
    const c = r2.elapsed_cycles - t0, st = stats[name];
    st.n++; st.sum += c;
    if (c > st.worst) { st.worst = c; st.frame = `${frame[0]}x${frame[1]}`; }
}
for (const [name, st] of Object.entries(stats))
    console.log(`${name.padEnd(14)} ${String(st.n).padStart(4)} calls  avg ${String(Math.round(st.sum / Math.max(st.n, 1))).padStart(6)}  worst ${String(st.worst).padStart(6)} (sp_frame ${st.frame})`);
await b.close(); process.exit(0);
