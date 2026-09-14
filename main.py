from __future__ import annotations

import html
import sys
from pathlib import Path
from urllib.parse import quote


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# The repository root to generate indexes for.
#
# Usage:
#   python generate_index.py [DIRECTORY]
#
# If no directory is supplied, the current working directory is used.
ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()

# Name of the generated index file.
INDEX_NAME = "index.html"
ignore_path = ["venv"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def url_encode(name: str) -> str:
    """
    Encode a file or directory name for use in a URL.

    '/' is not allowed here because this function only receives a single
    path component.
    """
    return quote(name, safe="")


def display_name(path: Path) -> str:
    """
    Return the name displayed in the index.

    Directories get a trailing slash to make them visually distinguishable.
    """
    if path.is_dir():
        return f"{path.name}/"

    return path.name


def href_for(path: Path) -> str:
    """
    Return a relative href for an entry inside its parent directory.
    """
    encoded_name = url_encode(path.name)

    if path.is_dir():
        return f"{encoded_name}/"

    return encoded_name


def relative_directory_path(directory: Path) -> str:
    """
    Return the directory path relative to ROOT, using POSIX separators.
    """
    relative = directory.relative_to(ROOT)

    if relative == Path("."):
        return "/"

    return f"/{relative.as_posix()}/"


def generate_html(directory: Path) -> str:
    """
    Generate an index.html document for the given directory.
    """
    entries = [
        entry
        for entry in directory.iterdir()
        if entry.name != INDEX_NAME and not entry.name.startswith(".") and entry.name not in ignore_path and (directory != ROOT or entry.is_dir())
    ]

    directories = sorted(
        (entry for entry in entries if entry.is_dir()),
        key=lambda path: path.name.casefold(),
    )

    files = sorted(
        (entry for entry in entries if entry.is_file()),
        key=lambda path: path.name.casefold(),
    )

    current_path = relative_directory_path(directory)

    lines = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '    <meta charset="UTF-8">',
        '    <meta name="viewport" content="width=device-width, initial-scale=1">',
        f"    <title>Index of {html.escape(current_path)}</title>",
        "    <style>",
        "        body {",
        "            font-family: monospace;",
        "            max-width: 1000px;",
        "            margin: 40px auto;",
        "            padding: 0 20px;",
        "            color: #222;",
        "            background: #fff;",
        "        }",
        "",
        "        h1 {",
        "            font-size: 1.5rem;",
        "            overflow-wrap: anywhere;",
        "        }",
        "",
        "        ul {",
        "            list-style: none;",
        "            padding: 0;",
        "        }",
        "",
        "        li {",
        "            padding: 4px 0;",
        "        }",
        "",
        "        a {",
        "            text-decoration: none;",
        "            color: #0969da;",
        "        }",
        "",
        "        a:hover {",
        "            text-decoration: underline;",
        "        }",
        "    </style>",
        "</head>",
        "<body>",
        f"    <h1>Index of {html.escape(current_path)}</h1>",
        "    <ul>",
    ]

    # Parent directory.
    if directory != ROOT:
        lines.append('        <li><a href="../">../</a></li>')

    # Directories first.
    for entry in directories:
        href = href_for(entry)
        label = html.escape(display_name(entry))

        lines.append(
            f'        <li><a href="{html.escape(href, quote=True)}">'
            f"📁 {label}</a></li>"
        )

    # Files afterwards.
    for entry in files:
        href = href_for(entry)
        label = html.escape(display_name(entry))

        lines.append(
            f'        <li><a href="{html.escape(href, quote=True)}">'
            f"📄 {label}</a></li>"
        )

    lines.extend(
        [
            "    </ul>",
            "</body>",
            "</html>",
            "",
        ]
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if not ROOT.exists():
        raise SystemExit(f"Directory does not exist: {ROOT}")

    if not ROOT.is_dir():
        raise SystemExit(f"Path is not a directory: {ROOT}")

    # Generate an index for the root directory and every subdirectory.
    directories = [ROOT]

    for path in ROOT.rglob("*"):
        if path.is_dir() and not path.name.startswith(".") and path.name not in ignore_path and (path != ROOT or path.is_dir()):
            directories.append(path)

    for directory in directories:
        index_file = directory / INDEX_NAME
        index_file.write_text(
            generate_html(directory),
            encoding="utf-8",
            newline="\n",
        )

        print(f"Generated: {index_file}")


if __name__ == "__main__":
    main()
