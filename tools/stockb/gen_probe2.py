#!/usr/bin/env python3
"""Make discprobe2.mjs from discprobe.mjs's set-up: the DFS's bytes in page
&10 one at a time, the 8271's parameters, and reads with the head kept
loaded (the motor spinning)."""
import os

here = os.path.dirname(os.path.abspath(__file__))
s = open(os.path.join(here, "discprobe.mjs")).read()
head = s[:s.index("console.log(`model ${model}`);")]
head = head.replace(
    """async function call({ osfile = false, track = 0, sector = 0, count = 1, fill = false, wait = 0, regions = FILL }) {
    if (!osfile) await beeb.write(0x2f00, [0, 0x00, 0x40, 0, 0, 3, 0x53, track, sector, 0x20 | count, 0xff]);""",
    """async function call({ osfile = false, track = 0, sector = 0, count = 1, fill = false, wait = 0, regions = FILL, block = null }) {
    if (block) await beeb.write(0x2f00, block);
    else if (!osfile) await beeb.write(0x2f00, [0, 0x00, 0x40, 0, 0, 3, 0x53, track, sector, 0x20 | count, 0xff]);""")
head = head.replace(
    """    const result = osfile ? null : (await beeb.read(0x2f0a, 1))[0];""",
    """    const result = osfile ? null : (await beeb.read(block ? 0x2f00 + 7 + block[5] : 0x2f0a, 1))[0];""")
assert "block = null" in head and "block[5]" in head
tail = r'''console.log(`model ${model}`);
const base = await beeb.saveState("ready");
for (let a = 0x10d0; a < 0x10e0; a++) {
    await beeb.restoreState(base);
    const r = await call({ track: 20, sector: 3, fill: true, regions: [[a, a + 1]] });
    if (r.failed) console.log(`  OSWORD &7F needs &${a.toString(16)}`);
}
await beeb.restoreState(base);
// The 8271's special registers the DFS's Specify set: step rate, settle, head load/unload.
const reg = async (n) => (await call({ block: [0, 0, 0x40, 0, 0, 1, 0x7d, n, 0xff] })).result;
const step = await reg(0x0d), settle = await reg(0x0e), load = await reg(0x0f);
console.log(`DFS's 8271 parameters: step &${step.toString(16)}, settle &${settle.toString(16)}, load/unload &${load.toString(16)}`);
const timed = async (label, args) => { const r = await call(args); console.log(`${label}: ${r.ms}ms (result ${r.result}, data ${r.data})`); return r; };
await timed("warm-up read t13", { track: 13, sector: 0 });
await timed("after 5s idle, t13", { track: 13, sector: 0, wait: 5 });
// Never unload the head (count &F): the drive keeps spinning.
await call({ block: [0, 0, 0x40, 0, 0, 4, 0x75, 0x0d, step, settle, 0xf0 | (load & 15), 0xff] });
await timed("head kept loaded: read t13", { track: 13, sector: 0 });
for (const w of [2, 5]) await timed(`head kept loaded, after ${w}s idle, t13 s5`, { track: 13, sector: 5, wait: w });
await timed("head kept loaded, t14 s0", { track: 14, sector: 0, wait: 3 });
await timed("head kept loaded, t16 s0", { track: 16, sector: 0, wait: 3 });
await timed("head kept loaded, t13 x4", { track: 13, sector: 0, count: 4, wait: 3 });
// And a faster step rate as well (half the DFS's).
await call({ block: [0, 0, 0x40, 0, 0, 4, 0x75, 0x0d, Math.max(1, step >> 1), settle, 0xf0 | (load & 15), 0xff] });
await timed("faster step, t30 s0", { track: 30, sector: 0, wait: 3 });
await timed("faster step, t13 s0", { track: 13, sector: 0, wait: 3 });
// Rotational latency spread: the same track, sectors 0-9, after varied waits.
const ms = [];
for (let s = 0; s < 10; s++) ms.push((await call({ track: 13, sector: s, wait: 0.37 * (s + 1) })).ms);
console.log(`head kept loaded, same track, sectors 0-9 after varied waits: ${ms.join(" ")}ms`);
await beeb.close();
'''
open(os.path.join(here, "discprobe2.mjs"), "w").write(head + tail)
