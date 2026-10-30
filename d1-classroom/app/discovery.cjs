const dgram = require('node:dgram');
const os = require('node:os');
const net = require('node:net');
const crypto = require('node:crypto');

const PORT = 8765;
function normalizeMac(value) {
  if (typeof value !== 'string') return null;
  const mac = value.replace(/-/g, ':').toUpperCase();
  if (!/^(?:[0-9A-F]{2}:){5}[0-9A-F]{2}$/.test(mac)) return null;
  if (mac === '00:00:00:00:00:00' || (parseInt(mac.slice(0, 2), 16) & 1)) return null;
  return mac;
}
function broadcast(address, mask) {
  if (!net.isIPv4(address) || !net.isIPv4(mask)) return null;
  const a = address.split('.').map(Number), m = mask.split('.').map(Number);
  if (m.join('.') === '255.255.255.255' || m[0] === 0) return null;
  return a.map((v, i) => v | (255 ^ m[i])).join('.');
}
function targets() {
  return Object.values(os.networkInterfaces()).flat().filter(i =>
    i && i.family === 'IPv4' && !i.internal && !i.address.startsWith('169.254.')
  ).map(i => ({ local: i.address, host: broadcast(i.address, i.netmask) })).filter(t => t.host);
}
function parseReply(buffer, request, address) {
  if (buffer.length > 1024 || !net.isIPv4(address)) return null;
  try {
    const data = JSON.parse(buffer.toString('utf8'));
    const mac = normalizeMac(data.mac);
    if (data.type !== 'd1-robot-v1' || data.request !== request || !mac ||
        !['available', 'busy', 'unavailable'].includes(data.state)) return null;
    return { mac, host: address, port: PORT, state: data.state };
  } catch { return null; }
}
function mergeReply(found, robot) {
  const old = found.get(robot.mac);
  if (old && old.host !== robot.host) {
    old.state = 'conflict';
    return;
  }
  if (!old || old.state !== 'conflict') found.set(robot.mac, robot);
}

// Options are dependency injection for tests; the renderer cannot supply targets or ports.
function scan({ signal, destinations = targets(), timeoutMs = 3000, port = PORT } = {}) {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) return resolve([]);
    if (!destinations.length) return reject(Error('沒有可用的 IPv4 網路，請先連接課室 Wi-Fi'));
    const request = crypto.randomBytes(16).toString('hex');
    const payload = Buffer.from(JSON.stringify({ type: 'd1-discover-v1', request }));
    const found = new Map(), sockets = [], timers = [];
    let finished = false, sent = 0;
    function finish(error) {
      if (finished) return;
      finished = true;
      timers.forEach(clearTimeout);
      signal?.removeEventListener('abort', abort);
      for (const socket of sockets) { try { socket.close(); } catch {} }
      if (error) reject(error);
      else resolve([...found.values()].sort((a, b) => a.mac.localeCompare(b.mac)));
    }
    const abort = () => finish();
    signal?.addEventListener('abort', abort, { once: true });
    timers.push(setTimeout(() => finish(sent ? null : Error('無法送出掃描，請檢查網路介面與防火牆')), timeoutMs));
    for (const target of destinations) {
      const socket = dgram.createSocket('udp4');
      sockets.push(socket);
      // A failed VPN/virtual interface must not prevent the usable interface from scanning.
      socket.on('error', () => {});
      socket.on('message', (buffer, peer) => {
        if (finished || peer.port !== port) return;
        const reply = parseReply(buffer, request, peer.address);
        if (reply && found.size < 256) mergeReply(found, { ...reply, port });
      });
      socket.bind(0, target.local, () => {
        if (finished) return;
        try { socket.setBroadcast(true); } catch { return; }
        const send = () => {
          if (finished) return;
          socket.send(payload, port, target.host, error => { if (!error) sent++; });
        };
        send();
        timers.push(setTimeout(send, Math.floor(timeoutMs / 3)));
        timers.push(setTimeout(send, Math.floor(timeoutMs * 2 / 3)));
      });
    }
  });
}
module.exports = { PORT, normalizeMac, broadcast, targets, parseReply, mergeReply, scan };
