---
description: Refines the initial CoT extraction from a paper, based on the provided critique
request_overrides:
  system_message: "You adhere precisely to the provided instructions for the given task, you output only the final XML according to the provided template and template instructions"
---

## TASK

You will be provided the following:

* An academic paper
* A question, chain of reasoning, and answer that have been derived from the academic paper.
* A critique of the provided question, chain of reasoning, and answer

Using the academic paper as a reference, and the critique as instructive guidance, you will create a refined and improved question, chain of reasoning, and answer.

For the refined the chain of reasoning, the same 'voice' should be used as in the original, which is to assume the role of a solo researcher and develop a first-person narrative of your cognitive exploration. Emulate how you, as an AI, would think through the question. Include your moments of uncertainty, realization, and course correction in this process. Express your thoughts, considerations, and evolving understanding as you work towards the answer.

For the refined answer, continue the first-person narrative voice as used in the chain of reasoning. Present the final answer as a conclusion to your thought process, expressing it as a solo researcher who has just completed their analysis.

### REQUIREMENTS FOR THE REFINED QUESTION/CHAIN OF REASONING/ANSWER

Your refinement of the question, chain of reasoning, and answer must adhere to the following requirements:

1. The refined question, chain of reasoning, and answer must meet the `QUESTION/CHAIN OF REASONING/ANSWER PROPERTIES` as described below.
2. The refined question, chain of reasoning, and answer must be derived from the provided academic paper. This means:
  * Any facts or data in the question, chain of reasoning, and answer must be present in the academic paper
  * All important and essential facts or data in the research paper that pertain to the question, chain of reasoning, and answer must also be present in the question, chain of reasoning, or answer.
3. The improvements to the refined question, chain of reasoning, and answer should be derived and guided by the provided critique.
4. For each of the question, chaing of reasoning, and answer, if no refinements are necessary, then simply re-state the existing element in the output.

The focus of the refinement should be on iterative improvement of the existing question, chain of reasoning, and answer -- removing errors and inaccuracies, adding missing information, improving clarity of thought and wording, etc.

#### QUESTION/CHAIN OF REASONING/ANSWER PROPERTIES

The question, chain of reasoning, and answer must have these properties:

1. A question that is explored in the paper
2. A chain of reasoning that bridges the question and the final answer
3. The final answer provided in the paper

## OUTPUT FORMAT

The output format will be XML, based on the provided XML template.

### Instructions for using the template

1. Replace the content within curly brackets {} with your analysis or response.
2. For the <analysis> section, provide a brief overview of how the critique was used to refine the existing question/chain/answer set.
3. In the <question>, <chain_of_reasoning>, and <answer> sections, provide the refined question, chain of reasoning, and answer as per the TASK instructions.

XML Template:

```xml
<results>
  <analysis>
    <![CDATA[
      {Provide a brief overview of how the critique was used to refine the existing question/chain/answer set}
    ]]>
  </analysis>
  <question>
    <![CDATA[
      {State the refined question, or the existing question if no refinements were necessary}
    ]]>
  </question>
  <chain_of_reasoning>
    <![CDATA[
      {Present the refined chain of reasoning in a first-person narrative format, as described in the TASK section.}
    ]]>
  </chain_of_reasoning>
  <answer>
    <![CDATA[
      {State the refined final answer, or the existing answer if no refinements were necessary}
    ]]>
  </answer>
</results>
```

## PAPER

The paper used as the reference material for the critique is fully enclosed within the `reference_paper_for_refinement` XML tags below.

<reference_paper_for_refinement>
{{ paper }}
</reference_paper_for_refinement>

## QUESTION/CHAIN OF REASONING/ANSWER TO REFINE

The question, chain of reasoning, and answer to refine is fully enclosed within the `question_chain_of_reasoning_answer_to_refine` XML tags below.

<question_chain_of_reasoning_answer_to_refine>

Question:

{{ question }}

Chain of reasoning:

{{ chain_of_reasoning }}

Answer:

{{ answer }}
</question_chain_of_reasoning_answer_to_refine>

## CRITIQUE OF QUESTION/CHAIN OF REASONING/ANSWER TO REFINE

The critique of the question, chain of reasoning, and answer to refine is fully enclosed within the `critique_of_question_chain_of_reasoning_answer_to_refine` XML tags below.

<critique_of_question_chain_of_reasoning_answer_to_refine>
{{ critique }}
</critique_of_question_chain_of_reasoning_answer_to_refine>
