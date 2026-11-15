/* Admin / staff dashboards: Chart.js charts + real OpenStreetMap complaint map. */
(function () {
  const read = id => {
    const element = document.getElementById(id);
    return element ? JSON.parse(element.textContent) : null;
  };
  const COL = {
    Submitted: '#00D9FF',
    'Under Review': '#FFD447',
    Assigned: '#b58cff',
    'In Progress': '#FF8A24',
    Resolved: '#39FF88',
    Rejected: '#ff5c6c'
  };
  const points = read('mapData');
  const charts = read('chartData');

  if (charts && window.Chart) {
    Chart.defaults.color = '#9db3a8';
    Chart.defaults.borderColor = 'rgba(255,255,255,.08)';
    Chart.defaults.font.family = 'Poppins, sans-serif';
    const palette = ['#39FF88', '#00D9FF', '#FF8A24', '#FFD447', '#b58cff', '#ff5c8a', '#12c26a', '#7a4dff'];

    new Chart('chStatus', {
      type: 'doughnut',
      data: {
        labels: charts.status.labels,
        datasets: [{ data: charts.status.data, backgroundColor: charts.status.labels.map(label => COL[label]), borderWidth: 0 }]
      },
      options: { maintainAspectRatio: false, cutout: '62%', plugins: { legend: { position: 'bottom' } } }
    });

    new Chart('chCategory', {
      type: 'bar',
      data: { labels: charts.category.map(item => item.label), datasets: [{ data: charts.category.map(item => item.n), backgroundColor: palette, borderRadius: 8 }] },
      options: { maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } }
    });

    new Chart('chMonthly', {
      type: 'line',
      data: {
        labels: charts.monthly.labels,
        datasets: [
          { label: 'Reported', data: charts.monthly.reported, borderColor: '#00D9FF', backgroundColor: 'rgba(0,217,255,.15)', fill: true, tension: .35 },
          { label: 'Resolved', data: charts.monthly.resolved, borderColor: '#39FF88', backgroundColor: 'rgba(57,255,136,.12)', fill: true, tension: .35 }
        ]
      },
      options: { maintainAspectRatio: false, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } }
    });

    new Chart('chParks', {
      type: 'bar',
      data: { labels: charts.parks.map(item => item.label), datasets: [{ data: charts.parks.map(item => item.n), backgroundColor: '#FF8A24', borderRadius: 8 }] },
      options: { indexAxis: 'y', maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, ticks: { precision: 0 } } } }
    });
  }

  const mapElement = document.getElementById('adminMap');
  if (mapElement && window.L) {
    // The default is only a starting view when there are no complaint points.
    const map = L.map(mapElement, { preferCanvas: true }).setView([12.9716, 77.5946], 12);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a>'
    }).addTo(map);
    L.control.scale({ imperial: false, metric: true }).addTo(map);

    const escapeHtml = value => String(value).replace(/[&<>"']/g, character => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[character]));
    const bounds = [];

    (points || []).forEach(point => {
      const lat = Number(point.latitude);
      const lng = Number(point.longitude);
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;
      const location = [lat, lng];
      bounds.push(location);
      const detailUrl = window.POINT_URL
        ? window.POINT_URL(point)
        : (window.ADMIN_BASE + '/' + encodeURIComponent(point.id));
      const externalMapUrl = `https://www.openstreetmap.org/?mlat=${encodeURIComponent(lat)}&mlon=${encodeURIComponent(lng)}#map=18/${encodeURIComponent(lat)}/${encodeURIComponent(lng)}`;
      const popup = `<strong>${escapeHtml(point.complaint_code)}</strong><br>${escapeHtml(point.title)}<br>${escapeHtml(point.category)} - ${escapeHtml(point.status)}<br><a href="${escapeHtml(detailUrl)}">Open complaint</a> · <a href="${externalMapUrl}" target="_blank" rel="noopener">Open map</a>`;

      L.circleMarker(location, {
        radius: 9,
        color: '#000',
        weight: 1,
        fillColor: COL[point.status] || '#fff',
        fillOpacity: .95
      }).addTo(map).bindPopup(popup);
    });

    if (bounds.length === 1) {
      map.setView(bounds[0], 18);
    } else if (bounds.length > 1) {
      map.fitBounds(bounds, { padding: [30, 30], maxZoom: 17 });
    }
    window.setTimeout(() => map.invalidateSize(), 150);
  }
})();
