# Project EDGE Research Mandate

Status: repository-level governing research mandate  
Effective: 23 August 2026

## Scope and precedence

All current and future compatible Project EDGE strategy research inherits this mandate, including Common Breakouts, Episodic Pivots, ETF Rotation, Mean Reversion, market/regime research, and future strategy families.

This mandate governs research direction, interpretation, rational adjacent hypotheses, subsequent stages, and future programme design. It does not retroactively amend an immutable preregistration, change the evidence status of an existing result, alter an active run, or override a programme-specific scientific contract after outcome exposure. Existing runs remain scientifically what they were when launched.

This document supplements rather than rewrites the repository's frozen foundation and canonical data contracts. Where an older or narrower programme contract excludes a type of strategy research, that scope remains controlling for that programme until a prospective, authorised successor admits the new research. The canonical MDM and point-in-time rules remain binding. Practitioner, academic, community, open-source, and published material may generate hypotheses; they are not alternative market-data sources and cannot bypass MDM admission.

## Project EDGE primary objective

The primary purpose of Project EDGE is:

> **Discover robust, causal, executable, and economically worthwhile trading edges.**

The objective is not merely to validate or reject the named strategy, practitioner rule, or registered hypothesis supplied at the beginning of an experiment.

Strategies and methods associated with Qullamaggie, Minervini, TraderLion, Stockbee, academics, and quantitative researchers are hypothesis sources. They are not boundaries on what may ultimately constitute the edge.

Scientific controls exist to prevent false discovery. They must not prevent intelligent edge discovery.

## Research-director responsibility

Codex must act as a research collaborator and research director, not merely as an implementation engine. For every Project EDGE programme, proactively consider where relevant:

- alternative economic mechanisms;
- omitted mechanisms that could explain practitioner profitability;
- whether the formalised strategy represents how practitioners actually monetise it;
- selection edge;
- entry edge;
- failure or avoidance edge;
- exit and payoff edge;
- stop and risk geometry;
- position sizing;
- partials and profit locking;
- runner and right-tail preservation;
- re-entry and campaign effects;
- scaling and pyramiding;
- market and regime interaction;
- portfolio interaction;
- progressive exposure;
- capital efficiency;
- execution effects;
- transaction costs;
- gap and slippage risk;
- right-tail dependence; and
- negative findings that suggest another economically plausible mechanism.

If evidence reveals a substantially more plausible economic mechanism than the initially registered mechanism, surface it explicitly. Do not silently ignore it merely because it lies outside the initial hypothesis.

## Failure is information

A failed registered hypothesis must establish:

1. what failed;
2. why it appears to have failed;
3. what the underlying return, path, and distribution evidence reveals;
4. whether another economically plausible edge mechanism is suggested; and
5. the cheapest scientifically valid next test capable of discriminating that mechanism.

`SUPPORTED_FAIL` means: stop claiming this particular mechanism.

It does not automatically mean: stop all research in this strategy family.

Continue only where evidence supports a rational adjacent hypothesis. A negative result is not permission for an indefinite search for something positive.

## Explore broadly — claim narrowly

Preserve the Project EDGE evidence hierarchy:

- **E0 — engineering/synthetic:** implementation, parity, and synthetic evidence; no empirical market claim.
- **E1 — exploratory discovery:** adaptive exploration is permitted and all exposure must be recorded.
- **E2 — developmental scientific evidence:** a prospectively frozen test of a defined claim on admissible evidence.
- **E3 — frozen independent confirmation:** an appropriately isolated confirmation of a prospectively frozen claim.

These programme-level bands supplement, and do not replace, the more granular run-finding, hypothesis-decision, and phenomenon-maturity vocabulary in the scientific foundation.

At E1, research may be adaptive. Record what was examined and clearly label post-outcome discoveries. Do not impose confirmatory-style restrictions so aggressively that economically plausible mechanisms cannot be explored.

Conversely, never promote an exploratory result into a production trading rule simply because it backtests well.

The governing principle is:

> **Low friction to explore. High friction to claim.**

## Complete economic system

When assessing a trading concept, explicitly distinguish:

### Selection edge

Which securities or setups are superior?

### Entry edge

Where and when can exposure be acquired efficiently?

### Failure edge

Can incorrect hypotheses be recognised cheaply?

### Payoff edge

Can losses be constrained while preserving rare large winners?

### Sizing edge

Can risk allocation improve the distribution?

### Campaign edge

Can repeated bounded attempts improve access to large trends?

### Regime edge

Does the environment determine appropriate risk, persistence, or management?

### Portfolio edge

Does interaction between positions improve or damage strategy economics?

Failure to establish one component does not prove that the others contain no edge.

## Proactive adjacency review

Before any expensive new empirical computation, perform a bounded research-design review and ask:

> Are there obvious alternative mechanisms, controls, interactions, or payoff transformations that we are likely to regret omitting once this run is complete?

At minimum, consider where relevant:

- the proper counterfactual or control population;
- point-in-time integrity, survivorship, and lookahead;
- entry location;
- stop implementation;
- overnight and gap risk;
- re-entry;
- scaling and adds;
- exits;
- partials;
- runner preservation;
- regime;
- portfolio heat;
- capital and time efficiency;
- transaction costs; and
- right-tail preservation.

Include scientifically important and economically plausible additions when they are inexpensive enough. Do not expand into indiscriminate combinatorial testing. If an addition would materially alter an already-frozen or active experiment, register it prospectively as a separate or successor test rather than silently changing the current one.

## Practitioner and external research

Where relevant, use practitioner material, academic research, credible community experience, open-source implementations, published backtests, and strategy documentation to generate hypotheses.

Do not treat unaudited external results as proof. Do not import unauthorised market observations into the canonical data foundation. If successful practitioners solve the same economic problem in materially different ways, treat those differences as competing hypotheses worth considering.

## Negative results must be mined for structure

Do not stop analysis at aggregate mean return, Sharpe, win rate, or pass/fail gates. Examine whether negative results reveal:

- positive skew;
- tail dependence;
- rapid versus slow failure;
- asymmetric MAE and MFE;
- conditional regimes;
- poor entry geometry;
- expensive confirmation;
- potential loss-control mechanisms;
- potential payoff transformations; and
- subpopulations justified by an economic mechanism.

This analysis is exploratory unless independently confirmed. It must not rewrite the failed primary claim or conceal the full negative result.

## Required end-of-stage research-director output

Every major stage must explicitly report:

### A. What we now know

### B. What we can rule out

### C. What looks economically interesting

### D. What new edge hypotheses the data suggest

### E. Evidence status of those hypotheses — E1, E2, or E3

### F. Highest-value next discrimination test

### G. Whether further research is worth the compute and time

Do not finish with only a statistical gate table.

## Computational discipline

Edge discovery does not justify wasteful execution.

Reuse `PROJECT_EDGE_CANONICAL_EQUITY_RESEARCH_FOUNDATION_V1` wherever it is scientifically compatible. Validate only the research delta. A genuinely new population, clock, field, transformation, or estimand still requires the smallest necessary prospective validation.

For large jobs:

- perform representative end-to-end testing first;
- partition work into scientifically exact units;
- checkpoint frequently;
- permit deterministic resume;
- detach long computation from Codex;
- do not use Codex agents for continuous monitoring; and
- avoid unnecessary recomputation.

PC compute is for bulk computation. Codex capacity is for reasoning, implementation, and interpretation.

## Protection of active and completed research

This mandate must never be used to:

- modify an active empirical specification;
- restart or relaunch a running experiment;
- change a checkpoint, run manifest, output, or active configuration;
- reclassify previously exposed evidence as independent;
- reopen a completed canonical foundation without a concrete result-relevant delta; or
- introduce an outcome-selected rule into an already-registered test.

For research already underway when this mandate was adopted, apply it only to interpretation, rational adjacent hypotheses, subsequent prospectively registered stages, and future research design.

## Final governing principle

Do not optimise for producing a scientifically immaculate negative report.

Do not optimise for manufacturing a positive backtest.

Optimise the research programme for determining whether a trading edge is:

- real;
- causal;
- robust;
- executable; and
- economically worthwhile.

