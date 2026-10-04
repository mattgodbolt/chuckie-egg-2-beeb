// A thin client for the jsbeeb MCP server, shared by every tool in here.
//
// We talk to the real MCP server over stdio (the same one Claude Code uses),
// so what the tools test is exactly what the MCP tools would do.
//
// Point JSBEEB_MCP at a local server.js to test against a working copy.
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "fs";
import { dirname, resolve } from "path";

const MCP = process.env.JSBEEB_MCP
    ? { command: "node", args: [process.env.JSBEEB_MCP] }
    : { command: "npx", args: ["-y", "jsbeeb-mcp"] };

const text = (r) => r.content.find((c) => c.type === "text")?.text ?? "";
const image = (r) => r.content.find((c) => c.type === "image");

// Baron's --symbols output: { "src/main.6502": { "label": value, ... } }.
// Flattened, so callers can ask for sym("angle") without caring which file.
export function loadSymbols(path = "build/symbols.json") {
    if (!existsSync(path)) return {};
    const all = JSON.parse(readFileSync(path, "utf8"));
    const out = {};
    for (const file of Object.values(all)) {
        for (const [k, v] of Object.entries(file)) if (!k.includes("@")) out[k] = v;
    }
    return out;
}

// bootUntil names a symbol to run to after booting (up to 30s): the way to
// know the program is running, since loading takes a while (4.6s measured,
// with the sideways RAM image).
export async function startBeeb({ disc, model = "B-DFS1.2", bootSecs = 0, bootUntil, symbols = "build/symbols.json" } = {}) {
    const transport = new StdioClientTransport(MCP);
    const client = new Client({ name: "ce2-harness", version: "1.0.0" });
    await client.connect(transport);

    const call = async (name, args) => {
        const r = await client.callTool({ name, arguments: args });
        if (r.isError) throw new Error(`${name}: ${JSON.stringify(r.content)}`);
        return r;
    };
    const json = async (name, args) => JSON.parse(text(await call(name, args)));

    const { session_id } = await json("create_machine", { model });
    const syms = loadSymbols(symbols);

    const beeb = {
        session_id,
        call,
        syms,
        // Resolve a symbol name or pass a number straight through.
        addr(a) {
            if (typeof a === "number") return a;
            if (/^(0x|&)/i.test(a)) return parseInt(a.replace("&", "0x"));
            if (!(a in syms)) throw new Error(`unknown symbol ${a}`);
            return syms[a];
        },
        async boot(path = disc) {
            await call("boot_disc", { session_id, image_path: resolve(path) });
        },
        // Seconds of emulated time. Prefer frames() when sampling the display:
        // a whole number of seconds is a whole number of frames, so repeated
        // samples land at the same point in the game loop every time.
        async run(secs) {
            return json("run_for_cycles", { session_id, cycles: Math.max(1, Math.round(secs * 2e6)) });
        },
        async cycles(n) {
            return json("run_for_cycles", { session_id, cycles: Math.max(1, Math.round(n)) });
        },
        async frames(count = 1) {
            return json("run_frames", { session_id, count });
        },
        async keyDown(key) {
            await call("key_down", { session_id, key });
        },
        async keyUp(key) {
            await call("key_up", { session_id, key });
        },
        async tap(key, secs = 0.1) {
            await beeb.keyDown(key);
            await beeb.run(secs);
            await beeb.keyUp(key);
        },
        async read(address, length = 1) {
            const a = beeb.addr(address);
            const bytes = [];
            for (let off = 0; off < length; off += 256) {
                const n = Math.min(256, length - off);
                const r = await json("read_memory", { session_id, address: a + off, length: n });
                bytes.push(...r.bytes);
            }
            return bytes;
        },
        async peek(address) {
            return (await beeb.read(address, 1))[0];
        },
        async peekw(address) {
            const [lo, hi] = await beeb.read(address, 2);
            return lo | (hi << 8);
        },
        async write(address, bytes) {
            await call("write_memory", { session_id, address: beeb.addr(address), bytes });
        },
        async regs() {
            return text(await call("read_registers", { session_id }));
        },
        async shot(file) {
            const img = image(await call("screenshot", { session_id, active_only: true }));
            mkdirSync(dirname(resolve(file)), { recursive: true });
            writeFileSync(resolve(file), Buffer.from(img.data, "base64"));
            return resolve(file);
        },
        // The screen: 12K at &5000 (256x192 in MODE 1's pixels).
        async dump(file) {
            const bytes = await beeb.read(0x5000, 0x3000);
            if (file) {
                mkdirSync(dirname(resolve(file)), { recursive: true });
                writeFileSync(resolve(file), Buffer.from(bytes));
            }
            return bytes;
        },
        async breakpoint(address, type = "execute") {
            return json("set_breakpoint", { session_id, address: beeb.addr(address), type });
        },
        async clearBreakpoints() {
            await call("clear_breakpoint", { session_id, id: 0 });
        },
        async saveState(label = "") {
            return (await json("save_state", { session_id, label })).state_id;
        },
        async restoreState(state_id) {
            await call("restore_state", { session_id, state_id });
        },
        async close() {
            try {
                await call("destroy_machine", { session_id });
            } catch {}
            await client.close();
        },
        async runUntil(sym, secs = 30) {
            await beeb.breakpoint(sym);
            const r = await beeb.run(secs);
            await beeb.clearBreakpoints();
            return r;
        },
    };
    if (disc) {
        await beeb.boot(disc);
        if (bootUntil) await beeb.runUntil(bootUntil);
        if (bootSecs) await beeb.run(bootSecs);
    }
    return beeb;
}
