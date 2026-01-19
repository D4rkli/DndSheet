// =====================
// Telegram WebApp init
// =====================
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

// =====================
// DOM
// =====================
const statusEl = document.getElementById("status");
const listScreen = document.getElementById("listScreen");
const characterScreen = document.getElementById("characterScreen");
const itemEditor = document.getElementById("itemEditor");
const bottomNav = document.getElementById("bottomNav");

const hpEditor = document.getElementById("hpEditor");
const hpEditorMeta = document.getElementById("hpEditorMeta");
const hpMaxInput = document.getElementById("hpMaxInput");
const hpNowInput = document.getElementById("hpNowInput");
const hpPerLevelInput = document.getElementById("hpPerLevelInput");

const listEl = document.getElementById("chars");
const createBtn = document.getElementById("createBtn");
const newName = document.getElementById("newName");

// =====================
// STATE
// =====================
const INIT_DATA = tg.initData || "";

let activeResource = null; // "hp" | "mana" | "energy"
let activeCharacterId = null;
let currentCharacter = null;
let activeItemId = null;
let editMode = false;

if (!INIT_DATA) {
  document.body.innerHTML = "<p>Открой приложение из Telegram</p>";
  throw new Error("No Telegram initData");
}

// =====================
// API helper
// =====================
async function api(path, opts = {}) {
  const res = await fetch(path, {
    method: opts.method || "GET",
    headers: {
      "Content-Type": "application/json",
      "X-TG-INIT-DATA": INIT_DATA,
    },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });

  if (!res.ok) {
    throw new Error(await res.text());
  }

  return res.json();
}

// =====================
// INIT
// =====================
loadCharacters();

// =====================
// LOAD CHARACTERS
// =====================
async function loadCharacters() {
  showOnly("list");

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
    li.onclick = () => openCharacter(c.id);
    listEl.appendChild(li);
  }
}

// =====================
// CREATE CHARACTER
// =====================
createBtn.onclick = async () => {
  const name = newName.value.trim();
  if (!name) return;

  await api("/api/characters", {
    method: "POST",
    body: { name },
  });

  newName.value = "";
  loadCharacters();
};

// =====================
// OPEN CHARACTER
// =====================
async function openCharacter(id) {
  activeCharacterId = id;
  editMode = false;

  currentCharacter = await api(`/api/characters/${id}`);

  showOnly("character");
  bottomNav.style.display = "flex";

  renderCharacter();
  openTab("stats");
  renderResources();
}

function backToList() {
  activeCharacterId = null;
  currentCharacter = null;
  editMode = false;

  bottomNav.style.display = "none";
  showOnly("list");
  loadCharacters();
}

// =====================
// RENDER CHARACTER
// =====================
function renderCharacter() {
  const c = currentCharacter;

  document.getElementById("charTitle").textContent = c.name;
  document.getElementById("charMeta").textContent =
    `${c.race || "—"} • ${c.klass || "—"} • ур. ${c.level || 1}`;

  // 👇 ВОТ ЭТОГО НЕ ХВАТАЛО
  document.getElementById("viewName").textContent = c.name;
  document.getElementById("viewRace").textContent = c.race || "—";
  document.getElementById("viewClass").textContent = c.klass || "—";
  document.getElementById("viewLevel").textContent = c.level || 1;

  renderResources();   // 👈 КЛЮЧ
  renderStats();
}

// =====================
// STATS TAB
// =====================
function renderStats() {
  const el = document.getElementById("tab-stats");

  if (!editMode) {
    el.innerHTML = `
      <p><b>Имя:</b> ${currentCharacter.name}</p>
      <p><b>Раса:</b> ${currentCharacter.race || "—"}</p>
      <p><b>Класс:</b> ${currentCharacter.klass || "—"}</p>
      <p><b>Уровень:</b> ${currentCharacter.level || 1}</p>
      <button onclick="enableEdit()">✏️ Редактировать</button>
    `;
  } else {
    el.innerHTML = `
      <input id="edit-name" value="${currentCharacter.name}">
      <input id="edit-race" value="${currentCharacter.race || ""}">
      <input id="edit-klass" value="${currentCharacter.klass || ""}">
      <input id="edit-level" type="number" value="${currentCharacter.level || 1}">
      <button onclick="saveStats()">💾 Сохранить</button>
      <button onclick="cancelEdit()">❌ Отмена</button>
    `;
  }
}

function enableEdit() {
  editMode = true;
  renderStats();
}

function cancelEdit() {
  editMode = false;
  renderStats();
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
    body: payload,
  });

  editMode = false;
  renderCharacter();
}

// =====================
// TABS
// =====================
function openTab(name) {
  if (!activeCharacterId) return;

  document.querySelectorAll(".tab-content").forEach(el => el.style.display = "none");
  document.querySelectorAll(".bottom-nav button").forEach(b => b.classList.remove("active"));

  document.getElementById(`tab-${name}`).style.display = "block";
  document.getElementById(`nav-${name}`).classList.add("active");

  if (name === "inventory") loadInventory();
}

// =====================
// INVENTORY
// =====================
async function loadInventory() {
  const list = document.getElementById("inventoryList");
  list.innerHTML = "<li class='muted'>Загрузка…</li>";

  const items = await api(`/api/characters/${activeCharacterId}/items`);
  list.innerHTML = "";

  if (!items.length) {
    list.innerHTML = "<li class='muted'>Пусто</li>";
    return;
  }

  for (const it of items) {
    const li = document.createElement("li");
    li.innerHTML = `
      <b>${it.name}</b>
      <div class="muted">${it.description || ""}</div>
      <button onclick='openItemEditor(${JSON.stringify(it)})'>⚙️</button>
    `;
    list.appendChild(li);
  }
}

// =====================
// ITEM EDITOR
// =====================
function openItemEditor(item = null) {
  activeItemId = item?.id || null;

  showOnly("item");
  bottomNav.style.display = "none";

  document.getElementById("itemEditorTitle").textContent =
    item ? "Редактировать предмет" : "Новый предмет";

  document.getElementById("editItemName").value = item?.name || "";
  document.getElementById("editItemDesc").value = item?.description || "";
  document.getElementById("editItemStats").value = item?.stats || "";

  document.getElementById("deleteItemBtn").style.display =
    item ? "block" : "none";
}

function closeItemEditor() {
  activeItemId = null;
  showOnly("character");
  bottomNav.style.display = "flex";
  openTab("inventory");
}

function openHpEditor() {
  if (!currentCharacter) return;

  // закрываем всё и показываем редактор
  showOnly("hp");
  bottomNav.style.display = "none";

  hpEditorMeta.textContent =
    `${currentCharacter.name} • ур. ${currentCharacter.level || 1}`;

  // берём значения (если max ещё нет — считаем max = текущее, как ты делала)
  const hpMax = currentCharacter.hp_max ?? currentCharacter.hp ?? 0;
  const hpNow = currentCharacter.hp ?? 0;

  hpMaxInput.value = hpMax;
  hpNowInput.value = hpNow;

  // прибавка за уровень — пока храним в level_up_rules (как текст/JSON)
  // если пока нет — ставим пусто
  const rules = safeParseJson(currentCharacter.level_up_rules);
  hpPerLevelInput.value = (rules?.hp_per_level ?? "");
}

function openResourceEditor(res) {
  if (!currentCharacter) return;

  activeResource = res;

  const titleMap = { hp: "❤️ HP", mana: "🔵 Мана", energy: "⚡ Энергия" };
  document.getElementById("resourceEditorTitle").textContent = `Настройка: ${titleMap[res]}`;

  const cur = currentCharacter[res] ?? 0;
  const max = currentCharacter[`${res}_max`] ?? 0;
  const per = currentCharacter[`${res}_per_level`] ?? 0;

  document.getElementById("resCurrent").value = cur;
  document.getElementById("resMax").value = max;
  document.getElementById("resPerLevel").value = per;

  showOnly("resource");
  bottomNav.style.display = "none";
}

function closeResourceEditor() {
  activeResource = null;
  showOnly("character");
  bottomNav.style.display = "flex";
  renderResources();
}

function stepResource(delta) {
  const input = document.getElementById("resCurrent");
  const v = Number(input.value || 0) + delta;
  input.value = v;
}

async function saveResource() {
  if (!activeResource) return;

  const res = activeResource;

  const cur = Number(document.getElementById("resCurrent").value || 0);
  const max = Number(document.getElementById("resMax").value || 0);
  const per = Number(document.getElementById("resPerLevel").value || 0);

  const payload = {
    [res]: cur,
    [`${res}_max`]: max,
    [`${res}_per_level`]: per,
  };

  currentCharacter = await api(`/api/characters/${activeCharacterId}`, {
    method: "PATCH",
    body: payload,
  });

  closeResourceEditor();
}

function closeHpEditor() {
  showOnly("character");
  bottomNav.style.display = "flex";
  renderResources(); // обновим отображение
}

async function saveHpSettings() {
  if (!activeCharacterId) return;

  const hpMax = Number(hpMaxInput.value || 0);
  let hpNow = Number(hpNowInput.value || 0);

  if (hpNow > hpMax) hpNow = hpMax;
  if (hpNow < 0) hpNow = 0;

  const hpPerLevel = hpPerLevelInput.value === "" ? null : Number(hpPerLevelInput.value);

  // сохраняем правила в level_up_rules как JSON
  const rules = safeParseJson(currentCharacter.level_up_rules) || {};
  if (hpPerLevel === null || Number.isNaN(hpPerLevel)) {
    delete rules.hp_per_level;
  } else {
    rules.hp_per_level = hpPerLevel;
  }

  const payload = {
    hp: hpNow,
    hp_max: hpMax,
    level_up_rules: JSON.stringify(rules),
  };

  currentCharacter = await api(`/api/characters/${activeCharacterId}`, {
    method: "PATCH",
    body: payload,
  });

  closeHpEditor();
}

async function saveItem() {
  const payload = {
    name: editItemName.value,
    description: editItemDesc.value,
    stats: editItemStats.value,
  };

  if (!activeItemId) {
    await api(`/api/characters/${activeCharacterId}/items`, {
      method: "POST",
      body: payload,
    });
  }

  closeItemEditor();
}

async function deleteItem() {
  if (!confirm("Удалить предмет?")) return;

  await api(`/api/characters/${activeCharacterId}/items/${activeItemId}`, {
    method: "DELETE",
  });

  closeItemEditor();
}

// =====================
// SCREEN SWITCHER
// =====================
function showOnly(name) {
  listScreen.style.display = "none";
  characterScreen.style.display = "none";
  itemEditor.style.display = "none";
  document.getElementById("resourceEditor").style.display = "none";

  if (name === "list") listScreen.style.display = "block";
  if (name === "character") characterScreen.style.display = "block";
  if (name === "item") itemEditor.style.display = "block";
  if (name === "resource") document.getElementById("resourceEditor").style.display = "block";
}

function renderResources() {
  const c = currentCharacter;

  const hpMax = (c.hp_max ?? 0) > 0 ? c.hp_max : c.hp;
  const manaMax = (c.mana_max ?? 0) > 0 ? c.mana_max : c.mana;
  const energyMax = (c.energy_max ?? 0) > 0 ? c.energy_max : c.energy;

  setBar("hp", c.hp ?? 0, hpMax ?? 0);
  setBar("mana", c.mana ?? 0, manaMax ?? 0);
  setBar("energy", c.energy ?? 0, energyMax ?? 0);
}

function setBar(type, value, max) {
  const safeMax = max > 0 ? max : 1;
  const percent = Math.max(0, Math.min(100, (value / safeMax) * 100));

  document.getElementById(`${type}Bar`).style.width = `${percent}%`;

  const text = `${value} / ${max > 0 ? max : value}`;
  document.getElementById(`${type}Text`).textContent = text;
  document.getElementById(`${type}TextOnBar`).textContent = text;
}

async function spendResources({ hp = 0, mana = 0, energy = 0 }) {
  const payload = {
    hp: currentCharacter.hp - hp,
    mana: currentCharacter.mana - mana,
    energy: currentCharacter.energy - energy
  };

  currentCharacter = await api(
    `/api/characters/${activeCharacterId}`,
    { method: "PATCH", body: payload }
  );

  renderResources();
}

async function changeResource(type, delta) {
  if (!currentCharacter) return;

  const field = type;
  const maxField = `${type}_max`;

  const current = currentCharacter[field] ?? 0;
  const max = currentCharacter[maxField] ?? current;

  const next = Math.max(0, Math.min(max, current + delta));

  currentCharacter = await api(
    `/api/characters/${activeCharacterId}`,
    {
      method: "PATCH",
      body: { [field]: next }
    }
  );

  renderResources();
}

async function editResource(type) {
  const current = currentCharacter[type] ?? 0;

  // ВАЖНО: если max = 0 или undefined — разрешаем ввод
  const rawMax = currentCharacter[`${type}_max`];
  const max = rawMax && rawMax > 0 ? rawMax : 999999;

  const value = prompt(
    `Введите ${type.toUpperCase()} (0 – ${max})`,
    current
  );

  if (value === null) return;

  const num = Number(value);
  if (Number.isNaN(num)) return;

  const safe = Math.max(0, Math.min(max, num));

  currentCharacter = await api(
    `/api/characters/${activeCharacterId}`,
    {
      method: "PATCH",
      body: { [type]: safe }
    }
  );

  renderResources();
}

function safeParseJson(str) {
  try {
    if (!str) return null;
    return JSON.parse(str);
  } catch {
    return null;
  }
}
