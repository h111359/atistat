"""
test_investment_instrument_mockup.py: Acceptance checks for the portable Bulgarian Analyst prototype.
Part of AIB request R-20260731-0719; validates routes, data, calculations, accessibility, exports, and file portability.
"""

from __future__ import annotations

import csv
import json
import math
import re
import shutil
import subprocess
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
PROTOTYPE_ROOT = WORKSPACE_ROOT / "workdir/investment_instrument"
SOURCE_REQUIREMENTS = WORKSPACE_ROOT / "workdir/investment_instrument_input.md"
PRIMARY_ROUTES = (
    "index.html",
    "offers.html",
    "analysis.html",
    "requirements.html",
)
PRINT_ROUTE = "print-report.html"
ALL_HTML = (*PRIMARY_ROUTES, PRINT_ROUTE)
REQUIRED_DATA = (
    "data/market-indicators.json",
    "data/source-registry.json",
    "data/offers.json",
    "data/analyses.json",
    "data/location-context.json",
)
REQUIRED_EXPORTS = (
    "exports/sample-analysis.json",
    "exports/sample-comparison.csv",
)
REQUIRED_ASSETS = (
    "assets/css/styles.css",
    "assets/fonts/bookman-cyr.woff2",
    "assets/images/atistat-logo-outlined.svg",
    "assets/js/app.js",
    "assets/js/calculations.js",
    "assets/js/demo-data.js",
)
LOCAL_REFERENCE_TAGS = {
    "a": ("href",),
    "img": ("src",),
    "link": ("href",),
    "script": ("src",),
}
NETWORK_RESOURCE_TAGS = {
    "img": ("src",),
    "link": ("href",),
    "script": ("src",),
}
OFFICIAL_PUBLISHERS = {"NSI", "BNB", "EUROSTAT", "SOFIAPLAN"}
OFFICIAL_PROVENANCE_FIELDS = {
    "publisher",
    "publisherCode",
    "sourceUrl",
    "observationDate",
    "retrievalDate",
    "unit",
    "scope",
    "preliminary",
    "licenseReuseNote",
    "transformationNote",
    "limitations",
}
OFFER_TRACEABILITY_FIELDS = {
    "id",
    "title",
    "neighborhood",
    "neighborhoodId",
    "priceEur",
    "areaSqm",
    "classification",
    "synthetic",
    "syntheticNoticeBg",
    "provenance",
    "version",
    "quality",
    "freshness",
    "duplicate",
    "hardConstraintExcluded",
    "risk",
    "confidence",
    "comparison",
}
FORBIDDEN_PRIMARY_ROUTES = {
    "offer.html",
    "comparison.html",
    "administration.html",
    "help.html",
    "future.html",
    "roadmap.html",
}


class PrototypeHtmlParser(HTMLParser):
    """Collect route references, identifiers, text, and navigation without owning resources."""

    def __init__(self) -> None:
        """Initialize parser collections and structural state."""
        super().__init__(convert_charrefs=True)
        self.identifiers: set[str] = set()
        self.duplicates: set[str] = set()
        self.language: str | None = None
        self.references: list[tuple[str, str, str]] = []
        self.landmarks: dict[str, int] = {
            "header": 0,
            "nav": 0,
            "main": 0,
            "footer": 0,
        }
        self.primary_navigation_hrefs: list[str] = []
        self._inside_primary_navigation = False
        self._primary_navigation_depth = 0
        self._inside_requirements_source = False
        self._requirements_source_parts: list[str] = []
        self.visible_text_parts: list[str] = []

    @property
    def requirements_source_text(self) -> str:
        """Return source-reader text reconstructed without empty anchor elements."""
        return "".join(self._requirements_source_parts)

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        """
        Collect relevant attributes from one HTML element.

        Args:
            tag: Parsed lowercase element name.
            attrs: Parsed element attributes.

        Returns:
            None; parser collections are updated in place.
        """
        attributes = dict(attrs)
        identifier = attributes.get("id")
        if identifier:
            if identifier in self.identifiers:
                self.duplicates.add(identifier)
            self.identifiers.add(identifier)
        if tag == "html":
            self.language = attributes.get("lang")
        if tag in self.landmarks:
            self.landmarks[tag] += 1

        classes = set((attributes.get("class") or "").split())
        if tag == "nav" and "primary-nav" in classes:
            self._inside_primary_navigation = True
            self._primary_navigation_depth = 1
        elif self._inside_primary_navigation:
            self._primary_navigation_depth += 1
        if self._inside_primary_navigation and tag == "a" and attributes.get("href"):
            self.primary_navigation_hrefs.append(attributes["href"] or "")

        if tag == "pre" and identifier == "requirements-source":
            self._inside_requirements_source = True

        for attribute in LOCAL_REFERENCE_TAGS.get(tag, ()):
            value = attributes.get(attribute)
            if value:
                self.references.append((tag, attribute, value))

    def handle_endtag(self, tag: str) -> None:
        """
        Close parser state for primary navigation and the requirements source.

        Args:
            tag: Parsed lowercase closing element name.

        Returns:
            None; parser state is updated.
        """
        if self._inside_requirements_source and tag == "pre":
            self._inside_requirements_source = False
        if self._inside_primary_navigation:
            self._primary_navigation_depth -= 1
            if self._primary_navigation_depth == 0:
                self._inside_primary_navigation = False

    def handle_data(self, data: str) -> None:
        """
        Collect visible document text and exact formatted-verbatim source text.

        Args:
            data: Decoded character data between HTML tags.

        Returns:
            None; text collections are updated.
        """
        self.visible_text_parts.append(data)
        if self._inside_requirements_source:
            self._requirements_source_parts.append(data)


def _read_json(relative_path: str) -> dict[str, Any]:
    """
    Parse a prototype JSON fixture.

    Args:
        relative_path: Path relative to the prototype root.

    Returns:
        Parsed JSON object.
    """
    return json.loads((PROTOTYPE_ROOT / relative_path).read_text(encoding="utf-8"))


def _parse_html(relative_path: str) -> PrototypeHtmlParser:
    """
    Parse a prototype HTML document.

    Args:
        relative_path: Path relative to the prototype root.

    Returns:
        Parser populated with structural metadata.
    """
    parser = PrototypeHtmlParser()
    parser.feed((PROTOTYPE_ROOT / relative_path).read_text(encoding="utf-8"))
    parser.close()
    return parser


def _resolve_local_reference(document_path: Path, reference: str) -> Path | None:
    """
    Resolve a local HTML reference while ignoring fragments and external schemes.

    Args:
        document_path: HTML document containing the reference.
        reference: Raw href or src value.

    Returns:
        Resolved filesystem path, or None for a non-local reference.
    """
    parsed = urlsplit(reference)
    if parsed.scheme or parsed.netloc or reference.startswith(("#", "mailto:", "tel:")):
        return None
    clean_path = unquote(parsed.path)
    if not clean_path:
        return None
    return (document_path.parent / clean_path).resolve()


def _extract_demo_data() -> dict[str, Any]:
    """
    Parse the stable JSON object embedded in demo-data.js.

    Returns:
        Runtime demo-data object.

    Raises:
        AssertionError: If the stable browser-global assignment is absent.
    """
    content = (PROTOTYPE_ROOT / "assets/js/demo-data.js").read_text(encoding="utf-8")
    match = re.search(
        r"window\.ATISTAT_DEMO_DATA\s*=\s*(\{.*\});\s*$",
        content,
        re.DOTALL,
    )
    if not match:
        raise AssertionError("demo-data.js lacks the stable ATISTAT_DEMO_DATA assignment")
    return json.loads(match.group(1))


def _calculation_harness_html(
    calculation_script: str,
    fixtures: list[dict[str, Any]],
    invalid_fixtures: list[dict[str, Any]],
) -> str:
    """
    Build a direct-file browser harness for valid and invalid calculation fixtures.

    Args:
        calculation_script: Complete calculations.js source.
        fixtures: Canonical valid calculator fixtures.
        invalid_fixtures: Canonical invalid-state fixtures.

    Returns:
        Self-contained HTML harness string.
    """
    fixtures_json = json.dumps(fixtures, ensure_ascii=False)
    invalid_json = json.dumps(invalid_fixtures, ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="bg">
<body data-result="pending">
<script>{calculation_script}</script>
<script>
const fixtures = {fixtures_json};
const invalidFixtures = {invalid_json};
const calculator = window.ATISTATCalculations;
const operations = {{
  acquisition: [calculator.calculateAcquisition, "totalEur"],
  repair: [calculator.calculateRepair, "totalEur"],
  loan: [calculator.calculateLoan, "monthlyPaymentEur"],
  rentMonthlyCashFlow: [calculator.calculateRentMonthlyCashFlow, "cashFlowEur"],
  flip: [calculator.calculateFlip, null],
  npv: [calculator.calculateNpv, "npvEur"],
  flipSensitivity: [calculator.calculateFlipSensitivity, null],
  roi: [calculator.calculateRoi, "roiPercent"]
}};
const failures = [];
fixtures.forEach((fixture) => {{
  const [operation, scalarField] = operations[fixture.operation];
  const result = operation(fixture.input);
  if (!result.ok) {{
    failures.push(`${{fixture.id}}:${{result.errorBg}}`);
    return;
  }}
  if (fixture.operation === "flipSensitivity") {{
    const actual = result.scenarios.map((scenario) => scenario.netProfitEur);
    fixture.expected.netProfitEur.forEach((expected, index) => {{
      if (Math.abs(actual[index] - expected) > 0.01) failures.push(`${{fixture.id}}:${{index}}`);
    }});
  }} else if (fixture.operation === "flip") {{
    Object.entries(fixture.expected).forEach(([field, expected]) => {{
      if (Math.abs(result[field] - expected) > 0.01) failures.push(`${{fixture.id}}:${{field}}`);
    }});
  }} else if (Math.abs(result[scalarField] - Object.values(fixture.expected)[0]) > 0.01) {{
    failures.push(fixture.id);
  }}
}});
invalidFixtures.forEach((fixture) => {{
  const [operation] = operations[fixture.operation];
  const result = operation(fixture.input);
  if (result.ok || !result.errorBg.includes(fixture.expectedErrorContainsBg)) {{
    failures.push(`${{fixture.id}}:invalid-state`);
  }}
}});
const negative = calculator.calculateRentMonthlyCashFlow({{
  monthlyRentEur: 500,
  vacancyRate: 0.1,
  monthlyOperatingEur: 200,
  monthlyDebtPaymentEur: 500
}});
if (!negative.ok || negative.cashFlowEur !== -250) failures.push("negative-cash-flow");
document.body.dataset.result = failures.length ? failures.join("|") : "OK";
</script>
</body>
</html>"""


def _find_chrome() -> str | None:
    """
    Find a supported local headless browser executable.

    Returns:
        Chrome or Chromium executable path, or None when unavailable.
    """
    return shutil.which("google-chrome") or shutil.which("chromium")


def _run_chrome(document_path: Path, virtual_time_budget: int = 1800) -> subprocess.CompletedProcess[str]:
    """
    Render a local HTML document through the file protocol.

    Args:
        document_path: Local HTML file to open.
        virtual_time_budget: Milliseconds allowed for deferred browser work.

    Returns:
        Completed Chrome process with captured DOM and diagnostics.
    """
    chrome = _find_chrome()
    if chrome is None:
        raise unittest.SkipTest("Chrome/Chromium is required for direct-file smoke testing")
    with tempfile.TemporaryDirectory(prefix="atistat-chrome-profile-") as profile_directory:
        return subprocess.run(
            [
                chrome,
                "--headless=new",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                f"--user-data-dir={profile_directory}",
                "--enable-logging=stderr",
                "--v=0",
                f"--virtual-time-budget={virtual_time_budget}",
                "--dump-dom",
                document_path.as_uri(),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )


class InvestmentInstrumentMockupTests(unittest.TestCase):
    """Validate the isolated investment mockup without mutating shared product state."""

    def test_required_routes_data_assets_exports_and_guidance_exist(self) -> None:
        """Verify the four-route experience, standalone print report, data, assets, and exports."""
        required = (
            *ALL_HTML,
            *REQUIRED_DATA,
            *REQUIRED_EXPORTS,
            *REQUIRED_ASSETS,
            "requirements-source.md",
            "README.txt",
        )
        missing = [path for path in required if not (PROTOTYPE_ROOT / path).is_file()]
        self.assertEqual(missing, [])
        for forbidden_route in FORBIDDEN_PRIMARY_ROUTES:
            self.assertFalse((PROTOTYPE_ROOT / forbidden_route).exists(), forbidden_route)

    def test_primary_navigation_is_exactly_four_routes_and_print_is_standalone(self) -> None:
        """Require only the selected four routes in primary navigation and no primary nav in print."""
        expected = list(PRIMARY_ROUTES)
        for route in PRIMARY_ROUTES:
            with self.subTest(route=route):
                parser = _parse_html(route)
                self.assertEqual(parser.primary_navigation_hrefs, expected)
        print_parser = _parse_html(PRINT_ROUTE)
        self.assertEqual(print_parser.primary_navigation_hrefs, [])
        self.assertGreaterEqual(print_parser.landmarks["nav"], 1)

    def test_every_html_document_is_bulgarian_experimental_and_identifier_safe(self) -> None:
        """Require Bulgarian language, a main landmark, visible boundary text, and unique IDs."""
        for route in ALL_HTML:
            with self.subTest(route=route):
                parser = _parse_html(route)
                content = (PROTOTYPE_ROOT / route).read_text(encoding="utf-8")
                self.assertEqual(parser.language, "bg")
                self.assertGreaterEqual(parser.landmarks["main"], 1)
                self.assertGreaterEqual(parser.landmarks["nav"], 1)
                self.assertEqual(parser.duplicates, set())
                self.assertIn("Вътрешен експериментален прототип", content)
                self.assertNotIn("style=", content)

    def test_local_references_resolve_and_remote_runtime_resources_are_absent(self) -> None:
        """Ensure every local reference stays inside the archive and no runtime asset is remote."""
        failures: list[str] = []
        for route in ALL_HTML:
            document = PROTOTYPE_ROOT / route
            for tag, attribute, reference in _parse_html(route).references:
                parsed = urlsplit(reference)
                if tag in NETWORK_RESOURCE_TAGS and parsed.scheme in {"http", "https"}:
                    failures.append(f"{route}: remote {tag} {reference}")
                    continue
                target = _resolve_local_reference(document, reference)
                if target is not None and not target.exists():
                    failures.append(f"{route}: missing {attribute} {reference}")
                if (
                    target is not None
                    and PROTOTYPE_ROOT not in target.parents
                    and target != PROTOTYPE_ROOT
                ):
                    failures.append(f"{route}: escaped prototype root {reference}")
        self.assertEqual(failures, [])
        scripts = "\n".join(
            (PROTOTYPE_ROOT / path).read_text(encoding="utf-8")
            for path in (
                "assets/js/app.js",
                "assets/js/calculations.js",
                "assets/js/demo-data.js",
            )
        )
        executable_scripts = re.sub(
            r"/\*.*?\*/|//[^\n]*",
            "",
            scripts,
            flags=re.DOTALL,
        )
        self.assertNotRegex(executable_scripts, r"\bfetch\s*\(")
        self.assertNotIn("XMLHttpRequest", executable_scripts)

    def test_canonical_offers_are_twelve_synthetic_eur_records_in_eight_neighborhoods(self) -> None:
        """Validate exact counts, traceability, synthetic labels, and EUR-only money fields."""
        dataset = _read_json("data/offers.json")
        offers = dataset["offers"]
        self.assertEqual(len(offers), 12)
        self.assertEqual(len({offer["neighborhoodId"] for offer in offers}), 8)
        self.assertEqual(dataset["currency"], "EUR")
        self.assertTrue(all(offer["synthetic"] for offer in offers))
        self.assertTrue(all(offer["classification"] == "synthetic" for offer in offers))
        self.assertTrue(all("СИНТЕТИЧНА" in offer["syntheticNoticeBg"] for offer in offers))
        self.assertEqual(
            sum(offer["comparison"]["selectedByDefault"] for offer in offers),
            5,
        )
        for offer in offers:
            self.assertTrue(OFFER_TRACEABILITY_FIELDS.issubset(offer))
            self.assertIsInstance(offer["priceEur"], int)
            self.assertGreater(offer["priceEur"], 0)
            self.assertTrue(math.isfinite(offer["comparison"]["pricePerSqmEur"]))

    def test_location_context_matches_offers_and_contains_no_geometry(self) -> None:
        """Require the same eight IDs, a rights block, and no copied or fabricated geometry."""
        location = _read_json("data/location-context.json")
        location_ids = {item["id"] for item in location["neighborhoods"]}
        offer_ids = {
            offer["neighborhoodId"]
            for offer in _read_json("data/offers.json")["offers"]
        }
        self.assertEqual(location_ids, offer_ids)
        self.assertEqual(len(location_ids), 8)
        self.assertEqual(location["status"], "blocked-pending-rights")
        self.assertFalse(location["source"]["licenseRightsSpecifiedForSelectedCopy"])
        self.assertEqual(
            location["source"]["geometryReuseDecision"],
            "blocked-pending-documented-rights",
        )
        forbidden_keys = {
            "coordinates",
            "geometry",
            "geometries",
            "polygon",
            "polygons",
            "features",
        }

        def collect_keys(value: Any) -> set[str]:
            """Collect nested JSON object keys for geometry-field rejection."""
            if isinstance(value, dict):
                return set(value) | {
                    nested_key
                    for nested_value in value.values()
                    for nested_key in collect_keys(nested_value)
                }
            if isinstance(value, list):
                return {
                    nested_key
                    for nested_value in value
                    for nested_key in collect_keys(nested_value)
                }
            return set()

        self.assertTrue(collect_keys(location).isdisjoint(forbidden_keys))
        self.assertEqual(list(PROTOTYPE_ROOT.rglob("*.geojson")), [])
        offers_html = (PROTOTYPE_ROOT / "offers.html").read_text(encoding="utf-8")
        self.assertNotIn("schematic-map", offers_html)
        self.assertNotIn("<svg", offers_html)
        self.assertIn("Блокирано до документирани права", offers_html)
        self.assertIn("Няма копирани или фабрикувани координати", offers_html)

    def test_runtime_demo_data_is_value_equivalent_to_all_five_json_files(self) -> None:
        """Require the direct-file browser mirror to exactly match every canonical dataset."""
        runtime = _extract_demo_data()
        self.assertEqual(runtime["offers"], _read_json("data/offers.json")["offers"])
        self.assertEqual(runtime["analyses"], _read_json("data/analyses.json"))
        self.assertEqual(
            runtime["marketIndicators"],
            _read_json("data/market-indicators.json"),
        )
        self.assertEqual(
            runtime["locationContext"],
            _read_json("data/location-context.json"),
        )
        self.assertEqual(
            runtime["sourceRegistry"],
            _read_json("data/source-registry.json"),
        )

    def test_official_snapshots_have_bounded_provenance_and_no_offer_evidence(self) -> None:
        """Require publisher, dates, units, reuse notes, limits, and evidence separation."""
        indicators = _read_json("data/market-indicators.json")
        self.assertIn("никога", indicators["noticeBg"])
        self.assertEqual(
            {record["publisherCode"] for record in indicators["records"]},
            OFFICIAL_PUBLISHERS,
        )
        for record in indicators["records"]:
            self.assertTrue(OFFICIAL_PROVENANCE_FIELDS.issubset(record))
            self.assertTrue(record["sourceUrl"].startswith("https://"))
            self.assertEqual(record["retrievalDate"], "2026-07-31")
            self.assertTrue(record["aggregateNotOfferEvidence"])
            self.assertRegex(record["limitations"], r"(Не |Няма )")
        registry = _read_json("data/source-registry.json")
        self.assertIn("никога", registry["policyBg"])
        official_sources = [
            source
            for source in registry["sources"]
            if source["type"].startswith("official")
        ]
        self.assertEqual(len(official_sources), 4)
        self.assertTrue(all(source["propertyEvidence"] is False for source in official_sources))

    def test_calculation_fixtures_and_invalid_states_run_through_file_protocol(self) -> None:
        """Execute acquisition, repair, loan, rent, flip, ROI, NPV, and sensitivity in Chrome."""
        calculations = (PROTOTYPE_ROOT / "assets/js/calculations.js").read_text(
            encoding="utf-8"
        )
        analyses = _read_json("data/analyses.json")
        harness = _calculation_harness_html(
            calculations,
            analyses["calculatorFixtures"],
            analyses["invalidStateFixtures"],
        )
        with tempfile.TemporaryDirectory(prefix="atistat-calculation-") as temp_directory:
            harness_path = Path(temp_directory) / "calculation-harness.html"
            harness_path.write_text(harness, encoding="utf-8")
            result = _run_chrome(harness_path, virtual_time_budget=1200)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('data-result="OK"', result.stdout)

    def test_versioned_storage_fallback_reset_and_analyst_only_contract_exist(self) -> None:
        """Check guarded local state, memory fallback, visible notices, reset, and omitted role state."""
        app_script = (PROTOTYPE_ROOT / "assets/js/app.js").read_text(encoding="utf-8")
        self.assertIn("STORAGE_SCHEMA_VERSION = 1", app_script)
        self.assertIn("global.localStorage", app_script)
        self.assertIn('storageMode = "memory"', app_script)
        self.assertIn("showStorageFallback", app_script)
        self.assertIn("data-action='close-dialog'", app_script)
        self.assertIn("URL.createObjectURL", app_script)
        self.assertNotIn("roleState", app_script)
        self.assertNotIn("roadmap", app_script.lower())
        for route in PRIMARY_ROUTES:
            content = (PROTOTYPE_ROOT / route).read_text(encoding="utf-8")
            self.assertIn('id="storage-notice"', content)
            self.assertIn('data-action="reset-prototype"', content)
            self.assertIn('data-role="analyst"', content)
        combined = "\n".join(
            (PROTOTYPE_ROOT / route).read_text(encoding="utf-8")
            for route in PRIMARY_ROUTES
        )
        self.assertNotIn("Превключи роля", combined)
        self.assertNotIn('data-action="role-', combined)

    def test_requirements_copy_is_identical_and_reader_contains_complete_source(self) -> None:
        """Verify byte fidelity, exact reader text, all top-level anchors, search, and source link."""
        copied = PROTOTYPE_ROOT / "requirements-source.md"
        self.assertEqual(copied.read_bytes(), SOURCE_REQUIREMENTS.read_bytes())
        source = SOURCE_REQUIREMENTS.read_text(encoding="utf-8")
        parser = _parse_html("requirements.html")
        self.assertEqual(parser.requirements_source_text, source)
        self.assertTrue(
            {f"section-{number}" for number in range(1, 22)}
            .issubset(parser.identifiers)
        )
        rendered = (PROTOTYPE_ROOT / "requirements.html").read_text(encoding="utf-8")
        self.assertIn('id="requirements-search-input"', rendered)
        self.assertIn('id="requirements-search-status"', rendered)
        self.assertIn('href="requirements-source.md"', rendered)
        self.assertIn("AC-01", rendered)
        self.assertIn("AC-40", rendered)
        self.assertIn("Матрица за проследимост", rendered)
        self.assertNotIn("__AIB_REQUIREMENTS_SOURCE__", rendered)

    def test_sample_exports_are_numeric_eur_versioned_and_spreadsheet_safe(self) -> None:
        """Validate JSON/CSV structure, provenance, warnings, and formula-injection boundaries."""
        export = _read_json("exports/sample-analysis.json")
        self.assertEqual(export["currency"], "EUR")
        self.assertTrue(export["synthetic"])
        self.assertEqual(export["classification"], "synthetic")
        self.assertEqual(export["modelVersion"], "core-demo-1.0")
        self.assertIsInstance(export["offer"]["priceEur"], int)
        self.assertIsInstance(export["assumptions"]["priceEur"], int)
        self.assertIsInstance(export["calculations"]["flipNetProfitEur"], int)
        self.assertGreaterEqual(len(export["scenarios"]), 3)
        self.assertTrue(export["provenance"]["datasetVersions"])
        self.assertTrue(export["warningBg"])
        self.assertTrue(export["limitationsBg"])
        self.assertTrue(export["humanReview"]["required"])

        with (PROTOTYPE_ROOT / "exports/sample-comparison.csv").open(
            encoding="utf-8",
            newline="",
        ) as csv_file:
            rows = list(csv.reader(csv_file))
        self.assertEqual(len(rows), 4)
        self.assertIn("цена_eur", rows[0])
        self.assertIn("ремонт_eur", rows[0])
        for row in rows[1:]:
            self.assertEqual(row[2], "synthetic")
            self.assertGreater(float(row[3]), 0)
            self.assertTrue(math.isfinite(float(row[5])))
            self.assertTrue(all(not cell.startswith(("=", "+", "-", "@")) for cell in row))

    def test_accessibility_responsive_reduced_motion_and_print_contracts_exist(self) -> None:
        """Require focus, labels, live regions, non-color states, reduced motion, and print rules."""
        styles = (PROTOTYPE_ROOT / "assets/css/styles.css").read_text(encoding="utf-8")
        app_script = (PROTOTYPE_ROOT / "assets/js/app.js").read_text(encoding="utf-8")
        combined_html = "\n".join(
            (PROTOTYPE_ROOT / route).read_text(encoding="utf-8")
            for route in ALL_HTML
        )
        self.assertIn(":focus-visible", styles)
        self.assertIn("@media (prefers-reduced-motion: reduce)", styles)
        self.assertIn("@media print", styles)
        self.assertIn(".status::before", styles)
        self.assertIn("aria-live", combined_html)
        self.assertIn("<label", (PROTOTYPE_ROOT / "offers.html").read_text(encoding="utf-8"))
        self.assertIn("<label", (PROTOTYPE_ROOT / "analysis.html").read_text(encoding="utf-8"))
        self.assertIn('event.key === "ArrowRight"', app_script)
        self.assertIn('event.key === "ArrowLeft"', app_script)
        self.assertIn('event.key === "Home"', app_script)
        self.assertIn('event.key === "End"', app_script)
        self.assertIn("<dialog", (PROTOTYPE_ROOT / "index.html").read_text(encoding="utf-8"))
        self.assertIn("showModal", app_script)
        self.assertIn("restoredDialogFocus", app_script)

    def test_print_report_contains_complete_boundary_and_report_sections(self) -> None:
        """Check report identity, example status, assumptions, evidence, decisions, and PDF guidance."""
        content = (PROTOTYPE_ROOT / PRINT_ROUTE).read_text(encoding="utf-8")
        required_markers = (
            "analysis-offer-001-v1",
            "core-demo-1.0",
            "ПРИМЕРНИ",
            "Не е реална оферта",
            "Допускания и придобиване",
            "Ремонт",
            "Финансиране",
            "Парични потоци и показатели",
            "Сценарии",
            "Чувствителност",
            "Риск и увереност",
            "Официален контекст",
            "Произход и версии",
            "Човешко решение",
            "Задължителни предупреждения",
            "Save as PDF",
            'data-action="print"',
        )
        for marker in required_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, content)
        self.assertNotIn('class="primary-nav"', content)

    def test_readme_explains_portable_operation_and_all_material_boundaries(self) -> None:
        """Require extraction, direct opening, persistence, reset, exports, sources, rights, and advice limits."""
        readme = (PROTOTYPE_ROOT / "README.txt").read_text(encoding="utf-8")
        required_markers = (
            "извлечете цялата папка",
            "index.html",
            "Не е нужна инсталация",
            "Не е нужен сървър",
            "localStorage",
            "временна памет",
            "Нулирай локалното състояние",
            "sample-analysis.json",
            "sample-comparison.csv",
            "Save as PDF",
            "НСИ",
            "БНБ",
            "Eurostat",
            "Софияплан",
            "12 оферти",
            "8 квартала",
            "не съдържа координати",
            "не е продукционна система",
            "не дава",
        )
        for marker in required_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, readme)

    def test_dashboard_offers_and_analysis_render_directly_without_script_errors(self) -> None:
        """Open all interactive routes through file:// and verify their canonical enhanced output."""
        dashboard = _run_chrome(PROTOTYPE_ROOT / "index.html", virtual_time_budget=1800)
        self.assertEqual(dashboard.returncode, 0, dashboard.stderr)
        self.assertIn('data-role="analyst"', dashboard.stdout)
        self.assertEqual(dashboard.stdout.count('class="card offer-card"'), 3)

        offers = _run_chrome(PROTOTYPE_ROOT / "offers.html", virtual_time_budget=2200)
        self.assertEqual(offers.returncode, 0, offers.stderr)
        self.assertEqual(offers.stdout.count("data-offer-id=\"offer-"), 36)
        self.assertIn("5 от максимум 5 оферти", offers.stdout)
        self.assertIn("offer-001-v1", offers.stdout)

        analysis = _run_chrome(PROTOTYPE_ROOT / "analysis.html", virtual_time_budget=2200)
        self.assertEqual(analysis.returncode, 0, analysis.stderr)
        self.assertNotIn('id="analysis-profit">—', analysis.stdout)
        self.assertNotIn('id="analysis-npv">—', analysis.stdout)

        diagnostics = "\n".join(
            (dashboard.stderr, offers.stderr, analysis.stderr)
        )
        self.assertNotIn("ReferenceError", diagnostics)
        self.assertNotIn("TypeError", diagnostics)


if __name__ == "__main__":
    unittest.main()
