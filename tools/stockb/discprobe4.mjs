// Does OSWORD &7F still work in the game's conditions? The game owns IRQ1V
// (its own handler, the System VIA's interrupts off but VSync), has tables
// over the OS vectors in page 2, its scratch over zero page &90-&FB, and
// (with LowState moved up) its state over &0D1B-&0DEF. Each case runs the
// read with the game-like interrupt set-up, from the same saved state.
//   node <this>        (from the repository root, after mkdisc.py)
import { startBeeb } from "../beeb.mjs";
import { dirname, resolve } from "path";
import { fileURLToPath } from "url";

const here = dirname(fileURLToPath(import.meta.url));
const beeb = await startBeeb({ model: "B-DFS1.2" });
const sid = beeb.session_id;
const J = async (name, args) => JSON.parse((await beeb.call(name, { session_id: sid, ...args })).content[0].text);
await beeb.call("boot_disc", { session_id: sid, image_path: resolve(here, "disc.ssd") });
await J("run_until_prompt", { timeout_secs: 20 });

// &3000: the game's interrupt set-up, the read, everything put back.
const BASIC = `5 FOR I%=0 TO 2 STEP 2
10 P%=&3000
20 [OPT I%
30 SEI:LDA &FE4E:STA &2FF0:LDA #&7F:STA &FE4E:LDA #&82:STA &FE4E
40 LDA &204:STA &2FF1:LDA &205:STA &2FF2:LDA #irq MOD 256:STA &204:LDA #irq DIV 256:STA &205
50 CLI:LDA #&7F:LDX #0:LDY #&2F:JSR &FFF1
60 .done NOP:SEI:LDA &2FF1:STA &204:LDA &2FF2:STA &205
70 LDA #&7F:STA &FE4E:LDA &2FF0:ORA #&80:STA &FE4E:CLI:RTS
80 .irq LDA &FE4D:AND #2:BEQ notv:STA &FE4D:INC &2FF3
90 .notv LDA &FC:RTI
100 ]
105 NEXT
110 PRINT ~done
`;
await beeb.call("load_basic", { session_id: sid, source: BASIC });
await beeb.call("type_input", { session_id: sid, text: "RUN" });
const out = await J("run_until_prompt", { timeout_secs: 5 });
const DONE = parseInt(out.screenText.trim().split("\n").filter((l) => /^[0-9A-F]+$/.test(l.trim())).pop(), 16);
console.log("DONE =", DONE.toString(16), JSON.stringify(out.screenText));
const base = await beeb.saveState("ready");

async function trial(label, fills, track = 20, sector = 3) {
    await beeb.restoreState(base);
    await beeb.write(0x2f00, [0, 0x00, 0x40, 0, 0, 3, 0x53, track, sector, 0x21, 0xff]);
    await beeb.write(0x2ff3, [0]);
    await beeb.write(0x4000, new Array(256).fill(0xaa));
    await beeb.breakpoint(0x3000);
    let r = await J("type_input", { text: "CALL &3000" });
    if (r.completed !== false) r = await J("run_for_cycles", { cycles: 4e6 });
    await beeb.clearBreakpoints();
    for (const [a, b] of fills) await beeb.write(a, new Array(b - a).fill(0xe5));
    await beeb.breakpoint(DONE);
    r = await J("run_for_cycles", { cycles: 20e6 });
    await beeb.clearBreakpoints();
    if (r.stopped_reason !== "breakpoint") {
        const regs = JSON.parse(await beeb.regs());
        const zp = await beeb.read(0x2ff0, 4);
        return console.log(`${label}: FAILED at pc ${regs.pcHex} (${JSON.stringify(r).slice(0, 200)}) vs ${zp}`);
    }
    const data = await beeb.read(0x4000, 2), res = await beeb.peek(0x2f0a), vs = await beeb.peek(0x2ff3);
    console.log(`${label}: ${(r.cycles_run / 2000).toFixed(0)}ms, result ${res}, data ${data}, ${vs} VSyncs taken by the game-like handler`);
}

const hex = (a) => "&" + a.toString(16).toUpperCase();
await trial("game's interrupts, nothing else", []);
for (const [a, b] of [[0x1081, 0x1090], [0x1090, 0x10a0], [0x10a0, 0x10b0], [0x10b0, 0x10c0], [0x10c0, 0x10d0]])
    await trial(`${hex(a)}-${hex(b - 1)} filled`, [[a, b]]);
await beeb.close();
