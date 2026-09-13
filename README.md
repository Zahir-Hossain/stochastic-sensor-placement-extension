# Prediction- and Uncertainty-Aware Sensor Placement for Stochastic Trajectories

A research-extension study built from the barrier-coverage framework of Kim, Stilwell, Yetkin, and Jimenez, **“Near-optimal Sensor Placement for Detecting Stochastic Target Trajectories in Barrier Coverage Systems”** (arXiv:2505.00825).

> **Timeline note**  
> The research task and simulation in this repository were carried out in **May–June 2026** and submitted to Prof. Mingyu Kim on **June 5, 2026**. This GitHub repository was organized and published later in **September 2026**. The repository publication date should therefore not be interpreted as the date the underlying work was performed.

## Research question

The original framework optimizes sensor placement from stochastic target-trajectory intensity estimated from **historical trajectories**. This project asks a natural extension question:

**How might sensor placement change if the deployment model explicitly accounts for predicted future trajectories and route uncertainty before sensors are placed?**

The study is intentionally a **conceptual and simulation-based extension**, not a reproduction of the full LGCLP/INLA pipeline and not a claim of new experimental validation.

## Starting point: the original framework

Kim et al. formulate near-optimal sensor placement for linear stochastic target trajectories in a 2-D barrier coverage system. Their workflow can be summarized as:

1. Approximate local target trajectories as straight lines.
2. Map each line into a unique point in representation space using
   \(\alpha = \pi/2 + \arctan(m)\) and \(p=b/\sqrt{1+m^2}\).
3. Estimate trajectory intensity in representation space using a log-Gaussian Cox line-process formulation.
4. Map sensor detection performance into the same representation space.
5. Optimize sensor locations by maximizing a void-probability approximation, using greedy selection and nonlinear refinement.

Original paper: https://arxiv.org/abs/2505.00825

## Where this project begins

This project keeps the core geometric and sensor-placement logic as a base, but changes the **trajectory information supplied to the placement stage**.

Three route scenarios are constructed:

- **Historical:** synthetic historical routes with small slope/intercept variation.
- **Predicted future:** a controlled shift of the route distribution to represent a changed future traffic pattern.
- **Historical + predicted + uncertainty:** historical and future routes are combined, then expanded by plausible slope/intercept deviations to create an uncertainty corridor.

The conceptual extension is summarized by an expanded intensity model:

\[
\lambda_E = w_H\lambda_H + w_F\lambda_F + w_U\lambda_U,
\]

where \(\lambda_H\), \(\lambda_F\), and \(\lambda_U\) denote historical, future-predicted, and uncertainty-adjusted trajectory intensity components.

## Simulation workflow

The MATLAB simulation uses a deliberately simplified pipeline:

`synthetic routes → line representation → (α,p) transformation → Gaussian-smoothed intensity map → distance-based sensor model → greedy sensor placement → normalized miss-score comparison`

Instead of implementing the original paper’s full LGCLP + INLA estimation, this study uses Gaussian smoothing to create interpretable intensity maps from synthetic trajectory sets.

### Sensor model

For a sensor at \((x_s,y_s)\) and route \(y=mx+b\), the perpendicular distance is

\[
d = \frac{|mx_s-y_s+b|}{\sqrt{m^2+1}}.
\]

Detection probability is modeled as a Gaussian decay with distance:

\[
P_D = \rho \exp\left(-\frac{d^2}{2r^2}\right),
\]

and route miss probabilities are updated as sensors are greedily added.

## What the simulation shows

The study compares the locations selected under the three trajectory assumptions and the corresponding normalized miss scores.

The important interpretation is **not** that one scenario is universally better. The inputs are synthetic, and some parameters were deliberately adjusted to make the route-set differences visible. The result instead demonstrates a structural point:

**sensor placement is sensitive to the trajectory model supplied to the optimizer.**

When uncertainty widens the plausible route region, the same number of sensors must cover a larger trajectory space, so the normalized miss score can increase. This motivates condition-aware or uncertainty-aware placement when future traffic may depart from historical patterns.

## Repository contents

```text
.
├── README.md
├── src/
│   └── sensor_placement_simulation.m
├── report/
│   ├── Research_Extension_Report_June_2026.pdf
│   └── Simulation_Results_June_2026.pdf
└── docs/
    ├── research_boundary.md
    └── methodology_notes.md
```

## Important research boundary

This repository separates the source paper from the extension work:

- The **LGCLP/INLA formulation, representation-space framework, void-probability formulation, and original AIS validation** belong to Kim et al.
- The **prediction-aware / uncertainty-aware extension idea, synthetic scenario construction, MATLAB implementation, comparison of historical vs. future vs. uncertainty-aware placement, and proposed extended-intensity framing** are the work documented here.

See [`docs/research_boundary.md`](docs/research_boundary.md) for the detailed distinction.

## Limitations

- Synthetic routes are used instead of AIS observations.
- Future trajectories are represented by controlled parameter shifts rather than a trained forecasting model.
- Uncertainty is represented by slope/intercept perturbations rather than a learned probabilistic trajectory model.
- Gaussian smoothing replaces the paper’s LGCLP/INLA intensity estimation.
- The normalized miss-score comparison is illustrative, not a benchmark against the original paper.

## Natural next steps

A stronger follow-on study could combine real AIS trajectories with:

- ARIMA, Kalman filtering, LSTM/Transformer trajectory forecasting,
- Gaussian-process or Bayesian uncertainty estimation,
- weather-, traffic-, port-, or season-conditioned trajectory models,
- the full LGCLP/INLA intensity pipeline,
- dynamic sensor redeployment or robust optimization.

## Citation of the source work

M. Kim, D. J. Stilwell, H. Yetkin, and J. Jimenez, *Near-optimal Sensor Placement for Detecting Stochastic Target Trajectories in Barrier Coverage Systems*, arXiv:2505.00825, 2025.

## Author

**A. S. M. Jahir Hossain**  
Electrical & Electronic Engineering  
Research interests: sensing, stochastic systems, scientific computing, physical systems, and computational modeling.
