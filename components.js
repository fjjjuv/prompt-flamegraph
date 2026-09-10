const header = document.querySelector('.site-header');
let lastScrollY = window.scrollY;

function initHeaderScroll() {
  if (!header) return;
  window.addEventListener('scroll', () => {
    const y = window.scrollY;
    if (y > 80 && y > lastScrollY) {
      header.classList.add('nav-hidden');
    } else {
      header.classList.remove('nav-hidden');
    }
    lastScrollY = y;
  }, { passive: true });
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
  if (!('IntersectionObserver' in window)) {
    els.forEach((el) => el.classList.add('visible'));
    return;
  }
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
  initHeaderScroll();
  initMobileNav();
  initActiveNav();
  initBackToTop();
  initScrollReveal();
  setupCopyButtons();
  initTabs();
});
