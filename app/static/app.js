"use strict";

const SERVICE = "/arcgis/rest/services/KAPSAMA_VEKTOR/MapServer/0/query";

async function getJSON(url) {
  const response = await fetch(url, { headers: { "Accept": "application/json" } });
  if (!response.ok) {
    throw new Error("HTTP " + response.status);
  }
  return response.json();
}

function query(params) {
  const search = new URLSearchParams(Object.assign({ f: "json", where: "1=1" }, params));
  return getJSON(SERVICE + "?" + search.toString());
}

async function loadProvinceOptions() {
  const select = document.getElementById("province-filter");
  if (!select) return;
  const data = await getJSON("/webservice/api/AddressData/Iller");
  for (const il of data.iller) {
    const option = document.createElement("option");
    option.value = il.il;
    option.textContent = String(il.plaka).padStart(2, "0") + " - " + il.il;
    select.appendChild(option);
  }
}

async function loadCoverageCount() {
  const target = document.getElementById("coverage-count");
  if (!target) return;
  const data = await query({ returnCountOnly: "true" });
  target.textContent = Number(data.count).toLocaleString("tr-TR");
}

async function loadCoverageRows(where) {
  const tbody = document.querySelector("#coverage-table tbody");
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="6" class="muted">Yükleniyor…</td></tr>';
  const data = await query({
    where: where || "1=1",
    outFields: "IL,ILCE,MAHALLE,BANT,KAPASITE,DURUM",
    returnGeometry: "false",
    resultRecordCount: "25",
    orderByFields: "OBJECTID"
  });
  tbody.innerHTML = "";
  for (const feature of data.features) {
    const row = document.createElement("tr");
    for (const key of ["IL", "ILCE", "MAHALLE", "BANT", "KAPASITE", "DURUM"]) {
      const cell = document.createElement("td");
      cell.textContent = feature.attributes[key];
      row.appendChild(cell);
    }
    tbody.appendChild(row);
  }
  if (!data.features.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="muted">Kayıt bulunamadı.</td></tr>';
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadProvinceOptions().catch((err) => console.warn("İl listesi alınamadı:", err));

  const select = document.getElementById("province-filter");
  const reload = () => {
    const value = select && select.value;
    const where = value ? "IL='" + value.toLocaleUpperCase("tr-TR") + "'" : "1=1";
    loadCoverageRows(where).catch((err) => {
      const tbody = document.querySelector("#coverage-table tbody");
      if (tbody) tbody.innerHTML = '<tr><td colspan="6" class="muted">Sorgu başarısız.</td></tr>';
      console.warn("Kapsama sorgusu başarısız:", err);
    });
  };

  loadCoverageCount().catch((err) => console.warn("Sayaç alınamadı:", err));
  reload();
  if (select) select.addEventListener("change", reload);
});
