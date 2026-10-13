#!/usr/bin/env node
// The in-game music (src/music.6502, decision 46) against its data: play
// a stretch of a game on the sideways RAM edition, counting frames, and
// check that the player is where src/data/music.bin says it should be
// after that many frames, and that the tune's and the bass's notes reached
// the sound chip in its order (channel 1's are left out: the movement tick
// borrows it), a voice in MU_BLIPS an octave up for a note's first frame
// and then at its pitch. Then M: the music off (silent, and it stays where it was)
// and on again. Then the life-lost tune, with the music on: the music
// plays it (music + MU_DEATH, harmonised), its last chord ringing on
// after the game's frozen time, and then after MU_GAP frames' silence
// carries on from where it was, even in the middle of a repeat.
//
//   node tools/musiccheck.mjs [seconds]
//
// Exits non-zero on a difference. The streaming edition has no music.
import { readFileSync } from "fs";
import { startBeeb, edition } from "./beeb.mjs";

const SECS = +process.argv[2] || 30;
if (edition("build/test.json") !== "build/test.json") {
    console.log("musiccheck: the streaming edition has no music");
    process.exit(0);
}
const data = readFileSync("src/data/music.bin");
let mudeath;

// The player's position, from the machine.
async function state(b) {
    const [ptrLo, ptrHi, retLo, retHi, left, wait] = await b.read("mu_ptr", 6);
    const owed = await b.peek("mu_owed"), blip = await b.peek("mu_blip");
    const note = [...(await b.read("mu_note", 3))];
    return { ptr: ptrLo | (ptrHi << 8), ret: retLo | (retHi << 8), left, wait, owed, blip, note };
}

// music_tick's events, frames times, as data says; the dividers written go
// to `out` ([channel, divider]), from `divider(entry, half)`.
function play(s, frames, base, out, divider, blips) {
    s = { ...s, note: [...s.note] };
    const byte = () => {
        const v = data[s.ptr - base];
        s.ptr++;
        if (s.left && !--s.left) s.ptr = s.ret;
        return v;
    };
    for (let f = 0; f < frames; f++) {
        for (let ch = 2; ch >= 0; ch--) {
            if (s.blip & (1 << ch)) out.push(divider(s.note[ch], false));
        }
        s.blip = 0;
        if (s.wait) { s.wait--; continue; }
        for (;;) {
            const v = byte();
            if (v < 0xc0) {
                const [ch] = divider(v, false);
                s.note[ch] = v;
                const half = (blips >> ch) & 1;
                out.push(divider(v, half));
                if (half) s.blip |= 1 << ch;
            }
            else if (v < 0xfe) { s.wait = v - 0xc0; break; }
            else if (v === 0xfe) {
                const at = byte() | (byte() << 8);
                s.left = byte();
                s.ret = s.ptr;
                s.ptr = base + at;
            } else if (s.ptr > base + mudeath) { s.resumed = true; break; }   // the tune's end
            else { s.ptr = base; s.left = 0; }
        }
    }
    return s;
}

const b = await startBeeb({ disc: "build/test.ssd", symbols: "build/test.json", bootUntil: "game_loop" });
let failed = false;
const fail = (msg) => { console.log(`DIFFERS: ${msg}`); failed = true; };
try {
    const base = b.addr("music");
    mudeath = b.addr("MU_DEATH");
    const latch = await b.read("music_latch", b.addr("music_data") - b.addr("music_latch"));
    const dataTab = await b.read("music_data", latch.length);

    // A stretch, frames counted from vsyncs (a byte: read it often).
    await b.call("start_sound_capture", { session_id: b.session_id });
    const s0 = await state(b);
    let v = await b.peek("vsyncs"), frames = 0;
    for (let t = 0; t < SECS * 4; t++) {
        await b.run(0.25);
        const v1 = await b.peek("vsyncs");
        frames += (v1 - v + 256) & 255;
        v = v1;
    }
    const s1 = await state(b);
    const log = (await b.call("stop_sound_capture", { session_id: b.session_id, max_entries: 1e6 })).content[0].text;
    if ((await b.peek("mu_on")) !== 0x80) fail("mu_on isn't on");

    // Where it should be: the frames less those still owed, from where it was.
    // A divider is the latch byte's low four bits and the data byte's six.
    const divider = (n, half) => {
        const d = ((dataTab[n] & 0x3f) << 4) | (latch[n] & 15);
        return [(latch[n] >> 5) & 3, half ? d >> 1 : d];
    };
    const notes = [];
    const want = play(s0, frames + s0.owed - s1.owed, base, notes, divider, b.addr("MU_BLIPS"));
    for (const k of ["ptr", "left", "wait", "blip"])
        if (want[k] !== s1[k]) fail(`after ${frames} frames ${k} is ${s1[k]}, the data says ${want[k]}`);

    // The chip's writes: channel 0's and channel 2's dividers, in order.
    const writes = [...log.matchAll(/: 0x([0-9a-f]{2}) /g)].map((m) => parseInt(m[1], 16));
    const seen = { 0: [], 2: [] };
    for (let i = 0; i < writes.length; i++) {
        const w = writes[i];
        const ch = (w >> 5) & 3;
        if (w & 0x80 && !(w & 0x10) && ch !== 1 && ch !== 3) seen[ch].push(((writes[i + 1] & 0x3f) << 4) | (w & 15));
    }
    // (Channel 2's at N = 833 are the train's noise set-up: not in room 1.)
    const expect = { 0: [], 2: [] };
    for (const [ch, d] of notes) if (ch !== 1) expect[ch].push(d);
    for (const ch of [0, 2]) {
        // The capture starts mid-frame: allow the first frame's notes either way.
        const a = seen[ch].join(","), e = expect[ch].join(",");
        if (!(a.endsWith(e) || e.endsWith(a)) || Math.abs(seen[ch].length - expect[ch].length) > 3)
            fail(`channel ${ch}: ${seen[ch].length} dividers written, the data has ${expect[ch].length}\n  seen ${a.slice(0, 120)}\n  want ${e.slice(0, 120)}`);
    }
    console.log(`music: ${frames} frames, ${notes.length} dividers (channel 0 ${seen[0].length}, bass ${seen[2].length})${failed ? "" : " as the data says"}`);

    // M off: silent, the position kept; M on again: it carries on.
    await b.keyDown("M");
    await b.run(0.2);
    await b.keyUp("M");
    await b.run(0.5);
    const off = await state(b);
    const sc = (await b.call("read_sound_state", { session_id: b.session_id })).content[0].text;
    if ((await b.peek("mu_on")) !== 0) fail("M didn't switch it off");
    // (Attenuations: 15 is silent.)
    for (const ch of ["CH0", "CH1", "CH2", "CH3"])
        if (!new RegExp(`${ch}:.*vol=15\\b`).test(sc)) fail(`${ch} isn't silent with the music off: ${sc}`);
    await b.run(1);
    const still = await state(b);
    if (still.ptr !== off.ptr || still.wait !== off.wait) fail("it moved on while off");
    await b.keyDown("M");
    await b.run(0.2);
    await b.keyUp("M");
    await b.run(1);
    if ((await b.peek("mu_on")) !== 0x80) fail("M didn't switch it on again");
    const on = await state(b);
    if (on.ptr === off.ptr && on.wait === off.wait) fail("it didn't carry on");
    console.log(`M: off and on again${failed ? "" : ", as it should"}`);

    // Into the dog, the music on: the life-lost tune is the music's.
    const was = failed;
    await b.keyDown("X");
    let r = await b.runUntil("music_death", 30);
    await b.keyUp("X");
    if (r.stopped_reason !== "breakpoint") fail("walking into the dog: no life lost");
    // As if in the middle of the music's first repeat, a byte into it: the
    // place put back must keep the repeat's count.
    const fe = data.indexOf(0xfe);
    const at = data[fe + 1] | (data[fe + 2] << 8), len = data[fe + 3], ret = base + fe + 4;
    await b.write("mu_ptr", [(base + at + 1) & 255, (base + at + 1) >> 8, ret & 255, ret >> 8, len - 1, 0]);
    const before = await state(b);
    await b.call("start_sound_capture", { session_id: b.session_id });
    const v0 = await b.peek("vsyncs");
    r = await b.runUntil("music_resume", 10);
    if (r.stopped_reason !== "breakpoint") fail("the life-lost tune didn't end");
    const dframes = ((await b.peek("vsyncs")) - v0 + 256) & 255;
    const dlog = (await b.call("stop_sound_capture", { session_id: b.session_id, max_entries: 1e6 })).content[0].text;
    const dwrites = [...dlog.matchAll(/: 0x([0-9a-f]{2}) /g)].map((m) => parseInt(m[1], 16));
    const dseen = { 0: [], 2: [] };
    for (let i = 0; i < dwrites.length; i++) {
        const w = dwrites[i], ch = (w >> 5) & 3;
        if (w & 0x80 && !(w & 0x10) && (ch === 0 || ch === 2)) dseen[ch].push(((dwrites[i + 1] & 0x3f) << 4) | (w & 15));
    }
    const dnotes = [];
    const silent = { ptr: base + mudeath, ret: 0, left: 0, wait: 0, blip: 0, note: [255, 255, 255] };
    // (music_resume is in the last frame's tick: vsyncs counted it.)
    const ended = play(silent, dframes, base, dnotes, divider, b.addr("MU_BLIPS"));
    if (!ended.resumed) fail(`the life-lost tune ended at frame ${dframes}, its data runs on`);
    for (const ch of [0, 2]) {
        const a = dseen[ch].join(","), e = dnotes.filter(([c]) => c === ch).map(([, d]) => d).join(",");
        if (a !== e) fail(`life-lost tune, channel ${ch}:\n  seen ${a}\n  want ${e}`);
    }
    // Then the music from where it was (its repeat's count too), after a gap.
    await b.runUntil("music_tick", 1);
    const after = await state(b);
    const gap = b.addr("MU_GAP");
    if (after.ptr !== before.ptr || after.ret !== before.ret || after.left !== before.left
        || after.wait !== before.wait + gap - 1)
        fail(`after the life-lost tune the music isn't where it was, MU_GAP on: ${JSON.stringify(before)} then ${JSON.stringify(after)}`);
    console.log(`life-lost tune: ${dframes} frames, ${dnotes.length} dividers${failed === was ? ", the music's, then the music again" : ""}`);
} finally {
    await b.close();
}
process.exit(failed ? 1 : 0);
