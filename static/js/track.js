/* Complaint tracking / staff / admin detail map using real OSM street tiles. */
(function () {
  const mapEl = document.getElementById('trackMap');
  if (mapEl && window.L) {
    const lat = Number(mapEl.dataset.lat);
    const lng = Number(mapEl.dataset.lng);
    if (Number.isFinite(lat) && Number.isFinite(lng)) {
      const position = [lat, lng];
      const map = L.map(mapEl, {
        scrollWheelZoom: false,
        preferCanvas: true
      }).setView(position, 18);

      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a>'
      }).addTo(map);
      L.control.scale({ imperial: false, metric: true }).addTo(map);

      const marker = L.marker(position).addTo(map);
      const popup = document.createElement('div');
      const title = document.createElement('strong');
      title.textContent = mapEl.dataset.title || 'Complaint location';
      const coordinates = document.createElement('div');
      coordinates.textContent = `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
      const openMap = document.createElement('a');
      openMap.href = `https://www.openstreetmap.org/?mlat=${encodeURIComponent(lat)}&mlon=${encodeURIComponent(lng)}#map=19/${encodeURIComponent(lat)}/${encodeURIComponent(lng)}`;
      openMap.target = '_blank';
      openMap.rel = 'noopener noreferrer';
      openMap.textContent = 'Open larger map';
      popup.append(title, document.createElement('br'), coordinates, document.createElement('br'), openMap);
      marker.bindPopup(popup).openPopup();
      window.setTimeout(() => map.invalidateSize(), 150);
    }
  }

  // Existing live status refresh retained.
  const card = document.getElementById('trackCard');
  if (card) {
    window.setInterval(async () => {
      if (document.hidden) return;
      try {
        const response = await fetch('/api/track/' + encodeURIComponent(card.dataset.code));
        if (response.ok && (await response.json()).status !== card.dataset.status) {
          window.location.reload();
        }
      } catch (error) {
        // Keep the page usable if the network is temporarily unavailable.
      }
    }, 20000);
  }
})();
