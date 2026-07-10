// ============================================================
// Procedural sound effects — WebAudio, no external files
// ============================================================
"use strict";

const SFX = (() => {
  let ctx = null;
  let muted = false;
  try { muted = localStorage.getItem("balkan-civ-muted") === "1"; } catch (e) { /* no storage */ }

  function ac() {
    if (!ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      ctx = new AC();
    }
    if (ctx.state === "suspended") ctx.resume();
    return ctx;
  }

  // One enveloped oscillator note
  function tone(freq, dur, type = "sine", vol = 0.12, delay = 0) {
    const a = ac();
    if (!a) return;
    const t0 = a.currentTime + delay;
    const osc = a.createOscillator();
    const gain = a.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, t0);
    gain.gain.setValueAtTime(0, t0);
    gain.gain.linearRampToValueAtTime(vol, t0 + 0.01);
    gain.gain.exponentialRampToValueAtTime(0.001, t0 + dur);
    osc.connect(gain).connect(a.destination);
    osc.start(t0);
    osc.stop(t0 + dur + 0.05);
  }

  // Filtered noise burst (impacts)
  function noise(dur, vol = 0.15, delay = 0, cutoff = 800) {
    const a = ac();
    if (!a) return;
    const t0 = a.currentTime + delay;
    const len = Math.max(1, Math.floor(a.sampleRate * dur));
    const buf = a.createBuffer(1, len, a.sampleRate);
    const data = buf.getChannelData(0);
    for (let i = 0; i < len; i++) data[i] = (Math.random() * 2 - 1) * (1 - i / len);
    const src = a.createBufferSource();
    src.buffer = buf;
    const filt = a.createBiquadFilter();
    filt.type = "lowpass";
    filt.frequency.value = cutoff;
    const gain = a.createGain();
    gain.gain.setValueAtTime(vol, t0);
    gain.gain.exponentialRampToValueAtTime(0.001, t0 + dur);
    src.connect(filt).connect(gain).connect(a.destination);
    src.start(t0);
  }

  function arp(freqs, step = 0.09, dur = 0.18, type = "triangle", vol = 0.1) {
    freqs.forEach((f, i) => tone(f, dur, type, vol, i * step));
  }

  const sounds = {
    click:    () => tone(600, 0.05, "square", 0.04),
    select:   () => tone(440, 0.05, "sine", 0.05),
    move:     () => { tone(300, 0.05, "sine", 0.05); tone(340, 0.05, "sine", 0.04, 0.05); },
    attack:   () => { noise(0.18, 0.22, 0, 900); tone(110, 0.18, "sawtooth", 0.12); },
    cityhit:  () => { noise(0.3, 0.25, 0, 500); tone(80, 0.3, "sawtooth", 0.14); },
    build:    () => { tone(523, 0.1, "triangle", 0.09); tone(659, 0.14, "triangle", 0.09, 0.08); },
    coin:     () => { tone(988, 0.06, "square", 0.07); tone(1319, 0.09, "square", 0.06, 0.05); },
    turn:     () => tone(196, 0.14, "sine", 0.08),
    research: () => arp([440, 554, 659], 0.08, 0.16),
    war:      () => { tone(98, 0.6, "sawtooth", 0.13); tone(104, 0.6, "sawtooth", 0.1, 0.02); noise(0.4, 0.1, 0, 300); },
    peace:    () => arp([392, 494, 587], 0.1, 0.25, "sine", 0.09),
    capture:  () => arp([330, 392, 494, 659], 0.09, 0.2),
    golden:   () => arp([523, 659, 784, 1047, 1319], 0.08, 0.3, "triangle", 0.11),
    bell:     () => { tone(880, 0.7, "sine", 0.1); tone(1760, 0.5, "sine", 0.05, 0.02); tone(587, 0.9, "sine", 0.06, 0.04); },
    spy:      () => { tone(740, 0.06, "square", 0.05); tone(740, 0.06, "square", 0.05, 0.12); },
    grow:     () => { tone(392, 0.08, "sine", 0.07); tone(523, 0.12, "sine", 0.07, 0.07); },
    wonder:   () => arp([392, 494, 587, 784, 988], 0.1, 0.4, "triangle", 0.1),
    defeat:   () => arp([392, 330, 262, 196], 0.12, 0.35, "sawtooth", 0.09),
  };

  function play(name) {
    if (muted) return;
    try { if (sounds[name]) sounds[name](); } catch (e) { /* audio unavailable */ }
  }

  function toggleMute() {
    muted = !muted;
    try { localStorage.setItem("balkan-civ-muted", muted ? "1" : "0"); } catch (e) { /* ignore */ }
    return muted;
  }

  // ---------- ambient music: slow drone + wandering Hijaz melody ----------
  let musicOn = true;
  try { musicOn = localStorage.getItem("balkan-civ-music") !== "0"; } catch (e) { /* ignore */ }
  let musicNodes = null, melodyTimer = null, nextNote = 0, melodyIdx = 3;
  // D E♭ F♯ G A B♭ C♯ D — the double-harmonic colour of Balkan folk tunes
  const SCALE = [293.66, 311.13, 369.99, 392.0, 440.0, 466.16, 554.37, 587.33];

  function melodyNote(freq, dur, when, vol = 0.028) {
    const a = ctx;
    const o = a.createOscillator();
    o.type = "sine";
    o.frequency.setValueAtTime(freq, when);
    const g = a.createGain();
    g.gain.setValueAtTime(0, when);
    g.gain.linearRampToValueAtTime(vol, when + dur * 0.25);
    g.gain.linearRampToValueAtTime(0, when + dur);
    o.connect(g).connect(a.destination);
    o.start(when);
    o.stop(when + dur + 0.1);
  }

  function scheduleMelody() {
    const a = ctx;
    if (!a || !musicNodes) return;
    while (nextNote < a.currentTime + 1.6) {
      const steps = [-2, -1, -1, 0, 1, 1, 2];
      melodyIdx = Math.max(0, Math.min(SCALE.length - 1,
        melodyIdx + steps[Math.floor(Math.random() * steps.length)]));
      const dur = [1.1, 1.6, 2.2, 3.0][Math.floor(Math.random() * 4)];
      if (Math.random() > 0.3) {
        melodyNote(SCALE[melodyIdx], dur, nextNote);
        if (Math.random() < 0.25) melodyNote(SCALE[melodyIdx] * 2, dur * 0.5, nextNote + 0.06, 0.012);
      }
      nextNote += dur;
    }
  }

  function startMusic() {
    if (!musicOn || musicNodes) return;
    const a = ac();
    if (!a) return;
    const master = a.createGain();
    master.gain.value = 0.05;
    master.connect(a.destination);
    const filt = a.createBiquadFilter();
    filt.type = "lowpass";
    filt.frequency.value = 300;
    filt.connect(master);
    const o1 = a.createOscillator();
    o1.type = "sawtooth"; o1.frequency.value = 73.42;   // D2 drone
    const o2 = a.createOscillator();
    o2.type = "sawtooth"; o2.frequency.value = 110.0;   // A2 fifth
    o2.detune.value = 5;
    const dg = a.createGain();
    dg.gain.value = 0.5;
    o1.connect(dg); o2.connect(dg); dg.connect(filt);
    o1.start(); o2.start();
    musicNodes = { master, o1, o2 };
    nextNote = a.currentTime + 0.8;
    melodyTimer = setInterval(scheduleMelody, 400);
  }

  function stopMusic() {
    if (melodyTimer) { clearInterval(melodyTimer); melodyTimer = null; }
    if (musicNodes) {
      try { musicNodes.o1.stop(); musicNodes.o2.stop(); musicNodes.master.disconnect(); } catch (e) { /* ok */ }
      musicNodes = null;
    }
  }

  function toggleMusic() {
    musicOn = !musicOn;
    try { localStorage.setItem("balkan-civ-music", musicOn ? "1" : "0"); } catch (e) { /* ignore */ }
    if (musicOn) startMusic(); else stopMusic();
    return musicOn;
  }

  return { play, toggleMute, startMusic, stopMusic, toggleMusic,
    get muted() { return muted; }, get musicOn() { return musicOn; } };
})();
