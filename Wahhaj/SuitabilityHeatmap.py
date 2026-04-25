import folium
import numpy as np
from branca.colormap import LinearColormap


class SuitabilityHeatmap:
    def __init__(self, resolution=100.0, color_scale="RdYlGn"):
        self.resolution = resolution
        self.color_scale = color_scale

    def generate_heatmap(self, scores):
        self._scores = scores
        return scores

    def create_folium_map(
        self,
        scores,
        aoi,
        location_name="Selected Location",
        selected_lon=None,
        selected_lat=None,
        zoom_start=11,
    ):
        lon_min, lat_min, lon_max, lat_max = aoi
        data = np.asarray(scores.data, dtype=float)
        nodata = getattr(scores, "nodata", -9999.0)

        center_lat = (lat_min + lat_max) / 2
        center_lon = (lon_min + lon_max) / 2

        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=zoom_start,
            tiles=None,
        )

        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Tiles © Esri, Maxar, Earthstar Geographics, and contributors",
            name="Satellite",
            overlay=False,
            control=True,
        ).add_to(m)

        rows, cols = data.shape[:2]
        lat_step = (lat_max - lat_min) / rows
        lon_step = (lon_max - lon_min) / cols

        colormap = LinearColormap(
            colors=["#e74c3c", "#f4b040", "#f1c40f", "#7fcc50", "#22c55e"],
            vmin=0,
            vmax=1,
        )
        colormap.caption = "Selected Location Suitability Scale"

        for r in range(rows):
            for c in range(cols):
                score = float(data[r, c])

                if not np.isfinite(score) or score == nodata:
                    continue

                score = max(0.0, min(1.0, score))

                cell_lat_max = lat_max - (r * lat_step)
                cell_lat_min = lat_max - ((r + 1) * lat_step)
                cell_lon_min = lon_min + (c * lon_step)
                cell_lon_max = lon_min + ((c + 1) * lon_step)

                folium.Rectangle(
                    bounds=[
                        [cell_lat_min, cell_lon_min],
                        [cell_lat_max, cell_lon_max],
                    ],
                    color="#4a8f2a",
                    weight=0.6,
                    fill=True,
                    fill_color=colormap(score),
                    fill_opacity=0.42,
                    tooltip=f"Suitability Score: {score * 100:.1f}%",
                ).add_to(m)

        folium.Rectangle(
            bounds=[[lat_min, lon_min], [lat_max, lon_max]],
            color="#0070FF",
            weight=3,
            fill=False,
        ).add_to(m)

        if selected_lat is not None and selected_lon is not None:
            folium.CircleMarker(
                location=[selected_lat, selected_lon],
                radius=7,
                color="#0070FF",
                weight=3,
                fill=True,
                fill_color="white",
                fill_opacity=1,
                tooltip=location_name,
            ).add_to(m)

            

        legend_html = """
        <div style="
            position: fixed;
            bottom: 28px;
            left: 28px;
            z-index: 9999;
            background: rgba(255,255,255,0.95);
            border-radius: 14px;
            padding: 12px 14px;
            box-shadow: 0 4px 18px rgba(0,0,0,0.12);
            min-width: 230px;
            font-family: Arial, sans-serif;
        ">
            <div style="
                font-size:13px;
                font-weight:700;
                color:#1f3864;
                margin-bottom:8px;
            ">Selected Location Suitability Scale</div>

            <div style="
                height:10px;
                border-radius:999px;
                background:linear-gradient(90deg,#e74c3c,#f4b040,#f1c40f,#7fcc50,#22c55e);
                margin-bottom:6px;
            "></div>

            <div style="
                display:flex;
                justify-content:space-between;
                font-size:11px;
                color:#666;
                margin-bottom:8px;
            ">
                <span>Low</span>
                <span>High</span>
            </div>

            <div style="font-size:11px;color:#666;margin-bottom:4px;">Blue outline = selected analysis boundary</div>
            <div style="font-size:11px;color:#666;margin-bottom:4px;">Colored cells = AHP suitability scores</div>
            <div style="font-size:11px;color:#666;">Blue marker = selected site center</div>
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))

        folium.LayerControl(position="topright").add_to(m)
        m.fit_bounds([[lat_min, lon_min], [lat_max, lon_max]])

        return m