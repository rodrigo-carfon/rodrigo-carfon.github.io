# Domain primer — reading the numbers behind the dashboard

> A short guide to the domain, from the basics (what ICE is, what a future is) to
> telling a **story** from the real numbers in the dashboard. By the end you won't just
> have a chart — you'll know **what the chart is saying**.

---

## Part 1 — The minimum vocabulary

### What is ICE?
**ICE = Intercontinental Exchange.** It is an **exchange** — one of the large U.S.
exchanges, headquartered in New York, and the owner of the New York Stock Exchange (NYSE).
The key point: **ICE is where the world's coffee and cotton futures are traded.** When
people say "the price of coffee", they almost always mean the price of the **Arabica
coffee future traded on ICE in New York**.

### What is a "future" (futures contract)?
A **contract to buy/sell a fixed quantity of something, at a price agreed today, for
delivery in the future.** Example: a coffee roaster agrees today to buy coffee it will
only receive in December, but **locks in the price** now. Why?

- The **producer** (farmer) wants to secure a price and not depend on where the market is
  at harvest → they **hedge**.
- The **buyer** (industry) wants to be sure it won't overpay if coffee rallies → it also
  hedges.
- And there are **speculators/traders** who buy and sell purely betting on price direction.

A physical-commodity merchant lives in the middle of this: **connecting** these clients to
the market and handling the **physical** commodity (coffee and cotton leaving the farm,
heading to port, being invoiced).

### What does "US¢/lb" mean?
The price is quoted in **U.S. cents per pound** (~0.45 kg). So coffee at **273 ¢/lb** =
**US$ 2.73 per pound**. One ICE coffee contract is **37,500 pounds** → worth ~**US$
102,000** (273 × 375). Cotton: a **50,000-pound** contract. That "value of one contract"
is what the dashboard calls the **notional**.

### The two characters in the story
| | Coffee (Arabica) | Cotton (Cotton No.2) |
|---|---|---|
| Exchange code | **KC** (`KC=F`) | **CT** (`CT=F`) |
| Where | ICE New York | ICE New York |
| Unit | US¢/lb | US¢/lb |
| Contract size | 37,500 lb | 50,000 lb |
| What drives the price | **weather in Brazil** (largest producer), crop, stocks | weather in the U.S., textile demand, China |

---

## Part 2 — The dashboard metrics, in plain terms

### Daily return
How much the price rose or fell from one day to the next, in %. The asset's "heartbeat".

### Volatility (annualized)
**The size of the up-and-down.** Technically it is the standard deviation of daily
returns, scaled to a year. In plain terms: **how much the price tends to swing.** High
volatility = nervous, unpredictable price = **more risk**. It is the #1 market-risk metric.
- In the dashboard this becomes **limit bands**: up to 30% "OK", 30–45% "warning" (WARN),
  above 45% "limit breached" (BREACH).

### Drawdown
**How far the price has fallen from its highest peak.** If it went to 100 and is now 70,
the drawdown is −30%. It answers: *"if I had bought at the top, how much would I be down?"*
The metric of **maximum pain**.

### Correlation (between coffee and cotton)
Measures whether the two **move together**. It ranges from −1 to +1:
- **+1** = they rise and fall in lockstep;
- **0** = one has nothing to do with the other;
- **−1** = when one rises, the other falls.

Why it matters for risk: if you hold both and they **don't move together** (correlation
near 0), your risk is **diversified** — the two rarely collapse on the same day. "Don't put
all your eggs in one basket", with a number on top.

---

## Part 3 — The story the real numbers tell (3 years)

> These come straight from the database (`data/commodities.db`).

### Coffee: a historic rally (the star of the period)
- Started the window (~Jun 2023) near **177 ¢/lb**, dropped to **145** (low, Oct 2023) and
  then **exploded to 439 ¢/lb** (peak on **Feb 13, 2025**). It later traded back near
  ~**274**.
- From low to peak, coffee **nearly tripled** (145 → 439) — one of the largest coffee
  rallies in history.
- **Why?** The market attributed it to **weather problems in producing regions — drought
  and frost in Brazil** (the world's largest producer) and a smaller crop, with **very low
  stocks**. When coffee is scarce and demand persists, the price spikes.
- And it was **nervous**: days of **+7%** and days of **−8%**. Strong rallies, strong
  corrections.

### Cotton: the opposite — sideways and down
- Started around **~81 ¢/lb**, hit **103** (peak, Feb 2024) and **slid to 61** (low, Feb
  2026). It traded back near ~**79** — practically **where it began three years earlier**.
- While coffee went wild, cotton stayed **sleepy and slightly lower** — soft textile demand
  and comfortable supply.

### The contrast that becomes your insight
- **Volatility:** coffee ran at **~32–36% per year**; cotton at **~18–24%**. → **Coffee is
  roughly twice as risky as cotton.** Both show up in "WARN" on the dashboard, but coffee
  lives closer to the limit.
- **Drawdown:** both fell hard from their tops at some point — coffee **−44%**, cotton
  **−41%**. Even a "champion" asset like coffee takes brutal tumbles along the way. Risk
  exists in both.
- **Correlation:** it ran between **0.03 and 0.14** over the 3 years → **basically zero.**
  Coffee and cotton **have little to do with each other** day to day. That makes sense:
  what moves coffee (weather in Brazil) is not what moves cotton (U.S./textile demand).

---

## Part 4 — The "so what?"

Put it together into a risk-minded conclusion:

> **"Over three years, coffee had a historic bull cycle and remains the riskier asset —
> volatility near 35% per year and single-day drops of up to 8%, driven by weather and
> stocks in Brazil. Cotton is the calm side, trading sideways. And because the two barely
> correlate, anyone running both legs has naturally diversified risk. That is why a control
> dashboard needs to look at each commodity with its own risk ruler — which is exactly what
> the volatility bands do."**

A risk-control dashboard exists to give the desk **risk visibility** so it can decide. This
one answers, in seconds, three questions a risk team asks every day:
1. **Where are we now?** (price, day change)
2. **How risky is it?** (volatility vs. limit, drawdown)
3. **Is the risk concentrated?** (correlation between the commodities)

---

## Part 5 — Quick glossary

| Term | In one line |
|---|---|
| **ICE** | The NY exchange where coffee and cotton futures trade. |
| **Future** | A contract to buy/sell in the future at a price locked today. |
| **Hedge** | Using a future to **protect** against price swings. |
| **Physical commodity** | The real goods (bags of coffee, bales of cotton), not just paper. |
| **¢/lb** | U.S. cents per pound (the price unit). |
| **Notional** | The financial value of one contract (price × contract size). |
| **Volatility** | The size of the up-and-down; the main risk measure. |
| **Drawdown** | How far it fell from the top; the "worst pain". |
| **Correlation** | Whether two assets move together (−1 to +1); near 0 = diversified. |
| **Mark-to-market** | Revaluing a position at today's market price. |
| **Basis risk** | The gap between the local physical price and the future used to hedge. |
