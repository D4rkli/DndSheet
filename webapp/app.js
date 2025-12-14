// =====================
// Telegram WebApp init
// =====================
const tg = window.Telegram.WebApp;

tg.ready();
tg.expand();

const statusEl = document.getElementById("status");
const listEl = document.getElementById("chars");
const createBtn = document.getElementById("createBtn");
const newName = document.getElementById("newName");

console.log("tg.initData:", tg.initData);
console.log("tg.initDataUnsafe:", tg.initDataUnsafe);


// =====================
// INIT DATA (ОБЯЗАТЕЛЬНО)
// =====================
const INIT_DATA = tg.initData || "";

let activeCharacterId = null;
let currentCharacter = null;
let editMode = false;

if (!tg || !INIT_DATA) {
  document.body.innerHTML = `
    <div style="padding:16px;color:#aaa">
      Открой WebApp из Telegram
    </div>
  `;
  throw new Error("No Telegram initData");
}

// =====================
// API helper (ЕДИНСТВЕННЫЙ)
// =====================
async function api(path, opts = {}) {
  const res = await fetch(path, {
    method: opts.method || "GET",
    headers: {
      "Content-Type": "application/json",
      "X-TG-INIT-DATA": INIT_DATA
    },
    body: opts.body ? JSON.stringify(opts.body) : undefined
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }

  return res.json();
}

// =====================
// Load profile + characters
// =====================
async function loadCharacters() {
  statusEl.textContent = "Загружаю профиль…";

  const me = await api("/api/me");
  statusEl.textContent =
    `Привет, ${me.tg.first_name || "игрок"}! DM: ${me.is_dm ? "да" : "нет"}`;

  const chars = await api("/api/characters");

  listEl.innerHTML = "";

  if (!chars.length) {
    listEl.innerHTML = "<li class='muted'>Нет персонажей</li>";
    return;
  }

  for (const c of chars) {
    const li = document.createElement("li");
    li.textContent = `${c.name} (ур. ${c.level || 1})`;
    li.style.cursor = "pointer";

    // 👇 ВАЖНО: НЕ location.href
    li.onclick = () => openCharacter(c.id);

    listEl.appendChild(li);
  }
}

// =====================
// Create character
// =====================
createBtn.onclick = async () => {
  const name = newName.value.trim();
  if (!name) return;

  await api("/api/characters", {
    method: "POST",
    body: { name }
  });

  newName.value = "";
  loadCharacters();
};

// =====================
// Initial load
// =====================
loadCharacters().catch(err => {
  console.error(err);
  statusEl.textContent = "Ошибка: " + err.message;
});

async function openCharacter(id) {
  activeCharacterId = id;

  const c = await api(`/api/characters/${id}`);

  // скрываем список
  document.getElementById("listScreen").style.display = "none";
  document.getElementById("characterScreen").style.display = "block";

  renderCharacter();
}

function backToList() {
  activeCharacterId = null;
  document.getElementById("characterScreen").style.display = "none";
  document.getElementById("listScreen").style.display = "block";
  loadCharacters();
}

function renderCharacter() {
  const c = currentCharacter;

  document.getElementById("charTitle").textContent = c.name;
  document.getElementById("charMeta").textContent =
    `${c.race || "—"} • ${c.klass || "—"} • ур. ${c.level || 1}`;

  renderStatsTab();
}

function renderCharacter() {
  const c = currentCharacter;

  document.getElementById("charTitle").textContent = c.name;
  document.getElementById("charMeta").textContent =
    `${c.race || "—"} • ${c.klass || "—"} • ур. ${c.level || 1}`;

  renderStatsTab();
}

function renderStatsEdit(el) {
  el.innerHTML = `
    <div class="field">
      <label>Имя</label>
      <input id="edit-name" value="${currentCharacter.name}">
    </div>

    <div class="field">
      <label>Раса</label>
      <input id="edit-race" value="${currentCharacter.race || ""}">
    </div>

    <div class="field">
      <label>Класс</label>
      <input id="edit-klass" value="${currentCharacter.klass || ""}">
    </div>

    <div class="field">
      <label>Уровень</label>
      <input id="edit-level" type="number" value="${currentCharacter.level || 1}">
    </div>

    <div class="actions">
      <button onclick="saveStats()">💾 Сохранить</button>
      <button onclick="cancelEdit()">❌ Отмена</button>
    </div>
  `;
}

function enableEdit() {
  editMode = true;
  renderStatsTab();
}

function cancelEdit() {
  editMode = false;
  renderStatsTab();
}

async function saveStats() {
  const payload = {
    name: document.getElementById("edit-name").value,
    race: document.getElementById("edit-race").value,
    klass: document.getElementById("edit-klass").value,
    level: Number(document.getElementById("edit-level").value),
  };

  currentCharacter = await api(`/api/characters/${activeCharacterId}`, {
    method: "PATCH",
    body: payload
  });

  editMode = false;
  renderCharacter();
}
