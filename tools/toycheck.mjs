#!/usr/bin/env node
// Each egg's toy as drawn (decision 45: only toy_load knows which egg's
// toy is in): for eggs past the first, the toy's parts, the toy and the
// toy maker's lights on the screen, pixel for pixel against the
// original's pictures for that egg (tools/toylog.py, from the tape's
// tables). Every egg's toy shows once over eggs 2-5, and egg 5's is egg
// 1's again. Exits non-zero on a difference.
//
//   node tools/toycheck.mjs
//
// The toy (&27) and the lights (&29-&30) start each egg out of the world:
// they are put in, as a part delivered and the toy made would. Each room
// is looked at twice: with all of them out of the world, then in, once
// the round robin has chosen (and drawn) each of them, counted in passes
// of the main loop, not time, as CE2S may wait for the room's read. Each
// picture's pixels must be lit just where the first look's are or the
// picture is. Harry stands clear of them, and the monsters are off
// (mon_limit 1: none of these rooms has entry 1), as a later egg's could
// cross a thing or kill him. Part 4 is left out: room 92's machine
// repaints its cells. The lights show every part's picture, part 4's too.
import { execFileSync } from "child_process";
import { startBeeb } from "./beeb.mjs";

const EGGS = [2, 3, 4, 5];
const HARRY = 5 * 32 + 16;          // row 5, column 16: clear of them all
const PASSES = 12;                  // passes in the room before looking, at least

const zx = JSON.parse(execFileSync(".venv/bin/python", ["tools/toylog.py", ...EGGS.map(String)], { encoding: "utf8" }))
    .map((things) => things.filter((t) => t.thing !== 4));

// Pixel (x, y) lit: MODE 1, a pixel's high bit in a byte's top nibble, its
// low bit in the bottom one.
const lit = (screen, x, y) => (screen[(y >> 3) * 0x200 + (x >> 2) * 8 + (y & 7)] & (0x88 >> (x & 3))) !== 0;

let failed = false;
for (const [i, egg] of EGGS.entries()) {
    const b = await startBeeb({ disc: "build/test.ssd", symbols: "build/test.json", bootUntil: "next_egg" });
    try {
        await b.write("egg", [egg - 1]);            // (next_egg adds the 1)
        await b.runUntil("game_loop");
        await b.write("mon_limit", [1]);
        const t_room = b.addr("t_room");
        const parts = [...Array(8).keys(), 0x27];
        // All of them in the world (bit 7 of a room clear; the lights'
        // bits in t_out's first byte) or out.
        const world = async (on) => {
            for (const x of parts) await b.write(t_room + x, [((await b.peek(t_room + x)) & 0x7f) | (on ? 0 : 0x80)]);
            await b.write("t_out", [on ? 0 : 0xff]);
        };
        // The room's screen after PASSES passes, and with the things in,
        // a pass after the last of them was chosen; null if Harry died.
        const look = async (room, on) => {
            await world(on);
            const lives = await b.peek("lives");
            await b.teleport(room, HARRY);
            const left = new Set(on ? zx[i].filter((t) => t.room === room).map((t) => t.thing) : []);
            // (next_object runs twice a pass: o_index, as it starts, is the
            // last one's choice.)
            for (let n = 0; n < 2 * PASSES || left.size; n++) {
                if (n > 100 * PASSES) throw new Error(`room ${room}: things never chosen: ${[...left]}`);
                await b.runUntil("next_object");
                left.delete(await b.peek("o_index"));
            }
            await b.runUntil("game_loop");
            const alive = (await b.peek("lives")) === lives && (await b.peek("room")) === room;
            return alive ? b.read(0x5000, 0x3000) : null;
        };
        const rooms = [...new Set(zx[i].map((t) => t.room))];
        for (const room of rooms) {
            const without = await look(room, false);
            const screen = await look(room, true);
            if (!without || !screen) {
                console.log(`egg ${egg} room ${room}: Harry DIED`);
                failed = true;
                continue;
            }
            // Every pixel of every footprint: lit where a picture is.
            const want = new Map();
            for (const t of zx[i].filter((t) => t.room === room))
                t.rows.forEach((bits, line) => [...bits].forEach((bit, k) => {
                    const key = `${t.col * 8 + k},${t.row * 8 + line}`;
                    want.set(key, (want.get(key) ?? false) || bit === "1");
                }));
            let wrong = 0;
            for (const [key, on] of want) {
                const [x, y] = key.split(",").map(Number);
                if (lit(screen, x, y) !== (on || lit(without, x, y))) wrong++;
            }
            const things = zx[i].filter((t) => t.room === room).map((t) => t.thing.toString(16)).join(" ");
            console.log(`egg ${egg} room ${room} (things ${things}): ${wrong ? `${wrong} pixels DIFFER` : "same"}`);
            failed ||= wrong > 0;
        }
    } finally {
        await b.close();
    }
}
console.log(failed ? "toy: FAILED" : "toy: every egg's as the original's");
process.exit(failed ? 1 : 0);
