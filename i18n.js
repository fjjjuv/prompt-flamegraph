(function () {
  'use strict';

  const I18N = {
    en: {},
    fr: {
      page_title: "prompt-flamegraph · Analyse des tokens de prompt",
      page_description: "Package Python léger et sans dépendance pour profiler les tokens de prompt LLM avec des flamegraphs interactifs, détection de gaspillage et export HTML/SVG/Markdown/terminal.",
      brand: "prompt-flamegraph",
      nav_home: "Accueil",
      nav_features: "Fonctionnalités",
      nav_examples: "Exemples",
      nav_docs: "Docs",
      nav_about: "À propos",
      nav_pypi: "PyPI",
      nav_github: "GitHub",
      nav_devto: "Dev.to",
      nav_toggle: "Ouvrir la navigation",
      hero_title: "Voyez où vont les tokens de votre prompt LLM",
      hero_lead: "Package Python léger et sans dépendance pour profiler les prompts avec des flamegraphs interactifs, la détection de gaspillage de tokens, les différences de prompts et des exportations HTML/SVG/Markdown/terminal.",
      install_cmd: "pip install prompt-flamegraph",
      copy: "Copier",
      btn_github: "Voir sur GitHub",
      btn_pypi: "Voir sur PyPI",
      badge_python: "Python 3.10+",
      badge_license: "GPL-3.0",
      badge_zero: "Zéro dépendance",
      demo_title: "Démo interactive du flamegraph",
      demo_desc: "Survolez les barres pour voir comment les tokens sont répartis entre le message système, les outils, le contexte RAG et l'historique de chat.",
      demo_total: "Total : <strong>102</strong> tokens · Coût estimé : <strong>0,000153 $</strong> à 1,5e-6/token",
      features_title: "Pourquoi utiliser prompt-flamegraph ?",
      features_desc: "Un outil ciblé pour un vrai problème : les tokens de prompt sont chers, opaques et faciles à gaspiller.",
      feature_visual: "Visualisation des tokens",
      feature_visual_text: "Transformez un prompt structuré en un flamegraph HTML interactif et repérez quelle catégorie consume le budget.",
      feature_waste: "Détection de gaspillage",
      feature_waste_text: "Repérez les textes en double, le contexte RAG surdimensionné, l'historique de chat long et trop d'outils avant d'appeler l'API.",
      feature_diff: "Différences de prompts",
      feature_diff_text: "Comparez deux versions de prompt et visualisez les tokens ajoutés, supprimés et modifiés.",
      feature_export: "Formats d'export multiples",
      feature_export_text: "Exportez en HTML, SVG, Markdown ou un graphique à barres coloré dans le terminal.",
      feature_zero: "Zéro dépendance",
      feature_zero_text: "Python pur, pas de serveur, pas de tableau de bord, pas de télémétrie. Extras optionnels <code>tiktoken</code> et <code>rich</code>.",
      feature_api: "CLI et API",
      feature_api_text: "Un appel de fonction en Python ou une seule commande dans votre terminal.",
      explore_features: "Toutes les fonctionnalités",
      quickstart_title: "Démarrage rapide",
      quickstart_desc: "Installez, appelez une fonction, ouvrez le rapport HTML.",
      filename_python: "python",
      quickstart_copy: "Copier le code de démarrage",
      more_examples: "Plus d'exemples",
      cli_title: "Exemples CLI",
      waste_title: "Détectez le gaspillage avant de payer",
      waste_desc: "Obtenez un WasteReport avec des constats concrets avant d'envoyer le prompt à une API.",
      filename_output: "résultat",
      waste_copy: "Copier le rapport",
      report_title: "À quoi ressemble le rapport",
      report_header: "Flamegraph de prompt",
      report_meta_tokens: "<strong>102</strong> tokens",
      report_meta_cats: "<strong>4</strong> catégories principales",
      report_meta_top: "Top : 41 outils (40,2 %) · 22 rag_context (21,6 %) · 21 chat_history (20,6 %) · 18 system_prompt (17,6 %)",
      report_cost: "Coût estimé : <strong>0,000153 $</strong>",
      report_footer: "Généré par <code>prompt-flamegraph</code>",
      links_title: "Liens et ressources",
      links_desc: "Package, source, article et projet compagnon.",
      link_pypi: "PyPI",
      link_pypi_text: "Installez la dernière version avec pip.",
      link_pypi_url: "pypi.org/project/prompt-flamegraph",
      link_github: "GitHub",
      link_github_text: "Code source, issues, pull requests et releases.",
      link_github_url: "github.com/fjjjuv/prompt-flamegraph",
      link_devto: "Article Dev.to",
      link_devto_text: "Guide pas à pas et motivations derrière l'outil.",
      link_devto_title: "Arrêtez de deviner où partent vos tokens",
      back_to_top: "Retour en haut",
      footer_built: "Conçu par <a href=\"https://github.com/fjjjuv\" target=\"_blank\" rel=\"noopener\">Fjjjuv</a>. Sous licence GPL-3.0.",
      not_found_title: "404",
      not_found_desc: "Cette page n'existe pas. Peut-être qu'un token s'est perdu.",
      not_found_home: "Retour à l'accueil",
      not_found_features: "Voir les fonctionnalités",
      lang_label: "Langue",
      lang_fr: "Français",
      lang_en: "English",
      features_hero_title: "Tout ce qu'il fait",
      features_hero_lead: "Un petit outil qui répond à une question simple : où vont les tokens de mon prompt, et est-ce que je les gaspille ?",
      examples_hero_title: "Exemples",
      examples_hero_lead: "Des extraits copier-coller que tu peux exécuter tout de suite. Tous les exemples fonctionnent avec le tokeniseur de mots intégré, sans extra.",
      docs_hero_title: "Documentation",
      docs_hero_lead: "Installe, importe, appelle. L'API est volontairement minimaliste pour commencer à profiler en quelques secondes.",
      about_hero_title: "À propos",
      about_hero_lead: "Conçu pour rendre l'utilisation des tokens de prompt visible, déboguable et bon marché.",
      lang_switch: "Changer de langue"
    }
  };

  const allowed = new Set(['en', 'fr']);
  const STORAGE_KEY = 'pfg-lang';

  function detect() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && allowed.has(saved)) return saved;
    const nav = navigator.language || navigator.userLanguage || 'en';
    const lang = nav.slice(0, 2).toLowerCase();
    return allowed.has(lang) ? lang : 'en';
  }

  function setLang(lang) {
    if (!allowed.has(lang)) lang = 'en';
    localStorage.setItem(STORAGE_KEY, lang);
    document.documentElement.lang = lang;
    translate(lang);
    const switcher = document.getElementById('lang-switch');
    if (switcher) switcher.value = lang;
  }

  function translate(lang) {
    const dict = I18N[lang] || {};
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      if (key && dict[key] !== undefined) {
        el.innerHTML = dict[key];
      }
    });

    const titleEl = document.querySelector('title[data-i18n-title]');
    if (titleEl) {
      const key = titleEl.getAttribute('data-i18n-title');
      if (dict[key]) document.title = dict[key];
    }

    const meta = document.querySelector('meta[data-i18n-meta]');
    if (meta) {
      const key = meta.getAttribute('data-i18n-meta');
      if (dict[key]) meta.setAttribute('content', dict[key]);
    }
  }

  function renderSwitcher() {
    const header = document.querySelector('.nav-actions');
    if (!header) return;
    const select = document.createElement('select');
    select.id = 'lang-switch';
    select.className = 'lang-switch';
    select.setAttribute('aria-label', 'Langue');
    select.innerHTML = '<option value="fr">FR</option><option value="en">EN</option>';
    select.addEventListener('change', e => setLang(e.target.value));
    header.appendChild(select);
  }

  function init() {
    renderSwitcher();
    const lang = detect();
    document.documentElement.lang = lang;
    if (lang === 'en') return;
    translate(lang);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
