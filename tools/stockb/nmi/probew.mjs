// The WD1770 measurements on a Master 128. Times in ms.
import { boot, runQueue } from "./harness.mjs";
const D = new URL(".", import.meta.url).pathname;
const t1 = process.argv.includes("--t1");
const beeb = await boot({ model: "Master", disc: D + "nmiw40.ssd", symbols: D + "nmiw.json", t1 });
const ms = (c) => (c / 2000).toFixed(1);
const LOOP = 17;            // busy loop: INC zp 5, BNE 3, LDA abs 4, LSR 2, BCS 3
const RESTORE = (rate = 0, extra = {}) => ({ cmd: 0x04 | rate, ...extra });   // with verify (cmd 0 means none here)
const SEEK = (t, rate = 0, extra = {}) => ({ cmd: 0x10 | rate, n: 4, params: [0, 0, t], ...extra });
const READ = (s, page = 0x30, variant = 1, extra = {}) => ({ cmd: 0x80, n: 2, params: [0, s], dest: page, variant, ...extra });
const MULTI = (s, page = 0x30) => ({ cmd: 0x90, n: 2, params: [0, s], dest: page, variant: 3 });
const FORCE = { cmd: 0xd0 };

async function check(page, t, s, n = 1) {
    let ok = true;
    for (let k = 0; k < n; k++) {
        const b = await beeb.read((page + k) * 256, 256);
        ok &&= b.every((v, j) => v === (j & 1 ? s + k : t));
    }
    return ok;
}
function line(label, t, extra = "") {
    const total = (t.toNmi ?? 0) + t.toEnd;
    const lost = total ? (1 - (t.count * LOOP) / total) * 100 : 0;
    console.log(`${label.padEnd(40)} total ${ms(total).padStart(7)}ms` + (t.toNmi !== undefined ? `  first NMI ${ms(t.toNmi).padStart(6)}ms` : "") +
        `  status &${t.result.toString(16).padStart(2, "0")}  cpu lost ${lost.toFixed(1).padStart(5)}%  vsyncs ${t.vsyncs} (expect ${(total / 40000).toFixed(1)})` +
        (t1 ? `  T1 irqs ${t.t1s} max latency ${255 - t.t1min}us` : "") + extra);
}

console.log("== cold: motor off after reset");
let r = await runQueue(beeb, [RESTORE(0), SEEK(1), READ(5)]);
line("restore+verify (spin-up wait, 6ms steps)", r[0]);
line("seek 1", r[1]);
line("read 1/5", r[2], ` ok ${await check(0x30, 1, 5)}`);
const warm = await beeb.saveState("warm");

console.log("== warm, motor on, track 1: single sectors back to back");
for (const v of [1, 2]) {
    await beeb.restoreState(warm);
    r = await runQueue(beeb, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map((s, i) => READ(s, 0x30 + i, v)));
    for (let i = 0; i < 10; i++) line(`variant ${v}: read 1/${i}`, r[i], ` ok ${await check(0x30 + i, 1, i)}`);
}
console.log("== with the settle bit (E, &84)");
await beeb.restoreState(warm);
r = await runQueue(beeb, [READ(6, 0x30, 1), { ...READ(7, 0x31, 1), cmd: 0x84 }]);
line("read 1/6 (&80)", r[0]); line("read 1/7 (&84: 15ms settle)", r[1], ` ok ${await check(0x31, 1, 7)}`);

console.log("== rotational latency: read 1/3 after n vsyncs");
for (let d = 1; d <= 10; d++) {
    await beeb.restoreState(warm);
    r = await runQueue(beeb, [READ(3, 0x30, 1, { delay: d })]);
    line(`delay ${d}`, r[0]);
}
console.log("== seeks (motor on)");
for (const [rate, label] of [[0, "6ms"], [3, "30ms"]]) {
    for (const n of [1, 2, 5, 10, 20, 38]) {
        await beeb.restoreState(warm);
        r = await runQueue(beeb, [SEEK(1 + n, rate), READ(0, 0x30, 1), SEEK(1, rate)]);
        line(`${label}: seek 1->${1 + n}`, r[0]);
        line(`${label}: then read ${1 + n}/0`, r[1], ` ok ${await check(0x30, 1 + n, 0)}`);
    }
}
console.log("== multi-sector read (&90)");
for (const n of [0, 7]) {
    await beeb.restoreState(warm);
    r = await runQueue(beeb, [MULTI(n)]);
    line(`read 1/${n}.. to the end of the track`, r[0], ` ok ${await check(0x30, 1, n, 10 - n)}`);
}
console.log("== motor");
for (const [label, q] of [
    ["idle 1.5s, then read", [{ delay: 75 }, READ(0)]],
    ["idle 2.5s (motor off after 9 revs), read", [{ delay: 125 }, READ(0)]],
    ["idle 5s, read", [{ delay: 250 }, READ(0)]],
    ["idle 5s, read with h (&88, no spin-up wait)", [{ delay: 250 }, { ...READ(0), cmd: 0x88 }]],
    ["&D0 every 1.4s for 5.6s, read", [{ delay: 70 }, FORCE, { delay: 70 }, FORCE, { delay: 70 }, FORCE, { delay: 70 }, FORCE, READ(0)]],
    ["idle 5s, &D0, 1s, read", [{ delay: 250 }, FORCE, { delay: 50 }, READ(0)]],
]) {
    await beeb.restoreState(warm);
    try {
        r = await runQueue(beeb, q);
        line(label, r[r.length - 1], ` ok ${await check(0x30, 1, 0)}`);
    } catch (e) {
        console.log(`${label.padEnd(40)} failed: ${e.message.slice(0, 200)}`);
    }
}
await beeb.close();
