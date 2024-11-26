---
description: Transforms a CoT and answer to a question into first-person narrative voice
request_overrides:
  system_message: "You adhere precisely to the provided instructions for the given task, you output only the final XML according to the provided template and template instructions"
---

## TASK

Given the original question, transform the provided chain of reasoning and answer into a consistent first-person narrative voice while maintaining complete factual accuracy and logical integrity.

### VOICE TRANSFORMATION REQUIREMENTS

The transformed chain of reasoning and answer must:

1. Present all reasoning as direct personal observations and analysis:
- Use "I observe...", "I find...", "My analysis reveals..."
- Show evolving understanding through the reasoning process
- Include moments of realization and course correction
- Express direct engagement with the subject matter

2. NEVER include:
- References to "the paper", "the authors", "the study"
- Phrases like "according to" or "the research shows"
- Any indication that information comes from a written document
- Citations or academic references

3. Maintain perfect factual accuracy:
- Preserve all critical information
- Keep all numerical data and technical details precise
- Maintain the complexity and nuance of arguments
- Retain all supporting evidence

4. Preserve logical integrity:
- Keep all reasoning steps in proper sequence
- Maintain clear connections between concepts
- Preserve the relationship between evidence and conclusions
- Retain the full depth of analysis

### TRANSFORMATION GUIDELINES

1. Converting Paper References:
  - Instead of "The authors found X", use "Looking at the data, I see X"
  - Replace "The paper shows" with "The evidence indicates"
  - Transform "According to the study" into "Based on what I observe"

2. Handling Analysis and Results:
  - Transform data observations into active reasoning:
    Instead of: "Looking at the mass spectrometry results, I can see..."
    Use: "When I examine these molecular patterns, I notice..."

  - Express pattern recognition as real-time insight:
    Instead of: "I notice this investigation examines two factors..."
    Use: "I see two key factors at play here..."

  - Frame statistical analysis as logical deduction:
    Instead of: "When I compare these groups statistically..."
    Use: "Comparing these groups, I can see a significant difference, which suggests..."

  - Present evidence evaluation as active reasoning:
    Instead of: "The presence of these controls helps me confirm..."
    Use: "Given these controlled conditions, I can conclude..."

  - Show analytical progression:
    Instead of: "This approach minimizes bias because..."
    Use: "Considering potential sources of bias, I can see that..."

The key is to position the model as actively thinking through the evidence and reaching conclusions in real-time, as if discovering and explaining insights during the conversation with the user.

3. Multiple Viewpoint Integration:
  - Present different perspectives as they arise in your thinking
  - Show how you evaluate competing explanations
  - Demonstrate real-time consideration of alternatives

4. Maintaining Academic Rigor:
  - Use precise, technical language naturally
  - Show careful consideration of evidence as you reason
  - Express uncertainty when evaluating complex relationships
  - Build conclusions step by step through clear logic

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
      {Explain how you maintained factual accuracy while transforming the voice}
    ]]>
  </analysis>
  <content>
    <chain_of_reasoning>
      <![CDATA[
        {The voice-transformed chain of reasoning}
      ]]>
    </chain_of_reasoning>
    <answer>
      <![CDATA[
        {The voice-transformed answer}
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
