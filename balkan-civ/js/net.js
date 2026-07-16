// ============================================================
// Network multiplayer: serverless WebRTC.
// The host and each friend swap one invite/reply code (via any
// chat app); after that the connection is direct browser-to-
// browser. The host owns the authoritative, versioned game state
// and relays accepted turn updates to every connected player.
// ============================================================
"use strict";

const NET = (() => {
  const PROTOCOL = 2;
  const DEFAULT_ICE = { iceServers: [{ urls: "stun:stun.l.google.com:19302" }] };
  const ICE = globalThis.BALKAN_CIV_ICE && Array.isArray(globalThis.BALKAN_CIV_ICE.iceServers)
    ? globalThis.BALKAN_CIV_ICE : DEFAULT_ICE;
  const CHUNK = 12000;
  const MAX_CHUNKS = 2048;
  const MAX_INBOX_MESSAGES = 32;
  const INBOX_TTL = 30000;

  let isHost = false;
  let myIndex = 0;              // my player index in the game
  let peers = [];               // host: [{pc, dc, index, civ, open}]
  let hostPeer = null;          // joiner: {pc, dc, open}
  let inbox = {};               // chunk reassembly buffers
  let handlers = {};            // event callbacks from UI
  let started = false;          // remains true after a connection drops
  let sessionId = null;
  let revision = 0;
  let lastState = null;
  let awaitingAck = false;
  let queuedState = null;
  let messageSeq = 0;

  const anyChannelOpen = () => isHost
    ? peers.some(p => p.open)
    : !!(hostPeer && hostPeer.open);
  const connected = () => {
    if (!started) return anyChannelOpen();
    if (isHost) return peers.length > 0 && peers.every(p => p.open && Number.isInteger(p.index));
    return !!(hostPeer && hostPeer.open);
  };

  function makeSessionId() {
    if (globalThis.crypto && typeof globalThis.crypto.randomUUID === "function")
      return globalThis.crypto.randomUUID();
    return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
  }

  function waitIce(pc) {
    return new Promise((resolve) => {
      if (pc.iceGatheringState === "complete") { resolve(); return; }
      let settled = false;
      let timer = null;
      const finish = () => {
        if (settled) return;
        settled = true;
        pc.removeEventListener("icegatheringstatechange", check);
        if (timer !== null) clearTimeout(timer);
        resolve();
      };
      const check = () => { if (pc.iceGatheringState === "complete") finish(); };
      pc.addEventListener("icegatheringstatechange", check);
      timer = setTimeout(finish, 4000); // don't hang forever on slow ICE
    });
  }

  const encode = (desc) => btoa(JSON.stringify(desc));
  function decode(code) {
    const desc = JSON.parse(atob(String(code || "").trim()));
    if (!desc || typeof desc !== "object" || typeof desc.type !== "string" || typeof desc.sdp !== "string")
      throw new Error("Invalid WebRTC session code");
    return desc;
  }

  function setupChannel(entry, dc, onOpen = null) {
    entry.dc = dc;
    dc.onopen = () => {
      entry.open = true;
      entry.dropNotified = false;
      emit("peers");
      if (onOpen) onOpen();
    };
    dc.onclose = () => markDropped(entry);
    dc.onmessage = (e) => onRaw(entry, e.data);
    entry.pc.onconnectionstatechange = () => {
      entry.connectionState = entry.pc.connectionState;
      emit("peers");
      if (entry.connectionState === "failed" || entry.connectionState === "closed") markDropped(entry);
    };
  }

  function markDropped(entry) {
    entry.open = false;
    emit("peers");
    if (entry.silent || entry.dropNotified) return;
    entry.dropNotified = true;
    emit("drop", entry);
  }

  // ---- chunked JSON transport ----
  function sendTo(dc, obj) {
    if (!dc || dc.readyState !== "open") return false;
    const str = JSON.stringify(obj);
    const id = `${Date.now().toString(36)}-${++messageSeq}`;
    const n = Math.ceil(str.length / CHUNK);
    if (n < 1 || n > MAX_CHUNKS) return false;
    for (let i = 0; i < n; i++) {
      dc.send(JSON.stringify({ _c: id, i, n, d: str.slice(i * CHUNK, (i + 1) * CHUNK) }));
    }
    return true;
  }

  function purgeStaleInbox(now) {
    for (const [key, buf] of Object.entries(inbox))
      if (now - buf.at > INBOX_TTL) delete inbox[key];
  }

  function onRaw(entry, raw) {
    let m;
    try { m = JSON.parse(raw); } catch (e) { return; }
    if (!m || typeof m !== "object") return;
    if (m._c === undefined) { handle(entry, m); return; }
    if ((typeof m._c !== "string" && typeof m._c !== "number") ||
        !Number.isInteger(m.i) || !Number.isInteger(m.n) ||
        m.i < 0 || m.n < 1 || m.n > MAX_CHUNKS || m.i >= m.n ||
        typeof m.d !== "string" || m.d.length > CHUNK) return;
    const now = Date.now();
    purgeStaleInbox(now);
    const key = `${entry.key}:${m._c}`;
    let buf = inbox[key];
    if (!buf) {
      const live = Object.entries(inbox);
      if (live.length >= MAX_INBOX_MESSAGES) {
        live.sort((a, b) => a[1].at - b[1].at);
        delete inbox[live[0][0]];
      }
      buf = inbox[key] = { parts: new Array(m.n), got: 0, n: m.n, at: now };
    }
    if (buf.n !== m.n) { delete inbox[key]; return; }
    buf.at = now;
    if (buf.parts[m.i] === undefined) { buf.parts[m.i] = m.d; buf.got++; }
    if (buf.got === buf.n) {
      delete inbox[key];
      try { handle(entry, JSON.parse(buf.parts.join(""))); } catch (e) { /* corrupt */ }
    }
  }

  function rejectState(entry, reason) {
    emit("reject", { fromIndex: entry.index, reason });
    if (lastState && entry.dc) {
      sendTo(entry.dc, { t: "sync", p: PROTOCOL, session: sessionId,
        revision, state: lastState, reason });
    }
  }

  function handleHostState(entry, m) {
    if (!started || m.p !== PROTOCOL || m.session !== sessionId) {
      rejectState(entry, "invalid session"); return;
    }
    if (!Number.isInteger(entry.index) || m.from !== entry.index) {
      rejectState(entry, "invalid player"); return;
    }
    if (!Number.isInteger(m.baseRevision) || m.baseRevision !== revision) {
      rejectState(entry, "stale revision"); return;
    }
    if (typeof m.state !== "string") {
      rejectState(entry, "invalid state"); return;
    }
    let accepted = false;
    try {
      accepted = emit("state", m.state, {
        remote: true, fromIndex: entry.index, revision: revision + 1,
      }) !== false;
    } catch (e) {
      accepted = false;
    }
    if (!accepted) { rejectState(entry, "out-of-turn state"); return; }

    revision++;
    lastState = m.state;
    const authoritative = { t: "state", p: PROTOCOL, session: sessionId,
      revision, from: entry.index, state: lastState };
    for (const p of peers) if (p.open) sendTo(p.dc, authoritative);
    emit("revision", revision);
  }

  function flushQueuedState() {
    if (!queuedState || awaitingAck || !hostPeer || !hostPeer.open) return;
    const state = queuedState;
    queuedState = null;
    sendJoinState(state);
  }

  function handleJoinState(m) {
    if (!started || m.p !== PROTOCOL || m.session !== sessionId ||
        !Number.isInteger(m.revision) || m.revision !== revision + 1 || typeof m.state !== "string") return;
    revision = m.revision;
    lastState = m.state;
    awaitingAck = false;
    emit("state", m.state, { remote: false, fromIndex: m.from, revision, sync: false });
    emit("revision", revision);
    flushQueuedState();
  }

  function handle(entry, m) {
    if (!m || typeof m !== "object") return;
    if (m.t === "hello" && isHost) {
      entry.protocol = m.p;
      entry.compatible = m.p === PROTOCOL;
      entry.civ = entry.compatible && typeof m.civ === "string" ? m.civ : null;
      emit("peers");
    } else if (m.t === "start" && !isHost) {
      if (m.p !== PROTOCOL || typeof m.session !== "string" || !Number.isInteger(m.revision) ||
          !Number.isInteger(m.yourIndex) || m.yourIndex < 1 || typeof m.state !== "string") return;
      myIndex = m.yourIndex;
      sessionId = m.session;
      revision = m.revision;
      lastState = m.state;
      awaitingAck = false;
      queuedState = null;
      started = true;
      emit("start", m.state, { revision, session: sessionId });
    } else if (m.t === "state") {
      if (isHost) handleHostState(entry, m);
      else handleJoinState(m);
    } else if (m.t === "sync" && !isHost) {
      if (!started || m.p !== PROTOCOL || m.session !== sessionId ||
          !Number.isInteger(m.revision) || m.revision < revision || typeof m.state !== "string") return;
      revision = m.revision;
      lastState = m.state;
      awaitingAck = false;
      queuedState = null;
      emit("state", m.state, { remote: false, fromIndex: 0, revision, sync: true, reason: m.reason });
      emit("revision", revision);
    } else if (m.t === "bye") {
      markDropped(entry);
    }
  }

  function emit(ev, ...args) {
    return handlers[ev] ? handlers[ev](...args) : undefined;
  }

  // ---------- host side ----------
  async function hostInvite() {
    isHost = true;
    myIndex = 0;
    if (!sessionId) sessionId = makeSessionId();
    const pc = new RTCPeerConnection(ICE);
    const entry = { pc, dc: null, open: false, civ: null, index: null,
      key: `p${peers.length}`, silent: false, compatible: null,
      connectionState: "new", dropNotified: false };
    setupChannel(entry, pc.createDataChannel("bc"));
    peers.push(entry);
    await pc.setLocalDescription(await pc.createOffer());
    await waitIce(pc);
    entry.inviteCode = encode(pc.localDescription);
    return entry;
  }

  async function hostAcceptReply(entry, code) {
    if (!entry || !entry.pc) throw new Error("Unknown invite slot");
    await entry.pc.setRemoteDescription(decode(code));
  }

  function hostStart(game, expectedPeers = null) {
    const ready = peers.filter(p => p.open && p.compatible);
    if (!ready.length || (expectedPeers !== null && ready.length !== expectedPeers)) return false;
    for (const p of peers) {
      if (!ready.includes(p)) {
        p.silent = true;
        try { p.pc.close(); } catch (e) { /* already closed */ }
      }
    }
    peers = ready;
    revision = 0;
    lastState = game.serialize();
    started = true;
    peers.forEach((p, i) => {
      p.index = i + 1;
      sendTo(p.dc, { t: "start", p: PROTOCOL, session: sessionId,
        revision, state: lastState, yourIndex: p.index });
    });
    emit("peers");
    return true;
  }

  // ---------- joiner side ----------
  async function joinWithInvite(code, myCiv) {
    isHost = false;
    const pc = new RTCPeerConnection(ICE);
    hostPeer = { pc, dc: null, open: false, key: "host", silent: false,
      connectionState: "new", dropNotified: false };
    pc.ondatachannel = (e) => setupChannel(hostPeer, e.channel, () => {
      sendTo(e.channel, { t: "hello", p: PROTOCOL, civ: myCiv });
    });
    await pc.setRemoteDescription(decode(code));
    await pc.setLocalDescription(await pc.createAnswer());
    await waitIce(pc);
    return encode(pc.localDescription);
  }

  // ---------- shared ----------
  function sendJoinState(state) {
    if (!hostPeer || !hostPeer.open) return false;
    awaitingAck = true;
    const sent = sendTo(hostPeer.dc, { t: "state", p: PROTOCOL, session: sessionId,
      baseRevision: revision, from: myIndex, state });
    if (!sent) awaitingAck = false;
    return sent;
  }

  function sendState(game) {
    if (!started || !connected()) return false;
    const state = game.serialize();
    if (isHost) {
      revision++;
      lastState = state;
      const m = { t: "state", p: PROTOCOL, session: sessionId,
        revision, from: myIndex, state };
      for (const p of peers) sendTo(p.dc, m);
      emit("revision", revision);
      return true;
    }
    if (awaitingAck) { queuedState = state; return true; }
    return sendJoinState(state);
  }

  function reset() {
    for (const p of peers) {
      p.silent = true;
      try { p.pc.close(); } catch (e) { /* already closed */ }
    }
    if (hostPeer) {
      hostPeer.silent = true;
      try { hostPeer.pc.close(); } catch (e) { /* already closed */ }
    }
    peers = [];
    hostPeer = null;
    isHost = false;
    myIndex = 0;
    inbox = {};
    started = false;
    sessionId = null;
    revision = 0;
    lastState = null;
    awaitingAck = false;
    queuedState = null;
    messageSeq = 0;
  }

  return {
    hostInvite, hostAcceptReply, hostStart, joinWithInvite, sendState, reset,
    on: (ev, fn) => { handlers[ev] = fn; },
    get active() { return started; },
    get connected() { return connected(); },
    get syncing() { return awaitingAck; },
    get isHost() { return isHost; },
    get myIndex() { return myIndex; },
    get peers() { return peers; },
    get revision() { return revision; },
    get sessionId() { return sessionId; },
  };
})();
