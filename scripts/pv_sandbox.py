from __future__ import annotations

import datetime as dt
import itertools
from dataclasses import dataclass

import numpy as np
import pyvista as pv
import seaborn as sns
from numpy.typing import ArrayLike, NDArray
from pyvista import examples

from navsim.emitters import SatelliteEmitters
from navtools.conversions import ecef2geodetic, geodetic2ecef
from navtools.geodesy import GeodeticDatum


@dataclass
class NavplotConstellation:
    constellation_name: str
    datetimes: dt.datetime | list[dt.datetime]
    satellite_names: str | list[str]
    positions: ArrayLike
    color: str | None = None

    def __post_init__(self):
        # convert to lists and arrays
        if isinstance(self.datetimes, dt.datetime):
            self.datetimes = [self.datetimes]

        if isinstance(self.satellite_names, str):
            self.satellite_names = [self.satellite_names]

        self.positions = np.asarray(self.positions)

        # check dimensionality
        invalid_ndim = self.positions.ndim != 3

        positions_shape = np.array(self.positions.shape)
        invalid_datetime_dims = np.all(positions_shape != len(self.datetimes))
        invalid_emitter_dims = np.all(positions_shape != len(self.satellite_names))

        if invalid_ndim or invalid_datetime_dims or invalid_emitter_dims:
            msg = "Position input must be of shape (E, T, 3) where E is the number of emitters and T is the number of datetimes."
            raise ValueError(msg)


def generate_timeseries(
    initial_datetime: dt.datetime,
    duration: float,
    fsim: float,
) -> tuple[list[float], list[dt.datetime]]:
    """
    Generate elapsed time points and corresponding UTC datetime stamps.

    Parameters
    ----------
    initial_datetime : datetime.datetime
        UTC start time for the simulation time series.
    duration : float
        Total simulation duration in seconds.
    fsim : float
        Simulation sampling frequency in Hz.

    Returns
    -------
    timeseries : list of float
        Elapsed time values from t=0 to t=duration.
    datetimes : list of datetime.datetime
        UTC timestamps corresponding to each elapsed time.

    Examples
    --------
    >>> from datetime import datetime
    >>> t, ts = generate_timeseries(datetime(2025,1,1), 10.0, 1.0)
    >>> len(t), ts[0], ts[-1]
    (11, datetime.datetime(2025, 1, 1, 0, 0), datetime.datetime(2025, 1, 1, 0, 0, 10))
    """
    tsim = 1.0 / fsim
    nperiods = int(np.ceil(duration / tsim)) + 1
    timeseries = np.linspace(start=0.0, stop=duration, num=nperiods).tolist()
    datetimes = [initial_datetime + dt.timedelta(seconds=step) for step in timeseries]

    return timeseries, datetimes


# Add planets to Plotter.


# Add title with explicit color


# # Add Denver, Colorado point on Earth's surface
# # Denver coordinates: 39.7392° N, 104.9903° W


# # Convert lat/lon to 3D coordinates on Earth's surface
# # Account for PyVista's coordinate system orientation (180° shift)
# lat_rad = np.radians(denver_lat)
# lon_rad = np.radians(denver_lon)  # Add 180° to correct for PyVista's coordinate system

# # Convert to Cartesian coordinates (Earth's surface)
# denver_x = earth_radius * np.cos(lat_rad) * np.cos(lon_rad)
# denver_y = earth_radius * np.cos(lat_rad) * np.sin(lon_rad)
# denver_z = earth_radius * np.sin(lat_rad)

# denver_pos = [denver_x, denver_y, denver_z]
# pl.set_focus(denver_pos)
# # Add Denver as a distinctive point
# denver_marker = pv.Sphere(radius=earth_radius * 0.015, center=denver_pos)
# pl.add_mesh(denver_marker, color="yellow", name="denver_marker")

# # Add Denver label
# pl.add_point_labels(
#     [denver_pos], ["Denver, CO"], point_size=1, font_size=12, text_color="yellow"
# )


def plot_satellites(
    constellations: list[NavplotConstellation],
    datum: GeodeticDatum = GeodeticDatum.from_datum(datum_name="wgs84"),
    focal_position: ArrayLike = np.zeros(3),
    focal_position_name: str = "Focal Position",
    color_palette: str = "bright",
    radius_multiple_threshold: int = 20,
    include_labels: bool = False,
    include_trajectories: bool = True,
):
    # define Earth parameters with datum
    earth_radius = datum.r0
    earth = examples.planets.load_earth(radius=earth_radius)
    earth.rotate_z(180, inplace=True)  # rotate to align plotting frame with ECEF frames
    earth_texture = examples.load_globe_texture()

    # add Earth to scene
    pl = pv.Plotter()
    pl.set_background("black")
    pl.add_mesh(earth, texture=earth_texture, smooth_shading=True)
    pl.add_title(
        f"Satellite Trajectories ({datum.name} ECEF Reference Frame)",
        font_size=16,
        color="white",
    )

    palette = sns.color_palette(color_palette).as_hex()
    color_cycle = itertools.cycle(palette)

    # Store constellation info for legend
    legend_entries = []

    for c in constellations:
        color = next(color_cycle) if c.color is None else c.color

        # Store for legend
        legend_entries.append((c.constellation_name.upper(), color))

        # find first valid positions (non-NaN) in time series
        non_nan_mask = np.logical_not(np.isnan(c.positions))
        first_valid_idx = np.unique(non_nan_mask.argmax(axis=1), axis=1).squeeze()
        rows = np.arange(c.positions.shape[0])
        first_valid_positions = c.positions[
            rows,
            first_valid_idx,
        ]

        pl.add_points(first_valid_positions, render_points_as_spheres=True, color=color)

        if include_labels:
            pl.add_point_labels(
                first_valid_positions,
                c.satellite_names,
                point_size=1,
                font_size=12,
                text_color=color,
            )

        if c.positions.shape[1] > 1 and include_trajectories:
            line_mesh = lines_from_array(lines_array=c.positions)
            pl.add_mesh(line_mesh, color=color)

    # Add custom legend with individual colored text labels (bottom right)
    legend_spacing = 0.05  # Reduced spacing between entries
    legend_y_start = 0.05  # Start from bottom
    legend_x = 0.85

    for i, (name, color) in enumerate(legend_entries):
        y_pos = legend_y_start + i * legend_spacing  # Build upward from bottom
        pl.add_text(
            name,
            position=(legend_x, y_pos),
            font_size=14,
            color=color,
            font="arial",
            viewport=True,  # Use normalized viewport coordinates
        )

    pl.add_axes(
        interactive=True,
        line_width=3,
        color="white",
        x_color="red",
        y_color="green",
        z_color="blue",
        xlabel="x",
        ylabel="y",
        zlabel="z",
        viewport=(0, 0, 0.3, 0.3),
    )

    if np.all(focal_position != 0.0):
        color = next(color_cycle)
        focal_marker = pv.Sphere(radius=earth_radius * 0.01, center=focal_position)
        pl.add_mesh(focal_marker, color=color, name=focal_position_name)

        # Add Denver label
        pl.add_point_labels(
            [focal_position],
            [focal_position_name],
            point_size=1,
            font_size=12,
            text_color=color,
        )

    # Set camera to focus on focal point from a distance
    camera_distance = earth_radius * 10.0  # Distance from focal point

    # Calculate camera position (offset from focal point)
    focal_position_lla = ecef2geodetic(
        focal_position[0], focal_position[1], focal_position[2]
    )
    camera_position = np.array(
        geodetic2ecef(
            lat=focal_position_lla.lat,
            lon=focal_position_lla.lon,
            alt=focal_position_lla.alt + camera_distance,
        )
    )

    # Set camera properties
    pl.camera.position = camera_position
    pl.camera.focal_point = focal_position
    pl.camera.up = (0, 0, 1)  # Z-axis up

    # Optional: set a good viewing angle
    pl.camera.view_angle = 30

    pl.show()


def lines_from_array(lines_array):
    """
    Create PyVista lines from 3D numpy array

    Parameters:
    lines_array: numpy array of shape (n_lines, n_points_per_line, 3)
    """
    n_lines, n_points_per_line, _ = lines_array.shape

    # Flatten all points
    all_points = lines_array.reshape(-1, 3)

    # Create line connectivity
    lines = []
    for i in range(n_lines):
        start_idx = i * n_points_per_line
        point_indices = list(range(start_idx, start_idx + n_points_per_line))
        # Format: [n_points_in_line, point1_idx, point2_idx, ...]
        line_def = [n_points_per_line] + point_indices
        lines.extend(line_def)

    lines = np.array(lines)
    return pv.PolyData(all_points, lines=lines)


# # Add satellite trajectories
# for sat, states in emitter_states.items():
#     # Create trajectory
#     trajectory = states[0]

#     if trajectory.shape[0] > 1:
#         line = pv.lines_from_points(
#             trajectory, close=False
#         )  # builds connected line :contentReference[oaicite:2]{index=2}
#         pl.add_mesh(line, line_width=2, name=f"{sat}_trajectory_line")

if __name__ == "__main__":
    import re

    GNSS_RE = re.compile(r"^[GRECIJ]\d{2}$")

    def is_gnss_id(s: str) -> bool:
        return bool(GNSS_RE.match(s))

    # find focal point ECEF position
    latitude = 40.7128
    longitude = -74.0060

    denver_ecef = np.array(
        geodetic2ecef(lat=latitude, lon=longitude, alt=0.0, deg=True)
    )

    # compute emitter states
    emitters = SatelliteEmitters(constellations=["globalstar", "iridium"])
    _, datetimes = generate_timeseries(
        dt.datetime(year=2025, month=7, day=5, tzinfo=dt.timezone.utc), 3600, 1
    )
    emitters.process(utc_timestamps=datetimes)
    emitter_states = emitters.find_in_view(rx_pos=denver_ecef, mask_angle=40)

    i_names = [name for name in list(emitter_states.keys()) if name.startswith("I")]
    i_pos = [
        states[0] for name, states in emitter_states.items() if name.startswith("I")
    ]

    i = NavplotConstellation(
        constellation_name="iridium",
        datetimes=datetimes,
        satellite_names=i_names,
        positions=i_pos,
    )

    starlink_names = [
        name
        for name in list(emitter_states.keys())
        if name.casefold().startswith("globalstar")
    ]
    starlink_pos = [
        states[0]
        for name, states in emitter_states.items()
        if name.casefold().startswith("globalstar")
    ]

    emitters = SatelliteEmitters(constellations=["gps"])
    emitters.process(utc_timestamps=datetimes)
    emitter_states = emitters.find_in_view(rx_pos=denver_ecef, mask_angle=10)

    gps_names = [
        name
        for name in list(emitter_states.keys())
        if name.startswith("G") and is_gnss_id(name)
    ]
    gps_pos = [
        states[0]
        for name, states in emitter_states.items()
        if name.startswith("G") and is_gnss_id(name)
    ]

    gps = NavplotConstellation(
        constellation_name="gps",
        datetimes=datetimes,
        satellite_names=gps_names,
        positions=gps_pos,
    )

    starlink = NavplotConstellation(
        constellation_name="globalstar",
        datetimes=datetimes,
        satellite_names=starlink_names,
        positions=starlink_pos,
    )

    # plot
    plot_satellites(
        constellations=[starlink, i, gps],
        include_labels=True,
        focal_position=denver_ecef,
        focal_position_name="NYC, NY, USA",
        radius_multiple_threshold=2,
        include_trajectories=True,
        color_palette="inferno",
    )
