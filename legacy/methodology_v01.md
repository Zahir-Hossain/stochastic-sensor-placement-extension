# Methodology Notes

## 1. Synthetic historical trajectories

A set of 250 straight-line routes is generated from Gaussian perturbations around a nominal slope and intercept.

## 2. Representation-space transformation

Each route \(y=mx+b\) is mapped to

\[
\alpha=\frac{\pi}{2}+\arctan(m), \qquad
p=\frac{b}{\sqrt{1+m^2}}.
\]

This preserves the basic geometric representation used by the source framework.

## 3. Simplified intensity estimation

Rather than fitting a log-Gaussian Cox process with INLA, the simulation forms a normalized Gaussian-smoothed density over the transformed points. This is a visualization and toy-model substitute, not a statistical equivalent of LGCLP/INLA.

## 4. Sensor detection model

Candidate sensor positions lie on a regular spatial grid. Detection probability decreases with perpendicular distance from the sensor to a route. A network miss probability is built multiplicatively as sensors are added.

## 5. Greedy sensor selection

For each sensor addition, all remaining candidate locations are tested. The candidate producing the smallest aggregate miss score is selected, then removed from the candidate pool.

## 6. Future-route scenario

A controlled shift is applied to route slopes and intercepts. The purpose is not to forecast trajectories accurately; it is to create a changed future route distribution so that sensitivity of sensor placement can be inspected.

## 7. Uncertainty-aware scenario

Historical and future routes are combined, then multiple slope/intercept perturbations are applied to represent a simple corridor of plausible route deviation.

## 8. Comparison

Historical, predicted, and uncertainty-aware placements are compared through their selected sensor positions and normalized miss scores.

Because the underlying route sets differ and are synthetic, the resulting scores are illustrative rather than a fair performance benchmark between algorithms.
