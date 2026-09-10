const flameData = {
  name: 'prompt',
  tokens: 102,
  color: '#7c5cf0',
  children: [
    {
      name: 'system_prompt',
      tokens: 18,
      color: '#f59e0b',
      children: [
        { name: 'role', tokens: 6, color: '#fbbf24' },
        { name: 'instructions', tokens: 12, color: '#d97706' },
      ],
    },
    {
      name: 'tools',
      tokens: 41,
      color: '#ef4444',
      children: [
        { name: 'read_file', tokens: 12, color: '#f87171', children: [
          { name: 'description', tokens: 5, color: '#a855f7' },
          { name: 'schema', tokens: 7, color: '#22c55e' },
        ] },
        { name: 'write_file', tokens: 10, color: '#dc2626' },
        { name: 'run_command', tokens: 9, color: '#b91c1c', children: [
          { name: 'description', tokens: 4, color: '#a855f7' },
          { name: 'schema', tokens: 5, color: '#22c55e' },
        ] },
        { name: 'search_web', tokens: 6, color: '#fb7185' },
        { name: 'send_email', tokens: 4, color: '#7f1d1d' },
      ],
    },
    {
      name: 'rag_context',
      tokens: 22,
      color: '#10b981',
      children: [
        { name: 'doc_1', tokens: 10, color: '#34d399' },
        { name: 'doc_2', tokens: 8, color: '#059669' },
        { name: 'doc_3', tokens: 4, color: '#047857' },
      ],
    },
    {
      name: 'chat_history',
      tokens: 21,
      color: '#3b82f6',
      children: [
        { name: 'turn_1', tokens: 7, color: '#60a5fa' },
        { name: 'turn_2', tokens: 6, color: '#2563eb' },
        { name: 'turn_3', tokens: 5, color: '#1d4ed8', children: [
          { name: 'user', tokens: 2, color: '#14b8a6' },
          { name: 'assistant', tokens: 3, color: '#ec4899' },
        ] },
        { name: 'turn_4', tokens: 3, color: '#1e40af' },
      ],
    },
  ],
};

function colorizeTree(node, index = { value: 0 }) {
  if (node.children) {
    node.children.forEach((c) => {
      const h = (index.value * 137) % 360;
      const s = 70;
      const l = 55;
      c.color = `hsl(${h}, ${s}%, ${l}%)`;
      index.value += 1;
      colorizeTree(c, index);
    });
  }
}
flameData.color = '#7c5cf0';
colorizeTree(flameData);

function renderBars(container, nodes, parentTokens) {
  const total = nodes.reduce((acc, n) => acc + n.tokens, 0);
  nodes.forEach((node) => {
    const bar = document.createElement('div');
    bar.className = 'flamegraph-bar';
    bar.style.width = `${(node.tokens / total) * 100}%`;
    bar.style.background = node.color;
    bar.dataset.name = node.name;
    bar.dataset.tokens = node.tokens;
    bar.dataset.parentTokens = parentTokens || total;
    bar.textContent = node.tokens >= 8 ? `${node.tokens} tokens` : '';
    container.appendChild(bar);
  });
}

function renderLegend(container, nodes) {
  nodes.forEach((node) => {
    const item = document.createElement('div');
    item.className = 'legend-item';
    const swatch = document.createElement('span');
    swatch.className = 'legend-color';
    swatch.style.background = node.color;
    item.appendChild(swatch);
    item.append(`${node.name} · ${node.tokens} tokens`);
    container.appendChild(item);
  });
}

function attachTooltip(barsContainer, tooltip) {
  barsContainer.querySelectorAll('.flamegraph-bar').forEach((bar) => {
    bar.addEventListener('mouseenter', (e) => {
      const name = bar.dataset.name;
      const tokens = parseInt(bar.dataset.tokens, 10);
      const total = parseInt(bar.dataset.parentTokens, 10);
      const pct = ((tokens / total) * 100).toFixed(1);
      tooltip.innerHTML = `<strong>${name}</strong><br/>${tokens} tokens (${pct}%)`;
      tooltip.style.display = 'block';
      const rect = e.currentTarget.getBoundingClientRect();
      const wrap = barsContainer.parentElement.getBoundingClientRect();
      tooltip.style.left = `${rect.left - wrap.left + rect.width / 2}px`;
      tooltip.style.top = `${rect.top - wrap.top - 10}px`;
      tooltip.style.transform = 'translate(-50%, -100%)';
    });
    bar.addEventListener('mouseleave', () => {
      tooltip.style.display = 'none';
    });
  });
}

function labelMinWidth(name) {
  const charW = window.innerWidth <= 640 ? 5.5 : 6.8;
  return Math.ceil(name.length * charW) + 14;
}

function pruneTree(node, totalTokens, maxW, depth, maxDepth) {
  if (!node.children || !node.children.length || depth >= maxDepth) {
    if (depth >= maxDepth) delete node.children;
    return;
  }
  if (depth > 0) {
    node.children = node.children.filter((c) => {
      const p = c.tokens / totalTokens;
      return Math.ceil(labelMinWidth(c.name) / p) <= maxW;
    });
  }
  if (!node.children.length) { delete node.children; return; }
  node.children.forEach((c) => pruneTree(c, totalTokens, maxW, depth + 1, maxDepth));
}

function renderReportGraph(rowsContainer, root, graphWidth, firstRender) {
  rowsContainer.innerHTML = '';

  let level = [{ node: root, width: 100 }];
  let i = 0;
  while (level.length) {
    const row = document.createElement('div');
    row.className = 'report-row';
    const next = [];
    level.forEach(({ node, width }) => {
      const bar = document.createElement('div');
      bar.className = 'report-bar';
      bar.style.width = `${width}%`;
      bar.style.background = node.color;
      bar.dataset.name = node.name;
      bar.dataset.tokens = node.tokens;
      bar.textContent = node.name;
      bar.title = `${node.name} — ${node.tokens} tokens`;
      if (firstRender) bar.style.transitionDelay = `${i * 0.025}s`;
      row.appendChild(bar);
      if (node.children && node.children.length) {
        const sum = node.children.reduce((a, c) => a + c.tokens, 0);
        node.children.forEach((c) => next.push({ node: c, width: (width * c.tokens) / sum }));
      }
      i += 1;
    });
    rowsContainer.appendChild(row);
    level = next;
  }
  rowsContainer.style.width = `${graphWidth}px`;
}

function renderReportLegend(container, nodes, totalTokens) {
  container.innerHTML = '';
  nodes.forEach((node) => {
    const pct = ((node.tokens / totalTokens) * 100).toFixed(1);
    const item = document.createElement('div');
    item.className = 'report-legend-item';
    const swatch = document.createElement('span');
    swatch.className = 'report-legend-color';
    swatch.style.background = node.color;
    item.appendChild(swatch);
    item.append(`${node.name} · ${node.tokens} (${pct}%)`);
    container.appendChild(item);
  });
}

function initReportTooltip(rowsContainer, tooltip) {
  const preview = document.querySelector('.report-preview');
  const showFor = (bar) => {
    const tokens = parseInt(bar.dataset.tokens, 10);
    const pct = ((tokens / flameData.tokens) * 100).toFixed(1);
    tooltip.innerHTML = `<strong>${bar.dataset.name}</strong><br/>${tokens} tokens (${pct}%)`;
    tooltip.style.display = 'block';
    const rect = bar.getBoundingClientRect();
    const wrap = preview.getBoundingClientRect();
    let left = rect.left - wrap.left + rect.width / 2;
    let top = rect.top - wrap.top - 8;
    left = Math.max(tooltip.offsetWidth / 2 + 4, left);
    left = Math.min(wrap.width - tooltip.offsetWidth / 2 - 4, left);
    tooltip.style.left = `${left}px`;
    if (top < 4) {
      top = rect.bottom - wrap.top + 8;
      tooltip.style.top = `${top}px`;
      tooltip.style.transform = 'translate(-50%, 0)';
    } else {
      tooltip.style.top = `${top}px`;
      tooltip.style.transform = 'translate(-50%, -100%)';
    }
  };
  const hide = () => { tooltip.style.display = 'none'; };

  rowsContainer.addEventListener('mouseover', (e) => {
    const bar = e.target.closest('.report-bar');
    if (bar) showFor(bar);
  });
  rowsContainer.addEventListener('mouseout', (e) => {
    if (!e.relatedTarget || !e.relatedTarget.closest('.report-bar')) hide();
  });
  rowsContainer.addEventListener('click', (e) => {
    const bar = e.target.closest('.report-bar');
    if (bar) showFor(bar);
  });
  rowsContainer.addEventListener('touchstart', (e) => {
    const bar = e.target.closest('.report-bar');
    if (bar) showFor(bar);
  }, { passive: true });
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.report-graph') && !e.target.closest('.report-tooltip')) hide();
  });
  document.addEventListener('touchstart', (e) => {
    if (!e.target.closest('.report-graph') && !e.target.closest('.report-tooltip')) hide();
  }, { passive: true });
}

function initFlamegraph() {
  const bars = document.getElementById('flamegraph-bars');
  const tooltip = document.getElementById('flamegraph-tooltip');
  const legend = document.getElementById('flamegraph-legend');
  if (!bars || !tooltip) return;

  renderBars(bars, flameData.children, flameData.tokens);
  attachTooltip(bars, tooltip);
  if (legend) renderLegend(legend, flameData.children);
}

function initReportPreview() {
  const report = document.getElementById('report-graph');
  const rows = document.getElementById('report-rows');
  const legend = document.getElementById('report-legend');
  if (!report || !rows) return;

  const tooltip = document.createElement('div');
  tooltip.className = 'report-tooltip';
  const preview = document.querySelector('.report-preview');
  if (preview) preview.appendChild(tooltip);

  const root = JSON.parse(JSON.stringify({
    name: flameData.name,
    tokens: flameData.tokens,
    color: flameData.color,
    children: flameData.children,
  }));

  const draw = (first) => {
    rows.innerHTML = '';
    const containerW = report.getBoundingClientRect().width - 48;
    const maxDepth = window.innerWidth <= 640 ? 2 : window.innerWidth <= 1024 ? 3 : 4;
    const tree = JSON.parse(JSON.stringify(root));
    let topLevelNeed = 0;
    tree.children.forEach((c) => {
      const need = Math.ceil(labelMinWidth(c.name) / (c.tokens / tree.tokens));
      if (need > topLevelNeed) topLevelNeed = need;
    });
    const graphW = Math.max(containerW, Math.min(topLevelNeed, 640));
    pruneTree(tree, tree.tokens, graphW, 0, maxDepth);
    renderReportGraph(rows, tree, graphW, first);
    report.scrollLeft = 0;
    if (legend) renderReportLegend(legend, tree.children, tree.tokens);
  };

  draw(true);
  report.scrollLeft = 0;
  initReportTooltip(rows, tooltip);

  const afterVisible = () => report.classList.add('is-visible');
  if ('IntersectionObserver' in window) {
    const obs = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) { afterVisible(); obs.unobserve(e.target); }
      });
    }, { threshold: 0.15 });
    obs.observe(report);
  } else {
    afterVisible();
  }

  let rT;
  window.addEventListener('resize', () => {
    clearTimeout(rT);
    rT = setTimeout(() => draw(false), 180);
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initFlamegraph();
  initReportPreview();
});
