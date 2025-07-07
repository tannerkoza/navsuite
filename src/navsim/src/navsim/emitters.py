import numpy as np
import datetime as dt

from astropy.time import Time
from sgp4.api import Satrec, SatrecArray

from navtools.io import FileDownloader
from navsim.utils import teme2itrf


class SatelliteEmitters:
    SUPPORTED_TLE_CONSTELLATIONS = {
        "iridium": "iridium-NEXT",
        "orbcomm": "orbcomm",
        "globalstar": "globalstar",
        "oneweb": "oneweb",
        "starlink": "starlink",
    }  # key: common name, value: url case-specific name

    def __init__(
        self,
        constellations: list,
    ):
        casefolded_constellations = [
            constellation.casefold() for constellation in constellations
        ]
        self._tle_constellations = {
            common_name: SatelliteEmitters.SUPPORTED_TLE_CONSTELLATIONS[common_name]
            for common_name in casefolded_constellations
            if common_name in SatelliteEmitters.SUPPORTED_TLE_CONSTELLATIONS
        }
        self._tle_lines = None

        self._sp3_constellations = {}

        self._downloader = FileDownloader()
        self._initial_time = []

    def process(
        self,
        utc_time: dt.datetime | list[dt.datetime],
        min_latitude: float | None = None,
    ):
        utc_time = Time(utc_time)

        new_time = utc_time[0] if utc_time.shape else utc_time
        if self._initial_time != new_time:
            self._initial_time = new_time

        if self._tle_constellations:
            emitters = self._process_tle(utc_time=utc_time, min_latitude=min_latitude)

        if self._sp3_constellations:
            pass

        return emitters

    def remove_emitters(self, emitter_id: str | list[str]):
        if isinstance(emitter_id, str):
            emitter_id = [emitter_id]

        valid_id_mask = np.logical_not(np.isin(self._tle_emitter_ids, emitter_id))
        self._tle_emitter_ids = self._tle_emitter_ids[valid_id_mask]
        self._tle_lines = self._tle_lines[valid_id_mask]
        self._build_tle_array()

    def _process_tle(self, utc_time: list[Time], min_latitude: float | None):
        if self._tle_lines is None:
            self._download_tle_files(min_latitude=min_latitude)
            self._build_tle_array()

        jd1 = np.atleast_1d(utc_time.jd1)
        jd2 = np.atleast_1d(utc_time.jd2)
        error_codes, teme_pos, teme_vel = self._tle_array.sgp4(jd1, jd2)

        if np.any(error_codes != 0):
            raise RuntimeError(f"SGP4 errors encountered: {set(error_codes)}")

        ecef_pos, ecef_vel = teme2itrf(
            utc_time,
            teme_pos,
            teme_vel,
        )
        ecef_pos *= 1000
        ecef_vel *= 1000

        emitters = {
            emitter_id: (pos, vel)
            for emitter_id, pos, vel in zip(self._tle_emitter_ids, ecef_pos, ecef_vel)
        }

        return emitters

    def _build_tle_array(self):
        self._tle_array = SatrecArray(
            [Satrec.twoline2rv(line[0], line[1]) for line in self._tle_lines]
        )

    def _download_tle_files(self, min_latitude: float | None):
        initial_time = self._initial_time.datetime.timetuple()
        year = initial_time.tm_year
        day = "%03d" % initial_time.tm_yday

        urls = [
            f"https://raw.githubusercontent.com/tannerkoza/celestrak-orbital-data/main/{constellation}/{year}/{day}/{constellation}.tle"
            for constellation in self._tle_constellations.values()
        ]
        files = [self._downloader.download(url) for url in urls]

        tle_emitter_ids = []
        tle_lines = []

        for file in files:
            with open(file, "r") as f:
                lines = f.readlines()

                for sv_idx in range(0, len(lines), 3):
                    line1 = lines[sv_idx + 1]
                    line2 = lines[sv_idx + 2]

                    if min_latitude is not None:
                        fields = line2.split()
                        inclination = float(fields[2])

                        if inclination < np.abs(min_latitude):
                            continue

                    tle_emitter_ids.append(lines[sv_idx].strip())
                    tle_lines.append(
                        [
                            line1,
                            line2,
                        ]
                    )

        self._tle_emitter_ids = np.array(tle_emitter_ids)
        self._tle_lines = np.array(tle_lines)
