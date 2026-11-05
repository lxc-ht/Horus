const icons = [
  ['analyze', 'Analysieren', 'Sensible Angaben im Text erkennen.'],
  ['preview', 'Vorschau', 'Prüfen, welche Fassung die KI erhält.'],
  ['output', 'Ausgabe', 'Die fertige Antwort anzeigen.'],
  ['original', 'Original', 'Den ursprünglichen Text öffnen.'],
  ['mask', 'Maskieren', 'Angaben durch Platzhalter ersetzen.'],
  ['release', 'Freigeben', 'Die geprüfte Fassung ausdrücklich bestätigen.'],
  ['lock', 'Gesperrt', 'Eine Aktion wartet auf die Freigabe.'],
  ['send', 'Senden', 'Nur die freigegebene Fassung übertragen.'],
  ['restore', 'Zurückübersetzen', 'Originale lokal wieder einsetzen.'],
  ['copy', 'Kopieren', 'Die freigegebene Fassung übernehmen.'],
  ['upload', 'Importieren', 'Ein Dokument in den Arbeitsbereich holen.'],
  ['download', 'Exportieren', 'Ein Ergebnis als Datei speichern.'],
  ['check', 'Erledigt', 'Einen abgeschlossenen Schritt bestätigen.'],
  ['warning', 'Hinweis', 'Auf eine nötige Prüfung aufmerksam machen.'],
  ['reset', 'Zurücksetzen', 'Wieder mit einem leeren Stand beginnen.'],
  ['settings', 'Einstellungen', 'Die Darstellung oder Optionen anpassen.'],
  ['close', 'Entfernen', 'Ein Element oder einen Platzhalter entfernen.'],
  ['local', 'Lokal', 'Verarbeitung auf diesem Rechner anzeigen.'],
];
const $ = (id) => document.getElementById(id);
const icon = (name) => `<svg class="icon" aria-hidden="true"><use href="#i-${name}"/></svg>`;
let selected = 'analyze';

function selectIcon(name) {
  selected = name;
  const [, label, help] = icons.find(([id]) => id === name);
  $('selectedSymbol').innerHTML = icon(name);
  $('selectedName').textContent = label;
  $('selectedHelp').textContent = help;
  for (const size of [16, 20, 24]) $('size' + size).innerHTML = icon(name);
  document.querySelectorAll('[data-icon]').forEach((button) => {
    button.setAttribute('aria-pressed', String(button.dataset.icon === name));
  });
  $('iconFeedback').textContent = '';
}

$('iconGrid').innerHTML = icons.map(([id, label]) => `<button type="button" class="icon-tile" data-icon="${id}" aria-pressed="false">${icon(id)}<span>${label}</span></button>`).join('');
$('iconGrid').addEventListener('click', (event) => {
  const button = event.target.closest('[data-icon]');
  if (button) selectIcon(button.dataset.icon);
});
selectIcon(selected);

function selectedSvg() {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">${$('i-' + selected).innerHTML}</svg>`;
}

$('copySvg').addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(selectedSvg());
    $('iconFeedback').textContent = $('selectedName').textContent + ' als SVG kopiert.';
  } catch {
    $('iconFeedback').textContent = 'Die Zwischenablage ist gesperrt. Nutze stattdessen „SVG laden“.';
  }
});
$('downloadSvg').addEventListener('click', () => {
  const url = URL.createObjectURL(new Blob([selectedSvg()], { type: 'image/svg+xml' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = `lp7-${selected}.svg`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  $('iconFeedback').textContent = $('selectedName').textContent + ' als SVG heruntergeladen.';
});

document.querySelectorAll('.segmented [data-look]').forEach((button) => {
  button.addEventListener('click', () => {
    document.body.dataset.look = button.dataset.look;
    document.querySelectorAll('.segmented [data-look]').forEach((peer) => peer.setAttribute('aria-pressed', String(peer === button)));
  });
});
document.querySelectorAll('.sample-action').forEach((button) => {
  button.addEventListener('click', () => { $('componentFeedback').textContent = button.dataset.message; });
});

const example = {
  original: 'Erika Musterfrau schreibt an Max Mustermann. Bitte formuliere eine kurze Rückfrage.',
  masked: '<span class="data-chip person">[PERSON_1]</span> schreibt an <span class="data-chip person">[PERSON_2]</span>. Bitte formuliere eine kurze Rückfrage.',
  answer: 'Erika Musterfrau hat eine Rückfrage an Max Mustermann.',
};
const designs = [ ['glass', 'Liquid Glass', 'Leicht & vertraut'], ['lime', 'Lime Soda', 'Frisch & ausdrucksstark'], ['pure', 'Pure White', 'Ruhig & reduziert'] ];
$('demoGrid').innerHTML = designs.map(([id, label, detail]) => `
  <article class="demo" data-design="${id}" data-stage="original" aria-label="${label} Demo">
    <div class="demo-caption"><strong>${label}</strong><span>${detail}</span></div>
    <div class="demo-window">
      <div class="demo-topbar"><span class="demo-mark">${icon('mask')}LP7</span><button type="button" class="icon-button demo-reset" aria-label="${label} Demo zurücksetzen">${icon('reset')}</button></div>
      <div class="demo-steps" aria-label="Arbeitsschritte"><span data-step="original">${icon('original')}Original</span><span data-step="preview">${icon('preview')}Vorschau</span><span data-step="output">${icon('output')}Ausgabe</span></div>
      <div class="demo-editor"><div class="demo-editor-top"><h4 class="demo-heading"></h4><span class="demo-status"></span></div><p class="demo-text"></p><p class="demo-help" role="status"></p></div>
      <div class="demo-actions"><button type="button" class="button primary demo-next"></button><button type="button" class="button secondary demo-output" disabled>${icon('lock')}Ausgabe</button></div>
      <p class="demo-safety">${icon('local')}Lokale Simulation. Keine Daten werden gesendet.</p>
    </div>
  </article>`).join('');

function renderDemo(demo) {
  const stage = demo.dataset.stage;
  const released = stage === 'released';
  const output = stage === 'output';
  const original = stage === 'original';
  const step = output ? 'output' : original ? 'original' : 'preview';
  demo.querySelectorAll('[data-step]').forEach((el) => {
    if (el.dataset.step === step) el.setAttribute('aria-current', 'step');
    else el.removeAttribute('aria-current');
  });
  demo.querySelector('.demo-heading').innerHTML = icon(step) + (output ? 'Deine Ausgabe' : original ? 'Dein Original' : 'Vorschau für Claude');
  demo.querySelector('.demo-status').textContent = output ? 'Fertig' : released ? 'Freigegeben' : original ? 'Lokal' : 'Prüfung nötig';
  demo.querySelector('.demo-text').innerHTML = output
    ? example.answer : original ? example.original : example.masked;
  demo.querySelector('.demo-help').textContent = output ? 'Beispielantwort. Die Originale wurden wieder eingesetzt.' : released ? 'Die geprüfte Fassung ist freigegeben. Ausgabe jetzt ausprobieren.' : original ? 'Starte die Beispielsanalyse. Dein Text bleibt lokal.' : 'Prüfe den gesamten Text. Erst die Freigabe aktiviert die Ausgabe.';
  const next = demo.querySelector('.demo-next');
  next.innerHTML = icon(original ? 'analyze' : output ? 'reset' : 'release') + (original ? 'Analysieren' : output ? 'Neu starten' : released ? 'Freigegeben' : 'Freigeben');
  next.classList.toggle('accent', !original && !output);
  next.classList.toggle('primary', original || output);
  next.disabled = released;
  const send = demo.querySelector('.demo-output');
  send.disabled = !released;
  send.innerHTML = icon(released ? 'output' : 'lock') + 'Ausgabe';
}

document.querySelectorAll('.demo').forEach((demo) => {
  demo.querySelector('.demo-next').addEventListener('click', () => {
    demo.dataset.stage = demo.dataset.stage === 'original' ? 'preview' : demo.dataset.stage === 'preview' ? 'released' : 'original';
    renderDemo(demo);
  });
  demo.querySelector('.demo-output').addEventListener('click', () => {
    if (demo.dataset.stage !== 'released') return;
    demo.dataset.stage = 'output';
    renderDemo(demo);
  });
  demo.querySelector('.demo-reset').addEventListener('click', () => {
    demo.dataset.stage = 'original';
    renderDemo(demo);
  });
  renderDemo(demo);
});

const dashboard = $('dashboardDemo');
const removed = new Set();
let dashboardStage = 'original';
$('dashOriginal').value = example.original;

function renderDashboard(message) {
  const original = dashboardStage === 'original';
  const released = dashboardStage === 'released';
  const output = dashboardStage === 'output';
  dashboard.dataset.stage = dashboardStage;
  const currentStep = original ? 'original' : released || output ? 'output' : 'preview';
  for (const panel of dashboard.querySelectorAll('[data-panel]')) {
    panel.dataset.active = String(panel.dataset.panel === currentStep);
  }
  for (const step of dashboard.querySelectorAll('[data-dash-step]')) {
    step.dataset.complete = String(step.dataset.dashStep === 'original' ? !original : step.dataset.dashStep === 'preview' ? released || output : output);
    if (step.dataset.dashStep === currentStep) step.setAttribute('aria-current', 'step');
    else step.removeAttribute('aria-current');
  }
  const person = (index, name) => removed.has(index) ? name : `<span class="data-chip person">[PERSON_${index}]<button type="button" data-person="${index}" aria-label="PERSON_${index} zurücknehmen">${icon('close')}</button></span>`;
  $('dashPreview').classList.toggle('is-empty', original);
  $('dashPreview').innerHTML = original ? `<div class="dash-placeholder">${icon('preview')}<strong>Hier prüfst du die Fassung</strong><span>Starte die Analyse. Danach siehst du die Platzhalter.</span></div>` : `${person(1, 'Erika Musterfrau')} schreibt an ${person(2, 'Max Mustermann')}. Bitte formuliere eine kurze Rückfrage.`;
  $('dashStatus').textContent = original ? 'Gesperrt' : released || output ? 'Freigegeben' : 'Prüfung nötig';
  $('dashStatus').className = 'badge ' + (original ? 'neutral' : released || output ? 'success' : 'warning');
  $('dashRelease').disabled = original || released || output;
  $('dashOutput').disabled = !released;
  $('dashRelease').innerHTML = icon(released || output ? 'check' : 'release') + (released || output ? 'Vorschau freigegeben' : 'Vorschau freigeben');
  $('dashReviewHelp').textContent = original ? 'Die Vorschau wartet auf deine Analyse.' : `${2 - removed.size} von 2 Namen ersetzt. × setzt den Originalnamen wieder ein.`;
  $('dashAnalyze').classList.toggle('primary', original);
  $('dashAnalyze').classList.toggle('secondary', !original);
  $('dashAnalyze').innerHTML = icon('analyze') + (original ? 'Analysieren' : 'Erneut analysieren');
  $('dashOutput').classList.toggle('primary', released);
  $('dashOutput').classList.toggle('secondary', !released);
  $('dashOutput').innerHTML = icon(output ? 'check' : released ? 'output' : 'lock') + (output ? 'Ausgabe bereit' : 'Ausgabe simulieren');
  $('dashAnswer').classList.toggle('is-empty', !output);
  if (output) $('dashAnswer').textContent = example.answer;
  else $('dashAnswer').innerHTML = `<div class="dash-placeholder">${icon(released ? 'output' : 'lock')}<strong>${released ? 'Bereit für deine Ausgabe' : 'Noch keine Ausgabe'}</strong><span>${released ? 'Die Vorschau ist freigegeben. Du kannst die Beispielantwort jetzt anzeigen.' : 'Prüfe die Vorschau und gib sie frei. Bis dahin bleibt die Ausgabe gesperrt.'}</span></div>`;
  $('dashAnswerStatus').textContent = output ? 'Fertig' : 'Ausstehend';
  $('dashAnswerStatus').className = 'badge ' + (output ? 'success' : 'neutral');
  $('dashNotice').textContent = message;
}

$('dashAnalyze').addEventListener('click', () => {
  removed.clear();
  dashboardStage = 'preview';
  renderDashboard('Zwei Angaben im Beispiel ersetzt. Prüfe die Vorschau und gib sie ausdrücklich frei.');
  $('dashPreviewTitle').focus();
});
$('dashRelease').addEventListener('click', () => {
  if (dashboardStage !== 'preview') return;
  dashboardStage = 'released';
  renderDashboard('Vorschau freigegeben. Die simulierte Ausgabe ist jetzt verfügbar.');
  $('dashOutput').focus();
});
$('dashOutput').addEventListener('click', () => {
  if (dashboardStage !== 'released') return;
  dashboardStage = 'output';
  renderDashboard('Beispielantwort bereit. Keine Anfrage an Claude gesendet.');
  $('dashAnswerTitle').focus();
});
$('dashPreview').addEventListener('click', (event) => {
  const button = event.target.closest('[data-person]');
  if (!button) return;
  removed.add(Number(button.dataset.person));
  dashboardStage = 'preview';
  renderDashboard('Ersetzung zurückgenommen. Freigabe und Ausgabe verworfen. Prüfe den Text erneut.');
  $('dashRelease').focus();
});
$('dashReset').addEventListener('click', () => {
  removed.clear();
  dashboardStage = 'original';
  renderDashboard('Bereit für die Beispielsanalyse. Alle Abläufe werden lokal simuliert.');
  $('dashAnalyze').focus();
});
document.querySelectorAll('.dashboard-controls [data-layout]').forEach((button) => {
  button.addEventListener('click', () => {
    dashboard.dataset.layout = button.dataset.layout;
    document.querySelectorAll('.dashboard-controls [data-layout]').forEach((peer) => peer.setAttribute('aria-pressed', String(peer === button)));
  });
});
renderDashboard('Bereit für die Beispielsanalyse. Alle Abläufe werden lokal simuliert.');
