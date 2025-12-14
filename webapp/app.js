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
let activeItemId = null;
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
  currentCharacter = c;

  // скрываем список
  document.getElementById("listScreen").style.display = "none";
  document.getElementById("characterScreen").style.display = "block";

  renderCharacter();
  openTab("stats");
}

function backToList() {
  activeCharacterId = null;
  document.getElementById("characterScreen").style.display = "none";
  document.getElementById("bottomNav").style.display = "none";
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

function renderStatsTab() {
  const view = document.getElementById("tab-stats");

  if (!editMode) {
    view.innerHTML = `
      <p><b>Имя:</b> ${currentCharacter.name}</p>
      <p><b>Раса:</b> ${currentCharacter.race || "—"}</p>
      <p><b>Класс:</b> ${currentCharacter.klass || "—"}</p>
      <p><b>Уровень:</b> ${currentCharacter.level || 1}</p>

      <button onclick="enableEdit()">✏️ Редактировать</button>
    `;
  } else {
    renderStatsEdit(view);
  }
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

function openTab(name) {
  // скрываем все вкладки
  document.querySelectorAll(".tab-content").forEach(el => {
    el.style.display = "none";
  });

  // убираем active у всех кнопок навигации
  document.querySelectorAll(".bottom-nav button").forEach(btn => {
    btn.classList.remove("active");
  });

  // показываем нужную вкладку
  document.getElementById(`tab-${name}`).style.display = "block";

  // подсвечиваем кнопку
  document.getElementById(`nav-${name}`)?.classList.add("active");

  // если инвентарь — грузим предметы
  if (name === "inventory") {
    loadInventory();
  }
}

async function loadInventory() {
  const items = await api(`/api/characters/${activeCharacterId}/items`);

  const list = document.getElementById("inventoryList");
  list.innerHTML = "";

  if (!items.length) {
    list.innerHTML = "<li class='muted'>Инвентарь пуст</li>";
    return;
  }

  for (const i of items) {
    const li = document.createElement("li");
    li.className = "item";

    li.innerHTML = `
      <b>${i.name}</b>
      <div class="muted">${i.description || ""}</div>
      <pre>${i.stats || ""}</pre>
      <button onclick="deleteItem(${i.id})">❌</button>
    `;

    list.appendChild(li);
  }
}

async function addItem() {
  const name = document.getElementById("itemName").value.trim();
  const desc = document.getElementById("itemDesc").value.trim();
  const stats = document.getElementById("itemStats").value.trim();

  if (!name) return alert("Название обязательно");

  await api(`/api/characters/${activeCharacterId}/items`, {
    method: "POST",
    body: {
      name,
      description: desc,
      stats
    }
  });

  document.getElementById("itemName").value = "";
  document.getElementById("itemDesc").value = "";
  document.getElementById("itemStats").value = "";

  loadInventory();
}

async function deleteItem(itemId) {
  if (!confirm("Удалить предмет?")) return;

  await api(`/api/characters/${activeCharacterId}/items/${itemId}`, {
    method: "DELETE"
  });

  loadInventory();
}

function openItemEditor(item = null) {
  activeItemId = item?.id || null;

  document.getElementById("characterScreen").style.display = "none";
  document.getElementById("itemEditor").style.display = "block";
  document.getElementById("bottomNav").style.display = "none";
  document.getElementById("addItemFab").style.display = "none";

  document.getElementById("itemEditorTitle").textContent =
    item ? "Редактировать предмет" : "Новый предмет";

  document.getElementById("itemName").value = item?.name || "";
  document.getElementById("itemDesc").value = item?.description || "";
  document.getElementById("itemStats").value = item?.stats || "";

  document.getElementById("deleteItemBtn").style.display =
    item ? "block" : "none";
}

function closeItemEditor() {
  activeItemId = null;

  document.getElementById("itemEditor").style.display = "none";
  document.getElementById("characterScreen").style.display = "block";
  document.getElementById("bottomNav").style.display = "flex";
  document.getElementById("addItemFab").style.display = "block";

  openTab("inventory");
}

async function saveItem() {
  const payload = {
    name: itemName.value,
    description: itemDesc.value,
    stats: itemStats.value
  };

  if (activeItemId) {
    // позже PATCH (если захочешь)
  } else {
    await api(`/api/characters/${activeCharacterId}/items`, {
      method: "POST",
      body: payload
    });
  }

  closeItemEditor();
  loadInventory();
}

async function deleteItem() {
  if (!activeItemId) return;

  if (!confirm("Удалить предмет?")) return;

  await api(`/api/characters/${activeCharacterId}/items/${activeItemId}`, {
    method: "DELETE"
  });

  closeItemEditor();
  loadInventory();
}

async function loadInventory() {
  const items = await api(`/api/characters/${activeCharacterId}/items`);
  const list = document.getElementById("inventoryList");

  list.innerHTML = "";

  if (!items.length) {
    list.innerHTML = "<li class='muted'>Инвентарь пуст</li>";
    return;
  }

  for (const i of items) {
    const li = document.createElement("li");
    li.innerHTML = `<b>${i.name}</b><br><small>${i.description || ""}</small>`;
    li.onclick = () => openItemEditor(i);
    list.appendChild(li);
  }
}

document.getElementById("addItemFab").style.display =
  name === "inventory" ? "block" : "none";

if (name === "inventory") {
  loadInventory();
}

