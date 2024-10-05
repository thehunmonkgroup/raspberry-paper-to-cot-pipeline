# Raspberry: Papers to CoT Pipeline

## Overview

The goal is to build a quality pipeline where academic papers go in one end and 'Chain of Thought' (CoT) sets come out the other.

A Chain of Thought set includes:

1. A question *(hopefully clear and answerable)*
2. An answer *(hopefully verifiable)*
3. Multi-step thinking/reasoning necessary to derive the answer from the question *(hopefully accessible to a layperson's understanding)*

The idea is that these academic papers represent the best of how humans reason through tasks, and these extracted Chain of Thought sets can then be used to train AI models to improve their complex reasoning ability.

## Pipeline Workflow

The following diagram illustrates the pipeline workflow:

![Pipeline Diagram](pipeline-diagram.png)

1. **Fetch Papers**: Retrieve academic papers from arXiv.org
2. **Clean Papers**: Verify paper accessibility and remove inaccessible papers
3. **Profile Papers**: Analyze and profile the papers based on specific criteria
   * Store criteria data in database
   * Generate profiling inference artifact
4. **Score Papers**: Assign suitability scores to the papers based on profiling criteria, store in database
5. **Extract CoT**: Extract Chain of Thought sets from the papers.
   * Generate CoT extraction inference artifact
   * Generate training data artifact

## Gathering the Papers

[arXiv.org](https://arxiv.org) provides a ready source of academic papers for this experiment. Papers are extracted from various categories to best represent different types of reasoning.

To ensure we build grounded Chain of Thought sets, the academic papers used are at least two years old. This helps prevent the model from encountering truly novel data that it hasn't been trained on, thereby reducing the risk of hallucinations.

### arXiv.org Categories

To see the list of default categories used and the default filter dates:

```sh
scripts/fetch-papers.py --config
```

### Fetching Papers

To start the paper extraction process:

```sh
scripts/fetch-papers.py
```

## Running the Pipeline

1. Install [LWE](https://llm-workflow-engine.readthedocs.io/en/latest/installation.html) and any needed [provider plugins](https://llm-workflow-engine.readthedocs.io/en/latest/plugins.html#provider-plugins)
2. [Configure](https://llm-workflow-engine.readthedocs.io/en/latest/initial_setup.html) any needed API keys for the models used in the pipeline
3. Clone this repository
4. From the root of the repository
   * Fetch papers as described above
   * Start the CLI
     ```sh
     ./cli.sh
     ```
5. Clean the papers
   ```sh
   python scripts/clean-paper-urls.py
   ```
   `--limit`: The number of papers to clean in one run (optional)
6. Profile the papers
   ```sh
   /workflow run raspberry-paper-profiler limit=1000
   ```
   `order_by`: How to order the papers when retrieving from the database (default `RANDOM()`)
   `limit`: The number of papers to profile in one run (default: `1`)
7. Score the papers
   ```sh
   /workflow run raspberry-paper-scorer limit=1000
   ```
   `limit`: The number of papers to profile in one run (default: `1`)
8. Extract CoT from the papers
   ```sh
   /workflow run raspberry-paper-to-cot-extraction limit=1000 suitability_score=10
   ```
   `limit`: The number of papers to profile in one run (default: `1`)
   `suitability_score` is the minimum suitability score needed, papers with a lower score are ignored (range `3-10`, default: `8`)
9. All artifacts are output to the `results` directory in the root of the repository
