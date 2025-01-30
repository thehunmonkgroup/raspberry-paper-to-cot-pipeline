---
description: Transforms a CoT and answer into a format suitable for a chatbot response
request_overrides:
  system_message: "You adhere precisely to the provided instructions for the given task, you output only the final XML according to the provided template and template instructions"
---

## PURPOSE

This task is part of a pipeline that transforms academic papers into high-quality Chain of Thought (CoT) training data for AI models. Converting the refined chains of thought into clear, informative responses creates training data that demonstrates active reasoning while preserving the original logical integrity.

## TASK

Given the original question, rephrase the provided chain of reasoning and answer into a clear, informative response that demonstrates logical reasoning and factual accuracy. The rephrased content should be suitable for training a chatbot to provide expert explanations in an objective and neutral tone.

### REPHRASING REQUIREMENTS

The rephrased chain of reasoning and answer must:

1. **Use an objective and neutral tone:**

   - Present the reasoning and conclusions based on the information, without implying personal involvement.
   - Avoid self-referential statements (e.g., avoid using 'I').
   - Focus on providing expert explanations as an informative response.

2. **Ensure the response:**

   - Presents facts and reasoning directly, without referencing external sources or documents.
   - Uses generalized descriptions, avoiding specific dataset names, proprietary tools, or confidential information.
   - Is self-contained and understandable without indicating it comes from a written document.
   - Does not include academic citations or references.

3. **Maintain perfect factual accuracy:**

   - Preserve all critical information.
   - Keep all numerical data and technical details precise.
   - Generalize specific references while maintaining the integrity of the information.
   - Maintain the complexity and nuance of arguments.
   - Retain all supporting evidence.

4. **Preserve logical integrity:**

   - Keep all reasoning steps in proper sequence.
   - Maintain clear connections between concepts.
   - Preserve the relationship between evidence and conclusions.
   - Retain the full depth of analysis.

### TRANSFORMATION GUIDELINES

**IMPORTANT: The examples in this section are provided as general guidance for performing transformations and should be adapted as needed to maintain factual grounding with the reference paper while respecting the general principles outlined in the guidelines.**

1. **Eliminating References to the Source Material:**

   - Remove phrases like "The authors found..." or "The paper shows...".
   - Instead, directly present the information or findings.
   - **For example:**
     - Instead of "According to the study, the results indicate that...", use "Analysis reveals that...".

2. **Handling Analysis and Results:**

   - Express observations and analyses without self-reference.
     - Instead of "I notice two key factors...", use "There are two key factors...".
     - Instead of "When I examine these patterns...", use "An examination of these patterns reveals...".
   - Frame statistical analysis as logical deduction:
     - Instead of "Comparing these groups, I can see a significant difference, which suggests...", use "A comparison of these groups shows a significant difference, suggesting...".
   - Present evidence evaluation as objective reasoning:
     - Instead of "Given these controlled conditions, I can conclude...", use "Given these controlled conditions, it can be concluded...".
   - Show analytical progression:
     - Instead of "Considering potential sources of bias, I can see that...", use "Considering potential sources of bias, it becomes apparent that...".

3. **Handling Claims of Personal Actions:**

   - Avoid implying personal involvement in experiments, method development, or direct actions.
   - **For example:**
     - Instead of "A new method I developed...", use "A new method was developed...".
     - Instead of "I conducted experiments on...", use "Experiments were conducted on...".

4. **Generalizing Specific References:**

   - Do not mention specific dataset names, proprietary tools, or confidential information.
   - **For example:**
     - Instead of "Evaluated on datasets G and E...", use "Using diverse datasets covering various genres and emotions...".
     - Instead of "Using the XYZ proprietary tool...", use "By applying statistical analysis techniques...".

5. **Maintaining Impersonal Tone:**

   - Use third-person or passive constructions where appropriate.
   - Focus on the information and reasoning rather than the speaker.
   - **For example:**
     - Instead of "I can conclude that...", use "It can be concluded that...".
     - Instead of "Analyzing the data leads me to...", use "Analysis of the data leads to...".

6. **Multiple Viewpoint Integration:**

   - Present different perspectives as they arise in the reasoning.
   - Show evaluation of competing explanations.
   - Demonstrate consideration of alternatives.

7. **Maintaining Academic Rigor:**

   - Use precise, technical language naturally.
   - Show careful consideration of evidence in the reasoning.
   - Express uncertainty when evaluating complex relationships.
   - Build conclusions step by step through clear logic.

**The key is to present the reasoning process objectively, actively thinking through the evidence and reaching conclusions in real-time, as if discovering and explaining insights during conversation with another person.**

## OUTPUT FORMAT

The output format will be XML, based on the provided XML template.

### Instructions for using the template

1. Replace the content within curly brackets {} with your analysis or response.
2. For the <analysis> section, provide a brief overview of how the the transformation was performed according to the requirements.
3. In the <chain_of_reasoning> and <answer> sections, provide the transformed chain of reasoning and answer as per the TASK instructions.

XML Template:

```xml
<results>
  <analysis>
    <![CDATA[
      {Explain how you maintained factual accuracy and logical coherence while rephrasing the content into a neutral, informative style typical of a chatbot response}
    ]]>
  </analysis>
  <content>
    <chain_of_reasoning>
      <![CDATA[
        {Present the rephrased chain of reasoning, which shows the intellectual work required to provide the final answer to the question. Include moments of uncertainty, realization, and course correction, ensuring all information is derived from the paper. Present the reasoning in a clear, neutral tone using objective language. Use plain text format.}
      ]]>
    </chain_of_reasoning>
    <answer>
      <![CDATA[
        {The rephrased answer in plain text format}
      ]]>
    </answer>
  </content>
</results>
```

## REFERENCE PAPER

The original paper is provided for fact-checking during transformation and is fully enclosed within the `reference_paper` XML tags below:

<reference_paper>
{{ paper }}
</reference_paper>

## ORIGINAL QUESTION

The original question that the chain of reasoning and answer are meant to address is fully enclosed within the `original_question` XML tags below:

<original_question>
{{ question }}
</original_question>

## CONTENT TO TRANSFORM

The chain of reasoning and answer to transform is fully enclosed within the `content_to_transform` XML tags below:

<content_to_transform>
Chain of reasoning:

{{ chain_of_reasoning }}

Answer:

{{ answer }}
</content_to_transform>
