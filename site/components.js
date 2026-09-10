const root = document.documentElement;
const storedTheme = localStorage.getItem('theme');
const systemTheme = window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
const initialTheme = storedTheme || systemTheme || 'dark';
root.setAttribute('data-theme', initialTheme);

function setTheme(theme) {
  root.setAttribute('data-theme', theme);
  localStorage.setItem('theme', theme);
  updateThemeIcon(theme);
}

function updateThemeIcon(theme) {
  const icon = document.querySelector('.theme-icon');
  if (!icon) return;
  icon.innerHTML = theme === 'light'
    ? '<path d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>'
    : '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>';
}

function initThemeToggle() {
  const btn = document.getElementById('theme-toggle');
  if (!btn) return;
  updateThemeIcon(initialTheme);
  btn.addEventListener('click', () => {
    const next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    setTheme(next);
  });
}

function initMobileNav() {
  const toggle = document.getElementById('nav-toggle');
  const links = document.querySelector('.nav-links');
  if (!toggle || !links) return;

  toggle.addEventListener('click', () => {
    const open = links.classList.toggle('open');
    toggle.setAttribute('aria-expanded', open);
    toggle.classList.toggle('open', open);
  });

  links.addEventListener('click', (e) => {
    if (e.target.closest('a')) {
      links.classList.remove('open');
      toggle.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
    }
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && links.classList.contains('open')) {
      links.classList.remove('open');
      toggle.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
      toggle.focus();
    }
  });
}

function initActiveNav() {
  const normalize = (p) => {
    const path = p.replace(/\/index\.html$/, '').replace(/\/$/, '') || '/';
    return path === '/prompt-flamegraph' ? '/' : path;
  };
  const current = normalize(location.pathname);
  document.querySelectorAll('.nav-links a').forEach((a) => {
    if (normalize(new URL(a.href).pathname) === current) {
      a.classList.add('active');
      a.setAttribute('aria-current', 'page');
    }
  });
}

function initBackToTop() {
  const btn = document.getElementById('back-to-top');
  if (!btn) return;
  const toggle = () => btn.classList.toggle('visible', window.scrollY > 320);
  window.addEventListener('scroll', toggle, { passive: true });
  toggle();
  btn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
}

function initScrollReveal() {
  const els = document.querySelectorAll('.reveal');
  if (!els.length) return;
  const obs = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (e.isIntersecting) {
        e.target.classList.add('visible');
        obs.unobserve(e.target);
      }
    });
  }, { threshold: 0.12 });
  els.forEach((el) => obs.observe(el));
}

function setupCopyButtons() {
  document.querySelectorAll('.copy').forEach((button) => {
    const label = button.querySelector('.copy-label');
    const original = label ? label.textContent : '';
    button.addEventListener('click', async () => {
      const text = button.dataset.copy;
      try {
        await navigator.clipboard.writeText(text);
      } catch {
        const ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        ta.remove();
      }
      button.classList.add('copied');
      if (label) label.textContent = 'Copied';
      setTimeout(() => {
        button.classList.remove('copied');
        if (label) label.textContent = original;
      }, 1400);
    });
  });
}

function initTabs() {
  document.querySelectorAll('.tabs').forEach((tabs) => {
    const buttons = tabs.querySelectorAll('[role="tab"]');
    buttons.forEach((btn) => {
      btn.addEventListener('click', () => {
        const target = document.getElementById(btn.dataset.tabTarget);
        if (!target) return;
        buttons.forEach((b) => b.setAttribute('aria-selected', b === btn));
        tabs.querySelectorAll('[role="tabpanel"]').forEach((panel) => {
          panel.hidden = panel !== target;
        });
      });
    });
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initThemeToggle();
  initMobileNav();
  initActiveNav();
  initBackToTop();
  initScrollReveal();
  setupCopyButtons();
  initTabs();
});
