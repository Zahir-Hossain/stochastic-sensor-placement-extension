# Expected-void planning under drift

Gap to the true-intensity heuristic: **3.67 [2.90, 4.44] pp**; 29 of 40 seeds exceed 1 pp. Correlation with non-drift component weight: 0.70. Detection difference from history: **-0.69 [-1.46, +0.11] pp**. The paired percentile interval includes zero, so the lower mean does not establish a reliable loss to history across seeds.

Computed only from `results/suite_drift/runs.csv` by `scripts/void_failure_analysis.py`; bootstrap over paired seeds. The heuristic reference is not a global optimum.
