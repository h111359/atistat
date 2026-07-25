"""
test_static_site.py: Regression checks for the dependency-free ATISTAT static export.
Part of request R-20260725-1526; validates routes, assets, fragments, and browser execution.
"""

from __future__ import annotations

import contextlib
import functools
import re
import shutil
import subprocess
import tempfile
import threading
import unittest
from collections.abc import Iterator, Sequence
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
IGNORED_DIRECTORIES = {".aib_brain", ".aib_memory", ".git", "tests", "workdir"}
RESOURCE_ATTRIBUTES = {
    "a": ("href",),
    "iframe": ("src",),
    "img": ("src", "srcset"),
    "link": ("href",),
    "script": ("src",),
    "source": ("src", "srcset"),
}
SHARED_ASSET_PAIRS = (
    (
        WORKSPACE_ROOT / "wp-content/themes/atistat/assets/js/main.js",
        WORKSPACE_ROOT / "wp-content/themes/atistat/assets/js/main.js?ver=1784544801",
    ),
    (
        WORKSPACE_ROOT / "wp-content/themes/atistat/assets/css/main.css",
        WORKSPACE_ROOT / "wp-content/themes/atistat/assets/css/main.css?ver=1784544801.css",
    ),
)
REPRESENTATIVE_ROUTES = (
    "index.html",
    "index-en.html",
    "opit/index.html",
    "proekti/matrix/index.html",
)
INTERACTION_HARNESS_ROUTE = "tests/fixtures/interaction_harness.html"
CSS_URL_PATTERN = re.compile(r"url\(\s*([\"']?)(.*?)\1\s*\)", re.IGNORECASE)
JAVASCRIPT_ERROR_MARKERS = (
    "Error",
    "SyntaxError",
    "ReferenceError",
    "TypeError",
    "Uncaught",
)


class StaticDocumentParser(HTMLParser):
    """Collect identifiers, scripts, and local-reference candidates from one HTML page."""

    def __init__(self) -> None:
        """Initialize empty collections for one document parse."""
        super().__init__(convert_charrefs=True)
        self.identifiers: set[str] = set()
        self.duplicate_identifiers: set[str] = set()
        self.references: list[str] = []
        self.script_types: list[str] = []
        self.language: str | None = None

    def handle_starttag(
        self,
        tag: str,
        attrs: Sequence[tuple[str, str | None]],
    ) -> None:
        """
        Collect relevant attributes from an HTML start tag.

        Args:
            tag: The normalized element name.
            attrs: The element's parsed attribute name/value pairs.

        Returns:
            None; collected values are stored on this parser instance.
        """
        attributes = dict(attrs)
        identifier = attributes.get("id")
        if identifier:
            if identifier in self.identifiers:
                self.duplicate_identifiers.add(identifier)
            self.identifiers.add(identifier)
        if tag == "html":
            self.language = attributes.get("lang")
        if tag == "script":
            self.script_types.append(attributes.get("type", "").lower())

        for attribute in RESOURCE_ATTRIBUTES.get(tag, ()):
            value = attributes.get(attribute)
            if not value:
                continue
            if attribute == "srcset":
                self.references.extend(_split_srcset(value))
            else:
                self.references.append(value)


class QuietRequestHandler(SimpleHTTPRequestHandler):
    """Serve the workspace without emitting request logs during browser smoke tests."""

    def log_message(self, format_string: str, *args: object) -> None:
        """
        Suppress expected local HTTP access logs.

        Args:
            format_string: The server's pending log-message format.
            *args: Values intended for the format string.

        Returns:
            None; no message is emitted.
        """
        return


def _html_paths() -> list[Path]:
    """Return all product HTML documents, excluding automation and test artifacts."""
    return sorted(
        path
        for path in WORKSPACE_ROOT.rglob("*.html")
        if not IGNORED_DIRECTORIES.intersection(path.relative_to(WORKSPACE_ROOT).parts)
        and _is_html_document(path)
    )


def _is_html_document(path: Path) -> bool:
    """Distinguish rendered pages from JSON snapshots stored with an HTML suffix."""
    with path.open("rb") as document:
        return document.read(64).lstrip().lower().startswith(b"<!doctype html")


def _parse_document(path: Path) -> StaticDocumentParser:
    """Parse an HTML document and return its collected structural metadata."""
    parser = StaticDocumentParser()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    return parser


def _split_srcset(srcset: str) -> list[str]:
    """Extract URL candidates from a comma-separated responsive-image source set."""
    return [
        candidate.strip().split()[0]
        for candidate in srcset.split(",")
        if candidate.strip()
    ]


def _resolve_local_reference(document: Path, reference: str) -> Path | None:
    """Resolve a local URL reference to its expected workspace path."""
    parts = urlsplit(reference)
    if parts.scheme or parts.netloc or (not parts.path and parts.fragment):
        return None

    decoded_path = unquote(parts.path)
    if not decoded_path:
        return document
    if decoded_path.startswith("/"):
        return WORKSPACE_ROOT / decoded_path.lstrip("/")
    return (document.parent / decoded_path).resolve()


def _is_within_workspace(path: Path) -> bool:
    """Report whether a resolved path remains inside the product workspace."""
    try:
        path.relative_to(WORKSPACE_ROOT)
    except ValueError:
        return False
    return True


@contextlib.contextmanager
def _serve_workspace() -> Iterator[str]:
    """Serve the static export on an available loopback port for browser tests."""
    handler = functools.partial(QuietRequestHandler, directory=str(WORKSPACE_ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _run_chrome(url: str) -> tuple[str, str]:
    """Render one URL in headless Chrome and return its DOM output and diagnostics."""
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if chrome is None:
        raise unittest.SkipTest("Headless Chrome or Chromium is required for browser smoke tests.")

    with tempfile.TemporaryDirectory(prefix="atistat-chrome-") as profile_directory:
        result = subprocess.run(
            (
                chrome,
                "--headless=new",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                f"--user-data-dir={profile_directory}",
                "--enable-logging=stderr",
                "--v=0",
                "--virtual-time-budget=1500",
                "--dump-dom",
                url,
            ),
            cwd=WORKSPACE_ROOT,
            capture_output=True,
            check=False,
            text=True,
            timeout=30,
        )
    if result.returncode != 0:
        raise AssertionError(
            f"Chrome failed for {url} with exit code {result.returncode}:\n{result.stderr}"
        )
    return result.stdout, result.stderr


def _first_party_console_errors(diagnostics: str) -> list[str]:
    """Extract first-party JavaScript errors from Chrome's diagnostic stream."""
    return [
        line
        for line in diagnostics.splitlines()
        if "CONSOLE:" in line
        and ("127.0.0.1" in line or "file://" in line)
        and any(marker in line for marker in JAVASCRIPT_ERROR_MARKERS)
    ]


class StaticSiteIntegrityTests(unittest.TestCase):
    """Verify that the complete static export has valid local wiring and safe fallbacks."""

    def test_every_html_document_has_required_shell(self) -> None:
        """Require a documented doctype, language, and closing HTML element on every page."""
        for path in _html_paths():
            with self.subTest(path=path.relative_to(WORKSPACE_ROOT)):
                content = path.read_text(encoding="utf-8")
                parser = _parse_document(path)
                self.assertRegex(content, r"\A<!DOCTYPE html>\s*<!--")
                self.assertIsNotNone(parser.language)
                self.assertRegex(content.rstrip(), r"</html>\Z")

    def test_local_references_resolve_inside_workspace(self) -> None:
        """Require every local document and asset reference to resolve to an existing path."""
        failures: list[str] = []
        for document in _html_paths():
            for reference in _parse_document(document).references:
                resolved = _resolve_local_reference(document, reference)
                if resolved is None:
                    continue
                if not _is_within_workspace(resolved):
                    failures.append(f"{document}: escapes workspace: {reference}")
                elif not resolved.exists():
                    failures.append(f"{document}: missing {reference} -> {resolved}")
        self.assertEqual([], failures)

    def test_fragment_links_have_matching_targets(self) -> None:
        """Require same-document fragment links to reference identifiers that exist."""
        failures: list[str] = []
        for document in _html_paths():
            parser = _parse_document(document)
            for reference in parser.references:
                parts = urlsplit(reference)
                if parts.path or parts.query or not parts.fragment:
                    continue
                if unquote(parts.fragment) not in parser.identifiers:
                    failures.append(f"{document}: missing fragment target #{parts.fragment}")
        self.assertEqual([], failures)

    def test_identifier_values_are_unique_per_document(self) -> None:
        """Reject duplicate identifiers that make DOM and accessibility lookups ambiguous."""
        failures: dict[str, list[str]] = {}
        for document in _html_paths():
            duplicates = _parse_document(document).duplicate_identifiers
            if duplicates:
                failures[str(document.relative_to(WORKSPACE_ROOT))] = sorted(duplicates)
        self.assertEqual({}, failures)

    def test_mobile_hero_has_explicit_overflow_constraints(self) -> None:
        """Keep long localized hero text within the minimum supported viewport."""
        stylesheet = SHARED_ASSET_PAIRS[1][0].read_text(encoding="utf-8")
        self.assertIn(".at-hero__text { min-width: 0; }", stylesheet)
        self.assertIn(
            "font-size: clamp(1.8rem, 9vw, 2.2rem); overflow-wrap: anywhere;",
            stylesheet,
        )

    def test_stylesheet_references_resolve(self) -> None:
        """Require every local URL in the shared stylesheet to resolve to an existing asset."""
        stylesheet = SHARED_ASSET_PAIRS[1][0]
        content = stylesheet.read_text(encoding="utf-8")
        failures: list[str] = []
        for _, reference in CSS_URL_PATTERN.findall(content):
            resolved = _resolve_local_reference(stylesheet, reference)
            if resolved is not None and not resolved.exists():
                failures.append(f"{reference} -> {resolved}")
        self.assertEqual([], failures)

    def test_speculative_prefetch_is_absent(self) -> None:
        """Prevent file-origin errors by rejecting exported speculation rules."""
        failures = [
            str(path.relative_to(WORKSPACE_ROOT))
            for path in _html_paths()
            if "speculationrules" in _parse_document(path).script_types
        ]
        self.assertEqual([], failures)

    def test_shared_asset_copies_are_identical(self) -> None:
        """Keep canonical and version-suffixed shared assets byte-identical."""
        for canonical, versioned in SHARED_ASSET_PAIRS:
            with self.subTest(asset=canonical.name):
                self.assertEqual(canonical.read_bytes(), versioned.read_bytes())

    def test_progressive_enhancement_and_dialog_fallbacks_exist(self) -> None:
        """Keep reveal content visible without JavaScript and closed dialogs out of layout."""
        stylesheet = SHARED_ASSET_PAIRS[1][0].read_text(encoding="utf-8")
        self.assertIn(".at-fade { opacity: 1; transform: none; }", stylesheet)
        self.assertIn("dialog.at-selected-projects:not([open])", stylesheet)


class BrowserSmokeTests(unittest.TestCase):
    """Exercise representative routes in Chrome to catch parse and runtime regressions."""

    def test_navigation_timeline_and_dialog_interactions(self) -> None:
        """Require the shared controls to update visible, focus, and accessible state."""
        with _serve_workspace() as base_url:
            rendered_html, diagnostics = _run_chrome(
                f"{base_url}/{INTERACTION_HARNESS_ROUTE}"
            )
        self.assertIn('data-status="passed"', rendered_html)
        self.assertEqual([], _first_party_console_errors(diagnostics))

    def test_representative_http_routes_execute_shared_javascript(self) -> None:
        """Require shared JavaScript to initialize without first-party console errors."""
        with _serve_workspace() as base_url:
            for route in REPRESENTATIVE_ROUTES:
                with self.subTest(route=route):
                    rendered_html, diagnostics = _run_chrome(f"{base_url}/{route}")
                    self.assertRegex(
                        rendered_html,
                        r"<html[^>]*class=\"[^\"]*\bhas-js\b",
                    )
                    self.assertEqual([], _first_party_console_errors(diagnostics))

    def test_file_url_homepage_has_no_origin_or_javascript_errors(self) -> None:
        """Require direct-file homepage loading to avoid origin and script diagnostics."""
        url = f"{(WORKSPACE_ROOT / 'index.html').as_uri()}#about"
        rendered_html, diagnostics = _run_chrome(url)
        self.assertRegex(rendered_html, r"<html[^>]*class=\"[^\"]*\bhas-js\b")
        self.assertNotIn("Unsafe attempt to load URL file:", diagnostics)
        self.assertEqual([], _first_party_console_errors(diagnostics))


if __name__ == "__main__":
    unittest.main(verbosity=2)
