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
	const FOCUSABLE_SELECTOR = 'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])';

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
	 * Resolves the project gallery launcher associated with a click.
	 *
	 * @param {Event} event - The delegated document click event.
	 * @returns {HTMLElement|null} The native launcher button, when one was clicked.
	 */
	function resolveGalleryLauncher(event) {
		if (!(event.target instanceof Element)) {
			return null;
		}

		return event.target.closest("button[data-project]");
	}

	/**
	 * Filters and opens the native dialog for one project.
	 *
	 * @param {HTMLDialogElement} dialog - The shared project gallery dialog.
	 * @param {HTMLElement|null} closeButton - The dialog close button.
	 * @param {HTMLElement} launcher - The project launcher that was activated.
	 * @param {string} defaultLabel - The fallback dialog label.
	 * @returns {void}
	 */
	function openGalleryProject(dialog, closeButton, launcher, defaultLabel) {
		const projectId = launcher.dataset.project;
		// Programmatic and pointer activation both establish the native return target.
		launcher.focus({ preventScroll: true });
		const projectContainers = dialog.querySelectorAll("[data-project]");
		projectContainers.forEach(function hideGalleryProject(container) {
			container.hidden = true;
		});
		const activeContainer = Array.from(projectContainers).find(
			function matchGalleryProject(container) {
				return container.dataset.project === projectId;
			}
		);
		if (!activeContainer) {
			console.warn("Gallery project not found: " + projectId);
			closeButton?.removeAttribute("hidden");
			dialog.setAttribute("aria-label", defaultLabel);
			dialog.showModal();
			closeButton?.focus();
			return;
		}

		activeContainer.hidden = false;
		const projectHeading = activeContainer.querySelector("h3");
		const projectName = projectHeading?.textContent.trim() || defaultLabel;
		const dialogTitle = dialog.querySelector(".at-dialog__header h2");
		dialog.setAttribute("aria-label", projectName);
		if (dialogTitle) {
			dialogTitle.textContent = projectName;
		}
		activeContainer.scrollTop = 0;
		dialog.showModal();
		const firstFocusable = activeContainer.querySelector(FOCUSABLE_SELECTOR);
		(firstFocusable || closeButton)?.focus();
	}

	/**
	 * Wires all project launchers to the filtered native gallery dialog.
	 *
	 * @returns {void}
	 */
	function initializeSelectedProjectsDialog() {
		const dialog = document.getElementById("selected-projects-dialog");
		if (
			typeof HTMLDialogElement === "undefined"
			|| !(dialog instanceof HTMLDialogElement)
		) {
			return;
		}

		const closeButton = dialog.querySelector(".at-dialog__close");
		const defaultLabel = dialog.getAttribute("aria-label") || "Selected projects";
		let lastGalleryLauncher = null;
		document.addEventListener("click", function openSelectedProject(event) {
			const launcher = resolveGalleryLauncher(event);
			if (!launcher) {
				return;
			}

			lastGalleryLauncher = launcher;
			openGalleryProject(dialog, closeButton, launcher, defaultLabel);
		});
		closeButton?.addEventListener("click", function closeSelectedProjects() {
			dialog.close();
		});
		dialog.addEventListener("close", function restoreSelectedProjectsFocus() {
			const launcherToRestore = lastGalleryLauncher;
			if (launcherToRestore && document.contains(launcherToRestore)) {
				// Native dialog focus restoration completes after the close event.
				window.setTimeout(function focusGalleryLauncher() {
					if (document.contains(launcherToRestore)) {
						launcherToRestore.focus();
					}
				}, 0);
			}
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
