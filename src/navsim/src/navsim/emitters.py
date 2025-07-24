import datetime as dt
from dataclasses import dataclass
from itertools import compress

import numpy as np
from astropy.time import Time
from navgnss.los import compute_visibility
from navtools.constants import SECONDS_PER_WEEK
from navtools.geodesy import GeodeticDatum
from navtools.io import FileDownloader
from navtools.io.parse import parse_sp3, parse_tle
from numpy.typing import ArrayLike
from scipy.interpolate import PchipInterpolator
from sgp4.api import Satrec, SatrecArray
from zoneinfo import ZoneInfo

from navsim.conversions import teme2itrf


@dataclass
class SupportedConstellation:
    eph_format: str
    eph_name: str
    orbit_type: str
    url_name: str | None = None


class SatelliteEmitters:
    FIRST_DATETIME = dt.datetime(year=2023, month=8, day=11, tzinfo=dt.timezone.utc)
    MEO_RADIUS_THRESHOLD = (
        45000000  # [m] sligthly beyond GEO radius from ECEF frame origin
    )
    LEO_RADIUS_THRESHOLD = (
        9000000  # [m] sligthly beyond LEO radius from ECEF frame origin
    )

    SUPPORTED_CONSTELLATIONS = {
        "gps": SupportedConstellation(eph_format="sp3", eph_name="G", orbit_type="MEO"),
        "galileo": SupportedConstellation(
            eph_format="sp3", eph_name="E", orbit_type="MEO"
        ),
        "glonass": SupportedConstellation(
            eph_format="sp3", eph_name="R", orbit_type="MEO"
        ),
        "beidou": SupportedConstellation(
            eph_format="sp3", eph_name="C", orbit_type="MEO"
        ),
        "qzss": SupportedConstellation(
            eph_format="sp3", eph_name="J", orbit_type="MEO"
        ),
        "iridium": SupportedConstellation(
            eph_format="tle",
            eph_name="IRIDIUM",
            url_name="iridium-NEXT",
            orbit_type="LEO",
        ),
        "orbcomm": SupportedConstellation(
            eph_format="tle", eph_name="ORBCOMM", url_name="orbcomm", orbit_type="LEO"
        ),
        "globalstar": SupportedConstellation(
            eph_format="tle",
            eph_name="GLOBALSTAR",
            url_name="globalstar",
            orbit_type="LEO",
        ),
        "oneweb": SupportedConstellation(
            eph_format="tle", eph_name="ONEWEB", url_name="oneweb", orbit_type="LEO"
        ),
        "starlink": SupportedConstellation(
            eph_format="tle", eph_name="STARLINK", url_name="starlink", orbit_type="LEO"
        ),
        "eutelsat": SupportedConstellation(
            eph_format="tle", eph_name="EUTELSAT", url_name="eutelsat", orbit_type="LEO"
        ),
        "kuiper": SupportedConstellation(
            eph_format="tle", eph_name="KUIPER", url_name="kuiper", orbit_type="LEO"
        ),
        "qianfan": SupportedConstellation(
            eph_format="tle", eph_name="QIANFAN", url_name="qianfan", orbit_type="LEO"
        ),
    }

    @property
    def tle_constellations(self):
        return self._tle_constellations

    @property
    def sp3_constellations(self):
        return self._sp3_constellations

    def __init__(self, constellations: list, disable_warnings: bool = True):
        casefolded_constellations = [
            constellation.casefold() for constellation in constellations
        ]
        self._tle_constellations = {
            common_name: SatelliteEmitters.SUPPORTED_CONSTELLATIONS[common_name]
            for common_name in casefolded_constellations
            if SatelliteEmitters.SUPPORTED_CONSTELLATIONS[common_name].eph_format
            == "tle"
        }
        self._sp3_constellations = {
            common_name: SatelliteEmitters.SUPPORTED_CONSTELLATIONS[common_name]
            for common_name in casefolded_constellations
            if SatelliteEmitters.SUPPORTED_CONSTELLATIONS[common_name].eph_format
            == "sp3"
        }
        self._eph_names = {
            SatelliteEmitters.SUPPORTED_CONSTELLATIONS[
                common_name
            ].eph_name: SatelliteEmitters.SUPPORTED_CONSTELLATIONS[common_name]
            for common_name in casefolded_constellations
        }

        self._tle_ids = None
        self._tle_lines = None
        self._sp3_ids = None
        self._sp3_states = None

        self._downloader = FileDownloader(disable_warning=disable_warnings)
        self._initial_time: Time | list = []

    def process(
        self,
        utc_timestamps: dt.datetime | list[dt.datetime],
        min_inclination: float | None = None,
    ) -> dict:
        # convert to astropy Time
        utc_ts = Time(utc_timestamps)

        # test to see in new_time is same as established initial_time
        new_time = utc_ts[0] if utc_ts.shape else utc_ts
        self._initialze_time(new_time=new_time)

        # process each constellation based on ephemeris format
        self._emitters = {}
        if self._tle_constellations:
            tle_emitters = self._process_tle(
                utc_time=utc_ts, min_inclination=min_inclination
            )
            self._emitters.update(tle_emitters)

        if self._sp3_constellations:
            sp3_emitters = self._process_sp3(utc_time=utc_ts)
            self._emitters.update(sp3_emitters)

        self._remove_outliers()

        return self._emitters

    def remove_emitters(self, emitter_id: str | list[str]):
        if isinstance(emitter_id, str):
            emitter_id = [emitter_id]

        # tle removal
        if not self._tle_ids is None:
            valid_tle_mask = np.logical_not(np.isin(self._tle_ids, emitter_id))
            self._tle_ids = self._tle_ids[valid_tle_mask]
            self._tle_lines = self._tle_lines[valid_tle_mask]
            self._build_tle_array()

        # sp3 removal
        if not self._sp3_ids is None:
            valid_sp3_mask = np.logical_not(np.isin(self._sp3_ids, emitter_id))
            self._sp3_ids = self._sp3_ids[valid_sp3_mask]
            self._sp3_states = list(compress(self._sp3_states, valid_sp3_mask.tolist()))

    def find_in_view(self, rx_pos: ArrayLike, mask_angle: float):
        new_emitters = {}

        for emitter_id, (emitter_pos, emitter_vel) in self._emitters.items():
            # determine visibility
            status, _, _ = compute_visibility(
                rx_pos=rx_pos,
                emitter_pos=emitter_pos,
                mask_angle=mask_angle,
            )

            if status.sum() == 0.0:
                continue

            out_of_view_mask = np.logical_not(status)
            emitter_pos[out_of_view_mask] = np.nan
            emitter_vel[out_of_view_mask] = np.nan

            new_emitters[emitter_id] = (emitter_pos, emitter_vel)

        return new_emitters

    def _initialze_time(self, new_time: Time):
        if self._initial_time != new_time:
            self._initial_time = new_time

        utc_datetime = self._initial_time.datetime.astimezone(ZoneInfo("UTC"))
        if SatelliteEmitters.FIRST_DATETIME > utc_datetime:
            msg = f"the initial time needs to be after {SatelliteEmitters.FIRST_DATETIME.isoformat()}."
            raise ValueError(msg)

    def _process_tle(self, utc_time: Time, min_inclination: float | None):
        if self._tle_lines is None:
            self._download_tle_files(min_inclination=min_inclination)
            self._build_tle_array()

        jd1 = np.atleast_1d(utc_time.jd1)
        jd2 = np.atleast_1d(utc_time.jd2)
        error_codes, teme_pos, teme_vel = self._tle_array.sgp4(jd1, jd2)

        if np.any(error_codes != 0):
            remove_idx = np.any(error_codes != 0, axis=1)
            valid_idx = np.logical_not(remove_idx)
            teme_pos = teme_pos[valid_idx]
            teme_vel = teme_vel[valid_idx]

            invalid_emitters = self._tle_ids[remove_idx]
            self.remove_emitters(emitter_id=invalid_emitters.tolist())

        ecef_pos, ecef_vel = teme2itrf(
            utc_time,
            teme_pos,
            teme_vel,
        )
        ecef_pos *= 1000  # [m]
        ecef_vel *= 1000  # [m/s]

        emitters = {
            emitter_id: (pos, vel)
            for emitter_id, pos, vel in zip(self._tle_ids, ecef_pos, ecef_vel)
        }

        return emitters

    def _build_tle_array(self):
        self._tle_array = SatrecArray(
            [Satrec.twoline2rv(line[0], line[1]) for line in self._tle_lines]
        )

    def _process_sp3(self, utc_time: list[Time]):
        if self._sp3_states is None:
            self._download_sp3_files()

        emitters = {}
        for emitter_id, states in zip(self._sp3_ids, self._sp3_states):
            time = states[0]
            xyz_clk = states[1]

            pchip = PchipInterpolator(x=time, y=xyz_clk)
            new_xyz_clk = np.atleast_2d(pchip(utc_time.gps))
            new_dxyz_clk = np.atleast_2d(pchip(utc_time.gps, 1))

            emitters[emitter_id] = (
                new_xyz_clk[:, :3],
                new_dxyz_clk[:, :3],
            )  # TODO: add ability to return clock states

        return emitters

    def _download_tle_files(self, min_inclination: float | None):
        # download tles
        urls = self._build_tle_urls()
        files = self._downloader.download(
            url=urls, progress_desc="Downloading TLE Ephemeris"
        )

        files = files if isinstance(files, list) else [files]

        # parse tles and append entries
        tle_entries = {}
        for file in files:
            file_entries = parse_tle(file_path=file, min_inclination=min_inclination)
            tle_entries.update(file_entries)

        self._tle_ids = np.array(list(tle_entries.keys()))
        self._tle_lines = np.array(list(tle_entries.values()))

    def _download_sp3_files(self):
        # download sp3s
        urls = self._build_sp3_urls()
        files = self._downloader.download(
            url=urls, progress_desc="Downloading SP3 Ephemeris"
        )
        files = files if isinstance(files, list) else [files]

        valid_sp3_ids = [
            SatelliteEmitters.SUPPORTED_CONSTELLATIONS[c].eph_name
            for c in self._sp3_constellations
        ]

        sp3_entries = {}
        file_entries = [
            parse_sp3(file_path=file, valid_constellations=valid_sp3_ids)
            for file in files
        ]

        # find common prns across all file entries (should have common, but just checking)
        common_prns = set.intersection(*[set(entry.keys()) for entry in file_entries])
        for prn in common_prns:
            # concatenate arbitrary # of arrays for # of files
            data_by_idx = zip(*[entry[prn] for entry in file_entries])
            entry = [np.concatenate(data) for data in data_by_idx]

            time = entry[0]
            states = entry[1]

            # find unique timestamps
            time, unique_idx = np.unique(time, return_index=True)
            states = states[unique_idx]

            # sort data by time
            sorted_idx = time.argsort()
            sp3_entries[prn] = [time[sorted_idx], states[sorted_idx]]

        self._sp3_ids = np.array(list(sp3_entries.keys()))
        self._sp3_states = list(sp3_entries.values())  # possibly non-homogenous

    def _build_tle_urls(self):
        initial_time = self._initial_time.datetime.timetuple()
        year = initial_time.tm_year
        day = "%03d" % initial_time.tm_yday

        urls = [
            f"https://raw.githubusercontent.com/tannerkoza/celestrak-orbital-data/main/{constellation.url_name}/{year}/{day}/{constellation.url_name}.tle"
            for constellation in self._tle_constellations.values()
        ]

        return urls

    def _build_sp3_urls(self):
        MAX_FINAL_DELAY = dt.timedelta(days=12)
        MAX_RAPID_DELAY = dt.timedelta(hours=26)

        # compute difference from now and initial sim time
        initial_datetime = self._initial_time.datetime.replace(tzinfo=ZoneInfo("UTC"))
        now = dt.datetime.now(tz=dt.timezone.utc)
        difference = now - initial_datetime

        if difference < dt.timedelta(days=1):
            raise ValueError(
                f"The selected time must be at least one day before current date ({now.isoformat()}) for GNSS."
            )

        # check if BeiDou and QZSS are possible with selected initial_datetime
        has_beidou_or_qzss = any(
            c in self._sp3_constellations for c in ["beidou", "qzss"]
        )
        if has_beidou_or_qzss and difference <= MAX_FINAL_DELAY:
            cutoff_date = (now - MAX_FINAL_DELAY).isoformat()
            raise ValueError(
                f"BeiDou and QZSS are not supported for ESA rapid or ultra-rapid SP3 products.\n"
                f"Remove these constellations or change the date to {cutoff_date} or before."
            )

        # select multiple days to interpolate across
        times = [
            initial_datetime - dt.timedelta(days=1),
            initial_datetime,
        ]

        # straddle true date to end-to-end interpolation
        if difference > dt.timedelta(days=2):
            times.append(initial_datetime + dt.timedelta(days=1))

        urls = []
        for time in times:
            # extract year, day, and gps week
            initial_time = time.timetuple()
            year = initial_time.tm_year
            day = "%03d" % initial_time.tm_yday
            gps_week = int(
                np.floor(np.array(self._initial_time.gps) / SECONDS_PER_WEEK)
            )

            # select final, rapid, or ultra rapid product url based on selected initial_datetime
            if difference > MAX_FINAL_DELAY:
                file_name = f"ESA0MGNFIN_{year}{day}0000_01D_05M_ORB.SP3"
            elif difference > MAX_RAPID_DELAY:
                file_name = f"ESA0OPSRAP_{year}{day}0000_01D_05M_ORB.SP3"
            else:
                file_name = f"ESA0OPSULT_{year}{day}0000_02D_05M_ORB.SP3"

            url = f"http://navigation-office.esa.int/products/gnss-products/{gps_week}/{file_name}.gz"
            urls.append(url)

        return urls

    def _remove_outliers(self):
        new_emitters = {}

        wgs84 = GeodeticDatum.from_datum("wgs84")
        meo_allowable_ratio = SatelliteEmitters.MEO_RADIUS_THRESHOLD / wgs84.r0
        leo_allowable_ratio = SatelliteEmitters.LEO_RADIUS_THRESHOLD / wgs84.r0

        for emitter_id, (emitter_pos, emitter_vel) in self._emitters.items():
            radius = np.linalg.norm(emitter_pos, axis=1)
            max_ratio = radius.max() / wgs84.r0

            orbit_type = self._get_emitter_orbit_type(emitter_id=emitter_id)

            if orbit_type == "MEO":
                invalid_orbit = max_ratio > meo_allowable_ratio

            elif orbit_type == "LEO":
                invalid_orbit = max_ratio > leo_allowable_ratio

            else:
                invalid_orbit = False

            if invalid_orbit:
                continue

            new_emitters[emitter_id] = (emitter_pos, emitter_vel)

        self._emitters = new_emitters

    def _get_emitter_orbit_type(self, emitter_id: str):
        orbit_type = next(
            (
                c.orbit_type
                for eph_name, c in self._eph_names.items()
                if emitter_id.startswith(eph_name)
            )
        )

        return orbit_type
