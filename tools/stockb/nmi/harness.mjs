// Shared harness: boot a test disc, run a queue of controller commands
// through the prototype, time each with breakpoints.
import { startBeeb, loadSymbols } from "../../beeb.mjs";

export async function boot({ model, disc, symbols, t1 = false }) {
    const beeb = await startBeeb({ model, symbols });
    const S = beeb.syms;
    await beeb.boot(disc);
    await beeb.breakpoint(S.start);
    await beeb.run(30);
    await beeb.clearBreakpoints();
    await beeb.write(S.t1_on, [t1 ? 1 : 0]);
    await beeb.runUntil("idle", 5);
    return beeb;
}

// entries: {cmd, params:[], dest, variant, delay}; returns per-entry timings (ms)
export async function runQueue(beeb, entries, { queue = 0x2800 } = {}) {
    const S = beeb.syms;
    const bytes = [];
    for (const e of entries) {
        const b = new Array(16).fill(0);
        b[0] = e.cmd ?? 0;
        const p = e.params ?? [];
        b[1] = e.n ?? p.length;
        p.forEach((v, i) => (b[2 + i] = v));
        b[6] = e.dest ?? 0x30;
        b[7] = e.variant ?? 0;
        b[8] = e.delay ?? 0;
        bytes.push(...b);
    }
    bytes.push(0xff, ...new Array(15).fill(0));
    for (let o = 0; o < bytes.length; o += 256) await beeb.write(queue + o, bytes.slice(o, o + 256));
    await beeb.write(S.go, [1]);
    const out = [];
    const step = async (addr, i, max = 4e6 * 5) => {
        await beeb.breakpoint(addr);
        const r = await beeb.cycles(max);
        await beeb.clearBreakpoints();
        if (r.completed !== false) throw new Error(`entry ${i} no stop at ${addr.toString(16)}: ${JSON.stringify(r)} ${await beeb.regs()}`);
        return r.cycles_run;
    };
    for (let i = 0; i < entries.length; i++) {
        const e = entries[i];
        const t = {};
        if (e.cmd) {
            t.toIssue = await step(S.cmd_issued, i);
            if (e.variant && !(e.variant & 0x80)) {
                t.toNmi = await step(0x0d00, i);
                t.toEnd = await step(S.cmd_finished, i);
            } else t.toEnd = await step(S.cmd_finished, i);
        } else t.toEnd = await step(S.cmd_finished, i);
        const r = await beeb.read(queue + 16 * i, 16);
        t.result = r[9];
        t.count = r[10] | (r[11] << 8) | (r[12] << 16);
        t.vsyncs = r[13];
        t.t1s = r[14];
        t.t1min = r[15];
        out.push(t); if (process.env.V) console.log(i, JSON.stringify(t));
    }
    await beeb.runUntil(S.idle, 5);
    return out;
}
