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

// =====================
// INIT DATA (ОБЯЗАТЕЛЬНО)
// =====================
const INIT_DATA = tg?.initData || "";

let activeCharacterId = null;

if (!tg || !INIT_DATA) {
  document.body.innerHTML =
    "<div style='padding:16px;color:#aaa'>Открой WebApp из Telegram</div>";
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

  // заполняем форму
  document.getElementById("charTitle").textContent = c.name;
  document.getElementById("charName").value = c.name || "";
  document.getElementById("charRace").value = c.race || "";
  document.getElementById("charClass").value = c.klass || "";
  document.getElementById("charLevel").value = c.level || 1;
}

async function saveCharacter() {
  if (!activeCharacterId) return;

  await api(`/api/characters/${activeCharacterId}`, {
    method: "PATCH",
    body: {
      name: document.getElementById("charName").value,
      race: document.getElementById("charRace").value,
      klass: document.getElementById("charClass").value,
      level: Number(document.getElementById("charLevel").value)
    }
  });

  alert("Сохранено 💾");
}

function backToList() {
  activeCharacterId = null;
  document.getElementById("characterScreen").style.display = "none";
  document.getElementById("listScreen").style.display = "block";
  loadCharacters();
}

