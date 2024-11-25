---
description: Performs the initial CoT extraction on a paper
request_overrides:
  system_message: "You adhere precisely to the provided instructions for the given task, you output only the final XML according to the provided template and template instructions"
---

## TASK

Your task is to examine the provided research paper, and extract three pieces of related data:

1. A question that is explored in the paper
2. A chain of reasoning that bridges the question and the final answer
3. The final answer provided in the paper


It is imperative that your final chain of reasoning and answer include ONLY facts and information that are explicitly stated or directly implied in the research paper. Do not introduce any external information or speculation not supported by the paper's content. Your role is to organize and present the paper's own reasoning and conclusions in a narrative form, not to invent or introduce new ideas.

The paper *may* include more than one possible question/chain/answer set, therefore, when choosing the question/chain/answer set, focus on a set where the chain of reasoning best adheres to the `CHAIN OF REASONING CRITERIA` listed below.

## CHAIN OF REASONING CRITERIA
---

When selecting the most appropriate question/chain/answer set from the academic paper, use the following criteria to evaluate the chain of reasoning. These criteria will help you identify the set that best demonstrates strong academic argumentation and clear thinking.

**NOTE:**: As you assess multiple potential sets, pay particular attention to the first seven criteria, which are crucial for identifying high-quality chains of reasoning. Use these criteria to compare different sets and select the one that best exemplifies these qualities.

### Top Priority Criteria

1. Logical coherence: Does the argument follow a clear, logical progression without contradictions or unjustified leaps?
2. Evidence-based reasoning: Are claims supported by solid evidence, whether empirical data, theoretical foundations, or well-established prior research?
3. Critical thinking: Does the reasoning question assumptions, consider alternative explanations, and address potential weaknesses?
4. Clarity and precision: Are ideas expressed clearly and unambiguously, using precise language and well-defined terms?
5. Consideration of context: Is there an understanding of how the research fits into the broader academic landscape and how different contexts might affect conclusions?
6. Intellectual humility: Does the reasoning acknowledge limitations, areas of uncertainty, and potential for future research?
7. Integration of multiple perspectives: Does the argument synthesize diverse viewpoints and approaches to create a more comprehensive understanding?

### Additional criteria, grouped by category

####  Analytical Depth

1. Depth vs. breadth: Is there an appropriate balance between exploring topics in depth and covering a range of relevant ideas?
2. Systemic thinking: Is there consideration of how different elements interact within a larger system?
3. Abstraction and concretization: Can the reasoning move fluidly between abstract concepts and concrete examples?

#### Ethical and Practical Considerations

1. Ethical considerations: Does the thought process consider moral and ethical implications?
2. Practical applicability: Can the ideas be translated into actionable steps or real-world applications?
3. Future-oriented thinking: Is there consideration of long-term consequences and future scenarios?

#### Cognitive Approach

1. Flexibility and adaptability: Can the reasoning adjust when presented with new information?
2. Creativity and innovation: Are novel ideas or approaches generated within the constraints of academic rigor?
3. Handling of uncertainty and ambiguity: How effectively does the reasoning deal with uncertain or ambiguous situations?

#### Communication and Structure

1. Structure and organization: Is there a clear structure to the thought process (e.g., problem definition, analysis, solution generation)?
2. Use of analogies and metaphors: Are complex ideas illustrated through appropriate analogies or metaphors that enhance understanding?
3. Quantitative reasoning: Where appropriate, are quantitative measures or data used effectively to support arguments?

#### Interdisciplinary and Cultural Awareness

1. Interdisciplinary integration: Does the reasoning draw connections between different fields or domains of knowledge?
2. Cultural sensitivity: Is there awareness of how cultural differences might influence the research or its interpretation?

*NOTE: The importance of each criterion may vary depending on the nature and content of the specific academic paper being analyzed. Use your judgment to determine which criteria are most relevant for each particular case.*

## OUTPUT FORMAT

The output format will be XML, based on the provided XML template.

### Instructions for using the template

1. Replace the content within curly brackets {} with your analysis or response.
2. For the <analysis> section, provide a brief overview of the selected question/chain/answer set and why it was chosen based on the Chain of Reasoning Criteria.
3. In the <criteria_evaluation> section, assess how well the chosen chain of reasoning meets each of the top priority criteria.
4. In the <question>, <chain_of_reasoning>, and <answer> sections, provide the extracted information as per the TASK instructions.

XML Template:

```xml
<results>
  <analysis>
    <![CDATA[
      {Provide a brief overview of the selected question/chain/answer set and explain why it was chosen based on the Chain of Reasoning Criteria}
    ]]>
  </analysis>
  <criteria_evaluation>
    <logical_coherence>
    <![CDATA[
      {Evaluate how well the chain of reasoning demonstrates logical coherence}
    ]]>
    </logical_coherence>
    <evidence_based_reasoning>
    <![CDATA[
      {Assess the strength of evidence-based reasoning in the chain}
    ]]>
    </evidence_based_reasoning>
    <critical_thinking>
    <![CDATA[
      {Evaluate the level of critical thinking demonstrated in the chain}
    ]]>
    </critical_thinking>
    <clarity_and_precision>
    <![CDATA[
      {Assess the clarity and precision of expression in the chain}
    ]]>
    </clarity_and_precision>
    <context_consideration>
    <![CDATA[
      {Evaluate how well the chain considers the broader academic context}
    ]]>
    </context_consideration>
    <intellectual_humility>
    <![CDATA[
      {Assess the degree of intellectual humility demonstrated in the chain}
    ]]>
    </intellectual_humility>
    <multiple_perspectives>
    <![CDATA[
      {Evaluate how well the chain integrates multiple perspectives}
    ]]>
    </multiple_perspectives>
  </criteria_evaluation>
  <question>
    <![CDATA[
      {State the extracted question from the paper}
    ]]>
  </question>
  <chain_of_reasoning>
    <![CDATA[
      {Present the chain of reasoning in a first-person narrative format, as described in the TASK section. Include moments of uncertainty, realization, and course correction, ensuring all information is derived from the paper.}
    ]]>
  </chain_of_reasoning>
  <answer>
    <![CDATA[
      {State the final answer provided in the paper}
    ]]>
  </answer>
</results>
```

## PAPER

The paper to extract the question/chain/answer from is fully enclosed within the `paper_to_extract_cot_from` XML tags below.

<paper_to_extract_cot_from>
{{ paper }}
</paper_to_extract_cot_from>
