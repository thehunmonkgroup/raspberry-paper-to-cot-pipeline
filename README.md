# Raspberry: Papers to CoT pipeline

## Overview

The goal is to build a quality pipeline where academic papers go in one end and 'Chain of Thought' sets come out the other.

A Chain of Thought set includes:

1. A question *(hopefully clear and answerable)*
2. An answer *(hopefully verifiable)*
3. Multi-step thinking/reasoning necessary to derive the answer from the question *(hopefully accessible to a layperson's understanding)*

The idea is that these academic papers represent the best of how humans reason through tasks, and these extracted Chain of Thought sets can then be used to train AI models to improve their complex reasoning ability.

## Gathering the papers

[arXiv.org](https://arxiv.org) provides a ready source of academic papers for this experiment. Papers were extracted from various categories to best represent different types of reasoning.

To ensure we build grounded Chain of Thought sets, the academic papers used are at least two years old -- this helps prevent the model from encountering truly novel data that it hasn't been trained on, thereby reducing the risk of hallucinations. 

### arxiv.org categories

1. cs.AI - Artificial Intelligence
2. cs.LG - Machine Learning
3. cs.CL - Computation and Language
4. cs.CV - Computer Vision and Pattern Recognition
5. cs.GT - Computer Science and Game Theory
6. cs.LO - Logic in Computer Science
7. cs.DS - Data Structures and Algorithms
8. cs.SI - Social and Information Networks
9. cs.SE - Software Engineering
10. cs.HC - Human-Computer Interaction
11. cs.RO - Robotics
12. cs.CY - Computers and Society
13. econ.TH - Theoretical Economics
14. econ.EM - Econometrics
15. eess.SP - Signal Processing
16. math.LO -- Logic
17. physics.ed-ph -- Physics Education
18. q-bio.QM -- Quantitative Methods
19. astro-ph.EP -- Earth and Planetary Astrophysics
20. cond-mat.stat-mech -- Statistical Mechanics
21. q-fin.PM -- Portfolio Management
22. stat.ME -- Methodology
23. math.HO -- History and Overview
24. physics.soc-ph -- Physics and Society
25. q-bio.PE -- Populations and Evolution
26. econ.GN -- General Economics
27. physics.hist-ph -- History and Philosophy of Physics
28. math.OC -- Optimization and Control
29. q-fin.RM -- Risk Management
30. stat.AP -- Applications

### Commands used to extract papers

```sh
./pull-arxiv-papers.py --debug --date-filter-begin 1970-01-01 --date-filter-end 2020-01-01 --output papers/cs.AI.txt --category cs.AI
./pull-arxiv-papers.py --debug --date-filter-begin 1970-01-01 --date-filter-end 2020-01-01 --output papers/cs.LG.txt --category cs.LG
./pull-arxiv-papers.py --debug --date-filter-begin 1970-01-01 --date-filter-end 2020-01-01 --output papers/cs.CL.txt --category cs.CL
./pull-arxiv-papers.py --debug --date-filter-begin 1970-01-01 --date-filter-end 2020-01-01 --output papers/cs.CV.txt --category cs.CV
./pull-arxiv-papers.py --debug --date-filter-begin 1970-01-01 --date-filter-end 2020-01-01 --output papers/cs.GT.txt --category cs.GT
./pull-arxiv-papers.py --debug --date-filter-begin 1970-01-01 --date-filter-end 2020-01-01 --output papers/cs.LO.txt --category cs.LO
./pull-arxiv-papers.py --debug --date-filter-begin 1970-01-01 --date-filter-end 2020-01-01 --output papers/cs.DS.txt --category cs.DS
./pull-arxiv-papers.py --debug --date-filter-begin 1970-01-01 --date-filter-end 2020-01-01 --output papers/cs.SI.txt --category cs.SI
./pull-arxiv-papers.py --debug --date-filter-begin 1970-01-01 --date-filter-end 2020-01-01 --output papers/cs.SE.txt --category cs.SE
./pull-arxiv-papers.py --debug --date-filter-begin 1970-01-01 --date-filter-end 2020-01-01 --output papers/cs.HC.txt --category cs.HC
./pull-arxiv-papers.py --debug --date-filter-begin 1970-01-01 --date-filter-end 2020-01-01 --output papers/cs.RO.txt --category cs.RO
./pull-arxiv-papers.py --debug --date-filter-begin 1970-01-01 --date-filter-end 2020-01-01 --output papers/cs.CY.txt --category cs.CY
./pull-arxiv-papers.py --debug --date-filter-begin 1970-01-01 --date-filter-end 2020-01-01 --output papers/econ.TH.txt --category econ.TH
./pull-arxiv-papers.py --debug --date-filter-begin 1970-01-01 --date-filter-end 2020-01-01 --output papers/econ.EM.txt --category econ.EM
./pull-arxiv-papers.py --debug --date-filter-begin 1970-01-01 --date-filter-end 2020-01-01 --output papers/eess.SP.txt --category eess.SP
./pull-arxiv-papers.py --debug --date-filter-begin 1970-01-01 --date-filter-end 2020-01-01 --output papers/math.LO.txt --category math.LO
./pull-arxiv-papers.py --debug --date-filter-begin 1970-01-01 --date-filter-end 2020-01-01 --output papers/physics.ed-ph.txt --category physics.ed-ph
./pull-arxiv-papers.py --debug --date-filter-begin 1970-01-01 --date-filter-end 2020-01-01 --output papers/q-bio.QM.txt --category q-bio.QM
./pull-arxiv-papers.py --debug --date-filter-begin 1970-01-01 --date-filter-end 2020-01-01 --output papers/astro-ph.EP.txt --category astro-ph.EP
./pull-arxiv-papers.py --debug --date-filter-begin 1970-01-01 --date-filter-end 2020-01-01 --output papers/cond-mat.stat-mech.txt --category cond-mat.stat-mech
./pull-arxiv-papers.py --debug --date-filter-begin 1970-01-01 --date-filter-end 2020-01-01 --output papers/q-fin.PM.txt --category q-fin.PM
./pull-arxiv-papers.py --debug --date-filter-begin 1970-01-01 --date-filter-end 2020-01-01 --output papers/stat.ME.txt --category stat.ME
./pull-arxiv-papers.py --debug --date-filter-begin 1970-01-01 --date-filter-end 2020-01-01 --output papers/math.HO.txt --category math.HO
./pull-arxiv-papers.py --debug --date-filter-begin 1970-01-01 --date-filter-end 2020-01-01 --output papers/physics.soc-ph.txt --category physics.soc-ph
./pull-arxiv-papers.py --debug --date-filter-begin 1970-01-01 --date-filter-end 2020-01-01 --output papers/q-bio.PE.txt --category q-bio.PE
./pull-arxiv-papers.py --debug --date-filter-begin 1970-01-01 --date-filter-end 2020-01-01 --output papers/econ.GN.txt --category econ.GN
./pull-arxiv-papers.py --debug --date-filter-begin 1970-01-01 --date-filter-end 2020-01-01 --output papers/physics.hist-ph.txt --category physics.hist-ph
./pull-arxiv-papers.py --debug --date-filter-begin 1970-01-01 --date-filter-end 2020-01-01 --output papers/math.OC.txt --category math.OC
./pull-arxiv-papers.py --debug --date-filter-begin 1970-01-01 --date-filter-end 2020-01-01 --output papers/q-fin.RM.txt --category q-fin.RM
./pull-arxiv-papers.py --debug --date-filter-begin 1970-01-01 --date-filter-end 2020-01-01 --output papers/stat.AP.txt --category stat.AP
```

Count of unique papers across categories:

```sh
cat papers/* | awk 'match($0, /([0-9]+\.[0-9]+)v[0-9]+/, a) { print a[1] }' | sort -un | wc -l
```
