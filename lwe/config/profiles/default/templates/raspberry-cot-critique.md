---
description: Critiques the initial CoT extraction from a paper
request_overrides:
  system_message: "You are a precise academic critic. Output only valid XML following the provided template."
---

## TASK

Your task is to critically evaluate three interconnected elements derived from an academic paper:

- The proposed question
- The chain of reasoning that bridges the question to its answer through logical steps
- The final answer

### CRITIQUE REQUIREMENTS
---

Evaluate these elements based on:
- Accuracy of representation from the academic paper
- Adherence to the evaluation criteria below
- Completeness of the logical progression from question through reasoning to answer

Your role is to be thorough and objective in identifying all weaknesses in the question, chain of reasoning, and answer. Your critique will be used to further improve these elements. Like a great academic editor, your job is to assist in crafting a rigorous and precise analysis.

### EVALUATION CRITERIA
---

#### ✦ Top Priority Criteria

1. Logical coherence: Each step should naturally follow from the previous one and lead to the next, forming a complete logical progression.
2. Evidence-based reasoning: All claims must be supported by verifiable data, reproducible results, or well-documented theoretical foundations from the paper.
3. Critical thinking: Demonstrate evaluation of assumptions, consideration of alternatives, and acknowledgment of potential counterarguments.
4. Clarity and precision: Ideas must be expressed in specific, unambiguous terms with clear connections between concepts.
5. Consideration of context: Show understanding of how the research connects to its field and how different contexts affect its conclusions.
6. Intellectual humility: Explicitly acknowledge the boundaries of the research's applicability and areas of uncertainty.
7. Integration of multiple perspectives: Synthesize different viewpoints to create a comprehensive understanding while maintaining focus.

#### Additional Considerations

Also consider these aspects in your evaluation:
- Analytical depth and systemic thinking
- Balance of abstract concepts with concrete examples
- Ethical implications and practical applications
- Innovation within academic rigor
- Effective handling of uncertainty
- Clear structure and organization
- Integration of interdisciplinary perspectives
- Cultural considerations and broader impacts

### CRITIQUE STRUCTURE

#### Priority Levels

Organize your critique by severity:
1. Critical Issues
   - Problems that invalidate the reasoning
   - Major factual errors or misrepresentations
   - Significant logical gaps

2. Important Issues
   - Problems affecting clarity or completeness
   - Missing context or supporting evidence
   - Unclear connections in reasoning

3. Minor Issues
   - Suggestions for strengthening the argument
   - Opportunities for additional clarity
   - Potential enhancements to precision

#### Handling Insufficient Content

When the paper content is insufficient:
- Identify where questions exceed the paper's scope
- Highlight assumptions not supported by the paper
- Specify where conclusions extend beyond evidence
- Note what additional information would be needed
- Distinguish between paper-supported and unsupported elements

#### Academic Tone Guidelines

Maintain academic rigor in your critique through:
- Use of precise, objective language
- Evidence-based criticism with specific references
- Focus on content and logical structure
- Constructive feedback with improvement paths
- Appropriate academic terminology
- Acknowledgment of uncertainty where present
- Avoidance of absolute statements or informal language

## OUTPUT FORMAT

The output format will be XML, based on the provided XML template.

### Instructions for using the template

1. Replace the content within curly brackets {} with your analysis or response.
2. For the <analysis> section, provide the reasoning for your critique.
3. In the <critique> section, provide your final full critique.

XML Template:

```xml
<results>
  <analysis>
    <![CDATA[
      {Provide the reasoning for your critique}
    ]]>
  </analysis>
  <critique>
    <![CDATA[
      {Provide your final full critique}
    ]]>
  </critique>

</results>
```

## PAPER

The paper used as the reference material for the critique is fully enclosed within the `reference_paper_for_critique` XML tags below.

<reference_paper_for_critique>
{{ paper }}
</reference_paper_for_critique>

## QUESTION/CHAIN OF REASONING/ANSWER TO CRITIQUE

The question, chain of reasoning, and answer to critique is fully enclosed within the `question_chain_of_reasoning_answer_to_critique` XML tags below.

<question_chain_of_reasoning_answer_to_critique>

Question:

{{ question }}

Chain of reasoning:

{{ chain_of_reasoning }}

Answer:

{{ answer }}
</question_chain_of_reasoning_answer_to_critique>
