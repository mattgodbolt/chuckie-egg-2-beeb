// Screenshot rooms in the BBC room viewer: node viewshots.mjs outdir first last
import { mkdirSync } from "fs";
import { startBeeb } from "../beeb.mjs";

const out = process.argv[2];
const first = parseInt(process.argv[3] ?? "1");
const last = parseInt(process.argv[4] ?? "120");
mkdirSync(out, { recursive: true });
const b = await startBeeb({ disc: "build/viewer.ssd", bootUntil: "viewer", symbols: "build/viewer.json" });
try {
    await b.runUntil("viewer.wait", 10);
    for (let r = first; r <= last; r++) {
        await b.write("room", [r]);
        await b.runUntil("viewer.wait", 10);
        await b.frames(2);
        await b.shot(`${out}/room_${String(r).padStart(3, "0")}.png`);
    }
} finally {
    await b.close();
}
process.exit(0);
