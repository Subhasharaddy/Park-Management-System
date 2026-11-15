/* ParkCare 3D - hero: procedural 3D park (trees, fountain, path, benches, flowers, butterflies, birds, fireflies).
   All geometry is generated in code - no external model files needed. */
(function () {
  const canvas = document.getElementById('hero-canvas');
  if (!canvas) return;
  if (!window.THREE || !window.PC_WEBGL) { document.documentElement.classList.add('no-webgl'); return; }
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const small = innerWidth < 700;
  let renderer;
  try { renderer = new THREE.WebGLRenderer({ canvas, antialias: !small, alpha: true, powerPreference: 'high-performance' }); }
  catch (e) { document.documentElement.classList.add('no-webgl'); return; }
  renderer.setPixelRatio(Math.min(devicePixelRatio, small ? 1.25 : 1.75));
  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x07120d, 0.028);
  const camera = new THREE.PerspectiveCamera(55, 1, .1, 150);

  // seeded random so the park looks the same every visit
  let seed = 11; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const M = (c, o = {}) => new THREE.MeshStandardMaterial(Object.assign({ color: c, roughness: .85, flatShading: true }, o));

  // lights
  scene.add(new THREE.HemisphereLight(0x9fffd0, 0x0b3d2e, .8));
  const sun = new THREE.DirectionalLight(0xffe2b0, .9); sun.position.set(-8, 14, 6); scene.add(sun);
  const glow = new THREE.PointLight(0x39ff88, 1.4, 22); glow.position.set(0, 3, 0); scene.add(glow);

  // ground
  const ground = new THREE.Mesh(new THREE.CircleGeometry(48, 48), M(0x0f5a35));
  ground.rotation.x = -Math.PI / 2; scene.add(ground);

  // path: closed ring around the fountain, built as a flat ribbon
  const curve = new THREE.CatmullRomCurve3([[8, 0, 0], [6, 0, 6.5], [-1, 0, 9], [-8, 0, 4], [-9, 0, -4], [-3, 0, -9], [5, 0, -7]].map(p => new THREE.Vector3(...p)), true);
  const pathPts = curve.getPoints(120);
  (function ribbon() {
    const pos = [], idx = [], w = 1.1;
    pathPts.forEach((p, i) => {
      const n = pathPts[(i + 1) % pathPts.length], t = new THREE.Vector3().subVectors(n, p).normalize(), s = new THREE.Vector3(-t.z, 0, t.x).multiplyScalar(w);
      pos.push(p.x - s.x, .03, p.z - s.z, p.x + s.x, .03, p.z + s.z);
      const k = i * 2, m = ((i + 1) % pathPts.length) * 2; idx.push(k, k + 1, m, k + 1, m + 1, m);
    });
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setIndex(idx); g.computeVertexNormals();
    scene.add(new THREE.Mesh(g, M(0xc9b48a, { side: THREE.DoubleSide, emissive: 0x2a2010 })));
  })();
  const nearPath = (x, z, d) => pathPts.some(p => Math.hypot(p.x - x, p.z - z) < d) || Math.hypot(x, z) < 3.4;

  // grass blades (instanced)
  (function grass() {
    const n = small ? 700 : 1800, m = new THREE.InstancedMesh(new THREE.ConeGeometry(.07, .55, 3), M(0x2ecc71), n), d = new THREE.Object3D();
    for (let i = 0, c = 0; c < n && i < n * 4; i++) {
      const a = rnd() * 6.283, r = 3 + rnd() * 30, x = Math.cos(a) * r, z = Math.sin(a) * r; if (nearPath(x, z, 1.5)) continue;
      d.position.set(x, .25, z); d.rotation.set((rnd() - .5) * .4, rnd() * 6, (rnd() - .5) * .4); d.scale.setScalar(.6 + rnd()); d.updateMatrix(); m.setMatrixAt(c++, d.matrix);
    }
    scene.add(m);
  })();

  // trees
  function tree(x, z, s) {
    const g = new THREE.Group(), cols = [0x1faa59, 0x17a34a, 0x2ecc71, 0x0e8a3e];
    const trunk = new THREE.Mesh(new THREE.CylinderGeometry(.18 * s, .28 * s, 1.6 * s, 6), M(0x6b4423)); trunk.position.y = .8 * s; g.add(trunk);
    for (let i = 0; i < 3; i++) { const c = new THREE.Mesh(new THREE.ConeGeometry((1.5 - i * .3) * s, 1.8 * s, 7), M(cols[(rnd() * 4) | 0])); c.position.y = (2 + i * .95) * s; g.add(c); }
    g.position.set(x, 0, z); g.userData.sway = rnd() * 6; scene.add(g); return g;
  }
  const trees = [];
  for (let i = 0, n = small ? 22 : 40; i < n * 5 && trees.length < n; i++) {
    const a = rnd() * 6.283, r = 6 + rnd() * 26, x = Math.cos(a) * r, z = Math.sin(a) * r; if (nearPath(x, z, 2.6)) continue;
    trees.push(tree(x, z, .8 + rnd() * .9));
  }

  // fountain
  const fountain = new THREE.Group(); scene.add(fountain);
  const stone = M(0x9aa5a0, { roughness: .6 });
  fountain.add(Object.assign(new THREE.Mesh(new THREE.CylinderGeometry(2.4, 2.6, .6, 24), stone), { position: new THREE.Vector3(0, .3, 0) }));
  const water = new THREE.Mesh(new THREE.CylinderGeometry(2.15, 2.15, .08, 24), new THREE.MeshStandardMaterial({ color: 0x00d9ff, emissive: 0x00536b, transparent: true, opacity: .8, roughness: .1 }));
  water.position.y = .58; fountain.add(water);
  const pillar = new THREE.Mesh(new THREE.CylinderGeometry(.25, .4, 1.8, 10), stone); pillar.position.y = 1.4; fountain.add(pillar);
  const bowl = new THREE.Mesh(new THREE.CylinderGeometry(1.0, .5, .35, 16), stone); bowl.position.y = 2.3; fountain.add(bowl);
  const N = small ? 160 : 360, wp = new Float32Array(N * 3), wd = Array.from({ length: N }, () => ({ a: rnd() * 6.283, v: 2.4 + rnd() * 1.4, h: 3 + rnd() * 1.5, t: rnd() * 3 }));
  const wg = new THREE.BufferGeometry(); wg.setAttribute('position', new THREE.BufferAttribute(wp, 3));
  const spray = new THREE.Points(wg, new THREE.PointsMaterial({ color: 0x9ff3ff, size: .1, transparent: true, opacity: .9, blending: THREE.AdditiveBlending, depthWrite: false }));
  spray.position.y = 2.4; fountain.add(spray);

  // benches facing the fountain
  function bench(angle) {
    const g = new THREE.Group(), wood = M(0xb4743a), iron = M(0x2c3a35);
    const seat = new THREE.Mesh(new THREE.BoxGeometry(1.8, .1, .55), wood); seat.position.y = .55; g.add(seat);
    const back = new THREE.Mesh(new THREE.BoxGeometry(1.8, .45, .08), wood); back.position.set(0, .95, .25); back.rotation.x = -.15; g.add(back);
    [-.75, .75].forEach(x => { const l = new THREE.Mesh(new THREE.BoxGeometry(.08, .55, .5), iron); l.position.set(x, .27, 0); g.add(l); });
    const r = 5.6; g.position.set(Math.cos(angle) * r, 0, Math.sin(angle) * r); g.lookAt(0, 0, 0); g.rotateY(Math.PI); scene.add(g);
  }
  [.5, 2.2, 3.7, 5.3].forEach(bench);

  // lamp posts
  [1.2, 3.1, 4.6].forEach(a => {
    const g = new THREE.Group(), pole = new THREE.Mesh(new THREE.CylinderGeometry(.05, .07, 2.6, 6), M(0x1c2723)); pole.position.y = 1.3; g.add(pole);
    const bulb = new THREE.Mesh(new THREE.SphereGeometry(.18, 12, 12), new THREE.MeshBasicMaterial({ color: 0xffd447 })); bulb.position.y = 2.7; g.add(bulb);
    const l = new THREE.PointLight(0xffc766, .9, 7); l.position.y = 2.6; g.add(l);
    g.position.set(Math.cos(a) * 7.2, 0, Math.sin(a) * 7.2); scene.add(g);
  });

  // flowers (instanced, per-instance colour)
  (function flowers() {
    const n = small ? 90 : 220, m = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(.13, 0), M(0xffffff), n), d = new THREE.Object3D();
    const pal = [0xff8a24, 0xffd447, 0xff5c8a, 0x00d9ff, 0xffffff, 0xb58cff];
    for (let i = 0, c = 0; c < n && i < n * 6; i++) {
      const a = rnd() * 6.283, r = 3.5 + rnd() * 20, x = Math.cos(a) * r, z = Math.sin(a) * r; if (nearPath(x, z, 1.7)) continue;
      d.position.set(x, .3 + rnd() * .2, z); d.scale.setScalar(.8 + rnd() * .8); d.updateMatrix(); m.setMatrixAt(c, d.matrix); m.setColorAt(c, new THREE.Color(pal[(rnd() * pal.length) | 0])); c++;
    }
    scene.add(m);
  })();

  // butterflies
  const flies = [0xff8a24, 0xffd447, 0x00d9ff, 0xff5c8a, 0x39ff88, 0xb58cff].map((c, i) => {
    const g = new THREE.Group(), mat = new THREE.MeshBasicMaterial({ color: c, side: THREE.DoubleSide });
    const mk = s => { const w = new THREE.Mesh(new THREE.PlaneGeometry(.32, .22), mat); w.position.x = s * .16; const p = new THREE.Group(); p.add(w); p.rotation.y = 0; return p; };
    const L = mk(-1), R = mk(1); g.add(L, R); g.userData = { L, R, o: i * 1.3, r: 3 + i * 1.4 }; scene.add(g); return g;
  });
  // birds
  const birds = Array.from({ length: 5 }, (_, i) => {
    const g = new THREE.Group(), mat = new THREE.MeshBasicMaterial({ color: 0xe8fff2, side: THREE.DoubleSide });
    const wing = s => { const p = new THREE.Mesh(new THREE.PlaneGeometry(.55, .14), mat); p.position.x = s * .27; const h = new THREE.Group(); h.add(p); return h; };
    const L = wing(-1), R = wing(1); g.add(L, R); g.userData = { L, R, o: i * 1.25, r: 12 + i * 2.5, y: 7 + i * .7 }; scene.add(g); return g;
  });
  // fireflies
  const FN = small ? 70 : 160, fp = new Float32Array(FN * 3), fs = [];
  for (let i = 0; i < FN; i++) { fs.push({ x: (rnd() - .5) * 40, y: .5 + rnd() * 5, z: (rnd() - .5) * 40, o: rnd() * 6 }); }
  const fg = new THREE.BufferGeometry(); fg.setAttribute('position', new THREE.BufferAttribute(fp, 3));
  scene.add(new THREE.Points(fg, new THREE.PointsMaterial({ color: 0xc8ff5a, size: .16, transparent: true, opacity: .9, blending: THREE.AdditiveBlending, depthWrite: false })));

  // sizing / interaction
  const hero = canvas.parentElement;
  function resize() { const w = hero.clientWidth, h = hero.clientHeight; renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); }
  resize(); new ResizeObserver(resize).observe(hero);
  let mx = 0, my = 0; addEventListener('pointermove', e => { mx = e.clientX / innerWidth - .5; my = e.clientY / innerHeight - .5; }, { passive: true });
  let visible = true; new IntersectionObserver(es => { visible = es[0].isIntersecting; }).observe(hero);

  const clock = new THREE.Clock(); let t = 0;
  (function loop() {
    requestAnimationFrame(loop);
    if (!visible || document.hidden) return;
    const dt = Math.min(clock.getDelta(), .05); t += reduce ? 0 : dt;
    // camera: slow orbit + mouse parallax + scroll lift
    const ang = t * .06, rad = 15 + Math.min(scrollY / 120, 4), py = 5.2 + scrollY * .006;
    camera.position.set(Math.cos(ang) * rad + mx * 1.6, py - my * 1.2, Math.sin(ang) * rad);
    camera.lookAt(-2.2, 1.4, 0);
    // fountain spray
    for (let i = 0; i < N; i++) { const p = wd[i]; p.t += dt * .7; if (p.t > 1) p.t = 0; const u = p.t, r = p.v * u * .55, y = p.h * (4 * u * (1 - u));
      wp[i * 3] = Math.cos(p.a) * r; wp[i * 3 + 1] = y; wp[i * 3 + 2] = Math.sin(p.a) * r; }
    wg.attributes.position.needsUpdate = true; water.rotation.y = t * .3;
    trees.forEach(g => { g.rotation.z = Math.sin(t * .9 + g.userData.sway) * .012; });
    flies.forEach(f => { const u = f.userData, a = t * .5 + u.o; f.position.set(Math.cos(a) * u.r, 1.2 + Math.sin(t * 1.3 + u.o) * .5, Math.sin(a * 1.2) * u.r);
      f.rotation.y = -a; const fl = Math.sin(t * 14 + u.o) * .9; u.L.rotation.z = fl; u.R.rotation.z = -fl; });
    birds.forEach(b => { const u = b.userData, a = -t * .22 + u.o; b.position.set(Math.cos(a) * u.r, u.y + Math.sin(t + u.o), Math.sin(a) * u.r);
      b.rotation.y = -a + Math.PI; const fl = Math.sin(t * 7 + u.o) * .6; u.L.rotation.z = fl; u.R.rotation.z = -fl; });
    for (let i = 0; i < FN; i++) { const f = fs[i]; fp[i * 3] = f.x + Math.sin(t * .4 + f.o) * 1.2; fp[i * 3 + 1] = f.y + Math.sin(t * .8 + f.o) * .4; fp[i * 3 + 2] = f.z + Math.cos(t * .35 + f.o) * 1.2; }
    fg.attributes.position.needsUpdate = true;
    glow.intensity = 1.2 + Math.sin(t * 2) * .25;
    renderer.render(scene, camera);
  })();
})();
