#!/usr/bin/env node
// The bytes the game sends the SN76489, captured by jsbeeb: the movement
// tick while Harry walks, and the life-lost tune when the dog gets him.
// Each must reach the chip as sound.6502 means it to: the tick as four
// writes (channel 1's tone, its high bits, on, off), the tune as channel 0
// loud, then death_notes' two bytes a note in order, then off. (Once the
// keyboard, left enabled, cleared bit 7 of every byte, and nothing noticed:
// docs/journal.md.) Exits non-zero on a failure.
//
//   node tools/soundcheck.mjs [--disc build/test.ssd] [--model B-DFS1.2]
import { startBeeb, KEYS } from "./beeb.mjs";

const args = process.argv.slice(2);
const opt = (name, def) => (args.indexOf(name) >= 0 ? args[args.indexOf(name) + 1] : def);
const b = await startBeeb({
    disc: opt("--disc", "build/test.ssd"), symbols: "build/test.json", bootUntil: "game_loop",
    model: opt("--model", undefined),
});

let failed = false;
const check = (ok, what) => {
    console.log(`${ok ? "ok  " : "FAIL"} ${what}`);
    if (!ok) failed = true;
};
const tool = async (name) => (await b.call(name, { session_id: b.session_id })).content[0].text;
// The bytes written between start and stop, in order.
const capture = async (during) => {
    await tool("start_sound_capture");
    await during();
    const log = await tool("stop_sound_capture");
    check(!log.startsWith("Showing last"), "... all the writes captured");
    return [...log.matchAll(/^\d+: 0x([0-9a-f]{2})/gm)].map((m) => parseInt(m[1], 16));
};
const hex = (bytes) => bytes.map((x) => x.toString(16).padStart(2, "0")).join(" ");

try {
    await b.run(3);                                   // the truck backs in
    const tick = await capture(async () => {
        await b.keyDown(KEYS.right);
        await b.run(1);
        await b.keyUp(KEYS.right);
        await b.run(0.1);
    });
    let groups = 0, bad = null;
    for (let i = 0; i + 4 <= tick.length; i += 4) {
        const [lo, hi, on, off] = tick.slice(i, i + 4);
        const n = (lo & 15) | (hi << 4);
        if ((lo & 0xf0) !== 0xa0 || hi > 0x3f || on !== 0xb2 || off !== 0xbf || n >= 80) {
            bad = bad ?? `at write ${i}: ${hex(tick.slice(i, i + 4))}`;
        }
        groups++;
    }
    check(groups >= 10 && tick.length % 4 === 0 && !bad,
        `walking: ${groups} ticks, each channel 1's tone, on, off${bad ? ` (${bad})` : ""}`);

    // Into the dog: the tune, from the moment he dies.
    await b.keyDown(KEYS.right);
    const r = await b.runUntil("harry_died", 30);
    check(r.stopped_reason === "breakpoint", "walking into the dog: a life lost");
    const notes = await b.read("death_notes", (await b.addr("death_notes_end")) - (await b.addr("death_notes")));
    const want = [0x90];
    for (let i = 0; i < notes.length; i += 3) want.push(notes[i], notes[i + 1]);
    want.push(0x9f);
    const tune = await capture(async () => {
        await b.run(3);
        await b.keyUp(KEYS.right);
    });
    check(JSON.stringify(tune.slice(0, want.length)) === JSON.stringify(want),
        `the life-lost tune: ${(want.length - 2) / 2} notes on channel 0, then off`
        + (JSON.stringify(tune.slice(0, want.length)) === JSON.stringify(want) ? "" : `\n     want ${hex(want)}\n     got  ${hex(tune)}`));
} finally {
    await b.close();
}
console.log(failed ? "sound: FAILED" : "sound: all checks pass");
process.exit(failed ? 1 : 0);
