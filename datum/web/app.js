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

/* ---------------- folder upload ----------------
   The browser can't hand the server a real directory path for an arbitrary local
   folder, so instead of browsing the server's filesystem, the user's folder is
   uploaded here (webkitdirectory keeps each file's relative path) and staged
   under data/uploads/ as the scan root. */
$('browse').onclick = () => $('folderInput').click();
$('root').onclick = () => $('folderInput').click();

$('folderInput').addEventListener('change', async (e) => {
  const files = [...e.target.files];
  e.target.value = '';
  if (files.length) await uploadFolder(files);
});

async function uploadFolder(files) {
  banner('err1', null);
  $('browse').disabled = true;
  $('barlab').textContent = `Uploading ${files.length} file${files.length === 1 ? '' : 's'}…`;
  try {
    const fd = new FormData();
    files.forEach(f => fd.append('files', f, f.webkitRelativePath || f.name));
    const res = await fetch('/api/upload', { method: 'POST', body: fd });
    if (!res.ok) {
      let detail = res.statusText;
      try { detail = (await res.json()).detail || detail; } catch (_) {}
      throw new Error(detail);
    }
    const r = await res.json();
    $('root').value = r.root;
    $('barlab').textContent = `Uploaded ${r.files} files`;
    $('scan').click();
  } catch (e) {
    banner('err1', `Upload failed: ${e.message}`);
    $('barlab').textContent = 'Idle';
  } finally {
    $('browse').disabled = false;
  }
}

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
    compliant:             ['ok', 'pass'],
    compliant_with_flags:  ['wr', 'flag'],
    non_compliant:         ['no', 'fail'],
    undetermined:          ['wr', '?'],
    excluded:              ['wr', 'excl'],
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

  showReviewPng(planId, rec);
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

function showReviewPng(planId, rec) {
  const box = $('reviewPreview');
  const outputs = (rec && rec.outputs) || [];
  if (!outputs.length) {
    box.innerHTML = `<div class="empty" style="min-height:120px">No annotated output for this plan.</div>`;
    return;
  }
  box.innerHTML = `<img alt="Annotated floor plan ${escapeHtml(planId)}" ` +
    `src="/api/plans/${encodeURIComponent(planId)}/png?file=${encodeURIComponent(outputs[0].output_png)}">`;
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
  paintCost(null);
}

const DOT = { pass: 'ok', fail: 'no', flag: 'wr', undetermined: 'wr', informational: 'nu' };
const TIER_CHIP = { critical: 'no', high: 'wr', medium: 'nu', lower: 'nu' };

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
  const hardFails = checks.filter(c => c.result === 'fail');
  const flagged = checks.filter(c => c.result === 'flag' || c.result === 'undetermined');
  const passed = checks.filter(c => c.result === 'pass');
  const info = checks.filter(c => c.result === 'informational');

  const map = {
    compliant:             ['pass', 'Compliant'],
    compliant_with_flags:  ['wr',   'Compliant with<br>flagged items'],
    non_compliant:         ['fail', 'Non-compliant'],
    undetermined:          ['wr',   'Cannot be<br>determined'],
    excluded:              ['wr',   'Excluded from<br>determination'],
  };
  const [cls, call] = map[v.determination] || ['wr', escapeHtml(v.determination || '—')];
  $('verdictHead').className = 'verdict-h ' + cls;
  $('verdictCall').innerHTML = call;

  const tally = `${hardFails.length} hard fail${hardFails.length === 1 ? '' : 's'}, ` +
    `${flagged.length} flagged.`;
  const section = v.applicable_section
    ? `<br><small style="color:var(--ink-3)">Section ${escapeHtml(v.applicable_section)}` +
      `${v.section_reason ? ' — ' + escapeHtml(v.section_reason) : ''}</small>`
    : '';
  $('verdictNote').innerHTML = `${tally} ${escapeHtml(v.summary || 'Each is traced to a clause in TGD M.')}${section}`;

  const row = (c) => {
    const dot = DOT[c.result] || 'nu';
    const tier = c.tier ? `<span class="chip ${TIER_CHIP[c.tier] || 'nu'}" style="font-size:8px;margin-left:6px">${escapeHtml(c.tier)}</span>` : '';
    const measured = c.measured_display ? `<span class="measure-sm">${escapeHtml(c.measured_display)}</span>` : '';
    const required = c.required_display ? ` vs <span class="measure-sm">${escapeHtml(c.required_display)}</span> required` : '';
    const clause = c.clause ? `<span class="ref">TGD M ${escapeHtml(c.clause)}</span>` : '';
    const sep = (measured || required) && clause ? ' · ' : '';
    const note = c.note ? `<small style="margin-top:4px">${escapeHtml(c.note)}</small>` : '';
    return `<div class="check"><span class="dot ${dot}"></span><div class="k">
      <b>${escapeHtml(c.item || '')}</b>${tier}
      <small>${measured}${required}${sep}${clause}</small>${note}</div></div>`;
  };
  const group = (title, list) => list.length
    ? `<div class="sec" style="margin:14px 16px 6px"><span class="eyebrow">${title}</span><span class="dimrule"></span></div>${list.map(row).join('')}`
    : '';

  $('checks').innerHTML =
    group('Hard fails', hardFails) +
    group('Flagged items', flagged) +
    group('Passed', passed) +
    group('Informational notes', info) ||
    `<div class="check"><div class="k"><small>No checks returned.</small></div></div>`;

  paintCost(v.usage, v.cached);
}

function paintCost(usage, cached) {
  const el = $('costLine');
  if (!usage) { el.textContent = 'No analysis run yet.'; return; }
  const parts = [`${usage.input_tokens.toLocaleString()} in`, `${usage.output_tokens.toLocaleString()} out`];
  if (usage.cache_read_input_tokens) parts.push(`${usage.cache_read_input_tokens.toLocaleString()} cached`);
  const prefix = cached ? '(replayed from cache, no new spend) ' : '';
  el.textContent = `${prefix}${parts.join(' + ')} = ${usage.total_tokens.toLocaleString()} tokens · $${usage.cost_usd.toFixed(4)} (${usage.model})`;
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
          const skipped = c.skipped_budget || 0;
          const spend = (m.spent_usd != null)
            ? ` — $${m.spent_usd.toFixed(2)} spent of the $${(m.budget_cap_usd || 0).toFixed(2)} cap` +
              (skipped ? `, ${skipped} skipped once the cap was reached` : '')
            : '';
          $('allLab').textContent = (m.message ||
            `Done — ${Object.entries(c).map(([k, v]) => `${v} ${k}`).join(', ')}`) + spend;
          if (skipped) banner('err2', `Reached the $${(m.budget_cap_usd || 0).toFixed(2)} spend cap for this run — ${skipped} plan${skipped === 1 ? '' : 's'} skipped. Click "Run all determinations" again to continue where it left off.`, 'warn');
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
