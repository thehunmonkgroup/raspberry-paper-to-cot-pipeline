# Raspberry: Papers to CoT Pipeline

## Overview

The goal is to build a quality pipeline where academic papers go in one end and 'Chain of Thought' (CoT) sets come out the other.

A Chain of Thought set includes:

1. A question *(hopefully clear and answerable)*
2. An answer *(hopefully verifiable)*
3. Multi-step thinking/reasoning necessary to derive the answer from the question *(hopefully accessible to a layperson's understanding)*

The idea is that these academic papers represent the best of how humans reason through tasks, and these extracted Chain of Thought sets can then be used to train AI models to improve their complex reasoning ability.

## Installation

1. Install [LLM Workflow Engine](https://llm-workflow-engine.readthedocs.io/en/latest/installation.html)
2. Install the following LWE plugins:
   * [Chat Anthropic](https://github.com/llm-workflow-engine/lwe-plugin-provider-chat-anthropic)
   * Any other [Provider plugins](https://llm-workflow-engine.readthedocs.io/en/latest/plugins.html#provider-plugins) needed depending on the models you'll want to use
3. [Configure](https://llm-workflow-engine.readthedocs.io/en/latest/initial_setup.html) any needed API keys for the models used in the pipeline
4. Clone this repository, change directory into the root
5. Install the package:
   ```sh
   pip install -e .
   ```

## Pipeline Workflow

*NOTE: All scripts described below can be run with the `--help` argument for a full list of options*

The following diagram illustrates the pipeline workflow:

![Pipeline Diagram](misc/pipeline-diagram.svg)

1. **raspberry-fetch-paper-urls**: Retrieve academic papers from arXiv.org
2. **raspberry-clean-paper-urls**: Verify paper accessibility and remove inaccessible papers
3. **raspberry-paper-profiler**: Analyze and profile the papers based on specific criteria, store criteria data in database

   Artifacts generated:
   * Profiling inference artifact
4. **raspberry-paper-profile-scorer**: Assign suitability scores to the papers based on profiling criteria, store in database
5. **raspberry-paper-cot-extractor**: Extract Chain of Thought sets from the papers through a three-stage process:
   * Initial Extraction: Generate initial question, reasoning chain and answer
   * Critique: Analyze and critique the initial extraction
   * Refinement: Improve the CoT based on critique feedback

   Artifacts generated:
   * Initial extraction inference artifact
   * Critique inference artifact
   * Refinement inference artifact
   * Training data artifact in JSONL format
6. **raspberry-cot-quality-assessor**: Assess the quality of the refined Chain of Thought sets from the papers based on specific criteria, store criteria in the database
6. **raspberry-cot-quality-scorer**: Assign suitability scores to the refined Chain of Thought sets based on quality assessment criteria, store in database
7. **raspberry-generate-training-data**: Compile the final training data from the individual training artifacts, filtering out invalid Chain of Thought sets based on their quality assessment score

   Artifacts generated:
   * Final training data in JSONL format

## Gathering the Papers

[arXiv.org](https://arxiv.org) provides a ready source of academic papers for this experiment. Papers are extracted from various categories to best represent different types of reasoning.

To ensure we build grounded Chain of Thought sets, the academic papers used are at least two years old. This helps prevent the model from encountering truly novel data that it hasn't been trained on, thereby reducing the risk of hallucinations.

### arXiv.org Categories

To see the list of default categories used and the default filter dates:

```sh
raspberry-fetch-paper-urls --config
```

### Fetching Papers

To start the paper extraction process:

```sh
raspberry-fetch-paper-urls
```

*NOTE: The default configuration downloads **a lot** of URLs! Run the script with `--help` for options to control the links that are retrieved.*

## Running the Pipeline

1. Fetch papers as described above
2. Clean the papers
   ```sh
   raspberry-clean-paper-urls
   ```

   Cleaning can take a long time if you've downloaded a lot of links. The cleaning process is not strictly necessary (its purpose is to verify that the PDF for a paper is actually available), if you'd like to skip it, run the script with the `--skip-cleaning` argument.
3. Run the rest of the pipeline
   ```sh
   raspberry-paper-cot-pipeline
   ```

   This runs the rest of the pipeline scripts with default arguments. For more control, you can also run each script individually:

   ```sh
   raspberry-paper-profiler
   raspberry-paper-profile-scorer
   raspberry-paper-cot-extractor
   raspberry-cot-quality-assessor
   raspberry-cot-quality-scorer
   raspberry-generate-training-data
   ```

All artifacts are output to the `results` directory in the root of the repository
