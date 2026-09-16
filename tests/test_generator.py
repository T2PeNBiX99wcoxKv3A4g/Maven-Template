import html
import shutil
import tempfile
import unittest
from pathlib import Path

from main import (
    INDEX_NAME,
    extract_maven_coords,
    format_file_size,
    generate_breadcrumbs,
    generate_html,
    generate_repository_indexes,
    get_file_icon_and_badge,
    is_ignored_dir,
    is_ignored_file,
    setup_template_env,
)


class TestMavenGenerator(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp()).resolve()
        self.env = setup_template_env()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_file_size_formatting(self):
        self.assertEqual(format_file_size(500), "500 B")
        self.assertEqual(format_file_size(1024), "1.00 KB")
        self.assertEqual(format_file_size(1024 * 1024 * 2), "2.00 MB")
        self.assertEqual(format_file_size(1024 * 1024 * 1024 * 3), "3.00 GB")

    def test_icons_and_badges(self):
        emoji, badge, badge_class = get_file_icon_and_badge("demo-1.0.0.jar")
        self.assertEqual(emoji, "📦")
        self.assertEqual(badge, "JAR")
        self.assertEqual(badge_class, "badge-jar")

        emoji, badge, badge_class = get_file_icon_and_badge("demo-1.0.0.pom")
        self.assertEqual(emoji, "📄")
        self.assertEqual(badge, "POM")
        self.assertEqual(badge_class, "badge-pom")

        emoji, badge, badge_class = get_file_icon_and_badge("demo-1.0.0.jar.sha256")
        self.assertEqual(emoji, "🔏")
        self.assertEqual(badge, "SHA256")
        self.assertEqual(badge_class, "badge-hash")

        emoji, badge, badge_class = get_file_icon_and_badge("maven-metadata.xml")
        self.assertEqual(emoji, "⚙️")
        self.assertEqual(badge, "XML")
        self.assertEqual(badge_class, "badge-xml")

        emoji, badge, badge_class = get_file_icon_and_badge("demo.zip")
        self.assertEqual(emoji, "🗜️")
        self.assertEqual(badge, "ZIP")

    def test_ignored_rules(self):
        self.assertTrue(is_ignored_dir(Path("templates")))
        self.assertTrue(is_ignored_dir(Path(".git")))
        self.assertTrue(is_ignored_dir(Path("venv")))
        self.assertTrue(is_ignored_dir(Path("build")))
        self.assertFalse(is_ignored_dir(Path("com")))

        self.assertTrue(is_ignored_file(Path(INDEX_NAME), Path(".")))
        self.assertTrue(is_ignored_file(Path("main.py"), Path(".")))
        self.assertTrue(is_ignored_file(Path("test.pyc"), Path("com")))
        self.assertFalse(is_ignored_file(Path("sample.jar"), Path("com")))

    def test_maven_coords_extraction_from_pom(self):
        artifact_dir = self.temp_dir / "com" / "example" / "demo" / "1.0.0"
        artifact_dir.mkdir(parents=True)
        pom_file = artifact_dir / "demo-1.0.0.pom"
        pom_content = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <groupId>com.example</groupId>
    <artifactId>demo</artifactId>
    <version>1.0.0</version>
</project>"""
        pom_file.write_text(pom_content, encoding="utf-8")

        coords = extract_maven_coords(artifact_dir, self.temp_dir)
        self.assertIsNotNone(coords)
        self.assertEqual(coords["groupId"], "com.example")
        self.assertEqual(coords["artifactId"], "demo")
        self.assertEqual(coords["version"], "1.0.0")

    def test_breadcrumbs(self):
        pkg_dir = self.temp_dir / "com" / "example" / "app" / "1.0.0"
        pkg_dir.mkdir(parents=True)
        crumbs = generate_breadcrumbs(pkg_dir, self.temp_dir)
        self.assertEqual(len(crumbs), 5)
        self.assertEqual(crumbs[0]["name"], "~ (root)")
        self.assertEqual(crumbs[0]["href"], "../../../../")
        self.assertEqual(crumbs[1]["name"], "com")
        self.assertEqual(crumbs[1]["href"], "../../../")
        self.assertEqual(crumbs[4]["name"], "1.0.0")
        self.assertEqual(crumbs[4]["href"], "#")

    def test_full_repository_index_generation(self):
        repo_root = self.temp_dir
        pkg_dir = repo_root / "com" / "example" / "app" / "1.0.0"
        pkg_dir.mkdir(parents=True)

        jar_file = pkg_dir / "app-1.0.0.jar"
        jar_file.write_bytes(b"mock jar binary content")
        sha_file = pkg_dir / "app-1.0.0.jar.sha1"
        sha_file.write_text("da39a3ee5e6b4b0d3255bfef95601890afd80709", encoding="utf-8")

        # Create ignored dirs
        (repo_root / "templates").mkdir()
        (repo_root / "templates" / "some_template.html").write_text("hello", encoding="utf-8")
        (repo_root / "venv").mkdir()
        (repo_root / "venv" / "file.txt").write_text("venv file", encoding="utf-8")

        count = generate_repository_indexes(repo_root)
        self.assertEqual(count, 5)  # root, com, com/example, com/example/app, com/example/app/1.0.0

        # Verify index.html exists in valid dirs
        self.assertTrue((repo_root / INDEX_NAME).exists())
        self.assertTrue((pkg_dir / INDEX_NAME).exists())

        # Verify index.html does NOT exist in ignored dirs
        self.assertFalse((repo_root / "templates" / INDEX_NAME).exists())
        self.assertFalse((repo_root / "venv" / INDEX_NAME).exists())

        # Verify HTML contents
        html_out = (pkg_dir / INDEX_NAME).read_text(encoding="utf-8")
        self.assertIn("app-1.0.0.jar", html_out)
        self.assertIn("app-1.0.0.jar.sha1", html_out)
        self.assertIn("Maven Repository", html_out)
        self.assertIn("implementation 'com.example:app:1.0.0'", html.unescape(html_out))
        self.assertIn("<groupId>com.example</groupId>", html.unescape(html_out))
        self.assertIn(".. (Parent Directory)", html_out)


if __name__ == "__main__":
    unittest.main()
