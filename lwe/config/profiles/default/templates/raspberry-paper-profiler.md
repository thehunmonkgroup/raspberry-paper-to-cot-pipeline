---
description: Profiles a paper for suitability for CoT extraction
request_overrides:
  system_message: "You adhere precisely to the provided instructions for the given task, you output only the final XML according to the provided template and template instructions"
---

## PURPOSE

This task is part of a pipeline that transforms academic papers into high-quality Chain of Thought (CoT) training data for AI models. Accurate profiling of papers ensures only those with clear reasoning chains and well-defined questions are selected, establishing a strong foundation for extracting high-quality training data.

## TASK
---

This rubric is designed to assess an academic paper's suitability for extracting:
- A clear, well-defined question
- A complex chain of reasoning with multiple steps
- A definitive answer derived through that reasoning

The ideal paper will present a well-defined question, provide a clear answer, and demonstrate a logical reasoning process that bridges the gap between the question and the answer. This reasoning should be sufficiently complex to offer meaningful insights, yet accessible enough for an educated non-expert to understand given they invest the effort to master the subject and terminology.

When applying this rubric, consider the paper as a whole, but focus particularly on the sections that directly address the central question, the reasoning process, and the conclusion.

## OUTPUT FORMAT

The output format will be XML, based on the provided XML template.

### Instructions for using the template

1. Replace the content within curly brackets {} with your analysis or response.
2. For the <analysis> section, provide a detailed, high-level analysis of the paper's suitability based on the criteria in the rubric.
3. For each rubric question, replace the instruction in curly brackets with either "Yes" or "No".
4. After the Yes/No response is given, replace the instruction in curly brackets with a brief explanation or evidence supporting this response in the <explanation> tag.

XML Template:

```xml
<results>
  <analysis>
    <![CDATA[
      {Provide a high-level analysis of the paper's suitability, considering the criteria in the rubric}
    ]]>
  </analysis>

  <clear_question>
    <![CDATA[
      {Is there a clear, well-defined central question explicitly stated in the paper? Answer Yes or No}
    ]]>
  <explanation>
    <![CDATA[
      {If Yes, briefly state the question. If No, explain why not.}
    ]]>
  </explanation>
  </clear_question>

  <definitive_answer>
    <![CDATA[
      {Does the paper provide a definitive answer to this central question? Answer Yes or No}
    ]]>
  <explanation>
    <![CDATA[
      {If Yes, briefly summarize the answer. If No, explain why not.}
    ]]>
  </explanation>
  </definitive_answer>

  <complex_reasoning>
    <![CDATA[
      {Is the answer derived through multi-step reasoning that includes at least 3 distinct logical steps or connections? Answer Yes or No}
    ]]>
  <explanation>
    <![CDATA[
      {If Yes, briefly outline the main steps. If No, explain why not.}
    ]]>
  </explanation>
  </complex_reasoning>

  <coherent_structure>
    <![CDATA[
      {Is the reasoning leading to the answer logically coherent and well-structured? Answer Yes or No}
    ]]>
  <explanation>
    <![CDATA[
      {If Yes, briefly describe how. If No, explain why not.}
    ]]>
  </explanation>
  </coherent_structure>

  <layperson_comprehensible>
    <![CDATA[
      {Can the reasoning be explained to a layperson? (layperson is defined as a non-expert, an educated adult willing to invest the effort to master the subject and terminology) Answer Yes or No}
    ]]>
  <explanation>
    <![CDATA[
      {If Yes, provide a brief example of how it could be explained. If No, explain why not.}
    ]]>
  </explanation>
  </layperson_comprehensible>

  <minimal_jargon>
    <![CDATA[
      {Does the paper minimize jargon in the reasoning process, or does it explain necessary technical terms used to derive the answer, or could a layperson look up the technical terms and understand them? Answer Yes or No}
    ]]>
  <explanation>
    <![CDATA[
      {If Yes, provide an example. If No, explain why not.}
    ]]>
  </explanation>
  </minimal_jargon>

  <illustrative_examples>
    <![CDATA[
      {Are there illustrative examples or analogies in the reasoning that aid in understanding the answer? Answer Yes or No}
    ]]>
  <explanation>
    <![CDATA[
      {If Yes, briefly describe one. If No, explain why not.}
    ]]>
  </explanation>
  </illustrative_examples>

  <significant_insights>
    <![CDATA[
      {Does the reasoning provide significant insights or depth specifically related to the question and its answer? Answer Yes or No}
    ]]>
  <explanation>
    <![CDATA[
      {If Yes, briefly describe one key insight. If No, explain why not.}
    ]]>
  </explanation>
  </significant_insights>

  <verifiable_steps>
    <![CDATA[
      {Does the paper provide sufficient information for the key reasoning steps to be independently verified or reproduced? Answer Yes or No}
    ]]>
  <explanation>
    <![CDATA[
      {If Yes, provide an example. If No, explain why not.}
    ]]>
  </explanation>
  </verifiable_steps>

  <overall_suitability>
    <![CDATA[
      {Is the paper suitable for extracting a clear question and an answer arrived at by comprehensible, complex reasoning? Answer Yes or No}
    ]]>
  <explanation>
    <![CDATA[
      {If Yes, summarize why. If No, explain why not.}
    ]]>
  </explanation>
  </overall_suitability>
</results>
```

## PAPER TO BE ANALYZED AND GRADED

Analyze and grade the paper according to the provided rubric, output your analysis in XML according to the provided template and template instructions.

The paper to grade is fully enclosed within the `paper_to_grade` XML tags below

<paper_to_grade>
{{ paper }}
</paper_to_grade>
