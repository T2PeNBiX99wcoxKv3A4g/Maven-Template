from __future__ import annotations

import argparse
import datetime
import html
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote
from jinja2 import Environment, FileSystemLoader, select_autoescape

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

INDEX_NAME = "index.html"
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
TEMPLATE_NAME = "maven_directory.html"

# Default directories and file patterns to ignore completely
IGNORE_DIRS = {
    "venv",
    ".venv",
    "env",
    ".env",
    "templates",
    "_templates",
    ".git",
    ".github",
    ".idea",
    ".junie",
    ".vscode",
    "__pycache__",
    ".gradle",
    "build",
    "out",
    "dist",
    "target",
    "tests",
    "test",
}

IGNORE_FILES = {
    "main.py",
    "generate_index.py",
    "pyproject.toml",
    "requirements.txt",
    "poetry.lock",
    "uv.lock",
    ".gitignore",
    ".gitattributes",
    "README.md",
    "LICENSE",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_ignored_dir(path: Path, root: Path | None = None) -> bool:
    """Check if a directory should be excluded from index generation."""
    if path.name.startswith("."):
        return True
    if path.name in IGNORE_DIRS:
        return True
    if root is not None:
        try:
            rel_parts = path.resolve().relative_to(root.resolve()).parts
            for part in rel_parts:
                if part.startswith(".") or part in IGNORE_DIRS:
                    return True
        except ValueError:
            pass
    return False


def is_ignored_file(path: Path, directory: Path, root: Path | None = None) -> bool:
    """Check if a file should be excluded from directory listing."""
    if path.name == INDEX_NAME:
        return True
    if path.name.startswith("."):
        return True
    if path.name.endswith(".py") or path.name.endswith(".pyc"):
        return True
    if root is not None:
        if directory.resolve() == root.resolve() and path.name in IGNORE_FILES:
            return True
    else:
        if path.name in IGNORE_FILES:
            return True
    return False


def format_file_size(size_bytes: int) -> str:
    """Convert bytes to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    for unit in ["KB", "MB", "GB", "TB"]:
        size_bytes /= 1024.0
        if size_bytes < 1024.0 or unit == "TB":
            return f"{size_bytes:.2f} {unit}"
    return f"{size_bytes:.2f} TB"


def format_timestamp(ts: float) -> str:
    """Format file modification timestamp."""
    dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def url_encode(name: str) -> str:
    """Encode path component for URL."""
    return quote(name, safe="")


def href_for(path: Path) -> str:
    """Return URL-safe relative href."""
    encoded_name = url_encode(path.name)
    if path.is_dir():
        return f"{encoded_name}/"
    return encoded_name


def relative_directory_path(directory: Path, root: Path) -> str:
    """Return POSIX path relative to root with leading and trailing slash."""
    try:
        relative = directory.resolve().relative_to(root.resolve())
    except ValueError:
        return "/"

    if relative == Path("."):
        return "/"
    return f"/{relative.as_posix()}/"


def get_file_icon_and_badge(filename: str) -> tuple[str, str | None, str | None]:
    """Return (emoji, badge_text, badge_class) for a given filename."""
    lower = filename.lower()
    if lower.endswith((".jar", ".war", ".aar")):
        ext = lower.split(".")[-1].upper()
        return "📦", ext, "badge-jar"
    if lower.endswith(".pom"):
        return "📄", "POM", "badge-pom"
    if lower.endswith((".xml", ".json", ".properties", ".yaml", ".yml")):
        ext = lower.split(".")[-1].upper()
        return "⚙️", ext, "badge-xml"
    if lower.endswith((".sha1", ".sha256", ".sha512", ".md5")):
        ext = lower.split(".")[-1].upper()
        return "🔏", ext, "badge-hash"
    if lower.endswith((".asc", ".sig")):
        return "🔏", "GPG", "badge-hash"
    if lower.endswith((".zip", ".tar.gz", ".tar", ".gz", ".7z")):
        return "🗜️", "ZIP", "badge-jar"
    if lower.endswith((".txt", ".md", ".log", ".html", ".htm")):
        return "📜", None, None
    return "📄", None, None


def extract_maven_coords(directory: Path, root: Path | None = None) -> dict[str, str] | None:
    """
    Attempt to extract Maven coordinates (groupId, artifactId, version)
    from pom.xml or directory hierarchy.
    """
    try:
        # Check if there is a .pom file in the directory
        pom_files = list(directory.glob("*.pom"))
        if pom_files:
            pom_path = pom_files[0]
            try:
                tree = ET.parse(pom_path)
                root_elem = tree.getroot()
                # Remove namespaces if present
                ns = ""
                if root_elem.tag.startswith("{"):
                    ns = root_elem.tag.split("}")[0] + "}"

                def find_text(elem, tag):
                    node = elem.find(f"{ns}{tag}")
                    return node.text.strip() if node is not None and node.text else None

                group_id = find_text(root_elem, "groupId")
                artifact_id = find_text(root_elem, "artifactId")
                version = find_text(root_elem, "version")

                # Fallback to parent group / version if not directly specified
                parent = root_elem.find(f"{ns}parent")
                if parent is not None:
                    if not group_id:
                        group_id = find_text(parent, "groupId")
                    if not version:
                        version = find_text(parent, "version")

                if group_id and artifact_id and version:
                    return {
                        "groupId": group_id,
                        "artifactId": artifact_id,
                        "version": version,
                    }
            except Exception:
                pass

        # Fallback to directory structure heuristic: .../<groupId-parts>/<artifactId>/<version>
        if root is not None:
            rel = directory.resolve().relative_to(root.resolve())
            parts = rel.parts
            if len(parts) >= 3:
                version = parts[-1]
                artifact_id = parts[-2]
                group_id = ".".join(parts[:-2])
                # Check if directory has any jar or pom
                has_artifacts = any(
                    f.is_file() and f.suffix in {".jar", ".pom", ".aar", ".war"}
                    for f in directory.iterdir()
                )
                if has_artifacts:
                    return {
                        "groupId": group_id,
                        "artifactId": artifact_id,
                        "version": version,
                    }
    except Exception:
        pass

    return None


def generate_breadcrumbs(directory: Path, root: Path) -> list[dict[str, str]]:
    """Generate breadcrumb navigation links."""
    dir_res = directory.resolve()
    root_res = root.resolve()
    if dir_res == root_res:
        return [{"name": "~ (root)", "href": "#"}]

    try:
        relative = dir_res.relative_to(root_res)
        parts = relative.parts
    except ValueError:
        return [{"name": directory.name, "href": "#"}]

    breadcrumbs = []

    # Calculate relative hops back to root
    total_hops = len(parts)

    root_href = "../" * total_hops
    breadcrumbs.append({"name": "~ (root)", "href": root_href})

    for idx, part in enumerate(parts):
        hops_up = total_hops - (idx + 1)
        if hops_up > 0:
            href = "../" * hops_up
        else:
            href = "#"
        breadcrumbs.append({"name": part, "href": href})

    return breadcrumbs


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

def setup_template_env(template_dir: Path | None = None) -> Environment:
    """Setup Jinja2 template environment."""
    tpl_dir = template_dir or TEMPLATE_DIR
    if not tpl_dir.exists():
        tpl_dir.mkdir(parents=True, exist_ok=True)

    template_file = tpl_dir / TEMPLATE_NAME
    if not template_file.exists():
        raise FileNotFoundError(f"Template file not found: {template_file}")

    return Environment(
        loader=FileSystemLoader(str(tpl_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )


def generate_html(env: Environment, directory: Path, root: Path | None = None) -> str:
    """Generate an index.html string for the given directory."""
    if root is None:
        root = directory

    template = env.get_template(TEMPLATE_NAME)

    raw_entries = [
        entry for entry in directory.iterdir()
        if not is_ignored_file(entry, directory, root)
    ]

    dir_entries = [
        entry for entry in raw_entries
        if entry.is_dir() and not is_ignored_dir(entry, root)
    ]

    file_entries = [
        entry for entry in raw_entries
        if entry.is_file()
    ]

    # Sort alphabetically (case-insensitive)
    dir_entries.sort(key=lambda p: p.name.casefold())
    file_entries.sort(key=lambda p: p.name.casefold())

    # Build directory view models
    directories_data = []
    for entry in dir_entries:
        try:
            stat = entry.stat()
            modified = format_timestamp(stat.st_mtime)
        except OSError:
            modified = "-"

        directories_data.append({
            "name": entry.name,
            "display_name": f"{entry.name}/",
            "href": href_for(entry),
            "last_modified": modified,
        })

    # Build file view models
    files_data = []
    for entry in file_entries:
        try:
            stat = entry.stat()
            size_formatted = format_file_size(stat.st_size)
            modified = format_timestamp(stat.st_mtime)
        except OSError:
            size_formatted = "-"
            modified = "-"

        emoji, badge, badge_class = get_file_icon_and_badge(entry.name)

        files_data.append({
            "name": entry.name,
            "display_name": entry.name,
            "href": href_for(entry),
            "size_formatted": size_formatted,
            "last_modified": modified,
            "icon_emoji": emoji,
            "badge": badge,
            "badge_class": badge_class,
        })

    current_path_str = relative_directory_path(directory, root)
    breadcrumbs = generate_breadcrumbs(directory, root)
    parent_href = "../" if directory != root else None

    # Snippet generation
    coords = extract_maven_coords(directory, root)
    maven_snippet = None
    if coords:
        g = coords["groupId"]
        a = coords["artifactId"]
        v = coords["version"]
        maven_snippet = {
            "maven": f"<dependency>\n    <groupId>{g}</groupId>\n    <artifactId>{a}</artifactId>\n    <version>{v}</version>\n</dependency>",
            "gradle": f"implementation '{g}:{a}:{v}'",
            "kotlin": f'implementation("{g}:{a}:{v}")',
        }

    now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    return template.render(
        current_path=current_path_str,
        breadcrumbs=breadcrumbs,
        parent_href=parent_href,
        directories=directories_data,
        files=files_data,
        total_dirs=len(directories_data),
        total_files=len(files_data),
        maven_snippet=maven_snippet,
        current_time=now_utc,
    )


def generate_repository_indexes(root: Path, template_dir: Path | None = None) -> int:
    """Generate index.html for root and all non-ignored subdirectories."""
    root = root.resolve()
    if not root.exists():
        raise SystemExit(f"Directory does not exist: {root}")

    if not root.is_dir():
        raise SystemExit(f"Path is not a directory: {root}")

    env = setup_template_env(template_dir)

    directories_to_process = [root]

    for path in root.rglob("*"):
        if path.is_dir() and not is_ignored_dir(path, root):
            directories_to_process.append(path)

    generated_count = 0
    for directory in directories_to_process:
        index_file = directory / INDEX_NAME
        html_content = generate_html(env, directory, root)
        index_file.write_text(
            html_content,
            encoding="utf-8",
            newline="\n",
        )
        print(f"Generated: {index_file}")
        generated_count += 1

    return generated_count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate static HTML index files for a Maven repository.")
    parser.add_argument("directory", nargs="?", default=".", help="Root directory to generate indexes for (default: .)")
    parser.add_argument("--template-dir", default=None, help="Custom template directory path")

    args = parser.parse_args()
    root_path = Path(args.directory).resolve()
    template_dir = Path(args.template_dir).resolve() if args.template_dir else None

    count = generate_repository_indexes(root_path, template_dir)
    print(f"\nSuccessfully generated {count} index files.")


if __name__ == "__main__":
    main()
