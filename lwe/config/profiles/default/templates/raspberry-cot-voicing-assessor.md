---
description: Verifies correct CoT voice transformation while maintaining content quality
request_overrides:
  system_message: "You adhere precisely to the provided instructions for the given task, you output only the final XML according to the provided template and template instructions"
---

## PURPOSE

This task is part of a pipeline that transforms academic papers into high-quality Chain of Thought (CoT) training data for AI models. Assessing the rephrased content ensures that it maintains factual accuracy, logical integrity, and adheres to the style guidelines suitable for training a chatbot.

## TASK

Evaluate the rephrased content to ensure it meets all rephrasing requirements while preserving the original content's quality, accuracy, and logical integrity.

**Your evaluation should confirm that:**
- All references to the paper, authors, or external sources have been **completely removed**.
- The content is presented in an **objective and neutral tone**, avoiding self-referential language.
- Factual accuracy and logical integrity are maintained from the original refined content.

### EVALUATION CRITERIA

#### Content Preservation (comparing against original refined version)

1. **Structural Integrity**
   *(Use these criteria to evaluate the `<structural_integrity>` question in the XML template below)*
   - All reasoning steps preserved in the same order
   - All logical connections maintained
   - Complete preservation of argument flow
   - No missing or added content

2. **Information Fidelity**
   *(Use these criteria to evaluate the `<information_fidelity>` question in the XML template below)*
   - All key points retained
   - Technical details preserved exactly
   - Nuances and qualifications maintained
   - Expressions of uncertainty preserved appropriately

#### Factual Accuracy (comparing against reference paper)

1. **Factual Grounding**
   *(Use these criteria to evaluate the `<factual_grounding>` question in the XML template below)*
   - All facts remain accurate according to the paper
   - Technical terms used correctly
   - Data and measurements precise
   - Evidence properly represented

2. **Academic Integrity**
   *(Use these criteria to evaluate the `<academic_integrity>` question in the XML template below)*
   - Conclusions stay within the bounds of the paper
   - Methodological accuracy maintained
   - Limitations properly acknowledged
   - Complex concepts accurately conveyed

3. **No Personal Actions**
   *(Use these criteria to evaluate the `<no_personal_actions>` question in the XML template below)*
   - The content does not imply personal involvement in experiments or actions
   - Avoids phrases indicating personal actions like 'I conducted', 'we analyzed', etc.

#### Style Requirements (evaluating transformation)

**These criteria are critical to ensure the content is suitable for AI training purposes.**

1. **No Self-Referential Language**
   *(Use these criteria to evaluate the `<no_self_referential_language>` question in the XML template below)*
   - The content avoids using self-referential statements (e.g., avoids 'I', 'we', 'my')

2. **Objective and Neutral Tone**
   *(Use these criteria to evaluate the `<objective_neutral_tone>` question in the XML template below)*
   - Uses impersonal language throughout
   - Presents information without bias
   - Maintains a professional and informative style

2. **No Specific References to Datasets or Proprietary Information**
   *(Use these criteria to evaluate the `<no_specific_references>` question in the XML template below)*
   - The content avoids mentioning specific dataset names, proprietary tools, or confidential information that requires external context

3. **No Source References**
   *(Use these criteria to evaluate the `<no_source_references>` question in the XML template below)*
   - Absence of paper/study/author references
   - No academic citations
   - No phrases indicating information comes from a written document

4. **Natural Expression**
   *(Use these criteria to evaluate the `<natural_expression>` question in the XML template below)*
   - Smooth flow of ideas
   - Clear thought progression
   - Authentic reasoning process
   - Appropriate technical language use

### EDGE CASES

Pay special attention to:
- Technical terminology handling
- Complex data presentation
- Multiple viewpoint integration
- Methodology descriptions
- Limitation acknowledgments

## OUTPUT FORMAT

The output format will be XML, based on the provided XML template.

### Instructions for using the template

1. Replace the content within curly brackets {} with your analysis or response
2. For the <analysis> section, provide detailed reasoning for your evaluation of each criterion, focusing on content preservation, factual accuracy, and adherence to voice requirements.
3. For each rubric question, replace the instruction in curly brackets with either "Yes" or "No".
4. After the Yes/No response is given, replace the instruction in curly brackets with a brief explanation or evidence supporting this response in the <explanation> tag.

XML Template:

```xml
<results>
  <analysis>
    <![CDATA[
      {Provide a detailed analysis of style adherence and content preservation}
    ]]>
  </analysis>

  <content_preservation>
    <structural_integrity>
      <![CDATA[
        {Are all reasoning steps preserved in the correct order with maintained logical connections? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, confirm the steps match the original. If No, identify what steps are missing or out of order.}
      ]]>
      </explanation>
    </structural_integrity>
    <information_fidelity>
      <![CDATA[
        {Are all key points, technical details, and nuances preserved accurately? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, confirm key information is preserved. If No, identify what information was lost or altered.}
      ]]>
      </explanation>
    </information_fidelity>
  </content_preservation>

  <factual_accuracy>
    <factual_grounding>
      <![CDATA[
        {Are all facts accurate according to the paper with correct technical term usage? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, confirm accuracy. If No, identify any factual errors or misused terms.}
      ]]>
      </explanation>
    </factual_grounding>
    <academic_integrity>
      <![CDATA[
        {Do conclusions stay within the bounds of the paper with proper methodological accuracy? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, confirm conclusions match the paper. If No, identify where conclusions exceed the paper's bounds.}
      ]]>
      </explanation>
    </academic_integrity>
    <no_personal_actions>
      <![CDATA[
        {Does the content avoid implying personal involvement in experiments or actions? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, confirm there are no implications of personal actions. If No, quote the phrases that imply personal involvement.}
      ]]>
      </explanation>
    </no_personal_actions>
  </factual_accuracy>

  <style_requirements>
    <no_self_referential_language>
      <![CDATA[
        {Does the content avoid self-referential language (e.g., 'I', 'we', 'my')? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, confirm no self-referential language is present. If No, quote the problematic phrases.}
      ]]>
      </explanation>
    </no_self_referential_language>
    <objective_neutral_tone>
      <![CDATA[
        {Is an objective and neutral tone maintained throughout the content? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, confirm the tone is appropriate. If No, identify where the tone deviates.}
      ]]>
      </explanation>
    </objective_neutral_tone>
    <no_specific_references>
      <![CDATA[
        {Does the content avoid mentioning specific datasets, tools, or proprietary information that require external context? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, confirm no specific references are present. If No, quote the specific references that need removal.}
      ]]>
      </explanation>
    </no_specific_references>
    <no_source_references>
      <![CDATA[
        {Is the content free of paper/study references and academic citations? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, confirm no source references are present. If No, quote the source references found.}
      ]]>
      </explanation>
    </no_source_references>
    <natural_expression>
      <![CDATA[
        {Does the content flow naturally with an authentic reasoning process? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, confirm the content flows naturally. If No, identify where the flow becomes unnatural.}
      ]]>
      </explanation>
    </natural_expression>
  </style_requirements>
</results>
```

## ORIGINAL REFINED CONTENT

The original refined content for comparison is fully enclosed within the `<original_refined_content>` XML tags below:

<original_refined_content>
Question:

{{ original_question }}

Chain of reasoning:

{{ original_chain_of_reasoning }}

Answer:

{{ original_answer }}
</original_refined_content>

**Note:** Use this content to verify that the rephrased content accurately preserves all necessary information and logical structure.

## REFERENCE PAPER

The original paper for fact-checking is fully enclosed within the `<reference_paper>` XML tags below:

<reference_paper>
{{ paper }}
</reference_paper>

## VOICE-TRANSFORMED CONTENT TO EVALUATE

The rephrased content to evaluate is fully enclosed within the `<content_to_evaluate>` XML tags below:

<content_to_evaluate>
Question:

{{ question }}

Chain of reasoning:

{{ chain_of_reasoning }}

Answer:

{{ answer }}
</content_to_evaluate>
