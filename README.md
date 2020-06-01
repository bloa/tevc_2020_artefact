# Empirical Comparison of Search Heuristics for Genetic Improvement of Software — Artefact

Artifact associated with a paper in submission in the _IEEE Transactions on Evolutionary Computation (TEVC)_ journal, by Aymeric Blot and Justyna Petke.
This paper investigates the performance of local search and genetic programming approaches when applying genetic improvement on MiniSAT, Sat4j, OptiPNG, MOEA/D and NSGA-II.

## Usage

There are two makefiles.
One to build the replication package, and the second to actually run the experiments; none require explicit arguments.

From the top level, simply run `make`.
The external code and data used in the experiments will first be downloaded unmodified into the "archives" folder, then installed into the experiments folder "artefact", applying when necessary corrective and instrumentalisation patches that can be found in the "instr" folder.

Once the replication package is completely rebuild, experiments can be started by running `make` from the "artefact" folder.


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
