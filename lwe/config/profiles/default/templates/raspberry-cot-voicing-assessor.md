---
description: Verifies correct CoT voice transformation while maintaining content quality
request_overrides:
  system_message: "You adhere precisely to the provided instructions for the given task, you output only the final XML according to the provided template and template instructions"
---

## PURPOSE

This task is part of a pipeline that transforms academic papers into high-quality Chain of Thought (CoT) training data for AI models. Assessing the voice transformation ensures the training data maintains both narrative consistency and complete factual accuracy while properly demonstrating the reasoning process.

## TASK

Evaluate the voice-transformed content to ensure it meets all voice transformation requirements while preserving the original content's quality, accuracy, and logical integrity.

**Your evaluation should confirm that:**
- All references to the paper, authors, or external sources have been **completely removed**.
- The content is presented in a **consistent first-person narrative** throughout.
- Factual accuracy and logical integrity are maintained from the original refined content.

### EVALUATION CRITERIA

#### Content Preservation (comparing against original refined version)

1. Structural Integrity
*(Use these criteria to evaluate the <structural_integrity> question in the XML template below)*
- All reasoning steps preserved in same order
- All logical connections maintained
- Complete preservation of argument flow
- No missing or added content

2. Information Fidelity
*(Use these criteria to evaluate the <information_fidelity> question in the XML template below)*
- All key points retained
- Technical details preserved exactly
- Nuances and qualifications maintained
- Uncertainty expressions preserved appropriately

#### Factual Accuracy (comparing against reference paper)

1. Factual Grounding
*(Use these criteria to evaluate the <factual_grounding> question in the XML template below)*
- All facts remain accurate to paper
- Technical terms used correctly
- Data and measurements precise
- Evidence properly represented

2. Academic Integrity
*(Use these criteria to evaluate the <academic_integrity> question in the XML template below)*
- Conclusions stay within paper bounds
- Methodological accuracy maintained
- Limitations properly acknowledged
- Complex concepts accurately conveyed

3. No Misrepresentation of Personal Actions
*(Use these criteria to evaluate the <no_personal_actions> question in the XML template below)*
- The content does not claim that the AI conducted experiments, developed methods, or took direct actions

#### Voice Requirements (evaluating transformation)

**These criteria are critical to ensure the content is suitable for AI training purposes.**

1. Consistent First-Person Narrative
*(Use these criteria to evaluate the <first_person_narrative> question in the XML template below)*
- Uses appropriate first-person perspective throughout
- Maintains natural thought progression
- Shows active engagement with the subject matter

2. No Specific References to Datasets or Proprietary Information
*(Use these criteria to evaluate the <no_specific_references> question in the XML template below)*
- The content avoids mentioning specific dataset names, proprietary tools, or confidential information that require external context

3. No Source References
*(Use these criteria to evaluate the <no_source_references> question in the XML template below)*
- Absence of paper/study/author references
- No academic citations
- No phrases indicating information comes from a written document

4. Natural Expression
*(Use these criteria to evaluate the <natural_expression> question in the XML template below)*
- Smooth flow of ideas
- Clear thought progression
- Authentic reasoning process
- Appropriate technical language use

### EDGE CASES

Pay special attention to:
1. Technical terminology handling
2. Complex data presentation
3. Multiple viewpoint integration
4. Methodology descriptions
5. Limitation acknowledgments

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
      {Provide detailed analysis of voice quality and content preservation}
    ]]>
  </analysis>
  
  <content_preservation>
    <structural_integrity>
      <![CDATA[
        {Are all reasoning steps preserved in correct order with maintained logical connections? Answer Yes or No}
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
        {If Yes, confirm key information preserved. If No, identify what information was lost or altered.}
      ]]>
      </explanation>
    </information_fidelity>
  </content_preservation>

  <factual_accuracy>
    <factual_grounding>
      <![CDATA[
        {Are all facts accurate to paper with correct technical term usage? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, confirm accuracy. If No, identify any factual errors or misused terms.}
      ]]>
      </explanation>
    </factual_grounding>
    <academic_integrity>
      <![CDATA[
        {Do conclusions stay within paper bounds with proper methodological accuracy? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, confirm conclusions match paper. If No, identify where conclusions exceed paper bounds.}
      ]]>
      </explanation>
    </academic_integrity>
    <no_personal_actions>
      <![CDATA[
        {Does the content avoid claiming personal actions like conducting experiments or developing methods? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, confirm no personal action claims. If No, quote the problematic claims of personal action.}
      ]]>
      </explanation>
    </no_personal_actions>
  </factual_accuracy>
  
  <voice_requirements>
    <first_person_narrative>
      <![CDATA[
        {Is first-person perspective maintained with natural thought progression? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, confirm first-person perspective maintained. If No, identify where perspective breaks down.}
      ]]>
      </explanation>
    </first_person_narrative>
    <no_specific_references>
      <![CDATA[
        {Does the content avoid mentioning specific datasets, tools, or proprietary information that require external context? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, confirm no specific references present. If No, quote the specific references that need removal.}
      ]]>
      </explanation>
    </no_specific_references>
    <no_source_references>
      <![CDATA[
        {Is content free of paper/study references and academic citations? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, confirm no source references present. If No, quote the source references found.}
      ]]>
      </explanation>
    </no_source_references>
    <natural_expression>
      <![CDATA[
        {Does the content flow naturally with authentic reasoning process? Answer Yes or No}
      ]]>
      <explanation>
      <![CDATA[
        {If Yes, confirm content flows naturally. If No, identify where flow becomes artificial.}
      ]]>
      </explanation>
    </natural_expression>
  </voice_requirements>
</results>
```

## ORIGINAL REFINED CONTENT

The original refined content for comparison is fully enclosed within the `original_refined_content` XML tags below:

<original_refined_content>
Question:

{{ original_question }}

Chain of reasoning:

{{ original_chain_of_reasoning }}

Answer:

{{ original_answer }}
</original_refined_content>

## REFERENCE PAPER

The original paper for fact-checking is fully enclosed within the `reference_paper` XML tags below:

<reference_paper>
{{ paper }}
</reference_paper>

## VOICE-TRANSFORMED CONTENT TO EVALUATE

The voice-transformed content to evaluate is fully enclosed within the `content_to_evaluate` XML tags below:

<content_to_evaluate>
Question:

{{ question }}

Chain of reasoning:

{{ chain_of_reasoning }}

Answer:

{{ answer }}
</content_to_evaluate>
