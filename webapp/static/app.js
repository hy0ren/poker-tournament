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
  playBtn: document.getElementById("play-btn"),
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
  playPanel: document.getElementById("play-panel"),
  playPrompt: document.getElementById("play-prompt"),
  playerHandCards: document.getElementById("player-hand-cards"),
  foldBtn: document.getElementById("fold-btn"),
  checkCallBtn: document.getElementById("check-call-btn"),
  raiseAmount: document.getElementById("raise-amount"),
  raiseBtn: document.getElementById("raise-btn"),
  allInBtn: document.getElementById("all-in-btn"),
};

const MAX_BOTS = 23;
const PLAY_EVENT_DELAY_MS = 520;
const REVEAL_EVENT_DELAY_MS = 1500;
let bots = [];
let replayEvents = [];
let currentEventIndex = 0;
let playTimer = null;
let isBusy = false;
let isPlayAnimating = false;
let playAnimationTimer = null;
let playSessionId = null;
let pendingAction = null;

loadBots();
wireEvents();
renderEmptyTable();
renderPlayControls();

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
  els.playBtn.addEventListener("click", startPlaySession);
  els.batchBtn.addEventListener("click", runBatch);
  els.foldBtn.addEventListener("click", () => submitPlayerAction("fold"));
  els.checkCallBtn.addEventListener("click", () => submitPlayerAction(pendingAction?.state?.call_amount ? "call" : "check"));
  els.raiseBtn.addEventListener("click", () => submitPlayerAction("raise"));
  els.allInBtn.addEventListener("click", submitAllInAction);
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
  els.selectAll.textContent = bots.length > MAX_BOTS ? `Select ${MAX_BOTS}` : "Select Lineup";
  if (!bots.length) {
    els.botList.innerHTML = `<p class="muted">No bots found.</p>`;
    updateBotCount();
    updateButtonStates();
    return;
  }

  let selectedByDefault = 0;
  for (const bot of [...bots].sort(compareBots)) {
    const checked = selectedByDefault < MAX_BOTS;
    els.botList.appendChild(createBotRow(bot, checked));
    if (checked) selectedByDefault += 1;
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
    option.textContent = bot.name;
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

function compareBots(a, b) {
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

async function startPlaySession() {
  const selected = selectedBots();
  if (!validateSelectedCount(selected, 1)) return;

  const body = playRequestBody(selected);
  if (!body) return;

  stopPlayback();
  clearReplay();
  playSessionId = null;
  pendingAction = null;
  isBusy = true;
  updateButtonStates();
  setStatus("Starting play session");

  try {
    const response = await fetch("/api/play/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(formatError(data.detail) || `HTTP ${response.status}`);
    playSessionId = data.session_id;
    applyPlayPayload(data);
    setStatus(data.done ? "Play session complete" : "Your turn", data.done ? "success" : "");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    isBusy = false;
    updateButtonStates();
  }
}

async function submitPlayerAction(action, amountOverride = null) {
  if (!playSessionId || !pendingAction) return;
  const amount = amountOverride !== null ? amountOverride : action === "raise" ? numberValue(els.raiseAmount) : 0;
  isBusy = true;
  updateButtonStates();
  setStatus("Playing hand");

  try {
    const response = await fetch(`/api/play/${encodeURIComponent(playSessionId)}/act`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, amount }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(formatError(data.detail) || `HTTP ${response.status}`);
    applyPlayPayload(data);
    setStatus(data.done ? "Play session complete" : "Your turn", data.done ? "success" : "");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    isBusy = false;
    updateButtonStates();
  }
}

function submitAllInAction() {
  if (!pendingAction) return;
  const state = pendingAction.state;
  const allInTo = (state.my_bet || 0) + (state.stack || 0);
  const action = state.stack <= state.call_amount ? "call" : "raise";
  submitPlayerAction(action, allInTo);
}

function applyPlayPayload(data) {
  const previousEventCount = replayEvents.length;
  replayEvents = data.events || [];
  currentEventIndex = Math.max(0, replayEvents.length - 1);
  els.eventRange.max = Math.max(0, replayEvents.length - 1);
  els.eventRange.value = String(currentEventIndex);
  pendingAction = data.pending || null;
  renderStandings({ standings: data.standings, hands_played: data.hands_played, config: { mode: "play", small_blind: numberValue(els.smallBlind), big_blind: numberValue(els.bigBlind) } });

  const liveSnapshot = data.snapshot || replayEvents[currentEventIndex]?.snapshot;
  const displaySnapshot = humanIsStillIn(liveSnapshot) ? liveSnapshot : lastSnapshotBeforeReveal(liveSnapshot);
  const newEvents = replayEvents.slice(previousEventCount);
  const shouldAnimateRunout = humanIsStillIn(liveSnapshot) && newEvents.length > 1 && newEvents.some((event) => ["street", "showdown", "reveal", "win"].includes(event.type));
  if (shouldAnimateRunout) {
    animatePlayRunout(previousEventCount, liveSnapshot, data.done);
    return;
  }

  if (displaySnapshot) {
    renderSnapshot(displaySnapshot);
  } else {
    renderCurrentEvent();
  }
  const lastEvent = replayEvents[currentEventIndex];
  els.eventMessage.textContent = pendingAction
    ? "Your turn."
    : lastEvent?.message || (data.done ? "Play session complete." : "Playing hand.");
  renderPlayControls();
  updateButtonStates();
}

function humanIsStillIn(snapshot) {
  const me = snapshot?.players?.find((player) => player.name === "You");
  return Boolean(me && !me.folded);
}

function lastSnapshotBeforeReveal(fallbackSnapshot) {
  for (let index = replayEvents.length - 1; index >= 0; index -= 1) {
    const event = replayEvents[index];
    if (!event?.snapshot || ["showdown", "reveal", "play_complete"].includes(event.type)) continue;
    if (event.snapshot.players?.some((player) => player.name === "You" && player.folded)) {
      currentEventIndex = index;
      els.eventRange.value = String(currentEventIndex);
      return event.snapshot;
    }
  }
  return fallbackSnapshot;
}

function animatePlayRunout(startIndex, liveSnapshot, done) {
  stopPlayAnimation();
  isPlayAnimating = true;
  renderPlayControls();
  updateButtonStates();

  let index = Math.max(0, startIndex);
  const lastIndex = Math.max(0, replayEvents.length - 1);
  const step = () => {
    currentEventIndex = Math.min(index, lastIndex);
    const event = replayEvents[currentEventIndex];
    els.eventRange.value = String(currentEventIndex);
    const isRevealMoment = event && ["showdown", "reveal"].includes(event.type);
    els.eventMessage.textContent = isRevealMoment
      ? "Cards revealed."
      : event?.message || "";
    if (event?.snapshot) renderSnapshot(event.snapshot);

    if (index >= lastIndex) {
      isPlayAnimating = false;
      playAnimationTimer = null;
      if (liveSnapshot) renderSnapshot(liveSnapshot);
      els.eventMessage.textContent = pendingAction
        ? "Your turn."
        : done
          ? "Play session complete."
          : event?.message || "Playing hand.";
      renderPlayControls();
      updateButtonStates();
      return;
    }
    index += 1;
    const delay = isRevealMoment ? REVEAL_EVENT_DELAY_MS : PLAY_EVENT_DELAY_MS;
    playAnimationTimer = window.setTimeout(step, delay);
  };
  step();
}

function stopPlayAnimation() {
  if (playAnimationTimer) {
    window.clearTimeout(playAnimationTimer);
    playAnimationTimer = null;
  }
  isPlayAnimating = false;
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

function playRequestBody(selected) {
  const body = {
    bots: selected,
    starting_chips: numberValue(els.chips),
    small_blind: numberValue(els.smallBlind),
    big_blind: numberValue(els.bigBlind),
    num_hands: numberValue(els.hands),
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

function validateSelectedCount(selected, minimum = 2) {
  if (selected.length < minimum) {
    setStatus(minimum === 1 ? "Pick at least one bot" : "Pick at least two bots", "error");
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
  renderPlayerHand(snapshot.players || []);
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
    if (player.name === "You") seat.classList.add("is-human");

    const stateLabel = player.folded ? "Folded" : player.all_in ? "All-in" : "In";
    const stackLabel = `${formatNumber(player.stack)} chips`;
    const betLabel = player.all_in
      ? `All-in ${formatNumber(player.total_bet || player.bet || 0)}`
      : player.bet
        ? `Bet ${formatNumber(player.bet)}`
        : "";
    seat.innerHTML = `
      <div class="seat-name">${escapeHtml(player.name)}</div>
      <div class="seat-badges">
        <div class="seat-state">${escapeHtml(stateLabel)}</div>
        <div class="dealer-chip">D</div>
      </div>
      <div class="seat-cards"></div>
      <div class="seat-meta">${escapeHtml(stackLabel)}</div>
      <div class="seat-bet">${escapeHtml(betLabel)}</div>
    `;
    const showBacks = player.name !== "You" && !player.folded && !(player.cards || []).length;
    renderCards(seat.querySelector(".seat-cards"), player.cards || [], 2, showBacks);
    els.seatLayer.appendChild(seat);
  });
}

function seatPosition(index, total) {
  const narrow = window.matchMedia("(max-width: 760px)").matches;
  const full = total > 12;
  const ultra = total > 16;
  const radiusX = narrow ? (ultra ? 36 : full ? 35 : 32) : ultra ? 46 : full ? 45 : 43;
  const radiusY = narrow ? (ultra ? 38 : full ? 37 : 34) : ultra ? 43 : full ? 42 : 40;
  const centerY = narrow ? 54 : 50;
  const angle = -90 + (360 / total) * index;
  const radians = (angle * Math.PI) / 180;
  return {
    x: 50 + Math.cos(radians) * radiusX,
    y: centerY + Math.sin(radians) * radiusY,
  };
}

function renderPlayerHand(players) {
  const me = players.find((player) => player.name === "You");
  renderCards(els.playerHandCards, me?.cards || [], 2);
}

function renderCards(container, cards, slots, faceDown = false) {
  container.innerHTML = "";
  for (let index = 0; index < slots; index += 1) {
    const card = cards[index];
    const node = document.createElement("div");
    node.className = "card";
    if (faceDown) {
      node.classList.add("is-back");
      node.setAttribute("aria-label", "Face-down card");
    } else if (!card) {
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

function renderPlayControls() {
  const state = pendingAction?.state;
  const canAct = Boolean(state);
  const callAmount = state?.call_amount || 0;
  const stack = state?.stack || 0;
  const minRaise = state?.min_raise || 0;
  const maxRaise = (state?.my_bet || 0) + stack;

  els.playPanel.classList.toggle("is-active", canAct);
  els.playPrompt.textContent = canAct
    ? callAmount
      ? `Call ${formatNumber(callAmount)} to continue.`
      : "You can check or raise."
    : playSessionId
      ? "Waiting for the next hand or session result."
      : "Start a play session to take a seat at the table.";
  els.checkCallBtn.textContent = callAmount ? `Call ${formatNumber(callAmount)}` : "Check";
  els.raiseAmount.min = String(minRaise);
  els.raiseAmount.max = String(maxRaise);
  if (canAct) {
    els.raiseAmount.value = String(Math.min(maxRaise, Math.max(minRaise, callAmount ? minRaise : state.big_blind)));
  }
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
  stopPlayAnimation();
  replayEvents = [];
  currentEventIndex = 0;
  playSessionId = null;
  pendingAction = null;
  renderPlayControls();
  stopPlayback();
}

function updateButtonStates() {
  const selected = selectedBots();
  const validSelection = selected.length >= 2 && selected.length <= MAX_BOTS;
  const validPlaySelection = selected.length >= 1 && selected.length <= MAX_BOTS - 1;
  const hasReplay = replayEvents.length > 0;
  const atStart = currentEventIndex <= 0;
  const atEnd = !hasReplay || currentEventIndex >= replayEvents.length - 1;

  els.runBtn.disabled = isBusy || !validSelection;
  els.playBtn.disabled = isBusy || !validPlaySelection;
  els.batchBtn.disabled = isBusy || !validSelection;
  els.prevEvent.disabled = !hasReplay || atStart;
  els.nextEvent.disabled = !hasReplay || atEnd;
  els.playToggle.disabled = !hasReplay || atEnd;
  els.eventRange.disabled = !hasReplay;
  els.foldBtn.disabled = isBusy || isPlayAnimating || !pendingAction;
  els.checkCallBtn.disabled = isBusy || isPlayAnimating || !pendingAction;
  els.raiseBtn.disabled = isBusy || isPlayAnimating || !pendingAction || !(pendingAction.legal_actions || []).includes("raise");
  els.allInBtn.disabled = isBusy || isPlayAnimating || !pendingAction;
  els.raiseAmount.disabled = els.raiseBtn.disabled;
}
