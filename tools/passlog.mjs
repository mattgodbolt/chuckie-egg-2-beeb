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
        log.push({
            pass: n, room: await b.peek("room"), cell: v[0] | (v[1] << 8), yf: v[2], xf: v[3],
            state: v[8], face: v[6], cnt: v[9], fall: v[10],
        });
    }
} finally {
    await b.close();
}
writeFileSync(out, log.map((e) => JSON.stringify(e)).join("\n") + "\n");
console.log(`${log.length} passes logged to ${out}`);
process.exit(0);
