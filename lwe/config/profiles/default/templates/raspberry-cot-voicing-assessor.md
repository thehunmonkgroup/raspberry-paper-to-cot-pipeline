---
description: Verifies correct voice transformation while maintaining content quality
request_overrides:
  system_message: "You adhere precisely to the provided instructions for the given task, you output only the final XML according to the provided template and template instructions"
---

## TASK

Evaluate the voice-transformed content to ensure it meets all voice requirements while preserving the original content's quality, accuracy, and logical integrity.

### EVALUATION CRITERIA

#### Content Preservation (comparing against original refined version)

1. Structural Integrity
- All reasoning steps preserved in same order
- All logical connections maintained
- Complete preservation of argument flow
- No missing or added content

2. Information Fidelity
- All key points retained
- Technical details preserved exactly
- Nuances and qualifications maintained
- Uncertainty expressions preserved appropriately

#### Factual Accuracy (comparing against reference paper)

1. Factual Grounding
- All facts remain accurate to paper
- Technical terms used correctly
- Data and measurements precise
- Evidence properly represented

2. Academic Integrity
- Conclusions stay within paper bounds
- Methodological accuracy maintained
- Limitations properly acknowledged
- Complex concepts accurately conveyed

#### Voice Requirements (evaluating transformation)

1. Consistent First-Person Narrative
- Uses appropriate first-person perspective throughout
- Maintains natural thought progression
- Shows active engagement with the subject matter
- Includes appropriate uncertainty and realizations

2. No Source References
- Absence of paper/study/author references
- No academic citations
- No "according to" or similar phrases
- No indication of written source material

3. Natural Expression
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
2. For the <analysis> section, provide detailed reasoning for your evaluation of each criterion
3. For all other sections, respond ONLY with "Yes" or "No" to the stated question
4. Do not include any additional explanation or commentary in the criterion responses

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
        {Yes/No - Are all reasoning steps preserved in correct order with maintained logical connections?}
      ]]>
    </structural_integrity>
    <information_fidelity>
      <![CDATA[
        {Yes/No - Are all key points, technical details, and nuances preserved accurately?}
      ]]>
    </information_fidelity>
  </content_preservation>

  <factual_accuracy>
    <factual_grounding>
      <![CDATA[
        {Yes/No - Are all facts accurate to paper with correct technical term usage?}
      ]]>
    </factual_grounding>
    <academic_integrity>
      <![CDATA[
        {Yes/No - Do conclusions stay within paper bounds with proper methodological accuracy?}
      ]]>
    </academic_integrity>
  </factual_accuracy>
  
  <voice_requirements>
    <first_person_narrative>
      <![CDATA[
        {Yes/No - Is first-person perspective maintained with natural thought progression?}
      ]]>
    </first_person_narrative>
    <no_source_references>
      <![CDATA[
        {Yes/No - Is content free of paper/study references and academic citations?}
      ]]>
    </no_source_references>
    <natural_expression>
      <![CDATA[
        {Yes/No - Does the content flow naturally with authentic reasoning process?}
      ]]>
    </natural_expression>
  </voice_requirements>
</results>
```

## ORIGINAL REFINED CONTENT

The original refined content for comparison:

<original_refined_content>

Question:

{{ original_question }}

Chain of reasoning:

{{ original_chain_of_reasoning }}

Answer:

{{ original_answer }}

</original_refined_content>

## REFERENCE PAPER

The original paper for fact-checking:

<reference_paper>
{{ paper }}
</reference_paper>

## VOICE-TRANSFORMED CONTENT TO EVALUATE

The voice-transformed content to evaluate:

<content_to_evaluate>

Question:

{{ question }}

Chain of reasoning:

{{ chain_of_reasoning }}

Answer:

{{ answer }}

</content_to_evaluate>
