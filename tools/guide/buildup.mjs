// Dump the screen before each record of a room as the viewer draws it,
// then a screenshot of the finished room.
//   node buildup.mjs room outdir
import { mkdirSync, writeFileSync } from "fs";
import { startBeeb } from "../beeb.mjs";

const room = parseInt(process.argv[2]);
const out = process.argv[3];
mkdirSync(out, { recursive: true });
const b = await startBeeb({ disc: "build/viewer.ssd", bootUntil: "viewer", symbols: "build/viewer.json" });
try {
    await b.runUntil("viewer.wait", 10);
    await b.write("room", [room]);
    await b.breakpoint("draw_cmds.next");
    let n = 0;
    for (;;) {
        const r = await b.run(3);
        const hit = r.stopped_reason !== undefined || JSON.stringify(r).includes("breakpoint");
        if (!hit) break;
        writeFileSync(`${out}/step_${String(n).padStart(2, "0")}.bin`, Buffer.from(await b.read(0x5000, 0x3000)));
        n++;
    }
    await b.clearBreakpoints();
    await b.frames(3);
    writeFileSync(`${out}/final.bin`, Buffer.from(await b.read(0x5000, 0x3000)));
    await b.shot(`${out}/final.png`);
    console.log(n, "steps");
} finally {
    await b.close();
}
process.exit(0);
