// driver.6502 on both machines, from the same disc image.
import { startBeeb } from "../../beeb.mjs";
const D = new URL(".", import.meta.url).pathname;
const reqs = [
    ["read", 1, 0, 0x30], ["read", 1, 1, 0x31], ["read", 1, 2, 0x32], ["read", 1, 3, 0x33],
    ["read", 5, 7, 0x34], ["read", 3, 2, 0x35], ["read", 20, 9, 0x36],
    ["pause", 0xff, 150, 1], ["read", 20, 0, 0x37],
    ["pause", 0xff, 150, 0], ["read", 21, 0, 0x38],
    ["pause", 0xff, 150, 0], ["spin", 0xfe, 0, 0], ["pause", 0xff, 50, 0], ["read", 22, 5, 0x39],
];
const label = (r) => r[0] === "read" ? `read ${r[1]}/${r[2]}` : r[0] === "spin" ? "fdc_spinup" : `pause ${r[2]} VSyncs${r[3] ? " with keepalive" : ""}`;
for (const model of process.argv.slice(2).length ? process.argv.slice(2) : ["B-DFS1.2", "Master"]) {
    const beeb = await startBeeb({ model, symbols: D + "dtest.json" });
    const S = beeb.syms;
    await beeb.boot(D + "dtest40.ssd");
    await beeb.runUntil(S.init_done, 30);
    const type = await beeb.peek(0x60);
    console.log(`== ${model}: fdc_type ${type} (${type ? "WD1770" : "8271"})`);
    await beeb.write(0x2800, [...reqs.flatMap((r) => r.slice(1)), 0xfd]);
    for (let i = 0; i < reqs.length; i++) {
        await beeb.breakpoint(S.req_done);
        const r = await beeb.cycles(2e7);
        await beeb.clearBreakpoints();
        if (r.completed !== false) { console.log("stuck", await beeb.regs()); break; }
        const o = await beeb.read(0x2a00 + 4 * i, 4);
        let ok = "";
        if (reqs[i][0] === "read") {
            const [, t, s, p] = reqs[i];
            const b = await beeb.read(p * 256, 256);
            ok = b.every((v, j) => v === (j & 1 ? s : t)) ? " data ok" : ` DATA BAD ${b.slice(0, 4)}`;
        }
        console.log(`${label(reqs[i]).padEnd(32)} ${(r.cycles_run / 2000).toFixed(1).padStart(7)}ms  result &${o[0].toString(16).padStart(2, "0")}  polls ${o[1] | (o[2] << 8) | (o[3] << 16)}${ok}`);
    }
    await beeb.close();
}
