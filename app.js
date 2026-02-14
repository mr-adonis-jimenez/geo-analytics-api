const map = L.map("map").setView([20, 0], 2);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(map);

fetch("/api/regions")
  .then(res => res.json())
  .then(data => {
    data.forEach(r => {
      L.marker([r.lat, r.lon])
        .addTo(map)
        .bindPopup(`${r.region}: $${r.value.toLocaleString()}`);
    });
  });
