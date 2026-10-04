#!/usr/bin/env node
// Play the BBC port pass by pass and log Harry's state each pass: the
// counterpart of tools/passlog.py (same inputs, same output), compared by
// tools/passcmp.py.
//
//   node tools/passlog.mjs '<inputs>' passes [--out build/bbc_passes.json]
//       [--start room,row,col,yf,xf,state,face] [--power] [--factory n] [--carry n]
//       [--peek sym:len,...]
//
// Pass 0 is the first time game_loop is reached; keys are set at the top of
// a pass, before read_keys.
import { writeFileSync } from "fs";
import { startBeeb, KEYS } from "./beeb.mjs";


const args = process.argv.slice(2);
const outIdx = args.indexOf("--out");
const out = outIdx >= 0 ? args.splice(outIdx, 2)[1] : "build/bbc_passes.json";
// --peek sym:len,...: extra memory to log each pass (for debugging; not compared).
// --cheat n: the developers' cheat byte (decision 27), set before the first pass;
// the key role "shift" is SHIFT (CAPS SHIFT on the Spectrum).
const peekIdx = args.indexOf("--peek");
const peeks = peekIdx >= 0 ? args.splice(peekIdx, 2)[1].split(",").map((p) => p.split(":")) : [];
const startIdx = args.indexOf("--start");
const start = startIdx >= 0 ? args.splice(startIdx, 2)[1].split(",").map(Number) : null;
const powerIdx = args.indexOf("--power");
const power = powerIdx >= 0 && args.splice(powerIdx, 1).length > 0;
const option = (name) => { const i = args.indexOf(name); return i >= 0 ? Number(args.splice(i, 2)[1]) : null; };
const factory = option("--factory");
const carry = option("--carry");
const cheat = option("--cheat");
const inputs = (args[0] ?? "").split(",").filter(Boolean).map((part) => {
    const [name, rng] = part.split(":");
    const [a, b] = rng.split("-").map(Number);
    return { key: name === "shift" ? "SHIFT" : KEYS[name], a, b: b ?? a };
});
const passes = parseInt(args[1] ?? "100");

// The tests' disc (make build/test.ssd): straight into a game, no front end.
const b = await startBeeb({ disc: "build/test.ssd", symbols: "build/test.json" });
const held = new Set();
const log = [];
try {
    await b.breakpoint("game_loop");
    if (start) {
        // --start room,row,col,yf,xf,state,face: put in the room at the end
        // of the first pass (beeb.mjs's teleport).
        await b.run(30);
        const [room, row, col, yf, xf, state, face] = start;
        await b.teleport(room, row * 32 + col, yf, xf, state, face);
        // As the original's logger does, at the teleport itself: on at the
        // top of this pass, room 1's machines would move the train.
        if (power) await b.write("factory", [(await b.peek("factory")) | 1]);
        if (factory !== null) await b.write("factory", [factory]);
        if (carry !== null) {
            // Carried, as touch_thing's take leaves it: out of the world,
            // its height (its type's frame) for the drop, its name shown.
            await b.write("carried", [carry]);
            await b.write(b.addr("t_room") + carry, [(await b.peek(b.addr("t_room") + carry)) | 0x80]);
            const type = await b.peek(b.addr("t_type") + carry);
            const [, gfx, kind] = await b.read(b.addr("thing_types") + 3 * type, 3);
            const frame = await b.read(b.addr("object_frames") + 2 * gfx, 2);
            await b.write("carried_h", [(await b.peek(frame[0] | (frame[1] << 8))) & 7]);   // (sprite.6502's header)
            await b.write("carrying_name", [(kind & 15) + 1]);
        }
        await b.breakpoint("game_loop");    // (runUntil cleared it)
    }
    // The developers' cheat byte, before the first pass reads the keys.
    let cheatSet = cheat === null;
    for (let n = 0; n < passes; n++) {
        const r = await b.run(n === 0 ? 30 : 10);
        if (r.stopped_reason === undefined && !String(JSON.stringify(r)).includes("breakpoint"))
            throw new Error(`pass ${n}: never reached game_loop: ${JSON.stringify(r)}`);
        if (!cheatSet) {
            await b.write("cheat", [cheat]);
            cheatSet = true;
        }
        // A key is down if any of its ranges holds this pass.
        for (const key of new Set(inputs.map((i) => i.key))) {
            const want = inputs.some((i) => i.key === key && i.a <= n && n <= i.b);
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
        const score = (await b.read("score", 10)).join("");
        log.push({
            pass: n, room: await b.peek("room"), cell: v[0] | (v[1] << 8), yf: v[2], xf: v[3],
            state: v[8], face: v[6], cnt: v[9], fall: v[10], rng, monsters,
            score, lives: await b.peek("lives"), carried: await b.peek("carried"),
            factory: await b.peek("factory"), rr: await b.peek("o_index"),
            sel: (await b.peek("o_sel")) ? 1 : 0, falling: await b.peek("f_thing"),
            train: [await b.peek("train_room"), await b.peek("train_pos")],
            things: (await b.read("t_room", 0x29)).map((x) => x.toString(16).padStart(2, "0")).join(""),
        });
        if (peeks.length) {
            const extra = {};
            for (const [sym, len] of peeks) extra[sym] = await b.read(sym, Number(len ?? 1));
            log[log.length - 1].peek = extra;
        }
    }
} finally {
    await b.close();
}
writeFileSync(out, log.map((e) => JSON.stringify(e)).join("\n") + "\n");
console.log(`${log.length} passes logged to ${out}`);
process.exit(0);
