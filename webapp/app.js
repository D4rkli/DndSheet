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
  battleRound: 1,
  battleLog: [],
  inBattle: false,
};

const DEFAULT_TABS = [
  "main",
  "stats",
  "inv",
  "spells",
  "abilities",
  "passive-abilities",
  "states",
  "summons",
  "equip",
  "custom",
];

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
  // что выбрано в шаблоне (или дефолт)
  const base = (state.sheet?.template?.config?.tabs && Array.isArray(state.sheet.template.config.tabs) && state.sheet.template.config.tabs.length)
  ? state.sheet.template.config.tabs
  : DEFAULT_TABS;

  // 👇 важное: добавляем новые вкладки, чтобы старые шаблоны не ломались
  const mustHave = ["passive-abilities", "abilities", "summons"]; // на будущее можно сюда докидывать новые

  return Array.from(new Set([...base, ...mustHave]));
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

  // чекбокс вкладок для создания
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
  const v = document.getElementById("characterSelect")?.value;

  // пусто/нет/“null”
  if (!v || v === "null" || v === "undefined") return null;

  const id = Number(v);
  return Number.isFinite(id) && id > 0 ? id : null;
}

function requireCharacterId() {
  const id = currentChId();
  if (!id) {
    alert("Сначала выбери персонажа в списке или создай нового 🙂");
    return null;
  }
  return id;
}

function intOrNull(v) {
  if (v === "" || v === null || v === undefined) return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function buildCostString({ hp, mana, energy }) {
  const parts = [];
  const push = (k, v) => {
    const s = String(v || "").trim();
    if (s) parts.push(`${k}:${s}`);
  };
  push("hp", hp);
  push("mana", mana);
  push("energy", energy);
  return parts.join(", ");
}

function parseCostParts(costStr) {
  const out = { hp: "", mana: "", energy: "" };
  const raw = String(costStr || "").trim();
  if (!raw) return out;

  raw.split(/[,;\n]+/).map(x => x.trim()).filter(Boolean).forEach(part => {
    const m = part.match(/^(hp|mana|energy)\s*[:=]?\s*(.+)$/i);
    if (!m) return;
    out[m[1].toLowerCase()] = m[2].trim();
  });
  return out;
}

function parseRatio(raw) {
  const s = String(raw || "").trim().toLowerCase();
  if (!s) return 0;

  // 50%
  if (s.endsWith("%")) {
    const n = Number(s.slice(0, -1).trim().replace(",", "."));
    return Number.isFinite(n) ? n / 100 : 0;
  }

  // 1/3
  if (s.includes("/")) {
    const [a, b] = s.split("/").map(x => Number(x.trim().replace(",", ".")));
    if (Number.isFinite(a) && Number.isFinite(b) && b !== 0) return a / b;
  }

  // 0.25
  const n = Number(s.replace(",", "."));
  return Number.isFinite(n) ? n : 0;
}

function calcSummonStats(ch, summon) {
  const hp = Math.round((ch.hp_max || 0) * parseRatio(summon.hp_ratio));
  const mana = Math.round((ch.mana_max || 0) * parseRatio(summon.mana_ratio));
  const energy = Math.round((ch.energy_max || 0) * parseRatio(summon.energy_ratio));

  const atk = Math.round((ch.attack || 0) * parseRatio(summon.attack_ratio));
  const def = Math.round((ch.defense || 0) * parseRatio(summon.defense_ratio));

  const initiative = Math.round((ch.initiative || 0) * parseRatio(summon.initiative_ratio));
  const luck = Math.round((ch.luck || 0) * parseRatio(summon.luck_ratio));
  const steps = Math.round((ch.steps || 0) * parseRatio(summon.steps_ratio));

  // пока базу дальности берём от steps персонажа (логично как “клетки/метры”),
  // если у тебя будет отдельный stat "attack_range" — поменяем на него.
  const attackRange = Math.round((ch.steps || 0) * parseRatio(summon.attack_range_ratio));

  const count = Math.max(1, Number(summon.count || 1));
  return { hp, mana, energy, atk, def, initiative, luck, steps, attackRange, count };
}

function openSummonModal(existing = null) {
  const isEdit = !!existing;
  const title = isEdit ? "Редактировать призыв" : "Добавить призыв";

  openModal(
    title,
    `
      <label class="form-label">Название</label>
      <input id="m_name" class="form-control" />

      <label class="form-label mt-2">Описание</label>
      <textarea id="m_desc" class="form-control" rows="3"></textarea>

      <div class="row g-2 mt-1">
        <div class="col-6">
          <label class="form-label">Длительность</label>
          <input id="m_duration" class="form-control" placeholder="напр. 3 хода" />
        </div>
        <div class="col-6">
          <label class="form-label">Количество</label>
          <input id="m_count" type="number" class="form-control" min="1" value="1" />
        </div>
      </div>

      <div class="row g-2 mt-2">
        <div class="col-4">
          <label class="form-label">HP доля</label>
          <input id="m_hp_ratio" class="form-control" placeholder="50%, 1/3, 3x-5" />
        </div>
        <div class="col-4">
          <label class="form-label">ATK доля</label>
          <input id="m_atk_ratio" class="form-control" placeholder="25%, 2x, 10%+x" />
        </div>
        <div class="col-4">
          <label class="form-label">DEF доля</label>
          <input id="m_def_ratio" class="form-control" placeholder="1/4, 15%, 5" />
        </div>
      </div>
      <div class="row g-2 mt-2">
      
      <div class="col-6">
        <label class="form-label">Мана доля</label>
        <input id="m_mana_ratio" class="form-control" placeholder="0, 1/4, 50%" />
      </div>
      <div class="col-6">
        <label class="form-label">Энергия доля</label>
        <input id="m_energy_ratio" class="form-control" placeholder="0, 1/4, 50%" />
      </div>
    </div>
    
    <div class="row g-2 mt-2">
      <div class="col-4">
        <label class="form-label">Инициатива доля</label>
        <input id="m_initiative_ratio" class="form-control" placeholder="0, 1/2, 100%" />
      </div>
      <div class="col-4">
        <label class="form-label">Удача доля</label>
        <input id="m_luck_ratio" class="form-control" placeholder="0, 1/2, 100%" />
      </div>
      <div class="col-4">
        <label class="form-label">Шаги доля</label>
        <input id="m_steps_ratio" class="form-control" placeholder="0, 1/2, 100%" />
      </div>
    </div>
    
    <div class="row g-2 mt-2">
      <div class="col-12">
        <label class="form-label">Дальность атаки доля</label>
        <input id="m_attack_range_ratio" class="form-control" placeholder="0, 1/2, 100%" />
        <div class="hint">Считается от шагов персонажа.</div>
      </div>
    </div>

      <div id="m_preview" class="hint mt-2"></div>
    `,
    async () => {
      const id = requireCharacterId();
      if (!id) return;

      const payload = {
        name: el("m_name").value,
        description: el("m_desc").value,
        duration: el("m_duration").value,
        count: Number(el("m_count").value || 1),
        hp_ratio: el("m_hp_ratio").value,
        attack_ratio: el("m_atk_ratio").value,
        defense_ratio: el("m_def_ratio").value,
        mana_ratio: el("m_mana_ratio").value,
        energy_ratio: el("m_energy_ratio").value,
        initiative_ratio: el("m_initiative_ratio").value,
        luck_ratio: el("m_luck_ratio").value,
        steps_ratio: el("m_steps_ratio").value,
        attack_range_ratio: el("m_attack_range_ratio").value,
      };

      const base = `/characters/${id}/summons`;
      const path = isEdit ? `${base}/${existing.id}` : base;
      const method = isEdit ? "PATCH" : "POST";

      await api(path, { method, body: JSON.stringify(payload) });
      await loadSheet(false);
    }
  );

  const ch = state.sheet?.character || {};
  const updatePreview = () => {
    const tmp = {
      hp_ratio: el("m_hp_ratio").value,
      attack_ratio: el("m_atk_ratio").value,
      defense_ratio: el("m_def_ratio").value,
      count: Number(el("m_count").value || 1),
    };
    const r = calcSummonStats(ch, tmp);
    el("m_preview").textContent =
      `Итого: HP ${r.hp} · Mana ${r.mana} · Energy ${r.energy} · ` +
      `ATK ${r.atk} · DEF ${r.def} · Ini ${r.initiative} · Luck ${r.luck} · ` +
      `Steps ${r.steps} · Range ${r.attackRange} · x${r.count}`;
  };

  ["m_hp_ratio","m_mana_ratio","m_energy_ratio","m_atk_ratio","m_def_ratio",
   "m_initiative_ratio","m_luck_ratio","m_steps_ratio","m_attack_range_ratio","m_count"
  ].forEach(id => el(id).addEventListener("input", updatePreview));

  if (existing) {
    el("m_name").value = existing.name || "";
    el("m_desc").value = existing.description || "";
    el("m_duration").value = existing.duration || "";
    el("m_count").value = String(existing.count ?? 1);
    el("m_hp_ratio").value = existing.hp_ratio || "1/3";
    el("m_atk_ratio").value = existing.attack_ratio || "1/2";
    el("m_def_ratio").value = existing.defense_ratio || "1/4";
    el("m_mana_ratio").value = existing?.mana_ratio ?? "0";
    el("m_energy_ratio").value = existing?.energy_ratio ?? "0";
    el("m_initiative_ratio").value = existing?.initiative_ratio ?? "0";
    el("m_luck_ratio").value = existing?.luck_ratio ?? "0";
    el("m_steps_ratio").value = existing?.steps_ratio ?? "0";
    el("m_attack_range_ratio").value = existing?.attack_range_ratio ?? "0";
  } else {
    el("m_hp_ratio").value = "1/3";
    el("m_atk_ratio").value = "1/2";
    el("m_def_ratio").value = "1/4";
  }

  updatePreview();
}

el("btnAddSummon")?.addEventListener("click", () => openSummonModal());

function evalCostExpr(res, expr, character, level) {
  const maxBase = Number(character?.[`${res}_max`] ?? 0) || 0;
  const s = String(expr || "").toLowerCase().replaceAll(" ", "");
  if (!s) return 0;

  const tokens = s.match(/[+-]?[^+-]+/g) || [];
  let total = 0;

  for (let t of tokens) {
    if (!t) continue;

    let sign = 1;
    if (t[0] === "+") t = t.slice(1);
    else if (t[0] === "-") { sign = -1; t = t.slice(1); }

    if (!t) continue;

    let val = null;

    const perc = t.match(/^(\d+(?:\.\d+)?)%$/);
    if (perc) {
      val = Math.round(maxBase * (Number(perc[1]) / 100));
    } else if (t.match(/^\d+\/\d+$/)) {
      const [a, b] = t.split("/").map(Number);
      if (b !== 0) val = Math.round(maxBase * (a / b));
    } else if (t.match(/^\d+(?:\.\d+)?x$/)) {
      val = Math.round(Number(t.replace("x", "")) * level);
    } else if (t === "x") {
      val = level;
    } else if (t.match(/^\d+(?:\.\d+)?$/)) {
      val = Math.round(Number(t));
    }

    if (val === null) continue;
    total += sign * val;
  }

  return total;
}

function evalSummonExpr(expr, base, level) {
  const s = String(expr || "").toLowerCase().replaceAll(" ", "");
  if (!s) return 0;

  const tokens = s.match(/[+-]?[^+-]+/g) || [];
  let total = 0;

  for (let t of tokens) {
    if (!t) continue;

    let sign = 1;
    if (t[0] === "+") t = t.slice(1);
    else if (t[0] === "-") { sign = -1; t = t.slice(1); }

    if (!t) continue;

    let val = null;

    // 50% от base
    const perc = t.match(/^(\d+(?:\.\d+)?)%$/);
    if (perc) {
      val = Math.round(Number(base) * (Number(perc[1]) / 100));
    }
    // 1/3 от base
    else if (t.match(/^\d+(?:\.\d+)?\/\d+(?:\.\d+)?$/)) {
      const [a, b] = t.split("/").map(x => Number(x.replace(",", ".")));
      if (Number.isFinite(a) && Number.isFinite(b) && b !== 0) {
        val = Math.round(Number(base) * (a / b));
      }
    }
    // 3x (от уровня)
    else if (t.match(/^\d+(?:\.\d+)?x$/)) {
      val = Math.round(Number(t.replace("x", "").replace(",", ".")) * level);
    }
    // x (от уровня)
    else if (t === "x") {
      val = Math.round(level);
    }
    // просто число
    else if (t.match(/^\d+(?:\.\d+)?$/)) {
      val = Math.round(Number(t.replace(",", ".")));
    }

    if (val === null) continue;
    total += sign * val;
  }

  return total;
}

function parseCost(costStr, character) {
  const level = Number(character?.level || 1);
  const raw = String(costStr || "")
    .toLowerCase()
    .replaceAll("мана", "mana")
    .replaceAll("хп", "hp")
    .replaceAll("здоровье", "hp")
    .replaceAll("энергия", "energy")
    .replaceAll("энер", "energy")
    .trim();

  const result = { hp: 0, mana: 0, energy: 0 };
  if (!raw) return result;

  const parts = raw.split(/[,;\n]+/).map(s => s.trim()).filter(Boolean);

  for (const part of parts) {
    const m = part.match(/^(hp|mana|energy)\s*([:=])?\s*(.+)$/);
    if (!m) continue;
    const res = m[1];
    const expr = m[3];
    const value = evalCostExpr(res, expr, character, level);
    if (Number.isFinite(value)) result[res] += value;
  }

  return result;
}

async function applyCostToCharacter(costStr, sourceName = "Способность") {
  const id = currentChId();
  if (!id || !state.sheet?.character) return;

  const ch = state.sheet.character;
  const delta = parseCost(costStr, ch);

  const hp = Number(ch.hp || 0);
  const mana = Number(ch.mana || 0);
  const energy = Number(ch.energy || 0);

  if (delta.hp > hp) {
    showBattleError("Недостаточно HP");
    return;
  }
  if (delta.mana > mana) {
    showBattleError("Недостаточно маны");
    return;
  }
  if (delta.energy > energy) {
    showBattleError("Недостаточно энергии");
    return;
  }

  const payload = {};
  if (delta.hp) payload.hp = hp - delta.hp;
  if (delta.mana) payload.mana = mana - delta.mana;
  if (delta.energy) payload.energy = energy - delta.energy;

  if (Object.keys(payload).length === 0) return;

  appendBattleLog(
    `✨ ${sourceName}:` +
    `${delta.hp ? ` HP -${delta.hp}` : ""}` +
    `${delta.mana ? ` Mana -${delta.mana}` : ""}` +
    `${delta.energy ? ` Energy -${delta.energy}` : ""}`
  );

  showBattleToast(`${sourceName}: действие применено`, "success");

  await saveMain(payload);
}

function parseIntSafe(v) {
  const n = parseInt(String(v ?? "").trim() || "0", 10);
  return Number.isFinite(n) ? n : 0;
}

function coinsToCp({ gold = 0, silver = 0, copper = 0 }) {
  return gold * 1000 + silver * 10 + copper;
}

function updateMoneyPreview(coins) {
  const node = el("moneyPreview");
  if (!node) return;

  const { gold = 0, silver = 0, copper = 0 } = coins || {};
  const totalCp = coinsToCp({ gold, silver, copper });
  const totalGold = (totalCp / 1000).toFixed(3);

  node.innerHTML = `
    Всего: <b>${gold}</b> 🟡 · <b>${silver}</b> ⚪ · <b>${copper}</b> 🟤
    <br>
    Эквивалент: <b>${totalGold}</b> золота
  `;
}

function wireMoneyInputs() {
  const g = el("f_gold");
  const s = el("f_silver");
  const c = el("f_copper");
  if (!g || !s || !c) return;

  const onInput = () => {
    const coins = {
      gold: parseIntSafe(g.value),
      silver: parseIntSafe(s.value),
      copper: parseIntSafe(c.value),
    };

    // 🔴 ВАЖНО: сохраняем в state
    if (state.sheet?.character) {
      state.sheet.character.gold = coins.gold;
      state.sheet.character.silver = coins.silver;
      state.sheet.character.copper = coins.copper;
    }

    updateMoneyPreview(coins);
  };

  g.addEventListener("input", onInput);
  s.addEventListener("input", onInput);
  c.addEventListener("input", onInput);

  onInput();
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

    // ✅ спец-поле: Агрессия / Доброта = два числа
    if (key === "aggression_kindness") {
      div.innerHTML = `
        <label class="form-label">${label}</label>

        <div class="stepper stepper-split" style="grid-template-columns: 1fr 14px 1fr;">
          <input class="form-control" type="number" step="1" inputmode="numeric" data-ak="a" placeholder="агрессия" />
          <span class="step-sep">/</span>
          <input class="form-control" type="number" step="1" inputmode="numeric" data-ak="k" placeholder="доброта" />
        </div>

        <input type="hidden" data-key="${key}" />
      `;

      // обновляем скрытое поле "a/b" при вводе
      const a = div.querySelector('input[data-ak="a"]');
      const k = div.querySelector('input[data-ak="k"]');
      const hidden = div.querySelector(`input[data-key="${key}"]`);

      const sync = () => {
        const av = String(a.value ?? "").trim();
        const kv = String(k.value ?? "").trim();
        hidden.value = `${av}/${kv}`;
      };

      a.addEventListener("input", sync);
      k.addEventListener("input", sync);
      sync();

      wrap.appendChild(div);
      return;
    }

    // остальные статы как раньше
    div.innerHTML = `
      <label class="form-label">${label}</label>
      <div class="stepper stepper-stat">
        <button class="btn btn-outline-light step-btn" type="button" data-step="-1">−</button>
        <input class="form-control num stat-num" type="number" step="1" data-key="${key}" />
        <button class="btn btn-outline-light step-btn" type="button" data-step="+1">+</button>
      </div>
    `;
    wrap.appendChild(div);
  });
}


function readStatInputs(containerId) {
  const data = {};
  el(containerId).querySelectorAll("input[data-key]").forEach((input) => {
    const key = input.dataset.key;
    const val = String(input.value ?? "").trim();
    if (val !== "") data[key] = val;
  });
  return data;
}

function fillStatInputs(containerId, source) {
  const root = el(containerId);

  // ✅ заполняем спец-поле aggression_kindness
  const hidden = root.querySelector('input[data-key="aggression_kindness"]');
  if (hidden) {
    const raw = String(source?.aggression_kindness ?? "").trim(); // "10/5"
    const [a, k] = raw.split("/");

    const aInp = root.querySelector('input[data-ak="a"]');
    const kInp = root.querySelector('input[data-ak="k"]');

    if (aInp) aInp.value = a ?? "";
    if (kInp) kInp.value = k ?? "";

    hidden.value = raw || `${aInp?.value ?? ""}/${kInp?.value ?? ""}`;
  }

  // остальные инпуты как раньше
  root.querySelectorAll('input[data-key]').forEach((input) => {
    const key = input.dataset.key;
    if (key === "aggression_kindness") return; // уже сделали выше
    input.value = source?.[key] ?? 0;
  });
}

function renderList(containerId, rows, onDelete, opts = {}) {
  const root = el(containerId);
  if (!root) return;
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

          ${opts.onUse ? `
            <button class="btn btn-sm btn-outline-light" data-act="use" title="Использовать">
              <i class="bi bi-play-fill"></i>
            </button>
          ` : ``}

          ${opts.onEdit ? `
            <button class="btn btn-sm btn-outline-light" data-act="edit" title="Редактировать">
              <i class="bi bi-pencil"></i>
            </button>
          ` : ``}

          <button class="btn btn-sm btn-outline-light" data-act="delete" title="Удалить">
            <i class="bi bi-trash3"></i>
          </button>
        </div>
      </div>

      <div class="item-details d-none">${details}</div>
    `;

    // раскрытие по тапу по карточке (кроме кнопки delete)
    card.addEventListener("click", (e) => {
      const actBtn = e.target.closest("button[data-act]");
      if (actBtn) return;

      const d = card.querySelector(".item-details");
      const caret = card.querySelector(".item-caret");
      const isHidden = d.classList.contains("d-none");
      d.classList.toggle("d-none");
      caret.classList.toggle("bi-chevron-down", isHidden);
      caret.classList.toggle("bi-chevron-up", !isHidden);
    });

    const delBtn = card.querySelector("button[data-act='delete']");
    delBtn?.addEventListener("click", async (e) => {
      e.stopPropagation();
      await onDelete(r);
    });

    const useBtn = card.querySelector("button[data-act='use']");
    useBtn?.addEventListener("click", async (e) => {
      e.stopPropagation();
      await opts.onUse(r);
    });

    const editBtn = card.querySelector("button[data-act='edit']");
    editBtn?.addEventListener("click", (e) => {
      e.stopPropagation();
      opts.onEdit(r);
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
function escapeAttr(s) {
  return String(s ?? "").replaceAll("&","&amp;").replaceAll('"',"&quot;").replaceAll("<","&lt;").replaceAll(">","&gt;");
}

// ===== Modal helpers
const modalEl = el("editModal");
const modal = new bootstrap.Modal(modalEl);
const restModalEl = el("restModal");
const restModal = restModalEl ? new bootstrap.Modal(restModalEl) : null;
const moveModalEl = el("moveModal");
const moveModal = moveModalEl ? new bootstrap.Modal(moveModalEl) : null;
const armorModalEl = el("armorModal");
const armorModal = armorModalEl ? new bootstrap.Modal(armorModalEl) : null;

// 🔧 FIX: чтобы экран не блокировался после закрытия модалок
restModalEl?.addEventListener("hidden.bs.modal", () => {
  document.querySelectorAll(".modal-backdrop").forEach((node) => node.remove());
  document.body.classList.remove("modal-open");
  document.body.style.removeProperty("padding-right");
});

moveModalEl?.addEventListener("hidden.bs.modal", () => {
  document.querySelectorAll(".modal-backdrop").forEach((node) => node.remove());
  document.body.classList.remove("modal-open");
  document.body.style.removeProperty("padding-right");
});

armorModalEl?.addEventListener("hidden.bs.modal", () => {
  document.querySelectorAll(".modal-backdrop").forEach((node) => node.remove());
  document.body.classList.remove("modal-open");
  document.body.style.removeProperty("padding-right");
});

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

function getXpPerLevel() {
  // если ты уже добавляла f_xp_per_level — используем его
  const per = intOrNull(el("f_xp_per_level")?.value);
  return (per && per > 0) ? per : 0;
}

function updateXpToNextUI() {
  const per = getXpPerLevel();
  const xp = intOrNull(el("f_xp")?.value) ?? 0;

  const out = el("f_xp_to_next");
  if (!out) return;

  if (!per) {
    out.value = "";
    out.placeholder = "задай XP на уровень";
    return;
  }

  const left = Math.max(0, per - xp);
  out.value = String(left);
}

// применить +lvl N раз (с авто-прибавками)
function applyLevelUps(delta) {
  if (delta <= 0) return;

  const hpPL = intOrNull(el("f_hp_per_level")?.value) ?? 0;
  const manaPL = intOrNull(el("f_mana_per_level")?.value) ?? 0;
  const energyPL = intOrNull(el("f_energy_per_level")?.value) ?? 0;

  const hpMax = intOrNull(el("f_hp_max")?.value) ?? 0;
  const manaMax = intOrNull(el("f_mana_max")?.value) ?? 0;
  const energyMax = intOrNull(el("f_energy_max")?.value) ?? 0;

  const hp = intOrNull(el("f_hp")?.value) ?? 0;
  const mana = intOrNull(el("f_mana")?.value) ?? 0;
  const energy = intOrNull(el("f_energy")?.value) ?? 0;

  const addHp = hpPL * delta;
  const addMana = manaPL * delta;
  const addEnergy = energyPL * delta;

  el("f_hp_max").value = String(hpMax + addHp);
  el("f_mana_max").value = String(manaMax + addMana);
  el("f_energy_max").value = String(energyMax + addEnergy);

  el("f_hp").value = String(hp + addHp);
  el("f_mana").value = String(mana + addMana);
  el("f_energy").value = String(energy + addEnergy);
}

async function addXpAndHandleLevelUp() {
  const per = getXpPerLevel();
  if (!per) {
    alert("Сначала задай XP на уровень");
    return;
  }

  const add = intOrNull(el("f_xp_add")?.value) ?? 0;
  if (add <= 0) return;

  let level = intOrNull(el("f_level")?.value) ?? 1;
  let xp = intOrNull(el("f_xp")?.value) ?? 0;

  xp += add;
  el("f_xp_add").value = "";

  let levelUps = 0;

  while (xp >= per) {
    xp -= per;
    level += 1;
    levelUps += 1;
  }

  el("f_xp").value = String(xp);
  el("f_level").value = String(level);

  if (levelUps > 0) {
    applyLevelUps(levelUps);
  }

  updateXpToNextUI();
  updateCombatHudFromSheet();
  await saveMain();
}

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

el("btnSync").addEventListener("click", async () => {
  try {
    await saveEquipment();   // ✅ сначала сохраняем экипировку
    await loadSheet(true);   // ✅ потом синхронизируем
  } catch (e) {
    alert(e.message);
  }
});

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
  // автоконвертация монет перед сохранением
  // монеты: сохраняем как ввели (без автоконвертации)
    const coinsRaw = {
      gold: parseIntSafe(el("f_gold")?.value),
      silver: parseIntSafe(el("f_silver")?.value),
      copper: parseIntSafe(el("f_copper")?.value),
    };

    // превью оставляем конвертированным (только для отображения)
  const payload = {
    name: el("f_name").value.trim(),
    race: el("f_race").value.trim(),
    klass: el("f_klass").value.trim(),
    gender: el("f_gender").value.trim(),
    level: intOrNull(el("f_level").value),
    xp: intOrNull(el("f_xp").value),
    xp_per_level: intOrNull(el("f_xp_per_level")?.value),

    gold: coinsRaw.gold,
    silver: coinsRaw.silver,
    copper: coinsRaw.copper,

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
  { key: "aggression", label: "Агрессия" },
  { key: "kindness", label: "Доброта" },
  { key: "intellect", label: "Интеллект" },
  { key: "fearlessness", label: "Бесстрашие" },
  { key: "confidence", label: "Уверенность" },
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

el("btnSaveEquip")?.addEventListener("click", async () => {
  try {
    await saveEquipment();
    await loadSheet(false);
  } catch (e) {
    alert(e.message);
  }
});


el("btnSaveStats").addEventListener("click", async () => {
  const extra = { ...readStatInputs("statsPersonality"), ...readStatInputs("statsCombat") };
  await saveMain(extra);
});

async function saveEquipDraft() {
  const chId = state.currentCharacterId;
  if (!chId) return;

  // берём то, что сейчас в черновике
  const payload = {};
  for (const { key } of equipFields) {
    const v = state.equipDraft?.[key];
    if (v !== undefined) payload[key] = v ?? "";
  }

  // если нечего сохранять — выходим
  if (Object.keys(payload).length === 0) return;

  await apiPatch(`/characters/${chId}/equipment`, payload);
}

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

state.equipDraft = {};

function parseEquipSlot(raw) {
  const s = String(raw ?? "").trim();
  if (!s) return { name: "", ac_bonus: 0, stats: "", info: "" };
  if (s.startsWith("{") && s.endsWith("}")) {
    try {
      const o = JSON.parse(s);
      if (o && typeof o === "object") {
        return {
          name: String(o.name ?? ""),
          ac_bonus: Number(o.ac_bonus ?? 0) || 0,
          stats: String(o.stats ?? ""),
          info: String(o.info ?? ""),
        };
      }
    } catch {}
  }
  return { name: s, ac_bonus: 0, stats: "", info: "" };
}

function serializeEquipSlot(slot) {
  const name = String(slot?.name ?? "").trim();
  const ac = Number(slot?.ac_bonus ?? 0) || 0;
  const stats = String(slot?.stats ?? "").trim();
  const info = String(slot?.info ?? "").trim();

  // если только имя — храним как раньше (простая строка)
  if (name && !ac && !stats && !info) return name;
  // если всё пусто — пустая строка
  if (!name && !ac && !stats && !info) return "";
  // иначе — JSON
  return JSON.stringify({ name, ac_bonus: ac, stats, info });
}

function equipArmorBonusTotal() {
  let sum = 0;
  equipFields.forEach(({ key }) => {
    const slot = parseEquipSlot(state.equipDraft?.[key]);
    sum += Number(slot.ac_bonus || 0);
  });
  return sum;
}

function renderEquipUI() {
  const wrap = el("equipGrid");
  if (!wrap) return;
  wrap.innerHTML = "";

  const bonus = equipArmorBonusTotal();
  const bonusEl = el("equipBonus");
  if (bonusEl) {
    bonusEl.innerHTML = `Бонус брони от экипировки: <b>${bonus ? `+${bonus}` : `0`}</b>`;
  }

  equipFields.forEach(({ key, label }) => {
    const raw = state.equipDraft?.[key] ?? "";
    const slot = parseEquipSlot(raw);

    const name = slot.name?.trim() || "—";
    const ac = Number(slot.ac_bonus || 0);
    const stats = slot.stats?.trim() || "";
    const info = slot.info?.trim() || "";

    const card = document.createElement("div");
    card.className = "equip-card";

    card.innerHTML = `
      <div class="equip-top">
        <div class="equip-slot">
          <i class="bi ${equipIcons[key] || "bi-shield"}"></i>
          <span>${label}:</span>
          <span
            class="equip-name ${name === "—" ? "equip-empty" : ""}"
            title="${name !== "—" ? escapeAttr(name) : ""}"
          >
            ${escapeHtml(name)}
          </span>
          ${ac ? `<span class="muted">+${ac} AC</span>` : ""}
        </div>
      </div>
    
      ${stats ? `<div class="equip-sub">${escapeHtml(stats)}</div>` : ""}
      ${info ? `<div class="equip-info">${escapeHtml(info)}</div>` : ""}
    `;

    card.addEventListener("click", () => {
      openEquipSlotModal(key, label);
    });

    wrap.appendChild(card);
  });
}

async function saveEquipment() {
  const id = currentChId();
  if (!id) return;

  // отправляем весь черновик на сервер
  const payload = {};
  equipFields.forEach(({ key }) => {
    payload[key] = state.equipDraft?.[key] ?? "";
  });

  await api(`/characters/${id}/equipment`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });

  setStatus("Экипировка сохранена ✅");
}


const equipIcons = {
  head: "bi-person-badge",        // Голова
  armor: "bi-shield-fill",        // Броня
  back: "bi-backpack",            // Спина
  hands: "bi-hand-index-thumb",   // Руки
  legs: "bi-person-walking",      // Ноги
  feet: "bi-arrow-down-circle",   // Ступни (условно, но читаемо)

  weapon1: "bi-sword",            // Оружие 1
  weapon2: "bi-sword",            // Оружие 2
  belt: "bi-bag",                 // Пояс

  ring1: "bi-gem",
  ring2: "bi-gem",
  ring3: "bi-gem",
  ring4: "bi-gem",

  jewelry: "bi-stars"             // Украшения
};

function openEquipSlotModal(key, label) {
  const cur = parseEquipSlot(state.equipDraft?.[key]);

  openModal(
    `Экипировка: ${label}`,
    `
      <label class="form-label">Название</label>
      <input id="m_eq_name" class="form-control" />

      <div class="row g-2 mt-2">
        <div class="col-4">
          <label class="form-label">AC бонус</label>
          <input id="m_eq_ac" type="number" class="form-control" value="0" />
        </div>
      </div>

      <label class="form-label mt-2">Характеристика</label>
      <input id="m_eq_stats" class="form-control" placeholder="Напр. +2 ловк, сопротивление огню" />

      <label class="form-label mt-2">Доп. Информация</label>
      <textarea id="m_eq_info" class="form-control" rows="3" placeholder="Любые заметки"></textarea>
    `,
    async () => {
      const name = document.getElementById("m_eq_name").value;
      const ac_bonus = intOrNull(document.getElementById("m_eq_ac").value) ?? 0;
      const stats = document.getElementById("m_eq_stats").value;
      const info = document.getElementById("m_eq_info").value;
      const nameTrim = String(name || "").trim();
      const allEmpty = !nameTrim && !ac_bonus && !String(stats||"").trim() && !String(info||"").trim();

      state.equipDraft[key] = allEmpty ? "" : serializeEquipSlot({ name, ac_bonus, stats, info });
      renderEquipUI();
    }
  );

  document.getElementById("m_eq_name").value = cur.name || "";
  document.getElementById("m_eq_ac").value = String(cur.ac_bonus ?? 0);
  document.getElementById("m_eq_stats").value = cur.stats || "";
  document.getElementById("m_eq_info").value = cur.info || "";
}

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
  if (!fab) return;
  fab.classList.add("d-none");
  fab.onclick = null;
}

function showFabMenu(show) {
  const m = document.getElementById("fabMenu");
  if (!m) return;
  m.classList.toggle("d-none", !show);
}

function toggleFabMenu() {
  const m = document.getElementById("fabMenu");
  if (!m) return;
  m.classList.toggle("d-none");
}

function wireFabMenu() {
  const fab = document.getElementById("fabAdd");
  const menu = document.getElementById("fabMenu");
  if (!fab || !menu) return;

  // клики по пунктам меню
  menu.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-action]");
    if (!btn) return;

    const action = btn.dataset.action;
    showFabMenu(false);

    // вызываем то, что у тебя точно есть:
    if (action === "add-spell") return openSpellModal("spell");
    if (action === "add-ability") return openSpellModal("passive");

    // а вот это попробуем дернуть через существующие кнопки (если есть)
    if (action === "add-item") return document.getElementById("btnAddItem")?.click();
    if (action === "add-state") return document.getElementById("btnAddState")?.click();
  });

  // обычной тап по FAB: действие по вкладке (как у тебя уже было)
  // долгий тап/ПК-правый клик: открыть меню

  let pressTimer = null;
  let longPressed = false;

  const startPress = () => {
    longPressed = false;
    pressTimer = window.setTimeout(() => {
      longPressed = true;
      showFabMenu(true);
    }, 420);
  };

  const cancelPress = () => {
    if (pressTimer) window.clearTimeout(pressTimer);
    pressTimer = null;
  };

  // touch
  fab.addEventListener("touchstart", (e) => {
    startPress();
  }, { passive: true });

  fab.addEventListener("touchend", (e) => {
    cancelPress();
  });

  // mouse
  fab.addEventListener("mousedown", (e) => {
    if (e.button === 2) return; // right click handled below
    startPress();
  });
  fab.addEventListener("mouseup", (e) => cancelPress());
  fab.addEventListener("mouseleave", (e) => cancelPress());

  // правый клик как альтернатива long-press на ПК
  fab.addEventListener("contextmenu", (e) => {
    e.preventDefault();
    showFabMenu(true);
  });

  // клик по FAB
  fab.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();

    // если меню уже открыто — закрыть
    if (!menu.classList.contains("d-none")) {
      showFabMenu(false);
      return;
    }

    // обычный клик = открыть меню
    showFabMenu(true);
  });
  // клик вне меню закрывает его
  document.addEventListener("click", (e) => {
    if (menu.classList.contains("d-none")) return;
    const inMenu = e.target.closest("#fabMenu");
    const inFab = e.target.closest("#fabAdd");
    if (!inMenu && !inFab) showFabMenu(false);
  });

  // ESC закрывает меню
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") showFabMenu(false);
  });
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
function openItemModal(existing = null) {
  const isEdit = !!existing;
  const title = isEdit ? "Редактировать предмет" : "Добавить предмет";

  openModal(
    title,
    `
      <label class="form-label">Название</label>
      <input id="m_name" class="form-control" />

      <div class="row g-2 mt-2">
        <div class="col-6">
          <label class="form-label">Количество</label>
          <input id="m_qty" type="number" class="form-control" value="1" min="0" />
        </div>
      </div>

      <label class="form-label mt-2">Описание</label>
      <textarea id="m_desc" class="form-control" rows="3"></textarea>

      <label class="form-label mt-2">Статы (по желанию)</label>
      <textarea id="m_stats" class="form-control" rows="2" placeholder="Напр. +2 AC, 1d6"></textarea>
    `,
    async () => {
      const id = requireCharacterId();
      if (!id) return;

      const payload = {
        name: document.getElementById("m_name").value,
        description: document.getElementById("m_desc").value,
        stats: document.getElementById("m_stats").value,
        qty: intOrNull(document.getElementById("m_qty").value) ?? 1,
      };

      const base = `/characters/${id}/items`;
      const path = isEdit ? `${base}/${existing.id}` : base;
      const method = isEdit ? "PATCH" : "POST";

      await api(path, { method, body: JSON.stringify(payload) });
      await loadSheet(false);
    }
  );

  if (existing) {
    document.getElementById("m_name").value = existing.name || "";
    document.getElementById("m_desc").value = existing.description || "";
    document.getElementById("m_stats").value = existing.stats || "";
    document.getElementById("m_qty").value = String(existing.qty ?? 1);
  }
}

function openSpellModal(kind, existing = null) {
  const labels = {
    spell: "Заклинание",
    ability: "Способность",
    passive: "Пассивное умение",
  };

  const isEdit = !!existing;
  const title = `${isEdit ? "Редактировать" : "Добавить"} ${labels[kind] || ""}`.trim();

  openModal(
    title,
    `
      <label class="form-label">Название</label>
      <input id="m_name" class="form-control" />
      <div class="row g-2 mt-1">
        <div class="col-4">
          <label class="form-label">Уровень</label>
          <input id="m_level" type="number" class="form-control" min="0" value="0" />
        </div>
      </div>
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
      <div class="row g-2 mt-2">
        <div class="col-4">
          <label class="form-label">HP</label>
          <input id="m_cost_hp" class="form-control" placeholder="напр. 3x-5, 10%, 1/2" />
        </div>
        <div class="col-4">
          <label class="form-label">Мана</label>
          <input id="m_cost_mana" class="form-control" placeholder="напр. 5, 2x, 10%" />
        </div>
        <div class="col-4">
          <label class="form-label">Энергия</label>
          <input id="m_cost_energy" class="form-control" placeholder="напр. 1, 1/2, x" />
        </div>
      </div>

      <div class="hint mt-2">
        Формулы: x = уровень. Примеры: HP = 3x-5, Мана = 10%, Энергия = 1/2
      </div>
    `,
    async () => {
      const id = requireCharacterId();
      if (!id) return;

      const payload = {
        name: document.getElementById("m_name").value,
        level: intOrNull(document.getElementById("m_level").value) ?? 0,
        description: document.getElementById("m_desc").value,
        range: document.getElementById("m_range").value,
        duration: document.getElementById("m_duration").value,
        cost: buildCostString({
          hp: document.getElementById("m_cost_hp").value,
          mana: document.getElementById("m_cost_mana").value,
          energy: document.getElementById("m_cost_energy").value,
        }),
      };

      const base = kind === "spell" ? `/characters/${id}/spells` : `/characters/${id}/abilities`;
      const path = isEdit ? `${base}/${existing.id}` : base;
      const method = isEdit ? "PATCH" : "POST";

      await api(path, { method, body: JSON.stringify(payload) });
      await loadSheet(false);
    }
  );

  if (existing) {
    document.getElementById("m_name").value = existing.name || "";
    document.getElementById("m_level").value = String(existing.level ?? 0);
    document.getElementById("m_desc").value = existing.description || "";
    document.getElementById("m_range").value = existing.range || "";
    document.getElementById("m_duration").value = existing.duration || "";

    const parts = parseCostParts(existing.cost || "");
    document.getElementById("m_cost_hp").value = parts.hp || "";
    document.getElementById("m_cost_mana").value = parts.mana || "";
    document.getElementById("m_cost_energy").value = parts.energy || "";
  }
}

function openStateModal(existing = null) {
  const isEdit = !!existing;
  const title = isEdit ? "Редактировать состояние" : "Добавить состояние";

  openModal(
    title,
    `
      <label class="form-label">Название</label>
      <input id="m_name" class="form-control" />
          <label class="form-label mt-2">Описание</label>
          <textarea id="m_desc" class="form-control" rows="3"
            placeholder="Что делает это состояние"></textarea>
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
      const id = requireCharacterId();
      if (!id) return;

      const payload = {
        name: document.getElementById("m_name").value,
        description: document.getElementById("m_desc").value,
        hp_cost: intOrNull(document.getElementById("m_hp_cost").value) ?? 0,
        duration: document.getElementById("m_duration").value,
        is_active: document.getElementById("m_active").checked,
      };

      const base = `/characters/${id}/states`;
      const path = isEdit ? `${base}/${existing.id}` : base;
      const method = isEdit ? "PATCH" : "POST";

      await api(path, { method, body: JSON.stringify(payload) });
      await loadSheet(false);
    }
  );

  if (existing) {
    document.getElementById("m_name").value = existing.name || "";
    document.getElementById("m_desc").value = existing.description || "";
    document.getElementById("m_hp_cost").value = String(existing.hp_cost ?? 0);
    document.getElementById("m_duration").value = existing.duration || "";
    document.getElementById("m_active").checked = !!existing.is_active;
  }
}

el("btnAddItem")?.addEventListener("click", () => openItemModal());
document.getElementById("btnAddSpell")?.addEventListener("click", () => openSpellModal("spell"));
document.getElementById("btnAddAbility")?.addEventListener("click", () => openSpellModal("ability"));
document.getElementById("btnAddPassiveAbility")?.addEventListener("click", () => openSpellModal("passive"));
document.getElementById("btnAddState")?.addEventListener("click", () => openStateModal());
document.getElementById("btnCombatAddState")?.addEventListener("click", () => openStateModal());

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
  fillInput("f_xp_per_level", ch.xp_per_level);

  updateXpToNextUI();

  fillInput("f_gold", ch.gold);
  fillInput("f_silver", ch.silver);
  fillInput("f_copper", ch.copper);

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

  // экипировка: берём с сервера и кладём в draft
    state.equipDraft = { ...(state.sheet.equipment || {}) };
    renderEquipUI();


  renderCustomFields();

  // Inventory (with qty)
  renderList(
    "invList",
    (state.sheet.items || []).map((it) => ({
      ...it,
      preview: `${(it.qty ?? 1) > 1 ? `x${it.qty}` : ""}${it.stats ? `${(it.qty ?? 1) > 1 ? " · " : ""}${it.stats}` : ""}`.trim(),
    })),
    async (it) => {
      await api(`/characters/${id}/items/${it.id}`, { method: "DELETE" });
      await loadSheet(false);
    },
    {
      icon: "bi-backpack",
      clamp: true,
      onEdit: (it) => openItemModal(it),
    }
  );

  // Spells
  renderList(
    "spellsList",
    (state.sheet.spells || []).map((s) => ({
      ...s,
      preview: [`lvl ${s.level ?? 0}`, s.range, s.duration, s.cost].filter(Boolean).join(" · "),
    })),
    async (s) => {
      await api(`/characters/${id}/spells/${s.id}`, { method: "DELETE" });
      await loadSheet(false);
    },
    {
      icon: "bi-stars",
      clamp: true,
      onUse: async (s) => applyCostToCharacter(s.cost),
      onEdit: (s) => openSpellModal("spell", s),
    }
  );

  // States
  renderList(
    "statesList",
    (state.sheet.states || []).map((s) => ({
      ...s,
      preview: `${s.is_active ? "Активно" : "Неактивно"}${s.duration ? ` · ${s.duration}` : ""}${s.hp_cost ? ` · HP ${s.hp_cost}` : ""}`,
    })),
    async (s) => {
      await api(`/characters/${id}/states/${s.id}`, { method: "DELETE" });
      await loadSheet(false);
    },
    {
      icon: "bi-activity",
      clamp: true,
      onEdit: (s) => openStateModal(s),
    }
  );

  // Abilities (optional split into passive/active if the containers exist)
  const allAbilities = state.sheet.abilities || [];
  const passive = allAbilities.filter((a) => (a.cost || "").toLowerCase().includes("passive"));
  const active = allAbilities.filter((a) => !(a.cost || "").toLowerCase().includes("passive"));

  if (el("passiveAbilitiesList")) {
    renderList(
      "passiveAbilitiesList",
      passive.map((a) => ({
        ...a,
        preview: [`lvl ${a.level ?? 0}`, a.range, a.duration, a.cost].filter(Boolean).join(" · "),
      })),
      async (a) => {
        await api(`/characters/${id}/abilities/${a.id}`, { method: "DELETE" });
        await loadSheet(false);
      },
      {
        icon: "bi-shield-check",
        clamp: true,
        onEdit: (a) => openSpellModal("passive", a),
      }
    );
  }

  if (el("abilitiesList")) {
    renderList(
      "abilitiesList",
      active.map((a) => ({
        ...a,
        preview: [`lvl ${a.level ?? 0}`, a.range, a.duration, a.cost].filter(Boolean).join(" · "),
      })),
      async (a) => {
        await api(`/characters/${id}/abilities/${a.id}`, { method: "DELETE" });
        await loadSheet(false);
      },
      {
        icon: "bi-lightning-fill",
        clamp: true,
        onUse: async (a) => applyCostToCharacter(a.cost),
        onEdit: (a) => openSpellModal("ability", a),
      }
    );
    // Summons
    if (el("summonsList")) {
      const ch = state.sheet.character || {};
      renderList(
        "summonsList",
        (state.sheet.summons || []).map((s) => {
          const r = calcSummonStats(ch, s);
          return {
            ...s,
            preview: `HP ${r.hp} · M ${r.mana} · E ${r.energy} · ATK ${r.atk} · DEF ${r.def} · Ini ${r.initiative} · L ${r.luck} · S ${r.steps} · R ${r.attackRange} · x${r.count}${s.duration ? ` · ${s.duration}` : ""}`,
          };
        }),
        async (s) => {
          const id = currentChId();
          await api(`/characters/${id}/summons/${s.id}`, { method: "DELETE" });
          await loadSheet(false);
        },
        {
          icon: "bi-person-plus",
          clamp: true,
          onEdit: (s) => openSummonModal(s),
        }
      );
    }
  }
  updateCombatHudFromSheet();
  renderCombatQuickLists();
  renderCombatStates();
  renderCombatRound();
  renderCombatLog();
  setStatus("Ок ✅");
}

function fillMoneyInputsFromState() {
  const ch = state.sheet?.character;
  if (!ch) return;

  el("f_gold").value = String(ch.gold ?? 0);
  el("f_silver").value = String(ch.silver ?? 0);
  el("f_copper").value = String(ch.copper ?? 0);

  updateMoneyPreview({
    gold: ch.gold ?? 0,
    silver: ch.silver ?? 0,
    copper: ch.copper ?? 0,
  });
}

async function boot() {
  try {
    await loadMe();
    await loadTemplates();
    await loadCharacters();
    if (state.characters.length === 0) setStatus("Персонажей нет. Создай нового 👆");
    await loadSheet();

    loadBattleUiState();
    updateBattleButton();
    wireBattleControls();
    wireArmorEditor();
    renderCombatRound();
    renderCombatLog();

    wireCombatHud();
    wireCombatQuickButtons();
    wireCombatSwipe();
    wireLongPressRepeat();
    wireCombatSheet();
    wireCombatStates();
    wireCombatModeCollapse();
    wireCombatModeLongTap();
    wireCombatCompactMode();
    updateCombatModeSummary();
    updateCombatHudFromSheet();

    fillMoneyInputsFromState();
    wireFabMenu();
    wireMoneyInputs();

      // XP / Level wiring
      el("btnAddXp")?.addEventListener("click", addXpAndHandleLevelUp);
      el("btnRest")?.addEventListener("click", () => {
        restModal?.show();
      });
      el("btnMove")?.addEventListener("click", () => {
        moveModal?.show();
      });
      el("applyRest")?.addEventListener("click", async () => {
        await applyRest();
        restModal?.hide();
      });
      el("applyMove")?.addEventListener("click", async () => {
        await applyMovement();
        moveModal?.hide();
      });
      // чтобы "осталось до уровня" обновлялось при правке XP и XP-per-level
      el("f_xp")?.addEventListener("input", updateXpToNextUI);
      el("f_xp_per_level")?.addEventListener("input", updateXpToNextUI);
  } catch (e) {
    console.error(e);
    setStatus("Ошибка");
    alert(e.message);
  }
}

boot();


// +/- для ресурсов (HP/Mana/Energy) — кнопки с data-target/data-step
document.addEventListener("click", (e) => {
  const btn = e.target.closest("button.step-btn");
  if (!btn) return;

  const step = parseInt(btn.dataset.step || "0", 10);

  let input = null;
  if (btn.dataset.target) {
    input = document.getElementById(btn.dataset.target);
  } else {
    input = btn.parentElement?.querySelector("input");
  }
  if (!input) return;

  const current = parseInt(String(input.value || "0"), 10) || 0;
  const next = current + step;

  // если это стат — оставляем как раньше, можно в минус
  const isStat = !btn.dataset.target;
  if (isStat) {
    input.value = String(next);
    input.dispatchEvent(new Event("input", { bubbles: true }));
    return;
  }

  // если это ресурс — ограничиваем от 0 до max
  const targetId = btn.dataset.target;
  const max = getResourceMax(targetId);

  if (next < 0) {
    showBattleError("Недостаточно HP / маны / энергии");
    return;
  }

  if (max !== null && next > max) {
    showBattleError("Нельзя восстановить выше максимума");
    return;
  }

  input.value = String(next);
  input.dispatchEvent(new Event("input", { bubbles: true }));
});

// =========================
// Collapsing header on scroll
// =========================
(function () {
  const header = document.querySelector(".topbar");
  if (!header) return;

  let lastScroll = 0;
  const threshold = 40; // через сколько px схлопывать

  window.addEventListener("scroll", () => {
    const current = window.scrollY;

    if (current > threshold && current > lastScroll) {
      header.classList.add("is-collapsed");
    } else if (current < threshold) {
      header.classList.remove("is-collapsed");
    }

    lastScroll = current;
  }, { passive: true });
})();

const topbar = document.querySelector(".topbar");

window.addEventListener("scroll", () => {
  if (window.scrollY > 40) {
    topbar.classList.add("is-collapsed");
  } else {
    topbar.classList.remove("is-collapsed");
  }
});

// ===== Конструктор вкладок =====

const builderState = {
  tabs: [],          // [{key,title,sections:[{title,fields:[...]}]}]
  selectedTab: null,
  selectedSection: null,
  selectedField: null,
};

function bEl(id) { return document.getElementById(id); }

function openBuilder() {
  document.body.classList.add("builder-open");
  bEl("builderModal").classList.remove("d-none");
  if (!bEl("builderTplName").value) {
    bEl("builderTplName").value = `Мой шаблон ${new Date().toLocaleDateString()}`;
  }
  renderBuilder();
}

function closeBuilder() {
  document.body.classList.remove("builder-open");
  bEl("builderModal").classList.add("d-none");
}

function slugKey(s) {
  return String(s || "")
    .trim()
    .toLowerCase()
    .replaceAll(" ", "_")
    .replace(/[^a-z0-9_]/g, "");
}

function renderBuilder() {
  // Tabs
  const tabsRoot = bEl("builderTabs");
  tabsRoot.innerHTML = "";
  builderState.tabs.forEach((t) => {
    const div = document.createElement("div");
    div.className = "builder-item" + (builderState.selectedTab === t.key ? " active" : "");
    div.innerHTML = `
      <div>${escapeHtml(t.title)}</div>
      <button class="btn btn-outline-light btn-sm" type="button" data-bdel="tab" data-bkey="${escapeHtml(t.key)}">🗑</button>
    `;
    div.addEventListener("click", (e) => {
      if (e.target.closest("[data-bdel]")) return;
      builderState.selectedTab = t.key;
      builderState.selectedSection = null;
      builderState.selectedField = null;
      renderBuilder();
    });
    tabsRoot.appendChild(div);
  });

  // Sections
  const secRoot = bEl("builderSections");
  secRoot.innerHTML = "";
  const tab = builderState.tabs.find(x => x.key === builderState.selectedTab);
  const sections = tab?.sections || [];
  sections.forEach((s, idx) => {
    const skey = `${tab.key}::${idx}`;
    const div = document.createElement("div");
    div.className = "builder-item" + (builderState.selectedSection === skey ? " active" : "");
    div.innerHTML = `
      <div>${escapeHtml(s.title)}</div>
      <button class="btn btn-outline-light btn-sm" type="button" data-bdel="section" data-bkey="${escapeHtml(skey)}">🗑</button>
    `;
    div.addEventListener("click", (e) => {
      if (e.target.closest("[data-bdel]")) return;
      builderState.selectedSection = skey;
      builderState.selectedField = null;
      renderBuilder();
    });
    secRoot.appendChild(div);
  });

  // Fields
  const fRoot = bEl("builderFields");
  fRoot.innerHTML = "";
  let fields = [];
  if (tab && builderState.selectedSection) {
    const idx = Number(builderState.selectedSection.split("::")[1]);
    fields = tab.sections?.[idx]?.fields || [];
  }
  fields.forEach((f, idx) => {
    const fkey = `${builderState.selectedSection}::${idx}`;
    const div = document.createElement("div");
    div.className = "builder-item" + (builderState.selectedField === fkey ? " active" : "");
    div.innerHTML = `
      <div>${escapeHtml(f.label)} <span class="muted">(${escapeHtml(f.key)} · ${escapeHtml(f.type)})</span></div>
      <button class="btn btn-outline-light btn-sm" type="button" data-bdel="field" data-bkey="${escapeHtml(fkey)}">🗑</button>
    `;
    div.addEventListener("click", (e) => {
      if (e.target.closest("[data-bdel]")) return;
      builderState.selectedField = fkey;
      // заполнить редактор
      bEl("builderFieldLabel").value = f.label || "";
      bEl("builderFieldKey").value = f.key || "";
      bEl("builderFieldType").value = f.type || "text";
      bEl("builderFieldDefault").value = f.default ?? "";
      renderBuilder();
    });
    fRoot.appendChild(div);
  });

  // JSON preview
  const cfg = buildTemplateConfigFromBuilder();
  bEl("builderJson").textContent = JSON.stringify(cfg, null, 2);
}

function buildTemplateConfigFromBuilder() {
  // основной список вкладок: твои базовые + custom + все кастомные
  const base = ["main", "stats", "inv", "custom"];
  const customTabs = builderState.tabs.map(t => ({
    key: t.key,
    title: t.title,
    sections: t.sections || [],
  }));

  return {
    tabs: base,
    custom_tabs: customTabs,
  };
}

function addTab() {
  const title = prompt("Название вкладки?", "Заметки");
  if (!title) return;
  const key = slugKey("tab_" + title);
  builderState.tabs.push({ key, title, sections: [] });
  builderState.selectedTab = key;
  builderState.selectedSection = null;
  builderState.selectedField = null;
  renderBuilder();
}

function addSection() {
  const tab = builderState.tabs.find(x => x.key === builderState.selectedTab);
  if (!tab) return alert("Сначала выбери вкладку.");
  const title = prompt("Название раздела?", "Раздел");
  if (!title) return;
  tab.sections.push({ title, fields: [] });
  builderState.selectedSection = `${tab.key}::${tab.sections.length - 1}`;
  builderState.selectedField = null;
  renderBuilder();
}

function addField() {
  const tab = builderState.tabs.find(x => x.key === builderState.selectedTab);
  if (!tab || !builderState.selectedSection) return alert("Сначала выбери вкладку и раздел.");
  const idx = Number(builderState.selectedSection.split("::")[1]);
  const sec = tab.sections[idx];

  const label = prompt("Название поля (label)?", "Поле");
  if (!label) return;
  const key = slugKey(prompt("Ключ поля (key)?", "my_field") || "my_field");
  const type = prompt("Тип (text / textarea / number / checkbox)?", "text") || "text";

  sec.fields.push({ key, label, type: type.toLowerCase(), default: type === "number" ? 0 : "" });
  builderState.selectedField = `${builderState.selectedSection}::${sec.fields.length - 1}`;
  renderBuilder();
}

function applyFieldEdits() {
  if (!builderState.selectedField) return alert("Выбери поле.");
  const tab = builderState.tabs.find(x => x.key === builderState.selectedTab);
  const secIdx = Number(builderState.selectedSection.split("::")[1]);
  const fieldIdx = Number(builderState.selectedField.split("::")[2]);
  const field = tab.sections[secIdx].fields[fieldIdx];

  field.label = bEl("builderFieldLabel").value.trim() || field.label;
  field.key = slugKey(bEl("builderFieldKey").value.trim() || field.key);
  field.type = (bEl("builderFieldType").value || "text").toLowerCase();
  const d = bEl("builderFieldDefault").value;
  field.default = field.type === "number" ? (parseInt(d || "0", 10) || 0) : (field.type === "checkbox" ? Boolean(d === "true" || d === "1") : d);

  renderBuilder();
}

function deleteBuilderEntity(kind, bkey) {
  if (kind === "tab") {
    builderState.tabs = builderState.tabs.filter(t => t.key !== bkey);
    if (builderState.selectedTab === bkey) {
      builderState.selectedTab = null;
      builderState.selectedSection = null;
      builderState.selectedField = null;
    }
  } else if (kind === "section") {
    const tab = builderState.tabs.find(x => x.key === builderState.selectedTab);
    if (!tab) return;
    const idx = Number(bkey.split("::")[1]);
    tab.sections.splice(idx, 1);
    builderState.selectedSection = null;
    builderState.selectedField = null;
  } else if (kind === "field") {
    const tab = builderState.tabs.find(x => x.key === builderState.selectedTab);
    if (!tab) return;
    const secIdx = Number(bkey.split("::")[1]);
    const fieldIdx = Number(bkey.split("::")[2]);
    tab.sections[secIdx].fields.splice(fieldIdx, 1);
    builderState.selectedField = null;
  }
  renderBuilder();
}

async function saveBuilderAsTemplateAndApply() {
  const chId = currentChId();
  if (!chId) return alert("Нет выбранного персонажа.");

  const name = bEl("builderTplName").value.trim() || "Мой шаблон";
  const config = buildTemplateConfigFromBuilder();

  // 1) создаём шаблон
  const tpl = await api("/templates", {
    method: "POST",
    body: JSON.stringify({ name, config }),
  });

  // ожидаем, что api вернёт {id, name, config}
  const templateId = tpl?.id;
  if (!templateId) return alert("Не получил id шаблона от сервера.");

  // 2) применяем к персонажу
  await api(`/characters/${chId}/apply-template`, {
    method: "POST",
    body: JSON.stringify({ template_id: templateId }),
  });

  closeBuilder();
  await loadSheet(true);
  setStatus("Шаблон применён ✅");
}

// wiring
document.addEventListener("click", (e) => {
  const del = e.target.closest("[data-bdel]");
  if (del) {
    e.preventDefault();
    deleteBuilderEntity(del.dataset.bdel, del.dataset.bkey);
  }
});

el("btnBuilder")?.addEventListener("click", openBuilder);
bEl("builderClose")?.addEventListener("click", closeBuilder);
bEl("builderModal")?.querySelector(".modalx-backdrop")?.addEventListener("click", closeBuilder);

bEl("builderAddTab")?.addEventListener("click", addTab);
bEl("builderAddSection")?.addEventListener("click", addSection);
bEl("builderAddField")?.addEventListener("click", addField);
bEl("builderApplyField")?.addEventListener("click", applyFieldEdits);
bEl("builderSave")?.addEventListener("click", saveBuilderAsTemplateAndApply);

document.addEventListener("DOMContentLoaded", () => {
  const closeBtn = document.getElementById("builderClose");
  const modal = document.getElementById("builderModal");
  const backdrop = modal?.querySelector(".modalx-backdrop");

  function closeBuilderModal() {
    modal?.classList.add("d-none");
  }

  closeBtn?.addEventListener("click", closeBuilderModal);
  backdrop?.addEventListener("click", closeBuilderModal);
});

// Donate button
(function initDonate() {
  const btn = document.getElementById("btnDonate");
  if (!btn) return;

  const DONATE_URL = "https://www.donationalerts.com/r/d4rkl1";

  btn.addEventListener("click", (e) => {
    e.preventDefault();

    // если это Telegram WebApp — открываем внешнюю ссылку правильно
    if (window.Telegram?.WebApp?.openLink) {
      window.Telegram.WebApp.openLink(DONATE_URL, { try_instant_view: false });
      return;
    }

    // fallback для обычного браузера
    window.open(DONATE_URL, "_blank", "noopener,noreferrer");
  });
})();

// ===== Donate button (DonationAlerts) =====
document.addEventListener("DOMContentLoaded", () => {
  const DONATE_URL = "https://www.donationalerts.com/r/d4rkl1";
  const btn = document.getElementById("btnDonate");
  if (!btn) return;

  // на всякий случай держим ссылку и в href
  btn.setAttribute("href", DONATE_URL);
  btn.setAttribute("target", "_blank");
  btn.setAttribute("rel", "noopener noreferrer");

  btn.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();

    if (window.Telegram?.WebApp?.openLink) {
      window.Telegram.WebApp.openLink(DONATE_URL, { try_instant_view: false });
      return;
    }

    window.open(DONATE_URL, "_blank", "noopener,noreferrer");
  });
});

// Fallback: если вдруг кнопка появилась позже / или DOMContentLoaded не помог
document.addEventListener("click", (e) => {
  const a = e.target.closest("#btnDonate");
  if (!a) return;

  const DONATE_URL = "https://www.donationalerts.com/r/d4rkl1";
  e.preventDefault();
  e.stopPropagation();

  if (window.Telegram?.WebApp?.openLink) {
    window.Telegram.WebApp.openLink(DONATE_URL, { try_instant_view: false });
  } else {
    window.open(DONATE_URL, "_blank", "noopener,noreferrer");
  }
});

function getResourceMax(targetId) {
  const map = {
    f_hp: "f_hp_max",
    f_mana: "f_mana_max",
    f_energy: "f_energy_max",
  };
  const maxId = map[targetId];
  return maxId ? Number(el(maxId)?.value || 0) : null;
}

function clampResourceValue(targetId, value) {
  const min = 0;
  const max = getResourceMax(targetId);

  if (max === null) return Math.max(min, value);
  return Math.min(max, Math.max(min, value));
}

function appendBattleLog(text) {
  if (!text) return;
  state.battleLog = [String(text), ...(state.battleLog || [])].slice(0, 20);
  try {
    localStorage.setItem("battleLog", JSON.stringify(state.battleLog));
  } catch {}
  renderCombatLog();
}

function loadBattleUiState() {
  try {
    const savedRound = Number(localStorage.getItem("battleRound") || 1);
    state.battleRound = Number.isFinite(savedRound) && savedRound > 0 ? savedRound : 1;
  } catch {
    state.battleRound = 1;
  }

  try {
    const savedLog = JSON.parse(localStorage.getItem("battleLog") || "[]");
    state.battleLog = Array.isArray(savedLog) ? savedLog : [];
  } catch {
    state.battleLog = [];
  }

    try {
    const savedInBattle = localStorage.getItem("inBattle");
    state.inBattle = savedInBattle === "1";
  } catch {
    state.inBattle = false;
  }
}

function saveBattleMode() {
  try {
    localStorage.setItem("inBattle", state.inBattle ? "1" : "0");
  } catch {}
}

function saveBattleRound() {
  try {
    localStorage.setItem("battleRound", String(state.battleRound || 1));
  } catch {}
}

function renderCombatLog() {
  const root = el("combatLog");
  if (!root) return;

  const rows = state.battleLog || [];
  if (!rows.length) {
    root.innerHTML = `<div class="combat-log-empty">Лог пуст.</div>`;
    return;
  }

  root.innerHTML = rows
    .map((row) => `<div class="combat-log-item">${escapeHtml(row)}</div>`)
    .join("");
}

function renderCombatRound() {
  const node = el("combatRoundBadge");
  const prevBtn = el("btnPrevRound");
  const nextBtn = el("btnNextRound");

  if (!node) return;

  if (!state.inBattle) {
    node.textContent = "Бой не начат";
    prevBtn?.classList.add("d-none");
    nextBtn?.classList.add("d-none");
    return;
  }

  node.textContent = `Раунд ${state.battleRound || 1}`;
  prevBtn?.classList.remove("d-none");
  nextBtn?.classList.remove("d-none");
}

function showBattleError(text) {
  appendBattleLog(`⛔ ${text}`);
  showBattleToast(text, "error");
}

let battleToastTimer = null;

function showBattleToast(text, kind = "info") {
  let node = el("battleToast");

  if (!node) {
    node = document.createElement("div");
    node.id = "battleToast";
    node.className = "battle-toast";
    document.body.appendChild(node);
  }

  node.textContent = text;
  node.className = `battle-toast show ${kind}`;

  clearTimeout(battleToastTimer);
  battleToastTimer = setTimeout(() => {
    node.classList.remove("show");
  }, 2200);
}

function updateBattleButton() {
  const btn = el("btnBattle");
  if (!btn) return;
  btn.textContent = state.inBattle ? "🛑 Закончить бой" : "⚔️ Начать бой";
}

function startBattle() {
  state.inBattle = true;
  state.battleRound = 1;
  state.battleLog = [];

  saveBattleRound();
  saveBattleMode();

  try {
    localStorage.setItem("battleLog", JSON.stringify(state.battleLog));
  } catch {}

  appendBattleLog("⚔️ Бой начат");
  renderCombatRound();
  renderCombatLog();
  updateBattleButton();
  focusBattleMode();
}

function endBattle() {
  state.inBattle = false;
  state.battleRound = 1;
  state.battleLog = [];

  saveBattleRound();
  saveBattleMode();

  try {
    localStorage.removeItem("battleLog");
  } catch {}

  renderCombatLog();
  renderCombatRound();
  updateBattleButton();
}

function focusBattleMode() {
  const body = el("combatModeBody");
  const card = document.querySelector(".combat-mode-card");
  if (!body || !card) return;

  body.classList.remove("d-none");
  card.classList.add("is-open");
  document.querySelector('[data-combat-tab="spells"]')?.click();
  card.scrollIntoView({ behavior: "smooth", block: "start" });
}

function setResourceValue(targetId, value, logText = "") {
  const input = el(targetId);
  if (!input) return;

  const next = clampResourceValue(targetId, Number(value || 0));
  input.value = String(next);
  input.dispatchEvent(new Event("input", { bubbles: true }));

  if (logText) appendBattleLog(logText);
}

function updateCombatHudFromSheet() {
  const ch = state.sheet?.character;
  if (!ch) return;

  const hp = Number(el("f_hp")?.value || 0);
  const hpMax = Number(el("f_hp_max")?.value || 0);

  const mana = Number(el("f_mana")?.value || 0);
  const manaMax = Number(el("f_mana_max")?.value || 0);

  const energy = Number(el("f_energy")?.value || 0);
  const energyMax = Number(el("f_energy_max")?.value || 0);

  ch.hp = hp;
  ch.hp_max = hpMax;
  ch.mana = mana;
  ch.mana_max = manaMax;
  ch.energy = energy;
  ch.energy_max = energyMax;

  const hpRatio = hpMax > 0 ? Math.max(0, Math.min(100, (hp / hpMax) * 100)) : 0;
  const manaRatio = manaMax > 0 ? Math.max(0, Math.min(100, (mana / manaMax) * 100)) : 0;
  const energyRatio = energyMax > 0 ? Math.max(0, Math.min(100, (energy / energyMax) * 100)) : 0;

  const hpEl = el("hud_hp");
  if (hpEl) hpEl.textContent = `${hp}/${hpMax}`;

  const manaEl = el("hud_mana");
  if (manaEl) manaEl.textContent = `${mana}/${manaMax}`;

  const energyEl = el("hud_energy");
  if (energyEl) energyEl.textContent = `${energy}/${energyMax}`;

  const hpBar = el("hud_hp_bar");
  if (hpBar) hpBar.style.width = `${hpRatio}%`;

  const manaBar = el("hud_mana_bar");
  if (manaBar) manaBar.style.width = `${manaRatio}%`;

  const energyBar = el("hud_energy_bar");
  if (energyBar) energyBar.style.width = `${energyRatio}%`;

  const atk = Number(ch.attack || 0);
  const { perm, temp } = getArmorValues();

  ch.perm_armor = perm;
  ch.temp_armor = temp;

  const atkEl = el("hud_attack");
  if (atkEl) atkEl.textContent = String(atk);

  const armorEl = el("hud_armor");
  if (armorEl) armorEl.textContent = `${perm}+${temp}`;

  updateCombatModeSummary();

  const hpChip = document.querySelector(".combat-chip.hp");
  const manaChip = document.querySelector(".combat-chip.mana");
  const energyChip = document.querySelector(".combat-chip.energy");

  const hpRatioState = hpMax > 0 ? hp / hpMax : 0;
  const manaRatioState = manaMax > 0 ? mana / manaMax : 0;
  const energyRatioState = energyMax > 0 ? energy / energyMax : 0;

  hpChip?.classList.toggle("is-low", hpRatioState > 0 && hpRatioState <= 0.3);
  manaChip?.classList.toggle("is-low", manaRatioState > 0 && manaRatioState <= 0.25);
  energyChip?.classList.toggle("is-low", energyRatioState > 0 && energyRatioState <= 0.25);

  hpChip?.classList.toggle("is-empty", hp <= 0);
  manaChip?.classList.toggle("is-empty", mana <= 0);
  energyChip?.classList.toggle("is-empty", energy <= 0);

  hpChip?.classList.remove("is-critical");

  if (hpRatioState > 0 && hpRatioState <= 0.25) {
    hpChip?.classList.add("is-critical");
  }
}

async function applyRest() {
  const hpPercent = Number(el("rest_hp")?.value || 0);
  const manaPercent = Number(el("rest_mana")?.value || 0);
  const energyPercent = Number(el("rest_energy")?.value || 0);

  const hpMax = Number(el("f_hp_max")?.value || 0);
  const manaMax = Number(el("f_mana_max")?.value || 0);
  const energyMax = Number(el("f_energy_max")?.value || 0);

  const hp = Number(el("f_hp")?.value || 0);
  const mana = Number(el("f_mana")?.value || 0);
  const energy = Number(el("f_energy")?.value || 0);

  const addHp = Math.floor(hpMax * hpPercent / 100);
  const addMana = Math.floor(manaMax * manaPercent / 100);
  const addEnergy = Math.floor(energyMax * energyPercent / 100);

  const newHp = Math.min(hpMax, hp + addHp);
  const newMana = Math.min(manaMax, mana + addMana);
  const newEnergy = Math.min(energyMax, energy + addEnergy);

  el("f_hp").value = String(newHp);
  el("f_mana").value = String(newMana);
  el("f_energy").value = String(newEnergy);

  el("f_hp").dispatchEvent(new Event("input", { bubbles: true }));
  el("f_mana").dispatchEvent(new Event("input", { bubbles: true }));
  el("f_energy").dispatchEvent(new Event("input", { bubbles: true }));

  appendBattleLog(`🛌 Отдых: HP +${newHp - hp}, Mana +${newMana - mana}, Energy +${newEnergy - energy}`);

  updateCombatHudFromSheet();
  await saveMain();
}

async function applyMovement() {
  const percent = Number(el("move_energy_percent")?.value || 0);

  const energyMax = Number(el("f_energy_max")?.value || 0);
  const energy = Number(el("f_energy")?.value || 0);

  const cost = Math.floor(energyMax * percent / 100);
  const newEnergy = Math.max(0, energy - cost);

  if (cost <= 0) {
    showBattleError("Задай корректный процент перемещения");
    return;
  }

  el("f_energy").value = String(newEnergy);
  el("f_energy").dispatchEvent(new Event("input", { bubbles: true }));

  appendBattleLog(`👣 Перемещение: Energy -${energy - newEnergy}`);

  updateCombatHudFromSheet();
  await saveMain();
}

function wireCombatHud() {
  // обновлять HUD при любых изменениях ресурсов
  ["f_hp","f_hp_max","f_mana","f_mana_max","f_energy","f_energy_max"].forEach((id) => {
    el(id)?.addEventListener("input", updateCombatHudFromSheet);
    el(id)?.addEventListener("change", updateCombatHudFromSheet);
  });
}

function quickApplyResource(targetId, delta) {
  const input = el(targetId);
  if (!input) return;

  const current = Number(input.value || 0);
  const nextRaw = current + Number(delta || 0);
  const max = getResourceMax(targetId);

  if (nextRaw < 0) {
    showBattleError("Недостаточно ресурса");
    return;
  }

  if (max !== null && nextRaw > max) {
    showBattleError("Нельзя выше максимума");
    return;
  }

  input.value = String(nextRaw);
  input.dispatchEvent(new Event("input", { bubbles: true }));

  if (targetId === "f_hp" && delta < 0 && navigator.vibrate) {
    navigator.vibrate(30);
  }
  if (targetId === "f_hp") {
    if (delta < 0) appendBattleLog(`💥 Получено ${Math.abs(delta)} урона`);
    if (delta > 0) appendBattleLog(`💚 Восстановлено ${delta} HP`);
  } else if (targetId === "f_mana") {
    if (delta < 0) appendBattleLog(`🔷 Потрачено ${Math.abs(delta)} маны`);
    if (delta > 0) appendBattleLog(`🔷 Восстановлено ${delta} маны`);
  } else if (targetId === "f_energy") {
    if (delta < 0) appendBattleLog(`🟡 Потрачено ${Math.abs(delta)} энергии`);
    if (delta > 0) appendBattleLog(`🟡 Восстановлено ${delta} энергии`);
  }
}

function wireCombatQuickButtons() {
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-quick-target]");
    if (!btn) return;

    const targetId = btn.getAttribute("data-quick-target");
    const step = Number(btn.getAttribute("data-quick-step") || 0);

    if (!targetId || !Number.isFinite(step)) return;
    quickApplyResource(targetId, step);
  });
}

function clearCombatSwipeState(chip) {
  if (!chip) return;
  chip.classList.remove("is-swiping", "swipe-left", "swipe-right");
  chip.style.removeProperty("transform");
}

function resolveCombatSwipeDelta(dx) {
  const abs = Math.abs(dx);

  if (abs < 36) return 0;
  if (abs >= 90) return dx > 0 ? 5 : -5;
  return dx > 0 ? 1 : -1;
}

function wireSwipeForCombatChip(selector, targetId) {
  const chip = document.querySelector(selector);
  if (!chip) return;

  chip.classList.add("swipe-enabled");

  let startX = 0;
  let startY = 0;
  let currentX = 0;
  let active = false;
  let locked = false;

  const onPointerDown = (e) => {
    // не начинаем свайп с кнопок
    if (e.target.closest("button")) return;

    active = true;
    locked = false;
    startX = e.clientX;
    startY = e.clientY;
    currentX = 0;

    chip.classList.add("is-swiping");
  };

  const onPointerMove = (e) => {
    if (!active) return;

    const dx = e.clientX - startX;
    const dy = e.clientY - startY;

    // если это скорее вертикальный жест — отпускаем
    if (!locked) {
      if (Math.abs(dy) > 14 && Math.abs(dy) > Math.abs(dx)) {
        active = false;
        clearCombatSwipeState(chip);
        return;
      }
      if (Math.abs(dx) > 8) {
        locked = true;
      }
    }

    if (!locked) return;

    currentX = dx;
    const limited = Math.max(-42, Math.min(42, dx));

    chip.classList.toggle("swipe-left", limited < -10);
    chip.classList.toggle("swipe-right", limited > 10);
    chip.style.transform = `translateX(${limited}px) scale(.985)`;
  };

  const finish = () => {
    if (!active && !locked) {
      clearCombatSwipeState(chip);
      return;
    }

    const delta = resolveCombatSwipeDelta(currentX);
    clearCombatSwipeState(chip);

    active = false;
    locked = false;
    currentX = 0;

    if (!delta) return;
    quickApplyResource(targetId, delta);
  };

  const cancel = () => {
    active = false;
    locked = false;
    currentX = 0;
    clearCombatSwipeState(chip);
  };

  chip.addEventListener("pointerdown", onPointerDown);
  chip.addEventListener("pointermove", onPointerMove);
  chip.addEventListener("pointerup", finish);
  chip.addEventListener("pointercancel", cancel);
  chip.addEventListener("lostpointercapture", cancel);
}

function wireCombatSwipe() {
  wireSwipeForCombatChip(".combat-chip.hp", "f_hp");
  wireSwipeForCombatChip(".combat-chip.mana", "f_mana");
  wireSwipeForCombatChip(".combat-chip.energy", "f_energy");
}

function triggerRepeatableAction(btn) {
  if (!btn) return;

  // step-btn
  if (btn.classList.contains("step-btn")) {
    const step = parseInt(btn.dataset.step || "0", 10);

    let input = null;
    if (btn.dataset.target) {
      input = document.getElementById(btn.dataset.target);
    } else {
      input = btn.parentElement?.querySelector("input");
    }
    if (!input) return;

    const current = parseInt(String(input.value || "0"), 10) || 0;
    const next = current + step;

    const isStat = !btn.dataset.target;
    if (isStat) {
      input.value = String(next);
      input.dispatchEvent(new Event("input", { bubbles: true }));
      return;
    }

    const targetId = btn.dataset.target;
    const max = getResourceMax(targetId);

    if (next < 0) return;
    if (max !== null && next > max) return;

    input.value = String(next);
    input.dispatchEvent(new Event("input", { bubbles: true }));
    return;
  }

  // quick buttons
  if (btn.hasAttribute("data-quick-target")) {
    const targetId = btn.getAttribute("data-quick-target");
    const step = Number(btn.getAttribute("data-quick-step") || 0);

    if (!targetId || !Number.isFinite(step)) return;
    quickApplyResource(targetId, step);
    return;
  }

  // compact-mode buttons
  if (btn.hasAttribute("data-compact-action")) {
    const action = btn.getAttribute("data-compact-action");

    if (action === "hit") {
      quickApplyResource("f_hp", -10);
      return;
    }

    if (action === "rest") {
      el("btnRest")?.click();
      return;
    }

    if (action === "move") {
      el("btnMove")?.click();
      return;
    }

    if (action === "armor") {
      openArmorModal();
    }
    return;
  }
}

function wireLongPressRepeat() {
  const HOLD_DELAY = 300;
  const REPEAT_EVERY = 120;

  let holdTimer = null;
  let repeatTimer = null;
  let activeBtn = null;
  let longPressTriggered = false;

  const clearTimers = () => {
    if (holdTimer) {
      clearTimeout(holdTimer);
      holdTimer = null;
    }
    if (repeatTimer) {
      clearInterval(repeatTimer);
      repeatTimer = null;
    }
  };

  const stopHold = () => {
    clearTimers();

    if (activeBtn) {
      activeBtn.classList.remove("is-holding");
    }

    activeBtn = null;
    longPressTriggered = false;
  };

  const startHold = (btn) => {
    if (!btn) return;

    activeBtn = btn;
    longPressTriggered = false;
    activeBtn.classList.add("is-holding");

    holdTimer = setTimeout(() => {
      longPressTriggered = true;

      triggerRepeatableAction(activeBtn);

      repeatTimer = setInterval(() => {
        triggerRepeatableAction(activeBtn);
      }, REPEAT_EVERY);
    }, HOLD_DELAY);
  };

  document.addEventListener("pointerdown", (e) => {
    const btn = e.target.closest(".step-btn, .combat-quick-btn, .combat-action-btn, .combat-mini-btn");
    if (!btn) return;

    // не трогаем кнопки, которые не стоит повторять
    const compactAction = btn.getAttribute("data-compact-action");
    if (compactAction === "rest" || compactAction === "move" || compactAction === "armor") return;

    startHold(btn);
  });

  document.addEventListener("pointerup", stopHold);
  document.addEventListener("pointercancel", stopHold);
  document.addEventListener("pointerleave", stopHold);

  document.addEventListener("dragstart", stopHold);
  window.addEventListener("blur", stopHold);

  // блокируем "обычный клик" после long-press,
  // чтобы не было лишнего +1 / -1 при отпускании
  document.addEventListener("click", (e) => {
    if (!longPressTriggered) return;

    const btn = e.target.closest(".step-btn, .combat-quick-btn, .combat-action-btn, .combat-mini-btn");
    if (!btn) return;

    e.preventDefault();
    e.stopPropagation();

    longPressTriggered = false;
  }, true);
}

function renderCombatQuickLists() {
  const id = currentChId();
  if (!id || !state.sheet) return;

  const q = String(el("combatSearch")?.value || "").trim().toLowerCase();

  const spells = (state.sheet.spells || [])
    .filter(s => !q || (String(s.name||"").toLowerCase().includes(q) || String(s.description||"").toLowerCase().includes(q)))
    .map((s) => ({
      ...s,
      preview: [`lvl ${s.level ?? 0}`, s.range, s.duration, s.cost].filter(Boolean).join(" · "),
    }));

  const abilities = (state.sheet.abilities || [])
    .filter(a => !q || (String(a.name||"").toLowerCase().includes(q) || String(a.description||"").toLowerCase().includes(q)))
    .map((a) => ({
      ...a,
      preview: [`lvl ${a.level ?? 0}`, a.range, a.duration, a.cost].filter(Boolean).join(" · "),
    }));

  // Заклинания (use = списать cost)
  renderList(
    "combatQuickSpells",
    spells,
    async (s) => {
      await api(`/characters/${id}/spells/${s.id}`, { method: "DELETE" });
      await loadSheet(false);
    },
    { icon: "bi-stars", clamp: true, onUse: async (s) => applyCostToCharacter(s.cost, s.name || "Заклинание") }
  );

  // Умения (use = списать cost)
  renderList(
    "combatQuickAbilities",
    abilities,
    async (a) => {
      await api(`/characters/${id}/abilities/${a.id}`, { method: "DELETE" });
      await loadSheet(false);
    },
    { icon: "bi-lightning-fill", clamp: true, onUse: async (a) => applyCostToCharacter(a.cost, a.name || "Умение") }
  );
}

function renderCombatStates() {
  const root = el("combatStatesList");
  const states = state.sheet?.states || [];
  if (!root) return;

  if (!states.length) {
    root.innerHTML = `<div class="combat-state-empty">Нет активных состояний.</div>`;
    return;
  }

  root.innerHTML = states.map((s) => {
    const duration = String(s.duration || "").trim();
    const hpCost = Number(s.hp_cost || 0);
    const active = !!s.is_active;

    return `
      <div class="combat-state-chip" data-state-id="${s.id}">
        <span class="combat-state-name">${escapeHtml(s.name || "Состояние")}</span>
        <span class="combat-state-meta">
          ${active ? "активно" : "неактивно"}
          ${duration ? ` · ${escapeHtml(duration)}` : ""}
          ${hpCost ? ` · HP ${hpCost}` : ""}
        </span>

        <div class="combat-state-actions">
          <button class="combat-state-btn" type="button" data-state-act="tick" title="Минус ход">−1</button>
          <button class="combat-state-btn" type="button" data-state-act="toggle" title="Вкл/выкл">⟳</button>
          <button class="combat-state-btn" type="button" data-state-act="delete" title="Удалить">×</button>
        </div>
      </div>
    `;
  }).join("");
}

function parseDurationValue(raw) {
  const s = String(raw || "").trim();
  const m = s.match(/^(\d+)(.*)$/);
  if (!m) return null;

  return {
    value: Number(m[1]),
    suffix: m[2] || "",
  };
}

async function combatStateTick(stateId) {
  const chId = currentChId();
  const states = state.sheet?.states || [];
  const st = states.find((x) => Number(x.id) === Number(stateId));
  if (!chId || !st) return;

  const parsed = parseDurationValue(st.duration);
  if (!parsed) return;

  const nextValue = parsed.value - 1;

  if (nextValue <= 0) {
    await api(`/characters/${chId}/states/${stateId}`, { method: "DELETE" });
  } else {
    await api(`/characters/${chId}/states/${stateId}`, {
      method: "PATCH",
      body: JSON.stringify({
        duration: `${nextValue}${parsed.suffix}`,
      }),
    });
  }

  await loadSheet(false);
}

async function combatStateToggle(stateId) {
  const chId = currentChId();
  const states = state.sheet?.states || [];
  const st = states.find((x) => Number(x.id) === Number(stateId));
  if (!chId || !st) return;

  await api(`/characters/${chId}/states/${stateId}`, {
    method: "PATCH",
    body: JSON.stringify({
      is_active: !st.is_active,
    }),
  });

  await loadSheet(false);
}

async function combatStateDelete(stateId) {
  const chId = currentChId();
  if (!chId) return;

  await api(`/characters/${chId}/states/${stateId}`, { method: "DELETE" });
  await loadSheet(false);
}

async function combatNextTurn() {
  const states = state.sheet?.states || [];
  for (const st of states) {
    const parsed = parseDurationValue(st.duration);
    if (!parsed) continue;

    const nextValue = parsed.value - 1;
    if (nextValue <= 0) {
      await api(`/characters/${currentChId()}/states/${st.id}`, { method: "DELETE" });
    } else {
      await api(`/characters/${currentChId()}/states/${st.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          duration: `${nextValue}${parsed.suffix}`,
        }),
      });
    }
  }

  await loadSheet(false);
}

async function combatClearStates() {
  const states = state.sheet?.states || [];
  for (const st of states) {
    await api(`/characters/${currentChId()}/states/${st.id}`, { method: "DELETE" });
  }

  await loadSheet(false);
}

function wireCombatStates() {
  el("btnNextTurn")?.addEventListener("click", combatNextTurn);
  el("btnClearStates")?.addEventListener("click", combatClearStates);
  el("btnCombatAddState")?.addEventListener("click", () => openStateModal());

  document.addEventListener("click", async (e) => {
    const btn = e.target.closest("[data-state-act]");
    if (btn) {
      const chip = btn.closest("[data-state-id]");
      const stateId = chip?.getAttribute("data-state-id");
      const act = btn.getAttribute("data-state-act");

      if (!stateId) return;

      if (act === "tick") return combatStateTick(stateId);
      if (act === "toggle") return combatStateToggle(stateId);
      if (act === "delete") return combatStateDelete(stateId);
      return;
    }

    const chip = e.target.closest(".combat-state-chip");
    if (!chip) return;

    const stateId = Number(chip.getAttribute("data-state-id"));
    if (!stateId) return;

    const st = (state.sheet?.states || []).find((x) => Number(x.id) === stateId);
    if (!st) return;

    openStateModal(st);
  });
}

function wireCombatSheet() {
  document.addEventListener("click", (e) => {
    const tabBtn = e.target.closest("[data-combat-tab]");
    if (!tabBtn) return;

    document.querySelectorAll("[data-combat-tab]").forEach(b => b.classList.remove("active"));
    tabBtn.classList.add("active");

    const tab = tabBtn.getAttribute("data-combat-tab");
    el("combatQuickSpells")?.classList.toggle("d-none", tab !== "spells");
    el("combatQuickAbilities")?.classList.toggle("d-none", tab !== "abilities");
  });

  el("combatSearch")?.addEventListener("input", renderCombatQuickLists);
}

function updateCombatModeSummary() {
  const ch = state.sheet?.character;
  const node = el("combatModeSummary");
  if (!ch || !node) return;

  const hp = Number(ch.hp || 0);
  const hpMax = Number(ch.hp_max || 0);

  const mana = Number(ch.mana || 0);
  const manaMax = Number(ch.mana_max || 0);

  const energy = Number(ch.energy || 0);
  const energyMax = Number(ch.energy_max || 0);

  const atk = Number(ch.attack || 0);
  const perm = Number(ch.perm_armor || 0);
  const temp = Number(ch.temp_armor || 0);

  node.textContent = `HP ${hp}/${hpMax} · Mana ${mana}/${manaMax} · Energy ${energy}/${energyMax} · DMG ${atk} · Armor ${perm}+${temp}`;
}

function wireCombatModeCollapse() {
  const toggle = el("combatModeToggle");
  const body = el("combatModeBody");
  const card = document.querySelector(".combat-mode-card");

  if (!toggle || !body || !card) return;

  let isOpen = false;

  const setOpen = (open) => {
    isOpen = open;
    body.classList.toggle("d-none", !open);
    card.classList.toggle("is-open", open);
  };

  setOpen(false);

  const onToggle = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setOpen(!isOpen);
  };

  toggle.addEventListener("click", onToggle);
  toggle.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      onToggle(e);
    }
  });
}

function wireCombatModeLongTap() {
  const elToggle = el("combatModeToggle");
  if (!elToggle) return;

  let timer = null;
  let longTriggered = false;

  const start = () => {
    longTriggered = false;
    timer = setTimeout(() => {
      longTriggered = true;

      const body = el("combatModeBody");
      const card = document.querySelector(".combat-mode-card");

      if (body && card) {
        body.classList.remove("d-none");
        card.classList.add("is-open");
      }

      document.querySelector('[data-combat-tab="spells"]')?.click();
      el("combatQuickSpells")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }, 500);
  };

  const cancel = () => {
    clearTimeout(timer);
  };

  elToggle.addEventListener("touchstart", start, { passive: true });
  elToggle.addEventListener("touchend", cancel);
  elToggle.addEventListener("touchmove", cancel);
  elToggle.addEventListener("touchcancel", cancel);
}

function setCombatCompactMode(enabled) {
  const body = el("combatModeBody");
  const card = document.querySelector(".combat-mode-card");
  const btn = el("btnCombatCompact");

  if (!body || !card || !btn) return;

  body.classList.toggle("is-compact", !!enabled);
  card.classList.toggle("is-compact", !!enabled);
  btn.setAttribute("aria-pressed", enabled ? "true" : "false");
  btn.textContent = enabled ? "Полный режим" : "Мини-режим";

  try {
    localStorage.setItem("combatCompactMode", enabled ? "1" : "0");
  } catch {}
}

function getCombatCompactMode() {
  try {
    return localStorage.getItem("combatCompactMode") === "1";
  } catch {
    return false;
  }
}

function wireCombatCompactMode() {
  const btn = el("btnCombatCompact");
  const body = el("combatModeBody");

  if (!btn || !body) return;

  setCombatCompactMode(getCombatCompactMode());

  btn.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();

    const next = !body.classList.contains("is-compact");
    setCombatCompactMode(next);
  });

  document.addEventListener("click", (e) => {
    const compactBtn = e.target.closest("[data-compact-action]");
    if (!compactBtn) return;

    const action = compactBtn.getAttribute("data-compact-action");

    if (action === "hit") {
      quickApplyResource("f_hp", -10);
      return;
    }

    if (action === "rest") {
      el("btnRest")?.click();
      return;
    }

    if (action === "move") {
      el("btnMove")?.click();
      return;
    }

    if (action === "armor") {
      openArmorModal();
    }
  });
}

function wireBattleControls() {
  el("btnBattle")?.addEventListener("click", () => {
    if (state.inBattle) {
      endBattle();
    } else {
      startBattle();
    }
  });

  el("btnNextRound")?.addEventListener("click", () => {
    if (!state.inBattle) {
      showBattleError("Сначала начни бой");
      return;
    }

    state.battleRound = (state.battleRound || 1) + 1;
    saveBattleRound();
    renderCombatRound();
    appendBattleLog(`🔄 Раунд ${state.battleRound}`);
  });

  el("btnPrevRound")?.addEventListener("click", () => {
    if (!state.inBattle) {
      showBattleError("Сначала начни бой");
      return;
    }

    state.battleRound = Math.max(1, (state.battleRound || 1) - 1);
    saveBattleRound();
    renderCombatRound();
    appendBattleLog(`↩️ Раунд ${state.battleRound}`);
  });
}

document.addEventListener("click", (e) => {
  const clearBtn = e.target.closest("#btnClearCombatLog");
  if (!clearBtn) return;

  e.preventDefault();
  e.stopPropagation();

  state.battleLog = [];

  try {
    localStorage.removeItem("battleLog");
  } catch {}

  renderCombatLog();
});

function getStatInputByKey(key) {
  return document.querySelector(`#statsCombat input[data-key="${key}"]`);
}

function getArmorValues() {
  const perm = Math.max(0, intOrNull(getStatInputByKey("perm_armor")?.value) ?? 0);
  const temp = Math.max(0, intOrNull(getStatInputByKey("temp_armor")?.value) ?? 0);
  return { perm, temp };
}

function setArmorValues(perm, temp) {
  const permInput = getStatInputByKey("perm_armor");
  const tempInput = getStatInputByKey("temp_armor");

  if (permInput) permInput.value = String(Math.max(0, perm));
  if (tempInput) tempInput.value = String(Math.max(0, temp));
}

function syncArmorModalInputs() {
  const { perm, temp } = getArmorValues();
  el("armor_perm_input").value = String(perm);
  el("armor_temp_input").value = String(temp);
}

function updateArmorHudFromInputs() {
  const { perm, temp } = getArmorValues();

  if (state.sheet?.character) {
    state.sheet.character.perm_armor = perm;
    state.sheet.character.temp_armor = temp;
  }

  el("hud_armor").textContent = `${perm}+${temp}`;
  updateCombatModeSummary();
}

function openArmorModal() {
  syncArmorModalInputs();
  armorModal?.show();
}

async function applyArmorChanges() {
  const perm = Math.max(0, intOrNull(el("armor_perm_input")?.value) ?? 0);
  const temp = Math.max(0, intOrNull(el("armor_temp_input")?.value) ?? 0);

  setArmorValues(perm, temp);
  updateArmorHudFromInputs();
  appendBattleLog(`🛡 Броня: ${perm}+${temp}`);

  await saveMain({
    perm_armor: perm,
    temp_armor: temp,
  });
}

function wireArmorEditor() {
  const armorChip = document.querySelector("#hud_armor")?.closest(".combat-chip");
  armorChip?.classList.add("armor-clickable");

  armorChip?.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    openArmorModal();
  });

  el("applyArmor")?.addEventListener("click", async () => {
    await applyArmorChanges();
    armorModal?.hide();
  });

  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-armor-act]");
    if (!btn) return;

    const [kind, action] = String(btn.getAttribute("data-armor-act") || "").split(":");
    const inputId = kind === "perm" ? "armor_perm_input" : "armor_temp_input";
    const input = el(inputId);
    if (!input) return;

    let current = intOrNull(input.value) ?? 0;

    if (action === "reset") {
      current = 0;
    } else {
      current = Math.max(0, current + Number(action || 0));
    }

    input.value = String(current);
  });
}

el("btnFullRestore")?.addEventListener("click", async () => {
  const hpMax = Number(el("f_hp_max")?.value || 0);
  const manaMax = Number(el("f_mana_max")?.value || 0);
  const energyMax = Number(el("f_energy_max")?.value || 0);

  el("f_hp").value = String(hpMax);
  el("f_mana").value = String(manaMax);
  el("f_energy").value = String(energyMax);

  el("f_hp").dispatchEvent(new Event("input", { bubbles: true }));
  el("f_mana").dispatchEvent(new Event("input", { bubbles: true }));
  el("f_energy").dispatchEvent(new Event("input", { bubbles: true }));

  appendBattleLog("🛌 Полный отдых: все ресурсы восстановлены");
  updateCombatHudFromSheet();
  await saveMain();
});