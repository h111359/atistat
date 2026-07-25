/**
 * main.js: Dependency-free interactions shared by every ATISTAT static page.
 * Provides navigation, reveal, accessible timeline, sketch, and gallery behavior.
 */
(function () {
	"use strict";

	const REVEAL_OPTIONS = {
		threshold: 0.12,
		rootMargin: "0px 0px -8% 0px"
	};
	const TIMELINE_MILESTONE_COUNT = 13;
	const TIMELINE_SCROLL_EDGE_TOLERANCE = 2;
	const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";
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
	 * Reports the position of the currently selected timeline tab.
	 *
	 * @param {HTMLElement[]} tabs - The ordered timeline tab controls.
	 * @returns {number} The zero-based selected position, or zero as a safe fallback.
	 */
	function getSelectedTimelinePosition(tabs) {
		const selectedPosition = tabs.findIndex(
			function findSelectedTimelineTab(tab) {
				return tab.getAttribute("aria-selected") === "true";
			}
		);
		return selectedPosition >= 0 ? selectedPosition : 0;
	}

	/**
	 * Synchronizes the visual track length and selected progress endpoint.
	 *
	 * @param {Object} state - The initialized timeline elements and behavior state.
	 * @returns {void}
	 */
	function updateTimelineGeometry(state) {
		const selectedTab = state.tabs[getSelectedTimelinePosition(state.tabs)];
		const progressWidth = selectedTab.offsetLeft + (selectedTab.offsetWidth / 2);
		state.timeline.style.setProperty("--timeline-track-width", `${state.rail.scrollWidth}px`);
		state.timeline.style.setProperty("--timeline-progress-width", `${progressWidth}px`);
	}

	/**
	 * Exposes whether additional milestones exist beyond either visible rail edge.
	 *
	 * @param {Object} state - The initialized timeline elements and behavior state.
	 * @returns {void}
	 */
	function updateTimelineEdges(state) {
		const maximumScroll = Math.max(0, state.rail.scrollWidth - state.rail.clientWidth);
		const hasPrevious = state.rail.scrollLeft > TIMELINE_SCROLL_EDGE_TOLERANCE;
		const hasNext = state.rail.scrollLeft
			< maximumScroll - TIMELINE_SCROLL_EDGE_TOLERANCE;
		state.timeline.classList.toggle("has-timeline-previous", hasPrevious);
		state.timeline.classList.toggle("has-timeline-next", hasNext);
	}

	/**
	 * Defers repeated scroll-edge calculations to one animation frame.
	 *
	 * @param {Object} state - The initialized timeline elements and behavior state.
	 * @returns {void}
	 */
	function scheduleTimelineEdgeUpdate(state) {
		if (state.edgeUpdateFrame !== null) {
			return;
		}
		state.edgeUpdateFrame = window.requestAnimationFrame(
			function applyScheduledTimelineEdgeUpdate() {
				state.edgeUpdateFrame = null;
				updateTimelineEdges(state);
			}
		);
	}

	/**
	 * Centers one tab unless the beginning or end of the rail prevents centering.
	 *
	 * @param {Object} state - The initialized timeline elements and behavior state.
	 * @param {HTMLElement} tab - The marker that should become visually centered.
	 * @returns {void}
	 */
	function centerTimelineTab(state, tab) {
		const maximumScroll = Math.max(0, state.rail.scrollWidth - state.rail.clientWidth);
		const desiredScroll = tab.offsetLeft - ((state.rail.clientWidth - tab.offsetWidth) / 2);
		const boundedScroll = Math.max(0, Math.min(maximumScroll, desiredScroll));
		const prefersReducedMotion = window.matchMedia(REDUCED_MOTION_QUERY).matches;
		const behavior = prefersReducedMotion ? "instant" : "smooth";
		state.rail.scrollTo({ left: boundedScroll, behavior });
		if (prefersReducedMotion) {
			updateTimelineEdges(state);
		} else {
			scheduleTimelineEdgeUpdate(state);
		}
	}

	/**
	 * Selects one timeline tab, its reciprocal panel, and its roving focus position.
	 *
	 * @param {Object} state - The initialized timeline elements and behavior state.
	 * @param {number} position - The zero-based tab position to activate.
	 * @param {boolean} shouldCenter - Whether the selected marker should be centered.
	 * @returns {void}
	 */
	function activateTimelineTab(state, position, shouldCenter) {
		state.tabs.forEach(function updateTimelineTab(tab, tabPosition) {
			const isActive = tabPosition === position;
			tab.classList.toggle("is-active", isActive);
			tab.setAttribute("aria-selected", isActive ? "true" : "false");
			tab.setAttribute("tabindex", isActive ? "0" : "-1");
		});
		state.panels.forEach(function updateTimelinePanel(panel, panelPosition) {
			const isActive = panelPosition === position;
			panel.classList.toggle("is-active", isActive);
			panel.setAttribute("aria-hidden", isActive ? "false" : "true");
		});

		state.previousControl.disabled = position === 0;
		state.nextControl.disabled = position === state.tabs.length - 1;
		state.timeline.classList.add("is-touched");
		updateTimelineGeometry(state);
		if (shouldCenter) {
			centerTimelineTab(state, state.tabs[position]);
		}
	}

	/**
	 * Moves focus to a tab without allowing the browser to perform competing page scroll.
	 *
	 * @param {Object} state - The initialized timeline elements and behavior state.
	 * @param {number} position - The zero-based tab position that should receive focus.
	 * @returns {void}
	 */
	function focusTimelineTab(state, position) {
		state.tabs[position].focus({ preventScroll: true });
	}

	/**
	 * Resolves Arrow, Home, and End keys to automatic-activation tab positions.
	 *
	 * @param {KeyboardEvent} event - The keyboard event raised by a timeline tab.
	 * @param {number} position - The zero-based position of the event's tab.
	 * @param {number} tabCount - The number of tabs in the timeline.
	 * @returns {number|null} The target tab position, or null for an unrelated key.
	 */
	function resolveTimelineKeyPosition(event, position, tabCount) {
		if (event.key === "Home") {
			return 0;
		}
		if (event.key === "End") {
			return tabCount - 1;
		}
		if (event.key === "ArrowLeft") {
			return (position - 1 + tabCount) % tabCount;
		}
		if (event.key === "ArrowRight") {
			return (position + 1) % tabCount;
		}
		return null;
	}

	/**
	 * Validates and initializes the continuous homepage timeline rail.
	 *
	 * @returns {void}
	 */
	function initializeTimeline() {
		const timeline = document.querySelector("[data-timeline]");
		if (!timeline) {
			return;
		}

		const rail = timeline.querySelector("[data-timeline-rail]");
		const previousControl = timeline.querySelector("button[data-timeline-previous][aria-label]");
		const nextControl = timeline.querySelector("button[data-timeline-next][aria-label]");
		const previousEdge = timeline.querySelector('[data-timeline-edge="previous"]');
		const nextEdge = timeline.querySelector('[data-timeline-edge="next"]');
		const tabs = Array.from(timeline.querySelectorAll('button.at-tlb[role="tab"]'));
		const panels = tabs.map(function resolveTimelinePanel(tab) {
			const controlledId = tab.getAttribute("aria-controls");
			return controlledId ? document.getElementById(controlledId) : null;
		});
		const selectedTabs = tabs.filter(function findSelectedTab(tab) {
			return tab.getAttribute("aria-selected") === "true";
		});
		const hasCompleteRelationships = panels.every(function validateTimelinePanel(panel, position) {
			return panel instanceof HTMLElement
				&& timeline.contains(panel)
				&& panel.getAttribute("role") === "tabpanel"
				&& panel.getAttribute("aria-labelledby") === tabs[position].id;
		});
		if (
			!(rail instanceof HTMLElement)
			|| !(previousControl instanceof HTMLButtonElement)
			|| !(nextControl instanceof HTMLButtonElement)
			|| !(previousEdge instanceof HTMLElement)
			|| !(nextEdge instanceof HTMLElement)
			|| tabs.length !== TIMELINE_MILESTONE_COUNT
			|| selectedTabs.length !== 1
			|| !hasCompleteRelationships
		) {
			return;
		}

		const state = {
			timeline,
			rail,
			tabs,
			panels,
			previousControl,
			nextControl,
			edgeUpdateFrame: null
		};
		tabs.forEach(function registerTimelineTab(tab, position) {
			tab.addEventListener("focus", function activateFocusedTimelineTab() {
				activateTimelineTab(state, position, true);
			});
			tab.addEventListener("click", function activateClickedTimelineTab() {
				activateTimelineTab(state, position, true);
			});
			tab.addEventListener("keydown", function navigateTimelineTabs(event) {
				const nextPosition = resolveTimelineKeyPosition(event, position, tabs.length);
				if (nextPosition === null) {
					return;
				}
				event.preventDefault();
				focusTimelineTab(state, nextPosition);
			});
		});
		previousControl.addEventListener("click", function selectPreviousTimelineTab() {
			const position = getSelectedTimelinePosition(tabs);
			focusTimelineTab(state, Math.max(0, position - 1));
		});
		nextControl.addEventListener("click", function selectNextTimelineTab() {
			const position = getSelectedTimelinePosition(tabs);
			focusTimelineTab(state, Math.min(tabs.length - 1, position + 1));
		});
		rail.addEventListener("scroll", function synchronizeTimelineEdges() {
			scheduleTimelineEdgeUpdate(state);
		}, { passive: true });
		window.addEventListener("resize", function recenterTimelineAfterResize() {
			updateTimelineGeometry(state);
			centerTimelineTab(state, tabs[getSelectedTimelinePosition(tabs)]);
		});

		// Controls and free-scrolling listeners are operational before the native scrollbar is hidden.
		activateTimelineTab(state, getSelectedTimelinePosition(tabs), true);
		timeline.classList.add("is-timeline-enhanced");
		updateTimelineEdges(state);
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

		// Timeline tabs may identify a project for styling but are never gallery launchers.
		return event.target.closest("button[data-project]:not(.at-tlb)");
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
	initializeTouchSketches();
	initializeSelectedProjectsDialog();
}());
