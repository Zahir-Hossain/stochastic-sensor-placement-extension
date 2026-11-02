# Model, derivations and guarantee scope

This note separates standard results, elementary consequences and numerical
heuristics. It does not claim a new general approximation algorithm.

## 1. Trajectories and probabilistic coverage

A line is represented by

$$x\cos\alpha+y\sin\alpha=p,\qquad \alpha\in[0,\pi),\quad p\in\mathbb R.$$

For a slope-intercept line, $\alpha=\pi/2+\arctan m$ and
$p=b/\sqrt{1+m^2}$. The identification
$(\alpha,p)\sim(\alpha+\pi,-p)$ makes the line space a Moebius strip.
Kernel images, the lattice prior and drift coordinates respect this seam.

For sensor $s=(x_s,y_s)$, the perpendicular distance is
$d_s=|x_s\cos\alpha+y_s\sin\alpha-p|$. With conditional independence of
sensor detections, network miss probability is

$$q_S(\ell)=\prod_{s\in S}(1-P_D(d_s(\ell))).$$

Let $\lambda$ be the intensity of a Poisson process in line space. Standard
independent thinning gives

$$L(S;\lambda)=\int\lambda q_S,\qquad
P(\text{no missed trajectory in an epoch})=e^{-L(S;\lambda)}.$$

The detected mass $\int\lambda(1-q_S)$ is monotone submodular. Greedy
selection of $k$ distinct candidates attains at least $1-1/e$ of the best
**detected mass on that finite candidate set**. This is not a multiplicative
bound on missed mass, void probability, a nonlinear risk objective or the
best continuous placement. L-BFGS-B refinement is local and keeps the start
if the objective becomes worse. These ingredients build on Kim et al.
(2025) and Nemhauser, Wolsey and Fisher (1978).

Numerically, Gaussian kernels are integrated over cells, but detection is
evaluated at cell centres and the window mask uses the centre line. The
result is quadrature, not an exact continuous-space integral. Synthetic
placement is evaluated on a finer grid as a separate check.

## 2. Chronological forecasting and intensity stacking

The history consists of epochs $0,\ldots,T-1$ and the target is
$t^\star=T-1+h$, $h\ge1$. Available forecasts are pooled history, recent
history, constant drift, uncertainty-expanded drift and cellwise log trend.
For a validation target $u$, the training prefix has length $u-h+1$.
**Bandwidth and every fitted quantity are recomputed on that prefix.**
A user-declared fixed bandwidth may be shared because it is not fitted on
validation observations.

For $K$ forecast intensities and $w$ on the probability simplex, define
$\lambda_{w,u}=\sum_k w_k\lambda_{k,u}$. Intensity stacking solves

$$\max_{w_k\ge0,\,\sum_kw_k=1}\sum_u
\left[\sum_{\ell\in D_u}\log\!\left(\sum_kw_k\lambda_{k,u}(\ell)\right)
-\sum_kw_k\int\lambda_{k,u}\right].$$

The code minimises the negative, a convex objective in the weights, using
SLSQP with an analytic gradient. A common absolute $10^{-12}$ numerical
floor protects the logarithm. Final component forecasts are then refitted
using the entire available history, without the future target epoch.

This is stacking of **Poisson intensities**. A Poisson process at a convex
combination of intensities is not the same predictive law as a mixture of
Poisson processes. Yao et al. (2018) provides background on predictive
stacking and distinguishes it from pseudo-BMA; no claim of equivalence to
full Bayesian predictive-distribution stacking is made here.

The `pseudo_bma` baseline instead sets
$w_k\propto\exp(\sum_u\mathrm{score}(\lambda_{k,u},D_u))$.
It can concentrate on one component even when an interior intensity mixture
scores better. Neither set of learned weights is asserted to be posterior
model probabilities. With no usable validation origin, `stacked` falls
back to the pooled forecast (or the first declared component).

## 3. What the intensity-error bound does and does not say

Let $\hat S$ be a plan made with $\hat\lambda$ and $S_{\rm ref}$ the same
heuristic run with true intensity $\lambda$. Define

$$R=L(\hat S;\lambda)-L(S_{\rm ref};\lambda),\qquad
\delta=L(\hat S;\hat\lambda)-L(S_{\rm ref};\hat\lambda).$$

Linearity gives the exact identity

$$R=\delta+\int(\lambda-\hat\lambda)(q_{\hat S}-q_{S_{\rm ref}}).$$

Since $|a-b|\le\max(1-a,1-b)\le1$ on $[0,1]$,

$$R\le\max(\delta,0)+\int|\lambda-\hat\lambda|
\max(1-q_{\hat S},1-q_{S_{\rm ref}})
\le\max(\delta,0)+\|\lambda-\hat\lambda\|_1.$$

This is an elementary sensitivity inequality. The measured $\delta$ is a
comparison to a particular reference, not a known global optimisation gap.
Both true intensity and the reference are unavailable at deployment.
Checking the inequality on simulations checks implementation consistency;
it does not independently establish scientific novelty or an observable
out-of-sample guarantee. The true-intensity heuristic can occasionally lose
to a different local solution, so an oracle gap need not be nonnegative.

For equal total $N$, the expected Poisson score differs from
$-N\,\mathrm{KL}(\lambda/N\|\hat\lambda/N)$ by a constant. Pinsker gives
$\|\lambda-\hat\lambda\|_1\le N\sqrt{2\mathrm{KL}}$. This motivates log
score under the equal-total assumption. Held-out empirical score is noisy;
minimising it does not prove that an individual deployment will have lower
regret, and unequal totals also carry a count-rate error term.

## 4. Predictive uncertainty and risk

For any integrable random nonnegative intensity $\Lambda$,

$$\mathbb E[L(S;\Lambda)]=L(S;\mathbb E\Lambda).$$

Thus the predictive mean suffices for the expected-miss objective.
If a finite mixture is a specified posterior model, its posterior-weighted
mean is a sufficient Bayes input for this objective. The identity does not
imply that posterior probabilities are necessary for a particular mean or
optimal decision, and does not turn held-out score weights into a posterior.

Three distinct decisions are supported:

* `expected`: minimise $\mathbb E L$, using the mean intensity.
* `void`: minimise $-\log\mathbb E e^{-L}$. This maximises the Cox-process
  probability of no missed trajectory for the stated predictive intensity
  law. It is a soft minimum of sample losses: its derivative weights
  samples proportionally to $e^{-L}$. It emphasises favourable futures and
  should not be described as a worst-case penalty. Under drift,
  component-sampled `stacked:void` performs worse than history on average
  in the saved runs; the paired interval includes zero. Component selection
  defines a distribution, but neither posterior model probabilities nor
  calibration has been established. The soft minimum can concentrate on
  favourable component draws. See [the generated analysis](tables/void_failure.md).
* `cvar`: minimise the upper-tail conditional value-at-risk of $L$.
  For equally weighted losses $l_i$, this is
  $\min_\eta[\eta+(n(1-\beta))^{-1}\sum_i(l_i-\eta)_+]$.
  Sort losses descending and weight observation of rank $j=0,1,\ldots$ by
  $\min(1,\max(0,n(1-\beta)-j))/(n(1-\beta))$.
  The fractional boundary observation is essential. For losses 0 through
  31 at $\beta=0.9$, CVaR is **29.875**, not 29.5.

The predictive intensity samples used in these comparisons have not been
checked for calibration. Void and CVaR results are sensitivity analyses of
the supplied law; no numerical calibration claim is made. Stacking and
pseudo-BMA use the same component-selection sampler. Its weights define
valid sampling probabilities, without establishing posterior model
probabilities or calibrated uncertainty. The fixed `mixture` forecast has
no stored samples, so void and CVaR reduce to its single mean-field loss.
A weighted sum of component draws would specify a different law. Matching
a mean alone would not justify its dependence structure or calibration.

Nonlinear objectives have no inherited $1-1/e$ guarantee. CVaR can be
nonsmooth; local gradient-based refinement is a heuristic, with the start
retained if it worsens the value.

A Gaussian shift $\Delta\sim N(\mu,\Sigma)$ convolved with a Gaussian
kernel of covariance $H$ gives covariance $H+\Sigma$ and mean shifted by
$\mu$. This standard convolution identity motivates `drift_u`. The
estimated drift covariance, its small-sample variance inflation, diagonal
approximation, finite image expansion and window masking are modelling and
numerical choices. They are not exact posterior calibration for arbitrary
traffic regimes.

## 5. A finite-grid distributionally robust objective

Let $m\ge0$ be nominal active-cell masses, $N=\sum_i m_i>0$ and let
$\epsilon\in[0,1]$. Define the equal-total ambiguity set

$$\mathcal M_\epsilon(m)=\{z\ge0:\ \mathbf1^Tz=N,
\ \tfrac12\|z-m\|_1\le\epsilon N\}.$$

The `tv` objective is

$$\rho_\epsilon(S;m)=\max_{z\in\mathcal M_\epsilon(m)}z^Tq_S.$$

**Inner solution.** Order cells by increasing $q_i$. Remove up to
$\epsilon N$ mass from the lowest-loss cells and place it at a
maximum-loss cell, stopping when remaining donors have that same maximum
loss. The resulting mass is feasible and optimal.

*Proof.* Every feasible change transfers at most $\epsilon N$ mass from
donors to recipients. For each unit moved, the largest recipient loss is
$q_{\max}$. Given that recipient, an exchange argument selects donors in
ascending loss order: using a higher-loss donor while a lower-loss donor
still has mass cannot improve the objective. Once all nonmaximum-loss
mass has been transferred, no further increase is possible. This constructs
a feasible transfer attaining the largest gain. The implementation is
checked against a separately formulated linear program.

Consequently,

$$m^Tq_S\le\rho_\epsilon(S;m)\le
\min\{Nq_{\max},\ m^Tq_S+\epsilon N(q_{\max}-q_{\min})\}.$$

For any **normalised grid truth** $p$ with
$\tfrac12\|p-m/N\|_1\le\epsilon$,

$$\mathbb E_p[1-q_S]\ge1-\rho_\epsilon(S;m)/N.$$

This is a conditional certificate for that plan and that finite grid. It
does not certify that the chosen radius covers future data, that the outer
sensor search is globally optimal, or that quadrature error is zero.
The robustness experiment records the truth-to-forecast TV distance and a
`certificate_applies_on_grid` flag; fine-grid detection is a separate metric.

The outer `tv` solver uses greedy initialisation and one-sensor exchanges
on the candidate set. Each accepted exchange decreases the objective.
The maximum over traffic distributions does not preserve the expected-mass
submodular guarantee in general. This is explicitly a heuristic outer
solver with an exact inner adversary. TV ambiguity and robust observation
selection are established tools; their application here is not claimed as a
new general robust-optimisation theorem.

## 6. Estimation and real-data scope

KDE uses cell-integrated product Gaussian kernels and seam images.
Leave-one-out selection removes each observation and all its images.
LGCP uses Poisson cell counts and a lattice smoothing prior
$Q=\tau(\kappa^2I+L)^2$, with a Laplace approximation and plug-in
hyperparameters. This is a lattice/SPDE-inspired model, not a reproduction
of the original R-INLA pipeline or an invariant physical Matérn field.
Its tuning can perform poorly for narrow lanes and sparse observations.

AIS reports are split before fitting at time gaps, window exits, low-speed
reports and validation-epoch boundaries. Scores measure modelled expected
detection per straight piece, not measured sensor detections or necessarily
one piece per ship. Four origins from one day are a demonstration. Bootstrap
intervals over these overlapping origins are descriptive and do not support
population-level significance claims.

A committed post hoc bandwidth probe changes only the KDE bandwidth scale.
Finer resolution materially changes the comparison with LGCP. This exposes
estimator-resolution sensitivity, not a selected setting, equivalence of
methods or a resolved comparison between history and forecast. See the
[generated sensitivity table](tables/ais_bandwidth_sensitivity.md).

## References

* Kim, Stilwell, Yetkin and Jimenez (2025), [arXiv:2505.00825](https://arxiv.org/abs/2505.00825).
* Kim et al. (2023), *Toward Optimal Placement of Spatial Sensors to Detect Poisson-Distributed Targets*, DOI 10.1109/ACCESS.2023.3326349.
* Nemhauser, Wolsey and Fisher (1978), *An analysis of approximations for maximizing submodular set functions*.
* Yao, Vehtari, Simpson and Gelman (2018), [Using stacking to average Bayesian predictive distributions](https://arxiv.org/abs/1704.02030).
* Rockafellar and Uryasev (2000), *Optimization of conditional value-at-risk*.
* Krause, McMahan, Guestrin and Gupta (2008), [Robust Submodular Observation Selection](https://www.jmlr.org/papers/v9/krause08b.html).
* Lindgren, Rue and Lindström (2011), *An explicit link between Gaussian fields and Gaussian Markov random fields*.
