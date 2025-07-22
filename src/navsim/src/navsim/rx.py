import numpy as np
import numpy.typing as npt

from navtools.constants import SPEED_OF_LIGHT


def compute_pll_sigma(
    cn0: npt.ArrayLike,
    noise_bw: float = 2,
    T: float = 0.005,
    data_channel: bool = True,
):
    cn0 = 10 ** (np.asarray(cn0) / 10)  # Hz

    if data_channel:
        squaring_loss = 1 + (1 / (2 * T * cn0))
    else:
        squaring_loss = 1

    pll_sigma = (1 / 2 * np.pi) * np.sqrt((noise_bw / cn0) * squaring_loss)  # [cycles]

    return pll_sigma


def compute_fll_sigma(
    cn0: npt.ArrayLike,
    fcarrier: float,
    noise_bw: float = 2,
    T: float = 0.005,
    cn0_threshold: float = 22,
):
    cn0 = 10 ** (np.asarray(cn0) / 10)  # Hz
    cn0_threshold = 10 ** (cn0_threshold / 10)  # Hz
    carrier_lambda = SPEED_OF_LIGHT * (1 / fcarrier)

    f = np.where(cn0 < cn0_threshold, 2, 1)

    fll_sigma = (carrier_lambda / (2 * np.pi * T)) * np.sqrt(
        ((4 * f * noise_bw) / cn0) * (1 + (1 / (T * cn0)))
    )  # [m/s]

    return fll_sigma


def compute_dll_sigma(
    cn0: npt.ArrayLike,
    noise_bw: float = 0.1,
    front_end_bw: float = 1.7e7,
    fchip: float = 1.023e6,
    correlator_spacing: float = 0.5,
    T: float = 0.005,
    noncoherent: bool = True,
):
    cn0 = 10 ** (np.asarray(cn0) / 10)  # Hz
    tchip = 1 / fchip

    if correlator_spacing >= (np.pi * fchip / front_end_bw):
        if noncoherent:
            squaring_loss = 1 + (2 / (T * cn0 * (2 - correlator_spacing)))
        else:
            squaring_loss = 1

        dll_sigma = np.sqrt((noise_bw / (2 * cn0)) * correlator_spacing * squaring_loss)

    if correlator_spacing > (fchip / front_end_bw) and correlator_spacing < (
        np.pi * fchip / front_end_bw
    ):
        if noncoherent:
            squaring_loss = 1 + (2 / (T * cn0 * (2 - correlator_spacing)))
        else:
            squaring_loss = 1

        dll_sigma = np.sqrt(
            (noise_bw / (2 * cn0))
            * (
                (front_end_bw * tchip)
                / (np.pi - 1)
                * (correlator_spacing - (1 / (front_end_bw * tchip))) ** 2
            )
            * squaring_loss
        )

    if correlator_spacing <= (fchip / front_end_bw):
        if noncoherent:
            squaring_loss = 1 + (1 / (T * cn0))
        else:
            squaring_loss = 1

        dll_sigma = np.sqrt(
            (noise_bw / (2 * cn0)) * (1 / (front_end_bw * tchip)) * squaring_loss
        )

    return dll_sigma  # [m]
