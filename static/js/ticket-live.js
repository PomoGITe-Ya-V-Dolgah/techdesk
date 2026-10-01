(() => {
  'use strict';
  const controls = document.getElementById('notification-controls');
  if (!controls) return;
  let prefs = JSON.parse(document.getElementById('notification-preferences').textContent);
  const sound = document.getElementById('notification-sound');
  const scope = document.getElementById('notification-scope');
  const feedback = document.getElementById('notification-feedback');
  const notice = document.getElementById('ticket-notice');
  const table = document.getElementById('ticket-table');
  const status = document.getElementById('ticket-live-status');
  const key = `techdesk-notification-${prefs.userId}`;
  let cursor = null, generation = 0, saving = false, stopped = false, audio;
  const read = name => { try { return localStorage.getItem(name); } catch { return null; } };
  const write = (name, value) => { try { localStorage.setItem(name, value); } catch { /* Storage can be disabled. */ } };

  async function request(url, options = {}) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetch(url, {credentials: 'same-origin', cache: 'no-store', ...options, signal: controller.signal});
      if (response.redirected || response.status === 401) {
        stopped = true;
        throw new Error('Сессия завершена. Войдите снова.');
      }
      if (!response.ok) throw new Error('Не удалось связаться с сервером. Повторим автоматически.');
      return response;
    } finally { clearTimeout(timeout); }
  }

  function applyPreferences(next) {
    if (prefs.scope !== next.scope) { cursor = null; generation++; }
    prefs = {...prefs, ...next};
    sound.checked = prefs.sound;
    scope.value = prefs.scope;
  }

  async function unlock() {
    const Audio = window.AudioContext || window.webkitAudioContext;
    if (!Audio) throw new Error('Этот браузер не поддерживает звуковые уведомления.');
    audio ||= new Audio();
    await audio.resume();
    if (audio.state !== 'running') throw new Error('Разрешите звук для этого сайта в браузере.');
  }

  function beep() {
    if (!audio || audio.state !== 'running') return;
    const oscillator = audio.createOscillator();
    const gain = audio.createGain();
    const now = audio.currentTime;
    oscillator.frequency.setValueAtTime(740, now);
    oscillator.frequency.setValueAtTime(988, now + 0.12);
    gain.gain.setValueAtTime(0, now);
    gain.gain.linearRampToValueAtTime(0.12, now + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
    oscillator.connect(gain).connect(audio.destination);
    oscillator.start(now); oscillator.stop(now + 0.36);
  }

  document.getElementById('notification-test').addEventListener('click', async () => {
    try { await unlock(); beep(); feedback.textContent = 'Звук разрешён на этом устройстве.'; }
    catch (error) { feedback.textContent = error.message; }
  });
  document.addEventListener('pointerdown', () => {
    if (prefs.sound) unlock().catch(() => {});
  }, {once: true});

  async function savePreferences() {
    const next = {sound: sound.checked, scope: scope.value};
    saving = true; sound.disabled = scope.disabled = true;
    try {
      if (next.sound) await unlock();
      const csrf = document.querySelector('[name=csrfmiddlewaretoken]').value;
      const response = await request(controls.dataset.preferencesUrl, {
        method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf}, body: JSON.stringify(next)
      });
      applyPreferences(await response.json());
      cursor = null; generation++;
      write(`${key}-preferences`, JSON.stringify(next));
      feedback.textContent = 'Настройки сохранены.';
    } catch (error) { applyPreferences(prefs); feedback.textContent = error.message; }
    finally { saving = false; sound.disabled = scope.disabled = false; }
  }
  sound.addEventListener('change', savePreferences);
  scope.addEventListener('change', savePreferences);
  window.addEventListener('storage', event => {
    if (event.key === `${key}-preferences` && event.newValue) {
      try { applyPreferences(JSON.parse(event.newValue)); } catch { /* Ignore invalid storage. */ }
    }
  });

  async function showEvents(events) {
    if (!events.length) return;
    const last = events[events.length - 1];
    const show = () => {
      if (Number(read(`${key}-last-event`) || 0) >= last.id) return;
      write(`${key}-last-event`, String(last.id));
      notice.replaceChildren();
      const link = document.createElement('a');
      link.href = last.url;
      link.textContent = events.length > 1 ? `Новых событий: ${events.length}. Последняя заявка: #${last.ticket_id}` : `${last.kind === 'created' ? 'Новая заявка' : 'Вам назначена заявка'} #${last.ticket_id}: ${last.title}`;
      const close = document.createElement('button');
      close.type = 'button'; close.className = 'btn-close ms-2'; close.setAttribute('aria-label', 'Закрыть уведомление');
      close.addEventListener('click', () => { notice.hidden = true; });
      notice.append(link, close); notice.hidden = false;
      if (prefs.sound) beep();
    };
    if (navigator.locks) await navigator.locks.request(`${key}-sound`, show);
    else {
      const claim = `${Date.now()}-${Math.random()}`;
      write(`${key}-claim`, claim);
      await new Promise(resolve => setTimeout(resolve, 80));
      if (read(`${key}-claim`) === claim || read(`${key}-claim`) === null) show();
    }
  }

  async function pollEvents() {
    try {
      const version = generation;
      const url = new URL(controls.dataset.eventsUrl, location.origin);
      if (cursor !== null) url.searchParams.set('after', cursor);
      const data = await (await request(url)).json();
      if (version === generation) {
        cursor = data.cursor;
        await showEvents(data.events);
      }
    } catch (error) { feedback.textContent = error.message; }
    if (!stopped) setTimeout(pollEvents, 5000);
  }

  async function refreshTable() {
    if (!table || stopped) return;
    try {
      const url = new URL(table.dataset.refreshUrl, location.origin);
      url.search = location.search; url.searchParams.set('partial', '1');
      const html = await (await request(url)).text();
      table.innerHTML = html;
      status.textContent = `Обновлено ${new Date().toLocaleTimeString('ru-RU')}. Автообновление каждые 10 секунд`;
    } catch (error) { status.textContent = error.message; }
    if (!stopped) setTimeout(refreshTable, 10000);
  }
  pollEvents();
  if (table) setTimeout(refreshTable, 10000);
})();
