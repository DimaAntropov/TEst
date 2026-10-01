(() => {
  'use strict';

  const root = document.documentElement;
  const storage = {
    get(key, fallback) { try { return localStorage.getItem(key) || fallback; } catch { return fallback; } },
    set(key, value) { try { localStorage.setItem(key, value); } catch {} }
  };

  // Theme and accent manager
  const media = matchMedia('(prefers-color-scheme: dark)');
  const themeButton = document.querySelector('#theme-button');
  const themePopover = document.querySelector('#theme-popover');
  const themeIcon = document.querySelector('#theme-icon');
  const themeMeta = document.querySelector('meta[name="theme-color"]');

  function resolvedTheme(preference) {
    return preference === 'system' ? (media.matches ? 'dark' : 'light') : preference;
  }

  function applyTheme(preference, persist = true) {
    const theme = resolvedTheme(preference);
    root.dataset.theme = theme;
    root.dataset.themePreference = preference;
    if (persist) storage.set('cinema-theme', preference);
    if (themeIcon) themeIcon.textContent = theme === 'dark' ? '☾' : '☀';
    if (themeMeta) themeMeta.content = theme === 'dark' ? '#0d1018' : '#111522';
    document.querySelectorAll('[data-theme-value]').forEach(button => {
      button.classList.toggle('active', button.dataset.themeValue === preference);
      button.setAttribute('aria-pressed', button.dataset.themeValue === preference ? 'true' : 'false');
    });
  }

  function applyAccent(accent) {
    root.dataset.accent = accent;
    storage.set('cinema-accent', accent);
    document.querySelectorAll('[data-accent-value]').forEach(button => {
      button.classList.toggle('active', button.dataset.accentValue === accent);
      button.setAttribute('aria-pressed', button.dataset.accentValue === accent ? 'true' : 'false');
    });
  }

  applyTheme(storage.get('cinema-theme', 'system'), false);
  applyAccent(storage.get('cinema-accent', 'violet'));
  media.addEventListener?.('change', () => {
    if (storage.get('cinema-theme', 'system') === 'system') applyTheme('system', false);
  });

  themeButton?.addEventListener('click', event => {
    event.stopPropagation();
    const opening = themePopover.hidden;
    themePopover.hidden = !opening;
    themeButton.setAttribute('aria-expanded', opening ? 'true' : 'false');
  });
  document.querySelectorAll('[data-theme-value]').forEach(button => {
    button.addEventListener('click', () => applyTheme(button.dataset.themeValue));
  });
  document.querySelectorAll('[data-accent-value]').forEach(button => {
    button.addEventListener('click', () => applyAccent(button.dataset.accentValue));
  });
  document.addEventListener('click', event => {
    if (themePopover && !themePopover.contains(event.target) && event.target !== themeButton) {
      themePopover.hidden = true;
      themeButton?.setAttribute('aria-expanded', 'false');
    }
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && themePopover) {
      themePopover.hidden = true;
      themeButton?.setAttribute('aria-expanded', 'false');
    }
  });

  // Mobile navigation
  const mobileButton = document.querySelector('.mobile-menu');
  const mainNav = document.querySelector('#main-nav');
  mobileButton?.addEventListener('click', () => {
    const opened = mainNav.classList.toggle('open');
    mobileButton.setAttribute('aria-expanded', opened ? 'true' : 'false');
    mobileButton.textContent = opened ? '×' : '☰';
  });

  // Flash messages
  document.querySelectorAll('.alert').forEach((alert, index) => {
    alert.style.setProperty('--delay', `${index * 70}ms`);
    const close = () => {
      alert.classList.add('leaving');
      setTimeout(() => alert.remove(), 220);
    };
    alert.querySelector('.alert-close')?.addEventListener('click', close);
    if (alert.classList.contains('success') || alert.classList.contains('info')) {
      setTimeout(close, 6000);
    }
  });

  // Interactive seat selection
  const seatForm = document.querySelector('#seat-form');
  if (seatForm) {
    const price = Number(seatForm.dataset.price || 0);
    const boxes = [...seatForm.querySelectorAll('.seat input:not(:disabled)')];
    const count = document.querySelector('#seat-count');
    const total = document.querySelector('#total');
    const names = document.querySelector('#seat-names');
    const submit = document.querySelector('#book-button');

    const renderSeats = () => {
      const selected = boxes.filter(box => box.checked);
      count.textContent = selected.length;
      total.textContent = new Intl.NumberFormat('ru-RU').format(selected.length * price);
      names.textContent = selected.length
        ? selected.slice(0, 3).map(box => box.dataset.label).join(' · ') + (selected.length > 3 ? ` · ещё ${selected.length - 3}` : '')
        : 'Места не выбраны';
      submit.disabled = selected.length === 0 || selected.length > 10;
      submit.title = selected.length > 10 ? 'Можно выбрать не более 10 мест' : '';
    };
    boxes.forEach(box => box.addEventListener('change', renderSeats));
    renderSeats();
  }

  // Password visibility toggles
  document.querySelectorAll('input[type="password"]').forEach(input => {
    const wrapper = document.createElement('span');
    wrapper.className = 'password-control';
    input.parentNode.insertBefore(wrapper, input);
    wrapper.appendChild(input);
    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'password-toggle';
    toggle.setAttribute('aria-label', 'Показать пароль');
    toggle.textContent = '👁';
    wrapper.appendChild(toggle);
    toggle.addEventListener('click', () => {
      const visible = input.type === 'text';
      input.type = visible ? 'password' : 'text';
      toggle.classList.toggle('active', !visible);
      toggle.setAttribute('aria-label', visible ? 'Показать пароль' : 'Скрыть пароль');
    });
  });

  // Loading feedback for submitted forms
  document.querySelectorAll('form[method="post"]').forEach(form => {
    form.addEventListener('submit', event => {
      if (!form.checkValidity()) return;
      const submitter = event.submitter;
      if (submitter && !submitter.classList.contains('link-button') && !submitter.classList.contains('text-danger')) {
        submitter.classList.add('loading');
        const original = submitter.innerHTML;
        submitter.dataset.original = original;
        submitter.innerHTML = '<span class="spinner"></span><span>Подождите</span>';
      }
    });
  });

  // Progressive card reveal
  const revealItems = document.querySelectorAll('.movie-card,.ticket,.panel,.stats>a,.stats>div');
  if ('IntersectionObserver' in window && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('revealed');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.06 });
    revealItems.forEach((item, index) => {
      item.classList.add('reveal');
      item.style.setProperty('--reveal-delay', `${Math.min(index, 8) * 35}ms`);
      observer.observe(item);
    });
  }

  // Back to top
  const toTop = document.querySelector('#to-top');
  const updateTopButton = () => toTop?.classList.toggle('visible', scrollY > 500);
  addEventListener('scroll', updateTopButton, { passive: true });
  toTop?.addEventListener('click', () => scrollTo({ top: 0, behavior: 'smooth' }));
  updateTopButton();

  // Prevent selecting dates before today for new sessions.
  document.querySelectorAll('input[type="datetime-local"][name="start_time"]:not([value])').forEach(input => {
    const now = new Date(Date.now() - new Date().getTimezoneOffset() * 60000);
    input.min = now.toISOString().slice(0, 16);
  });
})();
