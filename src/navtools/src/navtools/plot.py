import itertools
from dataclasses import dataclass

import numpy as np
import plotly.graph_objects as go
import seaborn as sns
from numpy.typing import ArrayLike

from navtools.geodesy import great_circle_distance


@dataclass
class GeoplotData:
    label: str
    lat: ArrayLike
    lon: ArrayLike
    alt: ArrayLike | None = None
    time: ArrayLike | None = None

    color: str | None = None


def igeoplot(
    geodata,
    symbol: str = "circle",
    size: int = 5,
    title: str = "Interactive Geoplot",
    color_palette: str = "bright",
    output_path=None,
):
    fig = go.Figure()

    palette = sns.color_palette(color_palette).as_hex()
    color_cycle = itertools.cycle(palette)

    if not isinstance(geodata, list):
        geodata = [geodata]

    all_lat = []
    all_lon = []

    for data in geodata:
        hover_strings = _build_hover_strings(geodata=data)
        color = next(color_cycle) if data.color is None else data.color

        fig.add_trace(
            go.Scattermap(
                lat=data.lat,
                lon=data.lon,
                mode="markers",
                name=data.label,
                marker=dict(symbol=symbol, size=size, color=color),
                hoverinfo="text",
                text=hover_strings,
                hoverlabel=dict(bordercolor="white", font=dict(color="black")),
            )
        )

        all_lat.extend(data.lat)
        all_lon.extend(data.lon)

    # compute bounding box width and height
    min_lat = min(all_lat)
    max_lat = max(all_lat)
    min_lon = min(all_lon)
    max_lon = max(all_lon)

    center_lat = (max_lat + min_lat) / 2
    center_lon = (max_lon + min_lon) / 2

    width = great_circle_distance(center_lat, min_lon, center_lat, max_lon)
    height = great_circle_distance(min_lat, center_lon, max_lat, center_lon)

    max_circumference = 40075017  # equator earth circumference [m]
    min_circumference = 40007863  # meridian earth circumference [m]

    if height > width:
        zoom = np.log2((min_circumference / 2) * np.cos(np.radians(center_lat)) / width)
    else:
        zoom = np.log2(max_circumference * np.cos(np.radians(center_lat)) / height)

    fig.update_layout(
        autosize=True,
        margin=dict(t=0, b=0, l=0, r=0),
        map=dict(
            style="white-bg",
            layers=[
                {
                    "below": "traces",
                    "sourcetype": "raster",
                    "source": ["https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}"],
                    "sourceattribution": "Google Hybrid Maps",
                }
            ],
            center=dict(lat=center_lat, lon=center_lon),
            zoom=zoom,
        ),
        title=title,
        legend=dict(
            x=0,
            y=0,
            xanchor="left",
            yanchor="bottom",
        ),
    )

    if output_path is not None:
        fig.write_html(output_path / "interactive_geoplot.html")
    fig.show()


def _build_hover_strings(geodata):
    latitudes, longitudes = geodata.lat, geodata.lon
    base_string = [
        f"<b>{geodata.label}</b><br>Latitude: {lat:.4f} [deg]<br>Longitude: {lon:.4f} [deg]"
        for lat, lon in zip(latitudes, longitudes)
    ]

    if geodata.alt is None:
        hover_string = base_string
    else:
        altitudes = geodata.alt
        hover_string = [
            f"{base}<br>Altitude: {alt:.3f} [m]"
            for base, alt in zip(base_string, altitudes)
        ]

    if not geodata.time is None:
        times = geodata.time
        hover_string = [
            f"{hover}<br>Time: {time:.3f} [s]"
            for hover, time in zip(hover_string, times)
        ]

    return hover_string
