/* Счётчик Метрики (с Вебвизором) и рекламный блок РСЯ на текстовых страницах сайта.
   Настройки берутся из config.js. Главная страница с картой подключает их сама (atlas.html),
   выбор посетителя о cookie общий: ключ 'atlas-cookie' в localStorage. */
(function () {
  var CFG = window.ATLAS_CONFIG || {};
  var adId = CFG.adBlockIdText || CFG.adBlockId;
  if (!CFG.metrikaId && !adId) return;

  var get = function () { try { return localStorage.getItem('atlas-cookie'); } catch (e) { return null; } };
  var set = function (v) { try { localStorage.setItem('atlas-cookie', v); } catch (e) { /* выбор действует до закрытия страницы */ } };
  var add = function (src) { var s = document.createElement('script'); s.async = true; s.src = src; document.head.appendChild(s); };

  var style = document.createElement('style');
  style.textContent =
    '.svc-cookie{position:fixed;z-index:50;left:12px;bottom:12px;max-width:420px;padding:12px 14px;display:flex;flex-direction:column;gap:10px;' +
    'font:13px/1.45 "Golos Text","Segoe UI",system-ui,sans-serif;background:var(--card,#fff);color:var(--ink,#14263a);' +
    'border:1px solid var(--line,#cdd7e0);border-radius:10px;box-shadow:0 6px 24px rgba(0,0,0,.18)}' +
    '.svc-cookie a{color:var(--accent,#c2500f)}.svc-cookie div{display:flex;gap:8px;justify-content:flex-end;flex-wrap:wrap}' +
    '.svc-cookie button{font:600 13px/1 inherit;font-family:inherit;padding:9px 12px;border-radius:8px;cursor:pointer;' +
    'border:1px solid var(--line,#cdd7e0);background:transparent;color:inherit}' +
    '.svc-cookie button.yes{background:var(--accent,#c2500f);border-color:var(--accent,#c2500f);color:var(--accent-ink,#fff)}' +
    '.svc-ad{margin:28px 0 0;min-height:90px}.svc-ad .note{display:block;font-size:12px;color:var(--muted,#5a6b7c);margin-bottom:4px}';
  document.head.appendChild(style);

  var start = function () {
    if (CFG.metrikaId) {
      window.ym = window.ym || function () { (window.ym.a = window.ym.a || []).push(arguments); };
      window.ym.l = Date.now();
      add('https://mc.yandex.ru/metrika/tag.js');
      window.ym(Number(CFG.metrikaId), 'init', { clickmap: true, trackLinks: true, accurateTrackBounce: true, webvisor: true });
    }
    var main = document.querySelector('main');
    if (adId && main) {
      var box = document.createElement('div');
      box.className = 'svc-ad';
      box.innerHTML = '<span class="note">Реклама</span><div id="yandex_rtb_' + adId + '"></div>';
      main.appendChild(box);
      window.yaContextCb = window.yaContextCb || [];
      window.yaContextCb.push(function () { window.Ya.Context.AdvManager.render({ blockId: adId, renderTo: 'yandex_rtb_' + adId }); });
      add('https://yandex.ru/ads/system/context.js');
    }
  };

  var ask = function () {
    var el = document.createElement('div');
    el.className = 'svc-cookie';
    el.setAttribute('role', 'dialog');
    el.setAttribute('aria-label', 'Файлы cookie');
    el.innerHTML = '<span>Сайт использует файлы cookie и сервисы Яндекса для статистики и показа рекламы. Подробности — в ' +
      '<a href="/privacy.html">политике обработки персональных данных</a>.</span>' +
      '<div><button type="button" class="no">Только необходимые</button><button type="button" class="yes">Принять</button></div>';
    var answer = function (v) { set(v); el.remove(); if (v === 'yes') start(); };
    el.querySelector('.yes').onclick = function () { answer('yes'); };
    el.querySelector('.no').onclick = function () { answer('no'); };
    document.body.appendChild(el);
  };

  var run = function () { var c = get(); if (c === 'yes') start(); else if (c !== 'no') ask(); };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run); else run();
})();
