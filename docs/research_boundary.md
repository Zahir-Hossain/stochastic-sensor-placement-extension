# Research Boundary: Original Framework vs. Extension Work

This note makes attribution explicit.

## Kim et al. — original framework

The source paper develops the underlying 2-D stochastic barrier-coverage framework. Its contributions include:

- representing local linear target trajectories as points in an \((\alpha,p)\) space;
- modeling stochastic target trajectories with a log-Gaussian Cox line process;
- estimating trajectory intensity from historical AIS-derived trajectories using INLA;
- expressing probabilistic sensor detection in the representation space;
- maximizing a void-probability approximation for sensor placement;
- greedy initialization followed by nonlinear optimization methods;
- numerical validation using historical ship traffic near Hampton Roads, Virginia.

These elements are **not claimed as original contributions of this repository**.

## Extension developed in this project

The work documented here begins from a different question:

> What if deployment is informed not only by historical trajectory intensity, but also by predicted future trajectories and explicit trajectory uncertainty before placement?

The extension work consists of:

1. separating historical, predicted-future, and uncertainty-aware trajectory scenarios;
2. creating controlled synthetic future shifts in line slope/intercept;
3. combining historical and future route sets;
4. constructing a simple uncertainty corridor through plausible route-parameter perturbations;
5. generating intensity maps for each route scenario;
6. applying the same simplified distance-based sensor model and greedy placement logic to each case;
7. comparing selected sensor locations and normalized miss scores;
8. proposing the conceptual extended intensity
   \(\lambda_E=w_H\lambda_H+w_F\lambda_F+w_U\lambda_U\);
9. identifying context-aware future directions such as weather-, traffic-, season-, or port-conditioned deployment.

## What this repository does not claim

This is not a full reproduction of the source paper, not an implementation of INLA/LGCLP estimation, and not an experimentally validated robust-sensor-placement algorithm. The simulations are intended to test and communicate the **research direction** created by adding future-route and uncertainty information before deployment.
