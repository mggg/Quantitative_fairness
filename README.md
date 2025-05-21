#Quantitative Fairness

This repository accompanies the paper "Quantitative Relaxations for Arrow's Axioms".

#Repository Structure

The repository contains the following core files:

**'voting_rules.py'**  
  Implements all complete-ranking voting rules used in the experiments.

**`fairness_metric.py`**  
  Implements:
  - The **Kendall Tau distance** function  
  - Our quantitative fairness metrics:
    - **σIIA** (Independence of Irrelevant Alternatives)
    - **σU** (Unanimity)

- **`experiments_main.ipynb`**  
 VScode / Jupyter notebook to reproduce all key experimental results.

- **`All_Scotland_wards_4th.shp`**  
   Shape file for producing the scottish heat map.



## Requirements

- Python `3.10.1`
- Votekit `3.1.0`

# Data

The "scot-elex-main" folder contains the Scottish election dataset.  
You can either download the dataset and specify its path in the experiments, or directly set the path to the `scot-elex-main` folder.

This is "scot-elex-main" folder contains the data from Scottish local government elections conducted by ranked voting in the years 2007, 2012, 2017, and 2022. This data was originally assembled and cleaned thanks to the work of David McCune, who collected cast vote records from Scottish sources to create files in a file format called BLT format.
This is the code repository for the project " Quantitative fairness measures for voting rules".
