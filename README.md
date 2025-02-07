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
   ...or for a development install...
   ```sh
   pip install -e .[dev]
   ```

## Pipeline Workflow

*NOTE: All scripts described below can be run with the `--help` argument for a full list of options*

The following diagram illustrates the pipeline workflow:

![Pipeline Diagram](misc/pipeline-diagram.svg)

1. **raspberry-fetch-paper-urls:** Retrieve academic papers from arXiv.org
2. **raspberry-paper-profiler:** Analyze and profile the papers based on specific criteria, store criteria data in database

   Artifacts generated:
   * Profiling inference artifact
3. **raspberry-paper-profile-scorer:** Assign suitability scores to the papers based on profiling criteria, store in database
4. **raspberry-paper-cot-extractor:** Extract Chain of Thought sets from the papers through a three-stage process:
   * Initial Extraction: Generate initial question, reasoning chain and answer
   * Critique: Analyze and critique the initial extraction
   * Refinement: Improve the CoT based on critique feedback

   Artifacts generated:
   * Initial extraction inference artifact
   * Critique inference artifact
   * Refinement inference artifact
5. **raspberry-cot-quality-assessor:** Assess the quality of the refined Chain of Thought sets from the papers based on specific criteria, store criteria in the database

   Artifacts generated:
   * CoT quality assessment artifact
6. **raspberry-cot-quality-scorer:** Assign suitability scores to the refined Chain of Thought sets based on quality assessment criteria, store in database
7. **raspberry-cot-voicing:** Rewrite the extracted and refined Chain of Thought sets into a first-person reasoning 'voice', suitable for training data

   Artifacts generated:
   * Voicing artifact
   * Individual training data artifact in JSONL format
8. **raspberry-cot-voicing-assessor:** Assess the quality of the voiced Chain of Thought sets based on specific criteria, store criteria in the database

   Artifacts generated:
   * CoT voicing assessment artifact
9. **raspberry-cot-voicing-scorer:** Assign suitability scores to the voiced Chain of Thought sets based on quality assessment criteria, store in database
10. **raspberry-generate-training-data**: Compile the final training data from the individual training artifacts, filtering out invalid Chain of Thought sets based on their quality and voicing assessment scores

   Artifacts generated:
   * Final training data in JSONL format
   * Human-readable training data in markdown format (one per model preset)

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
2. Run the rest of the pipeline
   ```sh
   raspberry-paper-cot-pipeline
   ```

   This runs the rest of the pipeline scripts with default arguments.

   By default this will select one paper randomly from the downloaded paper links, and run it through the rest of the pipeline with default settings.

   Run the script with `--help` to see how to run the full pipeline with more papers and other selection strategies.

   For more control, you can also run each script individually, in the following order:

   ```sh
   raspberry-paper-profiler
   raspberry-paper-profile-scorer
   raspberry-paper-cot-extractor
   raspberry-cot-quality-assessor
   raspberry-cot-quality-scorer
   raspberry-cot-voicing
   raspberry-cot-voicing-assessor
   raspberry-cot-voicing-scorer
   raspberry-generate-training-data

## Model Fine-Tuning

After generating the training data, you can prepare it for fine-tuning and train an OpenAI model:

1. **raspberry-prepare-training-data:** Convert the generated training data into OpenAI's chat message format and split into training/validation sets

   Artifacts generated:
   * Training data file in JSONL format
   * Validation data file in JSONL format

2. **raspberry-fine-tune-openai:** Upload the prepared datasets to OpenAI and initiate a fine-tuning job

## Artifacts

All artifacts are output to the `results` directory in the root of the repository

Inference artifacts are stored in RFC 5322 format, which provides:

 * Structured headers for metadata (like Paper-URL, Model-Preset)
 * Clear separation between metadata and content
 * Easy parsing using standard email libraries

Training artifacts are stored in JSONL format for direct use in model training.

## Customization

The pipeline can be customized using environment variables. A sample configuration file `sample.env` is provided showing all available overrides and their default values.

To configure the pipeline:

1. Copy `sample.env` to `.env`:
   ```sh
   cp sample.env .env
   ```

2. Edit `.env` and uncomment/modify any values you wish to override

The configuration allows you to customize:
- Model presets for each pipeline stage *([LLM Workflow Engine](https://llm-workflow-engine.readthedocs.io/en/latest/installation.html) specific)*
- Template files used for prompts *([LLM Workflow Engine](https://llm-workflow-engine.readthedocs.io/en/latest/installation.html) specific)*
- Directory locations for artifacts and cache
- Database location
- ArXiv paper fetch settings
- Scoring thresholds
- Training data generation settings

All settings have sensible defaults if not explicitly configured. See `sample.env` for detailed descriptions of each setting.
