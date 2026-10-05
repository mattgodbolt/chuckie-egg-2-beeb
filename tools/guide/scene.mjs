// A scene in the game (build/test.ssd), screenshots at chosen passes.
//   node scene.mjs '<json>' outdir
// json: {start:[room,row,col,yf,xf,state,face], power, factory, carry,
//        pokes:{sym:[bytes]}, keys:"right:5-40,...", passes:N,
//        shots:{pass:name}, after:[[secs,name],...]}
// Mirrors tools/passlog.mjs's set-up, so the scene is one the scenarios
// could check against the original.
import { mkdirSync } from "fs";
import { startBeeb, KEYS } from "../beeb.mjs";

const spec = JSON.parse(process.argv[2]);
const out = process.argv[3];
mkdirSync(out, { recursive: true });
const inputs = (spec.keys ?? "").split(",").filter(Boolean).map((part) => {
    const [name, rng] = part.split(":");
    const [a, b] = rng.split("-").map(Number);
    return { key: name === "shift" ? "SHIFT" : KEYS[name], a, b: b ?? a };
});
const b = await startBeeb({ disc: "build/test.ssd", symbols: "build/test.json" });
const held = new Set();
try {
    await b.breakpoint("game_loop");
    if (spec.start) {
        await b.run(30);
        const [room, row, col, yf, xf, state, face] = spec.start;
        await b.teleport(room, row * 32 + col, yf, xf, state, face);
        if (spec.power) await b.write("factory", [(await b.peek("factory")) | 1]);
        if (spec.factory !== undefined) await b.write("factory", [spec.factory]);
        if (spec.carry !== undefined) {
            const carry = spec.carry;
            await b.write("carried", [carry]);
            await b.write(b.addr("t_room") + carry, [(await b.peek(b.addr("t_room") + carry)) | 0x80]);
            const type = await b.peek(b.addr("t_type") + carry);
            const [, gfx, kind] = await b.read(b.addr("thing_types") + 3 * type, 3);
            const frame = await b.read(b.addr("object_frames") + 2 * gfx, 2);
            await b.write("carried_h", [(await b.peek(frame[0] | (frame[1] << 8))) & 7]);
            await b.write("carrying_name", [(kind & 15) + 1]);
        }
        for (const [sym, bytes] of Object.entries(spec.pokes ?? {})) await b.write(sym, bytes);
        await b.breakpoint("game_loop");
    }
    const shots = spec.shots ?? {};
    for (let n = 0; n < (spec.passes ?? 0); n++) {
        const r = await b.run(n === 0 ? 30 : (spec.wait ?? 10));
        const hit = r.stopped_reason !== undefined || JSON.stringify(r).includes("breakpoint");
        if (!hit) {
            console.log("pass", n, "never reached game_loop");
            for (const key of held) await b.keyUp(key);
            held.clear();
            break;
        }
        for (const key of new Set(inputs.map((i) => i.key))) {
            const want = inputs.some((i) => i.key === key && i.a <= n && n <= i.b);
            if (want && !held.has(key)) { await b.keyDown(key); held.add(key); }
            if (!want && held.has(key)) { await b.keyUp(key); held.delete(key); }
        }
        if (shots[n]) {
            await b.shot(`${out}/${shots[n]}.png`);
            const v = await b.read("h_cell", 11);
            console.log("shot", shots[n], "pass", n, "room", await b.peek("room"), "cell", v[0] | (v[1] << 8),
                "row", (v[0] | (v[1] << 8)) >> 5, "col", v[0] & 31, "yf", v[2], "xf", v[3], "state", v[8],
                "factory", (await b.peek("factory")).toString(16), "lives", await b.peek("lives"),
                "carried", (await b.peek("carried")).toString(16));
        }
    }
    await b.clearBreakpoints();
    for (const [secs, name] of spec.after ?? []) {
        await b.run(secs);
        await b.shot(`${out}/${name}.png`);
        console.log("after", secs, name);
    }
} finally {
    await b.close();
}
process.exit(0);
