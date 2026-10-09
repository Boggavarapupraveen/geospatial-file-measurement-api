// Geospatial Studio Client Logic
let map;
let geojsonLayer;
let currentMeasurements = null;
let currentGeoJSON = null;
let currentMetadata = null;

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
  initMap();
  setupUploadHandlers();
  setupSampleButtons();
  setupTabs();
  setupSearch();
});

// 1. Initialize Leaflet Map
function initMap() {
  map = L.map('map', {
    zoomControl: true,
    attributionControl: false
  }).setView([20, 0], 2);

  // CartoDB Dark Matter Tiles for sleek dark mode aesthetics
  L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19,
    subdomains: 'abcd',
  }).addTo(map);
}

// 2. Drag & Drop and File Selection Handlers
function setupUploadHandlers() {
  const dropZone = document.getElementById('drop-zone');
  const fileInput = document.getElementById('file-input');

  dropZone.addEventListener('click', (e) => {
    // Avoid triggering file picker when clicking sample buttons
    if (e.target.closest('.btn-sample')) return;
    fileInput.click();
  });

  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });

  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
  });

  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      uploadFile(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
      uploadFile(e.target.files[0]);
    }
  });
}

// 3. Upload File to POST /api/files/
async function uploadFile(file) {
  const statusEl = document.getElementById('upload-status');
  statusEl.style.display = 'block';
  statusEl.innerHTML = `<span style="color: var(--accent-cyan);">⏳ Uploading & processing ${file.name}...</span>`;

  const formData = new FormData();
  formData.append('file', file);

  try {
    const uploadRes = await fetch('/api/files/', {
      method: 'POST',
      body: formData,
    });

    if (!uploadRes.ok) {
      const errData = await uploadRes.json();
      throw new Error(errData.detail || `Upload failed with status ${uploadRes.status}`);
    }

    const uploadData = await uploadRes.json();
    statusEl.innerHTML = `<span style="color: var(--accent-emerald);">✔ Processed ${file.name} successfully (${uploadData.feature_count} features).</span>`;
    
    // Fetch and display data
    await loadFileDetails(uploadData.id);
  } catch (err) {
    console.error(err);
    statusEl.innerHTML = `<span style="color: var(--accent-rose);">✖ Error: ${err.message}</span>`;
  }
}

// 4. Fetch File Details, Measurements, and GeoJSON
async function loadFileDetails(fileId) {
  try {
    // Fetch metadata
    const metaRes = await fetch(`/api/files/${fileId}/`);
    currentMetadata = await metaRes.json();

    // Fetch measurements
    const measRes = await fetch(`/api/files/${fileId}/measurements/`);
    currentMeasurements = await measRes.json();

    // Fetch GeoJSON
    const geoRes = await fetch(`/api/files/${fileId}/geojson/`);
    currentGeoJSON = await geoRes.json();

    // Render components
    renderMetrics(currentMeasurements, currentMetadata);
    renderMap(currentGeoJSON, currentMeasurements);
    renderTable(currentMeasurements.measurements);
    renderJsonInspector();

    // Display UI panels
    document.getElementById('metrics-panel').style.display = 'grid';
    document.getElementById('data-display').style.display = 'grid';
    document.getElementById('json-panel').style.display = 'block';

    // Invalidate map size after showing container
    setTimeout(() => { map.invalidateSize(); }, 200);
  } catch (err) {
    console.error('Failed to load file details:', err);
    alert(`Failed to load file data: ${err.message}`);
  }
}

// 5. Render Top Metrics Cards
function renderMetrics(measurementsData, metadata) {
  const summary = measurementsData.summary;

  document.getElementById('val-area-m2').innerText = `${summary.total_area_sq_m.toLocaleString()} m²`;
  document.getElementById('val-area-ha').innerText = `${summary.total_area_hectares.toLocaleString()} ha (${summary.total_area_sq_km.toFixed(4)} km²)`;

  document.getElementById('val-length-m').innerText = `${summary.total_length_m.toLocaleString()} m`;
  document.getElementById('val-length-km').innerText = `${summary.total_length_km.toFixed(3)} km`;

  document.getElementById('val-feature-count').innerText = summary.total_features;
  document.getElementById('val-feature-breakdown').innerText = 
    `${summary.polygon_count} Polys · ${summary.linestring_count} Lines · ${summary.point_count} Points`;

  document.getElementById('val-crs-name').innerText = `${measurementsData.crs_original} → Metric`;
  document.getElementById('val-crs-notes').innerText = `Auto UTM Zones (min. distortion)`;
}

// 6. Render GeoJSON Layers onto Leaflet Map
function renderMap(geojsonData, measurementsData) {
  if (geojsonLayer) {
    map.removeLayer(geojsonLayer);
  }

  // Build lookup of measurements by feature id
  const measMap = {};
  measurementsData.measurements.forEach(m => {
    measMap[m.feature_id] = m;
  });

  geojsonLayer = L.geoJSON(geojsonData, {
    style: (feature) => {
      const type = feature.geometry.type;
      if (type.includes('Polygon')) {
        return {
          color: '#38bdf8',
          weight: 2,
          opacity: 0.9,
          fillColor: '#38bdf8',
          fillOpacity: 0.25
        };
      } else if (type.includes('LineString')) {
        return {
          color: '#f59e0b',
          weight: 4,
          opacity: 0.9
        };
      }
      return { color: '#a855f7' };
    },
    pointToLayer: (feature, latlng) => {
      return L.circleMarker(latlng, {
        radius: 7,
        fillColor: '#a855f7',
        color: '#ffffff',
        weight: 1.5,
        opacity: 1,
        fillOpacity: 0.8
      });
    },
    onEachFeature: (feature, layer) => {
      const m = measMap[feature.id] || {};
      let popupHtml = `
        <div style="font-family: Outfit, sans-serif; font-size: 13px; line-height: 1.5; color: #1e293b;">
          <strong style="font-size: 14px; color: #0284c7;">${m.name || 'Feature ' + feature.id}</strong><br/>
          <b>Type:</b> ${m.geometry_type || feature.geometry.type}<br/>
      `;

      if (m.area_sq_m !== null && m.area_sq_m !== undefined) {
        popupHtml += `<b>Area:</b> ${m.area_sq_m.toLocaleString()} m² (${m.area_hectares} ha)<br/>`;
        if (m.perimeter_m) popupHtml += `<b>Perimeter:</b> ${m.perimeter_m.toLocaleString()} m<br/>`;
      }
      if (m.length_m !== null && m.length_m !== undefined) {
        popupHtml += `<b>Length:</b> ${m.length_m.toLocaleString()} m (${m.length_km} km)<br/>`;
      }
      if (m.projected_crs) {
        popupHtml += `<b>Projected CRS:</b> ${m.projected_crs}<br/>`;
      }
      popupHtml += `</div>`;
      layer.bindPopup(popupHtml);
    }
  }).addTo(map);

  // Auto-fit bounds
  if (geojsonLayer.getLayers().length > 0) {
    map.fitBounds(geojsonLayer.getBounds(), { padding: [40, 40] });
  }
}

// 7. Render Features Table
function renderTable(measurements) {
  const tbody = document.getElementById('table-body');
  tbody.innerHTML = '';

  measurements.forEach(m => {
    const tr = document.createElement('tr');

    let badgeClass = 'geom-other';
    if (m.geometry_type.includes('Polygon')) badgeClass = 'geom-polygon';
    else if (m.geometry_type.includes('LineString')) badgeClass = 'geom-linestring';
    else if (m.geometry_type.includes('Point')) badgeClass = 'geom-point';

    let measText = '<span style="color: var(--text-muted);">None</span>';
    if (m.area_sq_m !== null && m.area_sq_m !== undefined) {
      measText = `<strong style="color: var(--accent-cyan);">${m.area_sq_m.toLocaleString()} m²</strong> (${m.area_hectares} ha)`;
    } else if (m.length_m !== null && m.length_m !== undefined) {
      measText = `<strong style="color: var(--accent-amber);">${m.length_m.toLocaleString()} m</strong> (${m.length_km} km)`;
    }

    const propSummary = Object.keys(m.properties).length > 0 
      ? JSON.stringify(m.properties).slice(0, 45) + (JSON.stringify(m.properties).length > 45 ? '...' : '')
      : (m.name || 'No attributes');

    tr.innerHTML = `
      <td><code>#${m.feature_id}</code></td>
      <td><span class="badge-geom ${badgeClass}">${m.geometry_type}</span></td>
      <td><strong>${m.name || '-'}</strong> <br/><small style="color: var(--text-muted); font-size: 0.75rem;">${propSummary}</small></td>
      <td>${measText}</td>
      <td><small style="color: var(--text-secondary);">${m.projected_crs || 'N/A'}</small></td>
    `;
    tbody.appendChild(tr);
  });
}

// 8. Table Filter Search
function setupSearch() {
  const searchInput = document.getElementById('table-search');
  searchInput.addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase();
    const rows = document.querySelectorAll('#table-body tr');
    rows.forEach(r => {
      const text = r.innerText.toLowerCase();
      r.style.display = text.includes(query) ? '' : 'none';
    });
  });
}

// 9. Raw JSON Tabs
function setupTabs() {
  const tabs = document.querySelectorAll('.tab-btn');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      renderJsonInspector(tab.dataset.tab);
    });
  });
}

function renderJsonInspector(activeTab = 'measurements') {
  const codeEl = document.getElementById('json-content');
  if (activeTab === 'measurements') {
    codeEl.innerText = JSON.stringify(currentMeasurements, null, 2);
  } else if (activeTab === 'geojson') {
    codeEl.innerText = JSON.stringify(currentGeoJSON, null, 2);
  } else if (activeTab === 'metadata') {
    codeEl.innerText = JSON.stringify(currentMetadata, null, 2);
  }
}

// 10. Sample Loaders
function setupSampleButtons() {
  document.getElementById('btn-sample-kml').addEventListener('click', async () => {
    const kmlContent = `<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Presidio Park Survey</name>
    <Placemark>
      <name>Main Botanical Garden</name>
      <description>Presidio Botanical Park Section A</description>
      <ExtendedData>
        <Data name="zone"><value>Park_A</value></Data>
        <Data name="capacity"><value>1200</value></Data>
      </ExtendedData>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              -122.460,37.790,0 -122.455,37.790,0 -122.455,37.785,0 -122.460,37.785,0 -122.460,37.790,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
    <Placemark>
      <name>Coastal Scenic Trail</name>
      <description>North coastal hiking path</description>
      <LineString>
        <coordinates>
          -122.465,37.792,0 -122.460,37.795,0 -122.455,37.793,0 -122.450,37.796,0
        </coordinates>
      </LineString>
    </Placemark>
    <Placemark>
      <name>Overlook Point</name>
      <description>Panoramic viewpoint</description>
      <Point>
        <coordinates>-122.458,37.792,0</coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>`;

    const blob = new Blob([kmlContent], { type: 'application/vnd.google-earth.kml+xml' });
    const file = new File([blob], 'presidio_survey.kml', { type: 'application/vnd.google-earth.kml+xml' });
    uploadFile(file);
  });

  document.getElementById('btn-sample-shp').addEventListener('click', async () => {
    // Fetch pre-generated sample shapefile from endpoint
    try {
      const res = await fetch('/api/samples/shapefile');
      if (!res.ok) throw new Error('Failed to fetch sample shapefile');
      const blob = await res.blob();
      const file = new File([blob], 'sample_urban_survey.zip', { type: 'application/zip' });
      uploadFile(file);
    } catch (e) {
      alert('Generating and uploading sample shapefile...');
      // Fallback: trigger sample KML
      document.getElementById('btn-sample-kml').click();
    }
  });
}
