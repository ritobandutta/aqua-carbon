# Glossary

| Term | Meaning |
|---|---|
| **PUE** (Power Usage Effectiveness) | Total facility energy divided by IT energy. Says nothing about water or carbon, which is why PUE alone can hide trade-offs. |
| **WUE** (Water Usage Effectiveness) | Annual site water use divided by IT energy (L/kWh). Here, direct (onsite) water. |
| **Direct water** | Water consumed onsite, mainly evaporation and blowdown from cooling towers. |
| **Indirect water** | Water consumed at power plants to generate the electricity the facility draws. |
| **CoC** (Cycles of Concentration) | How concentrated cooling-tower water gets before blowdown. Higher CoC means less blowdown water. |
| **Blowdown** | Water drained from a cooling tower to limit mineral build-up. |
| **Evaporative cooling** | Heat rejected by evaporating water. Low electricity, high water. |
| **Dry cooling / air-cooled** | Heat rejected to air without evaporation. Low water, more electricity, and performance drops in hot weather. |
| **COP** | Coefficient of performance: heat removed per unit of electrical energy. |
| **Wet-bulb / dry-bulb temperature** | Ambient air temperatures that govern evaporative and dry cooling performance respectively. |
| **TMY** | Typical Meteorological Year, a representative hourly weather dataset. |
| **ASHRAE A1** | An ASHRAE environmental class setting allowable server inlet conditions. Used here for thermal-safety limits. |
| **Facility ledger** | Operator-side metrics: energy, PUE, direct water, WUE, carbon, cost. |
| **Community ledger** | Indicators of what the facility draws from shared water and power systems, each with source, resolution and confidence. |
| **Burden-shifting view** | Side-by-side water, power and carbon burdens per profile. Deliberately has no combined score. |
| **Coverage check** | Compares independent public layers for an area and flags where official data likely under-represents people who rely on shared systems. Area-level only. |
| **Confidence** | How much to trust an indicator, based on source quality, age and resolution. Lowered when coverage checks disagree. |
| **Unavailable** | The explicit value shown when data does not exist. Never replaced by a default. |
| **Illustrative** | Label for synthetic facility inputs. Not real measurements. |
| **Modelled potential impact** | The only claim we make. Not measured or verified savings. |
| **Constraint-aware planner** | Searches configurations against facility and community limits and returns the feasible set, or says none exists. |
| **ADK** | Google Agent Development Kit, used for agent orchestration. |
| **MCP** | Model Context Protocol. Typed tool contract. Here it exposes the engine and data lookups. |
| **A2A** | Agent2Agent protocol. Used only where agents must be independent (verifier, community service). |
| **Run ID** | Hash of inputs, engine version and dataset versions. Identical inputs give identical runs. |
