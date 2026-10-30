const { test } = require('node:test');
const assert = require('node:assert/strict');
const dgram = require('node:dgram');
const { once } = require('node:events');
const { normalizeMac, broadcast, parseReply, mergeReply, scan } = require('../app/discovery.cjs');

test('MAC and broadcast address validation', () => {
  assert.equal(normalizeMac('02-aa-bb-cc-dd-ee'), '02:AA:BB:CC:DD:EE');
  for (const mac of ['00:00:00:00:00:00', 'FF:FF:FF:FF:FF:FF', '01:AA:BB:CC:DD:EE', '<img>', null]) assert.equal(normalizeMac(mac), null);
  assert.equal(broadcast('10.20.31.4', '255.255.252.0'), '10.20.31.255');
  assert.equal(broadcast('invalid', '255.255.255.0'), null);
});
test('ignore unrelated/old scan replies and keep conflicting MACs disabled', () => {
  const body = { type: 'd1-robot-v1', request: 'current', mac: '02:AA:BB:CC:DD:EE', state: 'available' };
  const packet = value => Buffer.from(JSON.stringify(value));
  assert.equal(parseReply(packet(body), 'old', '127.0.0.1'), null);
  assert.equal(parseReply(packet({ ...body, state: 'unknown' }), 'current', '127.0.0.1'), null);
  assert.equal(parseReply(Buffer.alloc(2048), 'current', '127.0.0.1'), null);
  const found = new Map(), robot = parseReply(packet(body), 'current', '127.0.0.1');
  mergeReply(found, robot);
  mergeReply(found, { ...robot, host: '127.0.0.2' });
  mergeReply(found, robot);
  assert.equal(found.get(robot.mac).state, 'conflict');
});
test('real UDP scan tolerates a failed interface, ignores bad replies, and cancels', async t => {
  const server = dgram.createSocket('udp4');
  server.bind(0, '127.0.0.1');
  await once(server, 'listening');
  t.after(() => server.close());
  server.on('message', (message, peer) => {
    const query = JSON.parse(message);
    server.send(Buffer.from('not json'), peer.port, peer.address);
    server.send(Buffer.from(JSON.stringify({ type: 'd1-robot-v1', request: query.request, mac: '02:AA:BB:CC:DD:EE', state: 'available' })), peer.port, peer.address);
  });
  const options = { destinations: [{ local: '192.0.2.200', host: '192.0.2.255' }, { local: '127.0.0.1', host: '127.0.0.1' }], port: server.address().port, timeoutMs: 150 };
  const robots = await scan(options);
  assert.equal(robots.length, 1);
  assert.equal(robots[0].mac, '02:AA:BB:CC:DD:EE');
  const abort = new AbortController();
  const pending = scan({ ...options, signal: abort.signal, timeoutMs: 5000 });
  abort.abort();
  await pending;
  await assert.rejects(scan({ destinations: [] }), /IPv4/);
});
