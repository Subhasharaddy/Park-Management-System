/* Six small animated Three.js scenes for the "common park issues" cards.
   Each renders only while visible on screen, so the page stays light. */
(function () {
  const holders = document.querySelectorAll('.issue-canvas[data-scene]');
  if (!holders.length) return;
  if (!window.THREE || !window.PC_WEBGL) { document.documentElement.classList.add('no-webgl'); return; }
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const M = (c, o = {}) => new THREE.MeshStandardMaterial(Object.assign({ color: c, roughness: .8, flatShading: true }, o));
  const box = (w, h, d, c, x = 0, y = 0, z = 0, o) => { const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), M(c, o)); m.position.set(x, y, z); return m; };
  const cyl = (rt, rb, h, c, x = 0, y = 0, z = 0, seg = 12, o) => { const m = new THREE.Mesh(new THREE.CylinderGeometry(rt, rb, h, seg), M(c, o)); m.position.set(x, y, z); return m; };
  const pointsOf = (n, color, size) => { const a = new Float32Array(n * 3), g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(a, 3));
    return { a, g, pts: new THREE.Points(g, new THREE.PointsMaterial({ color, size, transparent: true, opacity: .9, depthWrite: false })) }; };

  const scenes = {
    bench(root) {
      const wood = 0xb4743a, iron = 0x2c3a35;
      [-1, 1].forEach(s => { root.add(box(.12, .9, 1, iron, s * 1.1, .45, 0)); });
      root.add(box(2.5, .1, .35, wood, 0, .9, -.3), box(2.5, .1, .35, wood, 0, .9, .15));
      root.add(box(2.5, .12, .08, wood, 0, 1.45, -.5), box(2.5, .12, .08, wood, 0, 1.7, -.5));
      const loose = box(2.5, .1, .35, wood, 0, .95, .6); loose.rotation.x = .5; root.add(loose);           // broken plank hanging off
      const fallen = box(1.1, .1, .35, wood, 1.4, .08, 1.3); fallen.rotation.y = .6; root.add(fallen);
      const leg = root.children[1]; leg.rotation.z = -.22;                                                // bent leg
      const cone = cyl(.02, .3, .6, 0xff8a24, -1.9, .3, 1.2); root.add(cone);
      return t => { loose.rotation.x = .5 + Math.sin(t * 2) * .08; };
    },
    leak(root) {
      const horiz = cyl(.18, .18, 1.6, 0x7b8a86, 0, 1.6, 0); horiz.rotation.z = Math.PI / 2;
      root.add(cyl(.18, .18, 1.6, 0x7b8a86, -.8, .8, 0), horiz);
      root.add(cyl(.26, .26, .2, 0x4a5753, -.8, 1.6, 0));
      const puddle = new THREE.Mesh(new THREE.CircleGeometry(1, 32), new THREE.MeshStandardMaterial({ color: 0x00d9ff, transparent: true, opacity: .6, emissive: 0x00536b }));
      puddle.rotation.x = -Math.PI / 2; puddle.position.set(.3, .02, .5); root.add(puddle);
      const ring = new THREE.Mesh(new THREE.RingGeometry(.9, 1, 32), new THREE.MeshBasicMaterial({ color: 0x9ff3ff, transparent: true, side: THREE.DoubleSide }));
      ring.rotation.x = -Math.PI / 2; ring.position.copy(puddle.position); ring.position.y = .03; root.add(ring);
      const N = 70, d = pointsOf(N, 0x7fe9ff, .08); root.add(d.pts); const st = Array.from({ length: N }, () => ({ t: Math.random(), dx: Math.random() * .6, dz: (Math.random() - .5) * .3 }));
      return t => { st.forEach((s, i) => { s.t = (s.t + .012) % 1; d.a[i * 3] = -.8 + s.dx * s.t * 1.4; d.a[i * 3 + 1] = 1.5 - s.t * s.t * 1.5; d.a[i * 3 + 2] = s.dz * s.t; });
        d.g.attributes.position.needsUpdate = true; const k = .5 + ((t * .5) % 1) * .7; puddle.scale.setScalar(k); ring.scale.setScalar(k); ring.material.opacity = 1 - ((t * .5) % 1); };
    },
    path(root) {
      for (let x = -1; x <= 1; x++) for (let z = -1; z <= 1; z++) {
        if (x === 0 && z === 0) { root.add(box(.95, .5, .95, 0x1a1f1d, 0, -.05, 0)); continue; }              // missing tile -> hole
        const tile = box(.95, .18, .95, (x + z) % 2 ? 0x9a9588 : 0xaaa598, x, .09, z); if (x === 1 && z === 0) { tile.rotation.z = .25; tile.position.y = .2; } root.add(tile);
      }
      [[.5, .0], [-1, .4], [.9, -1]].forEach(([x, z], i) => { const c = box(.7, .02, .04, 0x2a2824, x, .2, z); c.rotation.y = .5 + i; root.add(c); });
      const sign = new THREE.Mesh(new THREE.ConeGeometry(.28, .6, 3), new THREE.MeshStandardMaterial({ color: 0xffd447, emissive: 0xff8a24, emissiveIntensity: .6 })); sign.position.set(-1.7, .3, 1.5); root.add(sign);
      return t => { sign.material.emissiveIntensity = .3 + Math.abs(Math.sin(t * 3)) * .9; };
    },
    bin(root) {
      root.add(cyl(.6, .5, 1.3, 0x1faa59, 0, .65, 0, 14));
      const lid = cyl(.65, .65, .12, 0x15803d, -.2, 1.5, 0, 14); lid.rotation.z = .5; root.add(lid);
      const junk = [0xff8a24, 0xffd447, 0xe8fff2, 0xff5c8a, 0x00d9ff, 0xb4743a].map((c, i) => { const m = box(.28, .28, .28, c, Math.cos(i * 1.2) * .5, 1.3 + (i % 3) * .2, Math.sin(i * 1.2) * .5); m.rotation.set(i, i * 2, 0); root.add(m); return m; });
      const spill = [0, 1, 2, 3].map(i => { const m = box(.24, .2, .24, [0xe8fff2, 0xff5c8a, 0xffd447, 0xb4743a][i], .8 + i * .3, .1, .5 + (i % 2) * .5); m.rotation.y = i; root.add(m); return m; });
      const f = pointsOf(8, 0x111111, .1); root.add(f.pts);
      return t => { junk.forEach((m, i) => { m.position.y = 1.35 + (i % 3) * .2 + Math.abs(Math.sin(t * 2 + i)) * .25; m.rotation.y += .01; });
        for (let i = 0; i < 8; i++) { f.a[i * 3] = Math.cos(t * 2 + i) * (.8 + i * .06); f.a[i * 3 + 1] = 1.8 + Math.sin(t * 3 + i) * .3; f.a[i * 3 + 2] = Math.sin(t * 2 + i) * (.8 + i * .06); } f.g.attributes.position.needsUpdate = true; };
    },
    light(root) {
      const pole = new THREE.Group(); pole.add(cyl(.09, .13, 3, 0x2c3a35, 0, 1.5, 0, 8)); pole.rotation.z = -.14; root.add(pole);
      const arm = box(.9, .08, .08, 0x2c3a35, .4, 3, 0); arm.rotation.z = .1; pole.add(arm);
      const head = new THREE.Group(); head.position.set(.85, 2.8, 0); pole.add(head);
      head.add(cyl(.05, .05, .5, 0x1c2723, 0, .25, 0, 6), box(.6, .14, .3, 0x2c3a35, 0, -.05, 0));
      const bulb = new THREE.Mesh(new THREE.SphereGeometry(.14, 12, 12), new THREE.MeshStandardMaterial({ color: 0xffd447, emissive: 0xffd447, emissiveIntensity: 1 })); bulb.position.y = -.2; head.add(bulb);
      const l = new THREE.PointLight(0xffd447, 1.2, 6); l.position.set(.85, 2.5, 0); root.add(l);
      const sp = pointsOf(24, 0xffb347, .07); root.add(sp.pts);
      return t => { const on = Math.sin(t * 9) * Math.sin(t * 3.3) > -.2; bulb.material.emissiveIntensity = on ? 1 : .05; l.intensity = on ? 1.2 : 0; head.rotation.z = Math.sin(t * 1.6) * .12;
        for (let i = 0; i < 24; i++) { const u = (t * .8 + i / 24) % 1; sp.a[i * 3] = 1.1 + Math.sin(i * 7) * .4 * u; sp.a[i * 3 + 1] = 2.5 - u * 2.4; sp.a[i * 3 + 2] = Math.cos(i * 5) * .4 * u; } sp.g.attributes.position.needsUpdate = true; };
    },
    play(root) {
      const metal = 0x3a8dde;
      [-1.3, 1.3].forEach(x => { const a = cyl(.06, .06, 2.4, metal, x - .3, 1.15, 0, 8), b = cyl(.06, .06, 2.4, metal, x + .3, 1.15, 0, 8); a.rotation.z = .25; b.rotation.z = -.25; root.add(a, b); });
      root.add(cyl(.06, .06, 2.9, 0xff8a24, 0, 2.25, 0, 8)); root.children[root.children.length - 1].rotation.z = Math.PI / 2;
      const swing = new THREE.Group(); swing.position.set(-.7, 2.25, 0); root.add(swing);
      swing.add(cyl(.015, .015, 1.5, 0xcccccc, -.25, -.75, 0, 4), cyl(.015, .015, 1.5, 0xcccccc, .25, -.75, 0, 4), box(.7, .06, .3, 0xff5c8a, 0, -1.5, 0));
      const broken = new THREE.Group(); broken.position.set(.7, 2.25, 0); root.add(broken);                         // one chain snapped
      const chain = cyl(.015, .015, 1.5, 0xcccccc, .25, -.75, 0, 4); broken.add(chain);
      const seat = box(.7, .06, .3, 0xff5c8a, 0, -1.5, 0); seat.position.set(-.1, -1.45, 0); seat.rotation.z = .75; broken.add(seat);
      const slide = box(.6, .08, 2, 0xffd447, -1.9, .7, 1.2); slide.rotation.x = -.5; slide.rotation.z = .15; root.add(slide);
      return t => { swing.rotation.z = Math.sin(t * 1.5) * .35; broken.rotation.z = Math.sin(t * 1.5 + 1) * .05; };
    },
  };

  holders.forEach(h => {
    const build = scenes[h.dataset.scene]; if (!build) return;
    let ready = false, visible = false, renderer, scene, camera, root, update, t = 0, tx = 0, ty = 0, rx = 0, ry = 0;
    function init() {
      let cv = document.createElement('canvas'); h.appendChild(cv);
      try { renderer = new THREE.WebGLRenderer({ canvas: cv, antialias: true, alpha: true }); } catch (e) { cv.remove(); h.classList.add('nofx'); document.documentElement.classList.add('no-webgl'); return; }
      renderer.setPixelRatio(Math.min(devicePixelRatio, 1.75));
      scene = new THREE.Scene(); camera = new THREE.PerspectiveCamera(42, 1, .1, 50); camera.position.set(3.6, 2.8, 4.6); camera.lookAt(0, 1, 0);
      scene.add(new THREE.HemisphereLight(0xb8ffe0, 0x0b3d2e, 1), Object.assign(new THREE.DirectionalLight(0xffffff, .9), { position: new THREE.Vector3(3, 6, 4) }));
      root = new THREE.Group(); scene.add(root);
      const floor = new THREE.Mesh(new THREE.CylinderGeometry(2.8, 2.8, .12, 40), M(0x0f5a35)); floor.position.y = -.06; root.add(floor);
      update = build(root);
      const fit = () => { const w = h.clientWidth, hh = h.clientHeight; renderer.setSize(w, hh, false); camera.aspect = w / hh; camera.updateProjectionMatrix(); };
      fit(); new ResizeObserver(fit).observe(h);
      h.addEventListener('pointermove', e => { const r = h.getBoundingClientRect(); ty = ((e.clientX - r.left) / r.width - .5) * 1.2; tx = ((e.clientY - r.top) / r.height - .5) * .4; });
      h.addEventListener('pointerleave', () => { tx = ty = 0; });
      ready = true; loop();
    }
    function loop() {
      if (!visible) return; requestAnimationFrame(loop);
      t += reduce ? 0 : .016; root.rotation.y += (reduce ? 0 : .004); rx += (tx - rx) * .08; ry += (ty - ry) * .08; root.rotation.x = rx; root.position.x = ry * .3;
      update(t); renderer.render(scene, camera);
    }
    new IntersectionObserver(es => { const v = es[0].isIntersecting; if (v && !visible) { visible = true; ready ? loop() : init(); } visible = v; }, { threshold: .1 }).observe(h);
  });
})();
