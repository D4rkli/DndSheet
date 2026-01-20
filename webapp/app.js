/* global Telegram, bootstrap */

const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
}

const API_BASE = (window.location.origin || ""); // same host as backend static

function tgInitData() {
  return tg?.initData || "";
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  const init = tgInitData();
  if (init) headers.set("X-TG-INIT-DATA", init);

  const res = await fetch(`${API_BASE}/api${path}`, {
    ...options,
    headers,
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`API ${res.status}: ${txt}`);
  }
  return res.json();
}

const el = (id) => document.getElementById(id);

const state = {
  me: null,
  characters: [],
  chId: null,
  sheet: null,
  templates: [],
  activeTemplateId: null,
};

const DEFAULT_TABS = ["main", "stats", "inv", "spells", "abilities", "states", "equip"];

function loadActiveTemplateId() {
  const raw = localStorage.getItem("activeTemplateId");
  const id = raw ? Number(raw) : null;
  return Number.isFinite(id) ? id : null;
}

function setActiveTemplateId(id) {
  state.activeTemplateId = id;
  if (id) localStorage.setItem("activeTemplateId", String(id));
  else localStorage.removeItem("activeTemplateId");
  applyTemplateToUI();
}

function activeTabs() {
  const tpl = state.templates.find((t) => t.id === state.activeTemplateId);
  const tabs = tpl?.config?.tabs;
  return Array.isArray(tabs) && tabs.length ? tabs : DEFAULT_TABS;
}

function applyTemplateToUI() {
  const allowed = new Set(activeTabs());
  document.querySelectorAll("#tabs .nav-link").forEach((b) => {
    const tab = b.dataset.tab;
    const show = allowed.has(tab);
    b.closest("li")?.classList.toggle("d-none", !show);
    updateFab();
  });
  // если текущая вкладка скрыта — прыгнем в main
  const cur = document.querySelector("#tabs .nav-link.active")?.dataset?.tab;
  if (cur && !allowed.has(cur)) {
    tabSwitch("main");
  }
}

function tabsCheckboxesHtml(checkedTabs) {
  const checked = new Set(checkedTabs || DEFAULT_TABS);
  return DEFAULT_TABS
    .map(
      (t) =>
        `<div class="form-check">
          <input class="form-check-input" type="checkbox" id="tpl_tab_${t}" ${checked.has(t) ? "checked" : ""}>
          <label class="form-check-label" for="tpl_tab_${t}">${t}</label>
        </div>`
    )
    .join("");
}

async function renderTemplatesModal() {
  // список
  const root = el("templatesList");
  root.innerHTML = "";
  if (!state.templates || state.templates.length === 0) {
    root.innerHTML = `<div class="muted">Шаблонов нет. Создай ниже.</div>`;
  } else {
    state.templates.forEach((t) => {
      const row = document.createElement("div");
      row.className = "item";
      row.innerHTML = `
        <div class="item-title">${escapeHtml(t.name)}</div>
        <div class="item-sub">Вкладки: ${(t.config?.tabs || DEFAULT_TABS).join(", ")}</div>
        <div class="item-actions d-flex gap-2">
          <button class="btn btn-sm ${t.id === state.activeTemplateId ? "btn-light" : "btn-outline-light"}" data-act="apply">${t.id === state.activeTemplateId ? "Активен" : "Применить"}</button>
          <button class="btn btn-sm btn-outline-danger" data-act="delete">Удалить</button>
        </div>
      `;
      row.querySelector("button[data-act='apply']").addEventListener("click", async () => {
        // apply to current character (server) if selected, so template is attached to sheet
        const id = currentChId();
        if (id) {
          await api(`/characters/${id}/apply-template`, { method: 'POST', body: JSON.stringify({ template_id: t.id }) });
          await loadSheet(false);
        }
        setActiveTemplateId(t.id);
        renderTemplatesModal();
      });
      row.querySelector("button[data-act='delete']").addEventListener("click", async () => {
        if (!confirm(`Удалить шаблон ‘${t.name}’?`)) return;
        await api(`/templates/${t.id}`, { method: "DELETE" });
        await loadTemplates();
        await renderTemplatesModal();
      });
      root.appendChild(row);
    });
  }

  // чекбоксы вкладок для создания
  el("tplTabs").innerHTML = tabsCheckboxesHtml(DEFAULT_TABS);
}

el("btnCreateTpl")?.addEventListener("click", async () => {
  const name = el("tplName").value.trim();
  if (!name) return alert("Название шаблона обязательно");

  const tabs = DEFAULT_TABS.filter((t) => document.getElementById(`tpl_tab_${t}`)?.checked);
  if (tabs.length === 0) return alert("Выбери хотя бы одну вкладку");

  let config = { tabs, version: 1 };

  // Optional: JSON that contains {custom_sections:[...]} or any other keys
  const raw = document.getElementById("tplCustomSections")?.value?.trim();
  if (raw) {
    try {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object") {
        config = { ...config, ...parsed };
      }
    } catch {
      return alert("JSON в ‘Кастомные поля’ не распарсился. Оставь пустым или проверь скобки/кавычки.");
    }
  }

  await api(`/templates`, { method: "POST", body: JSON.stringify({ name, config }) });
  el("tplName").value = "";
  const tcs = document.getElementById("tplCustomSections");
  if (tcs) tcs.value = "";
  await loadTemplates();
  await renderTemplatesModal();
});

function setStatus(text) {
  el("status").textContent = text;
}

function currentChId() {
  return state.chId;
}

function intOrNull(v) {
  if (v === "" || v === null || v === undefined) return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function fillInput(id, value) {
  const node = el(id);
  if (!node) return;
  node.value = value ?? "";
}

function tabSwitch(name) {
  document.querySelectorAll("#tabs .nav-link").forEach((b) => {
    b.classList.toggle("active", b.dataset.tab === name);
  });
  document.querySelectorAll(".tab").forEach((s) => s.classList.add("d-none"));
  el(`tab-${name}`).classList.remove("d-none");
}

function buildStatInputs(containerId, fields) {
  const wrap = el(containerId);
  wrap.innerHTML = "";
  fields.forEach(({ key, label }) => {
    const div = document.createElement("div");
    div.innerHTML = `
      <label class="form-label">${label}</label>
      <input class="form-control" type="number" data-key="${key}" />
    `;
    wrap.appendChild(div);
  });
}

function readStatInputs(containerId) {
  const data = {};
  el(containerId).querySelectorAll("input[data-key]").forEach((input) => {
    const key = input.dataset.key;
    const val = intOrNull(input.value);
    if (val !== null) data[key] = val;
  });
  return data;
}

function fillStatInputs(containerId, source) {
  el(containerId).querySelectorAll("input[data-key]").forEach((input) => {
    const key = input.dataset.key;
    input.value = source?.[key] ?? 0;
  });
}

function renderList(containerId, rows, onDelete, opts = {}) {
  const root = el(containerId);
  root.innerHTML = "";
  if (!rows || rows.length === 0) {
    root.innerHTML = `<div class="muted">Пусто.</div>`;
    return;
  }

  const icon = opts.icon || "bi-dot";
  rows.forEach((r) => {
    const card = document.createElement("div");
    card.className = "item";

    const title = escapeHtml(r.title || r.name || "");
    const preview = escapeHtml(r.preview || "");
    const details = escapeHtml(r.details || r.description || "");

    card.innerHTML = `
      <div class="item-head">
        <div class="min-w-0">
          <div class="item-title">
            <i class="bi ${icon}"></i>
            <span>${title}</span>
          </div>
          ${preview ? `<div class="item-sub">${preview}</div>` : ``}
        </div>

        <div class="d-flex align-items-center gap-2 item-actions">
          <i class="bi bi-chevron-down item-caret"></i>
          <button class="btn btn-sm btn-outline-light" data-act="delete" title="Удалить">
            <i class="bi bi-trash3"></i>
          </button>
        </div>
      </div>

      <div class="item-details d-none">${details}</div>
    `;

    // раскрытие по тапу по карточке (кроме кнопки delete)
    card.addEventListener("click", (e) => {
      const del = e.target.closest("button[data-act='delete']");
      if (del) return;

      const d = card.querySelector(".item-details");
      const caret = card.querySelector(".item-caret");
      const isHidden = d.classList.contains("d-none");
      d.classList.toggle("d-none");
      caret.classList.toggle("bi-chevron-down", isHidden);
      caret.classList.toggle("bi-chevron-up", !isHidden);
    });

    card.querySelector("button[data-act='delete']").addEventListener("click", async (e) => {
      e.stopPropagation();
      await onDelete(r);
    });

    root.appendChild(card);
  });
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll("\"", "&quot;")
    .replaceAll("'", "&#039;");
}

// ===== Modal helpers
const modalEl = el("editModal");
const modal = new bootstrap.Modal(modalEl);
let modalOnSave = null;

// JSON modal (import/export)
const jsonModalEl = el("jsonModal");
const jsonModal = jsonModalEl ? new bootstrap.Modal(jsonModalEl) : null;
let jsonOnAction = null;

function openJsonModal({ title, label, value, hint, extraHtml, actionText, onAction }) {
  if (!jsonModal) return;
  el("jsonModalTitle").textContent = title;
  el("jsonModalLabel").textContent = label || "Данные";
  el("jsonTextarea").value = value ?? "";
  el("jsonHint").textContent = hint ?? "";
  el("jsonExtra").innerHTML = extraHtml ?? "";
  el("jsonActionBtn").textContent = actionText || "Ок";
  jsonOnAction = onAction;
  jsonModal.show();
}

el("jsonActionBtn")?.addEventListener("click", async () => {
  if (!jsonOnAction) return;
  try {
    await jsonOnAction();
    jsonModal.hide();
  } catch (e) {
    alert(e.message);
  }
});

// Templates modal
const templatesModalEl = el("templatesModal");
const templatesModal = templatesModalEl ? new bootstrap.Modal(templatesModalEl) : null;

function openModal(title, bodyHtml, onSave) {
  el("modalTitle").textContent = title;
  el("modalBody").innerHTML = bodyHtml;
  modalOnSave = onSave;
  modal.show();
}

el("modalSave").addEventListener("click", async () => {
  if (!modalOnSave) return;
  try {
    await modalOnSave();
    modal.hide();
  } catch (e) {
    alert(e.message);
  }
});

// ===== UI wiring

document.querySelectorAll("#tabs .nav-link").forEach((btn) => {
  btn.addEventListener("click", () => tabSwitch(btn.dataset.tab));
});

el("btnSync").addEventListener("click", () => loadSheet());

el("btnExport")?.addEventListener("click", async () => {
  const id = currentChId();
  if (!id) return;
  const data = await api(`/characters/${id}/export`);
  const json = JSON.stringify(data, null, 2);
  openJsonModal({
    title: "Экспорт персонажа",
    label: "JSON (можно скопировать / сохранить)",
    value: json,
    hint: "Совет: храни в заметках или кидай другу — потом можно импортировать.",
    extraHtml: `
      <div class="d-flex gap-2">
        <button id="btnDownloadJson" class="btn btn-sm btn-outline-light">Скачать .json</button>
      </div>
    `,
    actionText: "Закрыть",
    onAction: async () => {},
  });

  // скачивание
  setTimeout(() => {
    const b = document.getElementById("btnDownloadJson");
    if (!b) return;
    b.addEventListener("click", () => {
      const blob = new Blob([json], { type: "application/json;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${(state.sheet?.character?.name || "character").replaceAll(" ", "_")}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    });
  }, 0);
});

el("btnImport")?.addEventListener("click", async () => {
  openJsonModal({
    title: "Импорт персонажа",
    label: "Вставь JSON",
    value: "",
    hint: "Вставь JSON из Экспорта и нажми ‘Импортировать’.",
    extraHtml: `
      <label class="form-label mt-2">Новое имя (необязательно)</label>
      <input id="importNewName" class="form-control" placeholder="Оставь пустым чтобы взять имя из JSON" />
    `,
    actionText: "Импортировать",
    onAction: async () => {
      const raw = el("jsonTextarea").value.trim();
      if (!raw) throw new Error("Вставь JSON");
      let parsed;
      try {
        parsed = JSON.parse(raw);
      } catch {
        throw new Error("JSON не распарсился — проверь скобки/кавычки");
      }
      const newName = document.getElementById("importNewName")?.value?.trim();
      if (newName) parsed.new_name = newName;
      await api(`/characters/import`, { method: "POST", body: JSON.stringify(parsed) });
      await loadCharacters();
      await loadSheet();
      setStatus("Импортировано ✅");
    },
  });
});

el("btnTemplates")?.addEventListener("click", () => {
  if (!templatesModal) return;
  renderTemplatesModal();
  templatesModal.show();
});

el("characterSelect").addEventListener("change", async (e) => {
  state.chId = Number(e.target.value);
  await loadSheet();
});

el("btnNew").addEventListener("click", () => {
  const options = [
    `<option value="">Без шаблона</option>`,
    ...state.templates.map((t) => `<option value="${t.id}">${escapeHtml(t.name)}</option>`),
  ].join("");
  openModal(
    "Новый персонаж",
    `
      <label class="form-label">Имя</label>
      <input id="newName" class="form-control" placeholder="Напр. Элвин" />
      <div class="mt-2">
        <label class="form-label">Создать по шаблону</label>
        <select id="newTpl" class="form-select">${options}</select>
      </div>
    `,
    async () => {
      const name = document.getElementById("newName").value.trim();
      if (!name) throw new Error("Введите имя");
      const tplId = document.getElementById("newTpl").value;
      if (tplId) {
        await api(`/templates/${tplId}/create-character`, { method: "POST", body: JSON.stringify({ name }) });
        // автоматически применим этот шаблон к интерфейсу
        setActiveTemplateId(Number(tplId));
      } else {
        await api(`/characters`, { method: "POST", body: JSON.stringify({ name }) });
      }
      await loadCharacters();
    }
  );
});

// MAIN save
async function saveMain(extra = {}) {
  const payload = {
    name: el("f_name").value.trim(),
    race: el("f_race").value.trim(),
    klass: el("f_klass").value.trim(),
    gender: el("f_gender").value.trim(),
    level: intOrNull(el("f_level").value),
    xp: intOrNull(el("f_xp").value),

    hp: intOrNull(el("f_hp").value),
    hp_max: intOrNull(el("f_hp_max").value),
    hp_per_level: intOrNull(el("f_hp_per_level").value),

    mana: intOrNull(el("f_mana").value),
    mana_max: intOrNull(el("f_mana_max").value),
    mana_per_level: intOrNull(el("f_mana_per_level").value),

    energy: intOrNull(el("f_energy").value),
    energy_max: intOrNull(el("f_energy_max").value),
    energy_per_level: intOrNull(el("f_energy_per_level").value),

    level_up_rules: el("f_level_up_rules").value,

    ...extra,
  };

  // remove nulls
  Object.keys(payload).forEach((k) => payload[k] === null && delete payload[k]);

  const id = currentChId();
  await api(`/characters/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
  setStatus("Сохранено ✅");
  await loadSheet(false);
}

document.getElementById("btnSaveMain").addEventListener("click", () => saveMain());
document.getElementById("btnSaveRules").addEventListener("click", () => saveMain());

// STATS
const personalityFields = [
  { key: "aggression_kindness", label: "Агрессия/Доброта" },
  { key: "intellect", label: "Интеллект" },
  { key: "fearlessness", label: "Бесстрашие" },
  { key: "humor", label: "Юмор" },
  { key: "emotionality", label: "Эмоц." },
  { key: "sociability", label: "Общительность" },
  { key: "responsibility", label: "Ответственность" },
  { key: "intimidation", label: "Запугивание" },
  { key: "attentiveness", label: "Внимательность" },
  { key: "learnability", label: "Обучаемость" },
  { key: "luck", label: "Удача" },
  { key: "stealth", label: "Скрытность" },
];

const combatFields = [
  { key: "initiative", label: "Инициатива" },
  { key: "attack", label: "Атака" },
  { key: "counterattack", label: "Контратака" },
  { key: "steps", label: "Шаги" },
  { key: "defense", label: "Защита" },
  { key: "perm_armor", label: "Броня (пост.)" },
  { key: "temp_armor", label: "Броня (врем.)" },
  { key: "action_points", label: "Очки действий" },
  { key: "dodges", label: "Увороты" },
];

buildStatInputs("statsPersonality", personalityFields);
buildStatInputs("statsCombat", combatFields);

el("btnSaveStats").addEventListener("click", async () => {
  const extra = { ...readStatInputs("statsPersonality"), ...readStatInputs("statsCombat") };
  await saveMain(extra);
});

// EQUIPMENT
const equipFields = [
  { key: "head", label: "Голова" },
  { key: "armor", label: "Броня" },
  { key: "back", label: "Спина" },
  { key: "hands", label: "Руки" },
  { key: "legs", label: "Ноги" },
  { key: "feet", label: "Ступни" },
  { key: "weapon1", label: "Оружие 1" },
  { key: "weapon2", label: "Оружие 2" },
  { key: "belt", label: "Пояс" },
  { key: "ring1", label: "Кольцо 1" },
  { key: "ring2", label: "Кольцо 2" },
  { key: "ring3", label: "Кольцо 3" },
  { key: "ring4", label: "Кольцо 4" },
  { key: "jewelry", label: "Украшения" },
];

(function buildEquip() {
  const wrap = el("equipGrid");
  wrap.innerHTML = "";
  equipFields.forEach(({ key, label }) => {
    const div = document.createElement("div");
    div.innerHTML = `
      <label class="form-label">${label}</label>
      <input class="form-control" data-eq="${key}" />
    `;
    wrap.appendChild(div);
  });
})();

function fillEquip(equipment) {
  document.querySelectorAll("input[data-eq]").forEach((input) => {
    const key = input.dataset.eq;
    input.value = equipment?.[key] ?? "";
  });
}

function readEquip() {
  const payload = {};
  document.querySelectorAll("input[data-eq]").forEach((input) => {
    const key = input.dataset.eq;
    payload[key] = input.value;
  });
  return payload;
}

el("btnSaveEquip").addEventListener("click", async () => {
  const id = currentChId();
  await api(`/characters/${id}/equipment`, { method: "PATCH", body: JSON.stringify(readEquip()) });
  setStatus("Сохранено ✅");
  await loadSheet(false);
});

// CUSTOM FIELDS (from template)
function renderCustomFields() {
  const root = el("customRoot");
  if (!root) return;
  root.innerHTML = "";

  const config = state.sheet?.template?.config || {};
  const sections = Array.isArray(config.custom_sections) ? config.custom_sections : [];
  const values = state.sheet?.custom_values || {};

  if (!sections.length) {
    root.innerHTML = `<div class="muted">В этом шаблоне нет кастомных полей. Создай/выбери шаблон и добавь custom_sections.</div>`;
    return;
  }

  sections.forEach((sec) => {
    const title = sec.title || sec.name || "Раздел";
    const card = document.createElement("div");
    card.className = "card card-soft mb-3";
    const fields = Array.isArray(sec.fields) ? sec.fields : [];
    card.innerHTML = `
      <div class="card-body">
        <div class="section-title">${escapeHtml(title)}</div>
        <div class="grid-2" data-custom-grid></div>
      </div>
    `;

    const grid = card.querySelector("[data-custom-grid]");
    fields.forEach((f) => {
      const key = String(f.key || "").trim();
      if (!key) return;
      const label = f.label || key;
      const type = (f.type || "text").toLowerCase();
      const val = values[key] ?? f.default ?? (type === "number" ? 0 : "");

      const wrap = document.createElement("div");
      if (type === "textarea") {
        wrap.innerHTML = `
          <label class="form-label">${escapeHtml(label)}</label>
          <textarea class="form-control" rows="3" data-ckey="${escapeHtml(key)}" data-ctype="textarea">${escapeHtml(val)}</textarea>
        `;
      } else if (type === "number") {
        wrap.innerHTML = `
          <label class="form-label">${escapeHtml(label)}</label>
          <input class="form-control" type="number" data-ckey="${escapeHtml(key)}" data-ctype="number" value="${escapeHtml(val)}" />
        `;
      } else if (type === "checkbox") {
        const checked = Boolean(val) ? "checked" : "";
        wrap.innerHTML = `
          <div class="form-check mt-2">
            <input class="form-check-input" type="checkbox" data-ckey="${escapeHtml(key)}" data-ctype="checkbox" id="ck_${escapeHtml(key)}" ${checked}>
            <label class="form-check-label" for="ck_${escapeHtml(key)}">${escapeHtml(label)}</label>
          </div>
        `;
      } else {
        wrap.innerHTML = `
          <label class="form-label">${escapeHtml(label)}</label>
          <input class="form-control" data-ckey="${escapeHtml(key)}" data-ctype="text" value="${escapeHtml(val)}" />
        `;
      }
      grid.appendChild(wrap);
    });

    root.appendChild(card);
  });
}

function getActiveTabKey() {
  const btn = document.querySelector("#tabs .nav-link.active");
  return btn ? btn.dataset.tab : "main";
}

function updateFab() {
  const fab = el("fabAdd");
  const tab = getActiveTabKey();

  // показываем FAB только там, где есть "добавить"
  const map = {
    inv: { text: "Предмет", icon: "bi-backpack", onClick: () => el("btnAddItem")?.click() },
    spells: { text: "Заклинание", icon: "bi-stars", onClick: () => openSpellModal("spell") },
    abilities: { text: "Умение", icon: "bi-lightning-charge", onClick: () => openSpellModal("ability") },
    states: { text: "Состояние", icon: "bi-activity", onClick: () => el("btnAddState")?.click() },
  };

  const cfg = map[tab];
  if (!cfg) {
    fab.classList.add("d-none");
    fab.onclick = null;
    return;
  }

  fab.classList.remove("d-none");
  fab.innerHTML = `<i class="bi bi-plus-lg"></i>`;
  fab.onclick = cfg.onClick;
}

function readCustomFields() {
  const root = el("customRoot");
  const values = {};
  if (!root) return values;
  root.querySelectorAll("[data-ckey]").forEach((node) => {
    const key = node.getAttribute("data-ckey");
    const type = node.getAttribute("data-ctype");
    if (!key) return;
    if (type === "checkbox") {
      values[key] = Boolean(node.checked);
    } else if (type === "number") {
      const n = intOrNull(node.value);
      values[key] = n === null ? 0 : n;
    } else {
      values[key] = node.value ?? "";
    }
  });
  return values;
}

el("btnSaveCustom")?.addEventListener("click", async () => {
  const id = currentChId();
  if (!id) return;
  await api(`/characters/${id}/custom`, { method: "PATCH", body: JSON.stringify({ values: readCustomFields() }) });
  setStatus("Сохранено ✅");
  await loadSheet(false);
  updateFab();
});

// INVENTORY / SPELLS / ABILITIES / STATES
el("btnAddItem").addEventListener("click", () => {
  openModal(
    "Добавить предмет",
    `
      <label class="form-label">Название</label>
      <input id="m_name" class="form-control" />
      <label class="form-label mt-2">Описание</label>
      <textarea id="m_desc" class="form-control" rows="3"></textarea>
      <label class="form-label mt-2">Статы (по желанию)</label>
      <textarea id="m_stats" class="form-control" rows="2" placeholder="Напр. +2 AC, 1d6"></textarea>
    `,
    async () => {
      const id = currentChId();
      await api(`/characters/${id}/items`, {
        method: "POST",
        body: JSON.stringify({
          name: document.getElementById("m_name").value,
          description: document.getElementById("m_desc").value,
          stats: document.getElementById("m_stats").value,
        }),
      });
      await loadSheet(false);
    }
  );
});

function openSpellModal(kind) {
  const labels = {
    spell: "Заклинание",
    ability: "Умение",
  };
  const title = `Добавить ${labels[kind]}`;
  openModal(
    title,
    `
      <label class="form-label">Название</label>
      <input id="m_name" class="form-control" />
      <label class="form-label mt-2">Описание</label>
      <textarea id="m_desc" class="form-control" rows="3"></textarea>
      <div class="row g-2 mt-1">
        <div class="col-6">
          <label class="form-label">Дальность</label>
          <input id="m_range" class="form-control" />
        </div>
        <div class="col-6">
          <label class="form-label">Длительность</label>
          <input id="m_duration" class="form-control" />
        </div>
      </div>
      <label class="form-label mt-2">Цена/стоимость</label>
      <input id="m_cost" class="form-control" />
    `,
    async () => {
      const id = currentChId();
      const payload = {
        name: document.getElementById("m_name").value,
        description: document.getElementById("m_desc").value,
        range: document.getElementById("m_range").value,
        duration: document.getElementById("m_duration").value,
        cost: document.getElementById("m_cost").value,
      };
      const path = kind === "spell" ? `/characters/${id}/spells` : `/characters/${id}/abilities`;
      await api(path, { method: "POST", body: JSON.stringify(payload) });
      await loadSheet(false);
    }
  );
}

document.getElementById("btnAddSpell").addEventListener("click", () => openSpellModal("spell"));
document.getElementById("btnAddAbility").addEventListener("click", () => openSpellModal("ability"));

document.getElementById("btnAddState").addEventListener("click", () => {
  openModal(
    "Добавить состояние",
    `
      <label class="form-label">Название</label>
      <input id="m_name" class="form-control" />
      <div class="row g-2 mt-1">
        <div class="col-6">
          <label class="form-label">HP стоимость</label>
          <input id="m_hp_cost" type="number" class="form-control" value="0" />
        </div>
        <div class="col-6">
          <label class="form-label">Длительность</label>
          <input id="m_duration" class="form-control" />
        </div>
      </div>
      <div class="form-check mt-2">
        <input class="form-check-input" type="checkbox" value="" id="m_active" checked>
        <label class="form-check-label" for="m_active">Активно</label>
      </div>
    `,
    async () => {
      const id = currentChId();
      const payload = {
        name: document.getElementById("m_name").value,
        hp_cost: intOrNull(document.getElementById("m_hp_cost").value) ?? 0,
        duration: document.getElementById("m_duration").value,
        is_active: document.getElementById("m_active").checked,
      };
      await api(`/characters/${id}/states`, { method: "POST", body: JSON.stringify(payload) });
      await loadSheet(false);
    }
  );
});

// ===== Loaders
async function loadMe() {
  state.me = await api("/me");
}

async function loadTemplates() {
  state.templates = await api("/templates");
  state.activeTemplateId = loadActiveTemplateId();
  // если шаблон удалили — сброс
  if (state.activeTemplateId && !state.templates.find((t) => t.id === state.activeTemplateId)) {
    state.activeTemplateId = null;
    localStorage.removeItem("activeTemplateId");
  }
  applyTemplateToUI();
}

async function loadCharacters() {
  state.characters = await api("/characters");
  const sel = el("characterSelect");
  sel.innerHTML = "";
  state.characters.forEach((c) => {
    const opt = document.createElement("option");
    opt.value = c.id;
    opt.textContent = `${c.name} (lvl ${c.level})`;
    sel.appendChild(opt);
  });

  if (!state.chId && state.characters.length > 0) {
    state.chId = state.characters[0].id;
  }
  if (state.chId) sel.value = state.chId;
}

async function loadSheet(showStatus = true) {
  const id = currentChId();
  if (!id) {
    setStatus("Создай персонажа 👆");
    return;
  }

  if (showStatus) setStatus("Загрузка…");
  state.sheet = await api(`/characters/${id}/sheet`);

  // template attached to character (server). If absent, keep UI template from localStorage
  if (state.sheet?.template?.id) setActiveTemplateId(Number(state.sheet.template.id));
  else if (state.activeTemplateId == null) setActiveTemplateId(loadActiveTemplateId());
  else applyTemplateToUI();


  const ch = state.sheet.character;
  fillInput("f_name", ch.name);
  fillInput("f_race", ch.race);
  fillInput("f_klass", ch.klass);
  fillInput("f_gender", ch.gender);
  fillInput("f_level", ch.level);
  fillInput("f_xp", ch.xp);

  fillInput("f_hp", ch.hp);
  fillInput("f_hp_max", ch.hp_max);
  fillInput("f_hp_per_level", ch.hp_per_level);

  fillInput("f_mana", ch.mana);
  fillInput("f_mana_max", ch.mana_max);
  fillInput("f_mana_per_level", ch.mana_per_level);

  fillInput("f_energy", ch.energy);
  fillInput("f_energy_max", ch.energy_max);
  fillInput("f_energy_per_level", ch.energy_per_level);

  fillInput("f_level_up_rules", ch.level_up_rules);

  fillStatInputs("statsPersonality", ch);
  fillStatInputs("statsCombat", ch);

  fillEquip(state.sheet.equipment);

  renderCustomFields();

  renderList("invList", state.sheet.items, async (it) => {
    await api(`/characters/${id}/items/${it.id}`, { method: "DELETE" });
    await loadSheet(false);
  }, { icon: "bi-backpack", clamp: true });


  renderList(
    "spellsList",
    state.sheet.spells.map((s) => ({
      ...s,
      sub: [s.range, s.duration, s.cost].filter(Boolean).join(" · ") + (s.description ? `\n${s.description}` : ""),
    })),
    async (s) => {
      await api(`/characters/${id}/spells/${s.id}`, { method: "DELETE" });
      await loadSheet(false);
    },
    { icon: "bi-stars", clamp: true }
  );

  renderList(
    "statesList",
    state.sheet.states.map((s) => ({
      ...s,
      sub: `${s.is_active ? "Активно" : "Неактивно"}${s.duration ? ` · ${s.duration}` : ""}${s.hp_cost ? ` · HP ${s.hp_cost}` : ""}`,
    })),
    async (s) => {
      await api(`/characters/${id}/states/${s.id}`, { method: "DELETE" });
      await loadSheet(false);
    },
    { icon: "bi-activity", clamp: true }
  );

  renderList(
    "statesList",
    state.sheet.states.map((s) => ({
      ...s,
      sub: `${s.is_active ? "Активно" : "Неактивно"}${s.duration ? ` · ${s.duration}` : ""}${s.hp_cost ? ` · HP ${s.hp_cost}` : ""}`,
    })),
    async (s) => {
      await api(`/characters/${id}/states/${s.id}`, { method: "DELETE" });
      await loadSheet(false);
    },
    { icon: "bi-activity", clamp: true }
  );

  setStatus("Ок ✅");
}

async function boot() {
  try {
    await loadMe();
    await loadTemplates();
    await loadCharacters();
    if (state.characters.length === 0) setStatus("Персонажей нет. Создай нового 👆");
    await loadSheet();
  } catch (e) {
    console.error(e);
    setStatus("Ошибка");
    alert(e.message);
  }
}

boot();
