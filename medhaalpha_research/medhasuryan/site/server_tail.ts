const PASS = process.env.APP_PASSWORD || "";
const DATA_URL = process.env.DATA_URL || "https://raw.githubusercontent.com/niithinlk-hub/indian_breakout_scanner/claude/cool-cannon-2qua2u/medhaalpha_research/medhasuryan/bt4.json";
let cache: string | null = null, fetchedAt = 0;
async function getData(): Promise<string | null> {
  if (cache && Date.now() - fetchedAt < 30 * 60 * 1000) return cache;
  try {
    const r = await fetch(DATA_URL, { headers: { "cache-control": "no-cache" } });
    if (r.ok) { const t = await r.text(); JSON.parse(t); cache = t; fetchedAt = Date.now(); }
    else console.log("data fetch status", r.status);
  } catch (e) { console.log("data fetch failed", String(e)); }
  return cache;
}
function authorized(req: Request): boolean {
  if (!PASS) return false;                                   // no password configured: nothing is served
  const h = req.headers.get("authorization") || "";
  if (!h.startsWith("Basic ")) return false;
  let dec = "";
  try { dec = atob(h.slice(6)); } catch { return false; }
  const given = new TextEncoder().encode(dec.slice(dec.indexOf(":") + 1)), want = new TextEncoder().encode(PASS);
  if (given.length !== want.length) return false;
  let x = 0;
  for (let i = 0; i < want.length; i++) x |= given[i] ^ want[i];
  return x === 0;
}
const server = Bun.serve({
  port: Number(process.env.PORT || 3000), hostname: "0.0.0.0",
  async fetch(req) {
    const url = new URL(req.url);
    if (url.pathname === "/health") return new Response("ok");
    if (!authorized(req)) return new Response("Password needed (use the medhaalpha app password).", { status: 401, headers: { "WWW-Authenticate": 'Basic realm="MedhaAlpha backtest", charset="UTF-8"' } });
    const head = { "cache-control": "no-store", "x-content-type-options": "nosniff", "referrer-policy": "no-referrer" };
    if (url.pathname === "/data.json") {
      const d = await getData();
      return d ? new Response(d, { headers: { ...head, "content-type": "application/json" } }) : new Response("data not loaded yet", { status: 503, headers: head });
    }
    return new Response(HTML, { headers: { ...head, "content-type": "text/html; charset=utf-8" } });
  },
});
console.log("medhaalpha 4-model backtest listening on", server.port);
getData();
