# Historical source snapshots

`pre_cleanup/` preserves the original root implementations, package implementations, old test
module, machine-specific settings, and root runners from the revision in `docs/baseline.json`.
The `.txt` suffix keeps these snapshots out of Python imports and test collection. They are
reference material, not supported entry points. `find_missing_stats.sh.txt` preserves the unused
root diagnostic for the earlier BT experiment layout.

The maintained metric modules live in `voting_metrics_main_code/`; root import shims were removed.
The old root test module had the same named tests as `tests/test_fairness_metric.py`, using the
older VoteKit API; the maintained tests and BT batch tests are under `tests/`.

Existing notebooks, `dev_files/`, `paper/`, inputs, statistics, and plots remain in their original
locations. The ignored directories may contain unique research work and are not expendable.

`single_alpha/collect_metrics.py.txt` preserves the collector for scalar-alpha profile folders.
Those inputs are not supplied. Maintained alpha boxplots instead pool the saved two-bloc results
using `pipelines/bradley_terry/pool_alpha_metrics.py`.
