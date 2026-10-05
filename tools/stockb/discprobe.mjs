// What keeping the DFS alive for streaming would cost, measured in jsbeeb on
// a Model B with DFS 1.2: which memory OSWORD &7F (raw 8271 sector reads)
// and OSFILE (a whole file by name) write, and how long reads take for
// different head movements, warm and cold.
//
//   node <this> [model]     (from the repository root, after mkdisc.py)
import { startBeeb } from "../beeb.mjs";
import { dirname, resolve } from "path";
import { fileURLToPath } from "url";

const here = dirname(fileURLToPath(import.meta.url));
const model = process.argv[2] || "B-DFS1.2";
const beeb = await startBeeb({ model });
const sid = beeb.session_id;
const J = async (name, args) => JSON.parse((await beeb.call(name, { session_id: sid, ...args })).content[0].text);

await beeb.call("boot_disc", { session_id: sid, image_path: resolve(here, "disc.ssd") });
await J("run_until_prompt", { timeout_secs: 20 });

// The routines: OSWORD &7F with the block at &2F00; OSFILE load with the
// block at &2F80. A NOP after each call for the breakpoint.
const BASIC = `10 P%=&3000
20 [OPT 0
30 LDA #&7F:LDX #0:LDY #&2F:JSR &FFF1
40 NOP:RTS
50 LDA #&FF:LDX #&80:LDY #&2F:JSR &FFDD
60 NOP:RTS
70 ]
80 $&2FA0="SMALL"
90 ?&2F80=&A0:?&2F81=&2F:!&2F82=&4000:?&2F86=0
`;
await beeb.call("load_basic", { session_id: sid, source: BASIC });
await beeb.call("type_input", { session_id: sid, text: "RUN" });
await J("run_until_prompt", { timeout_secs: 5 });
const GO = 0x3000, DONE = 0x3009, GO2 = 0x300B, DONE2 = 0x3014;

const range = (a, b) => Array.from({ length: b - a }, (_, i) => a + i);
const FILL = [[0x0900, 0x0d00], [0x0d00, 0x0d9f], [0x0e00, 0x1900]];
const WATCH = [[0x0000, 0x0100], [0x0100, 0x0200], [0x0200, 0x0400], [0x0800, 0x0900], ...FILL];

async function snapshot() {
    const out = {};
    for (const [a, b] of WATCH) out[a] = await beeb.read(a, b - a);
    return out;
}

function spans(addrs) {
    const out = [];
    for (const a of addrs) {
        if (out.length && out[out.length - 1][1] === a - 1) out[out.length - 1][1] = a;
        else out.push([a, a]);
    }
    return out.map(([a, b]) => (a === b ? `&${a.toString(16)}` : `&${a.toString(16)}-&${b.toString(16)}`)).join(" ");
}

// One call: OSWORD &7F read (track, sector, count) or OSFILE; optionally
// filling the FILL regions with a marker first. Returns cycles and writes.
async function call({ osfile = false, track = 0, sector = 0, count = 1, fill = false, wait = 0, regions = FILL }) {
    if (!osfile) await beeb.write(0x2f00, [0, 0x00, 0x40, 0, 0, 3, 0x53, track, sector, 0x20 | count, 0xff]);
    if (wait) await beeb.run(wait);
    const go = osfile ? GO2 : GO, done = osfile ? DONE2 : DONE;
    await beeb.breakpoint(go);
    let r = await J("type_input", { text: `CALL &${go.toString(16).toUpperCase()}` });
    if (r.completed !== false) r = await J("run_for_cycles", { cycles: 4e6 });
    else r.stopped_reason = "breakpoint";
    await beeb.clearBreakpoints();
    if (r.stopped_reason !== "breakpoint" && r.stopped_reason !== "pending_breakpoint") throw new Error("never reached go: " + JSON.stringify(r));
    const sp = JSON.parse(await beeb.regs()).s;
    if (fill) for (const [a, b] of regions) await beeb.write(a, new Array(b - a).fill(0xe5));
    await beeb.write(0x100, new Array(sp - 0x10 + 1).fill(0xe5).slice(0, sp + 1 - 0x10)); // page 1 below SP
    await beeb.write(0x4000, new Array(256 * count).fill(0xaa));
    const before = await snapshot();
    await beeb.breakpoint(done);
    r = await J("run_for_cycles", { cycles: 20e6 });
    await beeb.clearBreakpoints();
    if (r.stopped_reason !== "breakpoint") return { failed: true, screen: r.output.screenText.trim().split("\n").slice(-4).join(" | ") };
    const cycles = r.cycles_run;
    const after = await snapshot();
    const changed = [];
    for (const [a, b] of WATCH) for (const x of range(a, b)) if (before[a][x - a] !== after[a][x - a]) changed.push(x);
    const p1 = await beeb.read(0x100, 0x100);
    let low = 0x1ff;
    for (let i = 0x10; i < 0x100; i++) if (p1[i] !== 0xe5) { low = 0x100 + i; break; }
    const data = await beeb.read(0x4000, 2);
    const result = osfile ? null : (await beeb.read(0x2f0a, 1))[0];
    await J("run_until_prompt", { timeout_secs: 5 });
    return { cycles, ms: (cycles / 2000).toFixed(0), changed, sp: 0x100 + sp, low, data, result };
}

console.log(`model ${model}`);
// Footprints: each region filled alone, from the same saved state.
const base = await beeb.saveState("ready");
const show = (label, r) => {
    if (r.failed) return console.log(`${label}: FAILED (${r.screen})`);
    console.log(`${label}: ${r.ms}ms, result ${r.result}, data ${r.data}, stack from &${r.sp.toString(16)} down to &${r.low.toString(16)}`);
    console.log(`  wrote: ${spans(r.changed)}`);
};
show("OSWORD &7F t20 s3, no fill", await call({ track: 20, sector: 3 }));
for (const reg of [[0x0900, 0x0d00], [0x0d00, 0x0d9f], [0x0e00, 0x1000], [0x1000, 0x1100], [0x1100, 0x1900]]) {
    await beeb.restoreState(base);
    show(`OSWORD &7F t20 s3, &${reg[0].toString(16)}-&${(reg[1] - 1).toString(16)} filled`, await call({ track: 20, sector: 3, fill: true, regions: [reg] }));
}
for (let a = 0x1000; a < 0x1100; a += 16) {
    await beeb.restoreState(base);
    const r = await call({ track: 20, sector: 3, fill: true, regions: [[a, a + 16]] });
    if (r.failed) console.log(`  needs something in &${a.toString(16)}-&${(a + 15).toString(16)}`);
}
await beeb.restoreState(base);
show("OSFILE SMALL, no fill", await call({ osfile: true }));
for (const reg of [[0x0d00, 0x0d9f], [0x0e00, 0x1000], [0x1000, 0x1100], [0x1100, 0x1900]]) {
    await beeb.restoreState(base);
    show(`OSFILE SMALL, &${reg[0].toString(16)}-&${(reg[1] - 1).toString(16)} filled`, await call({ osfile: true, fill: true, regions: [reg] }));
}
await beeb.restoreState(base);
// Timing: a sequence of reads, each straight after the last (motor warm).
const seq = [[20, 0, 1], [20, 5, 1], [21, 0, 1], [22, 4, 1], [25, 0, 1], [30, 0, 1], [39, 0, 1], [0, 2, 1],
    [1, 0, 1], [1, 0, 2], [5, 0, 4], [10, 0, 10], [11, 0, 1], [10, 0, 1], [12, 3, 1], [12, 3, 1]];
for (const [track, sector, count] of seq) {
    const r = await call({ track, sector, count });
    console.log(`warm: track ${track} sector ${sector} x${count}: ${r.ms}ms (result ${r.result}, data ${r.data})`);
}
for (const wait of [1, 2, 3, 5]) {
    const r = await call({ track: 13, sector: 0, count: 1, wait });
    console.log(`after ${wait}s idle: track 13 x1: ${r.ms}ms`);
}
await beeb.close();
