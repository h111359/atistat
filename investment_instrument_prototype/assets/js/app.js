/**
 * app.js: Direct-file application controller for the Bulgarian ATISTAT prototype.
 * Provides rendering, filtering, comparison, recalculation, persistence, export, dialog, and reader interactions.
 */

(function initializeModule(global, document) {
    "use strict";

    const STORAGE_SCHEMA_VERSION = 1;
    const STORAGE_KEY = "atistat-investment-prototype";
    const MAX_COMPARISON_OFFERS = 5;
    const DEFAULT_COMPARISON_IDS = ["offer-001", "offer-003", "offer-005", "offer-007", "offer-010"];
    const EUR_FORMATTER = new Intl.NumberFormat("bg-BG", {
        style: "currency",
        currency: "EUR",
        maximumFractionDigits: 0
    });
    const DECIMAL_FORMATTER = new Intl.NumberFormat("bg-BG", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
    const data = global.ATISTAT_DEMO_DATA || null;
    const calculator = global.ATISTATCalculations || null;
    let storageMode = "local";
    let restoredDialogFocus = null;

    /**
     * Format a finite EUR value for visible Bulgarian output.
     *
     * @param {number} value - Numeric EUR amount.
     * @returns {string} Localized currency text or an em dash for invalid values.
     */
    function formatEur(value) {
        return Number.isFinite(value) ? EUR_FORMATTER.format(value) : "—";
    }

    /**
     * Escape canonical text before including it in a generated HTML template.
     *
     * @param {*} value - Candidate text value.
     * @returns {string} HTML-safe string representation.
     */
    function escapeHtml(value) {
        return String(value)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    /**
     * Create the default versioned UI state with only Analyst-workflow fields.
     *
     * @returns {Object} Fresh persisted state for the Analyst demonstrator.
     */
    function defaultState() {
        return {
            schemaVersion: STORAGE_SCHEMA_VERSION,
            selectedOfferId: "offer-001",
            comparisonIds: [...DEFAULT_COMPARISON_IDS],
            analysisAssumptions: {},
            humanDecision: null
        };
    }

    /**
     * Normalize a stored state from an earlier or malformed schema.
     *
     * @param {*} candidate - Parsed storage value.
     * @returns {Object} Current-schema state containing only supported prototype fields.
     */
    function migrateState(candidate) {
        const fallback = defaultState();
        if (!candidate || typeof candidate !== "object") {
            return fallback;
        }
        const validOfferIds = new Set(data ? data.offers.map((offer) => offer.id) : []);
        const candidateComparison = Array.isArray(candidate.comparisonIds)
            ? candidate.comparisonIds.filter((identifier) => validOfferIds.has(identifier))
            : fallback.comparisonIds;
        return {
            schemaVersion: STORAGE_SCHEMA_VERSION,
            selectedOfferId: validOfferIds.has(candidate.selectedOfferId)
                ? candidate.selectedOfferId
                : fallback.selectedOfferId,
            comparisonIds: [...new Set(candidateComparison)].slice(0, MAX_COMPARISON_OFFERS),
            analysisAssumptions: candidate.analysisAssumptions
                && typeof candidate.analysisAssumptions === "object"
                ? candidate.analysisAssumptions
                : {},
            humanDecision: typeof candidate.humanDecision === "string"
                ? candidate.humanDecision
                : null
        };
    }

    /**
     * Reveal the visible in-memory fallback status when localStorage is unavailable.
     *
     * @param {string} reasonBg - Concise Bulgarian fallback reason.
     * @returns {void} Updates the shared status notice when it exists.
     */
    function showStorageFallback(reasonBg) {
        const notice = document.querySelector("#storage-notice");
        if (!notice) {
            return;
        }
        notice.hidden = false;
        const message = notice.querySelector("[data-storage-message]");
        if (message) {
            message.textContent = reasonBg;
        }
    }

    /**
     * Create a guarded versioned persistence adapter with automatic memory fallback.
     *
     * @returns {{load: Function, save: Function, reset: Function, mode: Function}} Storage operations for prototype state.
     */
    function createStorageAdapter() {
        let memoryState = defaultState();
        let localStorageAvailable = false;
        try {
            const probeKey = `${STORAGE_KEY}-probe`;
            global.localStorage.setItem(probeKey, "1");
            global.localStorage.removeItem(probeKey);
            localStorageAvailable = true;
        } catch (error) {
            // Privacy modes and file-protocol policies can deny storage; the UI remains usable in memory.
            storageMode = "memory";
            showStorageFallback("Локалното съхранение е недостъпно. Промените се пазят само до затваряне на страницата.");
        }

        /**
         * Load and migrate the current prototype state.
         *
         * @returns {Object} Current-schema state.
         */
        function load() {
            if (!localStorageAvailable) {
                return migrateState(memoryState);
            }
            try {
                const serialized = global.localStorage.getItem(STORAGE_KEY);
                return serialized ? migrateState(JSON.parse(serialized)) : defaultState();
            } catch (error) {
                // Corrupt or newly blocked storage switches safely to a session-memory copy.
                localStorageAvailable = false;
                storageMode = "memory";
                showStorageFallback("Запазеното състояние не може да бъде прочетено. Използва се временна памет.");
                return migrateState(memoryState);
            }
        }

        /**
         * Save the supported state fields to local or in-memory persistence.
         *
         * @param {Object} nextState - Candidate current UI state.
         * @returns {Object} Normalized state that was saved.
         */
        function save(nextState) {
            const normalized = migrateState(nextState);
            memoryState = normalized;
            if (!localStorageAvailable) {
                return normalized;
            }
            try {
                global.localStorage.setItem(STORAGE_KEY, JSON.stringify(normalized));
            } catch (error) {
                // Quota and access changes must not interrupt analysis interactions.
                localStorageAvailable = false;
                storageMode = "memory";
                showStorageFallback("Промените вече се пазят временно, защото localStorage отказа запис.");
            }
            return normalized;
        }

        /**
         * Clear persisted UI state and restore demonstrator defaults.
         *
         * @returns {Object} Fresh default state.
         */
        function reset() {
            memoryState = defaultState();
            if (localStorageAvailable) {
                try {
                    global.localStorage.removeItem(STORAGE_KEY);
                } catch (error) {
                    // Reset still succeeds in memory even if the browser revokes storage between calls.
                    localStorageAvailable = false;
                    storageMode = "memory";
                    showStorageFallback("Локалният запис не можа да бъде изчистен; текущата страница е върната в начално състояние.");
                }
            }
            return defaultState();
        }

        return {
            load,
            save,
            reset,
            mode: () => storageMode
        };
    }

    const storage = createStorageAdapter();
    let state = storage.load();

    /**
     * Persist one partial UI-state update.
     *
     * @param {Object} partial - Supported fields to merge into current state.
     * @returns {Object} Saved current-schema state.
     */
    function updateState(partial) {
        state = storage.save({ ...state, ...partial });
        return state;
    }

    /**
     * Render one compact offer card for the dashboard.
     *
     * @param {Object} offer - Canonical synthetic offer.
     * @returns {string} Safe card markup.
     */
    function dashboardOfferMarkup(offer) {
        return `
            <article class="card offer-card" data-offer-id="${escapeHtml(offer.id)}">
                <div>
                    <span class="status status--info">Синтетична</span>
                    <p class="eyebrow">${escapeHtml(offer.neighborhood)}</p>
                    <h3>${escapeHtml(offer.title)}</h3>
                    <p class="offer-price">${formatEur(offer.priceEur)}</p>
                    <p class="muted">${escapeHtml(offer.areaSqm)} m² · ${escapeHtml(offer.rooms)} стаи · риск ${escapeHtml(offer.risk.band)}</p>
                </div>
                <a class="button button--secondary button--small" href="offers.html#${escapeHtml(offer.id)}">Преглед на офертата</a>
            </article>`;
    }

    /**
     * Populate the dashboard with exactly three highlighted synthetic offers.
     *
     * @returns {void} Updates dashboard markup when its container exists.
     */
    function initializeDashboard() {
        const container = document.querySelector("#highlighted-offers");
        if (!container || !data) {
            return;
        }
        const highlighted = ["offer-001", "offer-003", "offer-005"]
            .map((identifier) => data.offers.find((offer) => offer.id === identifier))
            .filter(Boolean);
        container.innerHTML = highlighted.map(dashboardOfferMarkup).join("");
    }

    /**
     * Map quality state to visible non-color Bulgarian text.
     *
     * @param {string} qualityStatus - Canonical quality code.
     * @returns {string} Localized quality label.
     */
    function qualityLabel(qualityStatus) {
        const labels = {
            complete: "Пълни данни",
            review: "Нужен преглед",
            warning: "Липсват проверки"
        };
        return labels[qualityStatus] || "Неопределено качество";
    }

    /**
     * Build a detailed offer card with native comparison and detail controls.
     *
     * @param {Object} offer - Canonical synthetic offer.
     * @returns {string} Safe offer-card markup.
     */
    function offerCardMarkup(offer) {
        const selected = state.selectedOfferId === offer.id;
        const compared = state.comparisonIds.includes(offer.id);
        const excludedClass = offer.hardConstraintExcluded ? " is-excluded" : "";
        const selectedClass = selected ? " is-selected" : "";
        const exclusion = offer.hardConstraintExcluded
            ? `<span class="status status--danger">Изключена: ${escapeHtml(offer.exclusionReasonsBg.join("; "))}</span>`
            : `<span class="status status--success">Покрива твърдите ограничения</span>`;
        const duplicate = offer.duplicate.status === "possible"
            ? `<span class="status status--warning">Възможен дубликат</span>`
            : `<span class="status status--info">Уникален запис</span>`;
        return `
            <article class="card offer-card${selectedClass}${excludedClass}" id="${escapeHtml(offer.id)}" data-offer-id="${escapeHtml(offer.id)}">
                <div>
                    <div class="cluster">
                        <span class="badge">СИНТЕТИЧНА</span>
                        ${exclusion}
                    </div>
                    <p class="eyebrow">${escapeHtml(offer.neighborhood)}</p>
                    <h3>${escapeHtml(offer.title)}</h3>
                    <p class="offer-price">${formatEur(offer.priceEur)}</p>
                    <p class="muted">${formatEur(offer.comparison.pricePerSqmEur)} / m²</p>
                    <ul class="offer-facts">
                        <li>${escapeHtml(offer.areaSqm)} m²</li>
                        <li>${escapeHtml(offer.rooms)} стаи</li>
                        <li>етаж ${escapeHtml(offer.floor)}</li>
                        <li>${escapeHtml(offer.buildYear)} г.</li>
                    </ul>
                    <div class="cluster">
                        <span class="status status--info">${escapeHtml(qualityLabel(offer.quality.status))}</span>
                        ${duplicate}
                        <span class="status status--warning">Риск ${escapeHtml(offer.risk.score)}/100</span>
                    </div>
                </div>
                <div class="offer-card-actions">
                    <!-- Native button: Enter/Space selects the synchronized detail panel; aria-pressed exposes current selection. -->
                    <button class="button button--quiet button--small" type="button" data-action="select-offer" data-offer-id="${escapeHtml(offer.id)}" aria-pressed="${selected}">
                        ${selected ? "Избрана оферта" : "Виж детайл"}
                    </button>
                    <!-- Checkbox: Space toggles comparison membership; visible text states the five-offer limit. -->
                    <label class="comparison-check">
                        <input type="checkbox" data-action="compare-offer" data-offer-id="${escapeHtml(offer.id)}" ${compared ? "checked" : ""} ${offer.hardConstraintExcluded ? "disabled" : ""}>
                        Сравни
                    </label>
                </div>
            </article>`;
    }

    /**
     * Return offers matching the active search, neighborhood, and risk filters.
     *
     * @returns {Object[]} Ordered matching offers.
     */
    function filteredOffers() {
        const search = (document.querySelector("#offer-search")?.value || "").trim().toLocaleLowerCase("bg");
        const neighborhood = document.querySelector("#neighborhood-filter")?.value || "all";
        const risk = document.querySelector("#risk-filter")?.value || "all";
        return data.offers.filter((offer) => {
            const searchTarget = `${offer.title} ${offer.neighborhood} ${offer.id}`.toLocaleLowerCase("bg");
            const matchesSearch = !search || searchTarget.includes(search);
            const matchesNeighborhood = neighborhood === "all" || offer.neighborhoodId === neighborhood;
            const matchesRisk = risk === "all" || offer.risk.band === risk;
            return matchesSearch && matchesNeighborhood && matchesRisk;
        });
    }

    /**
     * Render the selected offer provenance, quality, and due-diligence panel.
     *
     * @returns {void} Updates the sticky detail container.
     */
    function renderOfferDetail() {
        const container = document.querySelector("#offer-detail");
        const offer = data.offers.find((candidate) => candidate.id === state.selectedOfferId);
        if (!container || !offer) {
            return;
        }
        const missing = offer.quality.missingFields.length
            ? offer.quality.missingFields.join(", ")
            : "Няма в синтетичния запис";
        container.innerHTML = `
            <p class="eyebrow">Избрана оферта · ${escapeHtml(offer.id)}</p>
            <h2>${escapeHtml(offer.title)}</h2>
            <p>${escapeHtml(offer.syntheticNoticeBg)}</p>
            <dl class="detail-list">
                <dt>Цена</dt><dd>${formatEur(offer.priceEur)}</dd>
                <dt>Площ</dt><dd>${escapeHtml(offer.areaSqm)} m²</dd>
                <dt>Качество</dt><dd>${escapeHtml(offer.quality.score)}/100</dd>
                <dt>Увереност</dt><dd>${escapeHtml(offer.confidence.score)}/100</dd>
                <dt>Риск</dt><dd>${escapeHtml(offer.risk.score)}/100</dd>
                <dt>Версия</dt><dd>${escapeHtml(offer.provenance.recordVersion)}</dd>
            </dl>
            <div class="form-section">
                <h3>Произход и свежест</h3>
                <p>Локален генератор · фиксирана снимка ${escapeHtml(offer.freshness.observedAt)}.</p>
                <p class="muted">Липсващи полета: ${escapeHtml(missing)}.</p>
            </div>
            <div class="form-section">
                <h3>Due diligence</h3>
                <ul>
                    <li>Правен статус: непроверен</li>
                    <li>Технически оглед: непроведен</li>
                    <li>Пазарна съпоставка: само демонстрационна</li>
                    <li>Човешко решение: задължително</li>
                </ul>
            </div>
            <!-- Link: Enter opens the analysis route; the offer identifier remains visible in nearby text. -->
            <a class="button" href="analysis.html">Анализирай синтетичния пример</a>`;
    }

    /**
     * Render a five-offer comparison from current persisted selections.
     *
     * @returns {void} Updates comparison headings, values, and accessible status.
     */
    function renderComparison() {
        const head = document.querySelector("#comparison-head");
        const body = document.querySelector("#comparison-body");
        const status = document.querySelector("#comparison-status");
        if (!head || !body || !status) {
            return;
        }
        const compared = state.comparisonIds
            .map((identifier) => data.offers.find((offer) => offer.id === identifier))
            .filter(Boolean);
        head.innerHTML = `<tr><th scope="col">Показател</th>${compared.map((offer) => (
            `<th scope="col">${escapeHtml(offer.id)}<br>${escapeHtml(offer.neighborhood)}</th>`
        )).join("")}</tr>`;
        const rows = [
            ["Цена", (offer) => formatEur(offer.priceEur)],
            ["Цена / m²", (offer) => formatEur(offer.comparison.pricePerSqmEur)],
            ["Площ", (offer) => `${escapeHtml(offer.areaSqm)} m²`],
            ["Ремонт", (offer) => formatEur(offer.comparison.estimatedRepairEur)],
            ["Базова печалба", (offer) => formatEur(offer.comparison.baseFlipProfitEur)],
            ["Риск", (offer) => `${escapeHtml(offer.risk.score)}/100 · ${escapeHtml(offer.risk.band)}`],
            ["Увереност", (offer) => `${escapeHtml(offer.confidence.score)}/100 · ${escapeHtml(offer.confidence.band)}`]
        ];
        body.innerHTML = rows.map(([label, output]) => (
            `<tr><th scope="row">${label}</th>${compared.map((offer) => `<td>${output(offer)}</td>`).join("")}</tr>`
        )).join("");
        status.textContent = `${compared.length} от максимум ${MAX_COMPARISON_OFFERS} оферти са синхронизирани в сравнението.`;
    }

    /**
     * Render currently filtered offers and all synchronized secondary views.
     *
     * @returns {void} Updates offer grid, count, detail, and comparison.
     */
    function renderOffers() {
        const grid = document.querySelector("#offers-grid");
        const count = document.querySelector("#offer-count");
        if (!grid || !count) {
            return;
        }
        const visibleOffers = filteredOffers();
        grid.innerHTML = visibleOffers.map(offerCardMarkup).join("");
        count.textContent = `${visibleOffers.length} от ${data.offers.length} синтетични оферти`;
        renderOfferDetail();
        renderComparison();
    }

    /**
     * Handle offer selection and bounded comparison changes.
     *
     * @param {Event} event - Click or change event from the offers experience.
     * @returns {void} Persists valid interactions and re-renders synchronized views.
     */
    function handleOfferInteraction(event) {
        const target = event.target.closest("[data-action]");
        if (!target) {
            return;
        }
        const identifier = target.dataset.offerId;
        if (target.dataset.action === "select-offer") {
            updateState({ selectedOfferId: identifier });
            renderOffers();
            document.querySelector("#offer-detail")?.focus({ preventScroll: true });
            return;
        }
        if (target.dataset.action === "compare-offer") {
            const comparisonIds = new Set(state.comparisonIds);
            if (target.checked && comparisonIds.size >= MAX_COMPARISON_OFFERS) {
                target.checked = false;
                const status = document.querySelector("#comparison-status");
                if (status) {
                    status.textContent = `Могат да се сравняват до ${MAX_COMPARISON_OFFERS} оферти. Премахнете една, за да добавите друга.`;
                }
                return;
            }
            if (target.checked) {
                comparisonIds.add(identifier);
            } else {
                comparisonIds.delete(identifier);
            }
            updateState({ comparisonIds: [...comparisonIds] });
            renderOffers();
        }
    }

    /**
     * Initialize filters, selection, and comparison on the offers route.
     *
     * @returns {void} Attaches route-scoped handlers and renders canonical data.
     */
    function initializeOffers() {
        const grid = document.querySelector("#offers-grid");
        if (!grid || !data) {
            return;
        }
        const neighborhoodSelect = document.querySelector("#neighborhood-filter");
        if (neighborhoodSelect) {
            for (const neighborhood of data.locationContext.neighborhoods) {
                const option = document.createElement("option");
                option.value = neighborhood.id;
                option.textContent = neighborhood.nameBg;
                neighborhoodSelect.append(option);
            }
        }
        const filters = document.querySelector("#offer-filters");
        filters?.addEventListener("input", renderOffers);
        filters?.addEventListener("change", renderOffers);
        filters?.addEventListener("reset", () => {
            // Native reset applies values after the event; defer rendering until controls hold defaults.
            global.setTimeout(renderOffers, 0);
        });
        grid.addEventListener("click", handleOfferInteraction);
        grid.addEventListener("change", handleOfferInteraction);
        renderOffers();
    }

    /**
     * Read finite numeric assumptions from the analysis form.
     *
     * @returns {{ok: true, values: Object}|{ok: false, errorBg: string}} Parsed assumptions or first field error.
     */
    function readAnalysisForm() {
        const form = document.querySelector("#analysis-form");
        if (!form) {
            return { ok: false, errorBg: "Липсва формулярът за допускания." };
        }
        const values = {};
        for (const input of form.querySelectorAll("[data-assumption]")) {
            const numericValue = Number(input.value);
            if (!Number.isFinite(numericValue)) {
                input.setAttribute("aria-invalid", "true");
                return { ok: false, errorBg: `Полето „${input.labels?.[0]?.textContent || input.name}“ не е валидно число.` };
            }
            input.removeAttribute("aria-invalid");
            values[input.name] = numericValue;
        }
        return { ok: true, values };
    }

    /**
     * Populate visible result nodes from a completed calculation bundle.
     *
     * @param {Object} results - Successful acquisition, loan, rent, flip, NPV, and sensitivity outputs.
     * @returns {void} Updates only nodes present on the analysis route.
     */
    function displayAnalysisResults(results) {
        const outputs = {
            "analysis-acquisition": formatEur(results.acquisition.totalEur),
            "analysis-payment": formatEur(results.loan.monthlyPaymentEur),
            "analysis-cashflow": formatEur(results.rent.cashFlowEur),
            "analysis-profit": formatEur(results.flip.netProfitEur),
            "analysis-roi": `${DECIMAL_FORMATTER.format(results.flip.roiPercent)}%`,
            "analysis-npv": formatEur(results.npv.npvEur)
        };
        for (const [identifier, value] of Object.entries(outputs)) {
            const element = document.querySelector(`#${identifier}`);
            if (element) {
                element.textContent = value;
            }
        }
        const sensitivityBody = document.querySelector("#sensitivity-body");
        if (sensitivityBody) {
            sensitivityBody.innerHTML = results.sensitivity.scenarios.map((scenario) => `
                <tr>
                    <td>${scenario.change > 0 ? "+" : ""}${DECIMAL_FORMATTER.format(scenario.change * 100)}%</td>
                    <td>${formatEur(scenario.resalePriceEur)}</td>
                    <td>${formatEur(scenario.netProfitEur)}</td>
                    <td>${DECIMAL_FORMATTER.format(scenario.roiPercent)}%</td>
                    <td>${scenario.netProfitEur < 10000 ? "Да — изисква преглед" : "Не"}</td>
                </tr>`).join("");
        }
    }

    /**
     * Recalculate the full demonstrator from editable EUR assumptions.
     *
     * @param {boolean} announce - Whether to announce the update in the live region.
     * @returns {Object|null} Successful calculation bundle or null for invalid state.
     */
    function recalculateAnalysis(announce = true) {
        const live = document.querySelector("#calculation-status");
        const parsed = readAnalysisForm();
        if (!parsed.ok) {
            if (live) {
                live.textContent = parsed.errorBg;
            }
            return null;
        }
        const values = parsed.values;
        const acquisition = calculator.calculateAcquisition({
            priceEur: values.priceEur,
            transactionTaxRate: values.transactionTaxRate,
            notaryEur: values.notaryEur,
            registrationEur: values.registrationEur,
            brokerRate: values.brokerRate,
            repairEur: values.repairEur,
            bankFeesEur: values.bankFeesEur
        });
        const loan = calculator.calculateLoan({
            principalEur: values.loanPrincipalEur,
            annualRate: values.annualRate,
            months: values.loanMonths
        });
        if (!acquisition.ok || !loan.ok) {
            const failed = acquisition.ok ? loan : acquisition;
            if (live) {
                live.textContent = failed.errorBg;
            }
            return null;
        }
        const rent = calculator.calculateRentMonthlyCashFlow({
            monthlyRentEur: values.monthlyRentEur,
            vacancyRate: values.vacancyRate,
            monthlyOperatingEur: values.monthlyOperatingEur,
            monthlyDebtPaymentEur: loan.monthlyPaymentEur
        });
        const acquisitionBeforeRepairEur = acquisition.totalEur - values.repairEur;
        const flipInput = {
            acquisitionEur: acquisitionBeforeRepairEur,
            repairEur: values.repairEur,
            holdingEur: values.holdingEur,
            financingEur: values.financingEur,
            resalePriceEur: values.resalePriceEur,
            saleCostRate: values.saleCostRate
        };
        const flip = calculator.calculateFlip(flipInput);
        const npv = calculator.calculateNpv({
            cashFlowsEur: [-values.equityEur, -values.repairEur / 2, -values.repairEur / 2, flip.resaleNetEur - values.loanPrincipalEur],
            periodicDiscountRate: values.periodicDiscountRate
        });
        const sensitivity = calculator.calculateFlipSensitivity({
            baseInput: flipInput,
            resaleChanges: [-0.08, 0, 0.08]
        });
        const results = { acquisition, loan, rent, flip, npv, sensitivity, assumptions: values };
        const failureResult = Object.values(results).find((result) => result && result.ok === false);
        if (failureResult) {
            if (live) {
                live.textContent = failureResult.errorBg;
            }
            return null;
        }
        displayAnalysisResults(results);
        updateState({ analysisAssumptions: values });
        if (live && announce) {
            live.textContent = `Преизчислено: нетна печалба ${formatEur(flip.netProfitEur)}, NPV ${formatEur(npv.npvEur)}. Стойностите са примерни.`;
        }
        return results;
    }

    /**
     * Restore saved analysis assumptions into matching form controls.
     *
     * @returns {void} Applies only finite persisted numeric values.
     */
    function restoreAnalysisForm() {
        const form = document.querySelector("#analysis-form");
        if (!form) {
            return;
        }
        for (const [name, value] of Object.entries(state.analysisAssumptions)) {
            const input = form.elements.namedItem(name);
            if (input && Number.isFinite(value)) {
                input.value = String(value);
            }
        }
        if (state.humanDecision) {
            const decision = document.querySelector(`input[name="humanDecision"][value="${state.humanDecision}"]`);
            if (decision) {
                decision.checked = true;
            }
        }
    }

    /**
     * Build a machine-readable export from current calculations and canonical provenance.
     *
     * @returns {Object|null} Versioned sample analysis payload or null for invalid assumptions.
     */
    function buildAnalysisPayload() {
        const results = recalculateAnalysis(false);
        if (!results) {
            return null;
        }
        return {
            exportVersion: "1.0.0",
            analysisId: "analysis-offer-001-v1",
            analysisVersion: 1,
            modelVersion: "core-demo-1.0",
            classification: "synthetic",
            synthetic: true,
            warningBg: "Демонстрационен резултат; не е инвестиционен, правен или данъчен съвет.",
            currency: "EUR",
            offerId: "offer-001",
            assumptions: results.assumptions,
            calculations: {
                acquisitionTotalEur: results.acquisition.totalEur,
                monthlyPaymentEur: results.loan.monthlyPaymentEur,
                monthlyCashFlowEur: results.rent.cashFlowEur,
                netProfitEur: results.flip.netProfitEur,
                roiPercent: results.flip.roiPercent,
                npvEur: results.npv.npvEur
            },
            provenance: data.analyses.representativeAnalysis.sourceVersions,
            humanReview: {
                required: true,
                status: state.humanDecision ? "draft-selected" : "pending",
                decision: state.humanDecision
            }
        };
    }

    /**
     * Build a comparison CSV from current bounded offer selections.
     *
     * @returns {string} UTF-8 CSV with numeric EUR fields and safe bounded text.
     */
    function buildComparisonCsv() {
        const header = [
            "offer_id",
            "квартал",
            "класификация",
            "цена_eur",
            "площ_m2",
            "цена_на_m2_eur",
            "ремонт_eur",
            "печалба_eur",
            "риск_точки",
            "версия",
            "предупреждение"
        ];
        const rows = state.comparisonIds
            .map((identifier) => data.offers.find((offer) => offer.id === identifier))
            .filter(Boolean)
            .map((offer) => [
                offer.id,
                offer.neighborhood,
                "synthetic",
                offer.priceEur,
                offer.areaSqm,
                offer.comparison.pricePerSqmEur,
                offer.comparison.estimatedRepairEur,
                offer.comparison.baseFlipProfitEur,
                offer.risk.score,
                offer.provenance.recordVersion,
                "Не е реална оферта"
            ].join(","));
        return [header.join(","), ...rows].join("\n");
    }

    /**
     * Trigger a local browser download without network or filesystem APIs.
     *
     * @param {string} fileName - Suggested download name.
     * @param {string} content - Complete file content.
     * @param {string} mediaType - Blob media type.
     * @returns {void} Creates and revokes one temporary object URL.
     */
    function downloadText(fileName, content, mediaType) {
        const blob = new Blob([content], { type: mediaType });
        const objectUrl = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = objectUrl;
        anchor.download = fileName;
        document.body.append(anchor);
        anchor.click();
        anchor.remove();
        global.setTimeout(() => URL.revokeObjectURL(objectUrl), 0);
    }

    /**
     * Handle analysis export, print, decision, and recalculation controls.
     *
     * @param {Event} event - Input, change, or click event.
     * @returns {void} Performs only the explicitly selected local action.
     */
    function handleAnalysisAction(event) {
        const action = event.target.closest("[data-action]")?.dataset.action;
        if (event.type === "input" && event.target.matches("[data-assumption]")) {
            recalculateAnalysis(true);
            return;
        }
        if (event.type === "change" && event.target.name === "humanDecision") {
            updateState({ humanDecision: event.target.value });
            const live = document.querySelector("#decision-status");
            if (live) {
                live.textContent = `Чернова на човешко решение: ${event.target.value}. Няма автоматично действие.`;
            }
            return;
        }
        if (action === "download-analysis") {
            const payload = buildAnalysisPayload();
            if (payload) {
                downloadText(
                    "atistat-sample-analysis.json",
                    `${JSON.stringify(payload, null, 2)}\n`,
                    "application/json;charset=utf-8"
                );
            }
        } else if (action === "download-comparison") {
            downloadText(
                "atistat-sample-comparison.csv",
                `\uFEFF${buildComparisonCsv()}\n`,
                "text/csv;charset=utf-8"
            );
        } else if (action === "print") {
            global.print();
        }
    }

    /**
     * Initialize live calculations and human-review controls.
     *
     * @returns {void} Restores state, attaches handlers, and computes initial output.
     */
    function initializeAnalysis() {
        const form = document.querySelector("#analysis-form");
        if (!form || !calculator || !data) {
            return;
        }
        restoreAnalysisForm();
        form.addEventListener("input", handleAnalysisAction);
        form.addEventListener("change", handleAnalysisAction);
        document.querySelector(".decision-options")?.addEventListener("change", handleAnalysisAction);
        document.querySelector("#analysis-actions")?.addEventListener("click", handleAnalysisAction);
        recalculateAnalysis(false);
    }

    /**
     * Replace reader text with safely highlighted text fragments.
     *
     * @param {HTMLElement} container - Verbatim source container.
     * @param {string} sourceText - Original unmodified source text.
     * @param {string} query - Case-insensitive search query.
     * @returns {number} Number of highlighted matches.
     */
    function highlightRequirements(container, sourceText, query) {
        container.replaceChildren();
        if (!query) {
            container.textContent = sourceText;
            return 0;
        }
        const normalizedSource = sourceText.toLocaleLowerCase("bg");
        const normalizedQuery = query.toLocaleLowerCase("bg");
        const fragment = document.createDocumentFragment();
        let start = 0;
        let matches = 0;
        let matchIndex = normalizedSource.indexOf(normalizedQuery, start);
        while (matchIndex !== -1) {
            fragment.append(document.createTextNode(sourceText.slice(start, matchIndex)));
            const mark = document.createElement("mark");
            mark.textContent = sourceText.slice(matchIndex, matchIndex + query.length);
            fragment.append(mark);
            matches += 1;
            start = matchIndex + query.length;
            matchIndex = normalizedSource.indexOf(normalizedQuery, start);
        }
        fragment.append(document.createTextNode(sourceText.slice(start)));
        container.append(fragment);
        return matches;
    }

    /**
     * Initialize formatted-verbatim requirements search and feedback.
     *
     * @returns {void} Attaches a safe text-only search to the complete embedded source.
     */
    function initializeRequirementsReader() {
        const source = document.querySelector("#requirements-source");
        const search = document.querySelector("#requirements-search-input");
        const feedback = document.querySelector("#requirements-search-status");
        if (!source || !search || !feedback) {
            return;
        }
        const originalText = source.textContent;
        search.addEventListener("input", () => {
            const query = search.value.trim();
            const matches = highlightRequirements(source, originalText, query);
            feedback.textContent = query
                ? `${matches} съвпадения за „${query}“.`
                : "Показан е пълният източник без филтриране.";
            source.querySelector("mark")?.scrollIntoView({ block: "center", behavior: "smooth" });
        });
    }

    /**
     * Open a native dialog and remember the invoking element for focus restoration.
     *
     * @param {HTMLDialogElement} dialog - Dialog to display.
     * @param {HTMLElement|null} trigger - Invoking control.
     * @returns {void} Opens the modal when supported.
     */
    function openDialog(dialog, trigger) {
        restoredDialogFocus = trigger;
        if (typeof dialog.showModal === "function") {
            dialog.showModal();
        } else {
            dialog.setAttribute("open", "");
        }
        dialog.querySelector("[data-action='close-dialog']")?.focus();
    }

    /**
     * Close a native dialog and restore focus to its invoking control.
     *
     * @param {HTMLDialogElement} dialog - Dialog to close.
     * @returns {void} Returns keyboard focus after closing.
     */
    function closeDialog(dialog) {
        if (typeof dialog.close === "function") {
            dialog.close();
        } else {
            dialog.removeAttribute("open");
        }
        restoredDialogFocus?.focus();
        restoredDialogFocus = null;
    }

    /**
     * Initialize shared dialog, print, download, reset, and keyboard navigation actions.
     *
     * @returns {void} Attaches route-independent controls.
     */
    function initializeSharedActions() {
        document.addEventListener("click", (event) => {
            const control = event.target.closest("[data-action]");
            if (!control) {
                return;
            }
            const action = control.dataset.action;
            if (action === "open-dialog") {
                const dialog = document.querySelector(control.dataset.dialogTarget);
                if (dialog instanceof HTMLDialogElement) {
                    openDialog(dialog, control);
                }
            } else if (action === "close-dialog") {
                const dialog = control.closest("dialog");
                if (dialog) {
                    closeDialog(dialog);
                }
            } else if (action === "reset-prototype") {
                state = storage.reset();
                global.location.reload();
            } else if (action === "print") {
                global.print();
            }
        });

        for (const dialog of document.querySelectorAll("dialog")) {
            dialog.addEventListener("click", (event) => {
                // A click on the dialog element itself lands on the backdrop, not on its content.
                if (event.target === dialog) {
                    closeDialog(dialog);
                }
            });
        }

        const navLinks = [...document.querySelectorAll(".primary-nav .nav-link")];
        document.querySelector(".primary-nav")?.addEventListener("keydown", (event) => {
            const currentIndex = navLinks.indexOf(document.activeElement);
            if (currentIndex < 0) {
                return;
            }
            let targetIndex = null;
            if (event.key === "ArrowRight") {
                targetIndex = (currentIndex + 1) % navLinks.length;
            } else if (event.key === "ArrowLeft") {
                targetIndex = (currentIndex - 1 + navLinks.length) % navLinks.length;
            } else if (event.key === "Home") {
                targetIndex = 0;
            } else if (event.key === "End") {
                targetIndex = navLinks.length - 1;
            }
            if (targetIndex !== null) {
                event.preventDefault();
                navLinks[targetIndex].focus();
            }
        });
    }

    /**
     * Initialize the active route after canonical globals and DOM are available.
     *
     * @returns {void} Activates only page-relevant behaviors.
     */
    function initializeApplication() {
        initializeSharedActions();
        initializeDashboard();
        initializeOffers();
        initializeAnalysis();
        initializeRequirementsReader();
    }

    global.ATISTATPrototype = Object.freeze({
        STORAGE_SCHEMA_VERSION,
        formatEur,
        createStorageAdapter,
        buildAnalysisPayload,
        buildComparisonCsv
    });

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initializeApplication);
    } else {
        initializeApplication();
    }
}(window, document));
