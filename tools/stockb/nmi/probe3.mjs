// User VIA T1 IRQs (free-running, 1025us) alongside the reads: how late the
// IRQ handler gets to read T1 with and without NMIs arriving.
import { boot, runQueue } from "./harness.mjs";
const D = new URL(".", import.meta.url).pathname;
const beeb = await boot({ model: "B-DFS1.2", disc: D + "nmit40.ssd", symbols: D + "nmit.json", t1: true });
const INIT = [{ cmd: 0x75, params: [0x0d, 0x0c, 0x0a, 0xf8] }, { cmd: 0x75, params: [0x10, 0xff, 0xff, 0] }, { cmd: 0x7a, params: [0x17, 0xc1] }, { cmd: 0x69, params: [1], variant: 0x80 }];
await runQueue(beeb, INIT);
for (const v of [1, 2]) {
    const q = [{ delay: 100 }];
    for (let k = 0; k < 3; k++) for (let s = 0; s < 10; s++) q.push({ cmd: 0x53, params: [1, s, 0x21], dest: 0x30 + s, variant: v });
    const r = await runQueue(beeb, q);
    const idle = r[0], reads = r.slice(2);   // (the first read may wait for a spin-up)
    const lat = (t) => 255 - t.t1min;
    const t1s = reads.reduce((a, t) => a + t.t1s, 0), vs = reads.reduce((a, t) => a + t.vsyncs, 0);
    const cyc = reads.reduce((a, t) => a + (t.toNmi ?? 0) + t.toEnd + t.toIssue, 0);
    console.log(`variant ${v}: idle 2s: ${idle.t1s} T1 IRQs, worst T1 low byte read ${lat(idle)}us after the reload; ` +
        `29 reads (${(cyc / 2000).toFixed(0)}ms): ${t1s} T1 IRQs (expect ${(cyc / 2050).toFixed(0)}), ${vs} VSyncs (expect ${(cyc / 40000).toFixed(1)}), worst ${Math.max(...reads.map(lat))}us; ` +
        `per read: ${reads.map(lat).join(" ")}`);
}
await beeb.close();
