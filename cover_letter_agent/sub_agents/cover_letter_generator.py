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
        complete_prompt = f"""You are a Cover Letter Generator. Create a professional, personalized cover letter using the structured data provided.

STRUCTURED RESUME ANALYSIS:
{json.dumps(resume_analysis, indent=2)}

STRUCTURED JOB RESEARCH:
{json.dumps(job_research, indent=2)}

REQUIREMENTS:
1. Create a complete cover letter with proper formatting in **Markdown**
2. Use the candidate's actual name: {candidate_name}
3. Company name: {company_name}
4. Reference specific job requirements from job_research.job_details.requirements
5. Include quantifiable achievements from resume_analysis.work_experience
6. Reference company insights from job_research.company_info
7. Use store_letter_tool to save the final cover letter
8. No placeholders or brackets - use actual data from the structured inputs

STRUCTURED DATA USAGE GUIDE:
**Personal Info**: Use resume_analysis.personal_info for contact details
**Work Experience**: Use resume_analysis.work_experience for achievements and background
**Job Details**: Use job_research.job_details for position info and requirements
**Company Info**: Use job_research.company_info for company insights and culture
**Skills Matching**: Cross-reference resume_analysis.skills with job_research.job_details.requirements

Cover Letter Structure:

**CRITICAL HEADER FORMATTING:**
Create a professional header at the top with the candidate's contact information using this EXACT format with proper line breaks:

```
[Candidate's Full Name]

[Email Address] | [Phone Number] | [Location]

[LinkedIn Profile] | [Portfolio/Website] (if available)

```

Example:
```
John Smith

john.smith@email.com | (555) 123-4567 | San Francisco, CA

linkedin.com/in/johnsmith | portfolio.johnsmith.com

```

**REQUIREMENTS:**
- First line: Name ONLY (no other information)
- Second line: EMPTY (blank line for spacing)
- Third line: Email, phone, location separated by " | "
- Fourth line: EMPTY (blank line for spacing) 
- Fifth line: Professional links (LinkedIn, portfolio) if available
- Sixth line: EMPTY (blank line before rest of letter)

**Structure Guidelines:**
- Header with candidate's contact information from personal_info (use format above)
- Professional greeting to {company_name}
- Opening paragraph referencing specific job_title and company knowledge
- Body paragraphs highlighting relevant work_experience and company fit  
- Professional closing with proper signature format:

**CRITICAL SIGNATURE FORMATTING:**
End the cover letter with:
```
Sincerely,

[Candidate's Full Name]
```
Use exactly this format - "Sincerely," followed by a blank line, then the candidate's name on its own line.

WORKFLOW:
1. Generate the complete cover letter using ALL structured data
2. **ABSOLUTELY MANDATORY:** Call store_letter_tool(cover_letter="[complete cover letter text]")
3. Return ONLY a brief confirmation message

**🚨 CRITICAL TOOL USAGE REQUIREMENT 🚨**
YOU MUST CALL THE TOOL: store_letter_tool(cover_letter="[complete cover letter text here]")
- This is NOT optional
- The system depends on this tool call to save the cover letter
- Without this tool call, the cover letter will be lost
- Call the tool with the COMPLETE cover letter text as the parameter

**MANDATORY TOOL CALL FORMAT:**
```
store_letter_tool(cover_letter="[Insert the complete cover letter text here - from header to signature]")
```

**RESPONSE FORMAT:**
After calling the tool, respond with ONLY:
"✅ Cover letter generated and saved successfully."

**ABSOLUTELY DO NOT:**
- Include the full cover letter in your response text
- Skip the tool call
- Provide any other response format

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