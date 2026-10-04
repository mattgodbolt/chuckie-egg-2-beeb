#!/usr/bin/env node
// The front end and the way between it and the game (decision 13), on the
// release disc: the instructions, P to play, S to save in play and carry
// on, the abort key back to the menu, L to load and carry on, game over
// with a new high score and its name, and BREAK in play. Exits non-zero on the first failure.
//
//   node tools/frontcheck.mjs [--disc build/ce2.ssd] [--model B-DFS1.2]
//
// MENU's code shares addresses with the game's, so the menu is recognised
// by its text in MODE 7's screen memory; breakpoints go only on game
// routines above MENU (handoff, game_loop, harry_died).
import { startBeeb } from "./beeb.mjs";

const args = process.argv.slice(2);
const discIdx = args.indexOf("--disc");
const disc = discIdx >= 0 ? args[discIdx + 1] : "build/ce2.ssd";
const modelIdx = args.indexOf("--model");
const model = modelIdx >= 0 ? args[modelIdx + 1] : "B-DFS1.2";
const b = await startBeeb({ disc, bootUntil: "menu", model });

let failed = false;
const check = (ok, what) => {
    console.log(`${ok ? "ok  " : "FAIL"} ${what}`);
    if (!ok) failed = true;
};
const screen = async () => String.fromCharCode(...(await b.read(0x7c00, 1000)).map((c) => c & 0x7f));
// Run until MODE 7's screen shows the text (or give up after secs).
const waitText = async (text, secs = 30) => {
    for (let t = 0; t < secs * 5; t++) {
        if ((await screen()).includes(text)) return true;
        await b.run(0.2);
    }
    return false;
};
// The menu is drawn and waiting: its last lines are up, and MENU has had
// time to empty the keyboard buffer, which it does before reading. (Not the
// build stamp: the OS shows that too, echoing !BOOT's first line.)
const menuReady = async () => {
    const ok = await waitText("I TO SEE THE INSTRUCTIONS");
    await b.run(0.5);
    return ok;
};
const hold = async (key, secs = 0.3) => {
    await b.keyDown(key);
    await b.run(secs);
    await b.keyUp(key);
};
const state = async () => {
    const v = await b.read("h_cell", 11);
    return JSON.stringify({
        room: await b.peek("room"), cell: v[0] | (v[1] << 8), yf: v[2], xf: v[3], state: v[8],
        score: (await b.read("score", 10)).join(""), lives: await b.peek("lives"),
        monsters: await b.read("m_cell_lo", 5), things: await b.read("t_room", 0x29),
    });
};

try {
    // A page is up once its text is, but MENU may still be printing it and
    // empty the keyboard buffer after; and a Master repeats a key held 0.3s
    // (CMOS delay 30cs against OS 1.20's 32cs), skipping a page.
    check(await waitText("INSTRUCTIONS!"), "first boot: the instructions' title page");
    await b.run(0.5);
    await hold("SPACE", 0.2);
    check(await waitText("Harry has to make"), "instructions page 1");
    await b.run(0.5);
    await hold("SPACE", 0.2);
    check(await waitText("Henhouse Harry"), "instructions page 2");
    await b.run(0.5);
    await hold("SPACE", 0.2);
    check(await menuReady(), "the menu");

    // R: the keys in the original's order (up, down, left, right, jump,
    // take/drop, abort, save), each refused if it's taken already.
    await hold("R", 0.1);
    check(await waitText("PRESS UP KEY"), "R: redefine the keys");
    await b.run(0.5);
    for (const k of ["K", "M", "Z", "X", "X", "SPACE", "T", "Q", "V"]) await hold(k, 0.3);
    const back = await menuReady();
    check(back, "... and back to the menu (a second X refused)");
    if (!back) console.log((await screen()).match(/.{1,40}/g).join("\n"));

    await hold("P", 0.1);
    let r = await b.runUntil("game_loop", 60);
    check(r.stopped_reason === "breakpoint", "P starts a game");
    // In the game's control-bit order: jump, right, left, down, up, save,
    // take/drop, abort; internal key numbers.
    const keys = await b.read("mb_keys", 8);
    check(JSON.stringify(keys) === JSON.stringify([0x62, 0x42, 0x61, 0x65, 0x46, 0x63, 0x23, 0x10]),
        `the game has the new keys (${keys.map((k) => k.toString(16)).join(" ")})`);
    await b.run(3);                                   // the truck backs in
    const before = await b.peek("h_cell");
    await hold("X", 2);                               // walk right, with X now
    check((await b.peek("h_cell")) > before, "X walks Harry right");

    // The save key (V now) in play: the state saved, the game carried on.
    await b.keyDown("V");
    r = await b.runUntil("handoff", 5);
    check(r.stopped_reason === "breakpoint", "the save key hands the game to MENU");
    const saved = await state();
    await b.run(0.2);
    await b.keyUp("V");
    r = await b.runUntil("game_loop", 60);
    check(r.stopped_reason === "breakpoint" && (await state()) === saved, "the saved game carries on as it was");

    // The abort key (Q now): back to the menu, no instructions.
    await hold("Q", 0.5);
    check(await menuReady(), "the abort key returns to the menu");
    check(!(await screen()).includes("INSTRUCTIONS!"), "... without the instructions");

    // L: the save loaded, the game carried on from it.
    await hold("L", 0.1);
    r = await b.runUntil("game_loop", 60);
    const loaded = await state();
    check(r.stopped_reason === "breakpoint" && loaded === saved, "L loads the saved game as it was");
    if (loaded !== saved) console.log(`     saved  ${saved}\n     loaded ${loaded}\n     ${r.stopped_reason}\n${await screen()}`);

    // Game over with a score that beats the table: the name goes in.
    await b.write("lives", [1]);
    await b.write("score", [0, 0, 0, 0, 0, 1, 2, 3, 4, 0]);
    await b.keyDown("X");
    r = await b.runUntil("harry_died", 60);
    await b.keyUp("X");
    check(r.stopped_reason === "breakpoint", "walking into the dog: the last life lost");
    const final = (await b.read("score", 10)).join("");   // (room 2's visit bonus added 100)
    check(await waitText("ENTER NAME", 30), "game over: a new high score asks for a name");
    for (const k of ["M", "A", "X", "DELETE", "T", "RETURN"]) await hold(k, 0.1);
    const named = await waitText(`MAT.........${final}`, 10);
    check(named, "the name and score top the table");
    if (!named) console.log((await screen()).match(/.{1,40}/g).join("\n"));

    // BREAK in play (decision 22): a soft reset comes back to the menu,
    // without the instructions, with the start-up option put back, and
    // the game plays again.
    const options = await b.peek(0x28f);
    check(await menuReady(), "the menu after the name");
    await hold("P", 0.1);
    r = await b.runUntil("game_loop", 60);
    check(r.stopped_reason === "breakpoint", "P starts another game");
    await b.run(3);
    await b.call("reset", { session_id: b.session_id, hard: false });
    check(await menuReady(), "BREAK in play comes back to the menu");
    check(!(await screen()).includes("INSTRUCTIONS!"), "... without the instructions");
    check((await b.peek(0x28f)) === options, `... with the start-up options put back (&${(await b.peek(0x28f)).toString(16)})`);
    await hold("P", 0.1);
    r = await b.runUntil("game_loop", 60);
    check(r.stopped_reason === "breakpoint", "... and a game starts again");
} finally {
    await b.close();
}
console.log(failed ? "front end: FAILED" : "front end: all checks pass");
process.exit(failed ? 1 : 0);
