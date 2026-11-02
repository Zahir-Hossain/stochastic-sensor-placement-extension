# Exploratory geometry-aware ambiguity

For the signed line-distance function f_i(x)=n_i.x-p_i on a rectangular
window W, use

$$d(i,j)=\min_{s\in\{-1,1\}}\max_{x\in\mathrm{corners}(W)}|f_i(x)-s f_j(x)|.$$

The maximum of the absolute affine difference occurs at a corner. The
minimum over signs respects the unoriented line identification. This is
a quotient of a sup-norm metric on signed distance functions; it measures
window-scaled geometric discrepancy, not distance between intersections.

For normalised source masses m and miss probabilities q, the finite-grid
transport adversary is

$$\max_{\pi\ge0}\sum_{ij}\pi_{ij}q_j,\quad
\sum_j\pi_{ij}=m_i,\quad\sum_{ij}\pi_{ij}d(i,j)\le r.$$

Its scalar dual is

$$\inf_{\eta\ge0}\left[\eta r+\sum_i m_i\max_j(q_j-\eta d(i,j))\right].$$

Every evaluated dual value is an upper bound on the adversarial miss
fraction. The implementation numerically minimises this convex function
on a bounded interval and checks it against a separately written primal
linear program. The resulting detection lower bound is conditional on
the normalised grid truth lying in the chosen transport ball. Continuous
quadrature and global placement optimality are not certified.

Wasserstein distributional robustness and this dual construction are
established tools; see [Gao and Kleywegt](https://arxiv.org/abs/1604.02199).
No new general robust-optimisation theorem is claimed.

The experiment uses a small planning grid and radii from chronological
forecast-to-observed-KDE errors. A short empirical calibration history does
not provide a nominal coverage guarantee. Geometry alone does not impose
bathymetry, shipping rules or feasible routes. Report every regime and
whether any plan changes, including any negative result.

## Additional numerical checks

The presentation follow-up adds independent primal LP comparisons at the
study grid size for radii 0.3 and 1.5, and a separate Kantorovich dual LP
for the concentrated-mass fixture. The original four-cell checks and frozen
POT reference remain. This changes validation coverage, not the study's
transport method, calibration rule or outcomes.
