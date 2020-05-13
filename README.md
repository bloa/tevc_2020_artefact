# [Paper Title] -- Artefact

## Prerequisites

Different versions may lead to slightly different results.

- python 3.6.8
- perf 3.10.0
- gcc 4.8.5
- java 10.0.2

Optional:

- srcml 0.9.5


## Recalibration

Training budgets are function of the host processing speed.
To recalibrate, run the "analyse" step (in the artefact folder, run `make analyse`) and use the output to modify in `artefact/main_tevc.py' the `APPROX_TIME` of every scenario accordingly to the running time reported (in seconds).


## Troubleshooting

### `RuntimeError: PROXY_PATH should not exist (yet)`

Something went wrong in a previous run.
To avoid overwriting potentially precious log, execution for this particular run require the given path ("PyGGI will run from [...]") to be manually deleted.
