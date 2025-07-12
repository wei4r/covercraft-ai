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
from ..schemas import CoverLetterOutput, ResumeAnalysis, JobResearch
import json
from datetime import datetime

# MODEL = "gemini-2.5-flash"
MODEL = "gemini-2.5-flash-lite-preview-06-17"


class CoverLetterOutput(BaseModel):
    success: bool = Field(description="Whether the cover letter was stored successfully")
    message: str = Field(description="Success or error message")


async def store_cover_letter(tool_context: ToolContext, cover_letter: str) -> CoverLetterOutput:
    """Store the final cover letter in session state with structured data."""
    try:
        # Create structured cover letter output
        word_count = len(cover_letter.split())
        cover_letter_output = CoverLetterOutput(
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
        return CoverLetterOutput(success=True, message="Cover letter stored successfully")
    except Exception as e:
        return CoverLetterOutput(success=False, message=str(e))


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
- Header with candidate's contact information from personal_info
- Professional greeting to {company_name}
- Opening paragraph referencing specific job_title and company knowledge
- Body paragraphs highlighting relevant work_experience and company fit  
- Professional closing

WORKFLOW:
1. Generate the complete cover letter using ALL structured data
2. Call store_letter_tool with the complete letter text
3. Return the complete cover letter for display in **Markdown format**

"""
        
        # Update the agent's instruction with the complete data
        cover_letter_generator_agent.instruction = complete_prompt
        print("✅ Agent instruction updated with session state data")

        return None
        
    except Exception as e:
        print(f"❌ ERROR in before_agent_callback: {str(e)}")
        return None


async def after_model_callback(callback_context: CallbackContext, llm_response):
    """Capture the model response and store it in state for saving."""
    try:
        print("💾 Running after_model_callback to capture cover letter")
        
        # Extract the text content from the LLM response
        if llm_response and hasattr(llm_response, 'content') and llm_response.content:
            if hasattr(llm_response.content, 'parts') and llm_response.content.parts:
                cover_letter = llm_response.content.parts[0].text
                if cover_letter:
                    # Store it in state for the after_agent_callback to use
                    callback_context.state['cover_letter'] = cover_letter
                    print("✅ Cover letter captured from model response and stored in state")
        
        # Return the original response unchanged
        return llm_response
        
    except Exception as e:
        print(f"❌ ERROR in after_model_callback: {str(e)}")
        return llm_response


async def after_agent_callback(callback_context: CallbackContext):
    """Automatically save the cover letter after generation."""
    try:
        print("💾 Running after_agent_callback to save cover letter")
        # print(f"✅ Callback context: {callback_context.state.to_dict()}")
        
        # Check if cover letter was generated and stored in state
        cover_letter = callback_context.state.get('cover_letter')
        
        if not cover_letter:
            print("❌ No cover letter found in state, skipping save")
            return None
        
        print("✅ Cover letter found, proceeding to save")
        
        # Extract metadata for filename generation using structured data
        job_research = callback_context.state.get("job_research", {})
        job_details = job_research.get("job_details", {})
        company_name = job_details.get("company", "Unknown_Company")
        
        # Clean company name for filename
        safe_company = "".join(c for c in company_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_company = safe_company.replace(' ', '_')
        
        # Generate filename with timestamp
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"cover_letter_{safe_company}_{timestamp}"
        
        # Save as text file using save_cover_letter_function
        print(f"💾 Saving cover letter as text: {base_filename}.txt")
        
        text_result = await save_cover_letter_function(
            callback_context=callback_context,
            filename=f"{base_filename}.txt"
        )
        print(f"✅ Text save result: {text_result}")
        
        # Save as PDF using save_cover_letter_pdf_function  
        print(f"💾 Saving cover letter as PDF: {base_filename}.pdf")
        pdf_result = await save_cover_letter_pdf_function(
            callback_context=callback_context,
            filename=f"{base_filename}.pdf"
        )
        print(f"✅ PDF save result: {pdf_result}")
        
        # Update state with save information
        callback_context.state["save_results"] = {
            "text": text_result,
            "pdf": pdf_result,
            "timestamp": timestamp
        }
        
        print("✅ Cover letter saved successfully in both formats")
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