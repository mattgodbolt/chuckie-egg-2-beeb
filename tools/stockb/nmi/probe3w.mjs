// probe3 on the Master's 1770.
import { boot, runQueue } from "./harness.mjs";
const D = new URL(".", import.meta.url).pathname;
const beeb = await boot({ model: "Master", disc: D + "nmiw40.ssd", symbols: D + "nmiw.json", t1: true });
await runQueue(beeb, [{ cmd: 0x04 }, { cmd: 0x10, n: 4, params: [0, 0, 1] }]);
for (const v of [1, 2]) {
    const q = [{ delay: 100 }];
    for (let k = 0; k < 3; k++) for (let s = 0; s < 10; s++) q.push({ cmd: 0x80, n: 2, params: [0, s], dest: 0x30 + s, variant: v });
    const r = await runQueue(beeb, q);
    const idle = r[0], reads = r.slice(2);   // (the first read may wait for a spin-up)
    const lat = (t) => 255 - t.t1min;
    const t1s = reads.reduce((a, t) => a + t.t1s, 0), vs = reads.reduce((a, t) => a + t.vsyncs, 0);
    const cyc = reads.reduce((a, t) => a + (t.toNmi ?? 0) + t.toEnd + t.toIssue, 0);
    if (process.env.V) for (const t of reads) console.log(JSON.stringify(t));
    console.log(`variant ${v}: idle: worst ${lat(idle)}us; 29 reads (${(cyc / 2000).toFixed(0)}ms): ${t1s} T1 IRQs (expect ${(cyc / 2050).toFixed(0)}), ` +
        `${vs} VSyncs (expect ${(cyc / 40000).toFixed(1)}), worst ${Math.max(...reads.map(lat))}us; results ${[...new Set(reads.map((t) => t.result))]}`);
}
await beeb.close();
