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

To see the list of default categories used, and the default filter dates:

```sh
scripts/fetch-papers.sh --config
```

### Extract papers

```sh
scripts/fetch-papers.sh
```
