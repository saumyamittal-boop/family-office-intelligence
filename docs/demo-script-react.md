# Demo script: the React version, in person

> Illustrative simulation, not investment advice. Synthetic data only.

For Saturday 24 Oct 2026, with the mentor at the laptop. About **8 minutes** of demo and 2 minutes of questions for him. Every number below was produced by the
running application and is **checked automatically**: `demo\start-demo.cmd` runs `tools/demo_check.py` against the live app, and `tests/test_demo_script.py` runs the same
check in the test suite, so this page cannot drift from the engine. If you change an assumption, the check fails and tells you which figure moved.

The older three-minute script for the Streamlit version is [demo-script.md](demo-script.md). The numbers are the same; the screens differ.

## Before he arrives (10 minutes, the evening before and again an hour before)

1. **Plug in the laptop**, turn sleep off, close everything else (a busy laptop makes the app and its tests slow). Turn the Wi-Fi off once to prove it does not need it.
2. **Double-click `demo\start-demo.cmd`.** It builds the web app, starts the API and the web server with a **fresh private demo database** (your development database is not touched), runs the figures check, and opens `http://127.0.0.1:5181`.
   It takes about 20 seconds on this laptop. The last lines in the window must say **"41 of 41 figures in docs/demo-script-react.md match the running application."**
   If it says fewer, or prints MISSING, do not quote those figures; read the line, and tell Claude.
3. Press **F11** (full screen) and set the browser zoom to 100% (a little more for a projector). Pick light or dark from the account menu (top right); light reads better in a bright room.
4. **Sign out and stay on the sign-in page.** (Each demo family you open is a private copy, so you can click Save freely, and so can he.)
5. Keep these ready as fallbacks: the Streamlit app (`streamlit run app.py`, `http://localhost:8501`) or its live link on your phone, and a screen recording of one full run.
6. Rehearse the whole script twice with a timer. Stop with `demo\stop-demo.cmd` afterwards.

If the browser says it can't reach the server: run `demo\start-demo.cmd` again (it detects a running demo and just reopens it). Logs are in `%LOCALAPPDATA%\fo-demo`.

## The script

### 0:00 to 0:40. The sign-in page

**Say:** "This is Family Office Intelligence. It is for a wealthy family that has no family office and no fund manager to ask. Everything you will see runs on synthetic data, so read the numbers as a demonstration, not as advice."

Point at the line at the bottom: *Prototype with synthetic data only.* Then click **Legacy-conservative family**.

### 0:40 to 3:00. Story 1: "We have ₹100 Cr and no idea" (Plan my money)

Click **Plan my money**. The six steps are named across the top: *About you, What's coming, Your comfort, Safety net, What you own, Your strategies.*

| Step | Do | Say |
|---|---|---|
| About you | Leave the starting answers: ₹100 Cr of wealth and ₹3 Cr of spending. Click **Continue**. Before you do, change the wealth number and glance at the panel on the right | "I only know roughly what we have and what we spend. It asks for no returns and no volatility. And notice it recalculates as I type." (Put the number back.) |
| What's coming | **Continue** | "A wedding, a property or an education would go here, with a year and an amount. Or an expense of our own." |
| Your comfort | Leave *Balance safety and growth*. **Continue** | "It asks how big a fall we could sit through, in rupees: 15% of ₹100 Cr is ₹15 Cr." |
| Safety net | Leave 12 months. **Continue** | "A year of spending must stay within easy reach. Shares don't count, because they can be down exactly when we need the cash." |
| What you own | **See my strategies** | "A rough picture is enough; it starts from a typical split." |

On the results page, **say:** "Three strategies, and B is recommended for us. In a typical year B ranges from **+3.5% to +16.8%**. The worst year in the history was **−6.8%**. In a severe market crash we would lose **−₹15.5 Cr**. It is expected to return **3.8% after inflation**, and the screen is honest about our 4% goal: *Meets your return goal: Not quite*."

"Strategy A is gentler: its worst year is **−0.1%**. Strategy C expects **9.0%** a year, but its worst year is **−11.8%** and the screen flags it as **Beyond your comfort**. So the trade-off is visible."

The crash is labelled **In a severe market crash**: "a stylised shock, not a replay of any real year", it says so on screen.

Scroll to *What to buy and sell* for Strategy B. **Say:** "These are kinds of product, not stock picks: **Sell ₹15.6 Cr** of the large-cap index fund, **Buy ₹8.4 Cr** of the mid-cap index fund and **Buy ₹14.9 Cr** of a bond fund. The property and business holdings stay as they are."

### 3:00 to 5:00. Story 2: the ₹1,000 Cr family with a liquidity gap

Open the account menu (top right), **Log out**, then click **₹1,000 Cr liquidity-gap example**.

**Say:** "A ₹1,000 Cr family. Most of it is in one share portfolio, and only ₹50 Cr is easy to reach."

The warnings sit above the tiles. Point at the first (marked *Problem*): *Liquidity shortfall. Your current mix counts ₹50 Cr of easily reached assets against ₹120 Cr needed: 0.4x the safety net.* **Say:** "Nobody asked it to look for this." Click **Why?** beside it to open the explanation panel, then close it with Escape.

**Careful:** the dashboard opens on the *Balanced* mix, so its tiles look healthy. Click **Current** under *Mix to show*: **Worst drawdown 28.2%, Above your limit** (the family said 15%), and **Liquidity cover 0.4x**.

Click **Scenarios**, then scroll to *Compare your options under one scenario*. **Equities fall 25%** is already chosen.

**Say:** "If shares fall 25%, the current mix loses **−₹137.5 Cr, −13.8%**, and the safety net is short. The three options lose far less: Growth **−₹63.7 Cr**, Balanced **−₹45.0 Cr**, Defensive **−₹39.7 Cr**, and all three hold the safety net."

Read the red note at the bottom of that box aloud, because it is the app's own wording: *Your current mix would fall short of the safety net after this scenario (0.4x of what you need). Growth, Balanced, Defensive all hold it.*

### 5:00 to 7:30. What is new in this version

**1. The Assistant** (30 seconds). Click **Assistant**, then the chip **Is my liquidity enough?**. **Say:** "It never calculates a number itself and it uses no language model: every figure comes from the model's own results, and you can open the evidence." The answer reads: *Over the next 12 months your planned outflows come to ₹120 Cr. Your liquid assets count for ₹50 Cr, which is 0.4x the amount needed.* Click **Show the evidence**. Then type something it should refuse, such as "which stock should I buy?", to show that it declines and offers what it can do.

**2. Holdings import** (90 seconds). Click **Holdings**. **Say:** "A family's statements arrive as spreadsheets." Choose the file `demo\family-statement.csv` (synthetic, ₹1,000.0 Cr). The screen shows what it read before anything is stored: it reads 7 rows and reports **1 problem to fix**: the label **Equity** is not a class the model knows (large or mid cap?), and it never guesses. Under *Class for Equity* choose **Large-cap equity**, then click **Import 7 holdings**; the line "Imported." appears. The consolidated view shows large-cap at **36.0%** and illiquid at **25.0%** of the **₹1,000.0 Cr**.

Scroll to *Use these holdings in your profile*: the profile's large-cap share would go from **55.0%** to **36.0%**. **Say:** "Nothing changes in the family's profile until I choose it." Click **Use these holdings in my profile** ("Your profile now uses these holdings."), go back to **Overview**, and click **Current**.

**Say:** "The liquidity shortfall is gone: **₹285 Cr** counted against ₹120 Cr needed, **2.4x**. But the worst fall in the history is still **23.7%**, above the limit. It does not hide what is still wrong."

**3. Your own dashboard** (20 seconds). Click **Customise dashboard**: "Pick four of eight modules; it remembers my choice." Close it, and switch the theme from the account menu if you like.

### 7:30 to 8:30. Why you can trust it, and where it stops

**Say:**
- "This web app does no calculations. Every number comes from the same financial engine as the Streamlit version, and tests freeze the engine's output, so no number can change silently. More than 900 Python tests, 548 web tests and 29 browser tests pass."
- "It is an illustrative simulation on synthetic data. The assumptions are my drafts and nobody has validated them independently."
- "It is running on this laptop. The Streamlit version is the one with a public link. Hosting this version is the next step, and I have written the plan."

## What to ask him (write the answers down)

1. **Who is the product for?** The wealthy family with no adviser (the guided plan) or the fund manager who wants a consolidated dashboard (the analyst pages)?
2. **Vercel and Clerk: requirements or suggestions?** See [plan-sharing-and-deployment.md](plan-sharing-and-deployment.md) and [ADR-0022](adr/0022-authentication-own-or-managed.md).
3. **Is there a friendly family-office contact** to test with, and a route to licensed market data?
4. **What does he expect by the end of October:** a link to this version, or the Streamlit link plus a plan?

## If he asks

| Question | Honest answer |
|---|---|
| Is the data real? | No. Synthetic, generated; the averages are set by me. |
| Is it deployed? | The Streamlit version is. This one is only on this laptop; the plan is in `docs/plan-sharing-and-deployment.md`. |
| Is it secure? | It has been hardened and tested by me, with 29 browser tests and a written review. No outsider has reviewed it, and it must not hold real data until the readiness checklist is closed. |
| Is the Assistant AI? | No. It matches your question to one of about twenty reviewed answer types and fills it with the model's figures. It gets 79% of fresh questions right. |
| Why did the first screen show 3.2x cover? | That is the Balanced option. The shortfall is about the current mix: click *Current*. |
| Can I try it? | Yes. Every family is a private copy. Please don't type any real data. |
| Why not Vercel and Clerk now? | Vercel can host the web pages but not this API as it is written; Clerk needs a data-protection decision first. Both are in the plan. |

## After the meeting

Run `demo\stop-demo.cmd`. Write down his answers in [backlog-from-mentor-feedback.md](backlog-from-mentor-feedback.md).
