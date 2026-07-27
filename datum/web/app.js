/* app.js — wires the Datum UI to the real API.
   No mock data. Every number on screen came out of core/ or review/. */

const $  = (id) => document.getElementById(id);
const el = (sel) => document.querySelector(sel);

const state = {
  plans: [],          // manifest records
  selected: null,     // plan_id selected in Tab 1
  reviewPlan: null,   // plan_id selected in Tab 2
  history: [],        // chat turns for the current plan
  checks: null,       // deterministic geometry for the current plan
};

/* ---------------- tabs ---------------- */
const tabs = [...document.querySelectorAll('.tab')];

function selectTab(tab) {
  tabs.forEach(x => {
    const on = x === tab;
    x.setAttribute('aria-selected', on);
    $(x.getAttribute('aria-controls')).hidden = !on;
  });
  history.replaceState(null, '', tab.id === 't2' ? '#review' : '#extract');
  if (tab.id === 't2') refreshPicker();
}

tabs.forEach(t => t.addEventListener('click', () => selectTab(t)));

// Deep link: /#review opens the access review tab directly.
if (location.hash === '#review') selectTab(tabs[1]);

/* ---------------- segmented controls ---------------- */
document.querySelectorAll('.seg').forEach(seg => {
  seg.addEventListener('click', e => {
    const b = e.target.closest('button'); if (!b) return;
    [...seg.children].forEach(x => x.setAttribute('aria-pressed', x === b));
    seg.dataset.value = b.dataset.v;
  });
});

/* ---------------- helpers ---------------- */
function banner(id, msg, kind = 'err') {
  const b = $(id);
  if (!msg) { b.hidden = true; return; }
  b.hidden = false;
  b.className = 'banner' + (kind === 'warn' ? ' warn' : '');
  b.textContent = msg;
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch (_) {}
    throw new Error(detail);
  }
  return res.json();
}

const fmtNum = (v, dp = 2, unit = '') =>
  (v === null || v === undefined) ? '—' : `${Number(v).toFixed(dp)}${unit}`;

const escapeHtml = (s) => String(s).replace(/[&<>"]/g, c =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

const STATUS = {
  ok:        ['ok', 'Annotated'],
  estimated: ['wr', 'Estimated'],
  failed:    ['no', 'Failed'],
};

/* ---------------- folder picker ----------------
   The browser can't hand a server a real directory path — a file input gives
   file contents, not locations — so browsing happens server-side. */
let pkPath = null;

async function pkLoad(path) {
  try {
    const r = await api(`/api/browse${path ? `?path=${encodeURIComponent(path)}` : ''}`);
    pkPath = r.path;
    $('pkPath').textContent = r.path;
    $('pkUp').disabled = !r.parent;
    $('pkUp').dataset.path = r.parent || '';
    $('pkHome').dataset.path = r.home;
    $('pkHint').textContent = r.plans_here
      ? `${r.plans_here} plan folder${r.plans_here === 1 ? '' : 's'} directly in here — "Use this folder" is ready.`
      : 'No plan folders directly in here. Open a sub-folder, or pick one showing a plan count.';
    $('pkUse').disabled = false;

    $('pkList').innerHTML = r.dirs.length
      ? r.dirs.map(d => `<button class="pk-item" data-path="${escapeHtml(d.path)}">
          <span class="n">${escapeHtml(d.name)}</span>
          ${d.plans ? `<span class="c">${d.plans} plan${d.plans === 1 ? '' : 's'}</span>` : ''}
        </button>`).join('')
      : `<div class="pk-empty">No sub-folders here.</div>`;
    $('pkList').querySelectorAll('.pk-item').forEach(b => {
      b.onclick = () => pkLoad(b.dataset.path);
    });
    $('pkList').scrollTop = 0;
  } catch (e) {
    $('pkHint').textContent = `Cannot open that folder: ${e.message}`;
    $('pkList').innerHTML = `<div class="pk-empty">${escapeHtml(e.message)}</div>`;
  }
}

function openPicker() {
  $('picker-modal').hidden = false;
  const current = $('root').value.trim();
  pkLoad(current && current.startsWith('/') ? current : null);
}
const closePicker = () => { $('picker-modal').hidden = true; };

$('browse').onclick = openPicker;
$('root').onclick = openPicker;
$('pkClose').onclick = closePicker;
$('pkUp').onclick = () => { const p = $('pkUp').dataset.path; if (p) pkLoad(p); };
$('pkHome').onclick = () => pkLoad($('pkHome').dataset.path);
$('pkUse').onclick = () => {
  if (!pkPath) return;
  $('root').value = pkPath;
  closePicker();
  $('scan').click();
};
$('picker-modal').addEventListener('click', e => {
  if (e.target === $('picker-modal')) closePicker();
});
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && !$('picker-modal').hidden) closePicker();
});

/* ---------------- Tab 1 — scan ---------------- */
$('scan').onclick = async () => {
  banner('err1', null);
  $('scan').disabled = true;
  $('barlab').textContent = 'Scanning…';
  try {
    const r = await api('/api/scan', {
      method: 'POST',
      body: JSON.stringify({ root: $('root').value.trim() }),
    });
    $('s1').textContent = r.plans;
    $('s2').textContent = r.pngs;
    $('s3').textContent = '—';
    $('s4').textContent = r.already_annotated || 0;
    $('metaDataset').textContent = r.root.split('/').filter(Boolean).slice(-1)[0] || r.root;
    $('run').disabled = r.plans === 0;
    $('barlab').textContent = r.plans
      ? `Ready — ${r.plans} plans queued`
      : 'No plans found in that folder';
    if (!r.plans) banner('err1', `No folder under ${r.root} contains a model.svg with a PNG beside it.`, 'warn');
    await loadManifest();
  } catch (e) {
    banner('err1', `Scan failed: ${e.message}`);
    $('barlab').textContent = 'Idle';
  } finally {
    $('scan').disabled = false;
  }
};

/* ---------------- Tab 1 — annotate, with real SSE progress ---------------- */
$('run').onclick = async () => {
  banner('err1', null);
  $('run').disabled = true;
  $('scan').disabled = true;
  $('bar').style.width = '0%';
  $('barlab').textContent = 'Starting…';
  $('footState').textContent = 'annotating';

  try {
    const job = await api('/api/annotate', {
      method: 'POST',
      body: JSON.stringify({
        root: $('root').value.trim(),
        units: $('units').dataset.value,
        style: $('style').dataset.value,
        room_labels: $('roomLabels').value === 'true',
        resume: $('resume').checked,
      }),
    });

    await new Promise((resolve) => {
      const es = new EventSource(`/api/jobs/${job.job_id}/events`);
      es.onmessage = (ev) => {
        const m = JSON.parse(ev.data);
        if (m.type === 'progress') {
          const pct = m.total ? (m.done / m.total * 100) : 0;
          $('bar').style.width = `${pct}%`;
          $('barlab').textContent = `${m.status === 'skipped' ? 'Skipping' : 'Annotating'} ${m.done} / ${m.total} — ${m.plan_id}`;
        } else if (m.type === 'done') {
          $('bar').style.width = '100%';
          const c = m.counts || {};
          const parts = Object.entries(c).map(([k, v]) => `${v} ${k}`);
          $('barlab').textContent = `Done — ${parts.join(', ')}`;
          es.close(); resolve();
        } else if (m.type === 'error') {
          banner('err1', `Batch failed: ${m.error}`);
          $('barlab').textContent = 'Failed';
          es.close(); resolve();
        }
      };
      es.onerror = () => { es.close(); resolve(); };
    });

    await loadManifest();
  } catch (e) {
    banner('err1', `Could not start the batch: ${e.message}`);
    $('barlab').textContent = 'Idle';
  } finally {
    $('run').disabled = false;
    $('scan').disabled = false;
    $('footState').textContent = 'idle';
  }
};

/* ---------------- results table ---------------- */
async function loadManifest() {
  try {
    const r = await api('/api/plans');
    state.plans = r.plans || [];
    paintRows();
    const resolved = state.plans.filter(p => p.scale_source === 'room_label_crosscheck').length;
    if (state.plans.length) {
      $('s3').textContent = resolved;
      $('s4').textContent = state.plans.filter(p => p.status !== 'failed').length;
    }
    refreshPicker();
  } catch (e) {
    banner('err1', `Could not read the manifest: ${e.message}`);
  }
}

function paintRows() {
  const tb = $('rows');
  if (!state.plans.length) {
    tb.innerHTML = `<tr><td colspan="7" style="color:var(--ink-3);padding:26px 12px;text-align:center;font-family:var(--body)">Scan a folder to begin.</td></tr>`;
    return;
  }
  tb.innerHTML = state.plans.map(p => {
    const [cls, lab] = STATUS[p.status] || ['nu', p.status || '?'];
    const rooms = (p.rooms || []).length;
    return `<tr data-id="${escapeHtml(p.plan_id)}">
      <td>${escapeHtml(p.plan_id)}</td>
      <td>${p.px_per_m ? `<span class="measure-sm">${Number(p.px_per_m).toFixed(1)}</span> px/m` : '—'}</td>
      <td class="measure">${fmtNum(p.overall_width_m, 2, ' m')}</td>
      <td class="measure">${fmtNum(p.overall_depth_m, 2, ' m')}</td>
      <td class="measure">${fmtNum(p.internal_area_m2, 1, ' m²')}</td>
      <td>${rooms}</td>
      <td><span class="chip ${cls}">${lab}</span></td>
    </tr>`;
  }).join('');

  tb.querySelectorAll('tr[data-id]').forEach(tr => {
    tr.onclick = () => selectPlan(tr.dataset.id);
  });

  const first = state.plans.find(p => (p.outputs || []).length);
  if (first) selectPlan(state.selected && state.plans.some(p => p.plan_id === state.selected)
    ? state.selected : first.plan_id);
}

function selectPlan(planId) {
  state.selected = planId;
  document.querySelectorAll('#rows tr').forEach(x => x.removeAttribute('aria-selected'));
  const tr = document.querySelector(`#rows tr[data-id="${CSS.escape(planId)}"]`);
  if (tr) tr.setAttribute('aria-selected', 'true');

  const rec = state.plans.find(p => p.plan_id === planId);
  const outputs = (rec && rec.outputs) || [];
  const pv = $('preview');
  const files = $('pvfiles');

  if (!outputs.length) {
    $('pvid').textContent = planId;
    const why = rec && rec.status === 'failed'
      ? `${planId} failed: ${escapeHtml(rec.error || 'unknown error')}`
      : 'No annotated output for this plan.';
    pv.innerHTML = `<div class="empty">${why}</div>`;
    files.innerHTML = '';
    return;
  }

  showPng(planId, outputs[0].output_png);
  files.innerHTML = outputs.map((o, i) =>
    `<button class="btn ghost" style="padding:5px 10px;font-size:9px" data-f="${escapeHtml(o.output_png)}">${escapeHtml(o.source_png)}</button>`
  ).join('');
  files.querySelectorAll('button').forEach(b => {
    b.onclick = () => showPng(planId, b.dataset.f);
  });
}

function showPng(planId, file) {
  $('pvid').textContent = file;
  $('preview').innerHTML =
    `<img alt="Annotated floor plan ${escapeHtml(planId)}" src="/api/plans/${encodeURIComponent(planId)}/png?file=${encodeURIComponent(file)}">`;
}

/* ---------------- exports ---------------- */
function download(url, btn, busyLabel) {
  const label = btn.textContent;
  btn.disabled = true;
  btn.textContent = busyLabel;
  const f = document.createElement('iframe');
  f.style.display = 'none';
  f.src = url;
  document.body.appendChild(f);
  setTimeout(() => { btn.disabled = false; btn.textContent = label; }, 3000);
}

const exportXlsx = (btn) => download('/api/export/xlsx', btn, 'Building…');
$('expXlsx').onclick = () => exportXlsx($('expXlsx'));
$('expXlsx2').onclick = () => exportXlsx($('expXlsx2'));
$('expCsv').onclick = () => { window.location = '/api/export/csv'; };
$('expZip').onclick = () => download('/api/export/zip', $('expZip'), 'Zipping…');

/* ---------------- Tab 2 — plan picker ---------------- */
function refreshPicker() {
  const box = $('picker');
  const usable = state.plans.filter(p => p.status !== 'failed');
  if (!usable.length) {
    box.innerHTML = `<div style="padding:16px" class="note">No plans yet — run Tab 1.</div>`;
    return;
  }
  const VCHIP = {
    accessible:     ['ok', 'pass'],
    not_accessible: ['no', 'fail'],
    undetermined:   ['wr', '?'],
    excluded:       ['wr', 'excl'],
  };
  box.innerHTML = usable.map(p => {
    const d = p.verdict && p.verdict.determination;
    const [vc, vl] = VCHIP[d] || [];
    const flag = d
      ? `<span class="chip ${vc}" style="font-size:8px">${vl}</span>`
      : (p.status === 'estimated' ? `<span class="chip wr" style="font-size:8px">est</span>` : '');
    return `<button class="planitem" data-id="${escapeHtml(p.plan_id)}">
      <span>${escapeHtml(p.plan_id)}</span>
      <span style="display:flex;gap:6px;align-items:center">${flag}<span class="measure-sm">${fmtNum(p.internal_area_m2, 1, ' m²')}</span></span>
    </button>`;
  }).join('');
  box.querySelectorAll('.planitem').forEach(b => {
    b.onclick = () => selectReviewPlan(b.dataset.id);
    if (b.dataset.id === state.reviewPlan) b.setAttribute('aria-pressed', 'true');
  });
  if (!state.reviewPlan) selectReviewPlan(usable[0].plan_id);
}

async function selectReviewPlan(planId) {
  state.reviewPlan = planId;
  state.history = [];
  state.checks = null;
  document.querySelectorAll('.planitem').forEach(x =>
    x.setAttribute('aria-pressed', x.dataset.id === planId));
  $('who').textContent = planId;
  $('thread').innerHTML = '';
  resetVerdict();
  $('geomWrap').hidden = true;
  banner('err2', null);

  const rec = state.plans.find(p => p.plan_id === planId);
  if (rec && rec.status === 'estimated') {
    banner('err2',
      `${planId} fell through to the scale-estimation fallback (no room-label cross-check). ` +
      `It is excluded from Part 2 determinations — the measurements cannot be trusted to the millimetre.`,
      'warn');
  }

  addMsg('ai',
    `<p>Loaded <b>${escapeHtml(planId)}</b> — overall <span class="measure">${fmtNum(rec?.overall_width_m, 2)} × ${fmtNum(rec?.overall_depth_m, 2)} m</span>, ` +
    `${(rec?.rooms || []).length} rooms, scale resolved at <span class="measure-sm">${fmtNum(rec?.px_per_m, 1)}</span> px/m.</p>` +
    `<p>Python measures the geometry; I judge it against Technical Guidance Document M and cite the clause. Ask a question, or use a prompt below.</p>`);

  loadChecks(planId).catch(() => {});

  // Replay a stored determination rather than re-billing the API on every click.
  api(`/api/plans/${encodeURIComponent(planId)}/verdict`)
    .then(v => { if (state.reviewPlan === planId) paintVerdict(v); })
    .catch(() => {});
}

async function loadChecks(planId) {
  try {
    const r = await api(`/api/plans/${encodeURIComponent(planId)}/checks`);
    state.checks = r;
    paintGeom(r);
  } catch (e) {
    state.checks = null;
  }
}

/* ---------------- Tab 2 — chat ---------------- */
function addMsg(role, html) {
  const d = document.createElement('div');
  d.className = 'msg ' + (role === 'me' ? 'me' : '');
  d.innerHTML = `<div class="who eyebrow">${role === 'me' ? 'You' : 'Datum'}</div><div class="bub">${html}</div>`;
  $('thread').appendChild(d);
  $('thread').scrollTop = $('thread').scrollHeight;
  return d;
}

async function send(text) {
  text = (text || '').trim();
  if (!text) return;
  if (!state.reviewPlan) { banner('err2', 'Pick a plan first.'); return; }

  addMsg('me', escapeHtml(text));
  $('ask').value = '';
  const bubble = addMsg('ai', '<div class="typing"><i></i><i></i><i></i></div>');
  $('send').disabled = true;

  try {
    const r = await api('/api/review', {
      method: 'POST',
      body: JSON.stringify({
        plan_id: state.reviewPlan,
        question: text,
        history: state.history.slice(-6),
      }),
    });
    bubble.querySelector('.bub').innerHTML = r.html || escapeHtml(r.answer || '');
    state.history.push({ role: 'user', content: text });
    state.history.push({ role: 'assistant', content: r.answer || '' });
    if (r.clauses_used && r.clauses_used.length) {
      const refs = r.clauses_used.map(c => `<span class="ref">TGD M ${escapeHtml(c)}</span>`).join(' ');
      bubble.querySelector('.bub').insertAdjacentHTML('beforeend',
        `<p class="note" style="margin-top:10px">Clauses supplied to the model: ${refs}</p>`);
    }
  } catch (e) {
    bubble.querySelector('.bub').innerHTML =
      `<p>I could not complete that: ${escapeHtml(e.message)}</p>`;
  } finally {
    $('send').disabled = false;
    $('thread').scrollTop = $('thread').scrollHeight;
  }
}

$('send').onclick = () => send($('ask').value);
$('ask').addEventListener('keydown', e => { if (e.key === 'Enter') $('send').click(); });
$('suggest').addEventListener('click', e => {
  const b = e.target.closest('button'); if (b) send(b.textContent);
});

/* ---------------- Tab 2 — verdict card ---------------- */
function resetVerdict() {
  $('verdictHead').className = 'verdict-h';
  $('verdictCall').textContent = 'Not run';
  $('verdictNote').textContent = 'Run the determination to check this plan against TGD M.';
  $('checks').innerHTML = '';
}

const DOT = { pass: 'ok', fail: 'no', undetermined: 'wr' };

$('runVerdict').onclick = async () => {
  if (!state.reviewPlan) { banner('err2', 'Pick a plan first.'); return; }
  $('runVerdict').disabled = true;
  $('verdictCall').textContent = 'Working…';
  $('verdictNote').textContent = 'Python is measuring, then Claude judges against retrieved clause text.';
  $('checks').innerHTML = '';
  try {
    const v = await api('/api/verdict', {
      method: 'POST',
      body: JSON.stringify({ plan_id: state.reviewPlan }),
    });
    paintVerdict(v);
  } catch (e) {
    $('verdictHead').className = 'verdict-h';
    $('verdictCall').textContent = 'Not run';
    $('verdictNote').textContent = '';
    banner('err2', `Determination failed: ${e.message}`);
  } finally {
    $('runVerdict').disabled = false;
  }
};

function paintVerdict(v) {
  const checks = v.checks || [];
  const fails = checks.filter(c => c.result === 'fail').length;
  const undet = checks.filter(c => c.result === 'undetermined').length;

  const map = {
    accessible:      ['pass', 'Accessible<br>as drawn'],
    not_accessible:  ['fail', 'Not accessible<br>as drawn'],
    undetermined:    ['wr',   'Cannot be<br>determined'],
    excluded:        ['wr',   'Excluded from<br>determination'],
  };
  const [cls, call] = map[v.determination] || ['wr', escapeHtml(v.determination || '—')];
  $('verdictHead').className = 'verdict-h ' + cls;
  $('verdictCall').innerHTML = call;
  const tally = `${fails} of ${checks.length} checks fail${undet ? `, ${undet} undetermined` : ''}.`;
  $('verdictNote').textContent = `${tally} ${v.summary || 'Each is traced to a clause in TGD M.'}`;

  $('checks').innerHTML = checks.map(c => {
    const dot = DOT[c.result] || 'wr';
    const measured = c.measured_display
      ? `<span class="measure-sm">${escapeHtml(c.measured_display)}</span> measured · `
      : (c.result === 'undetermined' ? 'Not determinable from plan geometry · ' : '');
    const clause = c.clause
      ? `<span class="ref">TGD M ${escapeHtml(c.clause)}</span>` : '';
    const note = c.note ? `<small style="margin-top:4px">${escapeHtml(c.note)}</small>` : '';
    return `<div class="check"><span class="dot ${dot}"></span><div class="k">
      <b>${escapeHtml(c.item || '')}</b>
      <small>${measured}${clause}</small>${note}</div></div>`;
  }).join('') || `<div class="check"><div class="k"><small>No checks returned.</small></div></div>`;
}

/* ---------------- Tab 2 — run every determination ---------------- */
$('runAll').onclick = async () => {
  const pending = state.plans.filter(p => p.status !== 'failed' && !p.verdict).length;
  if (!state.plans.length) { banner('err2', 'No plans yet — run Tab 1 first.'); return; }
  if (pending === 0 &&
      !confirm('Every plan already has a determination. Run them all again?')) return;

  banner('err2', null);
  $('runAll').disabled = true;
  $('allWrap').hidden = false;
  $('allBar').style.width = '0%';
  $('allLab').textContent = 'Starting…';
  $('footState').textContent = 'reviewing';

  try {
    const job = await api('/api/verdict/all', {
      method: 'POST',
      body: JSON.stringify({ refresh: pending === 0 }),
    });

    await new Promise(resolve => {
      const es = new EventSource(`/api/jobs/${job.job_id}/events`);
      es.onmessage = ev => {
        const m = JSON.parse(ev.data);
        if (m.type === 'progress') {
          $('allBar').style.width = `${m.total ? (m.done / m.total * 100) : 0}%`;
          $('allLab').textContent = `${m.done} / ${m.total} — ${m.plan_id}: ${m.status}`;
          if (m.done % 5 === 0) loadManifest();
        } else if (m.type === 'done') {
          $('allBar').style.width = '100%';
          const c = m.counts || {};
          $('allLab').textContent = m.message ||
            `Done — ${Object.entries(c).map(([k, v]) => `${v} ${k}`).join(', ')}`;
          es.close(); resolve();
        } else if (m.type === 'error') {
          banner('err2', `Batch determination failed: ${m.error}`);
          $('allLab').textContent = 'Failed';
          es.close(); resolve();
        }
      };
      es.onerror = () => { es.close(); resolve(); };
    });

    await loadManifest();
    if (state.reviewPlan) {
      api(`/api/plans/${encodeURIComponent(state.reviewPlan)}/verdict`)
        .then(paintVerdict).catch(() => {});
    }
  } catch (e) {
    banner('err2', `Could not start: ${e.message}`);
    $('allLab').textContent = 'Idle';
  } finally {
    $('runAll').disabled = false;
    $('footState').textContent = 'idle';
  }
};

/* ---------------- Tab 2 — measured geometry panel ---------------- */
$('showGeom').onclick = async () => {
  if (!state.checks && state.reviewPlan) await loadChecks(state.reviewPlan);
  if (!state.checks) { banner('err2', 'No geometry available for this plan.'); return; }
  $('geomWrap').hidden = !$('geomWrap').hidden;
  paintGeom(state.checks);
};

function paintGeom(r) {
  $('geomDoors').innerHTML = (r.doors || []).map(d => `<tr>
    <td>${escapeHtml(d.id)}</td>
    <td>${escapeHtml((d.between || []).join(' → ') || '—')}</td>
    <td class="measure">${d.clear_width_mm ? d.clear_width_mm + ' mm' : '—'}</td>
    <td style="color:var(--ink-2)">${escapeHtml(d.method || '')}</td>
  </tr>`).join('') || `<tr><td colspan="4" class="note" style="padding:16px">No door openings resolved.</td></tr>`;

  $('geomRooms').innerHTML = (r.rooms || []).map(m => `<tr>
    <td>${escapeHtml(m.name || m.code || '')}</td>
    <td class="measure">${m.free_circle_mm ? m.free_circle_mm + ' mm' : '—'}</td>
    <td class="measure">${m.min_width_mm ? m.min_width_mm + ' mm' : '—'}</td>
  </tr>`).join('') || `<tr><td colspan="3" class="note" style="padding:16px">No room geometry.</td></tr>`;
}

/* ---------------- boot ---------------- */
(async () => {
  try {
    const h = await api('/api/health');
    $('root').value = h.dataset_default;
    if (h.annotated_plans) await loadManifest();
  } catch (_) {}
  try {
    const t = await api('/api/tgdm/status');
    $('docStat').textContent = t.indexed ? `${t.clauses} clauses indexed` : 'not indexed';
    $('docPulse').className = 'pulse' + (t.indexed ? '' : ' off');
    if (t.model) $('metaModel').textContent = t.model;
  } catch (_) {
    $('docStat').textContent = 'index unavailable';
    $('docPulse').className = 'pulse off';
  }
})();
