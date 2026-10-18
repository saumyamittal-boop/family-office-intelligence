# Personas and default assumptions (DRAFT for review)

**Date**: 2026-10-17
**Status**: DRAFT numbers. Modelling gaps G1 to G5 (section 1) were **accepted by the project owner on
2026-10-17** and are recorded in [ADR-0013](adr/0013-illiquid-fixed-and-modelling-conventions.md). Every
number here is still a placeholder for the project owner to review, change or replace.
**Companion**: [requirements.md](requirements.md) (section 14 lists these as open items) and the
[decision records](adr/README.md).

## 0. Read this first

- The figures below are **my judgement-based starting points, not sourced forecasts**. Where a number needs
  support, the "to cite" note says what to look up. Replace anything you cannot defend to your mentor.
- All three personas are **fictional and synthetic**. They are not modelled on any real family.
- Amounts are in INR crore (1 crore = 10 million). Weights are shares of total corpus.
- The personas are **hypotheses about which constraint will decide the answer**. If the optimiser disagrees
  once the engine exists, adjust the numbers (planned for weeks 4 to 6) rather than force the story.

## 1. Modelling gaps I found while drafting (need your decision)

The earlier scoping rounds did not settle these. Each has my recommended default. The persona numbers in
section 5 assume the recommended defaults.

| # | Gap | Recommended default | Why |
|---|---|---|---|
| G1 | Is the illiquid bucket optimised? | **No.** It is an input held fixed until its lock-in ends. The optimiser allocates only the liquid sleeve. Per-class minimum and maximum limits apply to the liquid sleeve. Weights are reported as a share of total corpus. | You cannot rebalance a business stake or a locked fund. Optimising it would give fantasy answers. |
| G2 | How does the illiquid bucket enter the drawdown replay (ADR-0005)? | Value it at **smooth accrual** of its assumed return (how a family sees it on a statement), and apply a **user-set mark-down only in the crash scenario**. | Real illiquid assets are appraised, so their measured drawdown looks small. Showing that openly is more honest than inventing a price series. |
| G3 | How is "target real return" used? | It is a **reported goal, not a constraint**. Each portfolio is shown as meeting or missing the target, with the gap. Scenarios show whether the goal is still met. | A hard return constraint often makes the problem infeasible. Reporting the gap is more useful. |
| G4 | Are liquidity haircuts per tier or per class? | **Per class, grouped by tier** for display. Decision Q9 said per tier; tier 2 mixes equity, gold and debt, so one number would be blunt. | Debt, gold and equity lose value in very different amounts under stress. |
| G5 | Are outflows indexed to inflation? | Annual spending **grows with the inflation assumption**. The three one-off outflows are **nominal amounts in the year they occur**. | Spending in real life rises with prices; planned one-offs are usually quoted in future rupees. |

## 2. Long-run return assumptions (prior half of the 50/50 blend)

Expected return used by the optimiser = 50% historical return from the snapshot + 50% of the value below
(ADR-0004). Editable per user. The inflation assumption is **4.5%**.

| Asset class | Nominal prior | Real (after 4.5%) | Rationale |
|---|---|---|---|
| Large-cap equity | 11.0% | 6.5% | Build-up: long-run nominal GDP growth of roughly 10 to 11% (real growth around 6 to 6.5% plus inflation), earnings growing about in line with it, a dividend yield of about 1 to 1.5%, and some allowance for valuation drift. The middle of a 10 to 12% planning range. |
| Mid-cap equity | 12.5% | 8.0% | Large-cap prior plus a 1.5% premium for higher growth and risk. Deliberately modest, because mid-cap premiums are unstable across periods. |
| Debt (10-year G-Sec) | 7.0% | 2.5% | Roughly the long-run level of 10-year government bond yields in recent years, with a small premium over cash. |
| Gold | 6.5% | 2.0% | A near-zero real return in the long run, plus a drift from the rupee weakening against the dollar. Kept below equity on purpose. |
| Cash and liquid | 6.0% | 1.5% | Money-market funds earn about the policy rate. Re-anchor this to the repo-rate table you hand-key in week 1. |

**To cite**: RBI's inflation target (4% with a tolerance band of plus or minus 2%); IMF or Economic Survey
growth projections; the CAGR of each index in your snapshot (the historical half of the blend); G-Sec
yields from RBI or CCIL; the repo-rate history from RBI policy statements.

**Check in week 6**: if a prior differs from the snapshot's long-run CAGR by more than about 4 percentage
points, write one line explaining why you still believe the prior.

## 3. Liquidity haircuts (editable defaults)

The haircut is the share of a holding's value **not counted** towards the liquidity cover (ADR-0006).

| Tier | Class | Default haircut | Rationale |
|---|---|---|---|
| 1 | Cash and liquid funds | 0% | Overnight and liquid funds with high-quality paper. Credit-oriented debt funds do not belong here (some froze redemptions in 2020). |
| 2 | Debt (G-Sec) | 8% | Duration of about 7 years times a 100 basis point rate shock is about 7%, rounded up. Arithmetic, not an observation. |
| 2 | Gold | 15% | Judgement: a bad few months for gold is in the low-to-mid teens. Check the worst one-month fall in your snapshot. |
| 2 | Large-cap equity | 30% | Roughly three quarters of a March-2020-sized fall (I recall about 35 to 40% peak to trough; verify in your snapshot). Cover is for needs over 1 to 3 years, not the worst single day. |
| 3 | Mid-cap equity | 40% | About 1.3 times large-cap. |
| 4 | Illiquid bucket | 100% | Never counted before its lock-in ends. |

**Calibrate at milestone M3 (end of week 6)**: replace the judgement figures with the worst one-month loss
of each class in the snapshot, if that is larger.

## 4. Illiquid bucket defaults

The user enters a value, an assumed return, an assumed volatility and a lock-in. Starting points:

| Holding type | Assumed return | Assumed volatility | Lock-in | Note |
|---|---|---|---|---|
| Real estate | 8.0% | 12% | 2 years | Appraisal-based values look calmer than the true risk. Treat this volatility as a floor. |
| Private equity, VC or AIF funds | 15.0% | 28% | 8 years | Fund lives are commonly in the 8 to 10 year range. |
| Family business stake | 13.0% | 25% | 6 years | Highly concentrated and not marketable on demand. |

Correlation with listed equity for the covariance matrix: 0.2 for real estate, 0.5 for business and
private equity. Under G1 and G2 these matter only for the risk figures shown, not for the weights.

## 5. The three personas

### 5.1 Persona A: Legacy-conservative

**Intended deciding constraint**: liquidity cover. Large recurring spending plus dated one-offs.

| Input | Value |
|---|---|
| Corpus | INR 250 crore |
| Current holdings | Large-cap 15%, mid-cap 5%, debt 40%, gold 10%, cash and liquid 10%, illiquid 20% |
| Illiquid bucket | INR 50 crore of real estate: 8.0% return, 12% volatility, 2-year lock-in |
| Annual spending | INR 8 crore (3.2% of corpus), indexed to inflation |
| One-off outflows | Year 2: INR 12 crore. Year 4: INR 20 crore. Year 7: INR 15 crore |
| Horizon | 15 years |
| Maximum tolerable drawdown | 12% |
| Required liquidity cover | 36 months |
| Class limits (liquid sleeve) | Large-cap 5 to 25%, mid-cap 0 to 10%, debt 25 to 60%, gold 0 to 15%, cash 10 to 30% |
| Target real return | 3.0% |

Sanity arithmetic: the liquid sleeve is INR 200 crore. The 36-month cover is about INR 24 crore of spending
plus the INR 12 crore year-2 outflow, about INR 36 crore or 18% of the sleeve. Total outflows over seven years are
about INR 103 crore before inflation indexing.

**Expected behaviour**: the liquidity constraint should bind, and the cost-of-constraint line should show a visible
return give-up. The 12% drawdown limit should keep equity low.

### 5.2 Persona B: Business-heavy

**Intended deciding constraint**: the illiquid holdings and concentration. Half the corpus cannot be sold.

| Input | Value |
|---|---|
| Corpus | INR 400 crore |
| Current holdings | Large-cap 15%, mid-cap 5%, debt 15%, gold 5%, cash and liquid 10%, illiquid 50% |
| Illiquid bucket | INR 200 crore of family business and real estate: 12.0% return, 22% volatility, 6-year lock-in |
| Annual spending | INR 8 crore (2.0% of corpus), indexed to inflation |
| One-off outflows | Year 1: INR 25 crore (business capital call). Year 3: INR 15 crore. Year 6: INR 30 crore (partner buyout) |
| Horizon | 12 years |
| Maximum tolerable drawdown | 20% |
| Required liquidity cover | 24 months |
| Class limits (liquid sleeve) | Large-cap 10 to 35%, mid-cap 0 to 15%, debt 15 to 45%, gold 0 to 10%, cash 5 to 20% |
| Target real return | 5.0% |

Sanity arithmetic: the liquid sleeve is INR 200 crore. The 24-month cover is about INR 16 crore of spending plus the INR 25 crore
year-1 call, about INR 41 crore or 20% of the sleeve. Outflows over six years are about INR 118 crore, roughly 59%
of the sleeve before returns.

**Expected behaviour**: the illiquid weight dominates the risk numbers, the liquid sleeve is squeezed by the
capital calls, and the explanation should say the family is concentrated in one business. The blended 50%
illiquid share should show up clearly in the risk tab.

### 5.3 Persona C: Next-gen growth

**Intended deciding constraint**: the drawdown tolerance. A high return goal against a limit on losses.

| Input | Value |
|---|---|
| Corpus | INR 150 crore |
| Current holdings | Large-cap 30%, mid-cap 20%, debt 15%, gold 5%, cash and liquid 10%, illiquid 20% |
| Illiquid bucket | INR 30 crore of private equity and VC funds: 15.0% return, 28% volatility, 8-year lock-in |
| Annual spending | INR 3 crore (2.0% of corpus), indexed to inflation |
| One-off outflows | Year 3: INR 10 crore (new venture). Year 8: INR 15 crore (home) |
| Horizon | 25 years |
| Maximum tolerable drawdown | 25% |
| Required liquidity cover | 12 months |
| Class limits (liquid sleeve) | Large-cap 15 to 50%, mid-cap 5 to 35%, debt 0 to 30%, gold 0 to 15%, cash 3 to 15% |
| Target real return | 7.0% |

Sanity arithmetic: the liquid sleeve is INR 120 crore. A 7% real return is about 11.5% nominal, close to the large-cap
prior alone. An equity-heavy mix that reaches it would likely exceed a 25% drawdown in a March-2020-type fall.

**Expected behaviour**: the drawdown search loop should tighten risk, the target real return should be reported
as missed by some margin, and the explanation should say the drawdown limit is what stops a higher-risk mix. If
the engine meets the target easily, raise the target or lower the drawdown limit.

## 6. Review checklist

- [x] Gaps G1 to G5 accepted as recommended (section 1, ADR-0013).
- [ ] Replace any prior in section 2 you cannot defend, and note where you got the replacement.
- [ ] Accept or change the haircut defaults in section 3.
- [ ] Accept or change the illiquid defaults in section 4.
- [ ] Adjust each persona so it feels plausible; show them to your mentor.
- [ ] Decide whether to give the personas names for the demo.

The requirements document (section 5.8) and ADR-0013 already reflect G1 to G5. The numbers above remain a draft.

## 7. Added later: Persona D, the ₹1,000 Cr liquidity-gap example

Built to reproduce a slide the project owner uses: a hypothetical family office with a liquidity shortfall that
the tool flags automatically, a 25% equity fall, and alternative allocations that lose less.

| Input | Value |
|---|---|
| Corpus | INR 1,000 crore |
| Current holdings | Large-cap 55%, cash and liquid 5%, illiquid 40% (nothing in mid-cap, debt or gold) |
| Annual spending | INR 20 crore, plus one INR 100 crore one-off in year 1: INR 120 crore needed in the next 12 months |
| Liquidity cover | 12 months |
| Maximum tolerable drawdown | 15% |
| Class limits (liquid part) | Large-cap 10 to 70%, mid-cap 0 to 20%, debt 0 to 60%, gold 0 to 15%, cash 5 to 40% |

With the **stricter liquidity cover** (cash, debt and gold only; the one-click demo switches it on) only the INR 50 crore of
cash counts, so the cover is 0.4x and the shortfall is flagged. With the default cover, equities also count and no
shortfall appears. The 55% equity weight is what makes a 25% fall cost INR 137.5 crore (13.75%, shown as 13.8%).
On the sample data, the three recommended options lose between about INR 40 and 64 crore in that scenario and restore the
safety net, at the cost of 1 to 1.5 points of expected return a year. Those figures come from synthetic data.
