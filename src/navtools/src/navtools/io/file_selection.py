__all__ = ["select_file"]

import html
import os
import pathlib as pl
from datetime import datetime

from prompt_toolkit.application import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Dimension, HSplit, Layout, VSplit, Window
from prompt_toolkit.layout.containers import DynamicContainer
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import Frame

PROJECT_PATH = pl.Path(__file__).parents[2]
CONFIG_PATH = PROJECT_PATH / "config"


def _list_files(directory: str) -> list[str]:
    """
    List all files (non-recursively) in a directory, sorted alphabetically.

    Parameters
    ----------
    directory : str
        Path to the directory to list files from.

    Returns
    -------
    list[str]
        Sorted list of filenames in the directory.
    """
    return sorted(
        [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    )


def _get_file_info(path: str) -> dict:
    """
    Get file information including size and modification time.

    Parameters
    ----------
    path : str
        Path to the file.

    Returns
    -------
    dict
        Dictionary containing file size and modification time.
    """
    try:
        stat = os.stat(path)
        size = stat.st_size
        mtime = datetime.fromtimestamp(stat.st_mtime)

        # Format file size
        if size < 1024:
            size_str = f"{size}B"
        elif size < 1024 * 1024:
            size_str = f"{size / 1024:.1f}KB"
        else:
            size_str = f"{size / (1024 * 1024):.1f}MB"

        return {"size": size_str, "modified": mtime.strftime("%Y-%m-%d %H:%M")}
    except Exception:
        return {"size": "N/A", "modified": "N/A"}


def _preview_file(path: str, lines: int = 30) -> str:
    """
    Read the first few lines of a file for preview.

    Parameters
    ----------
    path : str
        Path to the file to preview.
    lines : int, optional
        Number of lines to read from the start of the file, by default 20.

    Returns
    -------
    str
        The first `lines` lines of the file content or an error message.
    """
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content_lines = f.readlines()[:lines]

        if not content_lines:
            return "File is empty or contains only whitespace."

        # Join lines and ensure we don't have excessive whitespace
        content = "".join(content_lines)

        # If content is only whitespace, return a message
        if not content.strip():
            return "File is empty or contains only whitespace."

        return content

    except Exception as e:
        return f"❌ Error reading file: {e}"


def _is_binary_file(path: str) -> bool:
    """
    Check if a file is binary by looking for null bytes in the first 1024 bytes.

    Parameters
    ----------
    path : str
        Path to the file to check.

    Returns
    -------
    bool
        True if the file appears to be binary, False otherwise.
    """
    try:
        with open(path, "rb") as f:
            chunk = f.read(1024)
            return b"\x00" in chunk
    except Exception:
        return True  # Assume binary if we can't read it


def select_file(directory: str, title: str = "File Selection") -> pl.Path | None:
    """
    Interactive CLI file selector using prompt_toolkit with enhanced styling.

    Displays a file list from the given directory and a preview pane of the
    selected file. Navigation is via up/down arrow keys. Enter selects a file,
    Ctrl-Q exits without selection.

    Parameters
    ----------
    directory : str
        Directory to select files from.
    title : str, optional
        Title to display in the title bar, by default "File selector".

    Returns
    -------
    pl.Path or None
        The path to the selected file as a pathlib.Path object,
        or None if no selection was made or directory is invalid.
    """
    if not os.path.isdir(directory):
        print(f"❌ Directory does not exist: {directory}")
        return None

    files = _list_files(directory)
    if not files:
        print("📁 No files in the directory.")
        return None

    selected = [files[0]]  # mutable container to hold current selection
    kb = KeyBindings()

    @kb.add("c-q")
    def _exit_app(event):
        """Exit app without selection on Ctrl-Q."""
        event.app.exit(result=None)

    @kb.add("enter")
    def _enter_app(event):
        """Exit app and return current selection on Enter."""
        event.app.exit(result=selected[0])

    @kb.add("down")
    def _move_down(event):
        """Move selection down in the file list."""
        idx = files.index(selected[0])
        if idx < len(files) - 1:
            selected[0] = files[idx + 1]

    @kb.add("up")
    def _move_up(event):
        """Move selection up in the file list."""
        idx = files.index(selected[0])
        if idx > 0:
            selected[0] = files[idx - 1]

    def _get_file_icon(filename: str) -> str:
        """
        Get appropriate icon for file type.

        Parameters
        ----------
        filename : str
            The name of the file.

        Returns
        -------
        str
            Unicode emoji icon representing the file type.
        """
        ext = os.path.splitext(filename)[1].lower()
        icon_map = {
            ".py": "🐍",
            ".js": "📜",
            ".html": "🌐",
            ".css": "🎨",
            ".json": "📋",
            ".xml": "📄",
            ".md": "📝",
            ".txt": "📄",
            ".log": "📊",
            ".yaml": "🔧",
            ".yml": "🔧",
            ".toml": "🔧",
            ".ini": "🔧",
            ".cfg": "🔧",
            ".conf": "🔧",
        }
        return icon_map.get(ext, "📄")

    def _file_list_control() -> FormattedTextControl:
        """
        Create a FormattedTextControl showing the file list with current selection highlighted.

        Returns
        -------
        FormattedTextControl
            A control that displays the file list with icons, metadata, and highlighting.
        """

        def get_file_list():
            lines = []
            for f in files:
                icon = _get_file_icon(f)
                file_info = _get_file_info(os.path.join(directory, f))

                # Escape special characters for HTML
                escaped_filename = html.escape(f)
                escaped_size = html.escape(file_info["size"])
                escaped_modified = html.escape(file_info["modified"])

                if f == selected[0]:
                    # Highlighted selection with gradient-like effect
                    line = f'<style bg="#2D5AA0" fg="#E8F4FD">▶ {icon} {escaped_filename:<30} <style fg="#B8D4F0">{escaped_size:<8} {escaped_modified}</style></style>'
                else:
                    line = f'<style fg="#A0A0A0">  {icon} | <style fg="#E0E0E0">{escaped_filename:<30}</style> <style fg="#808080">{escaped_size:<8} {escaped_modified}</style></style>'
                lines.append(line)

            return HTML("\n".join(lines))

        return FormattedTextControl(
            text=get_file_list,
            focusable=True,
            key_bindings=kb,
        )

    def _preview_control() -> FormattedTextControl:
        """
        Create a FormattedTextControl showing a preview of the selected file content.

        Returns
        -------
        FormattedTextControl
            A control that displays a preview of the currently selected file.
        """

        def get_preview():
            file_path = os.path.join(directory, selected[0])

            # Check if file is binary
            if _is_binary_file(file_path):
                return HTML(
                    '<style fg="#FFA500">📦 binary file - no preview available</style>'
                )

            # Get file content
            content = _preview_file(file_path)

            # Handle error messages
            if content.startswith("❌"):
                escaped_content = html.escape(content)
                return HTML(f'<style fg="#FF6B6B">{escaped_content}</style>')

            # Handle empty file message
            if content.strip() == "File is empty or contains only whitespace.":
                return HTML(
                    '<style fg="#808080">📄 File is empty or contains only whitespace</style>'
                )

            # Process the content for better display
            lines = content.split("\n")
            processed_lines = []

            for i, line in enumerate(lines):
                # Escape HTML in the line
                escaped_line = html.escape(line)

                # Add line numbers for better readability
                line_num = f"{i + 1:>3}"

                # Handle empty lines
                if not line.strip():
                    processed_lines.append(f'<style fg="#404040">{line_num}</style> ')
                else:
                    # Add subtle line numbering
                    processed_lines.append(
                        f'<style fg="#606060">{line_num}</style> <style fg="#E0E0E0">{escaped_line}</style>'
                    )

            # Join the processed lines
            preview_text = "\n".join(processed_lines)

            return HTML(preview_text)

        return FormattedTextControl(
            text=get_preview,
            focusable=False,
        )

    def _create_title_bar() -> Window:
        """
        Create a centered title bar window with modern styling.

        Returns
        -------
        Window
            A window containing the centered title bar with appropriate styling.
        """

        def get_centered_title():
            try:
                width = get_app().output.get_size().columns
            except Exception:
                width = 80  # fallback width

            # Use the custom title parameter
            title_text = title
            pad = max(0, (width - len(title_text)) // 2)
            return HTML(
                f'<style bg="#1E3A8A" fg="#F1F5F9">{" " * pad}{title_text}</style>'
            )

        return Window(
            content=FormattedTextControl(get_centered_title),
            height=1,
            style="bg:#1E3A8A",
            always_hide_cursor=True,
        )

    def _create_status_bar() -> Window:
        """
        Create a status bar with helpful information.

        Returns
        -------
        Window
            A window containing the status bar with directory name, file count,
            and navigation instructions.
        """

        def get_status_text():
            try:
                width = get_app().output.get_size().columns
            except Exception:
                width = 80

            current_idx = files.index(selected[0]) + 1
            total_files = len(files)

            left_text = f"[D] {os.path.basename(directory)}"
            center_text = f"File {current_idx}/{total_files}"
            right_text = "↑↓ Navigate | Enter Select | Ctrl+Q Exit"

            # Calculate spacing
            used_space = len(left_text) + len(center_text) + len(right_text)
            available_space = width - used_space

            if available_space > 0:
                left_pad = available_space // 2
                right_pad = available_space - left_pad
                status_line = f"{left_text}{' ' * left_pad}{center_text}{' ' * right_pad}{right_text}"
            else:
                status_line = f"{left_text} | {center_text} | {right_text}"

            return HTML(f'<style bg="#374151" fg="#D1D5DB">{status_line}</style>')

        return Window(
            content=FormattedTextControl(get_status_text),
            height=1,
            style="bg:#374151",
            always_hide_cursor=True,
        )

    def _create_info_panel() -> Window:
        """
        Create an info panel showing details about the selected file.

        Returns
        -------
        Window
            A window containing detailed information about the currently
            selected file including name, size, modification time, and path.
        """

        def get_info_text():
            file_path = os.path.join(directory, selected[0])
            file_info = _get_file_info(file_path)

            # Escape special characters for HTML
            escaped_filename = html.escape(selected[0])
            escaped_size = html.escape(file_info["size"])
            escaped_modified = html.escape(file_info["modified"])
            escaped_path = html.escape(file_path)

            # Add file type information
            ext = os.path.splitext(selected[0])[1].lower()
            file_type = ext[1:].upper() if ext else "Unknown"

            # Check if binary
            is_binary = _is_binary_file(file_path)
            file_nature = "Binary" if is_binary else "Text"

            info_lines = [
                '<style fg="#60A5FA">File Details</style>',
                "",
                f'<style fg="#A3E635">Name:</style> <style fg="#E5E7EB">{escaped_filename}</style>',
                f'<style fg="#A3E635">Type:</style> <style fg="#E5E7EB">{file_type} ({file_nature})</style>',
                f'<style fg="#A3E635">Size:</style> <style fg="#E5E7EB">{escaped_size}</style>',
                f'<style fg="#A3E635">Modified:</style> <style fg="#E5E7EB">{escaped_modified}</style>',
                "",
                '<style fg="#FCD34D">Full Path:</style>',
                f'<style fg="#9CA3AF">{escaped_path}</style>',
            ]

            return HTML("\n".join(info_lines))

        return Window(
            content=FormattedTextControl(get_info_text),
            height=9,  # Fixed height for info panel
            style="bg:#111827",
            always_hide_cursor=True,
        )

    def _get_root_container() -> HSplit:
        """
        Build the main layout container with modern styling and better organization.

        Returns
        -------
        HSplit
            The root container with title bar, main content area (files, info,
            preview), and status bar arranged vertically.
        """
        try:
            size = get_app().output.get_size()
            rows = size.rows
        except Exception:
            rows = 24

        # Calculate heights - reserve space for title bar (1) and status bar (1)
        available_height = rows - 2

        # Info panel has fixed content height of 9
        info_content_height = 9

        # Files list gets the remaining height after accounting for info panel
        # Account for frame borders: each frame adds 2 lines (top and bottom border)
        files_content_height = (
            available_height - info_content_height - 4
        )  # 4 = 2 frames × 2 borders each
        files_content_height = max(5, files_content_height)  # Minimum height

        title_bar = _create_title_bar()
        status_bar = _create_status_bar()
        info_panel = _create_info_panel()

        # Create the left side HSplit first so we can use it for height calculation
        left_side = HSplit(
            [
                Frame(
                    Window(
                        _file_list_control(),
                        height=Dimension.exact(files_content_height),
                    ),
                    title="Files",
                    style="bg:#1F2937",
                ),
                Frame(info_panel, title="Info.", style="bg:#1F2937"),
            ],
            width=Dimension(max=50),
        )

        # Create main content area with side-by-side layout
        # The preview should have no explicit height - it will naturally match the left side
        main_content = VSplit(
            [
                left_side,
                Frame(
                    Window(
                        _preview_control(),
                        wrap_lines=True,
                    ),
                    title="Preview",
                    style="bg:#1F2937",
                ),
            ]
        )

        return HSplit(
            [
                title_bar,
                main_content,
                status_bar,
            ]
        )

    layout = Layout(DynamicContainer(_get_root_container))
    app = Application(layout=layout, key_bindings=kb, full_screen=True)
    result = app.run()
    return pl.Path(directory) / result if result else None


if __name__ == "__main__":
    # Example usage with custom titles
    result = select_file(".", "My Custom File Selector")
    if result:
        print(f"✅ Selected file: {result}")
    else:
        print("❌ No file selected")

    # Or with default title
    # result = select_file(".")
