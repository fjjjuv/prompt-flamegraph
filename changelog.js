/* Live changelog: fills #changelog-tbody from the GitHub releases API.
 * The static rows in about.html are kept as a fallback when the API is
 * unreachable (offline, rate-limited) or JavaScript is disabled.
 * Update-site-changelog workflow keeps the static rows fresh too. */
(function () {
  'use strict';

  var API = 'https://api.github.com/repos/fjjjuv/prompt-flamegraph/releases?per_page=50';

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

  var lastReleases = null;

  function render() {
    if (!lastReleases) return;
    var lang = document.documentElement.lang === 'fr' ? 'fr' : 'en';
    var rows = [];
    lastReleases.forEach(function (rel) {
      if (rel.draft) return;
      var ver = rel.tag_name.replace(/^v/, '');
      var h = HIGHLIGHTS[ver];
      rows.push({
        date: (rel.published_at || '').slice(0, 10),
        ver: ver,
        text: h ? h[lang] : firstLineSummary(rel.body)
      });
    });
    Object.keys(EXTRA_DATES).forEach(function (ver) {
      rows.push({ date: EXTRA_DATES[ver], ver: ver, text: HIGHLIGHTS[ver][lang] });
    });
    rows.sort(function (a, b) { return a.date < b.date ? 1 : -1; });
    document.getElementById('changelog-tbody').innerHTML = rows.map(function (r) {
      return '<tr><td><code>' + esc(r.ver) + '</code></td><td>' + esc(r.text) + '</td></tr>';
    }).join('\n');
  }

  var tbody = document.getElementById('changelog-tbody');
  if (!tbody) return;

  fetch(API, { headers: { Accept: 'application/vnd.github+json' } })
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function (releases) { lastReleases = releases; render(); })
    .catch(function () { /* keep static fallback rows */ });

  /* Re-render when the language switcher changes <html lang>. */
  new MutationObserver(function () { render(); })
    .observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });
})();
