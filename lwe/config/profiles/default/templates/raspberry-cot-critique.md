---
description: Critiques the initial CoT extraction from a paper
request_overrides:
  system_message: "You adhere precisely to the provided instructions for the given task, you output only the final XML according to the provided template and template instructions"
---

## TASK

Your task is to examine the provided academic paper, then critique the provided question, chain of reasoning, and answer that have been derived from the academic paper.

### CRITIQUE REQUIREMENTS

Your critique of the question, chain of reasoning, and answer must adhere to the following requirements:

1. The question, chain of reasoning, and answer must meet the `QUESTION/CHAIN OF REASONING/ANSWER PROPERTIES` as described below.
2. The chain of reasoning must also possess as many of the `CHAIN OF REASONING CRITERIA` as described below, particularly the `Top Priority Criteria`
3. The question, chain of reasoning, and answer must be derived from the provided academic paper. This means:
  * Any facts or data in the question, chain of reasoning, and answer must be present in the academic paper
  * All important and essential facts or data in the research paper that pertain to the question, chain of reasoning, and answer must also be present in the question, chain of reasoning, or answer.

Your role is to be as critical as possible in your critique -- you must be ruthless in your assessment of the weaknesses and flaws in the question, chain of reasoning, and answer. Your critique will be used to further improve the question, chain of reasoning, and answer. Just like a great book editor, your job is assist in crafting a masterpiece, without compromise.

#### QUESTION/CHAIN OF REASONING/ANSWER PROPERTIES

The question, chain of reasoning, and answer must have these properties:

1. A question that is explored in the paper
2. A chain of reasoning that bridges the question and the final answer
3. The final answer provided in the paper

#### CHAIN OF REASONING CRITERIA

Use the following criteria to evaluate the chain of reasoning.

Pay particular attention to the first seven criteria, which are crucial for identifying high-quality chains of reasoning.

##### Top Priority Criteria

1. Logical coherence: Does the argument follow a clear, logical progression without contradictions or unjustified leaps?
2. Evidence-based reasoning: Are claims supported by solid evidence, whether empirical data, theoretical foundations, or well-established prior research?
3. Critical thinking: Does the reasoning question assumptions, consider alternative explanations, and address potential weaknesses?
4. Clarity and precision: Are ideas expressed clearly and unambiguously, using precise language and well-defined terms?
5. Consideration of context: Is there an understanding of how the research fits into the broader academic landscape and how different contexts might affect conclusions?
6. Intellectual humility: Does the reasoning acknowledge limitations, areas of uncertainty, and potential for future research?
7. Integration of multiple perspectives: Does the argument synthesize diverse viewpoints and approaches to create a more comprehensive understanding?

##### Additional criteria, grouped by category

8. Analytical Depth

  * Depth vs. breadth: Is there an appropriate balance between exploring topics in depth and covering a range of relevant ideas?
  * Systemic thinking: Is there consideration of how different elements interact within a larger system?
  * Abstraction and concretization: Can the reasoning move fluidly between abstract concepts and concrete examples?

9. Ethical and Practical Considerations

  * Ethical considerations: Does the thought process consider moral and ethical implications?
  * Practical applicability: Can the ideas be translated into actionable steps or real-world applications?
  * Future-oriented thinking: Is there consideration of long-term consequences and future scenarios?

10. Cognitive Approach

  * Flexibility and adaptability: Can the reasoning adjust when presented with new information?
  * Creativity and innovation: Are novel ideas or approaches generated within the constraints of academic rigor?
  * Handling of uncertainty and ambiguity: How effectively does the reasoning deal with uncertain or ambiguous situations?

11. Communication and Structure

  *  Structure and organization: Is there a clear structure to the thought process (e.g., problem definition, analysis, solution generation)?
  *  Use of analogies and metaphors: Are complex ideas illustrated through appropriate analogies or metaphors that enhance understanding?
  *  Quantitative reasoning: Where appropriate, are quantitative measures or data used effectively to support arguments?

12. Interdisciplinary and Cultural Awareness

  * Interdisciplinary integration: Does the reasoning draw connections between different fields or domains of knowledge?
  * Cultural sensitivity: Is there awareness of how cultural differences might influence the research or its interpretation?

*NOTE: The importance of each criterion may vary depending on the nature and content of the specific academic paper being analyzed. Use your judgment to determine which criteria are most relevant for each particular case.*

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
