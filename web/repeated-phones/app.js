"use strict";

const state = {
  candidates: [],
  filtered: [],
  current: 0,
  audioBuffer: null,
  audioUrl: null,
  playTimer: null,
};

const els = {
  summary: document.getElementById("summary"),
  position: document.getElementById("position"),
  prev: document.getElementById("prev"),
  next: document.getElementById("next"),
  fileName: document.getElementById("fileName"),
  phoneLabel: document.getElementById("phoneLabel"),
  timeRange: document.getElementById("timeRange"),
  words: document.getElementById("words"),
  canvas: document.getElementById("spectrogram"),
  overlay: document.getElementById("overlay"),
  audio: document.getElementById("audio"),
  playWindow: document.getElementById("playWindow"),
  playRepeat: document.getElementById("playRepeat"),
  loop: document.getElementById("loop"),
  filter: document.getElementById("filter"),
  list: document.getElementById("list"),
};

function seconds(value) {
  return `${value.toFixed(3)}s`;
}

function currentItem() {
  return state.filtered[state.current];
}

async function init() {
  const response = await fetch("repeated-phone-candidates.json");
  if (!response.ok) {
    throw new Error(`Could not load candidates: ${response.status}`);
  }
  const payload = await response.json();
  state.candidates = payload.candidates || [];
  state.filtered = state.candidates.slice();
  els.summary.textContent =
    `${state.candidates.length} adjacent repeated-phone candidates`;
  renderList();
  await selectCandidate(0);
}

function renderList() {
  els.list.textContent = "";
  const fragment = document.createDocumentFragment();
  state.filtered.forEach((item, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `candidate${index === state.current ? " active" : ""}`;
    button.dataset.index = String(index);
    button.innerHTML = `
      <span class="name">${item.file}</span>
      <span class="phone">${item.leftLabel} | ${item.rightLabel}</span>
      <span class="time">${seconds(item.start)}-${seconds(item.end)}</span>
    `;
    button.addEventListener("click", () => selectCandidate(index));
    fragment.appendChild(button);
  });
  els.list.appendChild(fragment);
}

function applyFilter() {
  const query = els.filter.value.trim().toLocaleLowerCase();
  state.filtered = !query
    ? state.candidates.slice()
    : state.candidates.filter((item) => {
        return (
          item.file.toLocaleLowerCase().includes(query) ||
          item.phone.toLocaleLowerCase().includes(query) ||
          item.leftLabel.toLocaleLowerCase().includes(query) ||
          item.rightLabel.toLocaleLowerCase().includes(query)
        );
      });
  state.current = Math.min(state.current, Math.max(0, state.filtered.length - 1));
  renderList();
  selectCandidate(state.current);
}

async function selectCandidate(index) {
  if (!state.filtered.length) {
    clearView();
    return;
  }
  state.current = Math.max(0, Math.min(index, state.filtered.length - 1));
  const item = currentItem();
  els.fileName.textContent = item.file;
  els.phoneLabel.textContent = `${item.leftLabel} + ${item.rightLabel}`;
  els.timeRange.textContent = `${seconds(item.start)} - ${seconds(item.end)}`;
  els.words.textContent = item.words.map((word) => word.label).join(" / ") || "-";
  els.position.textContent = `${state.current + 1} / ${state.filtered.length}`;
  els.audio.src = item.audio;
  state.audioUrl = item.audio;
  renderList();
  if (item.audio) {
    await loadAudioBuffer(item.audio);
    els.audio.removeAttribute("aria-disabled");
    els.playWindow.disabled = false;
    els.playRepeat.disabled = false;
  } else {
    state.audioBuffer = null;
    els.audio.removeAttribute("src");
    els.audio.setAttribute("aria-disabled", "true");
    els.playWindow.disabled = true;
    els.playRepeat.disabled = true;
  }
  drawSpectrogram(item);
  drawOverlay(item);
}

function clearView() {
  els.fileName.textContent = "-";
  els.phoneLabel.textContent = "-";
  els.timeRange.textContent = "-";
  els.words.textContent = "-";
  els.position.textContent = "0 / 0";
  els.overlay.textContent = "";
  const ctx = els.canvas.getContext("2d");
  ctx.clearRect(0, 0, els.canvas.width, els.canvas.height);
}

async function loadAudioBuffer(url) {
  if (state.audioBuffer && state.audioUrl === url) {
    return;
  }
  const AudioContext = window.AudioContext || window.webkitAudioContext;
  const audioContext = new AudioContext();
  const response = await fetch(url);
  const bytes = await response.arrayBuffer();
  state.audioBuffer = await audioContext.decodeAudioData(bytes.slice(0));
  await audioContext.close();
}

function drawSpectrogram(item) {
  const canvas = els.canvas;
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.max(640, Math.floor(rect.width * dpr));
  canvas.height = Math.max(280, Math.floor(420 * dpr));

  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  if (!state.audioBuffer) {
    ctx.fillStyle = "#333333";
    ctx.font = `${14 * dpr}px system-ui, sans-serif`;
    ctx.fillText("No WAV available for this candidate", 18 * dpr, 32 * dpr);
    return;
  }

  const sampleRate = state.audioBuffer.sampleRate;
  const channel = state.audioBuffer.getChannelData(0);
  const startSample = Math.max(0, Math.floor(item.windowStart * sampleRate));
  const endSample = Math.min(channel.length, Math.ceil(item.windowEnd * sampleRate));
  const samples = channel.slice(startSample, endSample);
  const fftSize = 1024;
  const hop = 128;
  const bins = fftSize / 2;
  const frames = Math.max(1, Math.floor((samples.length - fftSize) / hop) + 1);
  const image = ctx.createImageData(canvas.width, canvas.height);
  const magnitudes = [];
  let minDb = Infinity;
  let maxDb = -Infinity;
  const windowValues = hann(fftSize);

  for (let frame = 0; frame < frames; frame += 1) {
    const offset = frame * hop;
    const real = new Float32Array(fftSize);
    const imag = new Float32Array(fftSize);
    for (let i = 0; i < fftSize; i += 1) {
      real[i] = (samples[offset + i] || 0) * windowValues[i];
    }
    fft(real, imag);
    const column = new Float32Array(bins);
    for (let bin = 0; bin < bins; bin += 1) {
      const mag = Math.sqrt(real[bin] * real[bin] + imag[bin] * imag[bin]);
      const db = 20 * Math.log10(mag + 1e-8);
      column[bin] = db;
      if (db < minDb) minDb = db;
      if (db > maxDb) maxDb = db;
    }
    magnitudes.push(column);
  }

  const floor = Math.max(minDb, maxDb - 78);
  for (let x = 0; x < canvas.width; x += 1) {
    const frame = Math.min(frames - 1, Math.floor((x / canvas.width) * frames));
    const column = magnitudes[frame];
    for (let y = 0; y < canvas.height; y += 1) {
      const bin = Math.min(
        bins - 1,
        Math.floor((1 - y / canvas.height) * bins)
      );
      const normalized = Math.max(0, Math.min(1, (column[bin] - floor) / (maxDb - floor || 1)));
      const shade = Math.round(255 - normalized * 255);
      const idx = (y * canvas.width + x) * 4;
      image.data[idx] = shade;
      image.data[idx + 1] = shade;
      image.data[idx + 2] = shade;
      image.data[idx + 3] = 255;
    }
  }
  ctx.putImageData(image, 0, 0);
}

function drawOverlay(item) {
  els.overlay.textContent = "";
  const duration = item.windowEnd - item.windowStart;
  const toPercent = (time) => ((time - item.windowStart) / duration) * 100;

  item.segments.forEach((segment) => {
    if (segment.end < item.windowStart || segment.start > item.windowEnd) {
      return;
    }
    const div = document.createElement("div");
    const left = Math.max(0, toPercent(segment.start));
    const right = Math.min(100, toPercent(segment.end));
    const selected = segment.start >= item.start && segment.end <= item.end;
    div.className = `segment${selected ? " selected" : ""}`;
    div.style.left = `${left}%`;
    div.style.width = `${Math.max(0.4, right - left)}%`;
    const label = document.createElement("span");
    label.className = "segment-label";
    label.textContent = segment.label;
    div.appendChild(label);
    els.overlay.appendChild(div);
  });

  const boundary = document.createElement("div");
  boundary.className = "boundary";
  boundary.style.left = `${toPercent(item.boundary)}%`;
  els.overlay.appendChild(boundary);
}

function playRange(start, end) {
  clearInterval(state.playTimer);
  els.audio.currentTime = start;
  els.audio.play();
  state.playTimer = window.setInterval(() => {
    if (els.audio.currentTime >= end) {
      if (els.loop.checked) {
        els.audio.currentTime = start;
      } else {
        els.audio.pause();
        clearInterval(state.playTimer);
      }
    }
  }, 25);
}

function hann(size) {
  const values = new Float32Array(size);
  for (let i = 0; i < size; i += 1) {
    values[i] = 0.5 * (1 - Math.cos((2 * Math.PI * i) / (size - 1)));
  }
  return values;
}

function fft(real, imag) {
  const n = real.length;
  for (let i = 1, j = 0; i < n; i += 1) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) {
      j ^= bit;
    }
    j ^= bit;
    if (i < j) {
      [real[i], real[j]] = [real[j], real[i]];
      [imag[i], imag[j]] = [imag[j], imag[i]];
    }
  }

  for (let len = 2; len <= n; len <<= 1) {
    const angle = (-2 * Math.PI) / len;
    const wlenReal = Math.cos(angle);
    const wlenImag = Math.sin(angle);
    for (let i = 0; i < n; i += len) {
      let wReal = 1;
      let wImag = 0;
      for (let j = 0; j < len / 2; j += 1) {
        const uReal = real[i + j];
        const uImag = imag[i + j];
        const vReal = real[i + j + len / 2] * wReal - imag[i + j + len / 2] * wImag;
        const vImag = real[i + j + len / 2] * wImag + imag[i + j + len / 2] * wReal;
        real[i + j] = uReal + vReal;
        imag[i + j] = uImag + vImag;
        real[i + j + len / 2] = uReal - vReal;
        imag[i + j + len / 2] = uImag - vImag;
        const nextReal = wReal * wlenReal - wImag * wlenImag;
        wImag = wReal * wlenImag + wImag * wlenReal;
        wReal = nextReal;
      }
    }
  }
}

els.prev.addEventListener("click", () => selectCandidate(state.current - 1));
els.next.addEventListener("click", () => selectCandidate(state.current + 1));
els.playWindow.addEventListener("click", () => {
  const item = currentItem();
  if (item) playRange(item.windowStart, item.windowEnd);
});
els.playRepeat.addEventListener("click", () => {
  const item = currentItem();
  if (item) playRange(item.start, item.end);
});
els.filter.addEventListener("input", applyFilter);
window.addEventListener("resize", () => {
  const item = currentItem();
  if (item) {
    drawSpectrogram(item);
    drawOverlay(item);
  }
});
window.addEventListener("keydown", (event) => {
  if (event.target === els.filter) return;
  if (event.key === "ArrowLeft") selectCandidate(state.current - 1);
  if (event.key === "ArrowRight") selectCandidate(state.current + 1);
  if (event.key === " ") {
    event.preventDefault();
    const item = currentItem();
    if (item) playRange(item.start, item.end);
  }
});

init().catch((error) => {
  els.summary.textContent = error.message;
  console.error(error);
});
