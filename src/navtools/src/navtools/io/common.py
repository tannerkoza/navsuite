"""contains common functions and classes for I/O such as decompression algorithms and downloaders"""

__all__ = ["decompress", "FileDownloader"]


import gzip
import os
import pathlib as pl
import shutil
import tarfile
import tempfile
import warnings
from datetime import datetime
from typing import Callable

import requests
import unlzw3

# custom types and function interfaces
DecompressionFunction = Callable[[pl.Path], pl.Path | list[pl.Path] | object]


# decompression
def decompress(
    compressed_file_path: str | os.PathLike,
) -> pl.Path | list[pl.Path] | object:
    """decompresses files with extensions indicated by VALID_COMPRESSIONS

    Parameters
    ----------
    compressed_file_path : str | os.PathLike
        path to compressed file

    Returns
    -------
    pl.Path | list
        path to single or multiple decompressed files

    Raises
    ------
    RuntimeError
        indicates unsupported compressed file type
    """

    path = pl.Path(compressed_file_path)

    compression_type = _match_compression_type(suffixes=path.suffixes)

    if compression_type is None:
        raise RuntimeError(
            f"the compression extension for {path.name} is currently not supported."
        )

    decompression_fn: DecompressionFunction = VALID_COMPRESSIONS[compression_type]
    decompressed_path = decompression_fn(path)

    return decompressed_path


def _decompress_unlzw(path: pl.Path) -> pl.Path:
    data = unlzw3.unlzw(inp=path)

    decompressed_path = _build_decompressed_path(path=path)
    with open(file=decompressed_path, mode="wb") as file:
        file.write(data)

    return decompressed_path


def _decompress_gzip(path: pl.Path) -> pl.Path:
    decompressed_path = _build_decompressed_path(path=path)

    with gzip.open(filename=path, mode="rb") as compressed_file:
        data = compressed_file.read()

        with open(file=decompressed_path, mode="wb") as file:
            file.write(data)

    return decompressed_path


def _decompress_tar(path: pl.Path) -> list[pl.Path]:
    file = tarfile.open(name=path)
    file.extractall(path=path.parent)
    file.close()

    decompressed_paths = [path.parent / name for name in file.getnames()]

    return decompressed_paths

    # ".zip": None,
    # ".7z": None,


VALID_COMPRESSIONS = {
    ".gz": _decompress_gzip,
    ".z": _decompress_unlzw,
    ".tar.gz": _decompress_tar,
}


def _match_compression_type(suffixes: list):
    str_suffixes = "".join(suffixes).lower()

    possible_compressions = [
        compression
        for compression in VALID_COMPRESSIONS.keys()
        if compression in str_suffixes
    ]

    if not possible_compressions:
        return None
    else:
        # returns largest string as substrings can be included with string comparison
        return max(possible_compressions)


def _build_decompressed_path(path: pl.Path):
    stem_path = path.parent / path.stem

    if len(path.suffixes) > 1:
        decompressed_path = stem_path.with_suffix(path.suffixes[0])
    else:
        decompressed_path = stem_path.with_suffix(".dec")  # .dec for decompressed

    return decompressed_path


class FileDownloader(object):
    TEMP_DIRECTORY_EXPIRATION_DAYS = 5

    def __init__(self, directory: str | os.PathLike | None = None):
        """a class used for downloading files from a URL and saving them to a specified or default local or temporary directory

        Parameters
        ----------
        directory : str | os.PathLike | None, optional
            directory to save downloaded files to, by default None
        """
        # setup
        if directory is None:
            temp_directory = pl.Path(tempfile.gettempdir())
            self.directory = temp_directory / "navtools"

        else:
            self.directory = pl.Path(directory).expanduser()

        # remove self.directory if not modified in TEMP_DIRECTORY_EXPIRATION_DAYS
        self._rm_expired_temp()

        # create or re-create directory
        self.directory.mkdir(parents=True, exist_ok=True)

        # attributes
        self._file_paths: list = []

    def download(
        self, url: str, nparents: int | None = None, reload: bool = False
    ) -> pl.Path:
        """downloads file from URL and saves to directory

        Parameters
        ----------
        url : str
            url to download from
        nparents : int | None, optional
            specifies the number of parent directories in URL to include in saved path, by default None
        reload : bool, optional
            determines whether existing file is re-downloaded, by default False

        Returns
        -------
        pl.Path
            path to downloaded file
        """

        self.current_url = pl.Path(url)
        write_path = self._build_write_path(nparents=nparents)

        if write_path.exists() and not reload:
            warnings.warn(
                message="requested file already exists and will not be updated. Set reload argument to True to re-download from requested url.",
                category=RuntimeWarning,
                stacklevel=2,
            )
            return write_path

        with open(file=write_path, mode="wb") as file:
            response = requests.get(url=url)
            file.write(response.content)

        return write_path

    def _build_write_path(self, nparents: int | None) -> pl.Path:
        if nparents is None:
            write_parent = self.directory
        else:
            max_nparents = len(self.current_url.parents)

            if nparents > 0 and nparents <= max_nparents:
                parent_names = reversed(
                    [parent.name for parent in self.current_url.parents[0:nparents]]
                )
                write_parent = self.directory.joinpath(*parent_names)
                write_parent.mkdir(parents=True, exist_ok=True)

            else:
                raise ValueError(
                    f"nparents must be greater than 0 or less than or equal to {max_nparents} for this url."
                )

        write_path = write_parent / self.current_url.name
        self._file_paths.append(write_path)

        return write_path

    def _rm_expired_temp(self):
        temp_directory = tempfile.gettempdir()
        directory_cp = os.path.commonprefix([temp_directory, self.directory])

        if (
            self.directory.exists() and directory_cp == temp_directory
        ):  # is self.directory temporary
            now = datetime.now()
            directory_mtime = datetime.fromtimestamp(self.directory.stat().st_mtime)

            elapsed_time = now - directory_mtime
            if elapsed_time.days > self.TEMP_DIRECTORY_EXPIRATION_DAYS:
                shutil.rmtree(self.directory)
