"""
test_static_site.py: Regression checks for the dependency-free ATISTAT static export.
Validates routes, assets, responsive timeline behavior, galleries, and browser execution.
"""

from __future__ import annotations

import contextlib
import functools
import re
import shutil
import struct
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
    "en": ("Previous stage", "Next stage"),
}
RESPONSIVE_TIMELINE_LABELS = {
    "bg": "Навигация по етапите",
    "en": "Milestone navigation",
}
GALLERY_OVERLAY_LABELS = {
    "bg": "Виж галерия",
    "en": "View gallery",
}
GALLERY_PROJECTS = (
    "montekanal",
    "elemag",
    "louis-ayer",
    "ubb-interlease",
    "arcadia",
    "bebelan",
    "power-properties",
)
FULL_RESOLUTION_GALLERY_FILES = {
    "arcadia": tuple(
        f"Снимка {sequence} , интериор Аркадия.png"
        for sequence in range(1, 7)
    ),
    "louis-ayer": tuple(
        f"Снимка {sequence} , интериор Луи Айер.png"
        for sequence in range(1, 5)
    ),
    "bebelan": tuple(
        f"Снимка {sequence} , интериор Бебелан.jpg"
        for sequence in range(1, 7)
    ),
    "elemag": tuple(
        f"Снимка {sequence} , строителство Елемаг.png"
        for sequence in range(1, 5)
    ),
    "montekanal": (
        "Снимка 1 ,IMG_6308 - готово за сайт.png",
        "Снимка 2 ,IMG_6307 - готово за сайт.png",
        "Снимка 3 ,IMG_6320 - готово за сайт.png",
        "Снимка 4 ,IMG_6321 - готово за сайт.png",
    ),
    "ubb-interlease": tuple(
        f"Снимка {sequence} , интериор ОББ Интерлийз.jpg"
        for sequence in range(1, 5)
    ),
    "power-properties": tuple(
        f"Снимка {sequence} , интериор Пауър П.png"
        for sequence in range(1, 5)
    ),
}
GALLERY_THUMBNAIL_ROOT = (
    WORKSPACE_ROOT / "wp-content/uploads/2026/07/gallery-thumbnails"
)
EXPECTED_GALLERY_THUMBNAILS = {
    f"{project}-{sequence:02d}.webp"
    for project in GALLERY_PROJECTS
    for sequence in range(1, 5)
}
ADREO_HOMEPAGE_ROUTES = {
    "index.html": "Адрео",
    "index-bg.html": "Адрео",
    "index-en.html": "Adreo",
    "index.html?lang=bg.html": "Адрео",
    "index.html?lang=en.html": "Adreo",
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
        self.responsive_timeline_navigation: dict[str, str | None] | None = None
        self.responsive_timeline_markers: list[dict[str, str | None]] = []
        self.timeline_cards: list[dict[str, str | None]] = []
        self.gallery_mosaics: list[dict[str, object]] = []
        self.gallery_projects: dict[str, list[str]] = {}
        self._active_gallery_mosaic: dict[str, object] | None = None
        self._inside_gallery_overlay = False
        self._active_gallery_project: str | None = None
        self._active_gallery_project_depth = 0

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
        if tag == "nav" and "data-responsive-timeline" in attributes:
            self.responsive_timeline_navigation = attributes
        if tag == "a" and "data-responsive-marker" in attributes:
            self.responsive_timeline_markers.append(attributes)
        if tag == "li" and "at-tlcard" in classes:
            self.timeline_cards.append(attributes)
        if tag == "button" and "at-gallery-mosaic" in classes:
            mosaic: dict[str, object] = {
                "attributes": attributes,
                "images": [],
                "icon_count": 0,
                "overlay_attributes": None,
                "overlay_text": [],
            }
            self.gallery_mosaics.append(mosaic)
            self._active_gallery_mosaic = mosaic
        elif self._active_gallery_mosaic is not None:
            if tag == "img":
                images = self._active_gallery_mosaic["images"]
                assert isinstance(images, list)
                images.append(attributes)
            elif tag == "span" and "at-gallery-mosaic__overlay" in classes:
                self._inside_gallery_overlay = True
                self._active_gallery_mosaic["overlay_attributes"] = attributes
            elif tag == "svg" and "at-gallery-mosaic__icon" in classes:
                icon_count = self._active_gallery_mosaic["icon_count"]
                assert isinstance(icon_count, int)
                self._active_gallery_mosaic["icon_count"] = icon_count + 1
        if tag == "div" and "at-gallery-project" in classes:
            project = attributes.get("data-project")
            if project:
                self._active_gallery_project = project
                self._active_gallery_project_depth = 1
                self.gallery_projects[project] = []
        elif self._active_gallery_project is not None:
            if tag == "div":
                self._active_gallery_project_depth += 1
            elif tag == "img":
                source = attributes.get("src")
                if source:
                    self.gallery_projects[self._active_gallery_project].append(source)

        for attribute in RESOURCE_ATTRIBUTES.get(tag, ()):
            value = attributes.get(attribute)
            if not value:
                continue
            if attribute == "srcset":
                self.references.extend(_split_srcset(value))
            else:
                self.references.append(value)

    def handle_endtag(self, tag: str) -> None:
        """
        Close active gallery parsing scopes.

        Args:
            tag: The normalized closing element name.

        Returns:
            None; active parser state is updated in place.
        """
        if tag == "button" and self._active_gallery_mosaic is not None:
            self._active_gallery_mosaic = None
            self._inside_gallery_overlay = False
        elif tag == "span" and self._inside_gallery_overlay:
            self._inside_gallery_overlay = False
        if tag == "div" and self._active_gallery_project is not None:
            self._active_gallery_project_depth -= 1
            if self._active_gallery_project_depth == 0:
                self._active_gallery_project = None

    def handle_data(self, data: str) -> None:
        """
        Collect localized visible text inside a gallery overlay.

        Args:
            data: Character data emitted by the HTML parser.

        Returns:
            None; non-empty overlay text is stored on the active mosaic.
        """
        if self._active_gallery_mosaic is None or not self._inside_gallery_overlay:
            return
        normalized = data.strip()
        if normalized:
            overlay_text = self._active_gallery_mosaic["overlay_text"]
            assert isinstance(overlay_text, list)
            overlay_text.append(normalized)


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


def _read_webp_dimensions(path: Path) -> tuple[int, int]:
    """
    Read WebP canvas dimensions without introducing an image-library dependency.

    Args:
        path: WebP file whose dimensions should be inspected.

    Returns:
        Width and height in CSS-independent image pixels.

    Raises:
        ValueError: If the file is not a supported WebP container.
    """
    content = path.read_bytes()
    if content[:4] != b"RIFF" or content[8:12] != b"WEBP":
        raise ValueError(f"{path} is not a WebP RIFF container")
    chunk_type = content[12:16]
    if chunk_type == b"VP8 " and content[23:26] == b"\x9d\x01\x2a":
        width, height = struct.unpack_from("<HH", content, 26)
        return width & 0x3FFF, height & 0x3FFF
    if chunk_type == b"VP8L" and content[20] == 0x2F:
        packed_dimensions = int.from_bytes(content[21:25], "little")
        width = (packed_dimensions & 0x3FFF) + 1
        height = ((packed_dimensions >> 14) & 0x3FFF) + 1
        return width, height
    if chunk_type == b"VP8X":
        width = int.from_bytes(content[24:27], "little") + 1
        height = int.from_bytes(content[27:30], "little") + 1
        return width, height
    raise ValueError(f"{path} uses an unsupported WebP payload")


def _expected_dialog_sources(asset_prefix: str) -> dict[str, list[str]]:
    """
    Build the immutable full-resolution dialog source mapping for one route depth.

    Args:
        asset_prefix: Route-relative prefix before wp-content.

    Returns:
        Project-keyed, source-order URL lists.
    """
    source_root = f"{asset_prefix}wp-content/uploads/2026/07/"
    return {
        project: [f"{source_root}{quote(name)}" for name in file_names]
        for project, file_names in FULL_RESOLUTION_GALLERY_FILES.items()
    }


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


def _run_chrome(
    url: str,
    viewport: tuple[int, int] = (1280, 900),
) -> tuple[str, str]:
    """
    Render one URL in headless Chrome at a requested viewport.

    Args:
        url: HTTP or file URL to render.
        viewport: CSS-pixel width and height requested from headless Chrome.

    Returns:
        Rendered DOM output and Chrome diagnostics.
    """
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
                f"--window-size={viewport[0]},{viewport[1]}",
                "--force-device-scale-factor=1",
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

    def test_adreo_partner_logo_is_localized_across_homepages(self) -> None:
        """Require the local Adreo image and language-appropriate alternative text."""
        for route, alternative_text in ADREO_HOMEPAGE_ROUTES.items():
            with self.subTest(route=route):
                content = (WORKSPACE_ROOT / route).read_text(encoding="utf-8")
                self.assertIn(
                    'src="wp-content/uploads/2026/07/adreo.png" '
                    f'alt="{alternative_text}" loading="lazy" decoding="async"',
                    content,
                )
                self.assertNotIn('class="at-partner__wordmark"', content)

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

    def test_timeline_documents_have_card_first_responsive_navigation(self) -> None:
        """Require localized source-order marker links mapped to focusable card containers."""
        for route, (language, _) in TIMELINE_ROUTES.items():
            with self.subTest(route=route):
                document = WORKSPACE_ROOT / route
                content = document.read_text(encoding="utf-8")
                parser = _parse_document(document)
                panel_position = content.index('<div class="at-tl-panels"')
                hint_position = content.index('<p class="at-tl-hint"')
                stage_position = content.index('<div class="at-tl-stage">')
                responsive_position = content.index(
                    '<nav class="at-tl-responsive" data-responsive-timeline'
                )
                cards_position = content.index('<ul class="at-tl-mobile">')
                self.assertLess(panel_position, hint_position)
                self.assertLess(hint_position, stage_position)
                self.assertLess(stage_position, responsive_position)
                self.assertLess(responsive_position, cards_position)

                navigation = parser.responsive_timeline_navigation
                self.assertIsNotNone(navigation)
                self.assertEqual(
                    RESPONSIVE_TIMELINE_LABELS[language],
                    navigation.get("aria-label") if navigation else None,
                )
                markers = parser.responsive_timeline_markers
                cards = parser.timeline_cards
                self.assertEqual(TIMELINE_MILESTONE_COUNT, len(markers))
                self.assertEqual(TIMELINE_MILESTONE_COUNT, len(cards))
                self.assertEqual(
                    [str(index) for index in range(TIMELINE_MILESTONE_COUNT)],
                    [marker.get("data-index") for marker in markers],
                )
                for index, (marker, card) in enumerate(zip(markers, cards, strict=True)):
                    destination_id = f"timeline-card-{index}"
                    self.assertEqual(f"#{destination_id}", marker.get("href"))
                    self.assertEqual(destination_id, card.get("id"))
                    self.assertEqual("-1", card.get("tabindex"))
                current_markers = [
                    marker
                    for marker in markers
                    if marker.get("aria-current") == "step"
                ]
                self.assertEqual(1, len(current_markers))
                self.assertEqual("3", current_markers[0].get("data-index"))

    def test_mosaics_use_exact_thumbnails_and_preserve_dialog_sources(self) -> None:
        """Require optimized preview mappings, localized overlays, and original dialogs."""
        for route, (language, asset_prefix) in TIMELINE_ROUTES.items():
            with self.subTest(route=route):
                parser = _parse_document(WORKSPACE_ROOT / route)
                self.assertEqual(len(GALLERY_PROJECTS) * 2, len(parser.gallery_mosaics))
                project_counts = {project: 0 for project in GALLERY_PROJECTS}
                for mosaic in parser.gallery_mosaics:
                    attributes = mosaic["attributes"]
                    images = mosaic["images"]
                    overlay_attributes = mosaic["overlay_attributes"]
                    overlay_text = mosaic["overlay_text"]
                    self.assertIsInstance(attributes, dict)
                    self.assertIsInstance(images, list)
                    self.assertIsInstance(overlay_attributes, dict)
                    self.assertIsInstance(overlay_text, list)
                    project = attributes.get("data-project")
                    self.assertIn(project, GALLERY_PROJECTS)
                    project_counts[project] += 1
                    self.assertTrue(attributes.get("aria-label"))
                    self.assertEqual(4, len(images))
                    for sequence, image in enumerate(images, start=1):
                        expected_source = (
                            f"{asset_prefix}wp-content/uploads/2026/07/"
                            f"gallery-thumbnails/{project}-{sequence:02d}.webp"
                        )
                        self.assertEqual(expected_source, image.get("src"))
                        self.assertEqual("160", image.get("width"))
                        self.assertEqual("160", image.get("height"))
                        self.assertEqual("lazy", image.get("loading"))
                        self.assertEqual("async", image.get("decoding"))
                        self.assertNotRegex(image.get("src", ""), r"\.(?:png|jpe?g)$")
                    self.assertEqual("true", overlay_attributes.get("aria-hidden"))
                    self.assertEqual(1, mosaic["icon_count"])
                    self.assertEqual([GALLERY_OVERLAY_LABELS[language]], overlay_text)
                self.assertEqual(
                    {project: 2 for project in GALLERY_PROJECTS},
                    project_counts,
                )
                self.assertEqual(
                    _expected_dialog_sources(asset_prefix),
                    parser.gallery_projects,
                )

    def test_gallery_thumbnail_assets_are_exact_bounded_webp_files(self) -> None:
        """Require exactly 28 named 160px WebP previews no larger than 20KB."""
        actual_files = {
            path.name
            for path in GALLERY_THUMBNAIL_ROOT.iterdir()
            if path.is_file()
        }
        self.assertEqual(EXPECTED_GALLERY_THUMBNAILS, actual_files)
        for thumbnail_name in sorted(EXPECTED_GALLERY_THUMBNAILS):
            with self.subTest(thumbnail=thumbnail_name):
                thumbnail = GALLERY_THUMBNAIL_ROOT / thumbnail_name
                self.assertLessEqual(thumbnail.stat().st_size, 20 * 1024)
                self.assertEqual((160, 160), _read_webp_dimensions(thumbnail))

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
                stage_position = content.index('<div class="at-tl-stage">')
                previous_position = content.index("data-timeline-previous")
                start_year_position = content.index('<div class="at-tl-year at-tl-year--start">')
                shell_position = content.index('<div class="at-tl-rail-shell">')
                next_position = content.index("data-timeline-next")
                end_year_position = content.index('<div class="at-tl-year at-tl-year--end">')
                self.assertLess(stage_position, previous_position)
                self.assertLess(previous_position, start_year_position)
                self.assertLess(start_year_position, shell_position)
                self.assertLess(shell_position, next_position)
                self.assertLess(next_position, end_year_position)
                self.assertNotIn('class="at-tl-controls"', content)
                self.assertIn('points="9,1 1,9 9,17"', content)
                self.assertIn('points="1,1 9,9 1,17"', content)

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
                    3,
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
        """Require compact desktop and progressive responsive interaction contracts."""
        stylesheet = SHARED_ASSET_PAIRS[1][0].read_text(encoding="utf-8")
        javascript = SHARED_ASSET_PAIRS[0][0].read_text(encoding="utf-8")
        self.assertIn("--timeline-control-width: calc(20% - .8rem);", stylesheet)
        self.assertIn("scroll-snap-type: x proximity;", stylesheet)
        self.assertIn("scroll-snap-align: center;", stylesheet)
        self.assertIn("touch-action: pan-x pan-y;", stylesheet)
        self.assertIn("overflow-x: auto;", stylesheet)
        self.assertIn(".is-timeline-enhanced .at-tl-buildings", stylesheet)
        self.assertIn("min-width: 44px; min-height: 44px;", stylesheet)
        self.assertIn(
            "position: absolute; z-index: 8; top: 50%; "
            "transform: translate(-50%, -50%); pointer-events: auto;",
            stylesheet,
        )
        self.assertIn("--timeline-boundary-center: clamp(38px, 4vw, 55px);", stylesheet)
        self.assertIn(
            "left: calc(var(--timeline-stage-padding-inline) + "
            "var(--timeline-boundary-center));",
            stylesheet,
        )
        self.assertIn(
            "right: calc(var(--timeline-stage-padding-inline) + "
            "var(--timeline-boundary-center));",
            stylesheet,
        )
        self.assertIn("transform: translate(50%, -50%);", stylesheet)
        self.assertIn(".at-tl-control:disabled { visibility: hidden; }", stylesheet)
        self.assertNotIn(".at-tl-controls {", stylesheet)
        self.assertNotIn(".at-partner__wordmark", stylesheet)
        self.assertIn('.at-tlb[data-project="arcadia"] .at-tlb__img', stylesheet)
        self.assertIn("filter: grayscale(1);", stylesheet)
        self.assertNotIn("scale(2.15)", stylesheet)
        self.assertNotIn("max-width: none; height:", stylesheet)
        self.assertIn("REDUCED_MOTION_QUERY", javascript)
        self.assertIn('(position - 1 + tabCount) % tabCount', javascript)
        self.assertIn('(position + 1) % tabCount', javascript)
        self.assertNotIn('addEventListener("mouseenter"', javascript)
        self.assertIn("height: clamp(105px, 10.5vw, 150px);", stylesheet)
        self.assertIn("font-size: clamp(16px, 1.5vw, 20px);", stylesheet)
        self.assertIn("font-size: clamp(9px, .7vw, 10px);", stylesheet)
        self.assertIn("--responsive-marker-width: calc((100% - 20px) / 3);", stylesheet)
        self.assertIn(".at-home-timeline.is-responsive-enhanced .at-tlr-rail", stylesheet)
        self.assertIn(".at-home-timeline.is-responsive-enhanced .at-tlr.is-current", stylesheet)
        self.assertIn("scroll-margin-top: 112px;", stylesheet)
        self.assertIn(".at-tlcard:focus { outline: 3px solid var(--green);", stylesheet)
        self.assertIn(".at-gallery-mosaic__overlay", stylesheet)
        self.assertIn("pointer-events: none;", stylesheet)
        self.assertIn("initializeResponsiveTimeline();", javascript)
        self.assertIn('event.key === "ArrowLeft" || event.key === "ArrowRight"', javascript)
        self.assertIn('event.key === "Enter" || event.key === " "', javascript)
        self.assertIn('card.focus({ preventScroll: true });', javascript)
        self.assertIn(
            'event.target.closest(".at-gallery-mosaic[data-project]")',
            javascript,
        )
        self.assertNotIn(
            'event.target.closest("button[data-project]:not(.at-tlb)")',
            javascript,
        )

    def test_progressive_enhancement_and_dialog_fallbacks_exist(self) -> None:
        """Keep reveal content visible without JavaScript and closed dialogs out of layout."""
        stylesheet = SHARED_ASSET_PAIRS[1][0].read_text(encoding="utf-8")
        self.assertIn(".at-fade { opacity: 1; transform: none; }", stylesheet)
        self.assertIn("dialog.at-selected-projects:not([open])", stylesheet)

    def test_gallery_dialog_uses_one_dynamic_project_heading(self) -> None:
        """Keep project names in the dialog title without repeated container headings."""
        javascript = SHARED_ASSET_PAIRS[0][0].read_text(encoding="utf-8")
        self.assertIn("activeContainer.dataset.name?.trim()", javascript)
        for route in TIMELINE_ROUTES:
            with self.subTest(route=route):
                content = (WORKSPACE_ROOT / route).read_text(encoding="utf-8")
                dialog_markup = content.split(
                    '<dialog id="selected-projects-dialog"',
                    maxsplit=1,
                )[1].split("</dialog>", maxsplit=1)[0]
                self.assertEqual(
                    7,
                    dialog_markup.count('class="at-gallery-project"'),
                )
                self.assertNotIn("<h3>", dialog_markup)


class BrowserSmokeTests(unittest.TestCase):
    """Exercise representative routes in Chrome to catch parse and runtime regressions."""

    def test_navigation_timeline_and_dialog_interactions(self) -> None:
        """Require desktop, 860px, and 320px interaction and overflow contracts."""
        with _serve_workspace() as base_url:
            for viewport in ((1280, 900), (860, 900), (320, 900)):
                with self.subTest(viewport=viewport):
                    harness_url = f"{base_url}/{INTERACTION_HARNESS_ROUTE}"
                    if viewport[0] == 320:
                        # Linux Chrome enforces a 500px outer-window minimum; the
                        # fixture constrains its responsive page canvas to 320px.
                        harness_url += "?width=320"
                    rendered_html, diagnostics = _run_chrome(
                        harness_url,
                        viewport=viewport,
                    )
                    self.assertIn('data-status="passed"', rendered_html)
                    self.assertIn(f'data-test-width="{viewport[0]}"', rendered_html)
                    if viewport[0] != 320:
                        self.assertIn(f'data-viewport="{viewport[0]}"', rendered_html)
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
