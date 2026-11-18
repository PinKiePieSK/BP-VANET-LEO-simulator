// Ovládanie grafického pohľadu na časovú fyzikálnu dostupnosť a výsledky paketového behu. Odlišuje
// geometrického kandidáta od skutočne prijatého paketu.
'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const ns = 'http://www.w3.org/2000/svg';
  const model = () => window.simulatorEditor;
  const state = () => model()?.state;
  const palette = {
    disabled: '#718489', blocked: '#be5966', envelope: '#dc9a60',
    antenna: '#8e79bd', possible: '#64bbb0', interval: '#dfc26a',
    positive: '#98cf80'
  };
  let request = 0;

  function rowFor(node) {
    const s = state(), rows = s?.audit?.nodes?.[node];
    if (!rows?.length) return null;
    return rows[Math.max(0, Math.min(rows.length - 1,
      Math.round(s.time / s.audit.step_us)))];
  }
  function color(row) {
    if (row.antenna_status === 'terminal_disabled') return palette.disabled;
    if (!row.horizon_count || ['blocked_all_candidates','native_building_blocked'].includes(row.sight_status) ||
        (row.native_rf_signals && !row.native_rf_reasons?.accepted))
      return palette.blocked;
    if (!row.public_envelope_count) return palette.envelope;
    if (row.antenna_status === 'outside_declared_fov' ||
        row.antenna_status === 'possible_pattern_unquantified') return palette.antenna;
    if (row.sight_status === 'uncertain') return palette.interval;
    if (row.margin_status === 'assumed_positive') return palette.positive;
    if (row.margin_status === 'assumed_negative') return palette.blocked;
    if (row.margin_status === 'assumed_interval_crosses_zero') return palette.interval;
    return palette.possible;
  }
  function selected() {
    const s = state();
    if (!s?.audit) return null;
    const id = ['car', 'rsu'].includes(s.selected?.type) ? s.selected.id :
      (s.audit.nodes[s.scenario?.rsu_id] ? s.scenario.rsu_id : Object.keys(s.audit.nodes)[0]);
    return [id, rowFor(id)];
  }
  function stage(title, value, tint) {
    const card = document.createElement('div');
    card.style.setProperty('--stage', tint);
    const heading = document.createElement('strong');
    heading.textContent = title;
    const body = document.createElement('span');
    body.textContent = value;
    card.append(heading, body);
    return card;
  }
  function interval(row, leg) {
    const lo = row[leg + '_margin_low_db'], hi = row[leg + '_margin_high_db'];
    return lo == null || hi == null ? 'neznáma' : `${lo.toFixed(1)} až ${hi.toFixed(1)} dB`;
  }
  const countWord=(n,one,few,many)=>n===1?one:n>=2&&n<=4?few:many;
  // Zobrazuje audit fyzikálnych kandidátov a dôvodov odmietnutia. Farba a legenda vysvetľujú stav;
  // skutočné doručenie paketu sa posudzuje podľa paketového verifiera.
  function render() {
    const s = state(), panel = $('physicalAudit');
    if (!s?.audit || !s.replay) return;
    const choice = selected();
    if (!choice || !choice[1]) return;
    const [node, row] = choice;
    panel.hidden = false;
    $('physicalAuditAt').textContent = `${node} · ${(row.time_us / 1e6).toFixed(1)} s · ${s.audit.service}`;
    const antenna = {
      terminal_disabled: 'terminál vypnutý', outside_public_envelope: 'mimo verejnej obálky',
      within_declared_fov: 'v deklarovanom zornom poli', outside_declared_fov: 'mimo zorného poľa',
      possible_pattern_unquantified: 'možná, ziskový vzor neznámy',
      native_mask_candidate: 'vybraný natívny SNS-3 podgraf nad výškovou maskou',
      native_mount_pointing_gate: 'montáž a smerovanie sa vyhodnocujú v SNS-3 kanáli',
      native_directional_pattern_unquantified: 'smerový zisk terminálu nie je verejne doložený'
    }[row.antenna_status] || row.antenna_status;
    const sight = {
      clear: 'voľný geometrický výhľad', uncertain: 'výška prekážky neistá',
      blocked_all_candidates: 'všetci kandidáti tienení', not_modelled: s.audit.schema_version===2?'satelitné tienenie lokálnymi budovami sa tu nevyhodnocuje':'bez lokálnej vrstvy',
      terminal_disabled: 'terminál vypnutý', no_antenna_candidate: 'bez anténneho kandidáta',
      no_proxy_route_or_eligible_serving: 'bez vybranej proxy cesty',
      native_building_mixed: 'časť signálov blokovali miestne budovy',
      native_building_blocked: 'miestne budovy blokovali signály',
      native_building_clear: 'v tejto vzorke bez bloku miestnou budovou',
      no_local_building_input: 'bez vstupu miestnych budov',
      native_no_signal_sample: 'v tomto intervale bez RF signálu'
    }[row.sight_status] || row.sight_status;
    const margin = {
      assumed_positive: 'kladná iba pri zadaných predpokladoch',
      assumed_negative: 'záporná iba pri zadaných predpokladoch',
      assumed_interval_crosses_zero: 'predpokladaný interval zahŕňa nulu',
      unknown_isl_budget: 'neznámy ISL rozpočet', unknown_rf_inputs: 'chýbajú RF parametre',
      unknown_no_link_budget: 'link budget nie je v tomto behu',
      no_route: 'bez cesty', terminal_disabled: 'terminál vypnutý'
    }[row.margin_status] || row.margin_status;
    const camDenm = s.replay.trace_kind?.startsWith('native/') &&
      s.replay.events.some(event => event.stage === 'DENM_UPER_TX');
    const packetWindow = camDenm ? s.replay.events.filter(event =>
      event.time_us >= row.time_us && event.time_us < row.time_us + 500000) : [];
    const countStage = name => packetWindow.filter(event => event.stage === name).length;
    const cards = [
      stage('1 · Čistý horizont', `${row.horizon_count} ${countWord(row.horizon_count,'satelit','satelity','satelitov')} nad 0°`, row.horizon_count ? palette.possible : palette.blocked),
      stage('2 · Verejná obálka', `${row.public_envelope_count} po elevácii a limite služby`, row.public_envelope_count ? palette.possible : palette.envelope),
      stage('3 · Anténa', `${row.antenna_possible_count} ${countWord(row.antenna_possible_count,'kandidát','kandidáti','kandidátov')} · ${antenna}`, color(row)),
      stage('4 · Budovy a terén', `${sight}${row.clear_sight_count+row.uncertain_sight_count+row.blocked_count?` · ${row.clear_sight_count} voľných, ${row.uncertain_sight_count} neistých, ${row.blocked_count} tienených`:''}`, row.sight_status === 'clear' ? palette.possible : palette.blocked),
      stage('5 · RF rezerva', row.margin_status === 'unknown_no_link_budget'?margin:
        `${margin}; auto/RSU ↑ ${interval(row, 'user_uplink')}, ↓ ${interval(row, 'user_downlink')}; brána ↑ ${interval(row, 'feeder_uplink')}, ↓ ${interval(row, 'feeder_downlink')}`,
        row.margin_status === 'assumed_positive' ? palette.positive : palette.interval),
      camDenm ? stage('6 · CAM a DENM', `0,5 s: CAM TX ${countStage('CAM_UPER_TX')} · DENM TX ${countStage('DENM_UPER_TX')} · brána RX ${countStage('GATEWAY_DENM_RX')} · uzly RX ${countStage('DENM_UPER_RX')}`, countStage('GATEWAY_DENM_RX') ? palette.positive : palette.disabled) :
      stage('6 · Pakety modelu', `0,5 s: ponuky ${row.packet_offers} · brána RX ${row.packet_gateway_rx} · straty ${row.packet_drops} · ACK ${row.packet_acks}`, row.packet_gateway_rx ? palette.positive : palette.disabled)
    ];
    $('physicalAuditStages').replaceChildren(...cards);
    const route=row.route_catalog_ids.length?row.route_catalog_ids.join(' → '):'žiadna';
    const reasons=Object.entries(row.native_rf_reasons||{}).map(([key,count])=>`${key}: ${count}`).join(', ');
    // Keep the measured trace counts visible; model limitations are documented
    // once in the technical report instead of repeated beside every time step.
    // Krátka poznámka oddelí geometrický a RF výpočet od skutočného príjmu paketu. Podrobný dôvod
    // zostáva v etapách a exporte, aby sa v prehrávači neopakoval dlhý opis modelu.
    $('physicalAuditNote').textContent=s.audit.schema_version===2?
      `Paketová trasa: ${route} · RF signály: ${row.native_rf_signals||0}${reasons?` · ${reasons}`:''} · RF zamietnutie ≠ strata paketu.`:
      `Geometrická trasa: ${route} · bez potvrdenia služby.`;
  }
  // Kreslí stav iba pre uzly s auditom a používa aktuálny stav editora na prepočet lokálnej
  // súradnice Y. Nezávisí od inej globálnej premennej; pri satelitnom replay sa mapa nesmie
  // prerušiť chybou kreslenia.
  function draw(layer) {
    const s = state();
    if (!s?.audit || !s.replay || !$('layerPhysicalState').checked) return;
    const ctm = $('groundMap').getScreenCTM();
    const scale = ctm ? 1 / Math.hypot(ctm.a, ctm.b) : s.view.w / Math.max(1, $('groundMap').clientWidth);
    for (const node of Object.keys(s.audit.nodes)) {
      const row = rowFor(node), p = model().groundPosition(node);
      if (!row || !p) continue;
      const circle = document.createElementNS(ns, 'circle');
      for (const [key, value] of Object.entries({cx: p.x, cy: (s.world?.height_m||s.world?.extent_m||2000) - p.y,
        r: 14 * scale, fill: 'none', stroke: color(row), 'stroke-width': 3,
        'vector-effect': 'non-scaling-stroke', 'pointer-events': 'none'})) {
        circle.setAttribute(key, String(value));
      }
      layer.append(circle);
    }
  }
  function clear() {
    request++;
    const s = state();
    if (s) s.audit = null;
    $('physicalAudit').hidden = true;
    $('physicalAuditStages').replaceChildren();
  }
  // Pozemný beh nemá satelitnú fyzikálnu časovú os. Panel sa vtedy skryje bez API požiadavky; pri
  // satelitnom behu sa načíta audit overeného výsledku.
  async function load(id) {
    const serial = ++request, s = state();
    if (!s?.scenario?.satellite_enabled) {
      clear();
      return;
    }
    s.audit = null;
    $('physicalAudit').hidden = false;
    $('physicalAuditAt').textContent = 'Počítam oddelené vrstvy z overeného behu…';
    $('physicalAuditStages').replaceChildren();
    $('physicalAuditNote').textContent = '';
    try {
      const response = await fetch(`/api/simulator/runs/${encodeURIComponent(id)}/physical-audit`);
      const report = await response.json();
      if (!response.ok) throw Error(report.reason || report.error || `HTTP ${response.status}`);
      if (serial !== request || s.runId !== id || !s.replay) return;
      s.audit = report;
      model().render();
    } catch (error) {
      if (serial !== request) return;
      $('physicalAuditAt').textContent = 'Fyzikálny audit nie je dostupný';
      $('physicalAuditNote').textContent = error.message;
    }
  }
  function download(kind) {
    const report = state()?.audit;
    if (!report) return;
    let content, mime;
    if (kind === 'json') {
      content = JSON.stringify(report, null, 2) + '\n'; mime = 'application/json';
    } else {
      const quote = value => `"${String(value ?? '').replaceAll('"', '""')}"`;
      content = report.csv_fields.join(',') + '\n';
      for (const node of Object.keys(report.nodes).sort()) {
        for (const row of report.nodes[node]) {
          content += report.csv_fields.map(key => quote(row[key])).join(',') + '\n';
        }
      }
      mime = 'text/csv';
    }
    const url = URL.createObjectURL(new Blob([content], {type: mime + ';charset=utf-8'}));
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `physical-audit-${report.run_id}.${kind}`;
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  }
  $('physicalAuditJson').onclick = () => download('json');
  $('physicalAuditCsv').onclick = () => download('csv');
  window.simulatorPhysicalAudit = {load, clear, render, draw};
})();
