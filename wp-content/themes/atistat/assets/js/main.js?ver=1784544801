/**
 * main.js: Dependency-free interactions shared by every ATISTAT static page.
 * Provides navigation, reveal, accessible timeline, selected-project links, gallery, and large-image behavior.
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
	const SELECTED_PROJECT_LINK_SELECTOR = 'a[data-selected-project-link][href^="#selected-project-"]';

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

		fades.forEach(function revealTimelineOrObserveFade(element) {
			// A 13-card responsive timeline can be taller than the observer's reachable threshold.
			if (element.hasAttribute("data-timeline")) {
				element.classList.add("is-in");
				return;
			}
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
	 * Exposes whether additional responsive markers exist beyond either rail edge.
	 *
	 * @param {Object} state - The validated responsive marker and card state.
	 * @returns {void}
	 */
	function updateResponsiveTimelineEdges(state) {
		const maximumScroll = Math.max(0, state.rail.scrollWidth - state.rail.clientWidth);
		const hasPrevious = state.rail.scrollLeft > TIMELINE_SCROLL_EDGE_TOLERANCE;
		const hasNext = state.rail.scrollLeft
			< maximumScroll - TIMELINE_SCROLL_EDGE_TOLERANCE;
		state.timeline.classList.toggle("has-responsive-previous", hasPrevious);
		state.timeline.classList.toggle("has-responsive-next", hasNext);
	}

	/**
	 * Defers responsive edge calculations so repeated scroll events share one frame.
	 *
	 * @param {Object} state - The validated responsive marker and card state.
	 * @returns {void}
	 */
	function scheduleResponsiveTimelineEdgeUpdate(state) {
		if (state.edgeUpdateFrame !== null) {
			return;
		}
		state.edgeUpdateFrame = window.requestAnimationFrame(
			function applyResponsiveTimelineEdgeUpdate() {
				state.edgeUpdateFrame = null;
				updateResponsiveTimelineEdges(state);
			}
		);
	}

	/**
	 * Centers a responsive marker without activating or scrolling to its card.
	 *
	 * @param {Object} state - The validated responsive marker and card state.
	 * @param {HTMLElement} marker - The marker that should be centered.
	 * @returns {void}
	 */
	function centerResponsiveTimelineMarker(state, marker) {
		const maximumScroll = Math.max(0, state.rail.scrollWidth - state.rail.clientWidth);
		const desiredScroll = marker.offsetLeft
			- ((state.rail.clientWidth - marker.offsetWidth) / 2);
		const boundedScroll = Math.max(0, Math.min(maximumScroll, desiredScroll));
		const prefersReducedMotion = window.matchMedia(REDUCED_MOTION_QUERY).matches;
		const behavior = prefersReducedMotion ? "instant" : "smooth";
		state.rail.scrollTo({ left: boundedScroll, behavior });
		if (prefersReducedMotion) {
			updateResponsiveTimelineEdges(state);
		} else {
			scheduleResponsiveTimelineEdgeUpdate(state);
		}
	}

	/**
	 * Moves the single responsive tab stop and optionally transfers keyboard focus.
	 *
	 * @param {Object} state - The validated responsive marker and card state.
	 * @param {number} position - Zero-based marker position that becomes tabbable.
	 * @param {boolean} shouldFocus - Whether keyboard focus should move to the marker.
	 * @returns {void}
	 */
	function setResponsiveTimelineFocus(state, position, shouldFocus) {
		state.markers.forEach(function updateResponsiveMarkerTabStop(marker, markerPosition) {
			marker.setAttribute("tabindex", markerPosition === position ? "0" : "-1");
		});
		state.focusedPosition = position;
		const marker = state.markers[position];
		if (shouldFocus) {
			marker.focus({ preventScroll: true });
		}
		centerResponsiveTimelineMarker(state, marker);
	}

	/**
	 * Activates one responsive destination and persists only that explicit selection.
	 *
	 * @param {Object} state - The validated responsive marker and card state.
	 * @param {number} position - Zero-based marker and card position to activate.
	 * @returns {void}
	 */
	function activateResponsiveTimelineMarker(state, position) {
		setResponsiveTimelineFocus(state, position, false);
		state.markers.forEach(function updateResponsiveCurrentMarker(marker, markerPosition) {
			const isCurrent = markerPosition === position;
			marker.classList.toggle("is-current", isCurrent);
			if (isCurrent) {
				marker.setAttribute("aria-current", "step");
			} else {
				marker.removeAttribute("aria-current");
			}
		});

		const behavior = window.matchMedia(REDUCED_MOTION_QUERY).matches ? "instant" : "smooth";
		const card = state.cards[position];
		card.scrollIntoView({ behavior, block: "start" });
		// preventScroll avoids a second browser-generated jump competing with the requested scroll.
		card.focus({ preventScroll: true });
	}

	/**
	 * Validates and enhances the static responsive milestone links.
	 *
	 * @returns {void}
	 */
	function initializeResponsiveTimeline() {
		const timeline = document.querySelector("[data-timeline]");
		const navigation = timeline?.querySelector("[data-responsive-timeline]");
		const rail = navigation?.querySelector("[data-responsive-timeline-rail]");
		const previousEdge = navigation?.querySelector('[data-responsive-edge="previous"]');
		const nextEdge = navigation?.querySelector('[data-responsive-edge="next"]');
		const markers = navigation
			? Array.from(navigation.querySelectorAll("a[data-responsive-marker]"))
			: [];
		const cards = timeline
			? Array.from(timeline.querySelectorAll(".at-tl-mobile > .at-tlcard"))
			: [];
		const destinations = markers.map(function resolveResponsiveDestination(marker) {
			const markerHref = marker.getAttribute("href") || "";
			const destinationId = markerHref.startsWith("#") ? markerHref.slice(1) : "";
			return destinationId ? document.getElementById(destinationId) : null;
		});
		const hasReciprocalMappings = destinations.every(
			function validateResponsiveDestination(destination, position) {
				return destination instanceof HTMLElement
					&& destination === cards[position]
					&& timeline.contains(destination)
					&& destination.getAttribute("tabindex") === "-1";
			}
		);
		const currentMarkers = markers.filter(function findResponsiveCurrentMarker(marker) {
			return marker.getAttribute("aria-current") === "step";
		});
		if (
			!(timeline instanceof HTMLElement)
			|| !(navigation instanceof HTMLElement)
			|| !(rail instanceof HTMLElement)
			|| !(previousEdge instanceof HTMLElement)
			|| !(nextEdge instanceof HTMLElement)
			|| markers.length !== TIMELINE_MILESTONE_COUNT
			|| cards.length !== TIMELINE_MILESTONE_COUNT
			|| new Set(destinations).size !== TIMELINE_MILESTONE_COUNT
			|| !hasReciprocalMappings
			|| currentMarkers.length !== 1
		) {
			return;
		}

		const initialPosition = markers.indexOf(currentMarkers[0]);
		const state = {
			timeline,
			rail,
			markers,
			cards,
			focusedPosition: initialPosition,
			edgeUpdateFrame: null
		};
		markers.forEach(function registerResponsiveMarker(marker, position) {
			marker.addEventListener("keydown", function handleResponsiveMarkerKey(event) {
				if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
					event.preventDefault();
					const direction = event.key === "ArrowLeft" ? -1 : 1;
					const nextPosition = (
						position + direction + markers.length
					) % markers.length;
					setResponsiveTimelineFocus(state, nextPosition, true);
					return;
				}
				if (event.key === "Enter" || event.key === " ") {
					event.preventDefault();
					activateResponsiveTimelineMarker(state, position);
				}
			});
			marker.addEventListener("click", function activateClickedResponsiveMarker(event) {
				event.preventDefault();
				activateResponsiveTimelineMarker(state, position);
			});
		});
		rail.addEventListener("scroll", function synchronizeResponsiveTimelineEdges() {
			scheduleResponsiveTimelineEdgeUpdate(state);
		}, { passive: true });
		window.addEventListener("resize", function recenterResponsiveTimelineAfterResize() {
			centerResponsiveTimelineMarker(state, markers[state.focusedPosition]);
			updateResponsiveTimelineEdges(state);
		});

		// Enhancement starts only after every native link resolves to its source-order card.
		timeline.classList.add("is-responsive-enhanced");
		setResponsiveTimelineFocus(state, initialPosition, false);
		updateResponsiveTimelineEdges(state);
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
	 * Scrolls selected-project links to their exact cards and transfers keyboard focus.
	 *
	 * @returns {void}
	 */
	function initializeSelectedProjectLinks() {
		document.querySelectorAll(SELECTED_PROJECT_LINK_SELECTOR).forEach(
			function registerSelectedProjectLink(link) {
				link.addEventListener("click", function focusSelectedProject(event) {
					const destinationId = link.getAttribute("href")?.slice(1);
					const destination = destinationId
						? document.getElementById(destinationId)
						: null;
					if (!(destination instanceof HTMLElement)) {
						return;
					}

					event.preventDefault();
					const prefersReducedMotion = window.matchMedia(REDUCED_MOTION_QUERY).matches;
					const behavior = prefersReducedMotion ? "auto" : "smooth";
					window.history.pushState(null, "", `#${destinationId}`);
					destination.scrollIntoView({ behavior, block: "center" });
					// preventScroll preserves the single reduced-motion-aware scroll requested above.
					destination.focus({ preventScroll: true });
				});
			}
		);
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

		// Only explicit gallery buttons open the dialog; timeline controls may also carry project metadata.
		const launcher = event.target.closest(
			".at-gallery-mosaic[data-project], .at-flagship__action[data-project]"
		);
		return launcher instanceof HTMLButtonElement ? launcher : null;
	}

	/**
	 * Filters and opens the native dialog for one project.
	 *
	 * @param {Object} state - The initialized project dialog and focus state.
	 * @param {HTMLElement} launcher - The project launcher that was activated.
	 * @returns {void}
	 */
	function openGalleryProject(state, launcher) {
		const projectId = launcher.dataset.project;
		// Programmatic and pointer activation both establish the native return target.
		launcher.focus({ preventScroll: true });
		const projectContainers = state.dialog.querySelectorAll(".at-gallery-project[data-project]");
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
			state.dialog.setAttribute("aria-label", state.defaultLabel);
			state.dialog.showModal();
			state.dialogCloseButton.focus();
			return;
		}

		activeContainer.hidden = false;
		const projectName = activeContainer.dataset.name?.trim() || state.defaultLabel;
		state.dialog.setAttribute("aria-label", projectName);
		state.dialogTitle.textContent = projectName;
		activeContainer.scrollTop = 0;
		state.dialog.showModal();
		const firstFocusable = activeContainer.querySelector(FOCUSABLE_SELECTOR);
		(firstFocusable || state.dialogCloseButton).focus();
	}

	/**
	 * Updates the viewport-filling image and its localized position announcement.
	 *
	 * @param {Object} state - The initialized project dialog and large-image state.
	 * @returns {void}
	 */
	function renderLargeImage(state) {
		const sourceImage = state.projectImages[state.imagePosition];
		state.largeImage.src = sourceImage.currentSrc || sourceImage.src;
		state.largeImage.alt = sourceImage.alt;
		state.largeImageCaption.textContent = (
			`${state.counterLabel} ${state.imagePosition + 1} / ${state.projectImages.length}`
		);
	}

	/**
	 * Opens one image within the active project's scoped large-image sequence.
	 *
	 * @param {Object} state - The initialized project dialog and large-image state.
	 * @param {HTMLImageElement} sourceImage - The gallery image selected by the visitor.
	 * @returns {void}
	 */
	function openLargeImage(state, sourceImage) {
		const projectContainer = sourceImage.closest(".at-gallery-project");
		if (!(projectContainer instanceof HTMLElement) || projectContainer.hidden) {
			return;
		}

		state.projectImages = Array.from(projectContainer.querySelectorAll(".at-gallery-grid img"));
		state.imagePosition = state.projectImages.indexOf(sourceImage);
		state.sourceImage = sourceImage;
		if (state.imagePosition < 0 || state.projectImages.length === 0) {
			return;
		}

		renderLargeImage(state);
		state.dialog.dataset.lightboxOpen = "true";
		state.dialogHeader.setAttribute("aria-hidden", "true");
		state.dialogBody.setAttribute("aria-hidden", "true");
		state.lightbox.hidden = false;
		state.lightbox.setAttribute("aria-hidden", "false");
		state.largeImageCloseButton.focus();
	}

	/**
	 * Moves to the adjacent image while remaining inside the active project.
	 *
	 * @param {Object} state - The initialized project dialog and large-image state.
	 * @param {number} direction - Minus one for previous or plus one for next.
	 * @returns {void}
	 */
	function moveLargeImage(state, direction) {
		const imageCount = state.projectImages.length;
		if (state.lightbox.hidden || imageCount === 0) {
			return;
		}
		state.imagePosition = (state.imagePosition + direction + imageCount) % imageCount;
		renderLargeImage(state);
	}

	/**
	 * Closes the large-image layer while optionally restoring focus to its source image.
	 *
	 * @param {Object} state - The initialized project dialog and large-image state.
	 * @param {boolean} shouldRestoreFocus - Whether the selected gallery image should regain focus.
	 * @returns {void}
	 */
	function closeLargeImage(state, shouldRestoreFocus) {
		if (state.lightbox.hidden) {
			return;
		}

		const imageToRestore = state.sourceImage;
		state.lightbox.hidden = true;
		state.lightbox.setAttribute("aria-hidden", "true");
		state.dialog.removeAttribute("data-lightbox-open");
		state.dialogHeader.removeAttribute("aria-hidden");
		state.dialogBody.removeAttribute("aria-hidden");
		state.largeImage.removeAttribute("src");
		state.largeImage.alt = "";
		state.projectImages = [];
		state.imagePosition = 0;
		state.sourceImage = null;
		if (shouldRestoreFocus && imageToRestore && document.contains(imageToRestore)) {
			imageToRestore.focus({ preventScroll: true });
		}
	}

	/**
	 * Enhances gallery images with button semantics and keyboard large-view activation.
	 *
	 * @param {Object} state - The initialized project dialog and large-image state.
	 * @returns {void}
	 */
	function enhanceGalleryImages(state) {
		state.dialog.querySelectorAll(".at-gallery-grid img").forEach(
			function enhanceGalleryImage(image) {
				image.setAttribute("role", "button");
				image.setAttribute("tabindex", "0");
				image.setAttribute("aria-haspopup", "dialog");
				image.setAttribute("aria-controls", state.lightbox.id);
				image.setAttribute("aria-label", `${state.imageActionLabel}: ${image.alt}`);
				image.addEventListener("click", function openClickedLargeImage() {
					openLargeImage(state, image);
				});
				image.addEventListener("keydown", function openKeyedLargeImage(event) {
					if (event.key !== "Enter" && event.key !== " ") {
						return;
					}
					event.preventDefault();
					openLargeImage(state, image);
				});
			}
		);
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
		const dialogHeader = dialog.querySelector(".at-dialog__header");
		const dialogBody = dialog.querySelector(".at-dialog__body");
		const dialogTitle = dialog.querySelector(".at-dialog__header h2");
		const lightbox = dialog.querySelector("[data-lightbox]");
		const largeImage = lightbox?.querySelector(".at-lightbox__image");
		const largeImageCaption = lightbox?.querySelector(".at-lightbox__caption");
		const largeImageCloseButton = lightbox?.querySelector(".at-lightbox__close");
		const previousImageButton = lightbox?.querySelector("[data-lightbox-previous]");
		const nextImageButton = lightbox?.querySelector("[data-lightbox-next]");
		if (
			!(closeButton instanceof HTMLButtonElement)
			|| !(dialogHeader instanceof HTMLElement)
			|| !(dialogBody instanceof HTMLElement)
			|| !(dialogTitle instanceof HTMLElement)
			|| !(lightbox instanceof HTMLElement)
			|| !(largeImage instanceof HTMLImageElement)
			|| !(largeImageCaption instanceof HTMLElement)
			|| !(largeImageCloseButton instanceof HTMLButtonElement)
			|| !(previousImageButton instanceof HTMLButtonElement)
			|| !(nextImageButton instanceof HTMLButtonElement)
		) {
			return;
		}

		const defaultLabel = dialog.getAttribute("aria-label") || "Selected projects";
		const state = {
			dialog,
			dialogHeader,
			dialogBody,
			dialogTitle,
			dialogCloseButton: closeButton,
			defaultLabel,
			lightbox,
			largeImage,
			largeImageCaption,
			largeImageCloseButton,
			previousImageButton,
			nextImageButton,
			imageActionLabel: dialog.dataset.imageActionLabel || "Open large view",
			counterLabel: dialog.dataset.counterLabel || "Image",
			projectImages: [],
			imagePosition: 0,
			sourceImage: null,
			lastGalleryLauncher: null
		};
		enhanceGalleryImages(state);
		document.addEventListener("click", function openSelectedProject(event) {
			const launcher = resolveGalleryLauncher(event);
			if (!launcher) {
				return;
			}

			state.lastGalleryLauncher = launcher;
			openGalleryProject(state, launcher);
		});
		closeButton.addEventListener("click", function closeSelectedProjects() {
			dialog.close();
		});
		largeImageCloseButton.addEventListener("click", function closeSelectedLargeImage() {
			closeLargeImage(state, true);
		});
		previousImageButton.addEventListener("click", function showPreviousLargeImage() {
			moveLargeImage(state, -1);
		});
		nextImageButton.addEventListener("click", function showNextLargeImage() {
			moveLargeImage(state, 1);
		});
		lightbox.addEventListener("click", function closeLargeImageBackdrop(event) {
			if (event.target === lightbox) {
				closeLargeImage(state, true);
			}
		});
		dialog.addEventListener("keydown", function navigateLargeImages(event) {
			if (state.lightbox.hidden) {
				return;
			}
			if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
				event.preventDefault();
				moveLargeImage(state, event.key === "ArrowLeft" ? -1 : 1);
			}
		});
		dialog.addEventListener("cancel", function closeTopmostDialogLayer(event) {
			if (!state.lightbox.hidden) {
				event.preventDefault();
				closeLargeImage(state, true);
			}
		});
		dialog.addEventListener("close", function restoreSelectedProjectsFocus() {
			closeLargeImage(state, false);
			const launcherToRestore = state.lastGalleryLauncher;
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
	initializeResponsiveTimeline();
	initializeTouchSketches();
	initializeSelectedProjectLinks();
	initializeSelectedProjectsDialog();
}());
