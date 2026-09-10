const flameData = {
  name: 'prompt',
  tokens: 102,
  children: [
    {
      name: 'system_prompt',
      tokens: 18,
      color: '#ffd166',
      children: [
        { name: 'role', tokens: 6, color: '#ffd166' },
        { name: 'instructions', tokens: 12, color: '#ffbc42' },
      ],
    },
    {
      name: 'tools',
      tokens: 41,
      color: '#ff7b00',
      children: [
        { name: 'read_file', tokens: 12, color: '#ff9f1c' },
        { name: 'write_file', tokens: 10, color: '#ff7b00' },
        { name: 'run_command', tokens: 9, color: '#ff6b00' },
        { name: 'search_web', tokens: 6, color: '#ff5400' },
        { name: 'send_email', tokens: 4, color: '#ff2a00' },
      ],
    },
    {
      name: 'rag_context',
      tokens: 22,
      color: '#06d6a0',
      children: [
        { name: 'doc_1', tokens: 10, color: '#06d6a0' },
        { name: 'doc_2', tokens: 8, color: '#04b38a' },
        { name: 'doc_3', tokens: 4, color: '#029f7a' },
      ],
    },
    {
      name: 'chat_history',
      tokens: 21,
      color: '#118ab2',
      children: [
        { name: 'turn_1', tokens: 7, color: '#118ab2' },
        { name: 'turn_2', tokens: 6, color: '#0d7a9e' },
        { name: 'turn_3', tokens: 5, color: '#096a8a' },
        { name: 'turn_4', tokens: 3, color: '#055a76' },
      ],
    },
  ],
};

const COLORS = flameData.children.map((c) => c.color);

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

function initFlamegraph() {
  const bars = document.getElementById('flamegraph-bars');
  const tooltip = document.getElementById('flamegraph-tooltip');
  const legend = document.getElementById('flamegraph-legend');
  if (!bars || !tooltip) return;

  renderBars(bars, flameData.children, flameData.tokens);
  attachTooltip(bars, tooltip);
  if (legend) renderLegend(legend, flameData.children);
}

document.addEventListener('DOMContentLoaded', initFlamegraph);
