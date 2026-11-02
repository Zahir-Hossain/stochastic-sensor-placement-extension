# Explain and defend the project

## The problem in plain language

There are only a few sensors, and they must be placed before tomorrow's
traffic arrives. Historical traffic is useful, but a route can move or a new
lane can appear. The project studies what happens when a sensor network is
planned for a forecast rather than for a pooled map of the past.

## Follow one trajectory

A straight trajectory in the plane becomes a point `(alpha, p)` in line
space. A sensor covers a curved band of these points because its distance
to each line depends on that line's angle and offset. Several sensors have
overlapping detection opportunities. Multiplying their miss probabilities
gives the network miss probability for that trajectory, under conditional
independence.

Integrating miss probability against the traffic intensity gives the
expected number of missed passages in an epoch. A 95% expected detection
rate does **not** mean a 95% chance that every passage is detected. For a
fixed Poisson intensity the latter probability is `exp(-expected misses)`.

## What the implementation adds

1. Forecast the line intensity from past epochs.
2. Compare and combine forecasts using strictly chronological validation.
3. Place sensors with an expected-loss, predictive-void, CVaR or TV objective.
4. Evaluate on known future truth in simulation and future passage pieces
   in the AIS demonstration.
5. Include a reversal that a constant-drift forecast cannot anticipate.

## Questions to be ready for

**What is original here?**

An independent extension and evaluation of future-aware placement, including
an explicit finite-grid ambiguity experiment and corrected validation.
The line representation, LGCP family, probabilistic coverage, greedy bound,
stacking principle and robust optimisation tools are established methods.
The repository does not establish a new general-purpose algorithm or a
state-of-the-art result.

**Why not just use the most recent traffic?**

Recent observations can adapt to a new lane while still lagging a steadily
moving one. Drift extrapolation helps in that case and can fail badly when
motion reverses. The experiments expose these distinct assumptions.

**Why learn weights rather than use a third each?**

A fixed mixture assigns weight to models even when their assumptions fail.
Intensity stacking chooses simplex weights by the held-out Poisson score of
the combined intensity. Pseudo-BMA weights individual model scores instead.
Neither is asserted to be a posterior model probability.

**What does the robust certificate actually guarantee?**

For the chosen sensor positions, it lower-bounds expected detection over
all equal-total cell-mass distributions within the chosen TV radius.
It is exact for that finite inner problem. It does not certify that the
sensor positions are globally optimal or that real traffic is inside the
ball. Fine-grid evaluation and grid-certificate values are kept separate.

**Does a green CI badge validate the science?**

It verifies the checks defined in the workflow. Scientific validity also
depends on assumptions, leakage control, fair baselines, and how closely
the synthetic and real-data experiments represent the intended use.

**What would improve the evidence next?**

A preregistered multi-day, multi-site AIS evaluation with held-out route
changes; calibrated forecast uncertainty; physical sensor-performance data;
and comparison against stronger domain-specific placement methods.

## A short demonstration

Run `examples/quickstart.py`, then `examples/robust_placement.py`.
Explain the reported metric before describing the improvement. Open the
robustness figure and identify the reversal case, then open a raw run in
`results/robustness/runs.csv`. Finish by stating the certificate's scope.
