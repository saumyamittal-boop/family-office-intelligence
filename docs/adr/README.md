# Architecture Decision Records

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [0001](0001-prototype-on-synthetic-data.md) | Prototype on synthetic data, outside regulated advice | accepted | 2026-10-17 |
| [0002](0002-scope-one-archetype-three-personas.md) | One family-office archetype, three personas, one demo path | accepted | 2026-10-17 |
| [0003](0003-asset-classes-and-profile-inputs.md) | Six asset classes and eight profile inputs | accepted | 2026-10-17 |
| [0004](0004-constrained-mean-variance.md) | Constrained mean-variance allocation | accepted | 2026-10-17 |
| [0005](0005-drawdown-by-historical-replay.md) | Enforce the drawdown limit by historical replay | accepted | 2026-10-17 |
| [0006](0006-rule-based-liquidity-tiers.md) | Rule-based liquidity tiers | accepted | 2026-10-17 |
| [0007](0007-risk-metrics-and-scenarios.md) | Risk metrics and calibrated scenarios | accepted | 2026-10-17 |
| [0008](0008-validation-strategy.md) | Validation without ground truth | accepted | 2026-10-17 |
| [0009](0009-streamlit-app-and-stack.md) | Streamlit app and small tool stack | accepted | 2026-10-17 |
| [0010](0010-multi-user-local-accounts.md) | Multi-user local accounts | accepted | 2026-10-17 |
| [0011](0011-data-sources-and-handling.md) | Data sources, licensing handling and frozen snapshot | accepted | 2026-10-17 |
| [0012](0012-delivery-plan-and-cut-order.md) | Delivery plan, cut order and documentation | accepted | 2026-10-17 |
| [0013](0013-illiquid-fixed-and-modelling-conventions.md) | Illiquid holdings held fixed, and four modelling conventions | accepted | 2026-10-17 |
| [0014](0014-app-structure-and-visual-direction.md) | App structure and visual direction | accepted | 2026-10-17 |
| [0015](0015-guided-plan-and-strategies-by-comfort-level.md) | Guided plan, with strategies built for each comfort level | accepted | 2026-10-18 |
| [0016](0016-hosting-and-public-link-protections.md) | Hosting approach and public-link protections | accepted | 2026-10-18 |
| [0017](0017-react-fastapi-migration.md) | React and FastAPI front and back end over the unchanged engine | accepted | 2026-10-19 |
| [0018](0018-guided-plan-api-and-live-recalculation.md) | Guided plan API and live recalculation | accepted | 2026-10-19 |
| [0019](0019-personalised-dashboard-and-analyst-workspace.md) | Personalised dashboard and analyst workspace | accepted | 2026-10-19 |
| [0020](0020-holdings-import-and-consolidation.md) | Holdings import and consolidation | accepted | 2026-10-20 |
| [0021](0021-grounded-explainer-copilot.md) | A grounded explainer, not a generative chatbot | accepted | 2026-10-21 |
| [0022](0022-authentication-own-or-managed.md) | Sign-in: keep our own for now, decide on a managed provider before real data | proposed | 2026-10-23 |

ADR-0013 amends parts of ADR-0003, ADR-0005 and ADR-0006. ADR-0014 builds on ADR-0009 and ADR-0010. ADR-0016 builds on ADR-0010 and ADR-0014.
ADR-0017 builds on ADR-0009, ADR-0010, ADR-0014 and ADR-0016 and leaves the engine decisions (0004 to 0007, 0013) untouched.
ADR-0018 builds on ADR-0015 and ADR-0017.
ADR-0019 builds on ADR-0017 and ADR-0018.
ADR-0020 builds on ADR-0010, ADR-0011, ADR-0017 and ADR-0019.
ADR-0021 builds on ADR-0017, ADR-0019 and ADR-0020.
ADR-0022 builds on ADR-0010, ADR-0016 and ADR-0017; it is a proposal, not yet decided.

Requirements: [../requirements.md](../requirements.md). Blank template: [template.md](template.md).

All records were written on 2026-10-17 from one scoping session. Deciders: the project owner,
facilitated by Claude using the grill-me skill.
