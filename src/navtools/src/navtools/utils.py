import itertools

import numpy as np
from numpy.typing import NDArray


def to_cartesian_series(array: NDArray) -> NDArray:
    array = np.atleast_2d(array)

    if array.ndim != 1:
        ncols = np.asarray(array[0]).size

        if ncols != 3:
            array = array.transpose()

    return array


def ragged_to_array(ragged: list, pad_value: any = np.nan) -> NDArray:
    # pad missing elements after tranposing list
    transposed = list(itertools.zip_longest(*ragged, fillvalue=pad_value))
    array = np.array(transposed).T  # transpose to original orientation

    return array


def find_axis(arr: NDArray, axis_length: int) -> int | None:
    return next((i for i, dim in enumerate(arr.shape) if dim == axis_length), None)
