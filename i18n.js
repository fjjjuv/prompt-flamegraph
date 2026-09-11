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
      badge_license: "LGPL-3.0-or-later",
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
      feature_export_text: "Exportez en HTML, SVG, Markdown, JSON ou un graphique à barres coloré dans le terminal.",
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
      footer_built: "Conçu par <a href=\"https://github.com/fjjjuv\" target=\"_blank\" rel=\"noopener\">Fjjjuv</a>. Sous licence LGPL-3.0-or-later.",
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
      features_page_title: "Fonctionnalités · prompt-flamegraph",
      features_page_description: "Liste détaillée des fonctionnalités de prompt-flamegraph : flamegraphs interactifs, détection de gaspillage de tokens, diff de prompts, formats d'export et tokenizers plugables.",
      examples_page_title: "Exemples · prompt-flamegraph",
      examples_page_description: "Exemples de code et d'utilisation CLI pour prompt-flamegraph : profiler des prompts, détecter le gaspillage, comparer des versions et exporter des rapports.",
      docs_page_title: "Documentation · prompt-flamegraph",
      docs_page_description: "Référence API, options CLI et instructions d'installation pour prompt-flamegraph.",
      about_page_title: "À propos · prompt-flamegraph",
      about_page_description: "À propos de prompt-flamegraph : pourquoi il a été conçu, licence, auteur et où obtenir de l'aide.",
      not_found_page_title: "Page non trouvée · prompt-flamegraph",
      not_found_page_description: "Page non trouvée sur prompt-flamegraph.",
      lang_switch: "Changer de langue"
    },
    frText: {
      "Home": "Accueil",
      "Features": "Fonctionnalités",
      "Examples": "Exemples",
      "Docs": "Docs",
      "About": "À propos",
      "PyPI": "PyPI",
      "GitHub": "GitHub",
      "Dev.to": "Dev.to",
      "Source code, issues and pull requests.": "Code source, issues et pull requests.",
      "Install the package.": "Installez le package.",
      "Dev.to article": "Article Dev.to",
      "Read the story behind the tool.": "Lisez l'histoire derrière l'outil.",
      "Stop Guessing Where Your LLM Prompt Tokens Go": "Arrêtez de deviner où partent vos tokens de prompt",
      "Why it exists": "Pourquoi il existe",
      "When a prompt contains tools, RAG chunks and a long chat history, the token bill becomes a black box. prompt-flamegraph turns that black box into a picture you can reason about.": "Quand un prompt contient des outils, des chunks RAG et un long historique de chat, la facture de tokens devient une boîte noire. prompt-flamegraph transforme cette boîte noire en une image que l'on peut analyser.",
      "Design principles": "Principes de conception",
      "No required dependencies": "Aucune dépendance requise",
      "No server, no telemetry, no proxy": "Pas de serveur, pas de télémétrie, pas de proxy",
      "One function call, one output file": "Un appel de fonction, un fichier de sortie",
      "Pluggable tokenizers": "Tokenizers plugables",
      "Open source under LGPL-3.0-or-later": "Open source sous LGPL-3.0-or-later",
      "When to use it": "Quand l'utiliser",
      "Your prompts keep growing and you do not know why": "Vos prompts ne cessent de grossir et vous ne savez pas pourquoi",
      "You want to compare two prompt versions": "Vous voulez comparer deux versions de prompt",
      "You suspect duplicate context or too many tools": "Vous soupçonnez un doublon de contexte ou trop d'outils",
      "You need to explain token cost to a teammate": "Vous devez expliquer le coût des tokens à un collègue",
      "Author & license": "Auteur et licence",
      "prompt-flamegraph is maintained by Fjjjuv and released under the GNU Lesser General Public License v3.0 or later.": "prompt-flamegraph est maintenu par Fjjjuv et publié sous la GNU Lesser General Public License v3.0 ou ultérieure.",
      "The story behind the tool, with step-by-step examples.": "L'histoire derrière l'outil, avec des exemples pas à pas.",
      "Read on Dev.to": "Lire sur Dev.to",
      "Install the latest release.": "Installez la dernière version.",
      "Changelog": "Journal des versions",
      "Latest changes from the repository.": "Dernières modifications du dépôt.",
      "Version": "Version",
      "Highlights": "Points forts",
      "Version sync, README updates with PyPI and Dev.to links.": "Synchronisation de version, mises à jour du README avec les liens PyPI et Dev.to.",
      "README badges, waste detection example, copyright year updates.": "Badges README, exemple de détection de gaspillage, mises à jour de l'année de copyright.",
      "Demo screenshot in README.": "Capture d'écran de démo dans le README.",
      "API payload adapters, model presets and dynamic pricing, CI budget gate, framework adapters, JSON export, aggregation buckets, LGPL-3.0-or-later license.": "Adaptateurs de payloads d'API, presets de modèles et tarification dynamique, garde de budget CI, adaptateurs de frameworks, export JSON, buckets d'agrégation, licence LGPL-3.0-or-later.",
      "Initial release with HTML/SVG/Markdown flamegraphs, waste detection, diff, terminal output and CLI.": "Version initiale avec des flamegraphs HTML/SVG/Markdown, la détection de gaspillage, le diff, la sortie terminal et la CLI.",
      "Contribute": "Contribuer",
      "Open an issue, submit a PR or share the project.": "Ouvrez une issue, soumettez une PR ou partagez le projet.",
      "Issues": "Issues",
      "Report bugs or request features.": "Signalez des bugs ou demandez des fonctionnalités.",
      "Open an issue": "Ouvrir une issue",
      "Pull requests": "Pull requests",
      "Contributions are welcome.": "Les contributions sont les bienvenues.",
      "Submit a PR": "Soumettre une PR",
      "Share": "Partager",
      "PyPI, GitHub, Dev.to and the companion optimizer.": "PyPI, GitHub, Dev.to et l'optimizer compagnon.",
      "See links": "Voir les liens",
      "Installation": "Installation",
      "Core package has no required dependencies. Optional extras add tiktoken and rich.": "Le package de base n'a pas de dépendances requises. Les extras optionnels ajoutent <code>tiktoken</code> et <code>rich</code>.",
      "bash": "bash",
      "Python API": "API Python",
      "All public functions are exported from prompt_flamegraph.": "Toutes les fonctions publiques sont exportées depuis <code>prompt_flamegraph</code>.",
      "Function": "Fonction",
      "Return": "Retour",
      "What it does": "Ce qu'elle fait",
      "Build a tree and write a standalone HTML flamegraph.": "Construit un arbre et écrit un flamegraph HTML autonome.",
      "Build a diff tree and write a standalone HTML diff.": "Construit un arbre de diff et écrit un diff HTML autonome.",
      "Build a token tree without rendering.": "Construit un arbre de tokens sans le rendre.",
      "Find duplicates, oversized categories and too many tools.": "Trouve les doublons, les catégories surdimensionnées et trop d'outils.",
      "Count tokens in a single string.": "Compte les tokens dans une seule chaîne.",
      "Resolve a tokenizer name or callable.": "Résout un nom de tokenizer ou une fonction.",
      "python": "python",
      "Node": "Nœud",
      "Internal tree node. Useful when you want to inspect the tree yourself.": "Nœud interne de l'arbre. Utile quand vous voulez inspecter l'arbre vous-même.",
      "WasteReport": "WasteReport",
      "Finding": "Observation",
      "One waste observation.": "Une observation de gaspillage.",
      "Tokenizer values": "Valeurs du tokenizer",
      "Strings or callables accepted anywhere a tokenizer is expected.": "Chaînes ou fonctions acceptées partout où un tokenizer est attendu.",
      "CLI options": "Options CLI",
      "Run prompt-flamegraph --help for the full list.": "Exécutez <code>prompt-flamegraph --help</code> pour la liste complète.",
      "Option": "Option",
      "Description": "Description",
      "Default": "Défaut",
      "JSON file, raw JSON string or OpenAI/Anthropic payload; - reads stdin.": "Fichier JSON, chaîne JSON brute ou payload OpenAI/Anthropic ; <code>-</code> lit stdin.",
      "Required unless --demo": "Requis sauf si <code>--demo</code>",
      "Output file (inferred from format).": "Fichier de sortie (déduit du format).",
      "prompt_flamegraph.<ext>": "<code>prompt_flamegraph.&lt;ext&gt;</code>",
      "Title in the generated report.": "Titre dans le rapport généré.",
      "Prompt Flamegraph / Prompt Diff": "Flamegraph de prompt / Diff de prompt",
      "html, svg, md or json.": "html, svg, md ou json.",
      "Cost per token, e.g. 1.5e-6.": "Coût par token, par ex. <code>1.5e-6</code>.",
      "Diff input against another file.": "Fichier d'entrée à comparer avec un autre.",
      "Print a bar chart in the terminal.": "Affiche un graphique à barres dans le terminal.",
      "Disable waste detection for HTML.": "Désactive la détection de gaspillage pour HTML.",
      "Use the built-in sample prompt.": "Utilise le prompt d'exemple intégré.",
      "Graph dimensions in pixels.": "Dimensions du graphique en pixels.",
      "Next steps": "Prochaines étapes",
      "Try the examples or read the feature deep-dive.": "Essayez les exemples ou lisez l'approfondissement des fonctionnalités.",
      "Ready-to-run snippets for Python and the CLI.": "Extraits prêts à exécuter pour Python et la CLI.",
      "See examples": "Voir les exemples",
      "Understand waste detection, diffs and exports.": "Comprendre la détection de gaspillage, les diffs et les exports.",
      "See features": "Voir les fonctionnalités",
      "Source": "Source",
      "Read the implementation on GitHub.": "Lisez l'implémentation sur GitHub.",
      "From quick profiling to waste detection and prompt diffs.": "Du profilage rapide à la détection de gaspillage et aux diffs de prompts.",
      "Profile a prompt": "Profiler un prompt",
      "Detect waste": "Détecter le gaspillage",
      "Diff prompts": "Différer les prompts",
      "Command line": "Ligne de commande",
      "Same features, without writing a single line of Python.": "Les mêmes fonctionnalités, sans écrire une seule ligne de Python.",
      "terminal": "terminal",
      "Read JSON from a file": "Lire le JSON depuis un fichier",
      "The CLI accepts a JSON file, a raw JSON string or an OpenAI/Anthropic payload — and reads stdin with -.": "La CLI accepte un fichier JSON, une chaîne JSON brute ou un payload OpenAI/Anthropic — et lit stdin avec <code>-</code>.",
      "Adapters": "Adaptateurs",
      "Model-aware pricing": "Tarification adaptée au modèle",
      "Pass --model gpt-4o and the tokenizer, per-token price and context window come from the model preset.": "Passez <code>--model gpt-4o</code> et le tokenizer, le prix par token et la fenêtre de contexte viennent du preset du modèle.",
      "Fail a pipeline when a prompt outgrows its budget — --budget exits with code 3, after the report is written.": "Faites échouer un pipeline quand un prompt dépasse son budget — <code>--budget</code> quitte avec le code 3, après l'écriture du rapport.",
      "Estimate cost": "Estimer le coût",
      "Pass --cost in dollars per token and the report shows estimated spend per category.": "Passez <code>--cost</code> en dollars par token et le rapport montre le coût estimé par catégorie.",
      "With OpenAI-style token counts": "Avec des comptes de tokens style OpenAI",
      "Install the tiktoken extra to match OpenAI models.": "Installez l'extra <code>tiktoken</code> pour correspondre aux modèles OpenAI.",
      "Install the extra": "Installer l'extra",
      "Use it in code": "L'utiliser dans le code",
      "Keep exploring": "Continuez à explorer",
      "Read the API docs or check the feature list.": "Lisez la documentation API ou consultez la liste des fonctionnalités.",
      "API docs": "Docs API",
      "Function signatures, parameters and return types.": "Signatures de fonctions, paramètres et types de retour.",
      "Read the docs": "Lire la doc",
      "What the tool can do and why it helps.": "Ce que l'outil peut faire et pourquoi il aide.",
      "Live demo": "Démo en direct",
      "See the interactive flamegraph on the home page.": "Voir le flamegraph interactif sur la page d'accueil.",
      "Back to demo": "Retour à la démo",
      "Interactive flamegraph": "Flamegraph interactif",
      "Each block in the flamegraph represents a part of your prompt. Width is proportional to token count, so the biggest budget eaters stand out immediately.": "Chaque bloc du flamegraph représente une partie de votre prompt. La largeur est proportionnelle au nombre de tokens, donc les plus gros consommateurs de budget ressortent immédiatement.",
      "Built for structured prompts": "Conçu pour les prompts structurés",
      "Accepts nested dict, list and str structures. Common top-level keys like system_prompt, tools, rag_context and chat_history become the top row.": "Accepte les structures imbriquées <code>dict</code>, <code>list</code> et <code>str</code>. Les clés de premier niveau courantes comme <code>system_prompt</code>, <code>tools</code>, <code>rag_context</code> et <code>chat_history</code> deviennent la ligne du haut.",
      "Standalone output": "Sortie autonome",
      "The HTML report is a single file with no external dependencies. Open it in any browser, share it, or archive it with your experiment.": "Le rapport HTML est un seul fichier sans dépendances externes. Ouvrez-le dans n'importe quel navigateur, partagez-le ou archivez-le avec votre expérience.",
      "Cost overlay": "Superposition du coût",
      "Pass cost_per_token and the report shows the estimated price of each category, not just the raw token count.": "Passez <code>cost_per_token</code> et le rapport montre le prix estimé de chaque catégorie, pas seulement le nombre brut de tokens.",
      "Hover and explore": "Survoler et explorer",
      "The report renders the tree as stacked, colored bars. Move the cursor over a block to see its name, tokens and share of the total.": "Le rapport rend l'arbre sous forme de barres empilées et colorées. Déplacez le curseur sur un bloc pour voir son nom, ses tokens et sa part du total.",
      "Aggregation buckets": "Buckets d'agrégation",
      "Nodes too thin to draw fold into striped · N more · buckets so the graph stays readable. Pass --no-aggregate (or aggregate=False) to draw every node — see the unaggregated demo.": "Les nœuds trop fins pour être dessinés sont regroupés dans des buckets <code>· N more ·</code> pour garder le graphe lisible. Passez <code>--no-aggregate</code> (ou <code>aggregate=False</code>) pour tout dessiner — voir la <a href=\"https://raw.githubusercontent.com/fjjjuv/prompt-flamegraph/main/docs/images/flamegraph_no_aggregate.png\" target=\"_blank\" rel=\"noopener\">démo non agrégée</a>.",
      "Token waste detection": "Détection de gaspillage de tokens",
      "detect_waste() scans the prompt tree and returns concrete findings you can act on before calling the API.": "<code>detect_waste()</code> analyse l'arbre du prompt et retourne des constats concrets sur lesquels agir avant d'appeler l'API.",
      "Detections included": "Détections incluses",
      "Duplicate text across leaves": "Textes en double à travers les feuilles",
      "Too many tools declared at once": "Trop d'outils déclarés en une fois",
      "Oversized RAG context": "Contexte RAG surdimensionné",
      "Long chat history": "Historique de chat long",
      "Large system prompt": "Prompt système large",
      "WasteReport output": "Sortie WasteReport",
      "Each report contains total_tokens, wasted_tokens and a list of Findings. A finding has a kind, path, human message and the number of tokens_wasted.": "Chaque rapport contient <code>total_tokens</code>, <code>wasted_tokens</code> et une liste d'<code>Findings</code>. Une observation a un <code>kind</code>, un <code>path</code>, un <code>message</code> lisible et le nombre de <code>tokens_wasted</code>.",
      "Kind": "Type",
      "What it means": "Signification",
      "Action": "Action",
      "duplicate": "<code>duplicate</code>",
      "The same text appears in several leaves.": "Le même texte apparaît dans plusieurs feuilles.",
      "Dedupe your RAG chunks or history.": "Dédoublonnez vos chunks RAG ou l'historique.",
      "too_many_tools": "<code>too_many_tools</code>",
      "More than 5 tool definitions.": "Plus de 5 définitions d'outils.",
      "Only declare tools the model is likely to call.": "Ne déclarez que les outils que le modèle est susceptible d'appeler.",
      "huge_rag": "<code>huge_rag</code>",
      "RAG context is over 50% of the prompt.": "Le contexte RAG dépasse 50 % du prompt.",
      "Trim, rerank or chunk your documents.": "Raccourcissez, re-classez ou découpez vos documents.",
      "long_history": "<code>long_history</code>",
      "Chat history is over 30% of the prompt.": "L'historique de chat dépasse 30 % du prompt.",
      "Summarize or truncate old turns.": "Résumez ou tronquez les anciens tours.",
      "large_system_prompt": "<code>large_system_prompt</code>",
      "System prompt is over 35% of the prompt.": "Le prompt système dépasse 35 % du prompt.",
      "Make it shorter or split instructions.": "Raccourcissez-le ou divisez les instructions.",
      "Prompt diff": "Différence de prompts",
      "Compare two versions of the same prompt and see where tokens were added, removed or changed. Useful for A/B testing system prompts or RAG chunking strategies.": "Comparez deux versions du même prompt et voyez où les tokens ont été ajoutés, supprimés ou modifiés. Utile pour les tests A/B de prompts système ou de stratégies de chunking RAG.",
      "Color-coded changes": "Changements colorés",
      "The diff report uses green for added, red for removed and orange for changed nodes. Unchanged nodes stay neutral.": "Le rapport de diff utilise le vert pour ajouté, le rouge pour supprimé et l'orange pour modifié. Les nœuds inchangés restent neutres.",
      "Same export formats": "Mêmes formats d'export",
      "Diffs render to HTML, SVG and Markdown just like regular flamegraphs, so you can embed them in pull requests or documentation.": "Les diffs sont rendus en HTML, SVG et Markdown comme les flamegraphs classiques, donc vous pouvez les intégrer dans des pull requests ou de la documentation.",
      "Export formats": "Formats d'export",
      "Choose the output that fits your workflow.": "Choisissez la sortie qui correspond à votre workflow.",
      "Format": "Format",
      "Best for": "Idéal pour",
      "Command": "Commande",
      "HTML": "HTML",
      "Interactive exploration in the browser": "Exploration interactive dans le navigateur",
      "--format html or default": "<code>--format html</code> par défaut",
      "SVG": "SVG",
      "Embedding in documentation or presentations": "Intégration dans la documentation ou des présentations",
      "--format svg": "<code>--format svg</code>",
      "Markdown": "Markdown",
      "Paste into GitHub issues, PRs or wiki": "Coller dans des issues, PRs ou wiki GitHub",
      "--format md": "<code>--format md</code>",
      "JSON": "JSON",
      "Machine-readable output for CI and downstream tooling": "Sortie lisible par machine pour la CI et l'outillage en aval",
      "--format json": "<code>--format json</code>",
      "Terminal": "Terminal",
      "Quick look from the shell": "Coup d'œil rapide depuis le shell",
      "Use the default word-punctuation heuristic, install tiktoken for OpenAI-style counts, or pass your own callable.": "Utilisez l'heuristique mots-ponctuation par défaut, installez <code>tiktoken</code> pour des comptes style OpenAI, ou passez votre propre fonction.",
      "Default: words": "Par défaut : words",
      "Fast, dependency-free estimator that counts word-like tokens and punctuation. Perfect for quick checks and offline usage.": "Estimateur rapide et sans dépendance qui compte les tokens de type mots et la ponctuation. Parfait pour les vérifications rapides et l'utilisation hors ligne.",
      "tiktoken / cl100k": "tiktoken / cl100k",
      "Install with pip install prompt-flamegraph[tiktoken] then pass tokenizer=\"tiktoken\" for accurate counts matching OpenAI models.": "Installez avec <code>pip install prompt-flamegraph[tiktoken]</code> puis passez <code>tokenizer=\"tiktoken\"</code> pour des comptes précis correspondant aux modèles OpenAI.",
      "Custom callable": "Fonction personnalisée",
      "Any Callable[[str], int] works. Plug in your own tokenizer, a Hugging Face tokenizer, or a model-specific counter.": "Tout <code>Callable[[str], int]</code> fonctionne. Branchez votre propre tokenizer, un tokenizer Hugging Face, ou un compteur spécifique au modèle.",
      "CLI override": "Écrasement CLI",
      "Use --tokenizer tiktoken, --tokenizer words or any registered name from the command line.": "Utilisez <code>--tokenizer tiktoken</code>, <code>--tokenizer words</code> ou tout nom enregistré depuis la ligne de commande.",
      "Other nice things": "Autres petits plus",
      "Details that make the tool pleasant to use.": "Des détails qui rendent l'outil agréable à utiliser.",
      "Zero telemetry": "Zéro télémétrie",
      "No network calls, no analytics, no server. Your prompts stay local.": "Pas d'appels réseau, pas d'analytics, pas de serveur. Vos prompts restent locaux.",
      "Python 3.10+": "Python 3.10+",
      "Modern Python, no compatibility hacks, clean type annotations where it matters.": "Python moderne, pas d'astuces de compatibilité, des annotations de type propres quand c'est important.",
      "CLI with helpful defaults": "CLI avec bons paramètres par défaut",
      "Run --demo to see a sample report in seconds, or pipe JSON directly.": "Exécutez <code>--demo</code> pour voir un exemple de rapport en quelques secondes, ou envoyez du JSON directement.",
      "Model-aware profiling": "Profilage adapté au modèle",
      "Pass --model gpt-4o to derive the tokenizer encoding, per-token pricing and context window. --list-models shows every preset.": "Passez <code>--model gpt-4o</code> pour dériver l'encodage du tokenizer, le prix par token et la fenêtre de contexte. <code>--list-models</code> affiche tous les presets.",
      "Dynamic pricing": "Tarification dynamique",
      "--update-models refreshes LiteLLM community pricing into a local cache; --offline (or PROMPT_FLAMEGRAPH_OFFLINE) keeps it bundled-only. Prices are community estimates.": "<code>--update-models</code> rafraîchit les tarifs communautaires LiteLLM dans un cache local ; <code>--offline</code> (ou <code>PROMPT_FLAMEGRAPH_OFFLINE</code>) reste sur les données intégrées. Les prix sont des estimations communautaires.",
      "Adapters for anything": "Des adaptateurs pour tout",
      "normalize() and from_messages() take raw OpenAI/Anthropic payloads; from_langchain(), from_litellm_messages() and profile_any() adapt framework objects by duck-typing — langchain is never imported.": "<code>normalize()</code> et <code>from_messages()</code> acceptent les payloads OpenAI/Anthropic bruts ; <code>from_langchain()</code>, <code>from_litellm_messages()</code> et <code>profile_any()</code> adaptent les objets de frameworks par duck-typing — langchain n'est jamais importé.",
      "CI budget gate": "Garde de budget CI",
      "--budget TOKENS exits with code 3 when the prompt is too big. Example workflow: .github/workflows/prompt-budget.yml.example.": "<code>--budget TOKENS</code> quitte avec le code 3 quand le prompt est trop gros. Workflow d'exemple : <code>.github/workflows/prompt-budget.yml.example</code>.",
      "LGPL-3.0-or-later": "LGPL-3.0-or-later",
      "Open source, weak copyleft — free to import into proprietary code.": "Open source, copyleft faible — libre d'import dans du code propriétaire.",
      "Start using it": "Commencez à l'utiliser",
      "Try the examples, read the API docs or install from PyPI.": "Essayez les exemples, lisez la doc API ou installez depuis PyPI.",
      "Python snippets, CLI commands and real-world use cases.": "Extraits Python, commandes CLI et cas d'usage concrets.",
      "Full function reference and parameter list.": "Référence complète des fonctions et liste des paramètres.",
      "Install": "Installer",
      "Get the latest release on PyPI.": "Obtenez la dernière version sur PyPI.",
      "Diff prompts": "Diff de prompts",
      "profile_prompt(data, ...)": "<code>profile_prompt(data, ...)</code>",
      "str": "<code>str</code>",
      "diff_prompts(v1, v2, ...)": "<code>diff_prompts(v1, v2, ...)</code>",
      "build_tree(data, name=\"prompt\", tokenizer=None)": "<code>build_tree(data, name=\"prompt\", tokenizer=None)</code>",
      "Node": "Nœud",
      "detect_waste(tree)": "<code>detect_waste(tree)</code>",
      "WasteReport": "WasteReport",
      "count_tokens(text, tokenizer=None)": "<code>count_tokens(text, tokenizer=None)</code>",
      "get_tokenizer(tokenizer=None)": "<code>get_tokenizer(tokenizer=None)</code>",
      "normalize(payload)": "<code>normalize(payload)</code>",
      "dict": "<code>dict</code>",
      "Convert a raw OpenAI/Anthropic payload into a prompt dict.": "Convertit un payload OpenAI/Anthropic brut en dict de prompt.",
      "from_messages(messages)": "<code>from_messages(messages)</code>",
      "Build a prompt dict from a chat messages list.": "Construit un dict de prompt depuis une liste de messages de chat.",
      "from_langchain(obj)": "<code>from_langchain(obj)</code>",
      "Convert LangChain-style objects by duck-typing.": "Convertit les objets style LangChain par duck-typing.",
      "from_litellm_messages(msgs)": "<code>from_litellm_messages(msgs)</code>",
      "Convert a LiteLLM message list.": "Convertit une liste de messages LiteLLM.",
      "profile_any(obj, ...)": "<code>profile_any(obj, ...)</code>",
      "Auto-detect the input shape and profile it.": "Détecte automatiquement la forme de l'entrée et la profile.",
      "Tokenizer": "Tokenizer",
      "name: string": "<code>name</code>: string",
      "tokens: int": "<code>tokens</code>: int",
      "children: list of Nodes": "<code>children</code>: liste de Nœuds",
      "text: string or None": "<code>text</code>: string ou None",
      "is_leaf: property": "<code>is_leaf</code>: propriété",
      "Returned by detect_waste().": "Retourné par <code>detect_waste()</code>.",
      "total_tokens: int": "<code>total_tokens</code>: int",
      "wasted_tokens: int": "<code>wasted_tokens</code>: int",
      "waste_ratio: float property": "<code>waste_ratio</code>: propriété float",
      "findings: list of Finding objects": "<code>findings</code>: liste d'objets Finding",
      "kind: string": "<code>kind</code>: string",
      "path: string": "<code>path</code>: string",
      "message: string": "<code>message</code>: string",
      "tokens_wasted: int": "<code>tokens_wasted</code>: int",
      "None: auto-loads tiktoken if installed, else words": "<code>None</code>: charge automatiquement <code>tiktoken</code> s'il est installé, sinon <code>words</code>",
      "\"tiktoken\" / \"cl100k_*\"": "<code>\"tiktoken\"</code> / <code>\"cl100k_*\"</code>",
      "\"words\": built-in heuristic": "<code>\"words\"</code>: heuristique intégrée",
      "Any Callable[[str], int]": "Tout <code>Callable[[str], int]</code>",
      "input": "<code>input</code>",
      "-o, --output": "<code>-o, --output</code>",
      "-t, --title": "<code>-t, --title</code>",
      "--format": "<code>--format</code>",
      "--tokenizer": "<code>--tokenizer</code>",
      "--cost": "<code>--cost</code>",
      "--diff FILE": "<code>--diff FICHIER</code>",
      "--terminal": "<code>--terminal</code>",
      "--no-waste": "<code>--no-waste</code>",
      "--demo": "<code>--demo</code>",
      "--width, --height": "<code>--width, --height</code>",
      "1200x720": "1200x720",
      "--model MODEL": "<code>--model MODÈLE</code>",
      "Derive tokenizer, pricing and context window from a model preset (e.g. gpt-4o).": "Dérive le tokenizer, le prix et la fenêtre de contexte d'un preset de modèle (par ex. gpt-4o).",
      "--list-models": "<code>--list-models</code>",
      "List bundled and cached model presets.": "Liste les presets de modèles intégrés et en cache.",
      "--update-models": "<code>--update-models</code>",
      "Refresh LiteLLM community pricing into the local cache.": "Rafraîchit les tarifs communautaires LiteLLM dans le cache local.",
      "--offline": "<code>--offline</code>",
      "Bundled models only; also PROMPT_FLAMEGRAPH_OFFLINE.": "Modèles intégrés uniquement ; aussi <code>PROMPT_FLAMEGRAPH_OFFLINE</code>.",
      "--budget TOKENS": "<code>--budget TOKENS</code>",
      "Exit with code 3 when total tokens exceed the budget.": "Quitte avec le code 3 quand le total de tokens dépasse le budget.",
      "--no-aggregate": "<code>--no-aggregate</code>",
      "Draw every node instead of folding thin ones into buckets.": "Dessine chaque nœud au lieu de regrouper les plus fins dans des buckets.",
      "Toggle navigation": "Ouvrir la navigation",
      "Copy install command": "Copier la commande d'installation",
      "Copy quick start code": "Copier le code de démarrage",
      "Copy waste report": "Copier le rapport",
      "Back to top": "Retour en haut",
      "Language": "Langue",
      "Main navigation": "Navigation principale",
      "Interactive prompt token flamegraph": "Flamegraph de tokens de prompt interactif",
      "prompt-flamegraph HTML report preview showing an interactive token flamegraph with waste findings": "Aperçu du rapport HTML prompt-flamegraph montrant un flamegraph de tokens interactif avec des constats de gaspillage"
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
    if (document.documentElement.lang === lang) return;
    location.reload();
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

    if (lang === 'fr') {
      translateByText();
      translateAria();
    }
  }

  function translateByText() {
    const dict = I18N.frText || {};
    if (!dict) return;
    const allowedChildren = new Set(['CODE','SPAN','STRONG','EM','B','I','A','BR','SMALL','SUP','SUB']);
    const selector = 'h1, h2, h3, h4, h5, h6, p, li, th, td, span, button, label, figcaption, summary, a';
    document.querySelectorAll(selector).forEach(el => {
      if (el.hasAttribute('data-i18n') || el.hasAttribute('data-i18n-title') || el.hasAttribute('data-i18n-meta')) return;
      if (el.closest('pre, code, svg, script, style, head, title, meta, .no-i18n')) return;
      if (el.querySelector('[data-i18n]')) return;
      for (const c of el.children) {
        if (!allowedChildren.has(c.tagName)) return;
      }
      const text = el.textContent.trim().replace(/\s+/g, ' ');
      if (dict[text]) el.innerHTML = dict[text];
    });
  }

  function translateAria() {
    const dict = I18N.frText || {};
    if (!dict) return;
    const stripTags = s => s.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
    document.querySelectorAll('[aria-label]').forEach(el => {
      if (el.hasAttribute('data-i18n') || el.hasAttribute('data-i18n-title') || el.hasAttribute('data-i18n-meta')) return;
      const text = el.getAttribute('aria-label').trim().replace(/\s+/g, ' ');
      if (dict[text]) el.setAttribute('aria-label', stripTags(dict[text]));
    });
  }

  function renderSwitcher() {
    const header = document.querySelector('.nav-actions');
    if (!header) return;
    const select = document.createElement('select');
    select.id = 'lang-switch';
    select.className = 'lang-switch';
    select.setAttribute('aria-label', 'Language');
    select.innerHTML = '<option value="fr">🇫🇷 FR</option><option value="en">🇬🇧 EN</option>';
    select.addEventListener('change', e => setLang(e.target.value));
    header.appendChild(select);
  }

  function init() {
    renderSwitcher();
    const lang = detect();
    document.documentElement.lang = lang;
    const switcher = document.getElementById('lang-switch');
    if (switcher) switcher.value = lang;
    if (lang === 'en') return;
    translate(lang);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();