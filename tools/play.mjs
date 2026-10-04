#!/usr/bin/env node
// Run a scripted session against the game and capture what happened.
//
//   node tools/play.mjs '<script>' [prefix] [--disc build/ce2.ssd] [--boot 3] [--model B-DFS1.2]
//
// The script is a comma-separated list of steps:
//   1.5            run 1.5 seconds of emulated time
//   f10            run exactly 10 frames
//   SPACE:tap      press and release (0.1s); SPACE:0.5 holds for 0.5s
//   LEFT:down      hold a key; LEFT:up releases it
//   !name          screenshot to <prefix>name.png
//   #name          dump the 12K screen to <prefix>name.bin
//   ?sym:n         print n bytes at a symbol (or &addr / 0xaddr)
//   =sym:v1/v2/..  poke bytes at a symbol
//   @label         run until PC reaches a symbol (execute breakpoint)
//
// Key names are jsbeeb's own: SPACE, RETURN, SHIFT, LEFT, RIGHT, UP, DOWN, A-Z.
import { startBeeb } from "./beeb.mjs";

const args = process.argv.slice(2);
const opt = (name, dflt) => {
    const i = args.indexOf(`--${name}`);
    if (i < 0) return dflt;
    const v = args[i + 1];
    args.splice(i, 2);
    return v;
};
const disc = opt("disc", "build/ce2.ssd");
const bootSecs = parseFloat(opt("boot", "3"));
const model = opt("model", "B-DFS1.2");
const script = args[0] ?? "";
const prefix = args[1] ?? "shots/p_";

const beeb = await startBeeb({ disc, bootSecs, model });
try {
    for (const raw of script.split(",")) {
        const step = raw.trim();
        if (!step) continue;
        if (step.startsWith("!")) {
            console.log("SHOT", await beeb.shot(`${prefix}${step.slice(1)}.png`));
        } else if (step.startsWith("#")) {
            await beeb.dump(`${prefix}${step.slice(1)}.bin`);
            console.log("DUMP", `${prefix}${step.slice(1)}.bin`);
        } else if (step.startsWith("?")) {
            const [sym, n] = step.slice(1).split(":");
            const bytes = await beeb.read(sym, parseInt(n || "1"));
            console.log(sym, bytes.map((b) => b.toString(16).padStart(2, "0")).join(" "));
        } else if (step.startsWith("=")) {
            const [sym, vals] = step.slice(1).split(":");
            await beeb.write(sym, vals.split("/").map((v) => parseInt(v)));
        } else if (step.startsWith("@")) {
            await beeb.breakpoint(step.slice(1));
            const r = await beeb.run(30);
            await beeb.clearBreakpoints();
            console.log("BREAK", step.slice(1), r.stopped_reason ?? "timeout");
        } else if (/^f\d+$/.test(step)) {
            await beeb.frames(parseInt(step.slice(1)));
        } else if (/^[\d.]+$/.test(step)) {
            await beeb.run(parseFloat(step));
        } else {
            const [key, action = "tap"] = step.split(":");
            if (action === "down") await beeb.keyDown(key);
            else if (action === "up") await beeb.keyUp(key);
            else if (action === "tap") await beeb.tap(key);
            else await beeb.tap(key, parseFloat(action));
        }
    }
} finally {
    await beeb.close();
}
process.exit(0);
