# PROJECT EDGE

## EDGE DISCOVERY PROGRAMME — FROM PHENOMENA TO EDGES

**Document type:** Prioritised scientific research roadmap  
**Version:** 1.0  
**Date:** 4 August 2026  
**Active working directory:** `D:\codex\equity_quant_research_platform`  
**Authorised market-data source:** Market Data Manager (MDM) only  
**Status:** Decision document; not an empirical result and not an edge claim

---

## 1. Executive decision

Project EDGE should maintain a queue of only five candidate research families and investigate them sequentially. The recommended order is:

1. **Regular-session price-discovery persistence or reversal**
2. **Abnormal-volume and participation shocks**
3. **OHLCV liquidity shocks and temporary price pressure**
4. **Cross-sectional regular-session relative strength**
5. **Raw-market breadth and participation state**

Rank 5 is conditional on a result-blind MDM membership preflight. If the observable's sign can be determined by changing raw-census composition or a small instrument subset, breadth becomes `BLOCKED` and is removed rather than redefined.

The single first family remains regular-session price-discovery persistence or reversal. Its first bounded question is whether a security's session `t` open-to-close log return predicts its next-observed-session open-to-close log return after removing retained exact-case ticker-by-era and formation-date effects.

This family ranks first because it combines:

- a credible information-underreaction mechanism;
- a competing liquidity-pressure mechanism that predicts the opposite sign;
- an observable future return component;
- one continuous, two-sided and highly falsifiable question;
- current MDM compatibility without a new data source;
- low enabling cost; and
- a valuable conclusion under continuation, reversal or a precise negligible result.

Recent primary research reports that past intraday returns contain momentum while past overnight returns do not, and interprets the evidence as consistent with underreaction to information revealed through trading. That is an external prior, not Project EDGE evidence. It strengthens the rationale for asking the question; it does not predetermine the answer. See [Barardehi, Bogousslavsky and Muravyev (2026)](https://academic.oup.com/rfs/advance-article-abstract/doi/10.1093/rfs/hhag036/8626980).

No candidate in this roadmap is currently an edge-qualified phenomenon. The top five are a **sequential falsification queue**, not a portfolio of approved signals. Project EDGE should run one bounded family at a time. If a family fails its frozen materiality, inferability or artefact gates, its tested ancestry should be eliminated before the next family starts. If it survives, effort should remain concentrated on its independent reproduction and qualification rather than immediately opening four more search programmes.

The tested opening-gap ancestry remains closed. The daily observed-range recurrence family retains its frozen `PAUSE` state but receives no rescue experiment or active research allocation. Neither result is reinterpreted by this roadmap.

---

## 2. Scope and non-claims

This document surveys thirty broad equity edge families. It is intended to cover the principal price, volume, liquidity, event, cross-sectional, accounting, flow and market-structure mechanisms that could plausibly create a persistent equity-market advantage. It is a decision-oriented survey, not an assertion that every published anomaly or every possible equity phenomenon has been enumerated.

The roadmap does not:

- implement a trading strategy;
- construct a portfolio;
- optimise a threshold, parameter, horizon or feature combination;
- perform profitability testing;
- authorise live or simulated execution;
- treat a published result as Project EDGE evidence;
- reopen an eliminated Project EDGE branch;
- treat a physically present MDM file as scientifically admissible without checking its timing and revision semantics; or
- modify the frozen Foundation, Milestone 1 or Milestone 2 documents.

The phrase **edge probability** means the comparative prior probability that a broad family contains at least one persistent, observable and economically material predictive phenomenon that could later survive edge qualification. It is not the probability that a strategy will be profitable.

---

## 3. Decision method

### 3.1 Ranking objective

The ranking maximises expected scientific learning about realistic edge mechanisms under today's MDM constraints. It does not rank families by fame, published t-statistics or the largest historical paper return.

Each family is assessed on six required dimensions:

1. economic rationale;
2. behavioural or institutional rationale;
3. implementability using current MDM;
4. Expected Scientific Information Gain (ESIG);
5. comparative probability of containing a persistent exploitable phenomenon; and
6. expected research cost.

The ordering also gives priority to a family whose first experiment can permanently close a large branch without parameter search.

### 3.2 External evidence is a prior only

The published anomaly literature warrants substantial scepticism. McLean and Pontiff found that published predictors weakened out of sample and weakened further after publication. Hou, Xue and Zhang found that most of hundreds of anomaly variables failed common replication standards after mitigating microcap influence and applying stronger test hurdles. Harvey, Liu and Zhu show why a large search universe requires a materially higher evidential hurdle. These findings justify a low base rate and a default decision of elimination, even for famous anomalies. See [McLean and Pontiff (2016)](https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12365), [Hou, Xue and Zhang (2020)](https://academic.oup.com/rfs/article/33/5/2019/5236964) and [Harvey, Liu and Zhu (2016)](https://academic.oup.com/rfs/article-abstract/29/1/5/1843824).

### 3.3 MDM implementability states

| State | Meaning |
|---|---|
| **NOW** | A bounded first experiment can be executed scientifically with current MDM and explicit scope limits. |
| **BOUNDED** | A meaningful partial question can be asked, but the result cannot support the full conventional family claim. |
| **BLOCKED** | A current MDM defect or absence can materially reverse the conclusion; the family must not be tested until that exact defect is resolved. |
| **PAUSED** | Data may be technically sufficient, but current Project EDGE evidence or governance does not justify further work. |
| **CLOSED** | The tested Project EDGE ancestry is eliminated; no descendant search is authorised. |

### 3.4 ESIG scale

| ESIG | Meaning |
|---|---|
| **Very high** | One bounded test can decide between major mechanisms or close a large, important branch. |
| **High** | Both positive and negative outcomes materially change programme knowledge. |
| **Medium** | Useful knowledge is likely, but the family overlaps others, has weak effective sample size or leaves substantial ambiguity. |
| **Low** | The likely result is incremental, highly conditional or difficult to interpret. |
| **None now** | Current programme state or data prevents decision-bearing learning. |

### 3.5 Edge-probability scale

| Prior | Meaning |
|---|---|
| **Medium-high** | Strong mechanism and comparatively durable external evidence, but no Project EDGE confirmation. |
| **Medium** | Credible mechanism and evidence, with important crowding, cost or measurement risk. |
| **Medium-low** | Plausible, but evidence is fragile, indirect or implementation-sensitive. |
| **Low** | Weak direct path to a durable edge or severe data-mining/cost risk. |
| **Unresolved** | Existing Project EDGE evidence is inconclusive and no active budget is justified. |
| **Reduced in tested ancestry** | Project EDGE evidence has lowered the prior for the exact tested branch. |

No numerical posterior is reported. Project EDGE has not generated enough independent evidence to support calibrated numerical probabilities across these families.

### 3.6 Research-cost scale

Cost includes scientific specification, feature validation, data admissibility work, computation, review and result deposition.

| Cost | Planning interpretation |
|---|---|
| **Low** | Approximately two to five research days; one or a small number of deterministic daily-data passes. |
| **Moderate** | Approximately one to three research weeks; additional validation, sensitivity or a larger data pass is required. |
| **High** | Approximately one to two research months; substantial MDM repair, event validation or specialised inference is required. |
| **Very high** | A missing data family, historical reconstruction or specialised market-data capability must first be created and validated by MDM. |

These are family-level planning bands, not preregistered experiment cost estimates. Every authorised experiment still requires its own frozen CPU, memory, storage, runtime, data-volume and statistical-complexity estimate.

---

## 4. Current MDM scientific capability

### 4.1 Capabilities usable now

The authoritative raw daily US aggregate archive currently contains 4,843 session files covering `2007-05-01` through `2026-07-30`. Its daily rows contain ticker, open, high, low, close, volume, transaction count and timestamp. Existing Project EDGE source audits recorded 42,302,420 rows for this archive and found no duplicate exact-case ticker-date key, blank ticker or incoherent OHLC row in the audited source.

This supports bounded studies based on:

- same-row `ln(close/open)`;
- same-row `ln(high/low)`;
- raw volume, dollar volume and transaction counts;
- exact-case ticker adjacency;
- contemporaneous raw-census cross-sections; and
- full-market minute aggregates from `2016-07-25` onward when a minute study is independently justified.

Same-row price ratios are invariant to a coherent multiplicative adjustment of all prices in that row. That makes them materially safer than unadjusted cross-session price-level returns, although bad bars, missing observations, identity drift and mixed instruments remain possible.

MDM also contains split execution records from 2007 onward. They require deterministic deduplication and do not provide dividend, merger, spin-off or terminal-return economics.

### 4.2 Limitations that bound, but do not automatically invalidate, the top five

The raw daily census:

- mixes ordinary shares, ETFs, ADRs and other instruments;
- uses ticker strings rather than a complete permanent security identity;
- lacks full dividend and terminal-return economics;
- does not provide complete historical sector, industry or index membership;
- lacks broad bid-ask spreads, order direction and auction imbalance;
- lacks complete point-in-time shares and market capitalisation over the full daily history; and
- is not identified by the MDM Git commit because the data payload is ignored by Git.

Every experiment must therefore bind the exact MDM file inventory and content hashes. Initial conclusions must be stated about the exact admitted MDM population, not silently generalised to all US common equities.

### 4.3 Physically present event data that are not currently return-join admissible

MDM contains substantial Benzinga archives for `2018-2025`, including:

- 157,656 normalised earnings rows, of which 116,159 contain both actual and estimated EPS;
- 364,669 analyst-rating rows;
- 80,575 corporate-guidance rows; and
- 1,642,128 news rows.

Physical presence does not make these files safe for event-return research:

- structured-event publication timestamps are stored at midnight rather than at a validated release time;
- most event and news records have later update timestamps without complete historical revision vintages;
- every normalised analyst action is currently `mixed_or_unknown`;
- every normalised guidance direction is currently `mixed`;
- prior price targets and prior guidance fields are incomplete; and
- the canonical catalyst manifest explicitly states `future_joins_permitted: false`.

Accordingly, post-earnings, news, analyst and guidance return studies are scientifically **BLOCKED today**. This is not perfectionism: event time and vintage determine which price outcome is genuinely future. Using those records before MDM admits the join could fundamentally reverse the conclusion.

### 4.4 Missing or unusable specialised data

Current MDM does not provide a research-admissible general history for:

- sector or industry classification;
- index membership and weights;
- consensus-estimate vintages;
- complete financial statements and revisions;
- institutional holdings or ownership breadth;
- short interest, borrow availability or borrow fees;
- options chains, implied volatility or dealer positioning;
- ETF or mutual-fund flows;
- complete IPO and listing-event history;
- complete repurchase, issuance, dividend, insider or merger-event history; or
- broad auction order imbalance and order-book history.

Price or volume proxies must not be relabelled as these unavailable mechanisms. In particular, abnormal volume may be called participation; it may not be called institutional accumulation without holdings or trader-type evidence.

---

## 5. Ranked equity edge-family landscape

The table ranks current programme priority, not historical fame. A high conditional literature prior cannot compensate for a scientifically blocked MDM question.

| Rank | Candidate family | Economic rationale | Behavioural or institutional rationale | MDM today | ESIG | Edge prior | Cost | Current disposition |
|---:|---|---|---|---|---|---|---|---|
| 1 | Regular-session price-discovery persistence or reversal | Information revealed through trading may be incorporated gradually; temporary inventory pressure predicts the opposite, a reversal. | Underreaction, disposition behaviour and slow learning compete with salience-driven overreaction. | **NOW** — same-row open-to-close returns and next-session same-row outcomes. | **Very high** | Medium | Low–moderate | **Top five; run first** |
| 2 | Abnormal-volume and participation shocks | Informed order splitting or persistent demand can continue; liquidity or attention shocks can exhaust and reverse. | Limited attention, disagreement and herding create abnormal participation without requiring a price-only story. | **BOUNDED** — raw volume and transactions exist, but their feature definitions must first pass Stage 2.5 validation; no trader identity or float. | **High** | Medium | Moderate | **Top five; second** |
| 3 | OHLCV liquidity shocks and temporary price pressure | Immediacy demand and intermediary inventory constraints can dislocate price; normalisation can reverse it. | Forced trading and attention can amplify temporary deviations from value. | **BOUNDED** — daily price-impact proxies only; no broad spreads, quotes or signed order flow. | **High** | Medium | Moderate | **Top five; third** |
| 4 | Cross-sectional regular-session relative strength | Information diffusion and slow capital reallocation can make leaders persist relative to laggards. | Disposition effects, anchoring and institutional herding can delay adjustment. | **BOUNDED** — regular-session components are measurable; full total-return momentum is not yet reliable. | **High** | Medium-high | Moderate–high | **Top five; fourth** |
| 5 | Raw-market breadth and participation state | Distributed demand may be more persistent than narrow, concentrated leadership; narrow breadth may reveal fragile risk-bearing. | Herding and crowded attention can separate broad conviction from index-level appearance. | **BOUNDED only after a membership preflight** — raw-census breadth, not certified ordinary-equity or index breadth. | **High** | Medium-low | Low–moderate | **Top five; fifth, conditionally** |
| 6 | Intraday time-of-day continuation or reversal | Institutional execution schedules and recurring liquidity supply can create predictable within-session propagation. | Habitual order timing and delayed reaction may repeat by clock time. | **NOW**, but minute aggregates are not auction prints or an order book. | High | Medium | High | Hold until the daily top-five queue is resolved |
| 7 | Extreme daily-move mean reversion | Forced liquidation and temporary imbalance may move price away from value. | Salience and overreaction can exaggerate extreme moves. | **NOW**, but an extreme threshold creates avoidable search freedom and overlaps rank 1. | Medium-high | Medium | Moderate | Do not open while rank 1 tests both signs continuously |
| 8 | Low-beta, low-volatility and downside-risk effects | Leverage constraints and benchmark mandates can create excess demand for high-beta securities. | Lottery preference and preference for positively skewed payoffs can overprice volatile stocks. | **BOUNDED** — mixed instruments, incomplete market cap and no full total-return history. | Medium | Medium | Moderate–high | Hold |
| 9 | Cross-sectional dispersion and correlation stress | Constrained risk-bearing, deleveraging or disagreement may cause convergence or further stress after unusually dispersed markets. | Crowding and divergent beliefs can create state-dependent behaviour. | **BOUNDED** — exact raw census; few independent market-level dates. | Medium | Medium-low | Moderate | Hold |
| 10 | Calendar and institutional-flow seasonality | Tax, payroll, reporting and benchmark cycles can create recurring demand. | Habitual timing and salience may reinforce calendar effects. | **NOW** for raw-session outcomes. | Medium | Medium-low | Low | Hold; high data-mining risk |
| 11 | 52-week-high and reference-price anchoring | Prices near salient reference points may respond slowly to new information. | Anchoring on a prior high can delay belief revision. | **BOUNDED** — reference prices are vulnerable to incomplete action and identity history. | Medium | Medium | Moderate | Hold behind cleaner families |
| 12 | Medium-horizon own-security trend persistence or breakout | Slow capital deployment and persistent information can sustain an absolute trend. | Extrapolation and feedback trading may reinforce it until correction. | **BOUNDED** — cross-session total-return and identity limitations; overlaps rank 4. | Medium | Medium | Moderate–high | Hold |
| 13 | Post-earnings-announcement behaviour | Earnings convey persistent cash-flow information that may take time to enter price. | Investors and analysts may underreact to the persistence of surprise. | **BLOCKED** — event time, revision vintage and explicit future-join prohibition. | High if unblocked | Medium-high | High | Reserve; do not run now |
| 14 | Earnings surprise and consensus-revision momentum | Changes in expected earnings alter fundamental value and may diffuse over several revisions. | Anchoring and slow analyst revision can delay consensus. | **BLOCKED** — no point-in-time consensus-estimate history; event timing unresolved. | High if unblocked | Medium-high | Very high | Reserve |
| 15 | Analyst recommendation, target and guidance changes | Analysts or management can reveal information not yet reflected in price. | Herding, anchoring and staged interpretation can create drift. | **BLOCKED** — unusable direction fields, date-only timestamps and incomplete priors. | High if unblocked | Medium | High | Reserve |
| 16 | News attention, sentiment and catalyst underreaction | Public information affects expected cash flows and risk, but incorporation may be delayed. | Limited attention, negativity bias and retail salience can cause continuation or reversal. | **BLOCKED** for return joins — updated content lacks complete original vintages; canonical joins prohibited. | High if unblocked | Medium | High | Reserve |
| 17 | Sector and industry leadership or rotation | Common shocks and reallocations can propagate through economically related firms. | Category-level attention and institutional herding can delay firm-level adjustment. | **BLOCKED** — no general PIT sector or industry history. | High if unblocked | Medium-high | High | Reserve |
| 18 | Customer, supplier and economically linked peer spillovers | News to one firm changes the outlook for connected firms. | Attention constraints can delay cross-firm information transfer. | **BLOCKED** — no PIT economic-link graph. | High if unblocked | Medium | Very high | Defer |
| 19 | Quality and profitability | Durable profitability and balance-sheet strength may be insufficiently priced or reflect a risk premium. | Investors may overpay for exciting growth and neglect steady compounders. | **BLOCKED** — no PIT financial-statement and revision history. | High if unblocked | Medium-high | Very high | Defer |
| 20 | Value and valuation spreads | Cheap securities may compensate for distress risk or be undervalued after excessive pessimism. | Extrapolation of glamour growth and neglect of unpopular firms can create mispricing. | **BLOCKED** — no historical PIT accounting values and full market cap. | Medium-high if unblocked | Medium | Very high | Defer |
| 21 | Investment, asset growth, accruals and cash-flow quality | Aggressive investment or low-quality accruals may imply lower future cash-flow persistence. | Empire building and investor fixation on headline earnings can delay recognition. | **BLOCKED** — no PIT accounts or revision history. | Medium if unblocked | Medium | Very high | Defer |
| 22 | Institutional ownership breadth, accumulation and herding | Large owners split orders and ownership changes can create inelastic demand. | Professional herding and delegated incentives can sustain flows. | **BLOCKED** for the institutional claim — volume alone is not ownership. | High if unblocked | Medium | Very high | Defer |
| 23 | Fund and ETF flows, fire sales and forced demand | Subscriptions, redemptions and leverage constraints force price-insensitive trades. | Performance chasing can make flows persistent and later reversible. | **BLOCKED** — no point-in-time fund flows, AUM or holdings. | High if unblocked | Medium-high | Very high | Defer |
| 24 | Index inclusion, deletion and reconstitution pressure | Passive and benchmarked capital must trade around membership changes. | Anticipatory crowding may move prices before effective dates. | **BLOCKED** — no index announcement or membership history. | Medium-high if unblocked | Medium | High | Defer |
| 25 | IPO and new-listing lifecycle | Initial price discovery, restricted float and lockups may cause distinctive behaviour. | Optimism and attention can overvalue difficult-to-price young firms. | **BLOCKED** — first observed bar cannot distinguish an IPO, relisting, ticker change or data start. | Medium | Medium | High | Defer |
| 26 | Issuance, repurchase, dividend and insider-information events | Capital supply, managerial timing and signalling can affect later valuation. | Investors may underreact to informed corporate actions; insider sales have competing motives. | **BLOCKED** — only split execution history is sufficiently present. | Medium | Medium | Very high | Defer |
| 27 | Short interest, borrow constraints and crowded shorts | Limits to arbitrage and forced covering can cause asymmetric price dynamics. | Disagreement and overvaluation can persist when pessimists cannot trade. | **BLOCKED** — no short-interest, availability, utilisation or fee history. | High if unblocked | Medium-high | Very high | Defer |
| 28 | Options-implied information and dealer hedging | Informed option trading and mechanical delta hedging can lead the underlying equity. | Lottery demand and attention can distort option-implied signals. | **BLOCKED** — no options chains, implied volatility, volume or open interest. | High if unblocked | Medium | Very high | Defer |
| 29 | Volatility contraction, expansion and range recurrence | Uncertainty and intermediary risk capacity persist, so volatility clusters. | Attention and fear can amplify volatility states, but volatility predictability is not inherently directional. | **PAUSED** — technically observable; existing range result failed inferability and concentration gates. | None now | Medium-low externally; unresolved in Project EDGE | Moderate if legitimately reopened; zero allocated now | Preserve pause; no rescue |
| 30 | Opening-auction imbalance and opening-gap behaviour | Overnight information and opening liquidity can cause price discovery or temporary pressure. | Delayed reaction or overreaction may follow salient overnight news. | **CLOSED/BLOCKED** — tested gap ancestry is closed; MDM lacks official auction imbalance and executable auction liquidity. | None now | Medium for an independent auction mechanism; reduced in the tested gap ancestry | Very high for auction data; zero allocated now | Do not reopen |

---

## 6. The five recommended families

### 6.1 Rank 1 — Regular-session price-discovery persistence or reversal

#### Scientific premise

Trading reveals information but may not incorporate it immediately. If learning and capital deployment are gradual, a positive regular-session return should predict a same-direction future regular-session return. If the original move is predominantly temporary inventory or liquidity pressure, it should predict reversal.

Both mechanisms are economically plausible and make opposing predictions. Llorente, Michaely, Saar and Wang develop this distinction between information-driven continuation and risk-sharing reversal in the return-volume relation. See [Llorente et al. (2002)](https://web.mit.edu/wangj/Public/Publication/Llorente-Michaely-Saar-Wang02.pdf).

#### First bounded question

> Within one frozen raw MDM ticker-date census, does `ln(close/open)` on session `t` predict the same exact-case ticker's `ln(close/open)` on its next observed MDM session after retained exact-case ticker-by-era effects and formation-date effects?

This is one continuous slope and one horizon. It requires no winner/loser threshold, no parameter grid and no strategy construction.

#### Uncertainty eliminated

- A stable positive relationship supports continued investigation of gradual regular-session price discovery.
- A stable negative relationship supports continued investigation of temporary price pressure and reversal.
- A precise economically negligible relationship eliminates the exact one-session, unconditional, linear raw-MDM-census branch.
- Failed inferability identifies a concrete measurement blocker and authorises no threshold or subgroup rescue.

#### MDM effect

The feature and outcome are both same-row price ratios, substantially reducing coherent split and dividend contamination. Mixed instruments, ticker identity and missing outcomes bound the population claim but do not invalidate the exact raw-census Level-1 question if influence and missingness gates pass.

All current MDM dates are already exposed to exploratory work. A surviving result cannot satisfy independent temporal reproduction until new, untouched MDM outcomes accrue after the specification is frozen.

#### Why it ranks ahead of every alternative

No other family combines an equally direct future-return observable, two competing mechanisms, a single no-threshold test, low cost and immediate MDM admissibility. Rank 2 has a richer participation observable but needs a baseline definition and stronger action/coverage controls. Ranks 3–5 have noisier proxies or weaker population identification. Event and fundamental families are blocked.

### 6.2 Rank 2 — Abnormal-volume and participation shocks

#### Scientific premise

Abnormal trading activity can distinguish persistent information demand from temporary attention or liquidity demand. Informed investors and large institutions often split orders; their activity can sustain a move. Conversely, a salient volume burst driven by disagreement, forced trading or retail attention can mark exhaustion.

Primary evidence links past volume to the magnitude and persistence of momentum, while dynamic volume-return theory predicts continuation for information-motivated trades and reversal for risk-sharing trades. See [Lee and Swaminathan (2000)](https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00280) and [Llorente et al. (2002)](https://web.mit.edu/wangj/Public/Publication/Llorente-Michaely-Saar-Wang02.pdf).

#### First bounded question

Use one preregistered continuous own-history participation deviation—preferably a split-resistant dollar-volume measure—with transaction-count deviation as a measurement check, not as a searched feature combination. Ask whether the relationship between the current regular-session return and the next regular-session return changes continuously with abnormal participation.

The question is **participation-conditioned continuation versus exhaustion**. It is not institutional accumulation, because MDM cannot identify owner or trader type.

#### Uncertainty eliminated

- A stable interaction of the predicted sign shows that participation contains incremental information about continuation or reversal.
- A precise negligible interaction rejects daily MDM participation as a useful discriminator within the frozen scope.
- A disagreement between dollar volume and transaction count identifies a measurement problem rather than authorising a favourable choice after outcomes.

#### MDM effect

Raw daily volume and transaction count are physically sufficient for a bounded census study, but this family is not yet experiment-ready. Its continuous feature definition must first pass Stage 2.5 validation covering deterministic reproduction, zero-volume observations, fractional volume, missingness, split behaviour, numerical stability, source-version consistency and lineage. The rules must be frozen without reference to future returns. A validation failure blocks the family; it does not authorise a favourable cleaning rule.

Shares outstanding, float, venue coverage and order direction are absent. Corporate actions can change share volume, so dollar volume and split-event controls are scientifically important.

#### Why it ranks second

It has a stronger observable connection to information flow and trading demand than most price-only anomalies and can become executable with current MDM after Stage 2.5 validation. It trails rank 1 because defining abnormal participation adds one baseline dependency and because MDM cannot distinguish informed, institutional, retail or liquidity trading.

### 6.3 Rank 3 — OHLCV liquidity shocks and temporary price pressure

#### Scientific premise

Investors who demand immediacy may temporarily move price away from value. Liquidity suppliers require compensation for absorbing inventory, so a sufficiently exogenous price-pressure shock may reverse as inventories normalise. Expected illiquidity can also command a persistent return premium.

Amihud's daily absolute-return-to-dollar-volume measure was designed as a coarse price-impact proxy when richer microstructure data are unavailable. The original study finds both cross-sectional and time-series relationships between illiquidity and returns. See [Amihud (2002)](https://www.sciencedirect.com/science/article/pii/S1386418101000246).

#### First bounded question

Ask whether a continuous, own-history shock in observed price movement per unit of dollar volume or transaction count predicts next-session regular-session reversal after common-date effects. Use one primary proxy and one preregistered measurement falsifier. Do not search among many liquidity formulas.

#### Uncertainty eliminated

- A stable reversal supports temporary price pressure as a candidate mechanism.
- A stable continuation contradicts the simplest inventory-normalisation account and points toward information content.
- A precise null eliminates the selected daily OHLCV proxy as a useful edge observable, although it cannot eliminate true spread- or order-book-based liquidity effects.

#### MDM effect

This family is scientifically bounded rather than structurally identified. MDM lacks broad spreads, quotes, signed order flow and order-book depth. The claim must remain about an OHLCV price-impact proxy. That limitation reduces ESIG relative to ranks 1 and 2 but does not invalidate the proxy question.

#### Why it ranks third

The underlying economic mechanism is recurring and directly relevant to implementation friction. The first question is feasible now and can reject weak daily proxies cheaply. It ranks below abnormal participation because a null may reflect proxy noise rather than absence of liquidity effects, and it ranks above relative strength because it needs less cross-session identity and return reconstruction.

### 6.4 Rank 4 — Cross-sectional regular-session relative strength

#### Scientific premise

Firm-specific information may diffuse gradually, and institutions may reallocate capital slowly across securities. Past leaders may therefore continue to lead. Behavioural accounts add the disposition effect, anchoring and herding.

Cross-sectional momentum is one of the most documented equity regularities. See [Jegadeesh and Titman (1993)](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1993.tb04702.x). Recent evidence separating intraday from overnight components is particularly relevant to what current MDM can observe safely. See [Barardehi, Bogousslavsky and Muravyev (2026)](https://academic.oup.com/rfs/advance-article-abstract/doi/10.1093/rfs/hhag036/8626980).

#### First bounded question

At one externally justified, preregistered formation horizon, ask whether the continuously accumulated regular-session return component predicts a future regular-session return component cross-sectionally. Do not test a horizon grid, winner/loser breakpoints or signal combinations.

This is not a full replication of conventional total-return momentum. It deliberately asks the narrower component that current MDM can measure with lower corporate-action risk.

#### Uncertainty eliminated

- A stable relationship would show that relative leadership survives within regular-session price discovery.
- A precise null would close that bounded component, not the full total-return momentum literature.
- Material concentration in unstable tickers or non-equity instruments would prevent an ordinary-equity conclusion and would not authorise retrospective population selection.

#### MDM effect

The major limitation is that full medium-horizon total returns require distributions, corporate-action completeness and stable identities. Accumulating same-row regular-session returns avoids much of that problem but changes the estimand. The current monthly PIT layer does not cover the full 2007–2026 history with a complete certified common-equity universe.

#### Why it ranks fourth

Its external prior and edge relevance are stronger than breadth, calendar, anchoring or volatility families. It trails ranks 1–3 because it has a longer feedback loop, higher overlap with published and crowded research, and a materially bounded MDM estimand.

### 6.5 Rank 5 — Raw-market breadth and participation state

#### Scientific premise

An index-level move supported by many securities may reflect distributed information and capital demand, while a move led by a narrow subset may be fragile, crowded or driven by a few large instruments. Breadth can therefore describe the cross-sectional structure behind an aggregate move.

#### First bounded question

Using one continuous participation measure derived from the exact contemporaneous MDM census, ask whether breadth contains next-session information beyond the common formation-date return. Avoid multiple breadth definitions, thresholds and regime partitions.

#### Uncertainty eliminated

- A stable effect would show that the distribution of participation contains information not captured by the common move alone.
- A precise negligible result would close the selected raw-census breadth branch before sector or indicator proliferation.
- A result dominated by ETFs, unstable membership or a small number of dates would show that current MDM breadth is not an ordinary-equity market observable.

#### MDM effect

Breadth is derivable, but its scientific population is the exact raw MDM census. Before this family can execute, a result-blind membership preflight must freeze:

- membership as every row actually available at the formation cutoff in the bound raw session file;
- only feature-independent bar-validity exclusions fixed before outcomes;
- the exact source inventory and content hashes;
- denominator, missing-row and next-session attrition accounting;
- session-by-session constituent-count and composition-change diagnostics; and
- a decision rule that classifies the family `BLOCKED` if changing census composition or a small identifiable instrument subset can determine the exposure's sign.

No security may enter because it survives to a later date, and no present-day classification may be projected backward. If this preflight passes, the result can describe only the frozen operational MDM census. It cannot be called NYSE breadth, S&P 500 breadth or US common-equity breadth. If the preflight fails, rank 5 drops from the executable queue; Project EDGE must not search for a better-looking universe.

#### Why it ranks fifth

Breadth makes cross-sectional information first-class, is inexpensive and can close a large family of popular indicators with one disciplined test. It trails relative strength because it has fewer independent market-level dates, weaker direct security-level identification and greater population-definition risk. It nevertheless ranks ahead of the blocked event, sector, fundamental and specialised-data families because it can produce valid bounded knowledge now.

---

## 7. Why the remaining families are not in the top five

### 7.1 Ranks 6–12: observable but lower-value now

These families can often be measured, but they do not deserve current research capital ahead of the top five:

- intraday time-of-day research is costlier, has a larger clock-time search surface and relies on aggregate bars rather than auction or order-book data;
- extreme-move reversal is largely a thresholded descendant of rank 1 and would introduce avoidable selection freedom;
- low-volatility research needs better ordinary-equity, market-cap, beta and total-return representation;
- dispersion and breadth share a limited number of independent market dates;
- calendar effects have a high data-mining prior and often small friction-sensitive magnitudes;
- 52-week-high anchoring depends on cross-session reference-price correctness and overlaps momentum; and
- trend persistence overlaps relative strength while relying more heavily on cross-session histories.

### 7.2 Ranks 13–28: plausible mechanisms, scientifically blocked today

Several blocked families may have higher external priors than raw breadth. They are not current recommendations because the missing MDM capability is decision-changing, not cosmetic.

Post-earnings drift is the clearest example. Bernard and Thomas provide influential evidence of delayed response to earnings information. See [Bernard and Thomas (1989)](https://www.jstor.org/stable/2491062). However, an event study cannot determine what return is future without a trustworthy event time and data vintage. Current MDM explicitly prohibits the canonical future join. Project EDGE should preserve this family in reserve, not manufacture a result from date-only or revised records.

The same principle applies to:

- analyst estimates and recommendations;
- news text and catalysts;
- sector and industry leadership;
- value, quality, investment and accruals;
- institutional ownership and fund flows;
- index reconstitution;
- IPOs and corporate actions;
- short interest and borrow; and
- options and dealer hedging.

If MDM independently releases a validated, point-in-time and join-admissible version of one of these datasets, the programme should rerank the affected family. Project EDGE should not build a one-off substitute or use another source.

### 7.3 Ranks 29–30: preserve existing decisions

Volatility contraction and range recurrence are not promoted merely because range is measurable. The existing range result did not pass its inferability, influence-concentration and missingness gates and is not a signed-return edge result.

Opening-gap research remains closed within the tested ancestry. A future official-auction hypothesis supported by genuinely new imbalance and executable-liquidity data would be a different scientific family. Current MDM does not contain those data, so no reopening is justified.

---

## 8. Sequential research roadmap

### 8.1 Programme rule

Only one unqualified family should be active at a time.

For each family:

1. freeze one precise mechanism-bearing question;
2. use one continuous primary exposure and one horizon;
3. identify the exact MDM limitations and whether they invalidate or merely bound the question;
4. execute one decisive screen;
5. classify the branch as eliminate, pause for a named material blocker, or continue to independent qualification;
6. preserve the negative result; and
7. open the next family only when the current decision is complete or the current family has entered a genuinely independent reproduction wait.

### 8.2 Queue

| Queue position | Family | Earliest action | Terminal value of a negative result |
|---:|---|---|---|
| 1 | Regular-session price-discovery persistence or reversal | Execute the already identified one-session continuous screen | Closes the exact one-session unconditional linear continuation/reversal branch |
| 2 | Abnormal-volume and participation shocks | Complete Stage 2.5 volume-feature validation, then freeze only after queue position 1 closes or enters independent-outcome waiting | Rejects daily MDM participation as an incremental continuation/exhaustion discriminator |
| 3 | OHLCV liquidity shocks | Proceed only after one primary proxy and falsifier are fixed | Rejects the selected daily proxy without overclaiming about true spread/order-book liquidity |
| 4 | Regular-session relative strength | Use one external, preregistered formation horizon | Closes the regular-session component at that horizon, not conventional total-return momentum |
| 5 | Raw-market breadth | Pass the frozen contemporaneous-membership preflight, then use one exact-census participation definition | Closes a broad class of raw-census breadth claims before indicator proliferation |

### 8.3 Promotion discipline

A positive first screen is not a success condition. Promotion requires, at minimum:

- a preregistered economically material gross-return contrast;
- stable direction through independently defined periods;
- dependence-aware precision;
- distributed support rather than dominance by a ticker, date block or instrument class;
- deterministic reproduction;
- resistance to obvious measurement artefacts;
- a plausible path through realistic friction; and
- genuinely new temporal evidence before a persistent-edge claim.

The roadmap does not choose friction thresholds, construct a tradable portfolio or test net profitability. Those activities remain outside the present task.

---

## 9. Principal scientific risks

### 9.1 Publication and crowding risk

The best-known families have been researched and traded for decades. A strong historical literature can increase mechanism credibility while decreasing the probability that a present-day effect remains exploitable. Literature rank and Project EDGE rank must remain separate.

### 9.2 Population risk

The full daily MDM census is not a certified common-equity universe. A raw-census result may be real but driven by ETFs, ADRs, warrants or unstable tickers. Project EDGE must not use current classifications retrospectively to improve a disappointing result.

### 9.3 Identity and lifecycle risk

Exact-case ticker continuity is an operational proxy, not permanent identity. Long horizons create more opportunity for ticker reuse, corporate events, relisting and terminal-outcome loss. This is why short same-row questions rank ahead of long-history families.

### 9.4 Return-component risk

Open-to-close returns deliberately omit overnight return. They are scientifically useful and action-resistant, but they cannot establish a full close-to-close or total-return effect. Every conclusion must name the regular-session estimand.

### 9.5 Effective-sample-size risk

Millions of security-day rows do not create millions of independent market states. Common dates, overlapping horizons and security persistence require dependence-aware inference. Breadth and dispersion are especially constrained by the number of independent dates.

### 9.6 Friction and capacity risk

Price, volume and transaction data can support a preliminary economic-magnitude test but not a complete implementation-cost claim. Sparse targeted quote coverage is not a broad historical spread dataset. No family can become edge-qualified merely because its gross relationship is statistically nonzero.

### 9.7 Exposed-history risk

The historical daily MDM archive has already been used for exploratory Project EDGE work. A new family can still be falsified on that archive, but persistence cannot be established from repeated reuse. Qualification ultimately requires untouched future observations or another genuinely independent dataset admitted through MDM.

### 9.8 Family-overlap risk

Return persistence, volume conditioning, liquidity reversal, relative strength and breadth are related. Treating minor transformations as new families would recreate multiple testing under different names. Dependency and search-exposure records must preserve shared ancestry.

---

## 10. Evidence anchors for the landscape survey

The following primary studies provide representative external priors. They do not validate any Project EDGE family:

- Intraday versus overnight momentum: [Barardehi, Bogousslavsky and Muravyev (2026)](https://academic.oup.com/rfs/advance-article-abstract/doi/10.1093/rfs/hhag036/8626980)
- Cross-sectional momentum: [Jegadeesh and Titman (1993)](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1993.tb04702.x)
- Price momentum and volume: [Lee and Swaminathan (2000)](https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00280)
- Dynamic return-volume mechanisms: [Llorente, Michaely, Saar and Wang (2002)](https://web.mit.edu/wangj/Public/Publication/Llorente-Michaely-Saar-Wang02.pdf)
- Daily illiquidity: [Amihud (2002)](https://www.sciencedirect.com/science/article/pii/S1386418101000246)
- Breadth/advance-decline evidence: [Zakon and Pennypacker (1968)](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/abs/an-analysis-of-the-advancedecline-line-as-a-stock-market-indicator/0381B292609316D5EC5D11D2C87EA746). This early study is included as a cautionary primary anchor; it does not supply a strong durable edge prior.
- Industry momentum: [Moskowitz and Grinblatt (1999)](https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00146)
- Post-earnings drift: [Bernard and Thomas (1989)](https://www.jstor.org/stable/2491062)
- News language and delayed response: [Tetlock, Saar-Tsechansky and Macskassy (2008)](https://onlinelibrary.wiley.com/doi/full/10.1111/j.1540-6261.2008.01362.x)
- Analyst recommendations: [Womack (1996)](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1996.tb05205.x)
- Reference-price anchoring: [George and Hwang (2004)](https://onlinelibrary.wiley.com/doi/full/10.1111/j.1540-6261.2004.00695.x)
- Idiosyncratic volatility: [Ang, Hodrick, Xing and Zhang (2006)](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.2006.00836.x)
- Value and the cross-section: [Fama and French (1992)](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1992.tb04398.x)
- Asset growth: [Cooper, Gulen and Schill (2008)](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.2008.01370.x)
- Accrual persistence: [Sloan (1996)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2598)
- Low-volatility mechanism: [Baker, Bradley and Wurgler (2011)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1745108)
- IPO lifecycle: [Ritter (1991)](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1991.tb03743.x)
- Cross-firm information diffusion: [Cohen and Frazzini (2008)](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.2008.01379.x)
- Anomaly decay after publication: [McLean and Pontiff (2016)](https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12365)
- Large-scale anomaly replication: [Hou, Xue and Zhang (2020)](https://academic.oup.com/rfs/article/33/5/2019/5236964)
- Multiple-testing standards: [Harvey, Liu and Zhu (2016)](https://academic.oup.com/rfs/article-abstract/29/1/5/1843824)

---

## 11. Final programme recommendation

Project EDGE should direct the majority of current research effort to the five-family queue in Section 1 and should activate only the first family now.

The immediate research direction is:

> **Regular-session price-discovery persistence or reversal: one continuous, one-session, cross-sectional test using raw MDM open-to-close returns.**

This is the highest-ESIG first move because:

- it starts from observable price discovery rather than an arbitrary indicator;
- continuation and reversal correspond to distinct information and liquidity mechanisms;
- one result can support one mechanism, support the competitor, or close the exact branch;
- it is executable with current MDM without pretending that the dataset is perfect;
- its limitations can be stated and bounded honestly;
- it is independent of the eliminated opening-gap ancestry and does not rescue paused range recurrence; and
- it moves Project EDGE directly toward or away from the existence of a persistent directional equity phenomenon.

Ranks 2–5 should remain queued, not run in parallel. Rank 2 first requires feature validation; rank 5 first requires its membership preflight and is removed if that preflight fails. Ranks 13–28 should not consume Project EDGE implementation effort unless MDM independently makes their missing point-in-time data scientifically admissible. Ranks 29 and 30 retain their existing paused and closed dispositions.

The roadmap therefore concentrates research capital where mechanism, observability, falsification value and direct relevance to an eventual edge are jointly strongest—while preserving the default scientific outcome of **ELIMINATE**.
