#!/usr/bin/env node
// Play the BBC port pass by pass and log Harry's state each pass: the
// counterpart of tools/passlog.py (same inputs, same output), compared by
// tools/passcmp.py.
//
//   node tools/passlog.mjs '<inputs>' passes [--out build/bbc_passes.json]
//
// Pass 0 is the first time game_loop is reached; keys are set at the top of
// a pass, before read_keys.
import { writeFileSync } from "fs";
import { startBeeb } from "./beeb.mjs";

const KEYS = { up: "Q", down: "A", left: "O", right: "P", jump: "SPACE", take: "K1" };
const args = process.argv.slice(2);
const outIdx = args.indexOf("--out");
const out = outIdx >= 0 ? args.splice(outIdx, 2)[1] : "build/bbc_passes.json";
const startIdx = args.indexOf("--start");
const start = startIdx >= 0 ? args.splice(startIdx, 2)[1].split(",").map(Number) : null;
const inputs = (args[0] ?? "").split(",").filter(Boolean).map((part) => {
    const [name, rng] = part.split(":");
    const [a, b] = rng.split("-").map(Number);
    return { key: KEYS[name], a, b: b ?? a };
});
const passes = parseInt(args[1] ?? "100");

const b = await startBeeb({ disc: "build/ce2.ssd" });
const held = new Set();
const log = [];
try {
    await b.breakpoint("game_loop");
    if (start) {
        // --start room,row,col,yf,xf,state,face: placed during the first
        // pass, put in the room at its end (teleport in game.6502).
        await b.run(10);
        const [room, row, col, yf, xf, state, face] = start;
        const cell = row * 32 + col;
        await b.write("dbg_start", [cell & 0xff, cell >> 8, yf, xf, state, face]);
        await b.write("dbg_room", [room]);
    }
    for (let n = 0; n < passes; n++) {
        const r = await b.run(10);
        if (r.stopped_reason === undefined && !String(JSON.stringify(r)).includes("breakpoint"))
            throw new Error(`pass ${n}: never reached game_loop: ${JSON.stringify(r)}`);
        for (const { key, a, b: last } of inputs) {
            const want = a <= n && n <= last;
            if (want && !held.has(key)) { await b.keyDown(key); held.add(key); }
            if (!want && held.has(key)) { await b.keyUp(key); held.delete(key); }
        }
        const v = await b.read("h_cell", 11);
        const count = await b.peek("m_count");
        const arr = async (sym) => b.read(sym, 5);
        const [clo, chi, yf, sub, dx, dy, tick, speed] = await Promise.all(
            ["m_cell_lo", "m_cell_hi", "m_yf", "m_sub", "m_dx", "m_dy", "m_tick", "m_speed"].map(arr));
        const monsters = [];
        for (let i = 0; i < count; i++)
            monsters.push([clo[i] | (chi[i] << 8), yf[i], sub[i], dx[i], dy[i], tick[i], speed[i]]);
        const rng = (await b.read("rng_state", 4)).map((x) => x.toString(16).padStart(2, "0")).join("");
        log.push({
            pass: n, room: await b.peek("room"), cell: v[0] | (v[1] << 8), yf: v[2], xf: v[3],
            state: v[8], face: v[6], cnt: v[9], fall: v[10], rng, monsters,
        });
    }
} finally {
    await b.close();
}
writeFileSync(out, log.map((e) => JSON.stringify(e)).join("\n") + "\n");
console.log(`${log.length} passes logged to ${out}`);
process.exit(0);
