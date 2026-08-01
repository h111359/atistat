/**
 * calculations.js: Pure financial demonstrator functions for the offline ATISTAT prototype.
 * Exposes acquisition, repair, financing, cash-flow, ROI, NPV, and sensitivity calculations.
 */

(function initializeCalculations(global) {
    "use strict";

    const PERCENT_DIVISOR = 100;
    const MONTHS_PER_YEAR = 12;
    const MINIMUM_DISCOUNT_RATE = -1;

    /**
     * Return a Bulgarian failure result without leaking NaN or Infinity.
     *
     * @param {string} explanationBg - Human-readable reason the calculation is unavailable.
     * @returns {{ok: false, errorBg: string}} A stable invalid-state result.
     */
    function failure(explanationBg) {
        return { ok: false, errorBg: explanationBg };
    }

    /**
     * Validate a numeric input against a bounded rule.
     *
     * @param {*} value - Candidate value supplied by a calculation caller.
     * @param {string} labelBg - Bulgarian field name used in explanations.
     * @param {{minimum?: number, exclusiveMinimum?: number, maximum?: number}} rule - Allowed bounds.
     * @returns {{ok: true, value: number}|{ok: false, errorBg: string}} A number or Bulgarian validation result.
     */
    function readNumber(value, labelBg, rule = {}) {
        if (value === null || value === undefined || value === "") {
            return failure(`Липсва стойност за „${labelBg}“.`);
        }
        const numericValue = Number(value);
        if (!Number.isFinite(numericValue)) {
            return failure(`Стойността за „${labelBg}“ трябва да е крайно число.`);
        }
        if (rule.minimum !== undefined && numericValue < rule.minimum) {
            return failure(`Стойността за „${labelBg}“ не може да е по-малка от ${rule.minimum}.`);
        }
        if (rule.exclusiveMinimum !== undefined && numericValue <= rule.exclusiveMinimum) {
            const minimumLabel = rule.exclusiveMinimum === 0
                ? "нула"
                : String(rule.exclusiveMinimum);
            return failure(`Стойността за „${labelBg}“ трябва да е по-голяма от ${minimumLabel}.`);
        }
        if (rule.maximum !== undefined && numericValue > rule.maximum) {
            return failure(`Стойността за „${labelBg}“ не може да е по-голяма от ${rule.maximum}.`);
        }
        return { ok: true, value: numericValue };
    }

    /**
     * Validate several named numeric fields and return their normalized values.
     *
     * @param {Object} input - Source values keyed by calculation field.
     * @param {Array<{key: string, labelBg: string, rule?: Object}>} definitions - Validation definitions.
     * @returns {{ok: true, values: Object}|{ok: false, errorBg: string}} Normalized values or first failure.
     */
    function readFields(input, definitions) {
        const values = {};
        for (const definition of definitions) {
            const result = readNumber(input[definition.key], definition.labelBg, definition.rule);
            if (!result.ok) {
                return result;
            }
            values[definition.key] = result.value;
        }
        return { ok: true, values };
    }

    /**
     * Calculate total acquisition cost including the stated repair allowance.
     *
     * @param {Object} input - EUR costs plus decimal transaction and broker rates.
     * @returns {Object} A valid cost breakdown or a Bulgarian invalid-state explanation.
     */
    function calculateAcquisition(input) {
        const parsed = readFields(input || {}, [
            { key: "priceEur", labelBg: "покупна цена", rule: { exclusiveMinimum: 0 } },
            { key: "transactionTaxRate", labelBg: "ставка на местния данък", rule: { minimum: 0, maximum: 1 } },
            { key: "notaryEur", labelBg: "нотариални разходи", rule: { minimum: 0 } },
            { key: "registrationEur", labelBg: "разходи за вписване", rule: { minimum: 0 } },
            { key: "brokerRate", labelBg: "брокерска ставка", rule: { minimum: 0, maximum: 1 } },
            { key: "repairEur", labelBg: "ремонт", rule: { minimum: 0 } },
            { key: "bankFeesEur", labelBg: "банкови разходи", rule: { minimum: 0 } }
        ]);
        if (!parsed.ok) {
            return parsed;
        }
        const values = parsed.values;
        const transactionTaxEur = values.priceEur * values.transactionTaxRate;
        const brokerEur = values.priceEur * values.brokerRate;
        const totalEur = values.priceEur + transactionTaxEur + values.notaryEur
            + values.registrationEur + brokerEur + values.repairEur + values.bankFeesEur;
        return {
            ok: true,
            totalEur,
            transactionTaxEur,
            brokerEur,
            currency: "EUR"
        };
    }

    /**
     * Calculate itemized repair cost and contingency.
     *
     * @param {{items: Array<{quantity: number, unitCostEur: number}>, contingencyRate: number}} input - Repair lines and decimal reserve.
     * @returns {Object} A valid repair breakdown or a Bulgarian invalid-state explanation.
     */
    function calculateRepair(input) {
        if (!input || !Array.isArray(input.items) || input.items.length === 0) {
            return failure("Липсва поне една позиция в ремонтния бюджет.");
        }
        const contingency = readNumber(input.contingencyRate, "ремонтен резерв", {
            minimum: 0,
            maximum: 1
        });
        if (!contingency.ok) {
            return contingency;
        }
        let subtotalEur = 0;
        for (const [index, item] of input.items.entries()) {
            const parsed = readFields(item || {}, [
                { key: "quantity", labelBg: `количество на позиция ${index + 1}`, rule: { exclusiveMinimum: 0 } },
                { key: "unitCostEur", labelBg: `единична цена на позиция ${index + 1}`, rule: { minimum: 0 } }
            ]);
            if (!parsed.ok) {
                return parsed;
            }
            subtotalEur += parsed.values.quantity * parsed.values.unitCostEur;
        }
        const contingencyEur = subtotalEur * contingency.value;
        return {
            ok: true,
            subtotalEur,
            contingencyEur,
            totalEur: subtotalEur + contingencyEur,
            currency: "EUR"
        };
    }

    /**
     * Calculate an annuity payment, including the exact zero-interest case.
     *
     * @param {{principalEur: number, annualRate: number, months: number}} input - Loan principal, annual percentage rate, and term.
     * @returns {Object} Monthly payment details or a Bulgarian invalid-state explanation.
     */
    function calculateLoan(input) {
        const parsed = readFields(input || {}, [
            { key: "principalEur", labelBg: "главница", rule: { exclusiveMinimum: 0 } },
            { key: "annualRate", labelBg: "годишна лихва", rule: { minimum: 0 } },
            { key: "months", labelBg: "брой месеци", rule: { exclusiveMinimum: 0 } }
        ]);
        if (!parsed.ok) {
            return parsed;
        }
        const values = parsed.values;
        const periodicRate = values.annualRate / PERCENT_DIVISOR / MONTHS_PER_YEAR;
        if (periodicRate === 0) {
            return {
                ok: true,
                monthlyPaymentEur: values.principalEur / values.months,
                periodicRate,
                formula: "zero-interest",
                currency: "EUR"
            };
        }
        const growth = (1 + periodicRate) ** values.months;
        const monthlyPaymentEur = values.principalEur * ((periodicRate * growth) / (growth - 1));
        if (!Number.isFinite(monthlyPaymentEur)) {
            return failure("Анюитетното плащане е неопределено при тези входове.");
        }
        return {
            ok: true,
            monthlyPaymentEur,
            periodicRate,
            formula: "annuity",
            currency: "EUR"
        };
    }

    /**
     * Calculate effective monthly rent and investor cash flow.
     *
     * @param {Object} input - Monthly rent, vacancy, operating cost, and debt payment.
     * @returns {Object} Cash-flow breakdown, including valid negative cash flow, or an explanation.
     */
    function calculateRentMonthlyCashFlow(input) {
        const parsed = readFields(input || {}, [
            { key: "monthlyRentEur", labelBg: "месечен наем", rule: { minimum: 0 } },
            { key: "vacancyRate", labelBg: "незаетост", rule: { minimum: 0, maximum: 1 } },
            { key: "monthlyOperatingEur", labelBg: "оперативни разходи", rule: { minimum: 0 } },
            { key: "monthlyDebtPaymentEur", labelBg: "плащане по дълга", rule: { minimum: 0 } }
        ]);
        if (!parsed.ok) {
            return parsed;
        }
        const values = parsed.values;
        const effectiveRentEur = values.monthlyRentEur * (1 - values.vacancyRate);
        return {
            ok: true,
            effectiveRentEur,
            cashFlowEur: effectiveRentEur - values.monthlyOperatingEur - values.monthlyDebtPaymentEur,
            currency: "EUR"
        };
    }

    /**
     * Calculate resale proceeds, net profit, and ROI for a repair-and-resale strategy.
     *
     * @param {Object} input - Acquisition, repair, holding, financing, resale, and sale-rate inputs.
     * @returns {Object} Resale result or a Bulgarian invalid-state explanation.
     */
    function calculateFlip(input) {
        const parsed = readFields(input || {}, [
            { key: "acquisitionEur", labelBg: "придобивна стойност", rule: { exclusiveMinimum: 0 } },
            { key: "repairEur", labelBg: "ремонт", rule: { minimum: 0 } },
            { key: "holdingEur", labelBg: "разходи за държане", rule: { minimum: 0 } },
            { key: "financingEur", labelBg: "разходи за финансиране", rule: { minimum: 0 } },
            { key: "resalePriceEur", labelBg: "продажна цена", rule: { minimum: 0 } },
            { key: "saleCostRate", labelBg: "ставка на изходните разходи", rule: { minimum: 0, maximum: 1 } }
        ]);
        if (!parsed.ok) {
            return parsed;
        }
        const values = parsed.values;
        const investmentBaseEur = values.acquisitionEur + values.repairEur
            + values.holdingEur + values.financingEur;
        const resaleNetEur = values.resalePriceEur * (1 - values.saleCostRate);
        const netProfitEur = resaleNetEur - investmentBaseEur;
        return {
            ok: true,
            resaleNetEur,
            investmentBaseEur,
            netProfitEur,
            roiPercent: (netProfitEur / investmentBaseEur) * PERCENT_DIVISOR,
            currency: "EUR"
        };
    }

    /**
     * Calculate ROI against an explicitly supplied positive investment base.
     *
     * @param {{netProfitEur: number, investmentBaseEur: number}} input - Profit and visible denominator.
     * @returns {Object} ROI percentage or a Bulgarian invalid-state explanation.
     */
    function calculateRoi(input) {
        const parsed = readFields(input || {}, [
            { key: "netProfitEur", labelBg: "нетна печалба" },
            { key: "investmentBaseEur", labelBg: "инвестиционна база", rule: { exclusiveMinimum: 0 } }
        ]);
        if (!parsed.ok) {
            return parsed;
        }
        return {
            ok: true,
            roiPercent: (parsed.values.netProfitEur / parsed.values.investmentBaseEur) * PERCENT_DIVISOR
        };
    }

    /**
     * Calculate periodic NPV without rounding intermediate values.
     *
     * @param {{cashFlowsEur: number[], periodicDiscountRate: number}} input - Ordered cash flows and matching periodic rate.
     * @returns {Object} NPV in EUR or a Bulgarian invalid-state explanation.
     */
    function calculateNpv(input) {
        if (!input || !Array.isArray(input.cashFlowsEur) || input.cashFlowsEur.length === 0) {
            return failure("Липсва редица от парични потоци за NPV.");
        }
        const rate = readNumber(input.periodicDiscountRate, "дисконтов процент", {
            exclusiveMinimum: MINIMUM_DISCOUNT_RATE
        });
        if (!rate.ok) {
            return rate;
        }
        let npvEur = 0;
        for (const [period, candidateFlow] of input.cashFlowsEur.entries()) {
            const flow = readNumber(candidateFlow, `паричен поток за период ${period}`, {});
            if (!flow.ok) {
                return flow;
            }
            npvEur += flow.value / ((1 + rate.value) ** period);
        }
        if (!Number.isFinite(npvEur)) {
            return failure("NPV е неопределена при тези входове.");
        }
        return { ok: true, npvEur, currency: "EUR" };
    }

    /**
     * Recalculate flip profit over stated resale-price changes.
     *
     * @param {{baseInput: Object, resaleChanges: number[]}} input - Base flip input and decimal price changes.
     * @returns {Object} Ordered scenario results or a Bulgarian invalid-state explanation.
     */
    function calculateFlipSensitivity(input) {
        if (!input || !Array.isArray(input.resaleChanges) || input.resaleChanges.length === 0) {
            return failure("Липсват стойности за чувствителност.");
        }
        const basePrice = readNumber(
            input.baseInput && input.baseInput.resalePriceEur,
            "базова продажна цена",
            { minimum: 0 }
        );
        if (!basePrice.ok) {
            return basePrice;
        }
        const scenarios = [];
        for (const candidateChange of input.resaleChanges) {
            const change = readNumber(candidateChange, "промяна на продажната цена", {
                exclusiveMinimum: MINIMUM_DISCOUNT_RATE
            });
            if (!change.ok) {
                return change;
            }
            const scenarioInput = {
                ...input.baseInput,
                resalePriceEur: basePrice.value * (1 + change.value)
            };
            const result = calculateFlip(scenarioInput);
            if (!result.ok) {
                return result;
            }
            scenarios.push({
                change: change.value,
                resalePriceEur: scenarioInput.resalePriceEur,
                netProfitEur: result.netProfitEur,
                roiPercent: result.roiPercent
            });
        }
        return { ok: true, scenarios, currency: "EUR" };
    }

    global.ATISTATCalculations = Object.freeze({
        calculateAcquisition,
        calculateRepair,
        calculateLoan,
        calculateRentMonthlyCashFlow,
        calculateFlip,
        calculateRoi,
        calculateNpv,
        calculateFlipSensitivity
    });
}(window));
