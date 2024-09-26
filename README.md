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

1. cs.AI (Artificial Intelligence)
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
```
