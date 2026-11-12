// Geospatial File Measurement & GIS Explorer Client Application

let map;
let geojsonLayerGroup;
let currentFeatures = [];
let currentFileInfo = null;
let selectedFeatureId = null;

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) lucide.createIcons();
  initMap();
  setupEventListeners();
  loadFilesHistory();
});

// Initialize Leaflet Map
function initMap() {
  map = L.map("map", {
    zoomControl: true,
    attributionControl: true,
  }).setView([20.0, 0.0], 2);

  // High contrast CartoDB Positron Dark basemap
  const darkBasemap = L.tileLayer(
    "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
    {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
      subdomains: "abcd",
      maxZoom: 20,
    }
  );

  const osmBasemap = L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
      attribution: '&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a>',
      maxZoom: 19,
    }
  );

  darkBasemap.addTo(map);

  L.control
    .layers(
      {
        "CartoDB Voyager": darkBasemap,
        "OpenStreetMap Standard": osmBasemap,
      },
      null,
      { position: "bottomright" }
    )
    .addTo(map);

  geojsonLayerGroup = L.featureGroup().addTo(map);
}

// Event Listeners
function setupEventListeners() {
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");

  dropzone.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) {
      uploadFile(e.target.files[0]);
    }
  });

  // Drag and drop handlers
  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add("border-emerald-400", "bg-slate-900");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove("border-emerald-400", "bg-slate-900");
    });
  });

  dropzone.addEventListener("drop", (e) => {
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      uploadFile(e.dataTransfer.files[0]);
    }
  });

  // Sample Loaders
  document.getElementById("btn-load-sample-kml").addEventListener("click", () => {
    loadSampleFile("/api/samples/kml", "sample_survey.kml");
  });

  document.getElementById("btn-load-sample-shp").addEventListener("click", () => {
    loadSampleFile("/api/samples/shapefile", "sample_shapefile.zip");
  });

  // Refresh history
  document.getElementById("btn-refresh-history").addEventListener("click", loadFilesHistory);

  // Delete active file
  document.getElementById("btn-delete-active-file").addEventListener("click", deleteActiveFile);

  // Search and filter table
  document.getElementById("table-search").addEventListener("input", filterTable);
  document.getElementById("table-filter-type").addEventListener("change", filterTable);
}

// Upload file to POST /api/files/
async function uploadFile(file) {
  const statusDiv = document.getElementById("upload-status");
  statusDiv.className = "mt-4 p-3 rounded-xl border text-xs bg-slate-900/80 border-slate-700 text-slate-300 flex items-center gap-2";
  statusDiv.innerHTML = `<i data-lucide="loader" class="w-4 h-4 text-emerald-400 animate-spin"></i> Uploading & processing ${file.name}...`;
  statusDiv.classList.remove("hidden");
  if (window.lucide) lucide.createIcons();

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/files/", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Upload failed");
    }

    statusDiv.className = "mt-4 p-3 rounded-xl border text-xs bg-emerald-950/40 border-emerald-700 text-emerald-300 flex items-center gap-2";
    statusDiv.innerHTML = `<i data-lucide="check-circle" class="w-4 h-4 text-emerald-400"></i> Successfully processed ${file.name}!`;
    if (window.lucide) lucide.createIcons();

    // Load full details for this file
    await loadFileDetails(data.id);
    loadFilesHistory();
  } catch (err) {
    statusDiv.className = "mt-4 p-3 rounded-xl border text-xs bg-red-950/40 border-red-700 text-red-300 flex items-center gap-2";
    statusDiv.innerHTML = `<i data-lucide="alert-triangle" class="w-4 h-4 text-red-400"></i> ${err.message}`;
    if (window.lucide) lucide.createIcons();
  }
}

// Load a sample file by fetching its blob and posting to /api/files/
async function loadSampleFile(sampleUrl, filename) {
  const statusDiv = document.getElementById("upload-status");
  statusDiv.className = "mt-4 p-3 rounded-xl border text-xs bg-slate-900/80 border-slate-700 text-slate-300 flex items-center gap-2";
  statusDiv.innerHTML = `<i data-lucide="loader" class="w-4 h-4 text-emerald-400 animate-spin"></i> Fetching sample ${filename}...`;
  statusDiv.classList.remove("hidden");
  if (window.lucide) lucide.createIcons();

  try {
    const fetchRes = await fetch(sampleUrl);
    if (!fetchRes.ok) throw new Error("Could not retrieve sample file.");
    const blob = await fetchRes.blob();
    const file = new File([blob], filename);
    await uploadFile(file);
  } catch (err) {
    statusDiv.className = "mt-4 p-3 rounded-xl border text-xs bg-red-950/40 border-red-700 text-red-300 flex items-center gap-2";
    statusDiv.innerHTML = `<i data-lucide="alert-triangle" class="w-4 h-4 text-red-400"></i> Error loading sample: ${err.message}`;
    if (window.lucide) lucide.createIcons();
  }
}

// Load complete details for a file (GET /api/files/{id}/details/)
async function loadFileDetails(fileId) {
  try {
    const res = await fetch(`/api/files/${fileId}/details/`);
    if (!res.ok) throw new Error("Failed to load file details.");
    const data = await res.json();

    currentFileInfo = data;
    currentFeatures = data.features || [];

    renderFileSummary(data);
    renderMapFeatures(currentFeatures);
    renderFeaturesTable(currentFeatures);

    // Auto-select first feature if available
    if (currentFeatures.length > 0) {
      selectFeature(currentFeatures[0]);
    }
  } catch (err) {
    console.error("Error loading file details:", err);
  }
}

// Render Summary Banner
function renderFileSummary(data) {
  document.getElementById("file-summary-empty").classList.add("hidden");
  document.getElementById("file-summary-content").classList.remove("hidden");
  document.getElementById("active-file-actions").classList.remove("hidden");

  document.getElementById("stat-filename").textContent = data.filename;
  document.getElementById("stat-filename").title = data.filename;
  document.getElementById("stat-filetype").textContent = data.file_type;
  document.getElementById("stat-features").textContent = data.feature_count;

  // Breakdown counts
  const summaryStr = Object.entries(data.geometry_summary || {})
    .map(([k, v]) => `${v} ${k}`)
    .join(", ");
  document.getElementById("stat-breakdown").textContent = summaryStr || "No features";

  document.getElementById("stat-crs").textContent = data.crs;
  document.getElementById("stat-crs").title = data.crs;
  document.getElementById("stat-status").textContent = data.status;
  document.getElementById("stat-id").textContent = `ID: ${data.id}`;

  const downloadGeoJSON = document.getElementById("btn-download-geojson");
  downloadGeoJSON.href = `/api/files/${data.id}/geojson/`;
  downloadGeoJSON.setAttribute("download", `${data.filename}.geojson`);

  if (window.lucide) lucide.createIcons();
}

// Render features on Leaflet Map
function renderMapFeatures(features) {
  geojsonLayerGroup.clearLayers();

  if (!features || features.length === 0) return;

  features.forEach((feat) => {
    const geom = feat.geometry;
    let layer = null;

    if (geom.type === "Point") {
      const [lon, lat] = geom.coordinates;
      layer = L.circleMarker([lat, lon], {
        radius: 7,
        fillColor: "#f59e0b",
        color: "#ffffff",
        weight: 2,
        opacity: 1,
        fillOpacity: 0.9,
      });
    } else {
      // Polygon, LineString, MultiPolygon, MultiLineString
      const isPolygon = geom.type.includes("Polygon");
      layer = L.geoJSON(
        { type: "Feature", geometry: geom, properties: feat.properties },
        {
          style: {
            color: isPolygon ? "#10b981" : "#06b6d4",
            weight: isPolygon ? 2 : 4,
            fillColor: isPolygon ? "#10b981" : "transparent",
            fillOpacity: isPolygon ? 0.35 : 0,
          },
        }
      );
    }

    if (layer) {
      // Attach click and popup
      const popupHtml = buildPopupContent(feat);
      layer.bindPopup(popupHtml);

      layer.on("click", () => {
        selectFeature(feat);
      });

      // Store reference
      layer._featureId = feat.id;
      geojsonLayerGroup.addLayer(layer);
    }
  });

  try {
    const bounds = geojsonLayerGroup.getBounds();
    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 16 });
    }
  } catch (e) {
    console.warn("Could not fit bounds:", e);
  }
}

// Build popup HTML for a feature
function buildPopupContent(feat) {
  const m = feat.measurement;
  let measHtml = "";
  if (m.supported) {
    if (m.measurement_type === "area") {
      measHtml = `
        <div class="mt-2 p-2 bg-emerald-950/60 rounded border border-emerald-800/80">
          <div class="text-[10px] text-emerald-400 uppercase font-bold">Calculated Area</div>
          <div class="text-sm font-black text-white">${m.units.sq_meters?.toLocaleString()} m²</div>
          <div class="text-[10px] text-slate-300 mt-0.5">
            ${m.units.hectares} ha &bull; ${m.units.acres} acres &bull; ${m.units.sq_kilometers} km²
          </div>
          <div class="text-[9px] text-slate-400 mt-1">Projected: ${m.projected_crs || "UTM"}</div>
        </div>`;
    } else if (m.measurement_type === "length") {
      measHtml = `
        <div class="mt-2 p-2 bg-cyan-950/60 rounded border border-cyan-800/80">
          <div class="text-[10px] text-cyan-400 uppercase font-bold">Calculated Length</div>
          <div class="text-sm font-black text-white">${m.units.meters?.toLocaleString()} meters</div>
          <div class="text-[10px] text-slate-300 mt-0.5">
            ${m.units.kilometers} km &bull; ${m.units.feet?.toLocaleString()} ft &bull; ${m.units.miles} mi
          </div>
          <div class="text-[9px] text-slate-400 mt-1">Projected: ${m.projected_crs || "UTM"}</div>
        </div>`;
    }
  } else {
    measHtml = `<div class="mt-2 p-2 bg-slate-800 rounded border border-slate-700 text-[10px] text-slate-400">${m.note}</div>`;
  }

  const name = feat.properties.name || feat.properties.NAME || `Feature ${feat.id}`;
  return `
    <div class="space-y-1">
      <div class="font-bold text-white text-xs">${name}</div>
      <div class="text-[10px] text-slate-400 font-mono">ID: ${feat.id} | ${feat.geometry_type}</div>
      ${measHtml}
    </div>
  `;
}

// Feature selection handler (updates inspector panel and highlights table row)
function selectFeature(feat) {
  selectedFeatureId = feat.id;

  document.getElementById("inspector-empty").classList.add("hidden");
  document.getElementById("inspector-content").classList.remove("hidden");

  document.getElementById("selected-feature-badge").textContent = `ID: ${feat.id} (${feat.geometry_type})`;

  const m = feat.measurement;
  const measTypeEl = document.getElementById("inspector-meas-type");
  const primaryValEl = document.getElementById("inspector-primary-val");
  const primaryUnitEl = document.getElementById("inspector-primary-unit");
  const crsCodeEl = document.getElementById("inspector-crs-code");
  const unitsGrid = document.getElementById("inspector-units-grid");

  unitsGrid.innerHTML = "";

  if (m.supported) {
    measTypeEl.textContent = `${m.measurement_type} Measurement`;
    crsCodeEl.textContent = m.projected_crs || "Projected UTM";
    primaryValEl.textContent = m.primary_value?.toLocaleString();
    primaryUnitEl.textContent = m.primary_unit === "sq_meters" ? "Square Meters (m²)" : "Meters (m)";

    // Units Grid
    for (const [unitKey, unitVal] of Object.entries(m.units)) {
      const cleanKey = unitKey.replace(/_/g, " ");
      const item = document.createElement("div");
      item.className = "bg-slate-900/90 p-2 rounded border border-slate-800";
      item.innerHTML = `
        <span class="text-[10px] text-slate-400 uppercase font-mono">${cleanKey}</span>
        <p class="text-xs font-bold text-slate-200 truncate">${unitVal?.toLocaleString()}</p>
      `;
      unitsGrid.appendChild(item);
    }
  } else {
    measTypeEl.textContent = "No Measurement";
    crsCodeEl.textContent = feat.crs;
    primaryValEl.textContent = "N/A";
    primaryUnitEl.textContent = m.note || "Not applicable";

    const item = document.createElement("div");
    item.className = "col-span-2 bg-slate-900/90 p-2 rounded border border-slate-800 text-slate-400 text-xs";
    item.textContent = m.note;
    unitsGrid.appendChild(item);
  }

  // Populate Properties Body
  const propsBody = document.getElementById("inspector-props-body");
  propsBody.innerHTML = "";
  const propEntries = Object.entries(feat.properties || {});
  if (propEntries.length === 0) {
    propsBody.innerHTML = `<tr><td class="py-2 px-3 text-slate-500 italic">No attributes present</td></tr>`;
  } else {
    propEntries.forEach(([k, v]) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td class="py-1.5 px-3 font-medium text-slate-400 bg-slate-900/40 w-1/3 truncate" title="${k}">${k}</td>
        <td class="py-1.5 px-3 text-slate-200 truncate" title="${v}">${v}</td>
      `;
      propsBody.appendChild(tr);
    });
  }

  // Highlight table row
  document.querySelectorAll("#features-table-body tr").forEach((tr) => {
    if (tr.dataset.featureId === String(feat.id)) {
      tr.classList.add("selected-row");
      tr.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } else {
      tr.classList.remove("selected-row");
    }
  });

  if (window.lucide) lucide.createIcons();
}

// Render Features Table
function renderFeaturesTable(features) {
  const tbody = document.getElementById("features-table-body");
  tbody.innerHTML = "";

  if (!features || features.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="py-8 text-center text-slate-500 italic">No features found in dataset.</td></tr>`;
    return;
  }

  features.forEach((feat) => {
    const m = feat.measurement;
    let measStr = "-";
    let badgeColor = "bg-slate-800 text-slate-400";

    if (m.supported) {
      if (m.measurement_type === "area") {
        measStr = `${m.units.sq_meters?.toLocaleString()} m² (${m.units.hectares} ha)`;
        badgeColor = "bg-emerald-950 text-emerald-400 border border-emerald-800";
      } else if (m.measurement_type === "length") {
        measStr = `${m.units.meters?.toLocaleString()} m (${m.units.kilometers} km)`;
        badgeColor = "bg-cyan-950 text-cyan-400 border border-cyan-800";
      }
    } else {
      badgeColor = "bg-amber-950 text-amber-400 border border-amber-800";
      measStr = "N/A";
    }

    const primaryAttr = feat.properties.name || feat.properties.NAME || Object.values(feat.properties)[0] || "-";

    const tr = document.createElement("tr");
    tr.dataset.featureId = String(feat.id);
    tr.dataset.geomType = feat.geometry_type;
    tr.className = "hover:bg-slate-800/80 cursor-pointer transition-colors";
    tr.innerHTML = `
      <td class="py-2.5 px-4 font-mono font-medium text-slate-200">${feat.id}</td>
      <td class="py-2.5 px-4"><span class="px-2 py-0.5 rounded text-[11px] font-medium ${badgeColor}">${feat.geometry_type}</span></td>
      <td class="py-2.5 px-4 capitalize text-slate-300">${m.measurement_type || "None"}</td>
      <td class="py-2.5 px-4 font-mono text-white">${measStr}</td>
      <td class="py-2.5 px-4 text-slate-400 text-[11px]">${m.projected_crs || feat.crs}</td>
      <td class="py-2.5 px-4 text-slate-300 truncate max-w-xs">${primaryAttr}</td>
    `;

    tr.addEventListener("click", () => {
      selectFeature(feat);
      // Zoom map to feature
      zoomMapToFeature(feat);
    });

    tbody.appendChild(tr);
  });
}

// Zoom map to specific feature
function zoomMapToFeature(feat) {
  geojsonLayerGroup.eachLayer((layer) => {
    if (layer._featureId === feat.id) {
      if (layer.getBounds) {
        map.fitBounds(layer.getBounds(), { maxZoom: 16, padding: [50, 50] });
      } else if (layer.getLatLng) {
        map.setView(layer.getLatLng(), 15);
      }
      if (layer.openPopup) layer.openPopup();
    }
  });
}

// Filter table by search input and geometry type select
function filterTable() {
  const query = document.getElementById("table-search").value.toLowerCase();
  const filterType = document.getElementById("table-filter-type").value;

  const rows = document.querySelectorAll("#features-table-body tr");
  rows.forEach((row) => {
    const text = row.textContent.toLowerCase();
    const type = row.dataset.geomType || "";

    const matchesSearch = text.includes(query);
    const matchesType = filterType === "ALL" || type === filterType;

    if (matchesSearch && matchesType) {
      row.style.display = "";
    } else {
      row.style.display = "none";
    }
  });
}

// Load previous files list from GET /api/files/
async function loadFilesHistory() {
  try {
    const res = await fetch("/api/files/");
    if (!res.ok) return;
    const data = await res.json();

    const countEl = document.getElementById("history-count");
    const chipsDiv = document.getElementById("history-chips");
    countEl.textContent = data.total;

    chipsDiv.innerHTML = "";
    if (data.total === 0) {
      chipsDiv.innerHTML = `<span class="text-xs text-slate-500 italic">No files in history</span>`;
      return;
    }

    data.files.forEach((f) => {
      const chip = document.createElement("button");
      chip.className = `text-xs px-2.5 py-1 rounded-lg border transition-all flex items-center gap-1.5 ${
        currentFileInfo && currentFileInfo.id === f.id
          ? "bg-emerald-600/30 border-emerald-500 text-emerald-200"
          : "bg-slate-900 border-slate-700 text-slate-300 hover:border-slate-500"
      }`;
      chip.innerHTML = `
        <span class="w-1.5 h-1.5 rounded-full ${f.status === "COMPLETED" ? "bg-emerald-400" : "bg-red-400"}"></span>
        <span class="truncate max-w-[120px]">${f.filename}</span>
        <span class="text-[10px] text-slate-400">(${f.feature_count})</span>
      `;
      chip.addEventListener("click", () => loadFileDetails(f.id));
      chipsDiv.appendChild(chip);
    });
  } catch (e) {
    console.error("Could not load history:", e);
  }
}

// Delete current active file
async function deleteActiveFile() {
  if (!currentFileInfo) return;
  if (!confirm(`Are you sure you want to delete '${currentFileInfo.filename}'?`)) return;

  try {
    const res = await fetch(`/api/files/${currentFileInfo.id}/`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error("Delete failed");

    // Reset UI
    currentFileInfo = null;
    currentFeatures = [];
    geojsonLayerGroup.clearLayers();
    document.getElementById("file-summary-empty").classList.remove("hidden");
    document.getElementById("file-summary-content").classList.add("hidden");
    document.getElementById("active-file-actions").classList.add("hidden");
    document.getElementById("inspector-empty").classList.remove("hidden");
    document.getElementById("inspector-content").classList.add("hidden");
    renderFeaturesTable([]);
    loadFilesHistory();
  } catch (e) {
    alert("Error deleting file: " + e.message);
  }
}
