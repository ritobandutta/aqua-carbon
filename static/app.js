/**
 * AquaCarbon DC — Commons Edition (v2)
 * Client-side Controller & UI Interactive Orchestrator
 */

// Application State
const state = {
  currentRegion: "bengaluru",
  currentSeason: "annual_average",
  workloadType: "static_inference",
  itCapacityMw: 15,
  gridCarbon: 710,
  activeTab: "dashboard",
  activeBrief: "operator",
  scenarioData: null,
  coverageData: null,
  plannerData: null
};

// Regional Scenario Presets
const PRESETS = {
  bengaluru: {
    region: "bengaluru",
    name: "Bengaluru Whitefield Hyperscale",
    capacity: 15,
    grid: 710,
    headroom: 220,
    substation: 60
  },
  chennai: {
    region: "chennai",
    name: "Chennai Ambattur Coastal Campus",
    capacity: 30,
    grid: 718,
    headroom: 180,
    substation: 80
  },
  mumbai: {
    region: "mumbai",
    name: "Navi Mumbai AI Cluster",
    capacity: 50,
    grid: 705,
    headroom: 450,
    substation: 120
  }
};

// DOM Initializer
document.addEventListener("DOMContentLoaded", () => {
  initEventListeners();
  openTabFromHash();
  loadScenario();
  loadCoverageCheck();
});

// /app#review opens that tab directly (the landing page links here)
function openTabFromHash() {
  const key = (location.hash || "").replace("#", "");
  const tab = key && document.querySelector(`.nav-tab[data-tab="${CSS.escape(key)}"]`);
  if (tab) tab.click();
}
window.addEventListener("hashchange", openTabFromHash);

function initEventListeners() {
  // Navigation Tabs
  document.querySelectorAll(".nav-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".nav-tab").forEach(t => { t.classList.remove("active"); t.setAttribute("aria-selected", "false"); });
      document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
      tab.classList.add("active");
      tab.setAttribute("aria-selected", "true");
      const targetId = `tab-${tab.dataset.tab}`;
      const content = document.getElementById(targetId);
      if (content) content.classList.add("active");
      state.activeTab = tab.dataset.tab;
      if (state.activeTab === "arbiter") {
        runArbiterSimulation();
      }
    });
  });

  // Permit claim review
  const btnRevS = document.getElementById("btn-run-review-structured");
  if (btnRevS) btnRevS.addEventListener("click", () => runReview("structured"));
  const btnRevT = document.getElementById("btn-run-review-text");
  if (btnRevT) btnRevT.addEventListener("click", () => runReview("text"));
  document.querySelectorAll("[data-review]").forEach(chip => chip.addEventListener("click", () => {
    document.getElementById("review-text").value = chip.dataset.review;
  }));

  // Presets Selector
  const presetSelector = document.getElementById("preset-selector");
  if (presetSelector) {
    presetSelector.addEventListener("change", (e) => {
      const presetKey = e.target.value;
      const preset = PRESETS[presetKey];
      if (preset) {
        state.currentRegion = preset.region;
        state.itCapacityMw = preset.capacity;
        state.gridCarbon = preset.grid;

        document.getElementById("capacity-slider").value = preset.capacity;
        document.getElementById("capacity-val").textContent = `${preset.capacity} MW`;
        document.getElementById("grid-slider").value = preset.grid;
        document.getElementById("grid-val").textContent = `${preset.grid} gCO2/kWh`;

        loadScenario();
        loadCoverageCheck();
      }
    });
  }

  // Season Selector
  const seasonSelector = document.getElementById("season-selector");
  if (seasonSelector) {
    seasonSelector.addEventListener("change", (e) => {
      state.currentSeason = e.target.value;
      loadScenario();
    });
  }

  // Workload Flexibility Selector
  const workloadSelector = document.getElementById("workload-selector");
  if (workloadSelector) {
    workloadSelector.addEventListener("change", (e) => {
      state.workloadType = e.target.value;
      loadScenario();
    });
  }

  // Capacity Slider
  const capSlider = document.getElementById("capacity-slider");
  if (capSlider) {
    capSlider.addEventListener("input", (e) => {
      state.itCapacityMw = parseFloat(e.target.value);
      document.getElementById("capacity-val").textContent = `${state.itCapacityMw} MW`;
    });
  }

  // Grid Slider
  const gridSlider = document.getElementById("grid-slider");
  if (gridSlider) {
    gridSlider.addEventListener("input", (e) => {
      state.gridCarbon = parseFloat(e.target.value);
      document.getElementById("grid-val").textContent = `${state.gridCarbon} gCO2/kWh`;
    });
  }

  // Recalculate Button
  const btnRecalc = document.getElementById("btn-recalculate");
  if (btnRecalc) {
    btnRecalc.addEventListener("click", async () => {
      // 1. Switch directly to Dual-Ledger Explorer tab so user immediately sees the updated cards!
      const dashTabBtn = document.querySelector('.nav-tab[data-tab="dashboard"]');
      if (dashTabBtn && !dashTabBtn.classList.contains("active")) {
        dashTabBtn.click();
      }

      // 2. Button visual feedback
      const origHtml = btnRecalc.innerHTML;
      btnRecalc.innerHTML = `<span class="spinner-sm"></span> Calculating`;
      btnRecalc.disabled = true;

      try {
        await Promise.all([loadScenario(), loadCoverageCheck()]);
        
        // 3. Highlight cards with animation pulse
        document.querySelectorAll(".ledger-metric-card, .burden-col-card").forEach(el => {
          el.classList.add("updated-pulse");
          setTimeout(() => el.classList.remove("updated-pulse"), 800);
        });

        // 4. Success badge on button
        btnRecalc.textContent = "Updated";
        btnRecalc.classList.add("is-done");

        setTimeout(() => {
          btnRecalc.innerHTML = origHtml;
          btnRecalc.classList.remove("is-done");
          btnRecalc.disabled = false;
        }, 1200);
      } catch (err) {
        console.error("Recalculation error:", err);
        btnRecalc.textContent = "Error, retry";
        setTimeout(() => {
          btnRecalc.innerHTML = origHtml;
          btnRecalc.disabled = false;
        }, 2000);
      }
    });
  }

  // Planner Run Button
  const btnPlanner = document.getElementById("btn-run-planner");
  if (btnPlanner) {
    btnPlanner.addEventListener("click", runPlanner);
  }

  // Investigation Query Button & Chips
  const btnAsk = document.getElementById("btn-ask-gemini");
  if (btnAsk) {
    btnAsk.addEventListener("click", runInvestigation);
  }

  document.querySelectorAll(".query-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const query = chip.dataset.q;
      const input = document.getElementById("investigate-input");
      if (input) {
        input.value = query;
        runInvestigation();
      }
    });
  });

  // Briefs Toggle Buttons
  document.querySelectorAll(".btn-toggle").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".btn-toggle").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.activeBrief = btn.dataset.brief;
      renderBriefContent();
    });
  });

  // Copy Brief Button
  const btnCopy = document.getElementById("btn-copy-brief");
  if (btnCopy) {
    btnCopy.addEventListener("click", () => {
      if (!state.scenarioData || !state.scenarioData.briefs) return;
      let text = "";
      if (state.activeBrief === "operator") {
        text = state.scenarioData.briefs.operator_brief_markdown;
      } else if (state.activeBrief === "community") {
        text = state.scenarioData.briefs.community_brief_markdown;
      } else {
        text = JSON.stringify(state.scenarioData.verification, null, 2);
      }
      navigator.clipboard.writeText(text).then(() => {
        btnCopy.textContent = "Copied";
        setTimeout(() => {
          btnCopy.textContent = "Copy markdown";
        }, 2000);
      });
    });
  }

  // Tamper Invalidation Demo Button
  const btnTamper = document.getElementById("btn-tamper-demo");
  if (btnTamper) {
    btnTamper.addEventListener("click", runTamperDemo);
  }

  // Live Evals Modal
  const btnEvals = document.getElementById("btn-run-evals");
  const modal = document.getElementById("evals-modal");
  const btnCloseModal = document.getElementById("btn-close-modal");

  if (btnEvals && modal) {
    btnEvals.addEventListener("click", () => {
      modal.classList.remove("hidden");
      runLiveEvals();
    });
  }

  if (btnCloseModal && modal) {
    btnCloseModal.addEventListener("click", () => {
      modal.classList.add("hidden");
    });
  }

  // 24h Arbiter Listeners
  const arbiterFlexSlider = document.getElementById("arbiter-flex-slider");
  const arbiterFlexVal = document.getElementById("arbiter-flex-val");
  if (arbiterFlexSlider && arbiterFlexVal) {
    arbiterFlexSlider.addEventListener("input", (e) => {
      arbiterFlexVal.textContent = `${e.target.value}%`;
    });
  }

  const btnArbiter = document.getElementById("btn-run-arbiter");
  if (btnArbiter) {
    btnArbiter.addEventListener("click", runArbiterSimulation);
  }
}

// Fetch and Render Scenario Data
async function loadScenario() {
  const payload = {
    scenario_id: `${state.currentRegion}_${state.itCapacityMw}mw`,
    scenario_title: `${state.currentRegion.toUpperCase()} Facility (${state.itCapacityMw} MW)`,
    region: state.currentRegion,
    it_capacity_mw: state.itCapacityMw,
    season: state.currentSeason,
    workload_type: state.workloadType,
    grid_carbon_factor_kg_per_mwh: state.gridCarbon,
    selected_profiles: ["evaporative", "dry_cooling", "hybrid_adiabatic"]
  };

  try {
    const res = await fetch("/api/scenario/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error("API call failed");
    const data = await res.json();
    state.scenarioData = data;

    renderBurdenMatrix(data.assessments);
    renderDualLedgers(data.assessments);
    renderBriefContent();
    const prov = document.getElementById("brief-provenance");
    if (prov) prov.textContent = provenanceLine(data);
  } catch (err) {
    console.error("Failed to load scenario:", err);
  }
}

// Fetch Spatial Coverage Check
async function loadCoverageCheck() {
  try {
    const res = await fetch(`/api/coverage-check/${state.currentRegion}`);
    if (!res.ok) throw new Error("Coverage API failed");
    const data = await res.json();
    state.coverageData = data;
    renderCoveragePanel(data);
  } catch (err) {
    console.error("Coverage check error:", err);
  }
}

// Render Burden Shifting Matrix
function renderBurdenMatrix(assessments) {
  const container = document.getElementById("burden-grid");
  if (!container || !assessments) return;

  const profiles = [
    { key: "evaporative", badge: "badge-evap", label: "Evaporative", desc: "Pushes the heaviest burden onto local water headroom." },
    { key: "dry_cooling", badge: "badge-dry", label: "Dry, air-cooled", desc: "Saves water, shifts the burden to the grid peak and to carbon." },
    { key: "hybrid_adiabatic", badge: "badge-hybrid", label: "Hybrid adiabatic", desc: "A compromise that trims both the water and the power peak." }
  ];

  container.innerHTML = profiles.map(p => {
    const a = assessments[p.key];
    if (!a) return "";
    const b = a.burden_scores;
    const f = a.facility_ledger;

    const peak = Math.max(b.water_system_burden, b.power_system_burden, b.carbon_atmosphere_burden);
    const peakClass = v => (v === peak ? " is-peak" : "");

    return `
      <div class="burden-col-card">
        <div class="burden-col-header">
          <div class="burden-title">${p.label}</div>
          <span class="cooling-badge ${p.badge}">PUE ${f.pue.toFixed(2)}</span>
        </div>

        <div class="bars-stack">
          <div class="bar-row">
            <div class="bar-labels">
              <span>Water system</span>
              <span class="bar-val">${b.water_system_burden.toFixed(0)}/100</span>
            </div>
            <div class="bar-track">
              <div class="bar-fill${peakClass(b.water_system_burden)}" data-w="${b.water_system_burden}"></div>
            </div>
          </div>

          <div class="bar-row">
            <div class="bar-labels">
              <span>Power system</span>
              <span class="bar-val">${b.power_system_burden.toFixed(0)}/100</span>
            </div>
            <div class="bar-track">
              <div class="bar-fill${peakClass(b.power_system_burden)}" data-w="${b.power_system_burden}"></div>
            </div>
          </div>

          <div class="bar-row">
            <div class="bar-labels">
              <span>Carbon</span>
              <span class="bar-val">${b.carbon_atmosphere_burden.toFixed(0)}/100</span>
            </div>
            <div class="bar-track">
              <div class="bar-fill${peakClass(b.carbon_atmosphere_burden)}" data-w="${b.carbon_atmosphere_burden}"></div>
            </div>
          </div>
        </div>

        <div class="burden-summary-note">
          ${p.desc}
        </div>
      </div>
    `;
  }).join("");

  // widths are set from data after insertion so the CSS transition can run, and no inline style is needed
  requestAnimationFrame(() => container.querySelectorAll(".bar-fill").forEach(el => { el.style.width = el.dataset.w + "%"; }));
}

// Render Side-by-Side Dual Ledgers
// One row: three values (evaporative, dry, hybrid). Lower is better for every metric here, so the lowest
// numeric value is marked with the accent underline. Meaning never depends on colour.
function ledgerRow(name, source, items, opts = {}) {
  const nums = items.map(i => i.raw).filter(v => typeof v === "number" && !Number.isNaN(v));
  const best = nums.length > 1 ? Math.min(...nums) : null;
  const cells = items.map(i => `
        <div class="val-item${best !== null && i.raw === best ? " is-best" : ""}"><span class="val-tag">${i.tag}</span><span class="val-number">${i.text}</span></div>`).join("");
  return `
    <div class="ledger-metric-card">
      <div class="metric-meta">
        <span class="metric-name">${name}</span>
        <span class="metric-source">${source}</span>
      </div>
      <div class="metric-values-row">${cells}
      </div>
    </div>`;
}

function chipRow(name, source, valueText, confidence) {
  return `
    <div class="ledger-metric-card">
      <div class="metric-meta">
        <span class="metric-name">${name}</span>
        <span class="metric-source">${source}</span>
      </div>
      <div class="metric-values-row is-flex">
        <span class="val-number">${valueText}</span>
        <span class="confidence-chip conf-${confidence}">${confidence} confidence</span>
      </div>
    </div>`;
}

function renderDualLedgers(assessments) {
  const facilityContainer = document.getElementById("facility-ledger-cards");
  const communityContainer = document.getElementById("community-ledger-cards");
  if (!facilityContainer || !communityContainer || !assessments) return;

  const E = assessments.evaporative.facility_ledger;
  const D = assessments.dry_cooling.facility_ledger;
  const H = assessments.hybrid_adiabatic.facility_ledger;
  const eC = assessments.evaporative.community_ledger;
  const dC = assessments.dry_cooling.community_ledger;
  const hC = assessments.hybrid_adiabatic.community_ledger;
  const trio = (fn) => [{ tag: "Evap", ...fn(E, eC) }, { tag: "Dry", ...fn(D, dC) }, { tag: "Hybrid", ...fn(H, hC) }];
  const sd = state.scenarioData;

  facilityContainer.innerHTML =
    ledgerRow("Power usage effectiveness", "Total facility energy over IT energy. Lower is better.",
      trio(f => ({ raw: f.pue, text: f.pue.toFixed(2) }))) +
    ledgerRow("Water usage effectiveness", "Litres of direct water per kWh of IT load.",
      trio(f => ({ raw: f.wue, text: `${f.wue.toFixed(2)} L` }))) +
    ledgerRow("Direct annual water", `Evaporation, drift and blowdown. Evaporative sensitivity range: ${bandRange(sd, "evaporative", "direct_water_ml", "ML", 0)}`,
      trio(f => ({ raw: f.direct_water_consumption_ml, text: `${f.direct_water_consumption_ml.toFixed(1)} ML` }))) +
    ledgerRow("Annual facility energy", `8,760 operating hours. Dry-cooling sensitivity range: ${bandRange(sd, "dry_cooling", "facility_energy_mwh", "MWh", 0)}`,
      trio(f => ({ raw: f.total_facility_energy_mwh, text: `${f.total_facility_energy_mwh.toLocaleString(undefined, { maximumFractionDigits: 0 })} MWh` }))) +
    ledgerRow("Annual operating cost", `Assumes INR 8.5/kWh power and INR 95/kL water. Evaporative sensitivity range: ${bandRange(sd, "evaporative", "operating_cost_inr_crores", "Cr", 0)}`,
      trio(f => ({ raw: f.annual_operating_cost_inr_crores, text: `INR ${f.annual_operating_cost_inr_crores.toFixed(1)} Cr` }))) +
    `<p class="legend-note mono">Underline marks the lowest value in each row</p>`;

  communityContainer.innerHTML =
    ledgerRow("Utility water headroom share", escapeHtml(eC.water_headroom_share_pct.source_label),
      trio((f, c) => ({ raw: c.water_headroom_share_pct.value, text: c.water_headroom_share_pct.formatted_value }))) +
    ledgerRow("Household water equivalents", escapeHtml(eC.household_water_equivalent_count.source_label),
      trio((f, c) => ({ raw: c.household_water_equivalent_count.value, text: c.household_water_equivalent_count.formatted_value }))) +
    ledgerRow("Local substation peak impact", escapeHtml(eC.substation_peak_demand_share_pct.source_label),
      trio((f, c) => ({ raw: c.substation_peak_demand_share_pct.value, text: c.substation_peak_demand_share_pct.formatted_value }))) +
    chipRow("Aquifer stress classification", escapeHtml(eC.aquifer_stress_classification.source_label),
      escapeHtml(eC.aquifer_stress_classification.formatted_value), eC.aquifer_stress_classification.confidence) +
    chipRow("Tanker dependency index", escapeHtml(eC.tanker_dependency_index.source_label),
      escapeHtml(eC.tanker_dependency_index.formatted_value), eC.tanker_dependency_index.confidence);
}

// Render Coverage Disparity Panel
function renderCoveragePanel(cov) {
  const container = document.getElementById("coverage-layout");
  if (!container || !cov) return;

  container.innerHTML = `
    <div class="coverage-stats-box">
      <div class="disparity-visual">
        <div class="stat-circle">
          <span class="stat-num">${cov.satellite_settlement_builtup_km2.toFixed(1)} km²</span>
          <span class="val-tag">Satellite built-up</span>
        </div>
        <div class="disparity-badge">${cov.disparity_ratio.toFixed(2)}x gap</div>
        <div class="stat-circle">
          <span class="stat-num">${cov.official_piped_water_coverage_km2.toFixed(1)} km²</span>
          <span class="val-tag">Official piped network</span>
        </div>
      </div>

      <div class="coverage-flags">
        ${cov.flags.map(f => `
          <div class="flag-item">
            <svg viewBox="0 0 24 24" stroke="currentColor" fill="none" stroke-width="1.5" aria-hidden="true"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
            <div>${escapeHtml(f)}</div>
          </div>
        `).join("")}
      </div>

      <div class="note"><strong>Data quality finding.</strong> ${escapeHtml(cov.confidence_impact)}</div>
    </div>

    <div class="coverage-stats-box actions-box">
      <h4>Recommended ground-truthing actions</h4>
      <ul class="actions-list">
        ${cov.recommended_ground_truth_actions.map(a => `<li>${escapeHtml(a)}</li>`).join("")}
      </ul>
      <div class="guardrail">Ethical boundary: this analysis works at ward and grid level only. It never collects or processes individual or household identity data.</div>
    </div>
  `;
}

// Constraint-Aware Planner Handler
async function runPlanner() {
  const pResults = document.getElementById("planner-results");
  if (!pResults) return;

  const constraints = {
    max_pue: parseFloat(document.getElementById("constraint-pue").value) || null,
    max_cooling_cost_inr_crores: parseFloat(document.getElementById("constraint-cost").value) || null,
    max_water_headroom_share_pct: parseFloat(document.getElementById("constraint-headroom").value) || null,
    max_grid_peak_share_pct: parseFloat(document.getElementById("constraint-grid").value) || null
  };

  const payload = {
    scenario: {
      scenario_id: `${state.currentRegion}_${state.itCapacityMw}mw`,
      scenario_title: `${state.currentRegion.toUpperCase()} Facility`,
      region: state.currentRegion,
      it_capacity_mw: state.itCapacityMw,
      season: state.currentSeason,
      grid_carbon_factor_kg_per_mwh: state.gridCarbon,
      selected_profiles: ["evaporative", "dry_cooling", "hybrid_adiabatic"]
    },
    constraints: constraints
  };

  pResults.innerHTML = `<div class="loading-spinner">Searching configurations</div>`;

  try {
    const res = await fetch("/api/scenario/planner", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error("Planner error");
    const data = await res.json();
    state.plannerData = data;

    const isFeasible = data.feasible_configurations.length > 0;
    const verdictClass = isFeasible ? "verdict-success" : "verdict-refusal";

    let html = `
      <div class="planner-verdict-box ${verdictClass}">
        <strong>${escapeHtml(data.summary_verdict)}</strong>
        ${data.refusal_reason ? `<p>${escapeHtml(data.refusal_reason)}</p>` : ""}
      </div>
    `;

    if (isFeasible) {
      html += `<h4>Feasible configurations (${data.feasible_configurations.length})</h4>`;
      html += data.feasible_configurations.map(fc => `
        <div class="feasible-item-card">
          <div class="item-head">
            <strong>${escapeHtml(fc.cooling_name)}</strong>
            <span class="cooling-badge badge-commons">Feasible</span>
          </div>
          <div class="item-meta">PUE ${fc.facility_ledger.pue.toFixed(2)} &middot; Water ${fc.facility_ledger.direct_water_consumption_ml.toFixed(1)} ML &middot; OpEx INR ${fc.facility_ledger.annual_operating_cost_inr_crores.toFixed(1)} Cr</div>
        </div>
      `).join("");
    }

    if (data.infeasible_configurations && data.infeasible_configurations.length > 0) {
      html += `<h4>Breached limits (${data.infeasible_configurations.length})</h4>`;
      html += data.infeasible_configurations.map(ic => `
        <div class="feasible-item-card is-breached">
          <div class="item-head">
            <strong>${escapeHtml(ic.cooling_name)}</strong>
            <span class="cooling-badge badge-dry">Breached</span>
          </div>
          <ul class="violations">
            ${ic.violations.map(v => `<li>${escapeHtml(v)}</li>`).join("")}
          </ul>
          ${ic.nearest_tradeoff ? `<div class="tradeoff">${escapeHtml(ic.nearest_tradeoff)}</div>` : ""}
        </div>
      `).join("");
    }

    pResults.innerHTML = html;
  } catch (err) {
    pResults.innerHTML = `<div class="is-error">Planner failed: ${escapeHtml(err.message)}</div>`;
  }
}

// Agentic Investigation Handler
async function runInvestigation() {
  const input = document.getElementById("investigate-input");
  const output = document.getElementById("investigator-output");
  if (!input || !output) return;

  const query = input.value.trim();
  if (!query) return;

  output.innerHTML = `<div class="loading-spinner">Answering, then checking every number</div>`;

  const payload = {
    query: query,
    scenario: {
      scenario_id: `${state.currentRegion}_${state.itCapacityMw}mw`,
      scenario_title: `${state.currentRegion.toUpperCase()} Facility`,
      region: state.currentRegion,
      it_capacity_mw: state.itCapacityMw,
      season: state.currentSeason,
      grid_carbon_factor_kg_per_mwh: state.gridCarbon,
      selected_profiles: ["evaporative", "dry_cooling", "hybrid_adiabatic"]
    }
  };

  try {
    const res = await fetch("/api/investigate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error("Investigation query failed");
    const data = await res.json();

    output.innerHTML = `
      <div class="output-head">
        <span class="query-echo">${escapeHtml(data.query)}</span>
        <span class="verifier-badge success">${escapeHtml(data.verification_signature)}</span>
      </div>
      <div>${simpleMarkdownToHtml(data.explanation_markdown)}</div>
    `;
  } catch (err) {
    output.innerHTML = `<div class="is-error">Investigation failed: ${escapeHtml(err.message)}</div>`;
  }
}

// Render Brief Content
function renderBriefContent() {
  const container = document.getElementById("brief-markdown-content");
  if (!container || !state.scenarioData) return;

  const briefs = state.scenarioData.briefs;
  const verifier = state.scenarioData.verification;

  if (state.activeBrief === "operator") {
    container.innerHTML = simpleMarkdownToHtml(briefs.operator_brief_markdown);
  } else if (state.activeBrief === "community") {
    container.innerHTML = simpleMarkdownToHtml(briefs.community_brief_markdown);
  } else {
    // Render Verifier Audit Table
    container.innerHTML = `
      <div class="output-head">
        <div>
          <h3>Independent verifier audit</h3>
          <p class="fine">SHA-256 digest over the check results, recomputed from the deterministic engine.</p>
        </div>
        <span class="verifier-badge ${verifier.status === 'PASSED' ? 'success' : ''}">${escapeHtml(verifier.signature)}</span>
      </div>

      <div class="stat-pair">
        <div><span class="mono">Status</span><span class="big">${escapeHtml(verifier.status)}</span></div>
        <div><span class="mono">Checks passed</span><span class="big">${verifier.passed_checks} / ${verifier.total_checks}</span></div>
      </div>

      <table class="audit-table">
        <thead>
          <tr>
            <th>Metric</th>
            <th>Engine value</th>
            <th>In the brief</th>
            <th>Result</th>
          </tr>
        </thead>
        <tbody>
          ${verifier.checks.map(c => `
            <tr>
              <td>${escapeHtml(c.metric_name)}</td>
              <td>${escapeHtml(c.engine_calculated_value)}</td>
              <td>${escapeHtml(c.claimed_value_in_brief)}</td>
              <td class="${c.matched ? 'audit-pass' : 'audit-fail'}">${c.matched ? 'Passed' : 'Flagged'}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    `;
  }
}

// Live Evaluations Suite Execution
async function runLiveEvals() {
  const modalBody = document.getElementById("modal-eval-body");
  if (!modalBody) return;

  modalBody.innerHTML = `<div class="loading-spinner">Running checks</div>`;

  try {
    const res = await fetch("/api/evals/run");
    if (!res.ok) throw new Error("Eval run failed");
    const data = await res.json();

    modalBody.innerHTML = `
      <div class="eval-summary mono ${data.all_passed ? '' : 'is-fail'}">
        ${data.all_passed ? `All ${data.checks.length} checks passed` : 'Some checks failed'}
      </div>

      <div>
        ${data.checks.map(c => `
          <div class="eval-item">
            <div>
              <strong>${escapeHtml(c.check)}</strong>
              <div class="eval-meta">
                ${escapeHtml(Object.entries(c).filter(([k]) => k !== 'check' && k !== 'success').map(([k, v]) => `${k}: ${v}`).join(' • '))}
              </div>
            </div>
            <span class="eval-badge ${c.success ? 'badge-pass' : 'badge-fail'}">
              ${c.success ? 'Pass' : 'Fail'}
            </span>
          </div>
        `).join("")}
      </div>
    `;
  } catch (err) {
    modalBody.innerHTML = `<div class="is-error">Evals failed: ${escapeHtml(err.message)}</div>`;
  }
}

// Lightweight Markdown Formatter
function bandRange(data, profile, metric, unit, digits) {
  const b = data && data.uncertainty_bands && data.uncertainty_bands[profile] && data.uncertainty_bands[profile][metric];
  if (!b) return "n/a";
  return `${b.low.toFixed(digits)}–${b.high.toFixed(digits)} ${unit}`;
}

function bandText(bands, profile, metric, unit, digits) {
  const b = bands && bands[profile] && bands[profile][metric];
  if (!b) return "";
  return ` (range ${b.low.toFixed(digits)}–${b.high.toFixed(digits)} ${unit})`;
}

function provenanceLine(data) {
  if (!data) return "";
  const src = data.brief_sources ? `Briefs: operator=${data.brief_sources.operator}, community=${data.brief_sources.community}` : "";
  const ver = data.verifier_mode ? ` | Verifier: ${data.verifier_mode}` : "";
  const run = data.run_id ? ` | Run ${data.run_id}` : "";
  return escapeHtml(src + ver + run);
}

async function runReview(mode) {
  const out = document.getElementById("review-output");
  if (!out) return;
  const text = document.getElementById("review-text").value.trim();
  const scenario = { region: state.currentRegion, it_capacity_mw: state.itCapacityMw, season: state.currentSeason, workload_type: state.workloadType || "static_inference" };
  const body = { scenario };
  if (mode === "structured") {
    const v = parseFloat(document.getElementById("review-value").value);
    if (!Number.isFinite(v)) { out.innerHTML = `<div class="is-error">Enter a numeric value first.</div>`; return; }
    body.claims = [{ cooling_type: document.getElementById("review-cooling").value, metric: document.getElementById("review-metric").value, claimed_value: v }];
    body.applicant_text = text;
  } else {
    if (!text) { out.innerHTML = `<div class="is-error">Paste some application text first.</div>`; return; }
    body.applicant_text = text;
  }
  out.innerHTML = `<div class="loading-spinner">Checking against the engine, then the verifier</div>`;
  try {
    const res = await fetch("/api/review", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const data = await res.json();
    if (!res.ok) { out.innerHTML = `<div class="is-error">${escapeHtml(data.detail || "Review failed")}</div>`; return; }
    const prov = data.provenance || {};
    const line = `Mode ${data.mode} · MCP ${prov.mcp} · Verification ${prov.verification} (${data.verification ? data.verification.signature : "n/a"})`;
    const badge = data.status === "verified" ? "success" : "";
    out.innerHTML = `
      <div class="output-head">
        <span class="verifier-badge ${badge}">${escapeHtml(data.status.replace(/_/g, " "))}</span>
        <span class="prov-line">${escapeHtml(line)}</span>
      </div>
      <div class="markdown-preview">${simpleMarkdownToHtml(data.review_markdown || "")}</div>
      <p class="fine">${escapeHtml(data.notice || "")}</p>`;
  } catch (err) {
    out.innerHTML = `<div class="is-error">Review failed: ${escapeHtml(err.message)}</div>`;
  }
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// Model output is untrusted: escape it first, then apply the markdown subset below.
function simpleMarkdownToHtml(md) {
  if (!md) return "";
  let html = escapeHtml(md)
    .replace(/^### (.*$)/gim, '<h3>$1</h3>')
    .replace(/^## (.*$)/gim, '<h2>$1</h2>')
    .replace(/^# (.*$)/gim, '<h1>$1</h1>')
    .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/gim, '<em>$1</em>')
    .replace(/^\- (.*$)/gim, '<li>$1</li>');

  // Handle tables
  const lines = html.split("\n");
  let inTable = false;
  let tableHtml = "";
  const outputLines = [];

  for (let line of lines) {
    if (line.trim().startsWith("|") && line.trim().endsWith("|")) {
      if (!inTable) {
        inTable = true;
        tableHtml = "<table><tbody>";
      }
      if (line.includes("---")) continue; // separator
      const cells = line.split("|").slice(1, -1).map(c => `<td>${c.trim()}</td>`).join("");
      tableHtml += `<tr>${cells}</tr>`;
    } else {
      if (inTable) {
        inTable = false;
        tableHtml += "</tbody></table>";
        outputLines.push(tableHtml);
      }
      outputLines.push(line);
    }
  }
  if (inTable) {
    outputLines.push(tableHtml + "</tbody></table>");
  }

  return outputLines.join("<br>");
}

// Live Invalidation Demo: Deliberately injects a -15% LLM Hallucination to demonstrate Verifier catching error
async function runTamperDemo() {
  const container = document.getElementById("brief-markdown-content");
  if (!container) return;
  container.innerHTML = `<div class="loading-spinner">Corrupting a brief, then verifying</div>`;
  try {
    const res = await fetch("/api/evals/tamper-demo");
    const data = await res.json();
    container.innerHTML = `
      <div class="callout">
        <div class="output-head">
          <strong>Verifier trust boundary engaged</strong>
          <span class="cooling-badge badge-fail">${escapeHtml(data.action_taken)}</span>
        </div>
        <p class="section-subtitle">${escapeHtml(data.injection_description)}</p>
        <div class="mono-block">
          <div>Test case: ${escapeHtml(data.demo_name)}</div>
          <div>Audit verdict: ${escapeHtml(data.result.status)}</div>
          <div>Injected errors caught: ${data.result.detected_failures} of ${data.result.total_injected_checks}</div>
          <div>Outcome: the draft failed verification and was withheld before it reached the reader.</div>
        </div>
      </div>
      <p class="fine">Choose Operator or Community above to restore a verified brief.</p>
    `;
  } catch (err) {
    container.innerHTML = `<div class="is-error">Tamper demo failed: ${escapeHtml(err.message)}</div>`;
  }
}

// 24-Hour Arbiter & AI Dispatcher Simulation
async function runArbiterSimulation() {
  const btn = document.getElementById("btn-run-arbiter");
  const slider = document.getElementById("arbiter-flex-slider");
  const flexPct = slider ? parseFloat(slider.value) : 40.0;
  
  const origText = btn ? btn.innerHTML : "";
  if (btn) {
    btn.innerHTML = `<span class="spinner"></span> Simulating`;
    btn.disabled = true;
  }

  try {
    const payload = {
      scenario: {
        scenario_id: `${state.currentRegion}_24h_arbiter`,
        scenario_title: `${state.currentRegion.toUpperCase()} 24h Thermal & Workload Arbiter`,
        region: state.currentRegion,
        season: state.currentSeason,
        it_capacity_mw: parseFloat(state.itCapacityMw),
        workload_type: state.workloadType,
        custom_grid_carbon_intensity: parseFloat(state.gridCarbon)
      },
      ai_flexibility_pct: flexPct
    };

    const res = await fetch("/api/arbiter/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    // Populate KPIs
    const elWater = document.getElementById("arbiter-water-saved");
    const elWaterPct = document.getElementById("arbiter-water-pct");
    const elHh = document.getElementById("arbiter-hh-restored");
    const elPeak = document.getElementById("arbiter-peak-shaved");
    const elFree = document.getElementById("arbiter-free-hours");

    if (elWater) elWater.textContent = `${Math.round(data.water_saved_liters).toLocaleString()} L/day`;
    if (elWaterPct) elWaterPct.textContent = `${data.water_savings_pct}% vs evaporative baseline`;
    if (elHh) elHh.textContent = `${data.households_water_restored_days.toLocaleString()}`;
    if (elPeak) elPeak.textContent = `${data.peak_grid_shaved_mw} MW`;
    if (elFree) elFree.textContent = `${data.free_cooling_hours} h`;

    // Render 24h timeline strip
    const strip = document.getElementById("timeline-bar-strip");
    if (strip && data.hourly_steps) {
      strip.innerHTML = data.hourly_steps.map(step => {
        let slotClass = "slot-dry";
        if (step.cooling_mode.includes("Free-Cooling")) slotClass = "slot-free";
        else if (step.cooling_mode.includes("CooL-LLM")) slotClass = "slot-shift";
        else if (step.cooling_mode.includes("Peak-Shave")) slotClass = "slot-shave";

        return `
          <div class="timeline-slot ${slotClass}" title="${escapeHtml(step.time_label)}: ${step.ambient_temp_c}°C | ${escapeHtml(step.cooling_mode)} | IT: ${step.it_load_mw}MW | PUE: ${step.pue}">
            <span class="slot-hour">${step.time_label}</span>
            <span class="slot-temp">${step.ambient_temp_c}°</span>
          </div>
        `;
      }).join("");
    }

    // Render hourly table
    const tbody = document.getElementById("arbiter-hourly-tbody");
    if (tbody && data.hourly_steps) {
      tbody.innerHTML = data.hourly_steps.map(s => {
        let badgeColor = "badge-dry";
        if (s.cooling_mode.includes("Free-Cooling")) badgeColor = "badge-evap";
        else if (s.cooling_mode.includes("CooL-LLM")) badgeColor = "badge-hybrid";
        else if (s.cooling_mode.includes("Peak-Shave")) badgeColor = "badge-fail";

        return `
          <tr>
            <td><strong>${s.time_label}</strong></td>
            <td>${s.ambient_temp_c}°C <small class="dim">(${s.ambient_rh_pct}% RH)</small></td>
            <td><span class="cooling-badge ${badgeColor}">${escapeHtml(s.cooling_mode)}</span></td>
            <td><small>${escapeHtml(s.chiller_status)}</small></td>
            <td>${s.it_load_mw.toFixed(1)} MW</td>
            <td><strong>${s.pue.toFixed(2)}</strong></td>
            <td>${s.water_intake_m3_h > 0 ? (s.water_intake_m3_h * 1000).toFixed(0) + " L/h" : "<span class='dim'>0 L, free air</span>"}</td>
            <td>${s.facility_power_mw.toFixed(1)} MW</td>
          </tr>
        `;
      }).join("");
    }

  } catch (err) {
    console.error("Arbiter simulation error:", err);
  } finally {
    if (btn) {
      btn.innerHTML = origText;
      btn.disabled = false;
    }
  }
}


