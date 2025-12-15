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

const listEl = document.getElementById("chars");
const createBtn = document.getElementById("createBtn");
const newName = document.getElementById("newName");

// =====================
// STATE
// =====================
const INIT_DATA = tg.initData || "";

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
  document.getElementById("charTitle").textContent = currentCharacter.name;
  document.getElementById("charMeta").textContent =
    `${currentCharacter.race || "—"} • ${currentCharacter.klass || "—"} • ур. ${currentCharacter.level || 1}`;

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

  if (name === "list") listScreen.style.display = "block";
  if (name === "character") characterScreen.style.display = "block";
  if (name === "item") itemEditor.style.display = "block";
}

function renderResources() {
  const c = currentCharacter;

  const hp = c.hp ?? 0;
  const mana = c.mana ?? 0;
  const energy = c.energy ?? 0;

  const hpMax = c.hp_max ?? hp || 1;
  const manaMax = c.mana_max ?? mana || 1;
  const energyMax = c.energy_max ?? energy || 1;

  setBar("hp", hp, hpMax);
  setBar("mana", mana, manaMax);
  setBar("energy", energy, energyMax);
}

function setBar(type, value, max) {
  const percent = Math.max(0, Math.min(100, (value / max) * 100));

  document.getElementById(`${type}Bar`).style.width = `${percent}%`;
  document.getElementById(`${type}Text`).textContent =
    `${value} / ${max}`;
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
