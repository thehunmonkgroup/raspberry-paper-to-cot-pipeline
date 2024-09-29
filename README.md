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

### Extract papers

```sh
scripts/fetch-papers.sh
```

Count of unique papers across categories:

```sh
cat papers/* | awk 'match($0, /([0-9]+\.[0-9]+)v[0-9]+/, a) { print a[1] }' | sort -un | wc -l
```
