"""Cover Letter Generator Agent - Creates personalized cover letters based on all research."""

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import FunctionTool, ToolContext
from google.genai import types
from typing import Optional
from pydantic import BaseModel, Field

# Import save functions for after_agent_callback
from ..tools.save_cover_letter import save_cover_letter_function
from ..tools.save_cover_letter_pdf import save_cover_letter_pdf_function
from ..schemas import CoverLetterOutput as CoverLetterSchema
import json
from datetime import datetime

MODEL = "gemini-2.5-flash-lite-preview-06-17"


class StorageResult(BaseModel):
    success: bool = Field(description="Whether the cover letter was stored successfully")
    message: str = Field(description="Success or error message")


async def store_cover_letter(tool_context: ToolContext, cover_letter: str) -> StorageResult:
    """Store the final cover letter in session state with structured data."""
    try:
        # Create structured cover letter output using the correct schema
        word_count = len(cover_letter.split())
        cover_letter_output = CoverLetterSchema(
            content=cover_letter,
            word_count=word_count,
            key_points_covered=[],  # Will be populated by the agent
            company_specific_mentions=[],  # Will be populated by the agent
            quantified_achievements=[],  # Will be populated by the agent
            generated_date=datetime.now().isoformat()
        )
        # Store both the raw content and structured data
        tool_context.state["cover_letter"] = cover_letter
        tool_context.state["cover_letter_structured"] = cover_letter_output.model_dump()
        
        print(f"✅ Cover letter stored in session state (length: {len(cover_letter)}, words: {word_count})")
        return StorageResult(success=True, message="Cover letter stored successfully")
    except Exception as e:
        return StorageResult(success=False, message=str(e))


store_letter_tool = FunctionTool(store_cover_letter)


async def before_agent_callback(callback_context: CallbackContext):
    """Extract data from session state and provide it to the agent."""
    global cover_letter_generator_agent
    
    try:
        print("📝 Cover letter generator starting")
        
        # Extract all required structured data from session state
        resume_analysis = callback_context.state.get('resume_analysis')
        job_research = callback_context.state.get('job_research')
        
        # Check what data is available
        missing_data = []
        if not resume_analysis:
            missing_data.append('resume_analysis')
        if not job_research:
            missing_data.append('job_research')
        
        if missing_data:
            print(f"❌ Missing data: {missing_data}")
            error_prompt = f"""You cannot create a cover letter because the following required data is missing from session state:
{chr(10).join('- ' + item for item in missing_data)}

Please inform the user that this data is required to proceed."""
            
            cover_letter_generator_agent.instruction = error_prompt
            return None
        
        print("✅ All required data found in session state")
        
        # Extract candidate name for personalization
        candidate_name = "Unknown"
        if isinstance(resume_analysis, dict):
            personal_info = resume_analysis.get('personal_info', {})
            if isinstance(personal_info, dict):
                candidate_name = personal_info.get('name', 'Unknown')
        
        # Extract company name for context
        company_name = "Unknown Company"
        if isinstance(job_research, dict):
            job_details = job_research.get('job_details', {})
            if isinstance(job_details, dict):
                company_name = job_details.get('company', 'Unknown Company')
        
        # Create a complete prompt with structured data
        complete_prompt = f"""

# Cover Letter Generator Agent

You are an expert Cover Letter Generator that creates compelling, personalized cover letters using structured data. Generate a professional cover letter that demonstrates clear value alignment between the candidate and the target role.

## INPUT DATA
**STRUCTURED RESUME ANALYSIS:**
```json
{json.dumps(resume_analysis, indent=2)}
```

**STRUCTURED JOB RESEARCH:**
```json
{json.dumps(job_research, indent=2)}
```

**CANDIDATE DETAILS:**
- Name: {candidate_name}
- Target Company: {company_name}

## CORE REQUIREMENTS
- **Length**: Maximum 250 words (excluding header/signature)
- **Format**: Professional Markdown formatting
- **Personalization**: Use actual data from structured inputs - NO placeholders
- **Value Proposition**: Demonstrate clear candidate-role alignment
- **Quantifiable Impact**: Include specific achievements with metrics when available

## MANDATORY STRUCTURE

### 1. PROFESSIONAL HEADER
```
[Candidate's Full Name]

[Email] | [Phone] | [Location]

[LinkedIn Profile] | [Portfolio/Website] (if available)

```

### 2. CONTENT STRUCTURE (250 words max)
**Opening (40-50 words):**
- Address hiring manager/company professionally
- Reference specific position title from job_research.job_details
- Include compelling hook showing company knowledge from job_research.company_info

**Body Paragraph 1 (80-100 words):**
- Highlight 2-3 most relevant achievements from resume_analysis.work_experience
- Include quantifiable results (percentages, dollar amounts, scale)
- Directly connect experience to job_research.job_details.requirements

**Body Paragraph 2 (60-80 words):**
- Demonstrate company culture fit using job_research.company_info insights
- Reference specific company values, recent news, or strategic initiatives
- Show how candidate's background aligns with company direction

**Closing (30-40 words):**
- Professional call to action
- Express enthusiasm for contribution opportunity
- Professional sign-off

### 3. SIGNATURE BLOCK
```
Sincerely,

[Candidate's Full Name]
```

## STRATEGIC GUIDELINES

**Skills Matching Protocol:**
1. Cross-reference resume_analysis.skills with job_research.job_details.requirements
2. Prioritize skills that appear in both datasets
3. Quantify skill application with specific examples

**Company Intelligence Integration:**
- Reference job_research.company_info for recent developments, culture, values
- Show research depth without excessive flattery
- Connect personal values to company mission

**Achievement Quantification:**
- Prioritize resume_analysis.work_experience entries with measurable outcomes
- Use specific metrics: "increased sales by 23%" not "improved sales"
- Include scale context: team size, budget responsibility, project scope

## QUALITY STANDARDS
- **Professional Tone**: Confident but not arrogant
- **Specificity**: Every claim supported by data from structured inputs
- **Relevance**: Every sentence advances the candidate's value proposition
- **Authenticity**: Genuine enthusiasm backed by concrete evidence

## CRITICAL EXECUTION STEPS

1. **Generate Complete Cover Letter** using ALL structured data
2. **MANDATORY TOOL CALL:**
   ```
   store_letter_tool(cover_letter="[complete cover letter text from header to signature]")
   ```
3. **Response Format:**
   ```
   ✅ Cover letter generated and saved successfully.
   ```

## ABSOLUTE REQUIREMENTS
- ✅ Call store_letter_tool with complete cover letter text
- ✅ Stay within 250-word body limit
- ✅ Use actual data from structured inputs
- ✅ Include professional header and signature formatting
- ✅ Respond only with confirmation message after tool call

**FAILURE TO CALL THE TOOL WILL RESULT IN SYSTEM FAILURE**

"""
        
        # Update the agent's instruction with the complete data
        cover_letter_generator_agent.instruction = complete_prompt
        print("✅ Agent instruction updated with session state data")

        return None
        
    except Exception as e:
        print(f"❌ ERROR in before_agent_callback: {str(e)}")
        return None


async def after_model_callback(callback_context: CallbackContext, llm_response):
    """Simply return the LLM response unchanged."""
    # Tools haven't executed yet at this point, so don't check for cover letter
    return llm_response


async def after_agent_callback(callback_context: CallbackContext):
    """Automatically save the cover letter after generation."""
    try:
        # Check if cover letter was generated and stored in state
        cover_letter = callback_context.state.get('cover_letter')
        
        if not cover_letter:
            # Wait a moment and check again (tools might still be executing)
            import asyncio
            await asyncio.sleep(1)
            cover_letter = callback_context.state.get('cover_letter')
            if not cover_letter:
                return None
        
        # Extract metadata for comprehensive filename generation using structured data
        job_research = callback_context.state.get("job_research", {})
        resume_analysis = callback_context.state.get("resume_analysis", {})
        
        job_details = job_research.get("job_details", {})
        company_name = job_details.get("company", "Unknown_Company")
        job_title = job_details.get("job_title", "Position")
        
        # Extract candidate name from resume analysis
        candidate_name = "Candidate"
        if isinstance(resume_analysis, dict):
            personal_info = resume_analysis.get('personal_info', {})
            if isinstance(personal_info, dict):
                full_name = personal_info.get('name', 'Candidate')
                # Use just the last name for filename
                name_parts = full_name.split()
                candidate_name = name_parts[-1] if name_parts else 'Candidate'
        
        # Clean and limit strings for filename
        def clean_for_filename(text, max_length=15):
            # Remove special characters and clean
            cleaned = "".join(c for c in text if c.isalnum() or c in (' ', '-', '_')).strip()
            # Replace spaces with underscores
            cleaned = cleaned.replace(' ', '_')
            # Limit length to prevent long filenames
            if len(cleaned) > max_length:
                cleaned = cleaned[:max_length]
            return cleaned
        
        safe_company = clean_for_filename(company_name, 20)
        safe_job_title = clean_for_filename(job_title, 25)
        safe_candidate = clean_for_filename(candidate_name, 15)
        
        # Generate descriptive but concise filename with date
        import datetime
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Create a more readable filename
        if safe_job_title and safe_company:
            base_filename = f"{safe_candidate}_CoverLetter_{safe_company}_{date_str}"
        else:
            base_filename = f"{safe_candidate}_CoverLetter_{date_str}"
        
        # Save as text file using save_cover_letter_function
        text_result = await save_cover_letter_function(
            callback_context,
            f"{base_filename}.txt"
        )
        
        # Save as PDF using save_cover_letter_pdf_function  
        pdf_result = await save_cover_letter_pdf_function(
            callback_context,
            f"{base_filename}.pdf"
        )
        
        # Update state with save information
        callback_context.state["save_results"] = {
            "text": text_result,
            "pdf": pdf_result,
            "timestamp": date_str
        }
        return None
        
    except Exception as e:
        print(f"❌ ERROR in after_agent_callback: {str(e)}")
        callback_context.state["save_error"] = str(e)
        return None
    


cover_letter_generator_agent = LlmAgent(
    name="cover_letter_generator",
    model=MODEL,
    description="Generates personalized, professional cover letters based on comprehensive research and analysis",
    instruction="",
    tools=[store_letter_tool], 
    before_agent_callback= before_agent_callback,
    after_model_callback=after_model_callback,
    after_agent_callback=after_agent_callback
)