import datetime as dt
from collections import defaultdict
from dataclasses import dataclass

import numpy as np
from astropy.time import Time, TimeGPS
from navtools.constants import SECONDS_PER_WEEK
from navtools.conversions import datetime_to_gps
from navtools.io import FileDownloader, decompress
from sgp4.api import Satrec, SatrecArray
from zoneinfo import ZoneInfo

from navsim.conversions import teme2itrf


@dataclass
class SupportedConstellation:
    eph_format: str
    eph_name: str
    url_name: str | None = None


class SatelliteEmitters:
    FIRST_DATETIME = dt.datetime(year=2023, month=8, day=11, tzinfo=dt.timezone.utc)

    SUPPORTED_CONSTELLATIONS = {
        "gps": SupportedConstellation(eph_format="sp3", eph_name="G"),
        "galileo": SupportedConstellation(eph_format="sp3", eph_name="E"),
        "glonass": SupportedConstellation(eph_format="sp3", eph_name="R"),
        "beidou": SupportedConstellation(eph_format="sp3", eph_name="C"),
        "qzss": SupportedConstellation(eph_format="sp3", eph_name="J"),
        "iridium": SupportedConstellation(
            eph_format="tle", eph_name="IRIDIUM", url_name="iridium-NEXT"
        ),
        "orbcomm": SupportedConstellation(
            eph_format="tle", eph_name="ORBCOMM", url_name="orbcomm"
        ),
        "globalstar": SupportedConstellation(
            eph_format="tle", eph_name="GLOBALSTAR", url_name="globalstar"
        ),
        "oneweb": SupportedConstellation(
            eph_format="tle", eph_name="ONEWEB", url_name="oneweb"
        ),
        "starlink": SupportedConstellation(
            eph_format="tle", eph_name="STARLINK", url_name="starlink"
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

        self._tle_lines = None
        self._sp3_states = None

        self._downloader = FileDownloader(disable_warning=disable_warnings)
        self._initial_time = []

    def process(
        self,
        utc_timestamps: dt.datetime | list[dt.datetime],
        min_latitude: float | None = None,
    ):
        utc_timestamps = Time(utc_timestamps)

        new_time = utc_timestamps[0] if utc_timestamps.shape else utc_timestamps
        self._initialze_time(new_time=new_time)

        if self._tle_constellations:
            emitters = self._process_tle(
                utc_time=utc_timestamps, min_latitude=min_latitude
            )

        if self._sp3_constellations:
            emitters = self._process_sp3(utc_time=utc_timestamps)

        return emitters

    def remove_emitters(self, emitter_id: str | list[str]):
        if isinstance(emitter_id, str):
            emitter_id = [emitter_id]

        valid_id_mask = np.logical_not(np.isin(self._tle_emitter_ids, emitter_id))
        self._tle_emitter_ids = self._tle_emitter_ids[valid_id_mask]
        self._tle_lines = self._tle_lines[valid_id_mask]
        self._build_tle_array()

    def _initialze_time(self, new_time: Time):
        if self._initial_time != new_time:
            self._initial_time = new_time

        utc_datetime = self._initial_time.datetime.astimezone(ZoneInfo("UTC"))
        if SatelliteEmitters.FIRST_DATETIME > utc_datetime:
            msg = f"the initial time needs to be after {SatelliteEmitters.FIRST_DATETIME.isoformat()}."
            raise ValueError(msg)

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

    def _process_sp3(self, utc_time: list[Time]):
        if self._sp3_states is None:
            self._download_sp3_files()

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

    def _download_tle_files(self, min_latitude: float | None):
        initial_time = self._initial_time.datetime.timetuple()
        year = initial_time.tm_year
        day = "%03d" % initial_time.tm_yday

        urls = [
            f"https://raw.githubusercontent.com/tannerkoza/celestrak-orbital-data/main/{constellation.url_name}/{year}/{day}/{constellation.url_name}.tle"
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

    def _download_sp3_files(self):
        urls = self._build_sp3_url()
        files = [self._downloader.download(url) for url in urls]

        eph_names = {
            SatelliteEmitters.SUPPORTED_CONSTELLATIONS[c].eph_name: c
            for c in self._sp3_constellations
        }

        states = defaultdict(list)

        for file in files:
            with open(file, "r") as f:
                lines = f.readlines()

            current_time = None
            for line in lines:
                if line.startswith("*"):
                    parts = line.split()
                    current_time = dt.datetime(
                        int(parts[1]),
                        int(parts[2]),
                        int(parts[3]),
                        int(parts[4]),
                        int(parts[5]),
                        int(float(parts[6])),
                        tzinfo=dt.timezone.utc,
                    )
                    gps_week, gps_tow = datetime_to_gps(datetime=current_time)
                    gps_time = Time(gps_week, gps_tow, format="gps")

                elif line.startswith("P") and current_time:
                    prn = line[1:4]

                    if prn[0] in eph_names:
                        x = float(line[4:18]) * 1e3
                        y = float(line[18:32]) * 1e3
                        z = float(line[32:46]) * 1e3
                        clk = float(line[46:60]) * 1e-6
                        states[prn].append((gps_time, [x, y, z, clk]))

        self._sp3_emitter_ids = np.array(list(states.keys()))
        self._sp3_states = list(states.values())

    def _build_sp3_url(self):
        MAX_FINAL_DELAY = dt.timedelta(days=12)
        MAX_RAPID_DELAY = dt.timedelta(hours=26)

        initial_datetime = self._initial_time.datetime
        times = [
            initial_datetime - dt.timedelta(days=1),
            initial_datetime + dt.timedelta(days=1),
        ]

        urls = []
        for time in times:
            # extract year, day, and gps week
            initial_time = time.timetuple()
            year = initial_time.tm_year
            day = "%03d" % initial_time.tm_yday
            gps_week = int(
                np.floor(np.array(self._initial_time.gps) / SECONDS_PER_WEEK)
            )

            # compute difference from now and initial sim time
            now = dt.datetime.now(tz=dt.timezone.utc)
            initial_time_utc = self._initial_time.datetime.astimezone(ZoneInfo("UTC"))
            difference = now - initial_time_utc

            has_beidou_or_qzss = any(
                c in self._sp3_constellations for c in ["beidou", "qzss"]
            )

            if has_beidou_or_qzss and difference <= MAX_FINAL_DELAY:
                cutoff_date = (now - MAX_FINAL_DELAY).isoformat()
                raise ValueError(
                    f"BeiDou and QZSS are not supported for ESA rapid or ultra-rapid SP3 products.\n"
                    f"Remove these constellations or change the date to {cutoff_date} or before."
                )

            if difference > MAX_FINAL_DELAY:
                file_name = f"ESA0MGNFIN_{year}{day}0000_01D_05M_ORB.SP3"
            elif difference > MAX_RAPID_DELAY:
                file_name = f"ESA0OPSRAP_{year}{day}0000_01D_05M_ORB.SP3"
            else:
                file_name = f"ESA0OPSULT_{year}{day}0000_02D_05M_ORB.SP3"

            url = f"http://navigation-office.esa.int/products/gnss-products/{gps_week}/{file_name}.gz"
            urls.append(url)

        return urls
