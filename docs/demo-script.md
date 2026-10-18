# Three-minute demo script

Two stories, about 3 minutes: **(1) a family that has no idea what to do** (the guided plan), then
**(2) a ₹1,000 Cr family with a liquidity gap** (the app catches the problem and compares options).
Every number below is what the current sample data shows. If you change an assumption or the sample data,
re-check the numbers before the day.

## Before you start (2 minutes, every time)

- [ ] Start the app: PowerShell, `cd D:\family-office-intelligence`, `.\.venv\Scripts\Activate.ps1`, `streamlit run app.py`.
- [ ] Open http://localhost:8501 full screen at 100% zoom. Close other tabs and notifications.
- [ ] Start **signed out**, on the login screen. (The text font loads from the internet; offline it falls back to a plain font.)
- [ ] **Do not refresh the page.** Refreshing signs you out. If it happens, click the demo button again.
- [ ] **Do not click Save** on the demo accounts. They are shared, and a save adds a profile to them.
- [ ] Rehearse the clicks twice with a timer. Keep a screen recording as a backup in case the laptop misbehaves.

## The script

### 0:00 to 0:15. The login screen

**Say:** "This is Family Office Intelligence. It's for a family that has real wealth but no family office or fund
manager to ask. Everything you'll see runs on synthetic sample data, so read the numbers as a demo, not as advice."

**Click:** **Legacy-conservative family**, then **Plan my money** in the top bar.

### 0:15 to 1:20. Story 1: "I have ₹100 crore and no idea" (Plan my money)

| Step on screen | Do | Say |
|---|---|---|
| 1. Tell us about the family | Leave 100 and 3. **Continue** | "I only know I have ₹100 crore and spend about ₹3 crore a year. Notice it asks for no returns and no volatility." |
| 2. Anything big coming up? | **Continue** (nothing planned) | "A wedding or education would go here with a year and an amount." |
| 3. How do you feel about a bad year? | Leave *Balance*. **Continue** | "It asks how big a fall I could sit through, in rupees: 15% of ₹100 crore is ₹15 crore." |
| 4. Your safety net | **Continue** | "Twelve months of spending must stay within easy reach. Shares don't count, because they can be down exactly when I need cash." |
| 5. What does the family own today? | **See my strategies** | "A rough picture is enough; it starts from a typical split." |

**On the results page, say:** "Three strategies, and B is recommended for me. In a typical year B ranges from
**+3.5% to +16.8%**. The worst year in the history was **−6.8%**, and a 2020-style crash costs **₹15.5 crore**.
A is gentler: its worst year is about zero. C expects the most growth, **9%**, but its worst year is **−11.8%** and
it's flagged as *beyond my comfort*. So the trade-off is visible, and B is honest: it's just under my 4% real-return goal."

**Scroll** to *How a year can turn out* (one line: "bars are the typical year, the cross is the worst year"), then to
*What to buy and sell*.

**Say:** "For B: sell **₹15.6 crore** of large-cap index fund, buy **₹8.4 crore** of mid-cap and **₹14.9 crore** of bond
fund. These are kinds of product, not stock picks."

### 1:20 to 2:35. Story 2: the ₹1,000 crore family with a liquidity gap

**Click:** **Log out** (left sidebar), then **₹1,000 Cr liquidity-gap example**.

**Say:** "A ₹1,000 crore family. ₹550 crore is in shares, only ₹50 crore is easy to reach, and **₹120 crore** is needed in
the next 12 months."

**On the Overview, point at:** the *Liquidity cover* tile (**0.4x**, ₹50 Cr vs ₹120 Cr needed) and the insight
*Liquidity shortfall*. **Say:** "Nobody asked it to look for this. It also notes the mix lost **28%** in the history against a
**15%** limit."

**Click:** **Scenarios**, then scroll to *Compare your options under one scenario* ("Equities fall 25%" is already selected).

**Say:** "If shares fall 25%, the current mix loses **₹137.5 crore, 13.8%**. All three options lose far less, between
**₹40 and ₹64 crore**, and they restore the safety net. The price is growth: about **1.6 points** of expected return a
year, from 9.8% down to 8.3%. That trade-off is the product."

### 2:35 to 3:00. Close

**Say:** "What's real: the optimiser, the risk replay and the liquidity checks. What's still a placeholder: the data,
which is synthetic until we settle licensing for real NSE and AMFI data. Next: a pilot with one friendly family
office, real data, and a deployed link. My question for you: is this for families without an office, or for the fund
manager who already has one?"

## Running long? Cut in this order

1. Skip the *How a year can turn out* chart.
2. Skip the *What to buy and sell* detail.
3. In Story 2, skip the Overview and go straight to Scenarios.

## Numbers to have in your head

| | |
|---|---|
| Story 1 | ₹100 Cr, spend ₹3 Cr. B: +3.5% to +16.8%, worst −6.8%, crash −₹15.5 Cr, expects 8.5%. C: expects 9.0%, worst −11.8%, beyond comfort. |
| Story 2 | ₹1,000 Cr. ₹50 Cr easy money vs ₹120 Cr needed = 0.4x. Equities −25% = −₹137.5 Cr (−13.8%). Options lose ₹39.7 / ₹45.0 / ₹63.7 Cr. Cost: 9.8% to 8.3%. |

## Questions you may get

- **"Isn't this a glorified Excel?"** It doesn't ask for numbers a family can't know. It asks goals and comfort in
  rupees, and gives strategies with what to buy.
- **"Who is it for?"** Working assumption: wealthy families without a family office. The Overview, Risk and Scenarios
  pages are the advanced view for a manager. Say you want his view.
- **"Why not pick stocks?"** On purpose. It stays at the level of index funds, bonds and gold.
- **"Where does the data come from?"** Synthetic today. The plan is NSE Indices, AMFI, RBI and MoSPI. NSE's terms forbid
  scraping, so the plan is manual downloads and a written-consent request.
- **"How do you know it's right?"** 90 automated tests check that every constraint is respected. It's labelled a simulation,
  not advice. A walk-forward backtest is a stretch goal.
- **"Is it dynamic?"** Yes: edit the family profile and every page recalculates.
- **"Why does B miss the 4% goal?"** It's reported honestly rather than forced. C meets it but breaks the comfort limit,
  which is the trade-off the family chooses.
