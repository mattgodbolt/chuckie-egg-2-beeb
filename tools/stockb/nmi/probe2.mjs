// The 8271 measurements. Times in ms (2000 cycles a ms).
import { boot, runQueue } from "./harness.mjs";
const D = new URL(".", import.meta.url).pathname;
const t1 = process.argv.includes("--t1");
const beeb = await boot({ model: "B-DFS1.2", disc: D + "nmit40.ssd", symbols: D + "nmit.json", t1 });
const ms = (c) => (c / 2000).toFixed(1);
const LOOP = 15;                                       // cycles per busy-loop pass
const SPEC = (step, settle, load) => ({ cmd: 0x75, params: [0x0d, step, settle, load] });
const INIT = [SPEC(0x0c, 0x0a, 0xf8), { cmd: 0x75, params: [0x10, 0xff, 0xff, 0] }, { cmd: 0x7a, params: [0x17, 0xc1] }];
const READ = (t, s, page = 0x30, variant = 1, extra = {}) => ({ cmd: 0x53, params: [t, s, 0x21], dest: page, variant, ...extra });
const SEEK = (t, extra = {}) => ({ cmd: 0x69, params: [t], ...extra });

async function check(page, t, s, n = 1) {
    let ok = true;
    for (let k = 0; k < n; k++) {
        const b = await beeb.read((page + k) * 256, 256);
        const ss = s + k;
        ok &&= b.every((v, j) => v === (j & 1 ? ss : t));
    }
    return ok;
}
function line(label, t, extra = "") {
    const total = (t.toNmi ?? 0) + t.toEnd;
    const lost = total ? (1 - (t.count * LOOP) / total) * 100 : 0;
    console.log(`${label.padEnd(38)} total ${ms(total).padStart(7)}ms` + (t.toNmi !== undefined ? `  first NMI ${ms(t.toNmi).padStart(6)}ms` : "") +
        `  result &${t.result.toString(16).padStart(2, "0")}  cpu lost ${lost.toFixed(1).padStart(5)}%  vsyncs ${t.vsyncs} (expect ${(total / 40000).toFixed(1)})` +
        (t1 ? `  T1 irqs ${t.t1s} max latency ${255 - t.t1min}us` : "") + extra);
}

// Cold start: the DFS left the drive; the 8271 reset deselects it.
console.log("== cold start (drive deselected after reset)");
let r = await runQueue(beeb, [...INIT, SEEK(0, { variant: 0x80 }), READ(1, 5, 0x30, 0x81)]);
line("seek 0, retrying until ready", r[3]);
line("read 1/5 (head loaded, track 0 -> 1)", r[4], ` ok ${await check(0x30, 1, 5)}`);
const warm = await beeb.saveState("warm");

console.log("== warm, head loaded, track 0: single sectors");
for (const v of [1, 2]) {
    await beeb.restoreState(warm);
    r = await runQueue(beeb, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map((s, i) => READ(1, s, 0x30 + i, v)));
    for (let i = 0; i < 10; i++) line(`variant ${v}: read 1/${i} straight after`, r[i], ` ok ${await check(0x30 + i, 1, i)}`);
}
console.log("== rotational latency: read 2/3 after a delay of n vsyncs (head loaded, on track 2)");
await beeb.restoreState(warm);
await runQueue(beeb, [SEEK(2)]);
const on2 = await beeb.saveState("on2");
for (let d = 1; d <= 10; d++) {
    await beeb.restoreState(on2);
    r = await runQueue(beeb, [READ(2, 3, 0x30, 1, { delay: d })]);
    line(`delay ${d} vsyncs`, r[0]);
}
console.log("== seeks (head loaded, step &0C = 24ms, settle &0A = 20ms)");
for (const [step, label] of [[0x0c, "step 24ms"], [0x03, "step 6ms"]]) {
    for (const n of [1, 2, 3, 5, 10, 20, 39]) {
        await beeb.restoreState(warm);
        r = await runQueue(beeb, [SPEC(step, 0x0a, 0xf8), SEEK(n), READ(n, 0, 0x30, 1), SEEK(0)]);
        line(`${label}: seek 1->${n}`, r[1]);
        line(`${label}: then read ${n}/0`, r[2], ` ok ${await check(0x30, n, 0)}`);
        line(`${label}: seek ${n}->0`, r[3]);
    }
}
console.log("== read with implied seek (Read Data on another track, no Seek first)");
for (const n of [1, 3, 10]) {
    await beeb.restoreState(warm);
    r = await runQueue(beeb, [READ(n, 4, 0x30, 1)]);
    line(`read ${n}/4 from track 1`, r[0], ` ok ${await check(0x30, n, 4)}`);
}
console.log("== multi-sector Read Data (variant 3)");
for (const n of [2, 4, 10]) {
    await beeb.restoreState(on2);
    r = await runQueue(beeb, [{ cmd: 0x53, params: [2, 0, 0x20 | n], dest: 0x30, variant: 3 }]);
    line(`read 2/0 x${n}`, r[0], ` ok ${await check(0x30, 2, 0, n)}`);
}
await beeb.restoreState(on2);
r = await runQueue(beeb, [{ cmd: 0x53, params: [2, 7, 0x20 | 3], dest: 0x30, variant: 3 }]);
line(`read 2/7 x3 (to the end of the track)`, r[0], ` ok ${await check(0x30, 2, 7, 3)}`);
await beeb.restoreState(on2);
r = await runQueue(beeb, [{ cmd: 0x53, params: [2, 8, 0x20 | 3], dest: 0x30, variant: 3 }]);
line(`read 2/8 x3 (past the end of the track)`, r[0]);

console.log("== head unload");
for (const [label, q] of [
    ["unload count 12 revs, wait 3s", [SPEC(0x0c, 0x0a, 0xc8), { delay: 150 }, READ(1, 0, 0x30, 0x81)]],
    ["unload count 12 revs, wait 1s", [SPEC(0x0c, 0x0a, 0xc8), { delay: 50 }, READ(1, 0, 0x30, 0x81)]],
    ["unload count 0 (now), wait 0.1s", [SPEC(0x0c, 0x0a, 0x08), { delay: 5 }, READ(1, 0, 0x30, 0x81)]],
    ["WSR &23 = 0 (deselect), wait 0.1s", [{ cmd: 0x7a, params: [0x23, 0] }, { delay: 5 }, READ(1, 0, 0x30, 0x81)]],
    ["WSR &23 = 0, wait 5s", [{ cmd: 0x7a, params: [0x23, 0] }, { delay: 250 }, READ(1, 0, 0x30, 0x81)]],
    ["WSR &23 = &48 (select+load), wait 1s", [{ cmd: 0x7a, params: [0x23, 0] }, { delay: 250 }, { cmd: 0x7a, params: [0x23, 0x48] }, { delay: 50 }, READ(1, 0, 0x30, 0x81)]],
    ["kept loaded (&F8), wait 5s", [{ delay: 250 }, READ(1, 0, 0x30, 0x81)]],
]) {
    await beeb.restoreState(warm);
    try {
        r = await runQueue(beeb, q);
        line(label, r[r.length - 1], ` ok ${await check(0x30, 1, 0)}`);
    } catch (e) {
        console.log(`${label.padEnd(38)} never completes: ${e.message.slice(0, 60)}`);
    }
}
await beeb.close();
