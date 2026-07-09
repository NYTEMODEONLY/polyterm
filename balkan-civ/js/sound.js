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

  return { play, toggleMute, get muted() { return muted; } };
})();
