// node cap.mjs <path> <out.jsonl> <seconds>
import fs from 'node:fs';
const [path, out, secs] = process.argv.slice(2);
const f = fs.createWriteStream(out, {flags: 'a'});
let ws, stop = Date.now() + 1000 * Number(secs || 3600);
function go() {
  ws = new WebSocket('wss://watch.joinbuilders.org/' + path);
  ws.onmessage = (e) => { const s = typeof e.data === 'string' ? e.data : Buffer.from(e.data).toString(); f.write(s.endsWith('\n') ? s : s + '\n'); };
  ws.onclose = () => { if (Date.now() < stop) setTimeout(go, 3000); else process.exit(0); };
  ws.onerror = () => {};
}
go();
setInterval(() => { if (Date.now() > stop) { try { ws.close(); } catch {} f.end(); process.exit(0); } }, 5000);
