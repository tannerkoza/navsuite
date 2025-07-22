__all__ = ["decompress", "FileDownloader"]


import asyncio
import datetime as dt
import gzip
import os
import pathlib as pl
import shutil
import tempfile
import traceback
from urllib.parse import urljoin, urlparse

from typing import Callable
import aiohttp
from tqdm.asyncio import tqdm_asyncio


def decompress(
    compressed_file_path: str | os.PathLike,
) -> pl.Path | list[pl.Path]:
    """
    Decompress files based on their extension.

    Parameters
    ----------
    compressed_file_path : str or os.PathLike
        Path to the compressed file.

    Returns
    -------
    pathlib.Path or list of pathlib.Path
        Path to the decompressed file or a list of paths if multiple files are extracted.

    Raises
    ------
    ValueError
        If the file extension is not supported or no decompression function is found.

    Examples
    --------
    >>> decompress("data.txt.gz")
    PosixPath('data.txt')
    """
    path = pl.Path(compressed_file_path)
    compression_type = _match_compression_type(path.suffixes)

    if compression_type is None:
        raise ValueError(f"Unsupported compression type for file: {path.name}")

    decompression_fn = VALID_COMPRESSIONS[compression_type]
    if decompression_fn is None:
        raise ValueError(f"No decompression function found for {compression_type}.")

    return decompression_fn(path)


def _decompress_gzip(path: pl.Path) -> pl.Path:
    """
    Decompress a .gz file.

    Parameters
    ----------
    path : pathlib.Path
        Path to the .gz file.

    Returns
    -------
    pathlib.Path
        Path to the decompressed file.
    """
    decompressed_path = _build_decompressed_path(path)
    with gzip.open(path, "rb") as f_in:
        with open(decompressed_path, "wb") as f_out:
            f_out.write(f_in.read())
    return decompressed_path


def _match_compression_type(suffixes: list[str]) -> Callable[[pl.Path], pl.Path] | None:
    """
    Match the file extension to a compression type.

    Parameters
    ----------
    suffixes : list of str
        List of file suffixes.

    Returns
    -------
    str or None
        Compression type if matched, else None.
    """
    str_suffixes = "".join(suffixes).lower()
    for ext, comp_type in VALID_COMPRESSIONS.items():
        if ext in str_suffixes:
            return comp_type
    return None


def _build_decompressed_path(path: pl.Path) -> pl.Path:
    """
    Build the path for the decompressed file.

    Parameters
    ----------
    path : pathlib.Path
        Path to the compressed file.

    Returns
    -------
    pathlib.Path
        Path to the decompressed file.
    """
    stem_path = path.parent / path.stem
    if len(path.suffixes) > 1:
        return stem_path.with_suffix(path.suffixes[0])
    return stem_path.with_suffix(".dec")


VALID_COMPRESSIONS = {
    ".gz": _decompress_gzip,
}


class FileDownloader(object):
    """
    A file downloader class that handles downloading files from URLs with caching.

    This class provides functionality to download files from URLs, with support for
    caching downloaded files to avoid re-downloading, automatic decompression,
    and concurrent downloads for improved performance.

    Parameters
    ----------
    directory : str, os.PathLike, or None, optional
        Directory to store downloaded files. If None, uses a temporary directory
        under the system temp path. Default is None.
    disable_warning : bool, optional
        Whether to disable warnings about existing files. Default is False.

    Attributes
    ----------
    TEMP_DIRECTORY_EXPIRATION_DAYS : int
        Number of days after which temporary directories are considered expired.

    Examples
    --------
    >>> downloader = FileDownloader()
    >>> path = downloader.download("https://example.com/data.txt")
    >>> paths = downloader.download(["https://example.com/file1.txt",
    ...                            "https://example.com/file2.txt"])
    """

    TEMP_DIRECTORY_EXPIRATION_DAYS = 1

    def __init__(
        self, directory: str | os.PathLike | None = None, disable_warning: bool = False
    ):
        # initialize attributes
        self._disable_warning = disable_warning

        # create directory path
        if directory is None:
            temp_path = pl.Path(tempfile.gettempdir())
            self._directory = temp_path / "navtools"

        else:
            self._directory = pl.Path(directory).expanduser()

        # remove self._directory if not modified in TEMP_DIRECTORY_EXPIRATION_DAYS
        self._remove_expired()

        # create or re-create directory
        self._directory.mkdir(parents=True, exist_ok=True)

    def download(
        self,
        url: str | list[str],
        url_parent_depth: int = 0,
        reload: bool = False,
        max_concurrent: int = 20,
        progress_desc: str = "Downloading File(s)",
    ) -> pl.Path | list[pl.Path]:
        """
        Download files from URLs with optional caching and decompression.

        Parameters
        ----------
        url : str or list of str
            URL or list of URLs to download.
        url_parent_depth : int, optional
            Number of parent directories from the URL path to include in the
            local file structure. Default is 0.
        reload : bool, optional
            Whether to re-download files even if they already exist locally.
            Default is False.
        max_concurrent : int, optional
            Maximum number of concurrent downloads. Default is 20.
        progress_desc : str, optional
            Description to show in the progress bar. Default is "Downloading File(s)".

        Returns
        -------
        pathlib.Path or list of pathlib.Path
            Path to downloaded file (if single URL) or list of paths (if multiple URLs).
            Files are automatically decompressed if they have supported compression formats.

        Examples
        --------
        >>> downloader = FileDownloader()
        >>> # Download single file
        >>> path = downloader.download("https://example.com/data.txt.gz")
        >>> # Download multiple files
        >>> paths = downloader.download([
        ...     "https://example.com/file1.txt",
        ...     "https://example.com/file2.txt"
        ... ])
        >>> # Download with directory structure preservation
        >>> path = downloader.download("https://example.com/data/file.txt",
        ...                          url_parent_depth=1)
        """
        urls = [url] if isinstance(url, str) else url  # ensure urls is list

        # create potential file output paths for each url
        possible_paths = [
            path_from_url(
                url=url, parent_path=self._directory, url_parent_depth=url_parent_depth
            )
            for url in urls
        ]

        # sort possible paths into exisiting and downloadable paths
        self._sort_possible_paths(urls=urls, output_paths=possible_paths, reload=reload)

        # try and fetch downloadble urls, extend succesful downloads
        if self._downloadable_paths:
            self._exisiting_paths.extend(
                asyncio.run(
                    fetch_files_async(
                        urls=self._urls,
                        output_paths=self._downloadable_paths,
                        max_concurrent=max_concurrent,
                        progress_desc=progress_desc,
                    )
                )
            )

        self._output_paths = [
            (
                decompress(compressed_file_path=path)
                if path.suffix in VALID_COMPRESSIONS
                else path
            )
            for path in self._exisiting_paths
        ]

        if len(self._output_paths) == 1:
            return self._output_paths[0]

        return self._output_paths

    def _sort_possible_paths(
        self, urls: list[str], output_paths: list[pl.Path], reload: bool
    ):
        """
        Sort possible paths into existing and downloadable paths.

        Parameters
        ----------
        urls : list of str
            List of URLs to download.
        output_paths : list of pathlib.Path
            List of potential output paths for the URLs.
        reload : bool
            Whether to reload existing files.
        """
        self._urls = []
        self._downloadable_paths = []
        self._exisiting_paths = []

        if reload:
            self._urls = urls
            self._downloadable_paths = output_paths

            return

        for url, path in zip(urls, output_paths):
            if path.exists():
                self._exisiting_paths.append(path)

                if not self._disable_warning:
                    print(
                        f"The file {path} already exists locally. "
                        "Assign reload=True to re-download from requested url."
                    )

                continue

            self._urls.append(url)
            self._downloadable_paths.append(path)

    def _remove_expired(self):
        """
        Remove expired temporary directories.

        Removes the download directory if it's located in the system temporary
        directory and hasn't been modified within TEMP_DIRECTORY_EXPIRATION_DAYS.
        """
        temp_path = tempfile.gettempdir()
        directory_common_prefix = os.path.commonprefix([temp_path, self._directory])

        # check if self._directory temporary
        if self._directory.exists() and directory_common_prefix == temp_path:
            now = dt.datetime.now()
            directory_mtime = dt.datetime.fromtimestamp(self._directory.stat().st_mtime)
            elapsed_time = now - directory_mtime

            # remove self._directory in not modified in certain number of days
            if elapsed_time.days > FileDownloader.TEMP_DIRECTORY_EXPIRATION_DAYS:
                shutil.rmtree(self._directory)


async def fetch_files_async(
    urls: str | list[str],
    output_paths: pl.Path | list[pl.Path],
    max_concurrent: int = 20,
    progress_desc: str = "Downloading File(s)",
):
    """
    Fetch files asynchronously and save directly to disk.

    Parameters
    ----------
    urls : str or list of str
        URL or list of URLs to fetch.
    output_paths : pathlib.Path or list of pathlib.Path
        Output path or list of paths where files should be saved.
    max_concurrent : int, optional
        Maximum number of concurrent downloads. Default is 20.
    progress_desc : str, optional
        Description to show in the progress bar. Default is "Downloading File(s)".

    Returns
    -------
    list of pathlib.Path or None
        List of saved file paths. Returns None for failed downloads.

    Raises
    ------
    RuntimeError
        If the length of urls and output_paths do not match.

    Examples
    --------
    >>> import asyncio
    >>> import pathlib as pl
    >>> urls = ["https://example.com/file1.txt", "https://example.com/file2.txt"]
    >>> paths = [pl.Path("file1.txt"), pl.Path("file2.txt")]
    >>> saved_files = asyncio.run(fetch_files_async(urls, paths))
    """

    url_list = [urls] if isinstance(urls, str) else urls
    output_path_list = (
        [output_paths] if isinstance(output_paths, pl.Path) else output_paths
    )

    if len(url_list) != len(output_path_list):
        raise RuntimeError(
            "The urls and output_paths arguments are not the same length."
        )

    connector = aiohttp.TCPConnector(limit=max_concurrent)
    async with aiohttp.ClientSession(connector=connector) as session:
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_file(url, save_path):
            async with semaphore:
                try:
                    async with session.get(
                        url, timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        response.raise_for_status()

                        # Ensure parent directories exist
                        save_path.parent.mkdir(parents=True, exist_ok=True)

                        # Save content to file
                        with open(save_path, "wb") as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)

                        return save_path

                except Exception as e:
                    print(f"There was an error fetching {url or 'unknown URL'}: {e}")
                    traceback.print_exc()

                    return

        # Create tasks for all files
        tasks = [fetch_file(url, path) for url, path in zip(url_list, output_path_list)]

        # Execute all tasks
        saved_files = await tqdm_asyncio.gather(
            *tasks, total=len(tasks), desc=progress_desc
        )

    return saved_files


def path_from_url(url: str, parent_path: pl.Path, url_parent_depth: int = 0):
    """
    Generate a local file path from a URL.

    Parameters
    ----------
    url : str
        The URL to extract the path from.
    parent_path : pathlib.Path
        The parent directory where the file should be saved.
    url_parent_depth : int, optional
        Number of parent directories from the URL path to include in the
        local path structure. Default is 0.

    Returns
    -------
    pathlib.Path
        The constructed local file path.

    Examples
    --------
    >>> import pathlib as pl
    >>> url = "https://example.com/data/files/document.txt"
    >>> parent = pl.Path("/downloads")
    >>> path = path_from_url(url, parent, url_parent_depth=1)
    >>> print(path)
    /downloads/files/document.txt
    """
    url_path = pl.Path(urlparse(url).path)

    if url_parent_depth > 0:
        output_parent = add_parents(
            parent_path=parent_path, base_path=url_path, nparents=url_parent_depth
        )
    else:
        output_parent = parent_path

    output_path = output_parent / url_path.name

    return output_path


def add_parents(parent_path: pl.Path, base_path: pl.Path, nparents: int) -> pl.Path:
    """
    Add parent directories from base_path to parent_path.

    Parameters
    ----------
    parent_path : pathlib.Path
        The base parent path to extend.
    base_path : pathlib.Path
        The path from which to extract parent directory names.
    nparents : int
        Number of parent directories to add from base_path.

    Returns
    -------
    pathlib.Path
        The extended parent path with additional parent directories.

    Raises
    ------
    ValueError
        If nparents is not greater than 0 or exceeds the number of available
        parent directories in base_path.

    Examples
    --------
    >>> import pathlib as pl
    >>> parent = pl.Path("/downloads")
    >>> base = pl.Path("/data/files/document.txt")
    >>> result = add_parents(parent, base, 2)
    >>> print(result)
    /downloads/data/files
    """
    max_nparents = len(base_path.parents)

    if nparents > 0 and nparents <= max_nparents:
        parent_names = reversed(
            [parent.name for parent in base_path.parents[0:nparents]]
        )
        parent_path = parent_path.joinpath(*parent_names)

        return parent_path

    else:
        raise ValueError(
            f"nparents ({nparents}) must be greater than 0 "
            f"and less than or equal to {max_nparents} "
            f"for this path: {base_path}"
        )


if __name__ == "__main__":
    api_url = "https://api.starlink.com/public-files/ephemerides/"
    file_manifest_url = api_url + "MANIFEST.txt"

    output_directory = pl.Path("./starlink")
    downloader = FileDownloader(directory=output_directory)
    file_manifest = downloader.download(url=file_manifest_url, reload=True)

    with open(file=file_manifest, mode="r") as f:
        eph_files = f.read().splitlines()

    urls = [urljoin(api_url, file) for file in eph_files[:100]]
    file_paths = downloader.download(url=urls, url_parent_depth=1, reload=True)

    pass
