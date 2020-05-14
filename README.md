# [Paper Title] -- Artefact

## Replication package

There are two makefiles.
One to build the replication package, and the second to actually run the experiments; none require explicit arguments.


## Software version used

Different versions may lead to slightly different results.

- python 3.6.8
- perf 3.10.0
- gcc 4.8.5
- java 10.0.2

Optional:

- srcml 0.9.5


## Recalibration

Training budgets are function of the host processing speed.
To recalibrate, run the "analyse" step (in the artefact folder, run `make analyse`) and use the output to modify in artefact/main_tevc.py the "APPROX_TIME" constant of every scenario accordingly to the running time reported (in seconds).


## Troubleshooting

### An archive fails to download

Backups for every archive can be found [here](https://github.com/bloa/tevc_2020_artefact/releases/tag/v1.0-archives).
Alternatively, you can use the makefile prepending "backup_" to the name of the archive.
For example, if `make archives/MOEA-D-DE.rar` fails, use `make archives/backup_MOEA-D-DE.rar`.

### `RuntimeError: PROXY_PATH should not exist (yet)`

Something went wrong in a previous run.
To avoid overwriting potentially precious log, execution for this particular run require the given path ("PyGGI will run from [...]") to be manually deleted.
