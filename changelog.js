/* Live changelog: fills #changelog-tbody from the GitHub releases API.
 * The static rows in about.html are kept as a fallback when the API is
 * unreachable (offline, rate-limited) or JavaScript is disabled.
 * Rows with a curated French text use it; new releases are translated
 * on the fly via the free MyMemory API and cached in localStorage.
 * The update-site-changelog workflow keeps the static rows fresh too. */
(function () {
  'use strict';

  var API = 'https://api.github.com/repos/fjjjuv/prompt-flamegraph/releases?per_page=50';
  var TRANSLATE = 'https://api.mymemory.translated.net/get';
  var FR_CACHE_KEY = 'pfg-changelog-fr';

  /* Curated one-line highlights. Key: version without leading "v". */
  var HIGHLIGHTS = {
    '0.4.1': {
      en: 'Windows console and redirected-stream robustness, BOM-tolerant JSON input, CI matrix and trusted PyPI publishing.',
      fr: 'Robustesse des consoles Windows et des flux redirigés, entrée JSON tolérante au BOM, matrice CI et publication PyPI de confiance.'
    },
    '0.4.0': {
      en: 'Dark mode: theme="auto|light|dark" and --theme CLI flag, CSS custom properties, persisted sun/moon toggle.',
      fr: 'Mode sombre : theme="auto|light|dark" et flag CLI --theme, propriétés CSS personnalisées, bascule soleil/lune persistante.'
    },
    '0.3.3': {
      en: 'Hardening release: token-accuracy fixes, error handling, security.',
      fr: 'Version de durcissement : corrections de précision des tokens, gestion des erreurs, sécurité.'
    },
    '0.3.2': {
      en: 'OpenAI Responses API payloads, top-level exports, Markdown waste report, accessible tooltips, token-accuracy and CLI fixes.',
      fr: 'Payloads OpenAI Responses API, exports au niveau racine, rapport de gaspillage Markdown, infobulles accessibles, corrections de précision des tokens et de la CLI.'
    },
    '0.3.1': {
      en: 'README redesign, PyPI/GitHub version alignment.',
      fr: 'Refonte du README, alignement des versions PyPI/GitHub.'
    },
    '0.3.0': {
      en: 'API payload adapters, model presets and dynamic pricing, CI budget gate, framework adapters, JSON export, aggregation buckets, LGPL-3.0-or-later license.',
      fr: 'Adaptateurs de payloads d\u2019API, presets de modèles et tarification dynamique, garde de budget CI, adaptateurs de frameworks, export JSON, buckets d\u2019agrégation, licence LGPL-3.0-or-later.'
    },
    '0.2.4': {
      en: 'Website link in README and PyPI metadata.',
      fr: 'Lien du site dans le README et les métadonnées PyPI.'
    },
    '0.2.3': {
      en: 'Version sync, README updates with PyPI and Dev.to links.',
      fr: 'Synchronisation de version, mises à jour du README avec les liens PyPI et Dev.to.'
    },
    '0.2.2': {
      en: 'README badges, waste detection example, copyright year updates.',
      fr: 'Badges README, exemple de détection de gaspillage, mises à jour de l\u2019année de copyright.'
    },
    '0.2.1': {
      en: 'Demo screenshot in README.',
      fr: 'Capture d\u2019écran de démo dans le README.'
    },
    '0.2.0': {
      en: 'Initial release with HTML/SVG/Markdown flamegraphs, waste detection, diff, terminal output and CLI.',
      fr: 'Version initiale avec des flamegraphs HTML/SVG/Markdown, la détection de gaspillage, le diff, la sortie terminal et la CLI.'
    }
  };

  /* Versions on PyPI with no GitHub release — kept in the table by date. */
  var EXTRA_DATES = {
    '0.2.3': '2026-09-10',
    '0.2.2': '2026-09-09',
    '0.2.1': '2026-09-08',
    '0.2.0': '2026-09-07'
  };

  function esc(s) {
    return s.replace(/[&<>]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c];
    });
  }

  function firstLineSummary(body) {
    var lines = (body || '').split('\n');
    for (var i = 0; i < lines.length; i++) {
      var line = lines[i].replace(/^[\s#\-*]+/, '').trim();
      if (line && line.charAt(0) !== '*') {
        return line.replace(/\[([^\]]+)\]\([^)]*\)/g, '$1');
      }
    }
    return 'See release notes on GitHub.';
  }

  function frCache() {
    try { return JSON.parse(localStorage.getItem(FR_CACHE_KEY) || '{}'); }
    catch (e) { return {}; }
  }

  /* Translate each English text to French via MyMemory, one request per
   * unique text, results cached in localStorage. Calls done(map). */
  function translateFr(texts, done) {
    var cache = frCache();
    var out = {};
    var pending = [];
    texts.forEach(function (t) {
      if (cache[t]) out[t] = cache[t];
      else if (pending.indexOf(t) === -1) pending.push(t);
    });
    var i = 0;
    (function next() {
      if (i >= pending.length) {
        try { localStorage.setItem(FR_CACHE_KEY, JSON.stringify(Object.assign(cache, out))); } catch (e) {}
        done(out);
        return;
      }
      var t = pending[i++];
      fetch(TRANSLATE + '?q=' + encodeURIComponent(t) + '&langpair=en|fr')
        .then(function (r) { return r.json(); })
        .then(function (d) {
          var tr = d && d.responseData && d.responseData.translatedText;
          out[t] = tr && tr.toUpperCase() !== 'QUERY LENGTH LIMIT EXCEEDED' ? tr : t;
          next();
        })
        .catch(function () { out[t] = t; next(); });
    })();
  }

  var rows = null; /* [{ver, en, fr|null}] */

  function render() {
    if (!rows) return;
    var lang = document.documentElement.lang === 'fr' ? 'fr' : 'en';
    var tbody = document.getElementById('changelog-tbody');
    tbody.innerHTML = rows.map(function (r, i) {
      var text = lang === 'fr' ? (r.fr || r.en) : r.en;
      return '<tr><td><code>' + esc(r.ver) + '</code></td><td data-cl="' + i + '">' + esc(text) + '</td></tr>';
    }).join('\n');
    if (lang !== 'fr') return;
    var missing = [];
    rows.forEach(function (r) { if (!r.fr && missing.indexOf(r.en) === -1) missing.push(r.en); });
    if (!missing.length) return;
    translateFr(missing, function (map) {
      if (document.documentElement.lang !== 'fr') return;
      rows.forEach(function (r) { if (!r.fr) r.fr = map[r.en] || r.en; });
      render();
    });
  }

  function buildRows(releases) {
    rows = [];
    releases.forEach(function (rel) {
      if (rel.draft) return;
      var ver = rel.tag_name.replace(/^v/, '');
      var h = HIGHLIGHTS[ver];
      rows.push({
        date: (rel.published_at || '').slice(0, 10),
        ver: ver,
        en: h ? h.en : firstLineSummary(rel.body),
        fr: h ? h.fr : null
      });
    });
    Object.keys(EXTRA_DATES).forEach(function (ver) {
      rows.push({ date: EXTRA_DATES[ver], ver: ver, en: HIGHLIGHTS[ver].en, fr: HIGHLIGHTS[ver].fr });
    });
    rows.sort(function (a, b) { return a.date < b.date ? 1 : -1; });
  }

  if (!document.getElementById('changelog-tbody')) return;

  fetch(API, { headers: { Accept: 'application/vnd.github+json' } })
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function (releases) { buildRows(releases); render(); })
    .catch(function () { /* keep static fallback rows */ });

  /* Re-render when the language switcher changes <html lang>. */
  new MutationObserver(render)
    .observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });
})();
