"use strict";

const els = {
  status: document.getElementById("status"),
  botList: document.getElementById("bot-list"),
  selectAll: document.getElementById("select-all"),
  clearAll: document.getElementById("clear-all"),
  settingsForm: document.getElementById("settings-form"),
  mode: document.getElementById("mode"),
  hands: document.getElementById("num-hands"),
  chips: document.getElementById("starting-chips"),
  smallBlind: document.getElementById("small-blind"),
  bigBlind: document.getElementById("big-blind"),
  seed: document.getElementById("seed"),
  runBtn: document.getElementById("run-btn"),
  batchRuns: document.getElementById("batch-runs"),
  batchBtn: document.getElementById("batch-btn"),
  handTitle: document.getElementById("hand-title"),
  pot: document.getElementById("pot"),
  community: document.getElementById("community-cards"),
  seatLayer: document.getElementById("seat-layer"),
  eventRange: document.getElementById("event-range"),
  eventMessage: document.getElementById("event-message"),
  prevEvent: document.getElementById("prev-event"),
  nextEvent: document.getElementById("next-event"),
  playToggle: document.getElementById("play-toggle"),
  replaySpeed: document.getElementById("replay-speed"),
  standingsBody: document.getElementById("standings-body"),
  runMeta: document.getElementById("run-meta"),
  batchBody: document.getElementById("batch-body"),
  batchMeta: document.getElementById("batch-meta"),
  codePicker: document.getElementById("code-picker"),
  botCode: document.getElementById("bot-code"),
  botCount: document.getElementById("bot-count"),
};

const MAX_BOTS = 23;
const TIER_ORDER = ["basic", "intermediate", "advanced"];
const TIER_LABELS = {
  basic: "Basic",
  intermediate: "Intermediate",
  advanced: "Advanced",
};
let bots = [];
let replayEvents = [];
let currentEventIndex = 0;
let playTimer = null;
let isBusy = false;

loadBots();
wireEvents();
renderEmptyTable();

async function loadBots() {
  setStatus("Loading bots");
  try {
    const response = await fetch("/api/bots");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    bots = data.bots || [];
    renderBotList();
    renderCodePicker();
    renderEmptyTable();
    updateButtonStates();
    setStatus("Ready");
  } catch (error) {
    setStatus(`Could not load bots: ${error.message}`, "error");
  }
}

function wireEvents() {
  els.runBtn.addEventListener("click", runTournament);
  els.batchBtn.addEventListener("click", runBatch);
  els.selectAll.addEventListener("click", () => setAllBots(true));
  els.clearAll.addEventListener("click", () => setAllBots(false));
  els.prevEvent.addEventListener("click", () => stepReplay(-1));
  els.nextEvent.addEventListener("click", () => stepReplay(1));
  els.playToggle.addEventListener("click", togglePlayback);
  els.replaySpeed.addEventListener("change", () => {
    if (playTimer) {
      stopPlayback();
      startPlayback();
    }
  });
  els.eventRange.addEventListener("input", () => {
    currentEventIndex = Number(els.eventRange.value);
    renderCurrentEvent();
  });
  els.codePicker.addEventListener("change", renderSelectedCode);
  els.botList.addEventListener("change", (event) => {
    enforceBotCap(event.target);
    updateBotRowStates();
    clearReplay();
    renderEmptyTable();
  });
  els.settingsForm.addEventListener("input", () => {
    clearReplay();
    renderEmptyTable();
  });
  window.addEventListener("resize", () => {
    if (replayEvents.length) {
      renderCurrentEvent();
    } else {
      renderEmptyTable();
    }
  });
}

function renderBotList() {
  els.botList.innerHTML = "";
  els.selectAll.textContent = bots.length > MAX_BOTS ? `Select ${MAX_BOTS}` : "Select All";
  if (!bots.length) {
    els.botList.innerHTML = `<p class="muted">No bots found.</p>`;
    updateBotCount();
    updateButtonStates();
    return;
  }

  let selectedByDefault = 0;
  for (const tier of TIER_ORDER) {
    const groupBots = bots.filter((bot) => normalizedTier(bot) === tier);
    if (!groupBots.length) continue;

    const section = document.createElement("div");
    section.className = `bot-tier bot-tier-${tier}`;
    section.innerHTML = `
      <div class="bot-tier-heading">
        <span>${TIER_LABELS[tier]}</span>
        <small>${groupBots.length} bots</small>
      </div>
    `;

    for (const bot of groupBots) {
      const checked = selectedByDefault < MAX_BOTS;
      section.appendChild(createBotRow(bot, checked));
      if (checked) selectedByDefault += 1;
    }
    els.botList.appendChild(section);
  }
  updateBotRowStates();
  updateBotCount();
  updateButtonStates();
}

function createBotRow(bot, checked) {
  const label = document.createElement("label");
  label.className = "bot-row";

  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.value = bot.filename;
  checkbox.checked = checked;

  const text = document.createElement("span");
  text.innerHTML = `<strong>${escapeHtml(bot.name)}</strong><small>${escapeHtml(bot.description)}</small>`;
  label.append(checkbox, text);
  return label;
}

function renderCodePicker() {
  els.codePicker.innerHTML = "";
  for (const bot of [...bots].sort(compareBots)) {
    const option = document.createElement("option");
    option.value = bot.filename;
    option.textContent = `${TIER_LABELS[normalizedTier(bot)]}: ${bot.name}`;
    els.codePicker.appendChild(option);
  }
  renderSelectedCode();
}

function renderSelectedCode() {
  const bot = bots.find((item) => item.filename === els.codePicker.value) || bots[0];
  els.botCode.textContent = bot ? bot.source : "No bot code loaded.";
}

function setAllBots(checked) {
  clearReplay();
  const checkboxes = [...els.botList.querySelectorAll("input[type=checkbox]")];
  checkboxes.forEach((checkbox, index) => {
    checkbox.checked = checked && index < MAX_BOTS;
  });
  updateBotRowStates();
  updateBotCount();
  renderEmptyTable();
  updateButtonStates();
  if (checked && checkboxes.length > MAX_BOTS) {
    setStatus(`Selected the first ${MAX_BOTS} bots`, "success");
  }
}

function selectedBots() {
  return [...els.botList.querySelectorAll("input[type=checkbox]")]
    .filter((checkbox) => checkbox.checked)
    .map((checkbox) => checkbox.value);
}

function normalizedTier(bot) {
  return TIER_ORDER.includes(bot.tier) ? bot.tier : "basic";
}

function compareBots(a, b) {
  const tierDiff = TIER_ORDER.indexOf(normalizedTier(a)) - TIER_ORDER.indexOf(normalizedTier(b));
  if (tierDiff !== 0) return tierDiff;
  return a.name.localeCompare(b.name);
}

async function runTournament() {
  const selected = selectedBots();
  if (!validateSelectedCount(selected)) return;

  const body = tournamentRequestBody(selected);
  if (!body) return;

  stopPlayback();
  isBusy = true;
  updateButtonStates();
  setStatus("Running tournament");

  try {
    const response = await fetch("/api/tournament", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(formatError(data.detail) || `HTTP ${response.status}`);

    replayEvents = data.events || [];
    currentEventIndex = replayEvents.length ? 0 : 0;
    els.eventRange.max = Math.max(0, replayEvents.length - 1);
    els.eventRange.value = String(currentEventIndex);
    renderCurrentEvent();
    renderStandings(data);
    setStatus(`Complete: ${data.hands_played} hands in ${data.duration_ms} ms`, "success");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    isBusy = false;
    updateButtonStates();
  }
}

async function runBatch() {
  const selected = selectedBots();
  if (!validateSelectedCount(selected)) return;

  const body = tournamentRequestBody(selected);
  if (!body) return;
  body.runs = numberValue(els.batchRuns);

  stopPlayback();
  isBusy = true;
  updateButtonStates();
  setStatus(`Running ${body.runs} tournaments`);

  try {
    const response = await fetch("/api/batch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(formatError(data.detail) || `HTTP ${response.status}`);

    renderBatchResults(data);
    setStatus(`Batch complete: ${data.runs} runs in ${data.duration_ms} ms`, "success");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    isBusy = false;
    updateButtonStates();
  }
}

function tournamentRequestBody(selected) {
  const body = {
    bots: selected,
    mode: els.mode.value,
    starting_chips: numberValue(els.chips),
    small_blind: numberValue(els.smallBlind),
    big_blind: numberValue(els.bigBlind),
    num_hands: numberValue(els.hands),
    verbose: false,
  };
  if (els.seed.value.trim() !== "") {
    body.seed = numberValue(els.seed);
  }
  if (body.small_blind >= body.big_blind) {
    setStatus("Small blind must be lower than big blind", "error");
    return null;
  }
  return body;
}

function validateSelectedCount(selected) {
  if (selected.length < 2) {
    setStatus("Pick at least two bots", "error");
    return false;
  }
  if (selected.length > MAX_BOTS) {
    setStatus(`Pick ${MAX_BOTS} or fewer bots`, "error");
    return false;
  }
  return true;
}

function renderCurrentEvent() {
  if (!replayEvents.length) {
    renderEmptyTable();
    return;
  }

  const event = replayEvents[currentEventIndex];
  els.eventRange.value = String(currentEventIndex);
  els.eventMessage.textContent = event.message || "";
  renderSnapshot(event.snapshot);
  updateButtonStates();
}

function renderSnapshot(snapshot) {
  const hand = snapshot.hand_number || 0;
  const street = snapshot.street || "waiting";
  els.handTitle.textContent = hand ? `Hand ${hand} · ${titleCase(street)}` : "No hand loaded";
  els.pot.textContent = `Pot ${formatNumber(snapshot.pot || 0)}`;
  renderCards(els.community, snapshot.community_cards || [], 5);
  renderSeats(snapshot.players || [], snapshot.dealer);
}

function renderSeats(players, dealerName) {
  els.seatLayer.innerHTML = "";
  els.seatLayer.dataset.count = String(players.length);
  els.seatLayer.classList.toggle("is-dense", players.length > 8);
  els.seatLayer.classList.toggle("is-full", players.length > 12);
  els.seatLayer.classList.toggle("is-ultra", players.length > 16);
  const total = Math.max(players.length, 1);
  players.forEach((player, index) => {
    const seat = document.createElement("div");
    seat.className = "seat";
    const position = seatPosition(index, total);
    seat.style.left = `${position.x}%`;
    seat.style.top = `${position.y}%`;

    if (player.folded) seat.classList.add("is-folded");
    if (player.all_in) seat.classList.add("is-all-in");
    if (player.name === dealerName) seat.classList.add("is-dealer");

    const status = player.folded ? "Folded" : player.all_in ? "All-in" : `${formatNumber(player.stack)} chips`;
    seat.innerHTML = `
      <div class="dealer-chip">D</div>
      <div class="seat-name">${escapeHtml(player.name)}</div>
      <div class="seat-cards"></div>
      <div class="seat-meta">${escapeHtml(status)}</div>
      <div class="seat-bet">${player.bet ? `Bet ${formatNumber(player.bet)}` : ""}</div>
    `;
    renderCards(seat.querySelector(".seat-cards"), player.cards || [], 2);
    els.seatLayer.appendChild(seat);
  });
}

function seatPosition(index, total) {
  const narrow = window.matchMedia("(max-width: 760px)").matches;
  const full = total > 12;
  const ultra = total > 16;
  const radiusX = narrow ? (ultra ? 36 : full ? 35 : 32) : ultra ? 46 : full ? 45 : 43;
  const radiusY = narrow ? (ultra ? 46 : full ? 45 : 43) : ultra ? 43 : full ? 42 : 40;
  const angle = -90 + (360 / total) * index;
  const radians = (angle * Math.PI) / 180;
  return {
    x: 50 + Math.cos(radians) * radiusX,
    y: 50 + Math.sin(radians) * radiusY,
  };
}

function renderCards(container, cards, slots) {
  container.innerHTML = "";
  for (let index = 0; index < slots; index += 1) {
    const card = cards[index];
    const node = document.createElement("div");
    node.className = "card";
    if (!card) {
      node.classList.add("is-empty");
      node.textContent = "";
    } else {
      node.classList.add(card.color === "red" ? "is-red" : "is-black");
      node.textContent = card.text;
    }
    container.appendChild(node);
  }
}

function renderStandings(data) {
  els.standingsBody.innerHTML = "";
  for (const row of data.standings) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.rank}</td>
      <td>${escapeHtml(row.name)}</td>
      <td>${formatNumber(row.chips)}</td>
      <td>${escapeHtml(row.status)}</td>
    `;
    els.standingsBody.appendChild(tr);
  }
  const config = data.config;
  els.runMeta.textContent = `${config.mode}, ${data.hands_played} hands, ${config.small_blind}/${config.big_blind}`;
}

function renderBatchResults(data) {
  els.batchBody.innerHTML = "";
  for (const row of data.results) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.rank}</td>
      <td>${escapeHtml(row.name)}</td>
      <td>${formatNumber(row.wins)}</td>
      <td>${Math.round(row.win_rate * 100)}%</td>
      <td>${row.average_rank.toFixed(2)}</td>
    `;
    els.batchBody.appendChild(tr);
  }
  const config = data.config;
  els.batchMeta.textContent = `${data.runs} runs, ${config.mode}, ${config.num_hands} hands each`;
}

function renderEmptyTable() {
  updateBotCount();
  updateButtonStates();
  if (replayEvents.length) return;
  const selected = selectedBots();
  const players = selected.map((filename) => {
    const bot = bots.find((item) => item.filename === filename);
    return {
      name: bot ? bot.name : filename,
      stack: numberValue(els.chips) || 1000,
      bet: 0,
      folded: false,
      all_in: false,
      cards: [],
    };
  });
  els.eventRange.max = 0;
  els.eventRange.value = 0;
  els.eventMessage.textContent = selected.length
    ? "Run a tournament to see the table replay."
    : "Select at least two bots to preview and run a tournament.";
  renderSnapshot({
    hand_number: 0,
    street: "waiting",
    dealer: players[0] ? players[0].name : "",
    pot: 0,
    community_cards: [],
    players,
  });
}

function stepReplay(direction) {
  if (!replayEvents.length) return;
  currentEventIndex = Math.max(
    0,
    Math.min(replayEvents.length - 1, currentEventIndex + direction)
  );
  renderCurrentEvent();
}

function togglePlayback() {
  if (playTimer) {
    stopPlayback();
    return;
  }
  if (!replayEvents.length) return;
  startPlayback();
}

function startPlayback() {
  els.playToggle.textContent = "Ⅱ";
  updateButtonStates();
  playTimer = window.setInterval(() => {
    if (currentEventIndex >= replayEvents.length - 1) {
      stopPlayback();
      return;
    }
    stepReplay(1);
  }, Number(els.replaySpeed.value));
}

function stopPlayback() {
  if (playTimer) {
    window.clearInterval(playTimer);
    playTimer = null;
  }
  els.playToggle.textContent = "▶";
  updateButtonStates();
}

function numberValue(input) {
  return Number(input.value || 0);
}

function setStatus(message, kind = "") {
  els.status.textContent = message;
  els.status.className = `status ${kind}`.trim();
}

function formatError(detail) {
  if (!detail) return "";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || JSON.stringify(item)).join("; ");
  }
  return JSON.stringify(detail);
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString();
}

function titleCase(value) {
  return String(value).replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));
}

function updateBotCount() {
  const count = selectedBots().length;
  els.botCount.textContent = `${count} / ${MAX_BOTS} selected`;
  els.botCount.classList.toggle("is-invalid", count > MAX_BOTS || count < 2);
}

function enforceBotCap(changed) {
  if (!changed || changed.type !== "checkbox" || !changed.checked) return;
  if (selectedBots().length <= MAX_BOTS) return;
  changed.checked = false;
  setStatus(`A Hold'em table is capped at ${MAX_BOTS} bots`, "error");
}

function updateBotRowStates() {
  for (const row of els.botList.querySelectorAll(".bot-row")) {
    const checkbox = row.querySelector("input[type=checkbox]");
    row.classList.toggle("is-selected", Boolean(checkbox && checkbox.checked));
  }
}

function clearReplay() {
  replayEvents = [];
  currentEventIndex = 0;
  stopPlayback();
}

function updateButtonStates() {
  const selected = selectedBots();
  const validSelection = selected.length >= 2 && selected.length <= MAX_BOTS;
  const hasReplay = replayEvents.length > 0;
  const atStart = currentEventIndex <= 0;
  const atEnd = !hasReplay || currentEventIndex >= replayEvents.length - 1;

  els.runBtn.disabled = isBusy || !validSelection;
  els.batchBtn.disabled = isBusy || !validSelection;
  els.prevEvent.disabled = !hasReplay || atStart;
  els.nextEvent.disabled = !hasReplay || atEnd;
  els.playToggle.disabled = !hasReplay || atEnd;
  els.eventRange.disabled = !hasReplay;
}
