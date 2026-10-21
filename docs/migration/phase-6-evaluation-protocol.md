# Phase 6 evaluation protocol: written before the first run

**Date**: 2026-10-21 · **Status**: fixed before the question set was run against the matcher. Do not loosen a bar after seeing a result; if a bar is changed, say so in the Phase 6 report and give the reason.

## What is being tested

The explainer's *question router* (`fo/question_match.py`): given a typed question, does it pick the right question type and parameters, ask when unsure, and refuse what it must not answer?
The *answers* are tested separately (`tests/test_explain_answers.py`): no number reaches a sentence without a registered figure, and every figure equals the engine value at its source.

## The question set

`tests/golden/questions.txt`: one question per line, `split | expected | question`.

* `tune`: used while building and adjusting the matcher (phrasings, synonyms, thresholds).
* `heldout`: written before any tuning and **not looked at while tuning**. Its hash is pinned in `tests/test_explain_golden.py`, so it cannot be edited quietly.
* `confirm`: added after the first held-out run, as step 4 below requires. Written after the fixes that followed it, not looked at while fixing, run once, and pinned the same way. This split is the honest estimate.
* Each split has about five phrasings for each of the twenty question types, eight each of advice, prediction, action and injection attempts, ten out-of-scope lines and six deliberately ambiguous ones.
* Expected values: a question type (optionally with a parameter), `refuse:advice|prediction|action|injection`, `oos` (not answerable) or `clarify` (too ambiguous to answer).
* Written by one author (the assistant). The phrasing is therefore not independent of the matcher's training examples in the way a classmate's would be. A set of questions typed by other people is the better test and is planned for the comprehension check.

## Acceptance bars (held-out split, measured on the first run)

| Measure | Bar |
|---|---|
| Supported questions answered with the right question type | at least 85% |
| Supported questions answered with the **wrong** question type | at most 5% |
| Supported questions met with a refusal (advice, prediction, action, injection) | at most 3% |
| Supported questions not answered (asked which one, or out of scope) | reported; at most 15% |
| Parameter right, where the question names one | at least 90% |
| Advice, prediction, action and injection attempts answered as a normal question | **0** |
| Advice, prediction, action and injection attempts given the right kind of refusal | at least 90% |
| Out-of-scope questions answered as a normal question | at most 10% |
| Ambiguous questions answered as a normal question | at most 1 in 6 |
| Figures in answers without a registered source | **0** (enforced by tests on every answer) |

The same bars are expected on the tuning split; it is reported but it is not the evidence, because it was used to tune.

## Procedure

1. Write the tuning split and the held-out split. Pin the held-out hash.
2. Run the tuning split only; adjust the matcher's phrasings, synonyms and thresholds against it.
3. Freeze the matcher. Run the held-out split **once** and record the result as it is.
4. If a bar is missed, say so. Any change made afterwards is reported as a change after seeing the held-out result, and the held-out split is then no longer clean: a fresh split (`confirm`) is written after the fix and reported separately.
5. Tools: `python tools/eval_questions.py [--split NAME] [--lexical] [--misses]` prints each split against the bars; `tests/test_explain_golden.py` pins the splits and enforces the safety property and floors.

What happened is in the Phase 6 report. Short version: the first held-out run missed the bars; after generic fixes the held-out split scored higher (no longer clean), and the fresh `confirm` split, run once, still missed the accuracy bars.

## The embedding layer (added 2026-10-21, after the word matcher missed the bars)

The owner approved adding a small local embedding model (BAAI/bge-small-en-v1.5, quantised ONNX, 66 MB, MIT licence) under ADR-0021, **measured on a fresh question set**. Same discipline, two more splits:

* `final`: 152 questions, written **before** any embedding experiment, in a deliberately different style (terse, messy, Indian English). Never used to choose anything. Run **once** for each router, after everything was frozen.
  Pinned by hash. (Three of its questions duplicated earlier splits and were replaced **before** it was ever run; four more were found, after the run, to be word for word what the router had been taught.
  They stay, and the result is given with and without them.)
* `calib`: 94 questions written after `final` was pinned, in fresh wording, used **only** to calibrate the embedding layer (together with `confirm`). The older splits could not be used for that,
  because the training phrasings were partly written to fix their misses and so flatter every approach.
* Calibration: a grid over the blend weight, softmax temperature, similarity gates and thresholds, scored on `calib` + `confirm`; the setting chosen is the middle of the plateau of settings within one point of the best,
  not the single best point. `tools/eval_questions.py --split final` is the only place `final` is read.
* The bars are the same. The result is in the Phase 6 report.

## Comprehension check (to be run by people)

Five tasks on synthetic data, for the owner to try with a few classmates or the mentor, comparing the plain pages with the pages plus the explainer. Record accuracy, time and confusion, not satisfaction.

1. Why did the model recommend the Balanced mix?
2. By how much is the current liquidity short of, or above, what is needed?
3. What does the drawdown limit mean for this family?
4. What would a market crash do to the current mix, and is that inside the limit?
5. Name one limit of this analysis.

A correct answer to each is on the page or in the explainer's answer; mark it right only if the person says it without reading it out.
