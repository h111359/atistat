"""
test_homepage_invariants.py: Validate static homepage invariants for R-20260725-1900.
Part of the request verification suite for timeline, gallery, localization, and Viber changes.
"""

import hashlib
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote


WORKSPACE = Path(__file__).resolve().parents[3]
ROOT_DOCUMENTS = (
    "index.html",
    "index-bg.html",
    "index-en.html",
    "index.html?lang=bg.html",
    "index.html?lang=en.html",
)
ALL_DOCUMENTS = ROOT_DOCUMENTS + ("opit/index.html",)
BG_DOCUMENTS = ("index.html", "index-bg.html", "index.html?lang=bg.html")
EN_DOCUMENTS = ("index-en.html", "index.html?lang=en.html", "opit/index.html")
PROJECT_IDS = {
    "arcadia",
    "louis-ayer",
    "bebelan",
    "power-properties",
    "montekanal",
    "elemag",
    "ubb-interlease",
}
BG_MILESTONES = (
    ("Корект Проект", "2006"),
    ("ЕОС Матрикс", "2007"),
    ("Инженерни Системи", "2008"),
    ("Монтеканал", "2011"),
    ("ЕМА", "2015"),
    ("Елемаг", "2021"),
    ("ап. Луи Айер", "2024"),
    ("ATISTAT", "2024"),
    ("ОББ Интерлийз", "2025"),
    ("ап. Аркадия", "2025"),
    ("Бебелан", "2025"),
    ("Пауър Пропъртис", "2025"),
    ("Британско училище в София", "2026"),
)
EN_MILESTONES = (
    ("Correct Project", "2006"),
    ("EOS Matrix", "2007"),
    ("Engineering Systems", "2008"),
    ("Montekanal", "2011"),
    ("EMA", "2015"),
    ("Elemag", "2021"),
    ("Apt. Louis Ayer", "2024"),
    ("ATISTAT", "2024"),
    ("UBB Interlease", "2025"),
    ("Apt. Arcadia", "2025"),
    ("Bebelan", "2025"),
    ("Power Properties", "2025"),
    ("British School of Sofia", "2026"),
)
TAB_PATTERN = re.compile(
    r'<(?:a|button)\b[^>]*class="at-tlb\b.*?</(?:a|button)>',
    re.DOTALL,
)
PANEL_PATTERN = re.compile(
    r'<article class="at-tlpanel\b.*?</article>',
    re.DOTALL,
)
CARD_PATTERN = re.compile(
    r'<li class="at-tlcard\b.*?</li>',
    re.DOTALL,
)


class StructureParser(HTMLParser):
    """Collect HTML element structure while deliberately ignoring localized text."""

    def __init__(self) -> None:
        """Initialize one parser-owned structural event list."""
        super().__init__(convert_charrefs=True)
        self.events: list[tuple[str, str, tuple[str, ...]]] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        """Record an opening tag and its attribute names."""
        self.events.append(("start", tag, tuple(sorted(name for name, _ in attrs))))

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        """Record a void element and its attribute names."""
        self.events.append(("void", tag, tuple(sorted(name for name, _ in attrs))))

    def handle_endtag(self, tag: str) -> None:
        """Record a closing tag."""
        self.events.append(("end", tag, ()))


def _extract_block(document: str, start_marker: str, end_marker: str) -> str:
    """Extract a uniquely delimited HTML block, including its closing marker."""
    start = document.index(start_marker)
    end = document.index(end_marker, start) + len(end_marker)
    return document[start:end]


def _extract_milestones(
    document: str,
    pattern: re.Pattern[str],
    name_pattern: str,
) -> tuple[tuple[str, str], ...]:
    """Return ordered milestone names and years from repeated component blocks."""
    milestones = []
    for match in pattern.finditer(document):
        block = match.group(0)
        name = re.search(name_pattern, block)
        year = re.search(r'class="at-tl(?:b|panel)__year">(\d{4})</span>', block)
        if not name or not year:
            raise AssertionError("Milestone block is missing a name or year")
        milestones.append((name.group(1), year.group(1)))
    return tuple(milestones)


def _structure(block: str) -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    """Return element structure and attribute names for localized parity checks."""
    parser = StructureParser()
    parser.feed(block)
    return tuple(parser.events)


class HomepageInvariantTests(unittest.TestCase):
    """Validate static homepage output without owning external services or resources."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load all target documents once for the test class."""
        cls.documents = {
            name: (WORKSPACE / name).read_text(encoding="utf-8")
            for name in ALL_DOCUMENTS
        }

    def test_timeline_order_and_counts(self) -> None:
        """Verify all desktop controls, panels, and mobile cards use 13 milestones."""
        for name in BG_DOCUMENTS:
            document = self.documents[name]
            self.assertEqual(
                _extract_milestones(document, TAB_PATTERN, r'alt="([^"]+)"'),
                BG_MILESTONES,
                name,
            )
            self.assertEqual(
                _extract_milestones(
                    document,
                    PANEL_PATTERN,
                    r'<h3 class="at-tlpanel__name">([^<]+)</h3>',
                ),
                BG_MILESTONES,
                name,
            )
            self.assertEqual(
                _extract_milestones(
                    document,
                    CARD_PATTERN,
                    r'<h3 class="at-tlpanel__name">([^<]+)</h3>',
                ),
                BG_MILESTONES,
                name,
            )
        for name in EN_DOCUMENTS:
            document = self.documents[name]
            self.assertEqual(
                _extract_milestones(document, TAB_PATTERN, r'alt="([^"]+)"'),
                EN_MILESTONES,
                name,
            )
            self.assertEqual(
                _extract_milestones(
                    document,
                    PANEL_PATTERN,
                    r'<h3 class="at-tlpanel__name">([^<]+)</h3>',
                ),
                EN_MILESTONES,
                name,
            )
            self.assertEqual(
                _extract_milestones(
                    document,
                    CARD_PATTERN,
                    r'<h3 class="at-tlpanel__name">([^<]+)</h3>',
                ),
                EN_MILESTONES,
                name,
            )

    def test_project_scoped_gallery_markup(self) -> None:
        """Verify launchers and dialog containers cover exactly seven projects."""
        for name, document in self.documents.items():
            launchers = re.findall(
                r'<button[^>]*class="at-gallery-mosaic"[^>]*data-project="([^"]+)"',
                document,
            )
            groups = re.findall(
                r'<div class="at-gallery-project" hidden data-project="([^"]+)"',
                document,
            )
            self.assertEqual(len(launchers), 14, name)
            self.assertEqual(set(launchers), PROJECT_IDS, name)
            self.assertTrue(all(launchers.count(project_id) == 2 for project_id in PROJECT_IDS))
            self.assertEqual(set(groups), PROJECT_IDS, name)
            self.assertEqual(len(groups), 7, name)
            self.assertNotIn("at-selected-projects__trigger", document, name)
            self.assertRegex(
                document,
                r'<dialog id="selected-projects-dialog"[^>]*aria-label="[^"]+"',
                name,
            )

    def test_localized_why_and_faq_parity(self) -> None:
        """Verify Bulgarian copies match exactly and English sections match structure."""
        section_markers = (
            '<section class="at-section at-why" id="why">',
            '<section class="at-section at-faq" id="faq">',
        )
        for marker in section_markers:
            canonical = _extract_block(self.documents["index.html"], marker, "</section>")
            for name in BG_DOCUMENTS[1:]:
                self.assertEqual(
                    _extract_block(self.documents[name], marker, "</section>"),
                    canonical,
                    name,
                )
            canonical_structure = _structure(canonical)
            for name in EN_DOCUMENTS[:2]:
                localized = _extract_block(self.documents[name], marker, "</section>")
                self.assertEqual(_structure(localized), canonical_structure, name)

    def test_viber_asset_and_controls(self) -> None:
        """Verify the untouched official icon replaces every Viber inline SVG."""
        icon_path = WORKSPACE / "wp-content/themes/atistat/assets/images/viber-icon.png"
        self.assertEqual(
            hashlib.sha256(icon_path.read_bytes()).hexdigest(),
            "29503fcfc0eb402ddd7272924808c9e58e2d43de6f14448385e0ba6cb9a97d32",
        )
        expected_counts = {
            "index.html": 2,
            "index-bg.html": 1,
            "index-en.html": 1,
            "index.html?lang=bg.html": 1,
            "index.html?lang=en.html": 1,
        }
        for name, expected_count in expected_counts.items():
            document = self.documents[name]
            self.assertEqual(document.count("viber-icon.png"), expected_count, name)
            for anchor in re.findall(
                r'<a\b(?=[^>]*href="viber://)[^>]*>.*?</a>',
                document,
                flags=re.DOTALL,
            ):
                self.assertIn("viber-icon.png", anchor, name)
                self.assertNotIn("<svg", anchor, name)

    def test_shared_assets_and_required_styles(self) -> None:
        """Verify mirrored assets and required shared interaction styles."""
        css = WORKSPACE / "wp-content/themes/atistat/assets/css/main.css"
        css_mirror = WORKSPACE / "wp-content/themes/atistat/assets/css/main.css?ver=1784544801.css"
        js = WORKSPACE / "wp-content/themes/atistat/assets/js/main.js"
        js_mirror = WORKSPACE / "wp-content/themes/atistat/assets/js/main.js?ver=1784544801"
        self.assertEqual(css.read_bytes(), css_mirror.read_bytes())
        self.assertEqual(js.read_bytes(), js_mirror.read_bytes())
        css_text = css.read_text(encoding="utf-8")
        self.assertIn("overflow-x: auto", css_text)
        self.assertIn("scroll-behavior: smooth", css_text)
        self.assertIn(".at-gallery-mosaic", css_text)
        self.assertIn(".at-viber-fab img", css_text)
        self.assertIn("@media (prefers-reduced-motion: reduce)", css_text)
        js_text = js.read_text(encoding="utf-8")
        self.assertIn('closest("button[data-project]")', js_text)
        self.assertIn('querySelectorAll("[data-project]")', js_text)
        self.assertIn("launcherToRestore.focus()", js_text)
        for name, document in self.documents.items():
            self.assertRegex(document, r"atistat-main-css[^>]+main\.css", name)
            self.assertNotIn("Additional styles for AI-proposals", document, name)

    def test_local_asset_references_resolve(self) -> None:
        """Verify every local wp-content image, script, and stylesheet path exists."""
        for name, document in self.documents.items():
            page_directory = (WORKSPACE / name).parent
            references = re.findall(
                r'(?:href|src)=["\']((?:\.\./)?wp-content/[^"\']+)["\']',
                document,
            )
            self.assertTrue(references, name)
            for reference in references:
                path_without_query = unquote(reference.split("?", 1)[0])
                resolved = (page_directory / path_without_query).resolve()
                self.assertTrue(resolved.is_file(), f"{name}: {reference}")
        opit = self.documents["opit/index.html"]
        self.assertNotRegex(opit, r'(?:href|src)=["\']wp-content/')
        self.assertNotIn("../../wp-content/", opit)

    def test_generated_timeline_assets_are_lightweight(self) -> None:
        """Verify generated WebPs use fixed ASCII names and remain below 100 KB."""
        asset_directory = WORKSPACE / "wp-content/uploads/2026/07"
        filenames = (
            "arcadia-timeline.webp",
            "louis-ayer-timeline.webp",
            "bebelan-timeline.webp",
            "power-properties-timeline.webp",
        )
        for filename in filenames:
            self.assertTrue(filename.isascii())
            path = asset_directory / filename
            self.assertTrue(path.is_file(), filename)
            self.assertLess(path.stat().st_size, 100_000, filename)


if __name__ == "__main__":
    unittest.main()
