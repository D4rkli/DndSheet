// =====================
// Telegram WebApp
// =====================
const tg = window.Telegram?.WebApp;
tg?.ready();
tg?.expand();

const INIT_DATA = tg?.initData || "";

// =====================
// API helper (ЕДИНСТВЕННЫЙ)
// =====================
async function api(path, opts = {}) {
  const res = await fetch(path, {
    method: opts.method || "GET",
    headers: {
      "Content-Type": "application/json",
      "X-TG-INIT-DATA": INIT_DATA,
      ...(opts.headers || {})
    },
    body: opts.body ? JSON.stringify(opts.body) : undefined
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text);
  }

  return res.json();
}

// =====================
// Получаем ID персонажа
// =====================
const params = new URLSearchParams(window.location.search);
const characterId = params.get("id");

if (!characterId) {
  alert("Нет ID персонажа");
  throw new Error("No character id");
}

// =====================
// Элементы
// =====================
const titleEl = document.getElementById("charName");
const nameEl = document.getElementById("name");
const raceEl = document.getElementById("race");
const klassEl = document.getElementById("klass");
const levelEl = document.getElementById("level");
const saveBtn = document.getElementById("saveBtn");

// =====================
// Загрузка персонажа
// =====================
async function loadCharacter() {
  const c = await api(`/api/characters/${characterId}`);

  titleEl.textContent = c.name;
  nameEl.value = c.name || "";
  raceEl.value = c.race || "";
  klassEl.value = c.klass || "";
  levelEl.value = c.level || 1;
}

// =====================
// Сохранение
// =====================
saveBtn.onclick = async () => {
  await api(`/api/characters/${characterId}`, {
    method: "PATCH",
    body: {
      name: nameEl.value,
      race: raceEl.value,
      klass: klassEl.value,
      level: Number(levelEl.value)
    }
  });

  titleEl.textContent = nameEl.value;
  alert("Сохранено 💾");
};

// =====================
loadCharacter().catch(e => alert(e.message));
