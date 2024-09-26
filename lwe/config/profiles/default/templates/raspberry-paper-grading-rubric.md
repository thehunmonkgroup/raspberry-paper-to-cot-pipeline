## TASK

This rubric is designed to assess an academic paper's suitability for extracting a clear question with an answer derived through complex, multi-step reasoning that is comprehensible to a layperson with some effort. The ideal paper will present a well-defined question, provide a clear answer, and demonstrate a logical reasoning process that bridges the gap between the question and the answer. This reasoning should be sufficiently complex to offer meaningful insights, yet accessible enough for an educated non-expert to understand with some effort.

When applying this rubric, consider the paper as a whole, but focus particularly on the sections that directly address the central question, the reasoning process, and the conclusion.

## OUTPUT FORMAT

The output format will be XML, based on the provided XML template.

### Instructions for using the template

1. Replace the content within curly brackets {} with your analysis or response.
2. For the <analysis> section, provide a detailed, high-level analysis of the paper's suitability based on the criteria in the rubric.
3. For each rubric question, replace the instruction in curly brackets with either "Yes" or "No".
4. If a "Yes" response is given, replace the instruction in curly brackets with a brief explanation or evidence supporting this response in the <explanation> tag. If the response is "No", you may leave the <explanation> tag empty or provide a brief reason for the "No" response.

XML Template:

```xml
<results>
  <analysis>
  {Provide a high-level analysis of the paper's suitability, considering the criteria in the rubric}
  </analysis>

  <clear_question>
  {Is there a clear, well-defined central question explicitly stated in the paper?}
  <explanation>
  {If Yes, briefly state the question. If No, explain why not.}
  </explanation>
  </clear_question>

  <definitive_answer>
  {Does the paper provide a definitive answer to this central question?}
  <explanation>
  {If Yes, briefly summarize the answer. If No, explain why not.}
  </explanation>
  </definitive_answer>

  <complex_reasoning>
  {Is the answer derived through multi-step reasoning that includes at least 3 distinct logical steps or connections?}
  <explanation>
  {If Yes, briefly outline the main steps. If No, explain why not.}
  </explanation>
  </complex_reasoning>

  <coherent_structure>
  {Is the reasoning leading to the answer logically coherent and well-structured?}
  <explanation>
  {If Yes, briefly describe how. If No, explain why not.}
  </explanation>
  </coherent_structure>

  <layperson_comprehensible>
  {Can the reasoning be explained to a layperson (defined as an educated adult without specific expertise in the paper's field) with some effort?}
  <explanation>
  {If Yes, provide a brief example of how it could be explained. If No, explain why not.}
  </explanation>
  </layperson_comprehensible>

  <minimal_jargon>
  {Does the paper minimize jargon in the reasoning process, or does it explain necessary technical terms used to derive the answer?}
  <explanation>
  {If Yes, provide an example. If No, explain why not.}
  </explanation>
  </minimal_jargon>

  <illustrative_examples>
  {Are there illustrative examples or analogies in the reasoning that aid in understanding the answer?}
  <explanation>
  {If Yes, briefly describe one. If No, explain why not.}
  </explanation>
  </illustrative_examples>

  <significant_insights>
  {Does the reasoning provide significant insights or depth specifically related to the question and its answer?}
  <explanation>
  {If Yes, briefly describe one key insight. If No, explain why not.}
  </explanation>
  </significant_insights>

  <verifiable_steps>
  {Does the paper provide sufficient information for the key reasoning steps to be independently verified or reproduced?}
  <explanation>
  {If Yes, provide an example. If No, explain why not.}
  </explanation>
  </verifiable_steps>

  <overall_suitability>
  {Is the paper suitable for extracting a clear question and an answer arrived at by comprehensible, complex reasoning?}
  <explanation>
  {If Yes, summarize why. If No, explain why not.}
  </explanation>
  </overall_suitability>
</results>
```

## PAPER TO BE ANALYZED AND GRADED

Analyze and grade the following paper according to the provided rubric, output your analysis in XML according to the provided template and template instructions:

{{ paper }}
