import numpy as np
from navtools.constants import BOLTZMANN, SPEED_OF_LIGHT
from navtools.conversions import ecef2geodetic
from numpy.typing import ArrayLike


def compute_klobuchar_delay(
    receiver_ecef: ArrayLike,
    azimuth_rad: ArrayLike,
    elevation_rad: ArrayLike,
    time_of_week_s: ArrayLike,
    fcarrier: float,
    alpha_coeffs: ArrayLike = np.array(
        [2.6768e-08, 4.4914e-09, -3.2658e-07, -5.2153e-07]
    ),
    beta_coeffs: ArrayLike = np.array([1.3058e05, -1.1203e05, -7.0416e05, -6.4865e06]),
) -> np.ndarray:
    """
    Compute the GPS Klobuchar ionospheric delay for L1 frequency.

    Implements the single-layer Klobuchar model using the receiver position,
    satellite azimuth/elevation, and GPS time-of-week, using broadcast α/β coefficients.

    Parameters
    ----------
    receiver_ecef : ArrayLike, shape (3,)
        Receiver ECEF position [meters].
    azimuth_rad : ArrayLike
        Azimuth angle(s) to satellite [radians].
    elevation_rad : ArrayLike
        Elevation angle(s) to satellite [radians].
    time_of_week_s : float
        GPS time-of-week [seconds].
    alpha_coeffs : array-like, length 4
        Model amplitude parameters (broadcast α values).
    beta_coeffs : array-like, length 4
        Model period parameters (broadcast β values).

    Returns
    -------
    iono_delay_s : ndarray or float
        Slant ionospheric delay [seconds] at L1 frequency; scalar if inputs scalar.
    """
    L1_FCARRIER = 1575.42e6

    az_arr, el_arr = np.broadcast_arrays(azimuth_rad, elevation_rad)
    original_shape = az_arr.shape
    az_arr = az_arr.ravel()
    el_arr = el_arr.ravel()
    is_scalar = np.prod(original_shape) == 1

    # Receiver geodetic latitude/longitude (radians)
    rec_lat_rad, rec_lon_rad, _ = ecef2geodetic(
        x=receiver_ecef[0], y=receiver_ecef[1], z=receiver_ecef[2]
    )

    semi_elev = el_arr / np.pi  # Elev in semicircles
    earth_angle = 0.0137 / (semi_elev + 0.11) - 0.022

    ip_lat = rec_lat_rad / np.pi + earth_angle * np.cos(az_arr)
    ip_lat = np.clip(ip_lat, -0.416, 0.416)

    ip_lon = rec_lon_rad / np.pi + earth_angle * np.sin(az_arr) / np.cos(ip_lat * np.pi)

    local_time = (43200.0 * ip_lon + time_of_week_s) % 86400.0

    mapping_factor = 1.0 + 16.0 * (0.53 - semi_elev) ** 3

    vert_delay_amp = np.polyval(alpha_coeffs[::-1], ip_lat)
    vert_delay_period = np.polyval(beta_coeffs[::-1], ip_lat)
    vert_delay_amp = np.maximum(vert_delay_amp, 0.0)
    vert_delay_period = np.maximum(vert_delay_period, 72000.0)

    phase = 2.0 * np.pi * (local_time - 50400.0) / vert_delay_period
    core_delay = np.full_like(phase, 5e-9)
    inside_mask = np.abs(phase) < 1.57
    core_delay[inside_mask] += vert_delay_amp[inside_mask] * (
        1 - 0.5 * phase[inside_mask] ** 2 + phase[inside_mask] ** 4 / 24.0
    )

    slant_delay_s = SPEED_OF_LIGHT * mapping_factor * core_delay

    slant_delay_s = (L1_FCARRIER / fcarrier) ** 2 * slant_delay_s

    if is_scalar:
        return float(slant_delay_s)
    return slant_delay_s.reshape(original_shape)


# def compute_klobuchar_delay(
#     rx_pos: np.ndarray,
#     az: np.ndarray,
#     el: np.ndarray,
#     tow: float,
#     alpha: np.array = np.array([2.6768e-08, 4.4914e-09, -3.2658e-07, -5.2153e-07]),
#     beta: np.array = np.array([1.3058e05, -1.1203e05, -7.0416e05, -6.4865e06]),
# ):
#     """
#     Optimized version using more efficient operations.
#     """

#     # Convert to arrays and handle broadcasting
#     az = np.asarray(az)
#     el = np.asarray(el)
#     original_shape = np.broadcast(az, el).shape
#     is_scalar = original_shape == ()

#     # Flatten for processing if needed
#     az = np.atleast_1d(az)
#     el = np.atleast_1d(el)
#     az, el = np.broadcast_arrays(az, el)

#     # Convert to geodetic coordinates
#     lat, lon, _ = ecef2geodetic(x=rx_pos[0], y=rx_pos[1], z=rx_pos[2])

#     # Vectorized calculations
#     el_norm = el / np.pi
#     psi = 0.0137 / (el_norm + 0.11) - 0.022

#     phi = lat / np.pi + psi * np.cos(az)
#     phi = np.clip(phi, -0.416, 0.416)

#     lam = lon / np.pi + psi * np.sin(az) / np.cos(phi * np.pi)

#     local_tod = 43200.0 * lam + tow
#     local_tod = np.fmod(local_tod, 86400.0)  # More efficient than floor operation

#     slant_factor = 1.0 + 16.0 * np.power(0.53 - el_norm, 3.0)

#     # Polynomial evaluation using Horner's method
#     amplitude = np.polyval(alpha[::-1], phi)  # Reverse alpha for polyval
#     period = np.polyval(beta[::-1], phi)  # Reverse beta for polyval

#     amplitude = np.maximum(amplitude, 0.0)
#     period = np.maximum(period, 72000.0)

#     phase = 2.0 * np.pi * (local_tod - 50400.0) / period

#     # Efficient multiple calculation
#     multiple = np.full_like(phase, 5e-9)
#     mask = np.abs(phase) < 1.57
#     phase_sq = phase * phase
#     multiple += mask * amplitude * (1.0 + phase_sq * (-0.5 + phase_sq / 24.0))

#     delay = SPEED_OF_LIGHT * slant_factor * multiple

#     # Return appropriate format
#     if is_scalar:
#         return delay.item()
#     else:
#         return delay.reshape(original_shape)


# def compute_saastamoinen_delay(
#     rx_pos, el, humidity=0.75, temperature_at_sea_level=15.0
# ):
#     """function from RTKlib: https://github.com/tomojitakasu/RTKLIB/blob/master/src/rtkcmn.c#L3362-3362
#         with no changes by way of laika: https://github.com/commaai/laika

#     Parameters
#     ----------
#     rx_pos : _type_
#         receiver ECEF position
#     el : _type_
#         elevation to emitter [rad]
#     humidity : float, optional
#         relative humidity, by default 0.75
#     temperature_at_sea_level : float, optional
#         temperature at sea level [C], by default 15.0

#     Returns
#     -------
#     _type_
#         sum of wet and dry tropospheric delay [m]
#     """
#     # TODO: clean this up
#     rx_pos_lla = ecef2geodetic(x=rx_pos[0], y=rx_pos[1], z=rx_pos[2])
#     if rx_pos_lla[2] < -1e3 or 1e4 < rx_pos_lla[2] or el <= 0:
#         return 0.0

#     hgt = 0.0 if rx_pos_lla.alt < 0.0 else rx_pos_lla.alt  # standard atmosphere

#     pres = 1013.25 * pow(1.0 - 2.2557e-5 * hgt, 5.2568)
#     temp = temperature_at_sea_level - 6.5e-3 * hgt + 273.16
#     e = 6.108 * humidity * np.exp((17.15 * temp - 4684.0) / (temp - 38.45))

#     # /* saastamoninen model */
#     z = np.pi / 2.0 - el
#     trph = (
#         0.0022768
#         * pres
#         / (1.0 - 0.00266 * np.cos(2.0 * rx_pos_lla.lat) - 0.00028 * hgt / 1e3)
#         / np.cos(z)
#     )
#     trpw = 0.002277 * (1255.0 / temp + 0.05) * e / np.cos(z)
#     return trph + trpw


def compute_saastamoinen_delay(
    rx_ecef: ArrayLike,
    elevation_rad: ArrayLike,
    relative_humidity: float = 0.75,
    sea_level_temperature_celsius: float = 15.0,
) -> np.ndarray:
    """
    Compute the total Saastamoinen tropospheric delay (wet + dry) for given
    receiver position(s) and satellite elevation angle(s).

    Parameters
    ----------
    receiver_ecef : ArrayLike, shape (3,) or (N, 3)
        Receiver position(s) in Earth-Centered Earth-Fixed coordinates [meters].
    elevation_rad : ArrayLike, shape () or (N,)
        Satellite elevation angle(s) above horizon, in radians.
    relative_humidity : float, default=0.75
        Relative humidity [0–1].
    sea_level_temperature_celsius : float, default=15.0
        Temperature at sea level in degrees Celsius.

    Returns
    -------
    total_delay_m : ndarray, shape (N,)
        Total tropospheric delay (meters). Returns zero for invalid positions
        (altitude below –1 000 m or above 10 000 m) or non-positive elevation.
    """
    pos_array = np.atleast_2d(rx_ecef)
    ele_array = np.atleast_1d(elevation_rad)
    num_epochs = max(pos_array.shape[0], ele_array.shape[0])

    receiver_positions = np.broadcast_to(pos_array, (num_epochs, 3))
    elevation_angles = np.broadcast_to(ele_array, (num_epochs,))

    total_delay_m = np.zeros(num_epochs, dtype=float)

    # Convert ECEF to geodetic coordinates {lat, lon, alt}
    geodetic_coords = np.array(
        ecef2geodetic(
            receiver_positions[:, 0], receiver_positions[:, 1], receiver_positions[:, 2]
        )
    ).transpose()

    latitudes = geodetic_coords[:, 0]
    altitudes_m = geodetic_coords[:, 2]

    # Determine valid data points: within altitude range and above horizon
    valid_data = (altitudes_m >= -1e3) & (altitudes_m <= 1e4) & (elevation_angles > 0)
    if not np.any(valid_data):
        return total_delay_m

    altitudes_nonneg = np.clip(altitudes_m[valid_data], 0.0, None)
    # Dry pressure model (hPa)
    surface_pressure_hpa = 1013.25 * (1.0 - 2.2557e-5 * altitudes_nonneg) ** 5.2568
    # Convert sea-level temperature + lapse rate to Kelvin
    temperature_kelvin = (
        sea_level_temperature_celsius - 6.5e-3 * altitudes_nonneg + 273.16
    )
    # Water vapor pressure (hPa)
    vapor_pressure_hpa = (
        6.108
        * relative_humidity
        * np.exp((17.15 * temperature_kelvin - 4684.0) / (temperature_kelvin - 38.45))
    )

    zenith_angle_rad = np.pi / 2.0 - elevation_angles[valid_data]
    # Dry delay in meters
    dry_delay_m = (
        0.0022768
        * surface_pressure_hpa
        / (
            1.0
            - 0.00266 * np.cos(2.0 * latitudes[valid_data])
            - 0.00028 * altitudes_nonneg / 1e3
        )
        / np.cos(zenith_angle_rad)
    )
    # Wet delay in meters
    wet_delay_m = (
        0.002277
        * (1255.0 / temperature_kelvin + 0.05)
        * vapor_pressure_hpa
        / np.cos(zenith_angle_rad)
    )

    total_delay_m[valid_data] = dry_delay_m + wet_delay_m
    return total_delay_m


def compute_carrier_to_noise(
    range: float,
    transmit_eirp: float,
    fcarrier: float,
    cn0_attenuation: float = 0,
    temperature: float = 290,
):
    ADDITIONAL_NOISE_FIGURE = 3  # [dB-Hz] cascaded + band-limiting/quantization noise

    wavelength = SPEED_OF_LIGHT / fcarrier  # [m]
    FSPL = 20 * np.log10(4 * np.pi * range / wavelength)  # [dB] free space path loss

    received_carrier_power = transmit_eirp - FSPL - cn0_attenuation  # [dBW]
    thermal_noise_density = 10 * np.log10(BOLTZMANN * temperature)  # [dBW/Hz]

    nominal_cn0 = received_carrier_power - thermal_noise_density  # [dB-Hz]
    cn0 = nominal_cn0 - ADDITIONAL_NOISE_FIGURE

    return cn0
