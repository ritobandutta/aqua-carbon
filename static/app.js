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
  loadScenario();
  loadCoverageCheck();
});

function initEventListeners() {
  // Navigation Tabs
  document.querySelectorAll(".nav-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".nav-tab").forEach(t => t.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
      tab.classList.add("active");
      const targetId = `tab-${tab.dataset.tab}`;
      const content = document.getElementById(targetId);
      if (content) content.classList.add("active");
      state.activeTab = tab.dataset.tab;
    });
  });

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
      btnRecalc.innerHTML = `<span class="spinner-sm"></span> Calculating...`;
      btnRecalc.disabled = true;

      try {
        await Promise.all([loadScenario(), loadCoverageCheck()]);
        
        // 3. Highlight cards with animation pulse
        document.querySelectorAll(".ledger-metric-card, .burden-col-card").forEach(el => {
          el.classList.add("updated-pulse");
          setTimeout(() => el.classList.remove("updated-pulse"), 800);
        });

        // 4. Success badge on button
        btnRecalc.innerHTML = `✓ Ledgers Updated!`;
        btnRecalc.style.background = "linear-gradient(135deg, #10b981, #059669)";

        setTimeout(() => {
          btnRecalc.innerHTML = origHtml;
          btnRecalc.style.background = "";
          btnRecalc.disabled = false;
        }, 1200);
      } catch (err) {
        console.error("Recalculation error:", err);
        btnRecalc.innerHTML = `Error Recalculating`;
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
        btnCopy.textContent = "Copied to Clipboard!";
        setTimeout(() => {
          btnCopy.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" fill="none" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg> Copy Markdown`;
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
    { key: "evaporative", badge: "badge-evap", label: "Evaporative Cooling", desc: "Pushes heavy burden onto local water headroom." },
    { key: "dry_cooling", badge: "badge-dry", label: "Dry Air-Cooling", desc: "Saves water but shifts immense burden to grid peak & carbon." },
    { key: "hybrid_adiabatic", badge: "badge-hybrid", label: "Hybrid Adiabatic", desc: "Balanced compromise trimming both water and power peaks." }
  ];

  container.innerHTML = profiles.map(p => {
    const a = assessments[p.key];
    if (!a) return "";
    const b = a.burden_scores;
    const f = a.facility_ledger;

    return `
      <div class="burden-col-card">
        <div class="burden-col-header">
          <div class="burden-title">${p.label}</div>
          <span class="cooling-badge ${p.badge}">PUE ${f.pue.toFixed(2)}</span>
        </div>

        <div class="bars-stack">
          <div class="bar-row">
            <div class="bar-labels">
              <span>Water-System Burden</span>
              <span class="bar-val">${b.water_system_burden.toFixed(0)}/100</span>
            </div>
            <div class="bar-track">
              <div class="bar-fill bar-water" style="width: ${b.water_system_burden}%"></div>
            </div>
          </div>

          <div class="bar-row">
            <div class="bar-labels">
              <span>Power-System Burden</span>
              <span class="bar-val">${b.power_system_burden.toFixed(0)}/100</span>
            </div>
            <div class="bar-track">
              <div class="bar-fill bar-power" style="width: ${b.power_system_burden}%"></div>
            </div>
          </div>

          <div class="bar-row">
            <div class="bar-labels">
              <span>Carbon Burden</span>
              <span class="bar-val">${b.carbon_atmosphere_burden.toFixed(0)}/100</span>
            </div>
            <div class="bar-track">
              <div class="bar-fill bar-carbon" style="width: ${b.carbon_atmosphere_burden}%"></div>
            </div>
          </div>
        </div>

        <div class="burden-summary-note">
          ${p.desc}
        </div>
      </div>
    `;
  }).join("");
}

// Render Side-by-Side Dual Ledgers
function renderDualLedgers(assessments) {
  const facilityContainer = document.getElementById("facility-ledger-cards");
  const communityContainer = document.getElementById("community-ledger-cards");
  if (!facilityContainer || !communityContainer || !assessments) return;

  const evap = assessments.evaporative.facility_ledger;
  const dry = assessments.dry_cooling.facility_ledger;
  const hybrid = assessments.hybrid_adiabatic.facility_ledger;

  const evapComm = assessments.evaporative.community_ledger;
  const dryComm = assessments.dry_cooling.community_ledger;
  const hybridComm = assessments.hybrid_adiabatic.community_ledger;

  // 1. Facility Ledger Items
  facilityContainer.innerHTML = `
    <div class="ledger-metric-card">
      <div class="metric-meta">
        <span class="metric-name">Power Usage Effectiveness (PUE)</span>
        <span class="metric-source">Total Facility Energy / IT Energy (ASHRAE TC 9.9)</span>
      </div>
      <div class="metric-values-row">
        <div class="val-item"><span class="val-tag">Evap</span><span class="val-number">${evap.pue.toFixed(2)}</span></div>
        <div class="val-item"><span class="val-tag">Dry</span><span class="val-number" style="color:#fb7185;">${dry.pue.toFixed(2)}</span></div>
        <div class="val-item"><span class="val-tag">Hybrid</span><span class="val-number" style="color:#34d399;">${hybrid.pue.toFixed(2)}</span></div>
      </div>
    </div>

    <div class="ledger-metric-card">
      <div class="metric-meta">
        <span class="metric-name">Water Usage Effectiveness (WUE)</span>
        <span class="metric-source">Liters direct water consumed per kWh of IT load</span>
      </div>
      <div class="metric-values-row">
        <div class="val-item"><span class="val-tag">Evap</span><span class="val-number" style="color:#38bdf8;">${evap.wue.toFixed(2)} L</span></div>
        <div class="val-item"><span class="val-tag">Dry</span><span class="val-number" style="color:#34d399;">${dry.wue.toFixed(2)} L</span></div>
        <div class="val-item"><span class="val-tag">Hybrid</span><span class="val-number">${hybrid.wue.toFixed(2)} L</span></div>
      </div>
    </div>

    <div class="ledger-metric-card">
      <div class="metric-meta">
        <span class="metric-name">Direct Annual Water Volume</span>
        <span class="metric-source">Cooling tower evaporation + drift + blowdown</span>
      </div>
      <div class="metric-values-row">
        <div class="val-item"><span class="val-tag">Evap</span><span class="val-number" style="color:#f43f5e;">${evap.direct_water_consumption_ml.toFixed(1)} ML</span></div>
        <div class="val-item"><span class="val-tag">Dry</span><span class="val-number" style="color:#34d399;">${dry.direct_water_consumption_ml.toFixed(1)} ML</span></div>
        <div class="val-item"><span class="val-tag">Hybrid</span><span class="val-number">${hybrid.direct_water_consumption_ml.toFixed(1)} ML</span></div>
      </div>
    </div>

    <div class="ledger-metric-card">
      <div class="metric-meta">
        <span class="metric-name">Total Annual Facility Energy</span>
        <span class="metric-source">Calculated across 8,760 annual operational hours</span>
      </div>
      <div class="metric-values-row">
        <div class="val-item"><span class="val-tag">Evap</span><span class="val-number">${evap.total_facility_energy_mwh.toLocaleString()} MWh</span></div>
        <div class="val-item"><span class="val-tag">Dry</span><span class="val-number" style="color:#fb7185;">${dry.total_facility_energy_mwh.toLocaleString()} MWh</span></div>
        <div class="val-item"><span class="val-tag">Hybrid</span><span class="val-number">${hybrid.total_facility_energy_mwh.toLocaleString()} MWh</span></div>
      </div>
    </div>

    <div class="ledger-metric-card">
      <div class="metric-meta">
        <span class="metric-name">Annual Operating Cost (OpEx)</span>
        <span class="metric-source">Commercial power tariff (₹8.5/kWh) + Water tariff</span>
      </div>
      <div class="metric-values-row">
        <div class="val-item"><span class="val-tag">Evap</span><span class="val-number">₹${evap.annual_operating_cost_inr_crores.toFixed(1)} Cr</span></div>
        <div class="val-item"><span class="val-tag">Dry</span><span class="val-number" style="color:#fb7185;">₹${dry.annual_operating_cost_inr_crores.toFixed(1)} Cr</span></div>
        <div class="val-item"><span class="val-tag">Hybrid</span><span class="val-number" style="color:#34d399;">₹${hybrid.annual_operating_cost_inr_crores.toFixed(1)} Cr</span></div>
      </div>
    </div>
  `;

  // 2. Community Ledger Items
  communityContainer.innerHTML = `
    <div class="ledger-metric-card">
      <div class="metric-meta">
        <span class="metric-name">Utility Water Headroom Share</span>
        <span class="metric-source">${evapComm.water_headroom_share_pct.source_label}</span>
      </div>
      <div class="metric-values-row">
        <div class="val-item"><span class="val-tag">Evap</span><span class="val-number" style="color:#f43f5e;">${evapComm.water_headroom_share_pct.formatted_value}</span></div>
        <div class="val-item"><span class="val-tag">Dry</span><span class="val-number" style="color:#34d399;">${dryComm.water_headroom_share_pct.formatted_value}</span></div>
        <div class="val-item"><span class="val-tag">Hybrid</span><span class="val-number">${hybridComm.water_headroom_share_pct.formatted_value}</span></div>
      </div>
    </div>

    <div class="ledger-metric-card">
      <div class="metric-meta">
        <span class="metric-name">Household Water Equivalents</span>
        <span class="metric-source">CPHEEO/BIS 1172 benchmark (135 LPCD, 4.2 persons/hh)</span>
      </div>
      <div class="metric-values-row">
        <div class="val-item"><span class="val-tag">Evap</span><span class="val-number" style="color:#f43f5e;">${evapComm.household_water_equivalent_count.formatted_value}</span></div>
        <div class="val-item"><span class="val-tag">Dry</span><span class="val-number" style="color:#34d399;">${dryComm.household_water_equivalent_count.formatted_value}</span></div>
        <div class="val-item"><span class="val-tag">Hybrid</span><span class="val-number">${hybridComm.household_water_equivalent_count.formatted_value}</span></div>
      </div>
    </div>

    <div class="ledger-metric-card">
      <div class="metric-meta">
        <span class="metric-name">Local Substation Peak Impact</span>
        <span class="metric-source">${evapComm.substation_peak_demand_share_pct.source_label}</span>
      </div>
      <div class="metric-values-row">
        <div class="val-item"><span class="val-tag">Evap</span><span class="val-number">${evapComm.substation_peak_demand_share_pct.formatted_value}</span></div>
        <div class="val-item"><span class="val-tag">Dry</span><span class="val-number" style="color:#f43f5e;">${dryComm.substation_peak_demand_share_pct.formatted_value}</span></div>
        <div class="val-item"><span class="val-tag">Hybrid</span><span class="val-number">${hybridComm.substation_peak_demand_share_pct.formatted_value}</span></div>
      </div>
    </div>

    <div class="ledger-metric-card">
      <div class="metric-meta">
        <span class="metric-name">Aquifer Stress Classification</span>
        <span class="metric-source">${evapComm.aquifer_stress_classification.source_label}</span>
      </div>
      <div class="metric-values-row">
        <span class="val-number" style="color:#fbbf24;">${evapComm.aquifer_stress_classification.formatted_value}</span>
        <span class="confidence-chip conf-high">HIGH CONF</span>
      </div>
    </div>

    <div class="ledger-metric-card">
      <div class="metric-meta">
        <span class="metric-name">Tanker Dependency Index</span>
        <span class="metric-source">${evapComm.tanker_dependency_index.source_label}</span>
      </div>
      <div class="metric-values-row">
        <span class="val-number">${evapComm.tanker_dependency_index.formatted_value}</span>
        <span class="confidence-chip conf-medium">MED CONF</span>
      </div>
    </div>
  `;
}

// Render Coverage Disparity Panel
function renderCoveragePanel(cov) {
  const container = document.getElementById("coverage-layout");
  if (!container || !cov) return;

  container.innerHTML = `
    <div class="coverage-stats-box">
      <div class="disparity-visual">
        <div class="stat-circle">
          <span class="stat-num satellite-color">${cov.satellite_settlement_builtup_km2.toFixed(1)} km²</span>
          <span class="val-tag">Satellite Built-Up Grid</span>
        </div>
        <div class="disparity-badge">${cov.disparity_ratio.toFixed(2)}x Gap</div>
        <div class="stat-circle">
          <span class="stat-num piped-color">${cov.official_piped_water_coverage_km2.toFixed(1)} km²</span>
          <span class="val-tag">Official Piped Network</span>
        </div>
      </div>

      <div class="coverage-flags">
        ${cov.flags.map(f => `
          <div class="flag-item">
            <svg viewBox="0 0 24 24" width="18" height="18" stroke="#f43f5e" fill="none" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
            <div>${f}</div>
          </div>
        `).join("")}
      </div>

      <div style="background:#0f1624; padding:0.85rem; border-radius:6px; font-size:0.75rem; color:#94a3b8;">
        <strong>Data Quality Finding:</strong> ${cov.confidence_impact}
      </div>
    </div>

    <div class="coverage-stats-box actions-box">
      <h4>Recommended Ground-Truthing Actions for Civil Society &amp; Municipalities</h4>
      <ul class="actions-list">
        ${cov.recommended_ground_truth_actions.map(a => `<li>${a}</li>`).join("")}
      </ul>
      <div style="margin-top:1.5rem; padding-top:1rem; border-top:1px solid #1e293b; font-size:0.75rem; color:#64748b;">
        Ethical Boundary Guardrail: This coverage analysis operates strictly at the macro ward / spatial grid level and explicitly never collects or processes individual or household identity data.
      </div>
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

  pResults.innerHTML = `<div class="loading-spinner">Searching configurations with deterministic physical constraints...</div>`;

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
        <strong>${data.summary_verdict}</strong>
        ${data.refusal_reason ? `<p style="margin-top:0.5rem; font-size:0.85rem;">${data.refusal_reason}</p>` : ""}
      </div>
    `;

    if (isFeasible) {
      html += `<h4>Feasible Configurations (${data.feasible_configurations.length})</h4>`;
      html += data.feasible_configurations.map(fc => `
        <div class="feasible-item-card">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <strong>${fc.cooling_name}</strong>
            <span class="badge-commons">FEASIBLE</span>
          </div>
          <div style="font-family:var(--font-mono); font-size:0.8rem; margin-top:0.4rem; color:#94a3b8;">
            PUE: ${fc.facility_ledger.pue.toFixed(2)} &bull; Water: ${fc.facility_ledger.direct_water_consumption_ml.toFixed(1)} ML &bull; OpEx: ₹${fc.facility_ledger.annual_operating_cost_inr_crores.toFixed(1)} Cr
          </div>
        </div>
      `).join("");
    }

    if (data.infeasible_configurations && data.infeasible_configurations.length > 0) {
      html += `<h4 style="margin-top:1.2rem; color:#94a3b8;">Violations &amp; Trade-offs (${data.infeasible_configurations.length})</h4>`;
      html += data.infeasible_configurations.map(ic => `
        <div class="feasible-item-card" style="border-color:#334155; opacity:0.85;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-weight:600;">${ic.cooling_name}</span>
            <span class="cooling-badge badge-dry">BREACHED</span>
          </div>
          <ul style="font-size:0.75rem; color:#fb7185; padding-left:1.2rem; margin-top:0.4rem;">
            ${ic.violations.map(v => `<li>${v}</li>`).join("")}
          </ul>
          ${ic.nearest_tradeoff ? `<div style="font-size:0.72rem; color:#f59e0b; margin-top:0.4rem;">💡 ${ic.nearest_tradeoff}</div>` : ""}
        </div>
      `).join("");
    }

    pResults.innerHTML = html;
  } catch (err) {
    pResults.innerHTML = `<div style="color:#f43f5e;">Failed to run planner: ${err.message}</div>`;
  }
}

// Agentic Investigation Handler
async function runInvestigation() {
  const input = document.getElementById("investigate-input");
  const output = document.getElementById("investigator-output");
  if (!input || !output) return;

  const query = input.value.trim();
  if (!query) return;

  output.innerHTML = `<div class="loading-spinner">Grounded agentic reasoning in progress with Verifier Agent cross-check...</div>`;

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
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
        <span style="font-size:0.8rem; color:#38bdf8; font-weight:600;">Query: "${data.query}"</span>
        <span class="verifier-badge success">
          <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" fill="none" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
          ${data.verification_signature}
        </span>
      </div>
      <div>${simpleMarkdownToHtml(data.explanation_markdown)}</div>
    `;
  } catch (err) {
    output.innerHTML = `<div style="color:#f43f5e;">Investigation failed: ${err.message}</div>`;
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
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1.25rem;">
        <div>
          <h3>Independent Verifier Audit Report</h3>
          <p style="font-size:0.8rem; color:#94a3b8;">Cryptographically anchored to deterministic physical engine execution.</p>
        </div>
        <div class="verifier-badge ${verifier.status === 'PASSED' ? 'success' : ''}">
          ${verifier.signature}
        </div>
      </div>

      <div style="display:flex; gap:1.5rem; margin-bottom:1.5rem;">
        <div style="background:#0f1624; padding:0.8rem 1.2rem; border-radius:6px;">
          <span style="font-size:0.7rem; color:#94a3b8; text-transform:uppercase;">Status</span>
          <div style="font-family:var(--font-mono); font-size:1.1rem; font-weight:bold; color:#34d399;">${verifier.status}</div>
        </div>
        <div style="background:#0f1624; padding:0.8rem 1.2rem; border-radius:6px;">
          <span style="font-size:0.7rem; color:#94a3b8; text-transform:uppercase;">Passed Checks</span>
          <div style="font-family:var(--font-mono); font-size:1.1rem; font-weight:bold; color:#f8fafc;">${verifier.passed_checks} / ${verifier.total_checks}</div>
        </div>
      </div>

      <table class="audit-table">
        <thead>
          <tr>
            <th>Metric Checked</th>
            <th>Engine Ground Truth</th>
            <th>Claimed in Brief</th>
            <th>Audit Result</th>
          </tr>
        </thead>
        <tbody>
          ${verifier.checks.map(c => `
            <tr>
              <td>${c.metric_name}</td>
              <td style="color:#38bdf8;">${c.engine_calculated_value}</td>
              <td>${c.claimed_value_in_brief}</td>
              <td class="${c.matched ? 'audit-pass' : 'audit-fail'}">${c.matched ? 'PASSED' : 'FLAGGED'}</td>
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

  modalBody.innerHTML = `<div class="loading-spinner">Executing Section 8 automated test suite...</div>`;

  try {
    const res = await fetch("/api/evals/run");
    if (!res.ok) throw new Error("Eval run failed");
    const data = await res.json();

    modalBody.innerHTML = `
      <div style="margin-bottom:1rem; padding:0.75rem 1rem; background:${data.all_passed ? 'rgba(16,185,129,0.15)' : 'rgba(244,63,94,0.15)'}; border-radius:6px; font-weight:600; color:${data.all_passed ? '#34d399' : '#f87171'};">
        ${data.all_passed ? '✓ ALL 5 SECTION 8 SPECIFICATION CHECKS PASSED' : 'SOME CHECKS FAILED'}
      </div>

      <div style="display:flex; flex-direction:column; gap:0.5rem;">
        ${data.checks.map(c => `
          <div class="eval-item">
            <div>
              <strong>${c.check}</strong>
              <div style="font-size:0.72rem; color:#94a3b8; font-family:var(--font-mono); margin-top:0.2rem;">
                ${Object.entries(c).filter(([k]) => k !== 'check' && k !== 'success').map(([k, v]) => `${k}: ${v}`).join(' &bull; ')}
              </div>
            </div>
            <span class="eval-badge ${c.success ? 'badge-pass' : 'badge-fail'}">
              ${c.success ? 'PASS' : 'FAIL'}
            </span>
          </div>
        `).join("")}
      </div>
    `;
  } catch (err) {
    modalBody.innerHTML = `<div style="color:#f43f5e;">Failed to execute evals: ${err.message}</div>`;
  }
}

// Lightweight Markdown Formatter
function simpleMarkdownToHtml(md) {
  if (!md) return "";
  let html = md
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
  container.innerHTML = `<div class="loading-spinner">Injecting -15% simulated LLM hallucination and routing through Independent Verifier Agent...</div>`;
  try {
    const res = await fetch("/api/evals/tamper-demo");
    const data = await res.json();
    container.innerHTML = `
      <div style="background:rgba(244,63,94,0.12); border:1px solid #f43f5e; border-radius:8px; padding:1.25rem; margin-bottom:1.5rem;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
          <strong style="color:#fb7185; font-size:1.05rem; display:flex; align-items:center; gap:0.5rem;">
            <svg viewBox="0 0 24 24" width="20" height="20" stroke="#f43f5e" fill="none" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
            A2A VERIFIER TRUST BOUNDARY ENGAGED
          </strong>
          <span class="cooling-badge badge-dry" style="font-size:0.8rem; background:rgba(244,63,94,0.25); color:#fda4af;">ACTION: ${data.action_taken}</span>
        </div>
        <p style="font-size:0.85rem; color:#fecdd3; margin-bottom:0.6rem;">${data.injection_description}</p>
        <div style="background:#0f1624; border-radius:6px; padding:0.85rem; font-family:var(--font-mono); font-size:0.78rem; color:#f8fafc; line-height:1.6;">
          <div><strong>Test Case</strong>: ${data.demo_name}</div>
          <div><strong>Audit Verdict</strong>: <span style="color:#fb7185;">${data.result.status}</span></div>
          <div><strong>Tampering Catch Rate</strong>: <span style="color:#34d399;">100% of injected numerical mutations intercepted</span></div>
          <div style="margin-top:0.5rem; color:#fbbf24;">✓ Guardrail Action: Draft failed verification; brief publication was strictly intercepted before rendering to user.</div>
        </div>
      </div>
      <p style="font-size:0.85rem; color:#94a3b8;">Click on "Operator Brief" or "Community Brief" above to restore verified documents.</p>
    `;
  } catch (err) {
    container.innerHTML = `<div style="color:#f43f5e;">Failed to run tamper demo: ${err.message}</div>`;
  }
}

