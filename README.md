This repository accompanies the paper "Quantitative Relaxations for Arrow's Axioms".

## Repository Structure

The repository contains the following core files:

**`All_Scotland_wards_4th.shp`**  
  Shape file for producing the scottish heat map.

**`fairness_metric.py`**  
  Implements:
  - The **Kendall Tau distance** function  
  - Our quantitative fairness metrics:
    - **$\sigma_{IIA}$** (Independence of Irrelevant Alternatives)
    - **$\sigma_{UM}$** (Unanimity)

**`generate_BT_profiles.py`**  
  Generates the preference profiles using the `name_BradleyTerry` model from VoteKit.

**`collect_stats_BT.py`**  
  Collects the statistics for several elections over the profiles generated using the 
  Bradley-Terry model.

**`create_sigma_output.py`**
  Creates some of the output plots for each of the fairness metrics and voting rules in
  the paper.

**`run_BT_pipeline.sh`**
  Runs the pipeline for the Bradley-Terry model.

**`collect_stats_scottish.py`**
  Collects the statistics for all elections in the Scottish dataset.

**`create_scottish_outputs.py`**
  Creates an output plot for the Scottish dataset for each of the fairness metrics
  and generates an overall statistics file.

**`run_scottish_pipeline.sh`**
  Runs the pipeline for the Scottish dataset.


## Setup

This repo uses [uv](https://docs.astral.sh/uv/) to manage dependencies. Once UV is installed,
simply run `uv sync` to install the dependencies.


## Running the Experiments

To repeat the experiments in the paper, you may run the included pipeline scripts:

```console
./run_scottish_pipeline.sh
./run_BT_pipeline.sh
```

## Scottish Election Data

All scottish election data can be obtained from the 
[Scottish Election Data Archive](https://github.com/mggg/scot-elex.git)
createed by the Metric Geometry and Gerrymandering Group (MGGG).


