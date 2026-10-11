// BREAK in play with junk in page 3, &0D9F-&0DFF and the DFS's &0E00-&10FF
// region untouched (already the game's): does MENU come back and a game start?
//   node breakjunk.mjs <model> <regions: p3,d9f,both>
import { startBeeb } from "../beeb.mjs";
const [model = "B-DFS1.2", which = "both", pat = "rand"] = process.argv.slice(2);
const b = await startBeeb({ disc: "build/ce2.ssd", bootUntil: "menu", model });
const screen = async () => String.fromCharCode(...(await b.read(0x7c00, 1000)).map((c) => c & 0x7f));
const waitText = async (text, secs = 30) => {
    for (let t = 0; t < secs * 5; t++) { if ((await screen()).includes(text)) return true; await b.run(0.2); }
    return false;
};
const hold = async (k, s = 0.1) => { await b.keyDown(k); await b.run(s); await b.keyUp(k); };
const junk = (n) => Array.from({ length: n }, (_, i) => pat === "rand" ? (i * 197 + 91) & 255 : (pat === "ff" ? 255 : 0));
await waitText("INSTRUCTIONS!"); await b.run(0.5);
for (let i = 0; i < 3; i++) { await hold("SPACE", 0.2); await b.run(1.5); }
console.log("menu:", await waitText("I TO SEE THE INSTRUCTIONS")); await b.run(0.5);
for (let round = 0; round < 2; round++) {
    await hold("P");
    let r = await b.runUntil("game_loop", 60);
    console.log("game started:", r.stopped_reason);
    await b.run(3);
    if (which === "p3" || which === "both") await b.write(0x300, junk(256));
    if (which === "d9f" || which === "both") await b.write(0xd9f, junk(0x61));
    if (which === "ext" || which === "p3ext") await b.write(0xd9f, junk(0x51));
    if (which === "p3ext") await b.write(0x300, junk(256));
    if (which === "rwt") await b.write(0xdf0, junk(16));
    await b.run(1);
    await b.call("reset", { session_id: b.session_id, hard: false });
    const ok = await waitText("I TO SEE THE INSTRUCTIONS", 20);
    console.log(`round ${round}: BREAK with junk (${which}, ${pat}) -> menu: ${ok}`);
    if (!ok) { console.log((await screen()).match(/.{1,40}/g).join("\n")); break; }
    await b.run(0.5);
}
process.exit(0);
