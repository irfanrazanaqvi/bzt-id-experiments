// Baseline identity services for comparison with the Fabric-backed BZT-ID chaincode.
//  MODE=central : centralized relational store (SQLite via node:sqlite) - single trusted DB.
//  MODE=jwt     : stateless signed-token service (ES256 JWT-style) - no ledger, no revocation store.
// Same logical operations as the chaincode: issue (write), verify (read), audit (write).
const http = require("http"), crypto = require("crypto");
const MODE = process.env.MODE || "central", PORT = +process.env.PORT || 8080;
const sha = s => crypto.createHash("sha256").update(s).digest("hex");
let db, ins, sel, aud;
if (MODE === "central") {
  const { DatabaseSync } = require("node:sqlite");
  db = new DatabaseSync(":memory:".replace(":memory:", process.env.DB || "/tmp/central.db"));
  db.exec("PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL;");   // durable commits, like a real registry DB
  db.exec("CREATE TABLE IF NOT EXISTS cred(id TEXT PRIMARY KEY, subject TEXT, hash TEXT, revoked INT, ts INT); CREATE TABLE IF NOT EXISTS audit(id TEXT, ev TEXT, ts INT)");
  ins = db.prepare("INSERT OR REPLACE INTO cred VALUES(?,?,?,0,?)");
  sel = db.prepare("SELECT hash,revoked FROM cred WHERE id=?");
  aud = db.prepare("INSERT INTO audit VALUES(?,?,?)");
}
const { privateKey, publicKey } = crypto.generateKeyPairSync("ec", { namedCurve: "P-256" });
const b64 = b => Buffer.from(b).toString("base64url");
const body = req => new Promise(r => { let d = ""; req.on("data", c => d += c); req.on("end", () => r(d)); });
http.createServer(async (req, res) => {
  const u = new URL(req.url, "http://x"); const parts = u.pathname.split("/").filter(Boolean);
  try {
    if (req.method === "POST" && parts[0] === "issue") {
      const b = JSON.parse(await body(req) || "{}"); const id = b.id || crypto.randomUUID();
      const h = sha(JSON.stringify(b));
      if (MODE === "central") { ins.run(id, b.subject || "s", h, Date.now()); res.end(JSON.stringify({ id })); }
      else {
        const payload = b64(JSON.stringify({ id, sub: b.subject, h, iat: Date.now() }));
        const sig = crypto.sign("sha256", Buffer.from(payload), privateKey).toString("base64url");
        res.end(JSON.stringify({ id, token: payload + "." + sig }));
      }
    } else if (req.method === "POST" && parts[0] === "audit") {
      const b = JSON.parse(await body(req) || "{}");
      if (MODE === "central") aud.run(b.id || "x", "verify", Date.now());
      res.end("{}");
    } else if (req.method === "GET" && parts[0] === "verify") {
      if (MODE === "central") { const r = sel.get(parts[1]); res.end(JSON.stringify({ ok: !!r && !r.revoked })); }
      else {
        const [p, s] = (u.searchParams.get("t") || ".").split(".");
        const ok = !!s && crypto.verify("sha256", Buffer.from(p), publicKey, Buffer.from(s, "base64url"));
        res.end(JSON.stringify({ ok }));
      }
    } else { res.statusCode = 404; res.end("{}"); }
  } catch (e) { res.statusCode = 500; res.end(String(e)); }
}).listen(PORT, () => console.log("listening", MODE, PORT));
