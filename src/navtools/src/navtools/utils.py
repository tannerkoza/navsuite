import numpy as np
from numpy.typing import NDArray


def to_cartesian_series(array: NDArray) -> NDArray:
    if array.ndim != 1:
        ncols = np.asarray(array[0]).size

        if ncols != 3:
            array = array.transpose()

    return array
