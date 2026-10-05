// The pause a streamed room change would add, on the records' real layout
// (records.idx from records.py: sector-aligned, room order, from track 9 as
// if after MENU and CE2): a random walk between neighbouring rooms, each
// record read with OSWORD &7F in the game's interrupt set-up (one read per
// track it spans), after a dwell in the room. With the DFS's own 8271
// settings (the head unloads after 12 revolutions) and with the head kept
// loaded (Specify, unload count &F).
//   node <this>        (from the repository root, after mkdisc.py and records.py)
import { startBeeb } from "../beeb.mjs";
import { dirname, resolve } from "path";
import { readFileSync } from "fs";
import { fileURLToPath } from "url";

const here = dirname(fileURLToPath(import.meta.url));
const idx = readFileSync(resolve(here, "records.idx"));
const BASE = 90;
const beeb = await startBeeb({ model: "B-DFS1.2" });
const sid = beeb.session_id;
const J = async (name, args) => JSON.parse((await beeb.call(name, { session_id: sid, ...args })).content[0].text);
await beeb.call("boot_disc", { session_id: sid, image_path: resolve(here, "disc.ssd") });
await J("run_until_prompt", { timeout_secs: 20 });
const BASIC = `5 FOR I%=0 TO 2 STEP 2
10 P%=&3000
20 [OPT I%
30 SEI:LDA &FE4E:STA &2FF0:LDA #&7F:STA &FE4E:LDA #&82:STA &FE4E
40 LDA &204:STA &2FF1:LDA &205:STA &2FF2:LDA #irq MOD 256:STA &204:LDA #irq DIV 256:STA &205
50 CLI:LDA #&7F:LDX #0:LDY #&2F:JSR &FFF1
55 LDA &2F1A:BEQ done:LDA #&7F:LDX #&10:LDY #&2F:JSR &FFF1
60 .done NOP:SEI:LDA &2FF1:STA &204:LDA &2FF2:STA &205
70 LDA #&7F:STA &FE4E:LDA &2FF0:ORA #&80:STA &FE4E:CLI:RTS
80 .irq LDA &FE4D:AND #2:BEQ notv:STA &FE4D
90 .notv LDA &FC:RTI
100 ]
105 NEXT
110 PRINT ~done
`;
await beeb.call("load_basic", { session_id: sid, source: BASIC });
await beeb.call("type_input", { session_id: sid, text: "RUN" });
const out = await J("run_until_prompt", { timeout_secs: 5 });
const DONE = parseInt(out.screenText.trim().split("\n").filter((l) => /^[0-9A-F]+$/.test(l.trim())).pop(), 16);
const ready = await beeb.saveState("ready");

async function osword(block) {
    await beeb.write(0x2f00, block);
    await beeb.write(0x2f1a, [0]);
    await beeb.breakpoint(0x3000);
    let r = await J("type_input", { text: "CALL &3000" });
    if (r.completed !== false) r = await J("run_for_cycles", { cycles: 4e6 });
    await beeb.clearBreakpoints();
    await beeb.breakpoint(DONE);
    r = await J("run_for_cycles", { cycles: 20e6 });
    await beeb.clearBreakpoints();
    await J("run_until_prompt", { timeout_secs: 5 });
    return r.cycles_run / 2000;
}

// One room's record: one read per track it spans (both blocks in one call).
async function load(room) {
    const first = BASE + (idx[3 * (room - 1)] | (idx[3 * (room - 1) + 1] << 8)), n = idx[3 * (room - 1) + 2];
    const t = Math.floor(first / 10), s = first % 10, n1 = Math.min(n, 10 - s), n2 = n - n1;
    const b1 = [0, 0, 0x40, 0, 0, 3, 0x53, t, s, 0x20 | n1, 0xff, 0, 0, 0, 0, 0];
    const b2 = [0, 0, 0x48, 0, 0, 3, 0x53, t + 1, 0, 0x20 | n2, 0xff];
    const block = [...b1, ...b2];
    block[0x1a] = n2;                   // &2F1A: a second read wanted
    return osword(block.slice(0, 0x1b));
}

let seed = 12345;
const rand = () => (seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x80000000;
function walk(steps) {
    const rooms = [1];
    while (rooms.length < steps) {
        const r = rooms[rooms.length - 1];
        const ns = [r - 1, r + 1, r - 10, r + 10].filter((n) => n >= 1 && n <= 120);
        rooms.push(ns[Math.floor(rand() * ns.length)]);
    }
    return rooms;
}

const route = walk(21);
console.log(`route: ${route.join(" ")}`);
for (const kept of [false, true]) {
    for (const dwell of [1.5, 5]) {
        await beeb.restoreState(ready);
        if (kept) await osword([0, 0, 0x40, 0, 0, 4, 0x75, 0x0d, 0x0c, 0x0a, 0xf8, 0xff, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]);
        await load(route[0]);
        const ms = [];
        for (const room of route.slice(1)) {
            await beeb.run(dwell);
            ms.push(await load(room));
        }
        const sorted = [...ms].sort((a, b) => a - b);
        const mean = ms.reduce((a, b) => a + b) / ms.length;
        console.log(`${kept ? "head kept loaded" : "DFS default     "}, ${dwell}s in each room: mean ${mean.toFixed(0)}ms, ` +
            `median ${sorted[sorted.length >> 1].toFixed(0)}, min ${sorted[0].toFixed(0)}, max ${sorted[sorted.length - 1].toFixed(0)}`);
        console.log(`  ${ms.map((x) => x.toFixed(0)).join(" ")}`);
    }
}
await beeb.close();
