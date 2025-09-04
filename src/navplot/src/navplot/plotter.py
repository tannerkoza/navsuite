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

# currently private functions to satellite. Not sure on the organization for these so leaving as is for now
from navplot.satellites import (
    NavplotConstellation,
    _find_first_valid_positions,
    _pyvista_lines_from_array,
)
from numpy.typing import ArrayLike, NDArray
from pyvista import examples


class NavPlotter(pv.Plotter):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def plot_earth(
        self,
        focal_position: ArrayLike = np.zeros(3),
        focal_position_name: str = "Focal Position",
        datum: GeodeticDatum = GeodeticDatum.from_datum(datum_name="wgs84"),
        color_palette: str = "gist_ncar",
        **kwargs,
    ):
        # define pyvista Earth parameters
        earth_radius = datum.r0  # equatorial radius [m]

        earth = examples.planets.load_earth(radius=earth_radius)
        earth.rotate_z(
            angle=180, inplace=True
        )  # rotate for coincidence with ECEF frame

        # initialize seaborn color palette
        palette = sns.color_palette(color_palette).as_hex()
        color_cycle = itertools.cycle(palette)

        earth_texture = examples.load_globe_texture()
        self.add_mesh(
            earth, texture=earth_texture, smooth_shading=True, name="earth", **kwargs
        )

        # plot focal position and set camera
        focal_position = np.asarray(focal_position)
        camera_distance = earth_radius * 7.5

        if np.all(focal_position != 0.0):
            color = next(color_cycle)

            focal_marker = pv.Sphere(radius=earth_radius * 0.01, center=focal_position)
            self.add_mesh(focal_marker, color=color, name=focal_position_name)

            self.add_point_labels(
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

        self.camera.position = camera_position
        self.camera.up = (0, 0, 1)

    def plot_satellites(
        self,
        constellations: list[NavplotConstellation],
        include_labels: bool = False,
        color_palette: str = "gist_ncar",
        **kwargs,
    ):
        if "earth" not in self.actors.values():
            self.plot_earth()
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
            self.add_points(
                first_positions,
                render_points_as_spheres=True,
                color=color,
                label=cnst.name.upper(),
                name=cnst.name,
                **kwargs,
            )

            sv_names = list(cnst.positions.keys())
            if include_labels:
                self.add_point_labels(
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
                self.add_mesh(mesh=trajectories, color=color)

    def plot_ECEF(self, axis_scale: float = 0.5, **kwargs):
        if "earth" not in self.actors.values():
            self.plot_earth()
        earth = self.actors["earth"]
        axes = pv.AxesAssembly(scale=earth.length * axis_scale, **kwargs)
        self.add_actor(axes)

    def add_triad(self, **kwargs):
        # create axes marker
        self.add_axes(
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
            **kwargs,
        )


def test():
    # define simulation parameters
    latitude = 39.7392
    longitude = -104.9903
    ecef_pos = np.array(geodetic2ecef(lat=latitude, lon=longitude, alt=0.0, deg=True))
    focal_position_name = "Denver, CO"

    constellations = ["gps", "glonass", "galileo", "beidou", "qzss", "globalstar"]
    mask_angle = 25

    initial_datetime = dt.datetime(year=2025, month=7, day=20, tzinfo=dt.timezone.utc)
    duration = 3600 * 24  # [s]
    time_step = 60  # [s]

    # initialize datetimes
    ntime_steps = int(np.ceil(duration / time_step)) + 1
    timeseries = np.linspace(start=0.0, stop=duration, num=ntime_steps)
    datetimes = [initial_datetime + dt.timedelta(seconds=step) for step in timeseries]

    # simulate satellite states
    satellites = SatelliteEmitters(constellations=constellations)
    satellite_states = satellites.process(utc_timestamps=datetimes)
    # satellite_states = satellites.find_in_view(rx_pos=ecef_pos, mask_angle=mask_angle)

    navplot_constellations = []

    for cnst in constellations:
        positions = {
            sv_name: states[0]
            for sv_name, states in satellite_states.items()
            if cnst.casefold() == satellites.get_constellation(emitter_id=sv_name)
        }
        velocities = {
            sv_name: states[1]
            for sv_name, states in satellite_states.items()
            if cnst.casefold() == satellites.get_constellation(emitter_id=sv_name)
        }

        if positions and velocities:
            navplot_cnst = NavplotConstellation(
                name=cnst, positions=positions, velocities=velocities
            )

            navplot_constellations.append(navplot_cnst)

    plt = NavPlotter()
    plt.set_background("black")

    title = f"Satellite Trajectories - WGS84 ECEF Reference Frame"
    plt.add_title(
        title=title,
        font_size=16,
        color="white",
    )

    plt.plot_earth(
        focal_position=ecef_pos,
        focal_position_name=focal_position_name,
    )
    plt.plot_satellites(constellations=navplot_constellations, point_size=10)
    plt.add_triad()
    plt.show()


if __name__ == "__main__":
    test()
