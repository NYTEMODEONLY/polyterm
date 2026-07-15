import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";
import { webcrypto } from "node:crypto";

const gameRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

class FakeDataChannel {
  constructor() {
    this.readyState = "connecting";
    this.sent = [];
    this.onopen = null;
    this.onclose = null;
    this.onmessage = null;
  }

  send(raw) { this.sent.push(raw); }
  open() { this.readyState = "open"; this.onopen?.(); }
  close() { this.readyState = "closed"; this.onclose?.(); }
  receive(message) { this.onmessage?.({ data: JSON.stringify(message) }); }
}

class FakePeerConnection {
  constructor() {
    this.iceGatheringState = "complete";
    this.localDescription = null;
    this.remoteDescription = null;
    this.channel = null;
    this.ondatachannel = null;
  }

  createDataChannel() { this.channel = new FakeDataChannel(); return this.channel; }
  async createOffer() { return { type: "offer", sdp: "test offer" }; }
  async createAnswer() { return { type: "answer", sdp: "test answer" }; }
  async setLocalDescription(description) { this.localDescription = description; }
  async setRemoteDescription(description) { this.remoteDescription = description; }
  addEventListener() {}
  removeEventListener() {}
  close() { this.channel?.close(); }
}

function loadNetwork() {
  const context = vm.createContext({
    console, Math, Date, JSON, crypto: webcrypto,
    RTCPeerConnection: FakePeerConnection,
    btoa: value => Buffer.from(value, "utf8").toString("base64"),
    atob: value => Buffer.from(value, "base64").toString("utf8"),
    setTimeout, clearTimeout,
  });
  vm.runInContext(fs.readFileSync(path.join(gameRoot, "js", "net.js"), "utf8"), context,
    { filename: "net.js" });
  return vm.runInContext("NET", context);
}

function decodedMessages(channel) {
  const complete = [];
  const chunks = new Map();
  for (const raw of channel.sent) {
    const message = JSON.parse(raw);
    if (message._c === undefined) { complete.push(message); continue; }
    let buffer = chunks.get(message._c);
    if (!buffer) {
      buffer = { parts: new Array(message.n), count: 0 };
      chunks.set(message._c, buffer);
    }
    if (buffer.parts[message.i] === undefined) {
      buffer.parts[message.i] = message.d;
      buffer.count++;
    }
    if (buffer.count === buffer.parts.length) complete.push(JSON.parse(buffer.parts.join("")));
  }
  return complete;
}

test("online host compacts connected invite slots into contiguous player indexes", async () => {
  const net = loadNetwork();
  const skipped = await net.hostInvite();
  const connected = await net.hostInvite();
  connected.dc.open();
  connected.dc.receive({ t: "hello", p: 1, civ: "BULGARIA" });
  assert.equal(net.hostStart({ serialize: () => "opening-state" }, 1), false);
  assert.equal(net.active, false);
  connected.dc.receive({ t: "hello", p: 2, civ: "BULGARIA" });

  assert.equal(net.hostStart({ serialize: () => "opening-state" }, 1), true);
  assert.equal(skipped.pc.channel.readyState, "closed");
  assert.equal(net.peers.length, 1);
  assert.equal(net.peers[0], connected);
  assert.equal(connected.index, 1);
  assert.equal(net.active, true);
  assert.equal(net.connected, true);

  const start = decodedMessages(connected.dc).find(message => message.t === "start");
  assert.deepEqual({ player: start.yourIndex, revision: start.revision, state: start.state },
    { player: 1, revision: 0, state: "opening-state" });
});

test("host authority rejects stale and out-of-turn states, then fail-closes after a drop", async () => {
  const net = loadNetwork();
  const peer = await net.hostInvite();
  peer.dc.open();
  peer.dc.receive({ t: "hello", p: 2, civ: "BULGARIA" });
  net.hostStart({ serialize: () => "opening-state" });

  let activeHuman = 1;
  const rejections = [];
  let drops = 0;
  net.on("state", (_state, meta) => meta.fromIndex === activeHuman);
  net.on("reject", rejection => rejections.push(rejection.reason));
  net.on("drop", () => { drops++; });

  peer.dc.receive({ t: "state", p: 2, session: net.sessionId,
    baseRevision: 0, from: 1, state: "guest-turn" });
  assert.equal(net.revision, 1);
  assert.equal(decodedMessages(peer.dc).filter(message => message.t === "state").at(-1).state, "guest-turn");

  peer.dc.receive({ t: "state", p: 2, session: net.sessionId,
    baseRevision: 0, from: 1, state: "stale-state" });
  activeHuman = 0;
  peer.dc.receive({ t: "state", p: 2, session: net.sessionId,
    baseRevision: 1, from: 1, state: "out-of-turn-state" });
  assert.equal(net.revision, 1);
  assert.deepEqual(rejections, ["stale revision", "out-of-turn state"]);
  const syncs = decodedMessages(peer.dc).filter(message => message.t === "sync");
  assert.equal(syncs.length, 2);
  assert.ok(syncs.every(message => message.revision === 1 && message.state === "guest-turn"));

  peer.dc.close();
  assert.equal(net.active, true);
  assert.equal(net.connected, false);
  assert.equal(drops, 1);
  net.reset();
  assert.equal(net.active, false);
  assert.equal(drops, 1);
});
