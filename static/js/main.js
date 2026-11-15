/* ParkCare 3D - shared behaviour: loader, nav, flashes, network background, counters, GSAP, validation */
(function () {
  'use strict';
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ---- WebGL detection (3D scenes read window.PC_WEBGL; CSS shows static fallbacks otherwise)
  window.PC_WEBGL = (function () {
    try {
      const c = document.createElement('canvas');
      return !!(window.WebGLRenderingContext && (c.getContext('webgl') || c.getContext('experimental-webgl')));
    } catch (e) { return false; }
  })();
  if (!window.PC_WEBGL) document.documentElement.classList.add('no-webgl');

  // ---- toast helper
  window.pcToast = function (msg, type) {
    const box = document.getElementById('flashes');
    const d = document.createElement('div');
    d.className = 'flash ' + (type || 'danger'); d.setAttribute('role', 'alert');
    const s = document.createElement('span'); s.textContent = msg;
    const b = document.createElement('button'); b.type = 'button'; b.innerHTML = '&times;';
    d.append(s, b); box.appendChild(d); wireFlash(d);
  };
  function wireFlash(el) {
    const kill = () => el.remove();
    el.querySelector('button').addEventListener('click', kill);
    setTimeout(kill, 8000);
  }
  document.querySelectorAll('.flash').forEach(wireFlash);

  // ---- loader
  const hideLoader = () => { const l = document.getElementById('loader'); if (l) l.classList.add('done'); };
  window.addEventListener('load', () => setTimeout(hideLoader, 450));
  setTimeout(hideLoader, 4000); // never block the page if a CDN is slow

  // ---- nav
  const nav = document.getElementById('nav');
  const onScroll = () => nav.classList.toggle('scrolled', window.scrollY > 30);
  onScroll(); window.addEventListener('scroll', onScroll, { passive: true });
  const links = document.getElementById('navLinks');
  document.getElementById('navToggle').addEventListener('click', () => links.classList.toggle('open'));
  links.querySelectorAll('a').forEach(a => a.addEventListener('click', () => links.classList.remove('open')));

  // ---- animated network background (cheap 2D canvas)
  (function network() {
    const cv = document.getElementById('bg-canvas'); if (!cv || reduce) return;
    const ctx = cv.getContext('2d'); let w, h, pts = [], raf;
    const colors = ['57,255,136', '255,138,36', '0,217,255'];
    function size() {
      w = cv.width = innerWidth; h = cv.height = innerHeight;
      const n = Math.min(70, Math.floor(w * h / 26000));
      pts = Array.from({ length: n }, () => ({ x: Math.random() * w, y: Math.random() * h, vx: (Math.random() - .5) * .35, vy: (Math.random() - .5) * .35, c: colors[(Math.random() * 3) | 0] }));
    }
    function draw() {
      ctx.clearRect(0, 0, w, h);
      for (let i = 0; i < pts.length; i++) {
        const p = pts[i]; p.x += p.vx; p.y += p.vy;
        if (p.x < 0 || p.x > w) p.vx *= -1; if (p.y < 0 || p.y > h) p.vy *= -1;
        ctx.fillStyle = `rgba(${p.c},.9)`; ctx.beginPath(); ctx.arc(p.x, p.y, 1.8, 0, 6.28); ctx.fill();
        for (let j = i + 1; j < pts.length; j++) {
          const q = pts[j], d = Math.hypot(p.x - q.x, p.y - q.y);
          if (d < 130) { ctx.strokeStyle = `rgba(${p.c},${(1 - d / 130) * .35})`; ctx.lineWidth = .7; ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y); ctx.stroke(); }
        }
      }
      raf = requestAnimationFrame(draw);
    }
    size(); draw(); addEventListener('resize', size);
    document.addEventListener('visibilitychange', () => { cancelAnimationFrame(raf); if (!document.hidden) draw(); });
  })();

  // ---- animated counters
  const counters = document.querySelectorAll('[data-count]');
  if (counters.length) {
    const io = new IntersectionObserver(es => es.forEach(e => {
      if (!e.isIntersecting) return; io.unobserve(e.target);
      const el = e.target, end = +el.dataset.count, t0 = performance.now(), dur = reduce ? 1 : 1600;
      (function tick(t) { const p = Math.min((t - t0) / dur, 1); el.textContent = Math.round(end * (1 - Math.pow(1 - p, 3))).toLocaleString(); if (p < 1) requestAnimationFrame(tick); })(t0);
    }), { threshold: .4 });
    counters.forEach(c => io.observe(c));
  }

  // ---- GSAP scroll / entrance animations
  window.addEventListener('load', () => {
    if (!window.gsap || reduce) return;
    if (window.ScrollTrigger) gsap.registerPlugin(ScrollTrigger);
    const title = document.getElementById('heroTitle');
    if (title) {
      title.innerHTML = title.innerHTML.replace(/(<[^>]+>)|([^<\s]+)/g, (m, tag, word) => tag ? tag : `<span class="w">${word}</span>`);
      gsap.from('#heroTitle .w', { y: 60, opacity: 0, duration: .9, stagger: .08, ease: 'power3.out', delay: .5 });
      gsap.from('.hero [data-anim]', { y: 30, opacity: 0, duration: .8, stagger: .15, delay: 1, ease: 'power2.out' });
    }
    if (window.ScrollTrigger) {
      document.querySelectorAll('main [data-anim]:not(.hero [data-anim])').forEach(el =>
        gsap.from(el, { y: 50, opacity: 0, duration: .8, ease: 'power2.out', scrollTrigger: { trigger: el, start: 'top 88%', once: true } }));
      const steps = document.getElementById('steps');
      if (steps) {
        gsap.from('#steps .step', { y: 40, opacity: 0, stagger: .2, duration: .7, scrollTrigger: { trigger: steps, start: 'top 80%', once: true } });
      }
    }
  });

  // ---- 3D tilt on cards
  if (!reduce && matchMedia('(hover:hover)').matches) {
    document.querySelectorAll('.tilt').forEach(el => {
      el.addEventListener('mousemove', e => {
        const r = el.getBoundingClientRect(), x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5;
        el.style.transform = `perspective(800px) rotateY(${x * 12}deg) rotateX(${-y * 12}deg) translateZ(6px)`;
      });
      el.addEventListener('mouseleave', () => { el.style.transform = ''; });
    });
  }

  // ---- client-side form validation (the server validates again)
  document.querySelectorAll('form[data-validate]').forEach(f => f.addEventListener('submit', e => {
    const pw = f.querySelector('[name=password]'), cf = f.querySelector('[name=confirm_password]');
    if (pw && cf && pw.value !== cf.value) { e.preventDefault(); pcToast('Passwords do not match.'); return; }
    if (!f.checkValidity()) {
      e.preventDefault();
      const bad = f.querySelector(':invalid'); pcToast(bad.validationMessage || 'Please complete the required fields.', 'warning'); bad.focus();
    }
  }));
})();
