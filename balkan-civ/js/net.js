// ============================================================
// Network multiplayer: serverless WebRTC.
// The host and each friend swap one invite/reply code (via any
// chat app); after that the connection is direct browser-to-
// browser. Star topology: everyone connects to the host, who
// relays turn states. The full game state is shipped on every
// turn handoff, so no lockstep determinism is required.
// ============================================================
"use strict";

const NET = (() => {
  const ICE = { iceServers: [{ urls: "stun:stun.l.google.com:19302" }] };
  const CHUNK = 12000;

  let isHost = false;
  let myIndex = 0;              // my player index in the game
  let peers = [];               // host: [{pc, dc, index, civ, open}]
  let hostPeer = null;          // joiner: {pc, dc, open}
  let inbox = {};               // chunk reassembly buffers
  let handlers = {};            // event callbacks from UI

  const active = () => isHost ? peers.some(p => p.open) : !!(hostPeer && hostPeer.open);

  function waitIce(pc) {
    return new Promise((res) => {
      if (pc.iceGatheringState === "complete") return res();
      const check = () => {
        if (pc.iceGatheringState === "complete") {
          pc.removeEventListener("icegatheringstatechange", check);
          res();
        }
      };
      pc.addEventListener("icegatheringstatechange", check);
      setTimeout(res, 4000); // don't hang forever on slow ICE
    });
  }

  const encode = (desc) => btoa(JSON.stringify(desc));
  const decode = (code) => JSON.parse(atob(code.trim()));

  function setupChannel(entry, dc) {
    entry.dc = dc;
    dc.onopen = () => { entry.open = true; emit("peers"); };
    dc.onclose = () => { entry.open = false; emit("drop", entry); };
    dc.onmessage = (e) => onRaw(entry, e.data);
  }

  // ---- chunked JSON transport ----
  function sendTo(dc, obj) {
    if (!dc || dc.readyState !== "open") return;
    const str = JSON.stringify(obj);
    const id = Math.floor(Math.random() * 1e9);
    const n = Math.ceil(str.length / CHUNK);
    for (let i = 0; i < n; i++) {
      dc.send(JSON.stringify({ _c: id, i, n, d: str.slice(i * CHUNK, (i + 1) * CHUNK) }));
    }
  }

  function onRaw(entry, raw) {
    let m;
    try { m = JSON.parse(raw); } catch (e) { return; }
    if (m._c === undefined) return handle(entry, m);
    const key = entry.key + ":" + m._c;
    const buf = inbox[key] || (inbox[key] = { parts: [], got: 0, n: m.n });
    if (buf.parts[m.i] === undefined) { buf.parts[m.i] = m.d; buf.got++; }
    if (buf.got === buf.n) {
      delete inbox[key];
      try { handle(entry, JSON.parse(buf.parts.join(""))); } catch (e) { /* corrupt */ }
    }
  }

  function handle(entry, m) {
    if (m.t === "hello" && isHost) {
      entry.civ = m.civ;
      emit("peers");
    } else if (m.t === "start" && !isHost) {
      myIndex = m.yourIndex;
      emit("start", m.state);
    } else if (m.t === "state") {
      if (isHost) {
        // relay to everyone else, then apply locally
        for (const p of peers) if (p !== entry && p.open) sendTo(p.dc, m);
      }
      emit("state", m.state);
    } else if (m.t === "bye") {
      entry.open = false;
      emit("drop", entry);
    }
  }

  function emit(ev, ...args) { if (handlers[ev]) handlers[ev](...args); }

  // ---------- host side ----------
  async function hostInvite() {
    isHost = true;
    myIndex = 0;
    const pc = new RTCPeerConnection(ICE);
    const entry = { pc, dc: null, open: false, civ: null, key: "p" + peers.length };
    setupChannel(entry, pc.createDataChannel("bc"));
    peers.push(entry);
    await pc.setLocalDescription(await pc.createOffer());
    await waitIce(pc);
    entry.inviteCode = encode(pc.localDescription);
    return entry;
  }

  async function hostAcceptReply(entry, code) {
    await entry.pc.setRemoteDescription(decode(code));
  }

  function hostStart(game) {
    peers.forEach((p, i) => {
      p.index = i + 1;
      if (p.open) sendTo(p.dc, { t: "start", state: game.serialize(), yourIndex: p.index });
    });
  }

  // ---------- joiner side ----------
  async function joinWithInvite(code, myCiv) {
    isHost = false;
    const pc = new RTCPeerConnection(ICE);
    hostPeer = { pc, dc: null, open: false, key: "host" };
    pc.ondatachannel = (e) => {
      setupChannel(hostPeer, e.channel);
      const prevOpen = e.channel.onopen;
      e.channel.onopen = () => {
        hostPeer.open = true;
        sendTo(e.channel, { t: "hello", civ: myCiv });
        emit("peers");
      };
    };
    await pc.setRemoteDescription(decode(code));
    await pc.setLocalDescription(await pc.createAnswer());
    await waitIce(pc);
    return encode(pc.localDescription);
  }

  // ---------- shared ----------
  function sendState(game) {
    const m = { t: "state", state: game.serialize() };
    if (isHost) { for (const p of peers) if (p.open) sendTo(p.dc, m); }
    else if (hostPeer && hostPeer.open) sendTo(hostPeer.dc, m);
  }

  function reset() {
    for (const p of peers) { try { p.pc.close(); } catch (e) { /* ok */ } }
    if (hostPeer) { try { hostPeer.pc.close(); } catch (e) { /* ok */ } }
    peers = []; hostPeer = null; isHost = false; myIndex = 0; inbox = {};
  }

  return {
    hostInvite, hostAcceptReply, hostStart, joinWithInvite, sendState, reset,
    on: (ev, fn) => { handlers[ev] = fn; },
    get active() { return active(); },
    get isHost() { return isHost; },
    get myIndex() { return myIndex; },
    get peers() { return peers; },
  };
})();
