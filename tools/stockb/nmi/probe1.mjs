import { boot, runQueue } from "./harness.mjs";
const D = new URL(".", import.meta.url).pathname;
const beeb = await boot({ model: "B-DFS1.2", disc: D + "nmit40.ssd", symbols: D + "nmit.json" });
const SPEC = (load) => ({ cmd: 0x75, params: [0x0d, 0x0c, 0x0a, load] });
const q = [
    { delay: 50 },                                      // calibrate the delay loop
    SPEC(0xf8),
    { cmd: 0x75, params: [0x10, 0xff, 0xff, 0] },
    { cmd: 0x7a, params: [0x17, 0xc1] },
    { cmd: 0x69, params: [0], variant: 0x80 },                         // seek 0, cold
    { cmd: 0x53, params: [5, 0, 0x21], dest: 0x30, variant: 0x81 },   // cold-ish read
    { cmd: 0x53, params: [5, 1, 0x21], dest: 0x31, variant: 1 },
    { cmd: 0x53, params: [5, 2, 0x21], dest: 0x32, variant: 2 },
    { cmd: 0x53, params: [5, 3, 0x21], dest: 0x33, variant: 2 },
];
const res = await runQueue(beeb, q);
res.forEach((t, i) => console.log(i, JSON.stringify(q[i]), JSON.stringify(t)));
for (let p = 0x30; p < 0x34; p++) {
    const b = await beeb.read(p * 256, 256);
    console.log(p.toString(16), b.slice(0, 4), b.slice(252), b.every((v, j) => v === b[j & 1]));
}
await beeb.close();
