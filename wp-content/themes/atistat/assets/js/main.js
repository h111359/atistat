/**
 * main.js: Dependency-free interactions shared by every ATISTAT static page.
 * Provides navigation, reveal, timeline, partner-card, sketch, and gallery behavior.
 */
(function () {
	"use strict";

	const REVEAL_OPTIONS = {
		threshold: 0.12,
		rootMargin: "0px 0px -8% 0px"
	};
	const TIMELINE_PROGRESS_PERCENT = 100;
	const TOUCH_POINTER_QUERY = "(hover: none)";

	/**
	 * Initializes the mobile navigation toggle and closes the menu after navigation.
	 *
	 * @returns {void}
	 */
	function initializeMobileNavigation() {
		const toggle = document.querySelector(".at-navtoggle");
		const nav = document.getElementById("at-nav");
		if (!toggle || !nav) {
			return;
		}

		toggle.addEventListener("click", function handleNavigationToggle() {
			const isOpen = nav.classList.toggle("is-open");
			toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
		});

		nav.querySelectorAll(".at-nav__link").forEach(function registerNavigationLink(link) {
			link.addEventListener("click", function closeNavigation() {
				nav.classList.remove("is-open");
				toggle.setAttribute("aria-expanded", "false");
			});
		});
	}

	/**
	 * Reveals marked sections as they enter the viewport.
	 *
	 * @returns {void}
	 */
	function initializeScrollReveal() {
		const fades = document.querySelectorAll("[data-fade]");
		if (!("IntersectionObserver" in window) || !fades.length) {
			fades.forEach(function revealImmediately(element) {
				element.classList.add("is-in");
			});
			return;
		}

		const observer = new IntersectionObserver(function revealVisibleEntries(entries) {
			entries.forEach(function revealVisibleEntry(entry) {
				if (entry.isIntersecting) {
					entry.target.classList.add("is-in");
					observer.unobserve(entry.target);
				}
			});
		}, REVEAL_OPTIONS);

		fades.forEach(function observeFade(element) {
			observer.observe(element);
		});
	}

	/**
	 * Activates a timeline panel and synchronizes its accessible tab state.
	 *
	 * @param {HTMLElement} timeline - The timeline component being updated.
	 * @param {NodeListOf<Element>} buttons - The timeline tab controls.
	 * @param {NodeListOf<Element>} panels - The timeline tab panels.
	 * @param {string} index - The data index of the panel to activate.
	 * @returns {void}
	 */
	function activateTimelinePanel(timeline, buttons, panels, index) {
		buttons.forEach(function updateTimelineButton(button) {
			const isActive = button.getAttribute("data-index") === index;
			button.classList.toggle("is-active", isActive);
			button.setAttribute("aria-selected", isActive ? "true" : "false");
		});
		panels.forEach(function updateTimelinePanel(panel) {
			const isActive = panel.getAttribute("data-panel") === index;
			panel.classList.toggle("is-active", isActive);
			panel.setAttribute("aria-hidden", isActive ? "false" : "true");
		});

		const progress = buttons.length > 1
			? (Number(index) / (buttons.length - 1)) * TIMELINE_PROGRESS_PERCENT
			: 0;
		timeline.style.setProperty("--active-progress", `${progress}%`);
		timeline.classList.add("is-touched");
	}

	/**
	 * Initializes pointer and keyboard navigation for the homepage timeline.
	 *
	 * @returns {void}
	 */
	function initializeTimeline() {
		const timeline = document.querySelector("[data-timeline]");
		if (!timeline) {
			return;
		}

		const buttons = timeline.querySelectorAll(".at-tlb");
		const panels = timeline.querySelectorAll(".at-tlpanel");
		buttons.forEach(function registerTimelineButton(button, position) {
			const index = button.getAttribute("data-index");
			const activateButtonPanel = function activateButtonPanel() {
				activateTimelinePanel(timeline, buttons, panels, index);
			};

			button.addEventListener("mouseenter", activateButtonPanel);
			button.addEventListener("focus", activateButtonPanel);
			button.addEventListener("click", activateButtonPanel);
			button.addEventListener("keydown", function navigateTimeline(event) {
				if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") {
					return;
				}

				event.preventDefault();
				const direction = event.key === "ArrowRight" ? 1 : -1;
				const nextPosition = Math.max(
					0,
					Math.min(buttons.length - 1, position + direction)
				);
				const nextButton = buttons[nextPosition];
				nextButton.focus();
				activateTimelinePanel(
					timeline,
					buttons,
					panels,
					nextButton.getAttribute("data-index")
				);
			});
		});
	}

	/**
	 * Makes timeline cards with data-href open their partner destinations.
	 *
	 * @returns {void}
	 */
	function initializeOutboundCards() {
		document.querySelectorAll("[data-href]").forEach(function registerOutboundCard(element) {
			element.addEventListener("click", function openOutboundDestination() {
				window.open(element.getAttribute("data-href"), "_blank", "noopener");
			});
		});
	}

	/**
	 * Enables tap-to-reveal behavior for non-link project sketches.
	 *
	 * @returns {void}
	 */
	function initializeTouchSketches() {
		if (!window.matchMedia(TOUCH_POINTER_QUERY).matches) {
			return;
		}

		document.querySelectorAll("figure[data-sketch]").forEach(function registerSketch(figure) {
			figure.addEventListener("click", function toggleSketch() {
				figure.classList.toggle("is-hot");
			});
		});
	}

	/**
	 * Wires the Selected Projects trigger to the native gallery dialog.
	 *
	 * @returns {void}
	 */
	function initializeSelectedProjectsDialog() {
		const trigger = document.querySelector(".at-selected-projects__trigger");
		const dialog = document.getElementById("selected-projects-dialog");
		if (
			!trigger
			|| typeof HTMLDialogElement === "undefined"
			|| !(dialog instanceof HTMLDialogElement)
		) {
			return;
		}

		const closeButton = dialog.querySelector(".at-dialog__close");
		trigger.addEventListener("click", function openSelectedProjects() {
			dialog.showModal();
			closeButton?.focus();
		});

		closeButton?.addEventListener("click", function closeSelectedProjects() {
			dialog.close();
		});
		dialog.addEventListener("close", function restoreSelectedProjectsFocus() {
			trigger.focus();
		});
	}

	document.documentElement.classList.add("has-js");
	initializeMobileNavigation();
	initializeScrollReveal();
	initializeTimeline();
	initializeOutboundCards();
	initializeTouchSketches();
	initializeSelectedProjectsDialog();
}());
