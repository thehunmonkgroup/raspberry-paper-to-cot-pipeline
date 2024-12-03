---
description: Refines the initial CoT extraction from a paper, based on the provided critique
request_overrides:
  system_message: "You adhere precisely to the provided instructions for the given task, you output only the final XML according to the provided template and template instructions"
---

## PURPOSE

This task is part of a pipeline that transforms academic papers into high-quality Chain of Thought (CoT) training data for AI models. Refinement of the extracted chains of thought based on expert critique ensures the training data demonstrates clear, precise reasoning while maintaining complete fidelity to the source material.

## TASK

You will be provided the following:

* An academic paper
* A question, chain of reasoning, and answer that have been derived from the academic paper.
* A critique of the provided question, chain of reasoning, and answer

Using the academic paper as a reference, and the critique as instructive guidance, you will create a refined and improved question, chain of reasoning, and answer.

### REFINEMENT REQUIREMENTS
Your task is to improve the existing question, chain of reasoning, and answer by:
1. Ensuring accuracy to the paper:
   - All facts must be present in the academic paper
   - All relevant information from the paper must be included
   - No external information should be added

2. Addressing the critique:
   - Use the critique as your primary guide for improvements
   - Fix any errors or inaccuracies identified
   - Add missing information noted in the critique
   - Improve clarity where the critique suggests

3. Maintaining essential properties:
   - The question must address a topic explored in the paper
   - The chain of reasoning must clearly connect the question to the answer
   - The answer must reflect conclusions supported by the paper

If any element (question, chain, or answer) needs no refinement based on the critique, keep it unchanged.

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
