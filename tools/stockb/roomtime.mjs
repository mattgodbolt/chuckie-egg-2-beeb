// How long the port takes to enter a room now (enter_room: draw and set up),
// for a sample of rooms: the pause a streamed load would add to.
//   node <this> [rooms...]    (from the repository root, test build)
import { startBeeb } from "../beeb.mjs";

const rooms = process.argv.slice(2).map(Number);
const list = rooms.length ? rooms : [1, 2, 5, 11, 33, 38, 48, 56, 66, 74, 89, 101, 111, 115, 120];
const b = await startBeeb({ disc: "build/test.ssd", symbols: "build/test.json", bootUntil: "game_loop" });
const ENTER = b.addr("enter_room"), AFTER = b.addr("teleport") + 7; // the JMP save_checkpoint
const out = [];
for (const room of list) {
    await b.write("dbg_room", [room]);
    await b.runUntil("teleport", 20);
    await b.write("room", [room]);
    await b.breakpoint(ENTER);
    let r = await b.run(20);
    await b.clearBreakpoints();
    await b.breakpoint(AFTER);
    r = await b.run(20);
    await b.clearBreakpoints();
    out.push([room, r.cycles_run]);
    console.log(`room ${room}: enter_room ${r.cycles_run} cycles (${(r.cycles_run / 2000).toFixed(0)}ms, ${(r.cycles_run / 40000).toFixed(1)} frames)`);
    for (let i = 0; i < 2; i++) await b.runUntil("game_loop", 20);
}
const c = out.map((x) => x[1]);
console.log(`mean ${(c.reduce((a, b) => a + b) / c.length / 2000).toFixed(0)}ms, max ${(Math.max(...c) / 2000).toFixed(0)}ms`);
await b.close();
