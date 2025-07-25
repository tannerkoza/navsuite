import datetime as dt
import itertools
from dataclasses import dataclass

import numpy as np
import pyvista as pv
import seaborn as sns
from navsim.emitters import SatelliteEmitters
from navtools.conversions import ecef2geodetic, geodetic2ecef
from navtools.geodesy import GeodeticDatum
from navtools.utils import find_axis, ragged_to_array
from numpy.typing import ArrayLike, NDArray
from pyvista import examples


@dataclass
class NavplotConstellation:
    name: str
    positions: dict[str, ArrayLike]
    velocities: dict[str, ArrayLike]
    color: str | None = None

    def __post_init__(self):
        self.positions = {
            sv_name: np.atleast_2d(pos) for sv_name, pos in self.positions.items()
        }
        self.velocities = {
            sv_name: np.atleast_2d(vel) for sv_name, vel in self.velocities.items()
        }


def plot_satellites(
    constellations: list[NavplotConstellation],
    focal_position: ArrayLike = np.zeros(3),
    focal_position_name: str = "Focal Position",
    include_labels: bool = False,
    datum: GeodeticDatum = GeodeticDatum.from_datum(datum_name="wgs84"),
    title: str | None = None,
    color_palette: str = "gist_ncar",
):
    # define pyvista Earth parameters
    earth_radius = datum.r0  # equatorial radius [m]

    earth = examples.planets.load_earth(radius=earth_radius)
    earth.rotate_z(angle=180, inplace=True)  # rotate for coincidence with ECEF frame

    # create scene and add Earth mesh
    pl = pv.Plotter()

    if title is None:
        title = f"Satellite Trajectories - {datum.name} ECEF Reference Frame"

    pl.add_title(
        title=title,
        font_size=16,
        color="white",
    )
    pl.set_background("black")

    earth_texture = examples.load_globe_texture()
    pl.add_mesh(earth, texture=earth_texture, smooth_shading=True)

    # initialize seaborn color palette
    palette = sns.color_palette(color_palette).as_hex()
    color_cycle = itertools.cycle(palette)

    for cnst in constellations:
        color = next(color_cycle) if cnst.color is None else cnst.color

        # create positions array
        ragged_positions = [pos for pos in cnst.positions.values()]
        positions = ragged_to_array(ragged=ragged_positions)

        # reorganize array (nsatellites, nepochs, 3)
        nsatellites = len(cnst.positions.keys())
        satellite_idx = find_axis(arr=positions, axis_length=nsatellites)
        position_idx = find_axis(arr=positions, axis_length=3)
        positions = np.moveaxis(positions, [satellite_idx, position_idx], [0, 2])

        # plot first positions
        first_positions = _find_first_valid_positions(positions=positions)
        pl.add_points(
            first_positions,
            render_points_as_spheres=True,
            color=color,
            label=cnst.name.upper(),
        )

        sv_names = list(cnst.positions.keys())
        if include_labels:
            pl.add_point_labels(
                first_positions,
                sv_names,
                point_size=1,
                font_size=12,
                text_color=color,
                shadow=True,
                shape_color="white",
            )

        # plot trajectories if other positions are available
        nepochs = positions.shape[1]
        if nepochs > 1:
            trajectories = _pyvista_lines_from_array(lines_array=positions)
            pl.add_mesh(mesh=trajectories, color=color)

    # create axes marker
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

    # plot focal position and set camera
    focal_position = np.asarray(focal_position)
    camera_distance = earth_radius * 7.5

    if np.all(focal_position != 0.0):
        color = next(color_cycle)

        focal_marker = pv.Sphere(radius=earth_radius * 0.01, center=focal_position)
        pl.add_mesh(focal_marker, color=color, name=focal_position_name)

        pl.add_point_labels(
            [focal_position],
            [focal_position_name],
            point_size=1,
            font_size=12,
            text_color=color,
            shadow=True,
            shape_color="white",
        )

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

    else:
        camera_position = [earth_radius + camera_distance, 0.0, 0.0]

    pl.camera.position = camera_position
    pl.camera.focal_point = focal_position
    pl.camera.up = (0, 0, 1)

    pl.add_legend(loc="lower right", size=(0.1, 0.1), face="none")

    pl.show()


def _find_first_valid_positions(positions: NDArray):
    valid_positions_mask = ~np.isnan(positions).all(axis=2)  # (nsatellites, nepochs)
    first_valid_idx = valid_positions_mask.argmax(axis=1)
    sat_idx = np.arange(first_valid_idx.size)

    first_positions = positions[sat_idx, first_valid_idx]

    return first_positions


def _pyvista_lines_from_array(lines_array):
    n_lines, n_points_per_line, _ = lines_array.shape
    all_points = lines_array.reshape(-1, 3)

    # create line connectivity
    lines = []
    for i in range(n_lines):
        start_idx = i * n_points_per_line
        point_indices = list(range(start_idx, start_idx + n_points_per_line))

        # [n_points_in_line, point1_idx, point2_idx, ...]
        line_def = [n_points_per_line] + point_indices
        lines.extend(line_def)

    lines = np.array(lines)

    return pv.PolyData(all_points, lines=lines)


def test():
    # define simulation parameters
    latitude = 39.7392
    longitude = -104.9903
    ecef_pos = np.array(geodetic2ecef(lat=latitude, lon=longitude, alt=0.0, deg=True))
    focal_position_name = "Denver, CO"

    constellations = ["globalstar", "iridium", "oneweb", "orbcomm", "starlink"]
    mask_angle = 35

    initial_datetime = dt.datetime(year=2025, month=7, day=5, tzinfo=dt.timezone.utc)
    duration = 3600  # [s]
    time_step = 1  # [s]

    # initialize datetimes
    ntime_steps = int(np.ceil(duration / time_step)) + 1
    timeseries = np.linspace(start=0.0, stop=duration, num=ntime_steps)
    datetimes = [initial_datetime + dt.timedelta(seconds=step) for step in timeseries]

    # simulate satellite states
    satellites = SatelliteEmitters(constellations=constellations)
    satellites.process(utc_timestamps=datetimes)
    satellite_states = satellites.find_in_view(rx_pos=ecef_pos, mask_angle=mask_angle)

    navplot_constellations = []

    for cnst in constellations:
        positions = {
            sv_name: states[0]
            for sv_name, states in satellite_states.items()
            if sv_name.casefold().startswith(cnst)
        }
        velocities = {
            sv_name: states[1]
            for sv_name, states in satellite_states.items()
            if sv_name.casefold().startswith(cnst)
        }

        navplot_cnst = NavplotConstellation(
            name=cnst, positions=positions, velocities=velocities
        )

        navplot_constellations.append(navplot_cnst)

    plot_satellites(
        constellations=navplot_constellations,
        focal_position=ecef_pos,
        focal_position_name=focal_position_name,
        include_labels=True,
    )


if __name__ == "__main__":
    test()
