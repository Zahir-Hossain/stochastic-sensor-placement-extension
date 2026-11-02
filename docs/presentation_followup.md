# Presentation feedback follow-up

The supplied `stochplace-presentation-fixes.zip` contains seven commits based
on `2c5fe28`, ending at `49366a2`. The published branch had already advanced
to `235bc59`, with a different, fully regenerated audit follow-up. The older
branch was compared rather than merged wholesale.

## Already addressed in the published audit follow-up

- The AIS final-fit-only probe is distinguished from nested-prefix selection.
- Every C1 method and component contrast is shown, including losses.
- C5 calibration-prefix fallback, discrete plans and degenerate intervals
  are disclosed; no stronger claim about geometry alone is made.
- Current validation pointers, solver-status records, the latent epoch
  default, calibration warnings and missing attribution are corrected.
- Local design-freeze evidence is explicitly not an external timestamp.

## Carried forward and adapted

- A result-led README and overview show both successful and failing cases.
  The figure, overview table and report macros derive from saved raw runs.
- Earlier reviews and raw check records move into `docs/history/`, with
  machine-input paths and current links updated. Bundle baselines remain.
- A concise changelog replaces the development log at the entry point.
- Three transport checks from the supplied branch cover two study-scale
  primal/dual comparisons and a separate dual LP for concentrated masses.
- The report title and abstract lead with the stress-test question and
  include the component, AIS, calibration and transport limitations.
- Unpublished Git tags are no longer presented as existing releases.

The repository keeps its fixed bootstrap procedure. In particular, the
random-walk-versus-recent interval includes zero; a near-zero endpoint from
the external audit's different resampling is not copied as a decisive loss.

Package-source bytes, study runners, configurations, seeds, gate thresholds,
raw runs, summaries and the compiled report's mathematical derivations are
unchanged. This follow-up does not create new experimental evidence or an
external preregistration. The latest checks are in [validation.md](validation.md).

Merge, tags, releases, About settings and a repository rename remain separate
publication decisions. A concrete [presentation proposal](repository_presentation.md)
is included. No multi-week AIS result is claimed.
