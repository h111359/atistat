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
TIMELINE_HEADING_COPY = {
    "bg": "ХРОНОЛОГИЯ",
    "en": "TIMELINE",
}
GALLERY_OVERLAY_LABELS = {
    "bg": "Виж галерия",
    "en": "View gallery",
}
SELECTED_PROJECTS = (
    "bebelan",
    "power-properties",
    "montekanal",
    "elemag",
    "louis-ayer",
    "arcadia",
    "ubb-interlease",
)
FLAGSHIP_PROJECTS = (
    "elemag",
    "montekanal",
    "bebelan",
    "ubb-interlease",
    "power-properties",
    "louis-ayer",
    "arcadia",
)
GALLERY_PROJECTS = SELECTED_PROJECTS
TIMELINE_ONLY_PROJECTS = (
    "eos-matrix",
    "ema",
    "british-school-sofia",
)
TIMELINE_DIALOG_PROJECTS = (*TIMELINE_ONLY_PROJECTS, *SELECTED_PROJECTS)
TIMELINE_PROJECTS = (
    "eos-matrix",
    "montekanal",
    "ema",
    "elemag",
    "louis-ayer",
    "ubb-interlease",
    "arcadia",
    "bebelan",
    "power-properties",
    "british-school-sofia",
)
TIMELINE_ONLY_PROJECT_MEDIA = {
    "eos-matrix": ("matrix-1-799x900.webp", ("799", "900")),
    "ema": ("ema-1-1100x733.webp", ("1100", "733")),
    "british-school-sofia": ("bss-1-1100x619.webp", ("1100", "619")),
}
FLAGSHIP_IMAGE_FILES = {
    "elemag": "elemag.webp",
    "bebelan": "bebelan.webp",
    "ubb-interlease": "ubb-interlease.webp",
}
FLAGSHIP_ASSET_ROOT = (
    WORKSPACE_ROOT / "wp-content/uploads/2026/07/flagship-projects"
)
SELECTED_PROJECT_COPY = {
    "bg": {
        "heading": "ИЗБРАНИ ПРОЕКТИ",
        "category_label": "Категория",
        "year_label": "Година",
        "retired_action": "Подробности и галерия",
        "projects": {
            "bebelan": {
                "title": "Административна сграда и склад на Бебелан",
                "category": "Индустриални обекти",
                "year": "2025",
                "image": "flagship-projects/bebelan.webp",
                "dimensions": ("1200", "750"),
            },
            "power-properties": {
                "title": "Сграда със смесено предназначение на Пауър Пропъртис",
                "category": "Индустриални обекти",
                "year": "2025",
                "image": "power-properties-timeline.png",
                "dimensions": ("675", "900"),
            },
            "montekanal": {
                "title": "Жилищен комплекс Монтеканал",
                "category": "Жилищни комплекси",
                "year": "2011",
                "image": "montekanal-1-1100x825.png",
                "dimensions": ("1100", "825"),
            },
            "elemag": {
                "title": "Жилищна сграда Елемаг",
                "category": "Жилищни сгради",
                "year": "2021",
                "image": "flagship-projects/elemag.webp",
                "dimensions": ("1200", "750"),
            },
            "louis-ayer": {
                "title": "Цялостен интериор на апартамент Луи Айер",
                "category": "Жилищни интериори",
                "year": "2024",
                "image": "louis-ayer-timeline.png",
                "dimensions": ("900", "675"),
            },
            "arcadia": {
                "title": "Цялостен интериор на апартамент Аркадия",
                "category": "Жилищни интериори",
                "year": "2025",
                "image": "arcadia-timeline.png",
                "dimensions": ("900", "674"),
            },
            "ubb-interlease": {
                "title": "Административна сграда „Пърл Център“ на ОББ Интерлийз",
                "category": "Офисни сгради",
                "year": "2025",
                "image": "flagship-projects/ubb-interlease.webp",
                "dimensions": ("1200", "750"),
            },
        },
    },
    "en": {
        "heading": "SELECTED PROJECTS",
        "category_label": "Category",
        "year_label": "Year",
        "retired_action": "Details and gallery",
        "projects": {
            "bebelan": {
                "title": "Administrative Building and Warehouse for Bebelan",
                "category": "Industrial Facilities",
                "year": "2025",
                "image": "flagship-projects/bebelan.webp",
                "dimensions": ("1200", "750"),
            },
            "power-properties": {
                "title": "Mixed-use Building for Power Properties",
                "category": "Industrial Facilities",
                "year": "2025",
                "image": "power-properties-timeline.png",
                "dimensions": ("675", "900"),
            },
            "montekanal": {
                "title": "Montekanal Residential Complex",
                "category": "Residential Complexes",
                "year": "2011",
                "image": "montekanal-1-1100x825.png",
                "dimensions": ("1100", "825"),
            },
            "elemag": {
                "title": "Elemag Residential Building",
                "category": "Residential Buildings",
                "year": "2021",
                "image": "flagship-projects/elemag.webp",
                "dimensions": ("1200", "750"),
            },
            "louis-ayer": {
                "title": "Complete Interior of Louis Ayer Apartment",
                "category": "Residential Interiors",
                "year": "2024",
                "image": "louis-ayer-timeline.png",
                "dimensions": ("900", "675"),
            },
            "arcadia": {
                "title": "Complete Interior of Arcadia Apartment",
                "category": "Residential Interiors",
                "year": "2025",
                "image": "arcadia-timeline.png",
                "dimensions": ("900", "674"),
            },
            "ubb-interlease": {
                "title": "UBB Interlease Pearl Center Administrative Building",
                "category": "Office Buildings",
                "year": "2025",
                "image": "flagship-projects/ubb-interlease.webp",
                "dimensions": ("1200", "750"),
            },
        },
    },
}
FLAGSHIP_PROJECT_COPY = {
    "bg": {
        "heading": "ИЗБРАНИ ПРОЕКТИ",
        "labels": ("Вид сграда", "Дейност", "Статус", "Година", "Опит"),
        "action": "Подробности и галерия",
        "projects": {
            "elemag": (
                "Елемаг",
                "Жилищна",
                "Строителство",
                "Завършена",
                "2021",
                "с Инженерни Системи",
            ),
            "montekanal": (
                "Монтеканал",
                "Жилищна",
                "Довършителни работи",
                "Завършена",
                "2011",
                "с Инженерни Системи",
            ),
            "bebelan": (
                "Бебелан",
                "Офисно-складова",
                "Довършителни работи",
                "Завършена",
                "2025",
                "с Инженерни Системи",
            ),
            "ubb-interlease": (
                "ОББ Интерлийз",
                "Офисна",
                "Довършителни работи",
                "Завършена",
                "2025",
                "с Инженерни Системи",
            ),
            "power-properties": (
                "Пауър Пропъртис",
                "Офисно-складова",
                "Довършителни работи",
                "Завършена",
                "2025",
                "с Инженерни Системи",
            ),
            "louis-ayer": (
                "ап. Луи Айер",
                "Апартамент",
                "Довършителни работи",
                "Завършен",
                "2024",
                "с АТИСТАТ",
            ),
            "arcadia": (
                "ап. Аркадия",
                "Апартамент",
                "Довършителни работи",
                "Завършен",
                "2025",
                "с АТИСТАТ",
            ),
        },
    },
    "en": {
        "heading": "SELECTED PROJECTS",
        "labels": ("Building type", "Activity", "Status", "Year", "Experience"),
        "action": "Details and gallery",
        "projects": {
            "elemag": (
                "Elemag",
                "Residential",
                "Construction works",
                "Completed",
                "2021",
                "with Engineering Systems",
            ),
            "montekanal": (
                "Montekanal",
                "Residential",
                "Fit-out works",
                "Completed",
                "2011",
                "with Engineering Systems",
            ),
            "bebelan": (
                "Bebelan",
                "Office and warehouse",
                "Fit-out works",
                "Completed",
                "2025",
                "with Engineering Systems",
            ),
            "ubb-interlease": (
                "UBB Interlease",
                "Office",
                "Fit-out works",
                "Completed",
                "2025",
                "with Engineering Systems",
            ),
            "power-properties": (
                "Power Properties",
                "Office and warehouse",
                "Fit-out works",
                "Completed",
                "2025",
                "with Engineering Systems",
            ),
            "louis-ayer": (
                "ap. Louis Ayer",
                "Apartment",
                "Fit-out works",
                "Completed",
                "2024",
                "with ATISTAT",
            ),
            "arcadia": (
                "ap. Arcadia",
                "Apartment",
                "Fit-out works",
                "Completed",
                "2025",
                "with ATISTAT",
            ),
        },
    },
}
TIMELINE_ONLY_PROJECT_COPY = {
    "bg": {
        "category_label": "Категория",
        "year_label": "Година",
        "activity_label": "Дейност",
        "projects": {
            "eos-matrix": {
                "title": "ЕОС Матрикс",
                "category": "Офис сграда",
                "year": "2007",
                "activity": (
                    "Управление и контрол на строително-инвестиционен проект"
                ),
            },
            "ema": {
                "title": "ЕМА",
                "category": "Логистична сграда",
                "year": "2015",
                "activity": "Строителство",
            },
            "british-school-sofia": {
                "title": "Британско училище в София",
                "category": "Училищна сграда",
                "year": "2026",
                "activity": "Строителство",
            },
        },
    },
    "en": {
        "category_label": "Category",
        "year_label": "Year",
        "activity_label": "Activity",
        "projects": {
            "eos-matrix": {
                "title": "EOS Matrix",
                "category": "Office building",
                "year": "2007",
                "activity": (
                    "Construction and investment project management and supervision"
                ),
            },
            "ema": {
                "title": "EMA",
                "category": "Logistics building",
                "year": "2015",
                "activity": "Construction",
            },
            "british-school-sofia": {
                "title": "British School of Sofia",
                "category": "School building",
                "year": "2026",
                "activity": "Construction",
            },
        },
    },
}
PROJECT_DIALOG_COPY = {
    "bg": {
        "labels": ("Вид сграда", "Година", "Дейност", "Опит"),
        "projects": {
            "eos-matrix": (
                "Офис сграда",
                "2007",
                "Управление и контрол на строително-инвестиционен проект",
                "с Корект Проект",
            ),
            "montekanal": (
                "Жилищна сграда",
                "2011",
                "Довършителни работи",
                "с Инженерни Системи",
            ),
            "ema": (
                "Логистична сграда",
                "2015",
                "Строителство",
                "с Инженерни Системи",
            ),
            "elemag": (
                "Жилищна сграда",
                "2021",
                "Строителство",
                "с Инженерни Системи",
            ),
            "louis-ayer": (
                "Апартамент",
                "2024",
                "Довършителни работи",
                "с АТИСТАТ",
            ),
            "ubb-interlease": (
                "Офис сграда",
                "2025",
                "Довършителни работи",
                "с Инженерни Системи",
            ),
            "arcadia": (
                "Апартамент",
                "2025",
                "Довършителни работи",
                "с АТИСТАТ",
            ),
            "bebelan": (
                "Офисно-складова сграда",
                "2025",
                "Довършителни работи",
                "с Инженерни Системи",
            ),
            "power-properties": (
                "Офисно-складова сграда",
                "2025",
                "Довършителни работи",
                "с Инженерни Системи",
            ),
            "british-school-sofia": (
                "Училищна сграда",
                "2026",
                "Строителство",
                "с Инженерни Системи",
            ),
        },
    },
    "en": {
        "labels": ("Building type", "Year", "Activity", "Experience"),
        "projects": {
            "eos-matrix": (
                "Office building",
                "2007",
                "Construction and investment project management and supervision",
                "with Correct Project",
            ),
            "montekanal": (
                "Residential building",
                "2011",
                "Fit-out works",
                "with Engineering Systems",
            ),
            "ema": (
                "Logistics building",
                "2015",
                "Construction",
                "with Engineering Systems",
            ),
            "elemag": (
                "Residential building",
                "2021",
                "Construction",
                "with Engineering Systems",
            ),
            "louis-ayer": (
                "Apartment",
                "2024",
                "Fit-out works",
                "with ATISTAT",
            ),
            "ubb-interlease": (
                "Office building",
                "2025",
                "Fit-out works",
                "with Engineering Systems",
            ),
            "arcadia": (
                "Apartment",
                "2025",
                "Fit-out works",
                "with ATISTAT",
            ),
            "bebelan": (
                "Office and warehouse building",
                "2025",
                "Fit-out works",
                "with Engineering Systems",
            ),
            "power-properties": (
                "Office and warehouse building",
                "2025",
                "Fit-out works",
                "with Engineering Systems",
            ),
            "british-school-sofia": (
                "School building",
                "2026",
                "Construction",
                "with Engineering Systems",
            ),
        },
    },
}
FINAL_ELEMAG_DESCRIPTIONS = {
    "bg": (
        "Съвременната жилищна сграда Елемаг е проектирана и изпълнена с мисъл "
        "за дълготрайност и комфорт за поколения напред. Отличава се с модерна "
        "окачена фасада с плочи от ламинам и високоефективна топлоизолация, както "
        "и с три подземни нива за гаражи, реализирани със специализирано укрепване "
        "по границите на парцела. Прецизната организация на строителните процеси "
        "и стриктният контрол на изпълнението осигуряват високо качество и "
        "завършване на обекта в определения срок."
    ),
    "en": (
        "The contemporary Elemag residential building was designed and built with "
        "durability and comfort for generations to come in mind. It features a "
        "modern curtain wall façade with Laminam slabs and high-efficiency thermal "
        "insulation, as well as three underground garage levels constructed using "
        "specialized shoring along the plot boundaries. Precise organization of the "
        "construction processes and strict execution control ensure high quality "
        "and completion of the project within the scheduled timeframe."
    ),
}
FINAL_PROVEN_EXPERIENCE_COPY = {
    "bg": (
        "26 години в бранша, много реализирани проекти от различен мащаб и тип - "
        "жилищни сгради, офиси, логистика, образование. Знаем как изглежда всеки "
        "тип предизвикателство."
    ),
    "en": (
        "With 26 years in the industry and many completed projects of different "
        "scales and types - residential buildings, offices, logistics, and "
        "education - we understand every kind of challenge."
    ),
}
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
FOOTER_SLOGANS = {
    "bg": (
        "Строителство с професионализъм,",
        "Инвестиции с визия.",
    ),
    "en": (
        "Construction with professionalism,",
        "Investments with vision.",
    ),
}
FAQ_QUOTE_COPY = {
    "bg": {
        "question": "Колко отнема изготвянето на оферта?",
        "answer": (
            "При наличие на проектна документация, количествени сметки и "
            "технически спецификации - от 3 до 15 работни дни. Времето за "
            "подготовка на оферта се определя за всяко конкретно запитване. "
            "В рамките на 48 часа от вашето запитване ще потвърдим получаването "
            "му и ще предложим удобен час за начален разговор."
        ),
        "obsolete": ("3 до 7 работни дни", "24 часа"),
    },
    "en": {
        "question": "How long does it take to prepare a quote?",
        "answer": (
            "Where project documentation, bills of quantities and technical "
            "specifications are available, preparation takes 3 to 15 working "
            "days. The time required to prepare a quote is determined for each "
            "individual enquiry. Within 48 hours of your enquiry, we will "
            "confirm receipt and propose a convenient time for an initial call."
        ),
        "obsolete": ("3 to 7 working days", "Within 24 hours"),
    },
}
FAQ_ROUTES = {
    "index.html": "bg",
    "index-bg.html": "bg",
    "index-en.html": "en",
    "index.html?lang=bg.html": "bg",
    "index.html?lang=en.html": "en",
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
        self.timeline_project_launchers: list[dict[str, str | None]] = []
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
        if tag == "button" and "at-timeline-project-launcher" in classes:
            self.timeline_project_launchers.append(attributes)
        if tag == "div" and "at-gallery-mosaic" in classes:
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
        if tag == "div" and self._active_gallery_mosaic is not None:
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
    gallery_sources = {
        project: [f"{source_root}{quote(name)}" for name in file_names]
        for project, file_names in FULL_RESOLUTION_GALLERY_FILES.items()
    }
    timeline_only_sources = {
        project: [f"{source_root}{filename}"]
        for project, (filename, _) in TIMELINE_ONLY_PROJECT_MEDIA.items()
    }
    return {**timeline_only_sources, **gallery_sources}


def _extract_flagship_markup(content: str) -> str:
    """
    Extract the single flagship-project subsection from one Experience document.

    Args:
        content: Complete HTML document text.

    Returns:
        The complete flagship subsection markup.

    Raises:
        ValueError: If the document does not contain exactly one flagship subsection.
    """
    matches = re.findall(
        r'<section class="at-flagship[^"]*"[^>]*>.*?</section>',
        content,
        flags=re.DOTALL,
    )
    if len(matches) != 1:
        raise ValueError(f"Expected one flagship subsection, found {len(matches)}")
    return matches[0]


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

    def test_footer_slogan_is_exact_localized_and_footer_only(self) -> None:
        """Require one approved two-line slogan beside every standard footer logo."""
        slogan_pattern = re.compile(
            r'<span class="at-footer__slogan">\s*'
            r"<span>([^<]+)</span>\s*"
            r"<span>([^<]+)</span>\s*"
            r"</span>"
        )
        footer_routes: list[str] = []
        for document in _html_paths():
            content = document.read_text(encoding="utf-8")
            route = str(document.relative_to(WORKSPACE_ROOT))
            if 'class="at-footer__logo"' not in content:
                self.assertNotIn('class="at-footer__slogan"', content)
                continue

            footer_routes.append(route)
            parser = _parse_document(document)
            self.assertIn(parser.language, FOOTER_SLOGANS)
            assert parser.language is not None
            footer_match = re.search(
                r'<footer class="at-footer">.*?</footer>',
                content,
                flags=re.DOTALL,
            )
            self.assertIsNotNone(footer_match)
            assert footer_match is not None
            self.assertEqual(
                [FOOTER_SLOGANS[parser.language]],
                slogan_pattern.findall(footer_match.group(0)),
                route,
            )
            self.assertEqual(1, content.count('class="at-footer__slogan"'), route)

        self.assertEqual(42, len(footer_routes))

    def test_footer_slogan_layout_has_wide_and_narrow_contracts(self) -> None:
        """Keep the slogan lower-right on wide screens and stacked below on narrow ones."""
        stylesheet = SHARED_ASSET_PAIRS[1][0].read_text(encoding="utf-8")
        self.assertRegex(
            stylesheet,
            r"\.at-footer__logo\s*\{[^}]*align-items:\s*flex-end;"
            r"[^}]*max-width:\s*100%;",
        )
        self.assertIn(".at-footer__slogan {", stylesheet)
        self.assertRegex(
            stylesheet,
            r"\.at-footer__slogan\s*\{[^}]*color:\s*var\(--ink\);",
        )
        self.assertIn(
            ".at-footer__slogan span:last-child { color: var(--green); }",
            stylesheet,
        )
        self.assertIn(
            ".at-footer__slogan span { display: block; white-space: nowrap; }",
            stylesheet,
        )
        self.assertRegex(
            stylesheet,
            r"(?s)@media \(max-width: 640px\)\s*\{"
            r".*?\.at-footer__logo\s*\{[^}]*flex-direction:\s*column;"
            r"[^}]*align-items:\s*center;",
        )

    def test_correct_project_partner_logo_has_unique_size_cap(self) -> None:
        """Limit only the six Correct Project partner marks to the approved 40px cap."""
        for route in TIMELINE_ROUTES:
            with self.subTest(route=route):
                content = (WORKSPACE_ROOT / route).read_text(encoding="utf-8")
                section_match = re.search(
                    r'<section class="at-section at-partners".*?</section>',
                    content,
                    flags=re.DOTALL,
                )
                self.assertIsNotNone(section_match)
                assert section_match is not None
                partner_section = section_match.group(0)
                self.assertEqual(
                    1,
                    partner_section.count(
                        'class="at-partner__logo--correct-project"'
                    ),
                )
                self.assertRegex(
                    partner_section,
                    r'<img class="at-partner__logo--correct-project" '
                    r'src="[^"]*correctproject\.png"',
                )
                self.assertEqual(
                    1,
                    content.count('class="at-partner__logo--correct-project"'),
                )

        stylesheet = SHARED_ASSET_PAIRS[1][0].read_text(encoding="utf-8")
        self.assertRegex(
            stylesheet,
            r"\.at-partner__link img\s*\{\s*max-height:\s*52px;",
        )
        self.assertRegex(
            stylesheet,
            r"\.at-partner__link \.at-partner__logo--correct-project\s*"
            r"\{\s*max-height:\s*40px;",
        )

    def test_quote_faq_answer_is_exact_and_localized(self) -> None:
        """Keep the approved quote lead-time answer in exactly the five FAQ routes."""
        detected_faq_routes = {
            str(document.relative_to(WORKSPACE_ROOT))
            for document in _html_paths()
            if 'class="at-section at-faq"' in document.read_text(encoding="utf-8")
        }
        self.assertEqual(set(FAQ_ROUTES), detected_faq_routes)

        for route, language in FAQ_ROUTES.items():
            with self.subTest(route=route):
                content = (WORKSPACE_ROOT / route).read_text(encoding="utf-8")
                copy = FAQ_QUOTE_COPY[language]
                question = copy["question"]
                answer = copy["answer"]
                self.assertEqual(1, content.count(f"<summary>{question}</summary>"))
                details_match = re.search(
                    rf"<details>\s*<summary>{re.escape(question)}</summary>"
                    rf".*?</details>",
                    content,
                    flags=re.DOTALL,
                )
                self.assertIsNotNone(details_match)
                assert details_match is not None
                self.assertEqual(
                    1,
                    details_match.group(0).count(f"<p>{answer}</p>"),
                )
                for obsolete_copy in copy["obsolete"]:
                    self.assertNotIn(obsolete_copy, details_match.group(0))

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

    def test_timeline_headings_are_localized_ordered_and_associated(self) -> None:
        """Require one localized heading to label every timeline after its flagship."""
        for route, (language, _) in TIMELINE_ROUTES.items():
            with self.subTest(route=route):
                content = (WORKSPACE_ROOT / route).read_text(encoding="utf-8")
                flagship_position = content.index('<section class="at-flagship')
                flagship_end_position = (
                    content.index("</section>", flagship_position) + len("</section>")
                )
                heading_markup = (
                    '<h3 class="at-timeline__title" id="timeline-title">'
                    f"{TIMELINE_HEADING_COPY[language]}</h3>"
                )
                heading_position = content.index(heading_markup)
                timeline_markup = (
                    '<div class="at-home-timeline at-fade" data-fade data-timeline '
                    'aria-labelledby="timeline-title" style="--active-progress: 25%">'
                )
                timeline_position = content.index(timeline_markup)

                self.assertEqual(1, content.count(heading_markup))
                self.assertLess(flagship_end_position, heading_position)
                self.assertLess(heading_position, timeline_position)

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
                    first_source = images[0].get("src", "") if images else ""
                    source_match = re.search(
                        r"gallery-thumbnails/([a-z-]+)-01\.webp$",
                        first_source,
                    )
                    self.assertIsNotNone(source_match)
                    project = source_match.group(1) if source_match else ""
                    self.assertIn(project, GALLERY_PROJECTS)
                    project_counts[project] += 1
                    self.assertEqual("true", attributes.get("aria-hidden"))
                    self.assertNotIn("data-project", attributes)
                    self.assertNotIn("aria-label", attributes)
                    self.assertNotIn("role", attributes)
                    self.assertNotIn("tabindex", attributes)
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

    def test_selected_projects_are_localized_complete_and_before_timeline(self) -> None:
        """Require ordered, localized metadata cards before every timeline."""
        for route, (language, asset_prefix) in TIMELINE_ROUTES.items():
            with self.subTest(route=route):
                content = (WORKSPACE_ROOT / route).read_text(encoding="utf-8")
                experience_position = content.index(
                    '<section class="at-section at-opit"'
                )
                head_position = content.index(
                    '<header class="at-opit__head',
                    experience_position,
                )
                head_end_position = content.index("</header>", head_position)
                flagship_position = content.index(
                    '<section class="at-flagship',
                    head_end_position,
                )
                timeline_position = content.index(
                    '<div class="at-home-timeline',
                    flagship_position,
                )
                self.assertLess(head_end_position, flagship_position)
                self.assertLess(flagship_position, timeline_position)

                flagship_markup = _extract_flagship_markup(content)
                localized_copy = FLAGSHIP_PROJECT_COPY[language]
                self.assertIn(
                    f'id="selected-projects-heading">'
                    f'{localized_copy["heading"]}</h3>',
                    flagship_markup,
                )
                cards = re.findall(
                    (
                        r'<article class="at-flagship__card" '
                        r'id="selected-project-([^"]+)" '
                        r'data-project="([^"]+)" tabindex="-1" '
                        r'aria-labelledby="([^"]+)">(.*?)</article>'
                    ),
                    flagship_markup,
                    flags=re.DOTALL,
                )
                self.assertEqual(
                    list(FLAGSHIP_PROJECTS),
                    [project for project, _, _, _ in cards],
                )
                self.assertTrue(
                    all(identifier == project for identifier, project, _, _ in cards)
                )
                self.assertEqual(7, flagship_markup.count('class="at-flagship__card"'))
                self.assertEqual(7, flagship_markup.count('class="at-flagship__image"'))
                self.assertEqual(7, flagship_markup.count('class="at-flagship__meta"'))
                self.assertEqual(7, flagship_markup.count('class="at-flagship__action"'))
                self.assertEqual(7, flagship_markup.count('aria-haspopup="dialog"'))
                self.assertNotIn('role="button"', flagship_markup)
                self.assertNotIn("at-flagship__category", flagship_markup)
                self.assertNotIn("at-flagship__description", flagship_markup)

                for project, _, label_identifier, card_markup in cards:
                    name, *values = localized_copy["projects"][project]
                    expected_label_identifier = f"selected-project-{project}-title"
                    self.assertEqual(expected_label_identifier, label_identifier)
                    name_markup = (
                        f'class="at-flagship__name" id="{label_identifier}">'
                        f"{name}</h4>"
                    )
                    self.assertIn(name_markup, card_markup)
                    self.assertEqual(5, card_markup.count("<dt>"))
                    self.assertEqual(5, card_markup.count("<dd>"))
                    for label, value in zip(localized_copy["labels"], values):
                        self.assertIn(
                            f"<div><dt>{label}</dt><dd>{value}</dd></div>",
                            card_markup,
                        )

                    action_markup = (
                        f'<button type="button" class="at-flagship__action" '
                        f'data-project="{project}" aria-haspopup="dialog" '
                        'aria-controls="selected-projects-dialog" '
                        f'aria-label="{localized_copy["action"]}: {name}">'
                    )
                    self.assertIn(action_markup, card_markup)
                    self.assertIn(
                        f"<span>{localized_copy['action']}</span>",
                        card_markup,
                    )

                    dialog_copy = SELECTED_PROJECT_COPY[language]["projects"][project]
                    expected_source = (
                        f"{asset_prefix}wp-content/uploads/2026/07/"
                        f'{dialog_copy["image"]}'
                    )
                    image_match = re.search(
                        (
                            r'class="at-flagship__image" '
                            f'src="{re.escape(expected_source)}" '
                            r'alt="([^"]+)" width="([^"]+)" height="([^"]+)" '
                            r'loading="lazy" decoding="async"'
                        ),
                        card_markup,
                    )
                    self.assertIsNotNone(image_match)
                    if image_match:
                        self.assertTrue(image_match.group(1))
                        self.assertEqual(
                            dialog_copy["dimensions"],
                            image_match.group(2, 3),
                        )
                    self.assertEqual(1, card_markup.count("<img "))
                    self.assertEqual(1, card_markup.count("at-flagship__name"))
                    self.assertLess(
                        card_markup.index('class="at-flagship__image"'),
                        card_markup.index(name_markup),
                    )
                    self.assertLess(
                        card_markup.index(name_markup),
                        card_markup.index('class="at-flagship__meta"'),
                    )
                    self.assertLess(
                        card_markup.index('class="at-flagship__meta"'),
                        card_markup.index(action_markup),
                    )

    def test_detailed_project_descriptions_precede_each_gallery(self) -> None:
        """Require one substantial localized description above every project gallery."""
        retired_templates = (
            "Жилищен проект от 2021 г.",
            "Офисна и складова среда от 2025 г.",
            "A 2021 residential project that brings",
            "A 2025 office and warehouse project presenting",
        )
        for route in TIMELINE_ROUTES:
            with self.subTest(route=route):
                content = (WORKSPACE_ROOT / route).read_text(encoding="utf-8")
                for retired_template in retired_templates:
                    self.assertNotIn(retired_template, content)
                for project in SELECTED_PROJECTS:
                    description_match = re.search(
                        (
                            r'<div class="at-gallery-project"[^>]*'
                            f'data-project="{re.escape(project)}"[^>]*>\\s*'
                            r'<dl class="at-gallery-project__facts">.*?</dl>\s*'
                            r'<p class="at-gallery-project__description">'
                            r"([^<]+)</p>\s*"
                            r'<div class="at-gallery-grid">'
                        ),
                        content,
                        flags=re.DOTALL,
                    )
                    self.assertIsNotNone(description_match, project)
                    if description_match:
                        self.assertGreaterEqual(len(description_match.group(1)), 180)

    def test_elemag_description_matches_final_localized_copy(self) -> None:
        """Require the approved Elemag technical description without bold markup."""
        for route, (language, _) in TIMELINE_ROUTES.items():
            with self.subTest(route=route):
                content = (WORKSPACE_ROOT / route).read_text(encoding="utf-8")
                project_start = content.index('data-project="elemag" data-name=')
                project_end = content.index(
                    '<div class="at-gallery-project"',
                    project_start + 1,
                )
                project_markup = content[project_start:project_end]
                expected = FINAL_ELEMAG_DESCRIPTIONS[language]
                self.assertIn(
                    f'<p class="at-gallery-project__description">{expected}</p>',
                    project_markup,
                )
                self.assertNotRegex(
                    project_markup,
                    r"<(?:b|strong)>[^<]*(?:лам|Laminam)",
                )

    def test_proven_experience_matches_final_localized_copy(self) -> None:
        """Require the approved many-projects claim without bold markup."""
        for route, language in FAQ_ROUTES.items():
            with self.subTest(route=route):
                content = (WORKSPACE_ROOT / route).read_text(encoding="utf-8")
                expected = FINAL_PROVEN_EXPERIENCE_COPY[language]
                self.assertIn(f"<p>{expected}</p>", content)
                self.assertNotIn("над 8 реализирани проекта", content)
                self.assertNotIn("more than 8 completed projects", content)
                self.assertNotRegex(
                    content,
                    r"<(?:b|strong)>\s*(?:много реализирани проекти|many completed projects)",
                )

    def test_timeline_project_cards_open_complete_localized_dialog_records(self) -> None:
        """Require ten full-card launchers and factual single-image records."""
        for route, (language, asset_prefix) in TIMELINE_ROUTES.items():
            with self.subTest(route=route):
                document = WORKSPACE_ROOT / route
                content = document.read_text(encoding="utf-8")
                parser = _parse_document(document)
                launcher_projects = [
                    launcher.get("data-project")
                    for launcher in parser.timeline_project_launchers
                ]
                self.assertEqual(20, len(launcher_projects))
                self.assertEqual(
                    {project: 2 for project in TIMELINE_PROJECTS},
                    {
                        project: launcher_projects.count(project)
                        for project in TIMELINE_PROJECTS
                    },
                )
                for launcher in parser.timeline_project_launchers:
                    self.assertEqual("dialog", launcher.get("aria-haspopup"))
                    self.assertEqual(
                        "selected-projects-dialog",
                        launcher.get("aria-controls"),
                    )
                    self.assertTrue(launcher.get("aria-label"))

                self.assertEqual(
                    9,
                    len(
                        re.findall(
                            (
                                r'<article class="at-tlpanel[^"]*" '
                                r'id="timeline-panel-[^"]+"[^>]*>\s*'
                                r'<button[^>]+class="at-timeline-project-launcher"'
                                r"[^>]+disabled"
                            ),
                            content,
                        )
                    ),
                )
                self.assertNotIn('class="at-selected-project-link"', content)
                self.assertNotRegex(
                    content,
                    r'<button[^>]+class="at-gallery-mosaic"',
                )

                localized_copy = TIMELINE_ONLY_PROJECT_COPY[language]
                for project in TIMELINE_ONLY_PROJECTS:
                    expected = localized_copy["projects"][project]
                    dialog_copy = PROJECT_DIALOG_COPY[language]
                    filename, dimensions = TIMELINE_ONLY_PROJECT_MEDIA[project]
                    project_match = re.search(
                        (
                            r'<div class="at-gallery-project" hidden '
                            f'data-project="{re.escape(project)}" '
                            f'data-name="{re.escape(expected["title"])}">'
                            r'(.*?</div>)(?=\s*<div class="at-gallery-project")'
                        ),
                        content,
                        flags=re.DOTALL,
                    )
                    self.assertIsNotNone(project_match, project)
                    project_markup = project_match.group(1) if project_match else ""
                    for label, value in zip(
                        dialog_copy["labels"],
                        dialog_copy["projects"][project],
                    ):
                        self.assertIn(
                            f"<div><dt>{label}</dt><dd>{value}</dd></div>",
                            project_markup,
                        )
                    self.assertEqual(4, project_markup.count("<dt>"))
                    self.assertEqual(4, project_markup.count("<dd>"))
                    self.assertIn('class="at-gallery-project__description"', project_markup)
                    self.assertNotIn('class="at-gallery-grid"', project_markup)
                    self.assertEqual(1, project_markup.count('class="at-project-image"'))
                    self.assertIn(
                        (
                            f'src="{asset_prefix}wp-content/uploads/2026/07/{filename}"'
                            f' alt="'
                        ),
                        project_markup,
                    )
                    self.assertIn(
                        f'width="{dimensions[0]}" height="{dimensions[1]}"',
                        project_markup,
                    )

    def test_flagship_assets_are_bounded_wide_webp_files(self) -> None:
        """Require exactly three optimized 1200-by-750 WebP flagship photographs."""
        actual_files = {
            path.name
            for path in FLAGSHIP_ASSET_ROOT.iterdir()
            if path.is_file()
        }
        self.assertEqual(set(FLAGSHIP_IMAGE_FILES.values()), actual_files)
        for project, filename in FLAGSHIP_IMAGE_FILES.items():
            with self.subTest(project=project):
                asset = FLAGSHIP_ASSET_ROOT / filename
                self.assertEqual((1200, 750), _read_webp_dimensions(asset))
                self.assertLessEqual(asset.stat().st_size, 300 * 1024)

    def test_flagship_styles_and_gallery_launcher_contracts_exist(self) -> None:
        """Require responsive metadata cards and accessible internal actions."""
        stylesheet = SHARED_ASSET_PAIRS[1][0].read_text(encoding="utf-8")
        self.assertIn(
            "grid-template-columns: repeat(3, minmax(0, 1fr));",
            stylesheet,
        )
        image_rule = re.search(
            r"\.at-flagship__image\s*\{([^}]+)\}",
            stylesheet,
        )
        self.assertIsNotNone(image_rule)
        image_declarations = image_rule.group(1) if image_rule else ""
        for declaration in (
            "width: 100%;",
            "height: auto;",
            "aspect-ratio: 8 / 5;",
            "object-fit: cover;",
        ):
            self.assertIn(declaration, image_declarations)

        body_rule = re.search(
            r"\.at-flagship__body\s*\{([^}]+)\}",
            stylesheet,
        )
        self.assertIsNotNone(body_rule)
        body_declarations = body_rule.group(1) if body_rule else ""
        for retired_declaration in (
            "align-items: center;",
            "gap: 10px;",
            "text-align: center;",
        ):
            self.assertNotIn(retired_declaration, body_declarations)

        name_rule = re.search(
            r"\.at-flagship__name\s*\{([^}]+)\}",
            stylesheet,
        )
        self.assertIsNotNone(name_rule)
        name_declarations = name_rule.group(1) if name_rule else ""
        for retired_declaration in (
            "display: grid;",
            "place-items: center;",
            "min-height: 2.5em;",
        ):
            self.assertNotIn(retired_declaration, name_declarations)

        self.assertIn("--flagship-control-size: 44px;", stylesheet)
        self.assertIn(".at-flagship__card:focus {", stylesheet)
        self.assertNotIn(".at-flagship__card:hover", stylesheet)
        self.assertNotIn(".at-flagship__card:focus-visible", stylesheet)
        self.assertNotIn(".at-flagship__category", stylesheet)
        for selector in (
            ".at-flagship__meta {",
            ".at-flagship__meta > div {",
            ".at-flagship__meta dt {",
            ".at-flagship__meta dd {",
            ".at-flagship__action {",
            ".at-flagship__action-icon {",
            ".at-flagship__action:hover {",
            ".at-flagship__action:focus-visible {",
        ):
            self.assertIn(selector, stylesheet)

        self.assertIn("@media (max-width: 680px)", stylesheet)
        self.assertIn(
            ".at-flagship__grid { grid-template-columns: minmax(0, 1fr); }",
            stylesheet,
        )
        shared_heading_rule = re.search(
            r"\.at-flagship__title,\s*\.at-timeline__title\s*\{([^}]+)\}",
            stylesheet,
        )
        self.assertIsNotNone(shared_heading_rule)
        heading_declarations = (
            shared_heading_rule.group(1) if shared_heading_rule else ""
        )
        for declaration in (
            "color: var(--green);",
            "font-size: clamp(1rem, 1.5vw, 1.2rem);",
            "letter-spacing: .12em;",
            "line-height: 1.25;",
            "text-transform: uppercase;",
        ):
            self.assertIn(declaration, heading_declarations)


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

                expected_destinations = set(TIMELINE_COMPANY_DESTINATIONS)
                self.assertEqual(
                    expected_destinations,
                    {link.get("href") for link in parser.timeline_panel_links},
                )
                self.assertEqual(
                    expected_destinations,
                    {link.get("href") for link in parser.timeline_mobile_links},
                )
                atistat_panel_start = content.index('id="timeline-panel-7"')
                atistat_panel_end = content.index("</article>", atistat_panel_start)
                atistat_panel = content[atistat_panel_start:atistat_panel_end]
                atistat_card_start = content.index('id="timeline-card-7"')
                atistat_card_end = content.index("</li>", atistat_card_start)
                atistat_card = content[atistat_card_start:atistat_card_end]
                for atistat_markup in (atistat_panel, atistat_card):
                    self.assertNotIn("href=", atistat_markup)
                    self.assertNotIn("at-timeline-project-launcher", atistat_markup)
                self.assertNotIn("data-href=", content)
                timeline_start = content.index(
                    '<h3 class="at-timeline__title"'
                )
                timeline_end = content.index("</section>", timeline_start)
                timeline_content = content[timeline_start:timeline_end]
                self.assertEqual(
                    3,
                    timeline_content.count(
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
            "top: var(--timeline-control-center-top); "
            "transform: translateX(-50%); pointer-events: auto;",
            stylesheet,
        )
        self.assertIn("--timeline-boundary-center: clamp(38px, 4vw, 55px);", stylesheet)
        self.assertIn(
            "--timeline-control-center-top: "
            "calc(var(--timeline-stage-padding-top) + 22px);",
            stylesheet,
        )
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
        self.assertIn("transform: translateX(50%);", stylesheet)
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
        self.assertIn('focusTarget.focus({ preventScroll: true });', javascript)
        self.assertIn("PROJECT_DIALOG_LAUNCHER_SELECTOR", javascript)
        self.assertIn("TIMELINE_PROJECT_LAUNCHER_SELECTOR", javascript)
        self.assertIn("FLAGSHIP_PROJECT_ACTION_SELECTOR", javascript)
        self.assertNotIn("FLAGSHIP_PROJECT_CARD_SELECTOR", javascript)
        self.assertNotIn(
            'event.target.closest("button[data-project]:not(.at-tlb)")',
            javascript,
        )

    def test_progressive_enhancement_and_dialog_fallbacks_exist(self) -> None:
        """Keep reveal content visible without JavaScript and closed dialogs out of layout."""
        stylesheet = SHARED_ASSET_PAIRS[1][0].read_text(encoding="utf-8")
        javascript = SHARED_ASSET_PAIRS[0][0].read_text(encoding="utf-8")
        self.assertIn(".at-fade { opacity: 1; transform: none; }", stylesheet)
        self.assertIn(
            ".has-js .at-home-timeline.at-fade "
            "{ opacity: 1; transform: none; transition: none; }",
            stylesheet,
        )
        self.assertIn('element.hasAttribute("data-timeline")', javascript)
        self.assertIn("dialog.at-selected-projects:not([open])", stylesheet)

    def test_gallery_dialog_uses_one_dynamic_project_heading(self) -> None:
        """Keep dynamic titles and exact four-field project facts in reading order."""
        javascript = SHARED_ASSET_PAIRS[0][0].read_text(encoding="utf-8")
        stylesheet = SHARED_ASSET_PAIRS[1][0].read_text(encoding="utf-8")
        self.assertIn("activeContainer.dataset.name?.trim()", javascript)
        self.assertIn(
            "grid-template-columns: repeat(2, minmax(0, 1fr));",
            stylesheet,
        )
        self.assertIn(
            "/* Stacked facts preserve the four-field reading order within "
            "narrow dialogs. */\n\t.at-gallery-project__facts {\n"
            "\t\tgrid-template-columns: 1fr;",
            stylesheet,
        )
        for route, (language, _) in TIMELINE_ROUTES.items():
            with self.subTest(route=route):
                content = (WORKSPACE_ROOT / route).read_text(encoding="utf-8")
                dialog_markup = content.split(
                    '<dialog id="selected-projects-dialog"',
                    maxsplit=1,
                )[1].split("</dialog>", maxsplit=1)[0]
                self.assertEqual(
                    len(TIMELINE_DIALOG_PROJECTS),
                    dialog_markup.count('class="at-gallery-project"'),
                )
                self.assertNotIn("<h3>", dialog_markup)
                self.assertNotRegex(
                    dialog_markup,
                    r"<dt>(?:Категория|Category|Статус|Status)</dt>",
                )
                localized_copy = PROJECT_DIALOG_COPY[language]
                for project in TIMELINE_PROJECTS:
                    project_start = dialog_markup.index(
                        f'data-project="{project}" '
                    )
                    project_end = dialog_markup.find(
                        '<div class="at-gallery-project"',
                        project_start + 1,
                    )
                    if project_end < 0:
                        project_end = len(dialog_markup)
                    project_markup = dialog_markup[project_start:project_end]
                    ordered_rows = "\n".join(
                        f"\t\t\t\t\t<div><dt>{label}</dt><dd>{value}</dd></div>"
                        for label, value in zip(
                            localized_copy["labels"],
                            localized_copy["projects"][project],
                        )
                    )
                    ordered_facts = (
                        '<dl class="at-gallery-project__facts">\n'
                        f"{ordered_rows}\n"
                        "\t\t\t\t</dl>"
                    )
                    self.assertIn(ordered_facts, project_markup)
                    self.assertEqual(4, project_markup.count("<dt>"))
                    self.assertEqual(4, project_markup.count("<dd>"))
                    self.assertLess(
                        project_markup.index("at-gallery-project__facts"),
                        project_markup.index("at-gallery-project__description"),
                    )
                    if project in SELECTED_PROJECTS:
                        self.assertLess(
                            project_markup.index("at-gallery-project__description"),
                            project_markup.index("at-gallery-grid"),
                        )

    def test_stakeholder_simplifications_and_project_links_are_consistent(self) -> None:
        """Require simplified contact/navigation UI without timeline-to-section links."""
        for route, (language, asset_prefix) in TIMELINE_ROUTES.items():
            with self.subTest(route=route):
                content = (WORKSPACE_ROOT / route).read_text(encoding="utf-8")
                for retired_markup in (
                    'class="at-stats"',
                    'class="at-contact-cta"',
                    'href="#partners"',
                    "viber://",
                    'class="at-viber-fab"',
                ):
                    self.assertNotIn(retired_markup, content)
                self.assertEqual(1, content.count("https://wa.me/359885704911"))
                self.assertEqual(1, content.count('class="at-whatsapp-fab"'))

                contacts_position = content.index(
                    '<section class="at-section at-contacts" id="contacts">'
                )
                partners_position = content.index(
                    '<section class="at-section at-partners" id="partners">'
                )
                dialog_position = content.index(
                    '<dialog id="selected-projects-dialog"'
                )
                footer_position = content.index('<footer class="at-footer">')
                self.assertLess(contacts_position, partners_position)
                self.assertLess(partners_position, dialog_position)
                self.assertLess(dialog_position, footer_position)
                for destination in (
                    "https://engsys.bg",
                    "https://correctproject.com",
                    "https://www.adreo.bg/",
                ):
                    self.assertIn(destination, content[partners_position:dialog_position])
                self.assertIn(
                    f'src="{asset_prefix}wp-content/uploads/2026/07/adreo.png"',
                    content[partners_position:dialog_position],
                )

                self.assertEqual(
                    0,
                    content.count('class="at-selected-project-link"'),
                )
                for project in SELECTED_PROJECTS:
                    self.assertEqual(
                        1,
                        content.count(
                            f'id="selected-project-{project}" '
                            f'data-project="{project}" tabindex="-1"'
                        ),
                    )

                montekanal_activity = (
                    "Довършителни работи" if language == "bg" else "Fit-out works"
                )
                self.assertRegex(
                    content,
                    (
                        r'class="at-sketch__cap"><span>'
                        r'(?:Проект Монтеканал|Project Montekanal)</span>'
                        f"<span>{re.escape(montekanal_activity)}</span>"
                    ),
                )

    def test_large_image_view_is_localized_scoped_and_focus_preserving(self) -> None:
        """Require viewport image controls, project scoping, keys, and focus restoration."""
        stylesheet = SHARED_ASSET_PAIRS[1][0].read_text(encoding="utf-8")
        javascript = SHARED_ASSET_PAIRS[0][0].read_text(encoding="utf-8")
        for declaration in (
            "dialog.at-selected-projects[data-lightbox-open]",
            "width: 100vw;",
            "height: 100dvh;",
            ".at-lightbox__image",
            "object-fit: contain;",
            ".at-lightbox__control--previous",
            ".at-lightbox__control--next",
        ):
            self.assertIn(declaration, stylesheet)
        for contract in (
            'sourceImage.closest(".at-gallery-project")',
            'projectContainer.querySelectorAll(".at-gallery-grid img")',
            'event.key === "ArrowLeft" || event.key === "ArrowRight"',
            'dialog.addEventListener("cancel"',
            "closeLargeImage(state, true);",
            "imageToRestore.focus({ preventScroll: true });",
            "launcherToRestore.focus();",
        ):
            self.assertIn(contract, javascript)

        for route, (language, _) in TIMELINE_ROUTES.items():
            with self.subTest(route=route):
                content = (WORKSPACE_ROOT / route).read_text(encoding="utf-8")
                dialog_markup = content.split(
                    '<dialog id="selected-projects-dialog"',
                    maxsplit=1,
                )[1].split("</dialog>", maxsplit=1)[0]
                self.assertEqual(
                    1,
                    dialog_markup.count('id="selected-projects-lightbox"'),
                )
                for control in (
                    'class="at-lightbox__close"',
                    "data-lightbox-previous",
                    "data-lightbox-next",
                    'class="at-lightbox__image"',
                    'aria-live="polite"',
                ):
                    self.assertIn(control, dialog_markup)
                localized_labels = (
                    ("Предишна снимка", "Следваща снимка", "Снимка")
                    if language == "bg"
                    else ("Previous image", "Next image", "Image")
                )
                for label in localized_labels:
                    self.assertIn(label, dialog_markup)


class BrowserSmokeTests(unittest.TestCase):
    """Exercise representative routes in Chrome to catch parse and runtime regressions."""

    def test_navigation_timeline_and_dialog_interactions(self) -> None:
        """Require interaction, visibility, and layout contracts from 320px upward."""
        with _serve_workspace() as base_url:
            viewports = (
                (320, 900),
                (360, 900),
                (412, 900),
                (768, 900),
                (860, 900),
                (861, 900),
                (1024, 900),
                (1440, 900),
            )
            for viewport in viewports:
                with self.subTest(viewport=viewport):
                    harness_url = f"{base_url}/{INTERACTION_HARNESS_ROUTE}"
                    if viewport[0] < 500:
                        # Linux Chrome enforces a 500px outer-window minimum; the
                        # fixture constrains its responsive page canvas to the target width.
                        harness_url += f"?width={viewport[0]}"
                    rendered_html, diagnostics = _run_chrome(
                        harness_url,
                        viewport=viewport,
                    )
                    self.assertIn('data-status="passed"', rendered_html)
                    self.assertIn(f'data-test-width="{viewport[0]}"', rendered_html)
                    if viewport[0] >= 500:
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
