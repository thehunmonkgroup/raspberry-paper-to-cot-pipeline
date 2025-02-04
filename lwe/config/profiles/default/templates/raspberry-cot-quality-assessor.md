---
description: Final quality filter for refined CoT extractions
request_overrides:
  system_message: "You adhere precisely to the provided instructions for the task, you output only the final XML according to the provided template and template instructions"
---

## PURPOSE

This task is part of a pipeline that transforms academic papers into high-quality Chain of Thought (CoT) training data for AI models. Quality assessment of the refined chains of thought ensures only the most suitable examples are selected for the final training data, maintaining high standards for logical reasoning and factual accuracy.

## TASK

Your task is to perform the final quality assessment of a question, chain of reasoning, and answer set extracted from an academic paper. This assessment must verify that the set is:
1. Completely and accurately grounded in the source paper
2. Logically sound and well-structured
3. Suitable for AI training purposes

Your evaluation must be rigorous and precise, focusing solely on the content's fidelity to the paper, logical integrity, and suitability for training purposes.

### EVALUATION APPROACH
---

Your evaluation should:
1. Analyze the question/chain of reasoning/answer set against the academic paper in detail.
2. Provide binary (Yes/No) assessments across multiple specific criteria.
3. Focus particularly on:
   - Presence of any content not found in the paper.
   - Missing critical information from the paper.
   - Accuracy of representation of the paper's content.
   - Logical integrity of the chain of reasoning.
   - Structural quality and consistency.

Each criterion must be evaluated independently and supported by specific evidence from the academic paper.

**Important Notes:**
- At this stage, the chain of reasoning and answer **may include references to the paper**, such as mentioning "the paper," "the authors," or using phrases like "according to the study."
- The chain of reasoning and answer **may be written in either first-person or third-person narrative**.
- These aspects will be addressed in a subsequent stage, and should be ignored for the purposes of the evaluation and suitability for training purposes. 

### EVALUATION PROCESS

1. Read and understand the source academic paper
2. Carefully examine the question/chain of reasoning/answer set
3. Compare the set against the paper for accuracy and completeness
4. Evaluate each criterion independently
5. Provide detailed reasoning in the analysis section
6. Give clear Yes/No answers for each specific criterion

## OUTPUT FORMAT

The output format will be XML, based on the provided XML template.

### Instructions for using the template

1. Replace the content within curly brackets {} with your analysis or response.
2. For the `<analysis>` section, provide detailed reasoning for your evaluation of each criterion, focusing on content accuracy, logical progression, and completeness. **Do not mention or penalize** references to the paper or narrative voice styles.
3. For each rubric question, replace the instruction in curly brackets with either "Yes" or "No".
4. After the Yes/No response is given, replace the instruction in curly brackets with a brief explanation or evidence supporting this response in the <explanation> tag.

XML Template:

```xml
<results>
  <analysis>
    <![CDATA[
      {Provide detailed reasoning for each evaluation point, explaining how the question/chain of reasoning/answer set meets or fails to meet each criterion. You MUST explicitly identify any instances where the set references "the paper", "the authors", "the study", uses phrases like "according to" or "the research shows", or indicates the information comes from a written document - these are critical failures that must be highlighted first in your analysis.}
    ]]>
  </analysis>

  <source_fidelity>
    <contains_only_paper_content>
      <![CDATA[
        {Does the question/chain of reasoning/answer set contain ONLY facts and reasoning present in the paper, with no external knowledge introduced? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, confirm all content is from the paper. If No, identify the external knowledge introduced.}
      ]]>
      </explanation>
    </contains_only_paper_content>
    <includes_all_critical_info>
      <![CDATA[
        {Does the question/chain of reasoning/answer set include ALL critical information needed to support the reasoning chain? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, outline the key information included. If No, identify what critical information is missing.}
      ]]>
      </explanation>
    </includes_all_critical_info>
    <accurate_representation>
      <![CDATA[
        {Does the question/chain of reasoning/answer set accurately represent the paper's methodology and conclusions? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, explain how it accurately represents the paper. If No, identify the misrepresentations.}
      ]]>
      </explanation>
    </accurate_representation>
    <technical_accuracy>
      <![CDATA[
        {Does the set maintain consistent technical accuracy with the paper's definitions and terms? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, confirm the technical accuracy. If No, identify any technical inconsistencies.}
      ]]>
      </explanation>
    </technical_accuracy>
  </source_fidelity>

  <reasoning_integrity>
    <steps_supported_by_paper>
      <![CDATA[
        {Is each step in the reasoning chain explicitly supported by content from the paper? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, confirm how each step is supported. If No, identify which steps lack support.}
      ]]>
      </explanation>
    </steps_supported_by_paper>
    <no_logical_leaps>
      <![CDATA[
        {Is the reasoning chain free from logical leaps or unstated assumptions? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, confirm the logical continuity. If No, identify the logical leaps or unstated assumptions.}
      ]]>
      </explanation>
    </no_logical_leaps>
    <correct_sequence>
      <![CDATA[
        {Are the reasoning steps presented in correct sequential order? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, confirm the sequence is logical. If No, identify where the sequence breaks down.}
      ]]>
      </explanation>
    </correct_sequence>
    <conclusion_follows>
      <![CDATA[
        {Does the conclusion follow directly from the presented reasoning steps? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, explain how the conclusion follows. If No, identify the disconnect.}
      ]]>
      </explanation>
    </conclusion_follows>
  </reasoning_integrity>

  <training_utility>
    <question_answerable>
      <![CDATA[
        {Is the question clearly answerable from the paper's content? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, explain how the paper provides the necessary information. If No, explain what information is missing.}
      ]]>
      </explanation>
    </question_answerable>
    <question_properly_formatted>
      <![CDATA[
        {Examining ONLY the question itself: Is it free from meta-references to documentation (like "the paper", "the study", "the authors")? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, confirm the question discusses the subject matter directly without meta-references. If No, identify the problematic meta-references in the question.}
      ]]>
      </explanation>
    </question_properly_formatted>
    <multi_step_progression>
      <![CDATA[
        {Does the chain of reasoning demonstrate clear multi-step logical progression? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, outline the key progression steps. If No, explain where progression breaks down.}
      ]]>
      </explanation>
    </multi_step_progression>
    <answer_addresses_question>
      <![CDATA[
        {Does the answer directly address the initial question? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, explain how it addresses the question. If No, identify the mismatch.}
      ]]>
      </explanation>
    </answer_addresses_question>
    <appropriate_complexity>
      <![CDATA[
        {Is the reasoning complexity appropriate (neither trivial nor unnecessarily complex)? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, explain why the complexity level is appropriate. If No, explain if it's too simple or too complex.}
      ]]>
      </explanation>
    </appropriate_complexity>
  </training_utility>

  <structural_quality>
    <terms_explained>
      <![CDATA[
        {Are all technical terms used properly explained? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, confirm the terms are explained adequately. If No, identify unexplained terms.}
      ]]>
      </explanation>
    </terms_explained>
    <no_contradictions>
      <![CDATA[
        {Is the set free from internal contradictions or inconsistencies? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, confirm the consistency. If No, identify the contradictions.}
      ]]>
      </explanation>
    </no_contradictions>
    <complete_flow>
      <![CDATA[
        {Is there complete logical flow from question through reasoning to answer? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, describe the flow. If No, identify where the flow breaks down.}
      ]]>
      </explanation>
    </complete_flow>
  </structural_quality>
</results>
```

## PAPER

The source academic paper is fully enclosed within the `reference_paper_for_filtering` XML tags below.

<reference_paper_for_filtering>
{{ paper }}
</reference_paper_for_filtering>

## QUESTION/CHAIN OF REASONING/ANSWER TO FILTER

The question, chain of reasoning, and answer to filter is fully enclosed within the `question_chain_of_reasoning_answer_to_filter` XML tags below.

<question_chain_of_reasoning_answer_to_filter>

Question:

{{ question }}

Chain of reasoning:

{{ chain_of_reasoning }}

Answer:

{{ answer }}
</question_chain_of_reasoning_answer_to_filter>
