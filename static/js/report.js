/* Park Management System - improved complaint location picker.
   Uses Leaflet + OpenStreetMap, device GPS, an accuracy radius,
   draggable marker, map-click selection, and one-shot place search. */
(function () {
  const $ = id => document.getElementById(id);
  const mapEl = $('map');
  const latI = $('latitude');
  const lngI = $('longitude');
  const msg = $('gpsMsg');
  const gpsBtn = $('gpsBtn');
  const form = $('reportForm');

  if (!mapEl || !latI || !lngI || !window.L) return;

  const startLat = Number(mapEl.dataset.lat);
  const startLng = Number(mapEl.dataset.lng);
  const validStart = Number.isFinite(startLat) && Number.isFinite(startLng);
  const haveSavedPoint = latI.value.trim() !== '' && lngI.value.trim() !== '';
  const initial = haveSavedPoint
    ? [Number(latI.value), Number(lngI.value)]
    : (validStart ? [startLat, startLng] : [12.9716, 77.5946]);

  const map = L.map(mapEl, {
    scrollWheelZoom: true,
    zoomControl: true,
    preferCanvas: true
  }).setView(initial, haveSavedPoint ? 18 : 15);

  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a>'
  }).addTo(map);

  L.control.scale({ imperial: false, metric: true }).addTo(map);

  let marker = null;
  let accuracyCircle = null;
  let gpsWatchId = null;
  let gpsDeadline = null;
  let bestAccuracy = Infinity;
  let bestGpsPoint = null;

  function setMessage(text) {
    if (msg) msg.textContent = text;
  }

  function setPoint(lat, lng, options = {}) {
    const latitude = Number(lat);
    const longitude = Number(lng);
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude) ||
        latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) {
      setMessage('That location is not valid. Choose another point on the map.');
      return;
    }

    latI.value = latitude.toFixed(7);
    lngI.value = longitude.toFixed(7);

    if (!marker) {
      marker = L.marker([latitude, longitude], {
        draggable: true,
        title: 'Complaint location'
      }).addTo(map);
      marker.on('dragend', () => {
        const p = marker.getLatLng();
        setPoint(p.lat, p.lng, { source: 'manual', pan: false });
        setMessage('Pin adjusted manually. The selected coordinates will be submitted.');
      });
    } else {
      marker.setLatLng([latitude, longitude]);
    }

    if (Number.isFinite(options.accuracy) && options.accuracy > 0) {
      if (accuracyCircle) accuracyCircle.remove();
      const radius = Math.max(1, options.accuracy);
      const good = radius <= 20;
      const fair = radius <= 75;
      const circleColor = good ? '#39ff88' : (fair ? '#ffd447' : '#ff8a24');
      accuracyCircle = L.circle([latitude, longitude], {
        radius,
        color: circleColor,
        weight: 2,
        fillColor: circleColor,
        fillOpacity: 0.13,
        interactive: false
      }).addTo(map);
    } else if (accuracyCircle) {
      accuracyCircle.remove();
      accuracyCircle = null;
    }

    if (options.pan) {
      map.setView([latitude, longitude], Math.max(map.getZoom(), 18));
    }
  }

  if (haveSavedPoint) {
    const savedLat = Number(latI.value);
    const savedLng = Number(lngI.value);
    if (Number.isFinite(savedLat) && Number.isFinite(savedLng)) {
      setPoint(savedLat, savedLng);
    }
  }

  map.on('click', event => {
    stopGpsWatch();
    setPoint(event.latlng.lat, event.latlng.lng);
    setMessage('Location selected from the street map. Drag the pin to fine-tune it.');
  });

  function stopGpsWatch() {
    if (gpsWatchId !== null && navigator.geolocation) {
      navigator.geolocation.clearWatch(gpsWatchId);
    }
    gpsWatchId = null;
    if (gpsDeadline !== null) window.clearTimeout(gpsDeadline);
    gpsDeadline = null;
    if (gpsBtn) gpsBtn.disabled = false;
  }

  function finishGps() {
    stopGpsWatch();
    if (bestGpsPoint) {
      const accuracy = Math.round(bestAccuracy);
      setPoint(bestGpsPoint.latitude, bestGpsPoint.longitude, {
        pan: true,
        accuracy: bestAccuracy
      });
      if (accuracy <= 20) {
        setMessage(`GPS fix acquired (device-reported accuracy about ±${accuracy} m). Drag the pin if needed.`);
      } else if (accuracy <= 75) {
        setMessage(`GPS fix acquired (about ±${accuracy} m). The yellow circle shows the estimated accuracy area. Move outdoors or adjust the pin for better precision.`);
      } else {
        setMessage(`GPS is approximate (about ±${accuracy} m). The orange circle shows the reported accuracy area. Try outdoors or place the pin manually.`);
      }
    } else {
      setMessage('Could not obtain a GPS fix. Search for the place or click the map to set the location.');
    }
  }

  function startGps() {
    if (!navigator.geolocation) {
      setMessage('This browser does not provide GPS. Search for the place or click the map instead.');
      return;
    }

    stopGpsWatch();
    bestAccuracy = Infinity;
    bestGpsPoint = null;
    if (gpsBtn) gpsBtn.disabled = true;
    setMessage('Getting GPS position… Keep the page open while the phone finds a more accurate reading.');

    // watchPosition can deliver improving fixes; getCurrentPosition may return
    // an early coarse Wi-Fi/IP estimate before a device GPS fix is ready.
    gpsWatchId = navigator.geolocation.watchPosition(position => {
      const accuracy = Number(position.coords.accuracy);
      const latitude = Number(position.coords.latitude);
      const longitude = Number(position.coords.longitude);
      if (!Number.isFinite(accuracy) || accuracy <= 0 ||
          !Number.isFinite(latitude) || !Number.isFinite(longitude)) return;

      if (accuracy < bestAccuracy) {
        bestAccuracy = accuracy;
        bestGpsPoint = { latitude, longitude };
        setPoint(latitude, longitude, { pan: true, accuracy });
        setMessage(`Improving GPS fix… device currently reports about ±${Math.round(accuracy)} m accuracy. You can drag the pin to adjust.`);
      }

      // Stop early when the device reports a reasonably precise fix.
      if (accuracy <= 20) finishGps();
    }, error => {
      const detail = error.code === 1
        ? 'Location permission was denied.'
        : error.code === 2
          ? 'Your device could not determine its location.'
          : 'The GPS request timed out.';
      stopGpsWatch();
      if (bestGpsPoint) finishGps();
      else setMessage(`${detail} Search for the place or click the map to choose the location.`);
    }, {
      enableHighAccuracy: true,
      maximumAge: 0,
      timeout: 30000
    });

    // Keep the best reading received during this window, even if accuracy
    // does not reach the 20 m early-stop target.
    gpsDeadline = window.setTimeout(finishGps, 30000);
  }

  if (gpsBtn) gpsBtn.addEventListener('click', startGps);

  // Add a one-shot place/landmark search without modifying the HTML template.
  // Public Nominatim is deliberately used only after the user clicks Search;
  // do not turn this into autocomplete or repeated background requests.
  const searchWrap = document.createElement('div');
  searchWrap.className = 'map-search-row';
  searchWrap.style.cssText = 'display:flex;gap:8px;align-items:center;margin:0 0 10px;flex-wrap:wrap;';

  const searchInput = document.createElement('input');
  searchInput.type = 'search';
  searchInput.id = 'mapPlaceSearch';
  searchInput.placeholder = 'Search park, street, landmark or address';
  searchInput.setAttribute('aria-label', 'Search for a park, street, landmark or address');
  searchInput.style.cssText = 'flex:1;min-width:190px;margin:0;';

  const searchButton = document.createElement('button');
  searchButton.type = 'button';
  searchButton.className = 'btn btn-ghost btn-sm';
  searchButton.innerHTML = '<i class="fa-solid fa-magnifying-glass"></i> Search place';

  searchWrap.append(searchInput, searchButton);
  mapEl.parentNode.insertBefore(searchWrap, mapEl);

  async function searchPlace() {
    const query = searchInput.value.trim();
    if (query.length < 3) {
      setMessage('Enter at least 3 characters to search for a place.');
      return;
    }

    searchButton.disabled = true;
    setMessage('Searching OpenStreetMap for that place…');
    try {
      const url = new URL('https://nominatim.openstreetmap.org/search');
      url.searchParams.set('format', 'jsonv2');
      url.searchParams.set('limit', '5');
      url.searchParams.set('q', query);

      const response = await fetch(url.toString(), {
        headers: { 'Accept': 'application/json' }
      });
      if (!response.ok) throw new Error(`Search service returned ${response.status}`);
      const results = await response.json();
      if (!Array.isArray(results) || results.length === 0) {
        setMessage('No matching place was found. Try a nearby landmark or click directly on the map.');
        return;
      }

      const place = results[0];
      const lat = Number(place.lat);
      const lng = Number(place.lon);
      setPoint(lat, lng, { pan: true });
      setMessage(`Map centred on: ${place.display_name || query}. Click the exact issue spot or drag the pin to fine-tune it.`);
    } catch (error) {
      setMessage('Place search is temporarily unavailable. You can still click the map or use GPS.');
    } finally {
      searchButton.disabled = false;
    }
  }

  searchButton.addEventListener('click', searchPlace);
  searchInput.addEventListener('keydown', event => {
    if (event.key === 'Enter') {
      event.preventDefault();
      searchPlace();
    }
  });

  // Park selection centres the map on that park; the citizen must still
  // choose the exact problem spot instead of silently using the park centre.
  const park = $('park_id');
  const other = $('park_other');
  if (park && other) {
    function parkChange(initial) {
      other.style.display = park.value === 'other' ? 'block' : 'none';
      other.required = park.value === 'other';
      const option = park.selectedOptions[0];
      if (!initial && option && option.dataset.lat && option.dataset.lng) {
        map.setView([Number(option.dataset.lat), Number(option.dataset.lng)], 18);
        if (!latI.value || !lngI.value) {
          setMessage('Map centred on the selected park. Now choose the exact issue location.');
        }
      }
    }
    park.addEventListener('change', () => parkChange(false));
    parkChange(true);
  }

  // Photo preview (existing behavior retained).
  const photoInput = $('photo');
  if (photoInput) {
    photoInput.addEventListener('change', event => {
      const file = event.target.files[0];
      const image = $('photoPreview');
      if (!image) return;
      if (!file) {
        image.style.display = 'none';
        return;
      }
      if (file.size > 8 * 1024 * 1024) {
        if (typeof pcToast === 'function') pcToast('Photo is larger than 8 MB.');
        else window.alert('Photo is larger than 8 MB.');
        photoInput.value = '';
        image.style.display = 'none';
        return;
      }
      image.src = URL.createObjectURL(file);
      image.style.display = 'block';
    });
  }

  // Live clock is display-only; the server records the authoritative time.
  const when = $('when');
  if (when) {
    const tick = () => { when.value = new Date().toLocaleString(); };
    tick();
    window.setInterval(tick, 1000);
  }

  // Require a user-selected location before allowing submission.
  if (form) {
    form.addEventListener('submit', event => {
      if (!latI.value || !lngI.value) {
        event.preventDefault();
        event.stopImmediatePropagation();
        if (typeof pcToast === 'function') pcToast('Please set the issue location using GPS, place search or the map.', 'warning');
        else window.alert('Please set the issue location using GPS, place search or the map.');
        mapEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }, true);
  }

  // Leaflet needs a size refresh after the form/card layout has painted.
  window.setTimeout(() => map.invalidateSize(), 150);
})();
