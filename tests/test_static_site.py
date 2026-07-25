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
from urllib.parse import quote, unquote, urlsplit


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
TIMELINE_ROUTES = {
    "index.html": ("bg", ""),
    "index-bg.html": ("bg", ""),
    "index-en.html": ("en", ""),
    "index.html?lang=bg.html": ("bg", ""),
    "index.html?lang=en.html": ("en", ""),
    "opit/index.html": ("en", "../"),
}
TIMELINE_CONTROL_LABELS = {
    "bg": ("Предишен етап", "Следващ етап"),
    "en": ("Previous milestone", "Next milestone"),
}
TIMELINE_COMPANY_DESTINATIONS = (
    "https://correctproject.com",
    "https://engsys.bg",
)
TIMELINE_MILESTONE_COUNT = 13
REPRESENTATIVE_ROUTES = (*TIMELINE_ROUTES, "proekti/matrix/index.html")
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
        self.timeline_tabs: list[dict[str, str | None]] = []
        self.timeline_panels: list[dict[str, str | None]] = []
        self.timeline_controls: list[dict[str, str | None]] = []
        self.timeline_panel_links: list[dict[str, str | None]] = []
        self.timeline_mobile_links: list[dict[str, str | None]] = []

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
        classes = set(attributes.get("class", "").split())
        identifier = attributes.get("id")
        if identifier:
            if identifier in self.identifiers:
                self.duplicate_identifiers.add(identifier)
            self.identifiers.add(identifier)
        if tag == "html":
            self.language = attributes.get("lang")
        if tag == "script":
            self.script_types.append(attributes.get("type", "").lower())
        if tag == "button" and attributes.get("role") == "tab":
            self.timeline_tabs.append(attributes)
        if attributes.get("role") == "tabpanel":
            self.timeline_panels.append(attributes)
        if tag == "button" and (
            "data-timeline-previous" in attributes
            or "data-timeline-next" in attributes
        ):
            self.timeline_controls.append(attributes)
        if tag == "a" and "at-tlpanel__copy--link" in classes:
            self.timeline_panel_links.append(attributes)
        if tag == "a" and "at-tlcard__link" in classes:
            self.timeline_mobile_links.append(attributes)

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
                "--window-size=1280,900",
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

    def test_timeline_documents_have_complete_automatic_tab_relationships(self) -> None:
        """Require all six timelines to expose one complete 13-item tab model."""
        for route in TIMELINE_ROUTES:
            with self.subTest(route=route):
                parser = _parse_document(WORKSPACE_ROOT / route)
                self.assertEqual(TIMELINE_MILESTONE_COUNT, len(parser.timeline_tabs))
                self.assertEqual(TIMELINE_MILESTONE_COUNT, len(parser.timeline_panels))

                tab_ids = [tab.get("id") for tab in parser.timeline_tabs]
                panel_ids = [panel.get("id") for panel in parser.timeline_panels]
                self.assertEqual(TIMELINE_MILESTONE_COUNT, len(set(tab_ids)))
                self.assertEqual(TIMELINE_MILESTONE_COUNT, len(set(panel_ids)))
                panels_by_id = {
                    panel["id"]: panel
                    for panel in parser.timeline_panels
                    if panel.get("id")
                }
                for tab in parser.timeline_tabs:
                    panel = panels_by_id.get(tab.get("aria-controls"))
                    self.assertIsNotNone(panel)
                    self.assertEqual(tab.get("id"), panel.get("aria-labelledby"))

                selected_tabs = [
                    tab for tab in parser.timeline_tabs
                    if tab.get("aria-selected") == "true"
                ]
                self.assertEqual(1, len(selected_tabs))
                self.assertEqual("0", selected_tabs[0].get("tabindex"))
                self.assertEqual(
                    TIMELINE_MILESTONE_COUNT - 1,
                    sum(tab.get("tabindex") == "-1" for tab in parser.timeline_tabs),
                )

    def test_timeline_controls_company_links_and_arcadia_assets_are_consistent(self) -> None:
        """Require localized controls, native company links, and Arcadia WebP parity."""
        for route, (language, asset_prefix) in TIMELINE_ROUTES.items():
            with self.subTest(route=route):
                document = WORKSPACE_ROOT / route
                content = document.read_text(encoding="utf-8")
                parser = _parse_document(document)
                controls_by_direction = {
                    "previous" if "data-timeline-previous" in control else "next": control
                    for control in parser.timeline_controls
                }
                expected_previous, expected_next = TIMELINE_CONTROL_LABELS[language]
                self.assertEqual(expected_previous, controls_by_direction["previous"].get("aria-label"))
                self.assertEqual(expected_next, controls_by_direction["next"].get("aria-label"))

                internal_destination = f"{asset_prefix or '/'}"
                expected_destinations = {
                    *TIMELINE_COMPANY_DESTINATIONS,
                    internal_destination,
                }
                self.assertEqual(
                    expected_destinations,
                    {link.get("href") for link in parser.timeline_panel_links},
                )
                self.assertEqual(
                    expected_destinations,
                    {link.get("href") for link in parser.timeline_mobile_links},
                )
                self.assertNotIn("data-href=", content)
                self.assertEqual(
                    2,
                    content.count(
                        f'src="{asset_prefix}wp-content/uploads/2026/07/'
                        'arcadia-timeline.webp"'
                    ),
                )
                arcadia_tabs = [
                    tab for tab in parser.timeline_tabs
                    if tab.get("data-project") == "arcadia"
                ]
                self.assertEqual(1, len(arcadia_tabs))

    def test_timeline_css_and_javascript_preserve_progressive_interaction(self) -> None:
        """Require five-item snapping, fallback scrolling, containment, and reduced motion."""
        stylesheet = SHARED_ASSET_PAIRS[1][0].read_text(encoding="utf-8")
        javascript = SHARED_ASSET_PAIRS[0][0].read_text(encoding="utf-8")
        self.assertIn("--timeline-control-width: calc(20% - .8rem);", stylesheet)
        self.assertIn("scroll-snap-type: x proximity;", stylesheet)
        self.assertIn("scroll-snap-align: center;", stylesheet)
        self.assertIn("touch-action: pan-x pan-y;", stylesheet)
        self.assertIn("overflow-x: auto;", stylesheet)
        self.assertIn(".is-timeline-enhanced .at-tl-buildings", stylesheet)
        self.assertIn("min-width: 44px; min-height: 44px;", stylesheet)
        self.assertIn('.at-tlb[data-project="arcadia"] .at-tlb__img', stylesheet)
        self.assertIn("filter: grayscale(1);", stylesheet)
        self.assertNotIn("scale(2.15)", stylesheet)
        self.assertNotIn("max-width: none; height:", stylesheet)
        self.assertIn("REDUCED_MOTION_QUERY", javascript)
        self.assertIn('(position - 1 + tabCount) % tabCount', javascript)
        self.assertIn('(position + 1) % tabCount', javascript)
        self.assertNotIn('addEventListener("mouseenter"', javascript)

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
                    encoded_route = quote(route, safe="/")
                    rendered_html, diagnostics = _run_chrome(
                        f"{base_url}/{encoded_route}"
                    )
                    self.assertRegex(
                        rendered_html,
                        r"<html[^>]*class=\"[^\"]*\bhas-js\b",
                    )
                    if route in TIMELINE_ROUTES:
                        self.assertIn("is-timeline-enhanced", rendered_html)
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
