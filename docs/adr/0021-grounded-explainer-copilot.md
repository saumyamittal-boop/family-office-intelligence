# ADR-0021: A grounded explainer, not a generative chatbot

**Date**: 2026-10-21
**Status**: accepted on 2026-10-21 (the owner approved the scope: "start phase 6 then"). Built in Phase 6; see the outcome at the end and [the Phase 6 report](../migration/phase-6-report.md)
**Deciders**: Project owner, facilitated by Claude. The owner held back the LLM option on 21 October 2026 and ran the alternatives research themselves; the findings are summarised here.
**Builds on**: [ADR-0017](0017-react-fastapi-migration.md) (decision D7: rule-based and grounded first; an LLM only later, optional, off by default, with separate approval), [ADR-0019](0019-personalised-dashboard-and-analyst-workspace.md) and [ADR-0020](0020-holdings-import-and-consolidation.md)

## Context

The Assistant page is a placeholder. The brief for Phase 6 is to compare a rule-based, an LLM and a hybrid copilot, get approval, build the chosen one, and test explanation accuracy, failure handling and privacy.
The product explains the output of a deterministic engine for Indian families (₹ crore). Every number shown must come from that engine. Family holdings should not leave the machine. The data is synthetic and the app says it is
"an illustrative simulation, not investment advice". Imported statements put user-supplied text (holding names, labels) into the app. The development machine is a Windows laptop (Ryzen 7 6800HS, 15 GB RAM, RTX 3050 with 4 GB VRAM).
The mentor meeting is **Saturday 24 October 2026**; the research report assumed a three-week window, so the scope below is built in small increments, each usable on its own.

What exists to ground answers: the per-mix reasons (`fo/engine.py::_explain`), the rule-based insights (`build_insights`, `comparison_insights`), the buy and sell plan, the scenario and stress results, the liquidity ladder and outflows,
the history replay, the projection, and the holdings consolidation. All are already computed, cached and covered by the golden master or by Phase 4 and 5 tests.

## What the research found (summary; the owner's report of 21 October 2026)

- **The useful split is language versus authority.** A language component may be allowed to decide *what was asked*; it must not write *what is true*. Free-form chat (cloud or local) and "a model rewords a fact sheet" both leave generated prose
  as the source of meaning. A number checker stops invented figures but not a changed caveat, an omitted limit, or a right number in the wrong context (for example a 15% drawdown **limit** presented as a predicted **loss**).
- **Explanations can raise trust without raising understanding.** A 2023 study (Bertrand, Eagan, Maxwell, ACM FAccT) found feature-based explanations did not improve appropriate reliance or understanding, and conversational explanations raised
  trust, sometimes to users' detriment. A 2026 working paper on a real French robo-adviser found graphical explanations did not raise adherence (not peer-reviewed as far as the report could verify). A 2023 *Memory & Cognition* study
  (four experiments, 731 people) found counterfactual explanations were often judged more helpful but did not consistently improve prediction of the AI, and in one experiment improved people's own decisions. Read together: design for
  understanding and informed disagreement; test comprehension, not satisfaction; prefer "what would change this?" over longer prose.
- **A bounded intent router fits the constraints.** A fixed catalogue of question types, a matcher that returns an intent and validated parameters, a threshold and margin with a clarifying question, and deterministic reviewed templates
  need no generative model. An embedding matcher (ONNX, on CPU) is a cheap upgrade over keywords if keywords fall short; a small local model (about 3B to 4B, for example Qwen3-4B-Instruct-2507, Apache 2.0) can be benchmarked as a router
  through Ollama or llama.cpp with JSON-schema output, but its Indian-English accuracy on this task is **unmeasured**, and valid JSON can still hold a wrong intent.
- **Regulation and privacy (summary, not legal advice; to be re-checked against primary sources before any pilot).** SEBI's amended Investment Advisers Regulations (notified 16 December 2024) make registered advisers responsible for AI-based
  advice and its data security and require disclosure of AI use; SEBI's 20 June 2025 consultation paper on responsible AI/ML is a consultation, not final guidance, and no final replacement was found. A disclaimer does not decide whether an answer
  is "advice"; personalised suggestions to change a securities portfolio, offered as a service, raise that question whatever the technology. The DPDP Rules 2025 (notified 14 November 2025) commence in phases (rules 1, 2 and 17 to 21 at once, rule 4
  after a year, rules 3, 5 to 16, 22 and 23 after 18 months, about May 2027); there is no separate "sensitive financial data" class, but financial data about an identifiable person is personal data, and uploaded statements may contain real identifiers.
- **Providers (for a possible later cloud mode).** Retention, training use and residency differ by vendor, endpoint and contract; none was shown to give an Indian-residency guarantee on the direct API. A silent fallback from a local model to a cloud one would break the privacy promise.
- **Uploaded files are an injection path.** Holding names and cell text must be treated as quoted data, never as instructions, whatever the model.

Evidence labels: the studies and regulations above are primary or peer-reviewed except where marked; architecture ratings and effort estimates in the report are engineering judgement, not measurements; model speeds are planning ranges to be
measured on the laptop.

## Decision (proposed)

1. **The model never authors an answer or a number.** Phase 6 builds a *grounded explainer*: answers are reviewed templates filled from engine results by deterministic code. No language model is used in Phase 6. This keeps D7 and the "no AI" side of
   the privacy promise.
2. **Typed figures with provenance.** An answer is `{intent, title, blocks, figures, caveats, sources, follow_ups}`. Each figure carries `{label, value, unit, source}` where `source` names the engine field and the page it appears on. Formatting (₹ crore,
   percentages) is done in one place. The UI has a "Show the evidence" panel listing the figures, assumptions and limits behind each answer. A test checks that every figure equals the engine value at its source and is shown only with its own label.
3. **Three ways in, one answer layer.** (a) Question chips for the common questions; (b) "Why?" buttons on the dashboard's warnings and headline numbers that open the same answers; (c) a free-text box.
4. **Free-text routing is a bounded matcher.** A fixed catalogue of about twenty intents with a few parameters each (which mix, which scenario, which asset class). The matcher is lexical first (normalised words, synonyms, Indian-English and
   spelling variants, no model download, instant, fully deterministic). It accepts only above a threshold and a margin over the second-best intent, otherwise it asks which of the nearest two the person meant and offers the chips.
   **An embedding matcher is added only if the lexical one misses the acceptance bar** on the frozen question set; a local generative model is not benchmarked in this phase.
5. **Safe failure is a feature with its own intents.** Advice-seeking ("which stock should I buy"), price prediction ("what will Nifty do next month"), actions ("move everything into the highest-return asset"), out-of-scope questions, ambiguous
   questions, and missing data each get a fixed, reviewed reply that says what the explainer can do. Refusing everything is a failure too; false refusals are measured.
6. **Untrusted text stays data.** The question text is length-capped, never interpolated into anything but an escaped echo, and never reaches a model. Holding names appear in answers only as escaped, length-capped data. The explainer reads only the
   signed-in account's own profile (the same ownership check as every other route); it has no tool, file or database access of its own.
7. **Stateless and quiet.** Questions are not stored. The server logs the intent id and the match confidence, not the text. The route is rate-limited like the others.
8. **Decision support over persuasion.** Answers lead with the result in one plain sentence, then the *why*, a comparison, the limits, and a "what would change this?" step. The tone avoids urging a person to follow the recommendation.
   "What would change this?" first links to the existing Scenarios lab with the relevant dial set; a *change one input and recompute* call (spending, a commitment, the drawdown limit, the cover months, on an unsaved copy validated by the
   profile rules) is a second increment, included only if the first is done and tested.
9. **Evaluation is fixed before it is run.** A frozen golden set of synthetic questions (supported, paraphrased, Indian-English phrasing, typos, ambiguous, adversarial, injection-in-holding-name) with the expected intent, parameters and required
   caveats, written before the matcher is tuned and split into a tuning half and a held-out half. Acceptance bars (exact intent and parameters on held-out supported questions; zero ungrounded figures; zero advice or prediction answered as if in scope;
   false-refusal rate reported) are written into the Phase 6 report **before** the first run. Mutation checks as in Phases 4 and 5.
10. **A comprehension check, run by people.** A short protocol (five synthetic tasks: why this mix, what is the liquidity shortfall, what does the drawdown limit mean, what changes if a commitment grows, what are the limits of the result) is written
    for the owner to try with a few classmates or the mentor; accuracy and confusion are recorded, not satisfaction. I cannot run this myself.
11. **An LLM later, only behind a switch.** The router is an interface. A local model may later replace the matcher (route only; Python still writes the answer) if a measured comparison on the frozen set justifies it, with the owner's separate approval.
    Rewording by a model, and any cloud model, stay out until privacy, retention, contract and regulatory reviews are done, and would be opt-in, never a silent fallback.

## Alternatives Considered

### Alternative 1: Free-form chat with a cloud model
- **Pros**: Flexible, quick to demo.
- **Cons**: Can state wrong figures or drop caveats; family data leaves the machine; prompt injection through uploaded names; not reproducibly testable; running cost.
- **Why not**: Fails two hard constraints (numbers from the engine only; data stays local).

### Alternative 2: Hybrid, a model rewords a verified fact sheet
- **Pros**: Natural wording with a number check.
- **Cons**: The check does not protect meaning, caveats or context; most of the build is the checker and the redaction; still sends data out if cloud.
- **Why not**: More machinery for a benefit nobody has yet measured. Revisit with the frozen set and the comprehension check.

### Alternative 3: A small local model as the router now
- **Pros**: Handles unforeseen phrasing; nothing leaves the machine; fits the laptop.
- **Cons**: Unmeasured on this task and on Indian English; a heavier install; valid output can still be a wrong intent.
- **Why not yet**: The lexical matcher is the baseline it must beat; keep the interface so it can be tried.

### Alternative 4: Rules and templates with keyword matching only
- **Pros**: Simplest.
- **Cons**: Brittle at the question box; no "what would change this?".
- **Why not**: Kept as the baseline and for the chips, but extended with the matcher, the "Why?" entry points and the what-if step.

### Alternative 5: A natural-language query layer over the engine (arbitrary queries)
- **Pros**: Powerful for analysts.
- **Cons**: Generated queries or code are an injection and correctness risk.
- **Why not**: The fixed intent catalogue is the safe subset of this idea.

## Consequences

### Positive
- Every sentence in an answer can be traced to a reviewed template and an engine value, and tested like the engine is.
- Works offline, costs nothing to run, and sends nothing out.
- Gives the mentor a demonstrable, defensible privacy and safety story; the evaluation protocol is itself a deliverable.

### Negative
- Unforeseen questions get "I can't answer that, here is what I can", which will feel less capable than a chatbot.
- About twenty templates must be written, reviewed and kept in step with the engine's wording.
- Lexical matching needs tuning for phrasing; the held-out set is what keeps that honest.

### Risks
- A template can state something the engine's rules do not support; mitigated by deriving each answer from the existing reasons and insights rather than restating them.
- Explanations may increase confidence without understanding; mitigated by the layered answer, the evidence panel and the comprehension check, and by not measuring success as agreement.
- Regulatory classification of "personalised suggestions" is untested; mitigated by keeping the app an illustrative simulation with synthetic data, and by re-checking SEBI and DPDP primary sources before any pilot.

## Scope proposed for Phase 6 (increments, each usable on its own)

1. The answer layer, about twenty intents, chips and the Assistant page, with typed figures and the evidence panel.
2. "Why?" entry points on the dashboard's warnings and headline numbers.
3. The free-text matcher with clarification and the safe-failure intents.
4. The frozen question set, the acceptance bars, the report and the comprehension protocol.
5. Only if time allows: *change one input and recompute*.

Sources are the studies and regulations named above; full citations are in the owner's research report of 21 October 2026. Check each primary source again before relying on it for a pilot.

## Outcome of the build (added 2026-10-21)

Increments 1 to 4 were built; increment 5 (change one input and recompute) was not. Where the build departed from the decisions above:

* **Decision 4 (routing): the condition for the next step was met.** The lexical matcher was meant to be replaced by an embedding matcher only if it missed the acceptance bars on the frozen set.
  It did: the first held-out run scored 76% right (bar 85%), and a fresh set written after the fixes scored 67%. The embedding matcher is therefore the proposed next step, but it needs a model download and a new dependency, so it waits for the owner's decision. A local generative model was not tried.
* **The embedding matcher was then added, with the owner's approval** (2026-10-21): BAAI/bge-small-en-v1.5, quantised ONNX, 66 MB, fetched once by `tools/fetch_embedding_model.py` into `data/models/` (not committed), loaded from disk only
  (never downloaded by the server), file hashes checked, optional (without it the router is the word matcher alone). A softmax over similarities to every training phrasing, mixed with the word score, plus separate gates for "close enough to
  ask which" and "close enough to answer", plus a refusal check against phrasings of what must not be done. On a fresh set written before any experiment it scored **79% right (word matcher alone: 71%)** against a bar of 85%:
  better, safer, and still short. No language model of any kind generates text.
* **The safety property mostly held, and slipped twice.** The first held-out run answered two requests that should have been declined, and the one run of the final split answered one ("invest in the balanced mix", which explained the mix; nothing was invested). Each was fixed with a general rule and is covered by tests with fresh wording. Without the embedding model the router declines less often than with it.
* **Decision 9 (evaluation) took five splits instead of two**: tune, held-out (run once; no longer clean after fixes made in view of it), confirm (written after the fixes, run once), calib (to calibrate the embedding layer) and final (written before any embedding experiment, run once). See [the evaluation protocol](../migration/phase-6-evaluation-protocol.md).
* **Added:** beside a typed answer the person is shown the nearest other questions ("Not what you meant?"), because the router answers the wrong question about one time in ten on fresh phrasing.
* **Decision 3(b)** was done as a "Why?" button on each warning and under "About this number", opening the same answer in a side panel; it was not added to every headline tile.
