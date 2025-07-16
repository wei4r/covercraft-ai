"""Resume Analyzer Agent - Extracts and analyzes resume information."""

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool, ToolContext
from ..tools.pdf_reader import pdf_reader_tool
from ..schemas import ResumeAnalysis, PersonalInfo, WorkExperience, Education
import json
from typing import Dict, Any

MODEL = "gemini-2.5-flash"

async def store_structured_resume(tool_context: ToolContext, structured_data: str) -> Dict[str, Any]:
    """Store structured resume analysis in session state."""
    try:
        # Parse the JSON string to validate structure
        data_dict = json.loads(structured_data)
        
        # Create ResumeAnalysis object to validate the structure
        structured_resume = ResumeAnalysis(**data_dict)
        
        # Store the validated data in session state
        tool_context.state["structured_resume"] = structured_resume.model_dump()
        
        print(f"✅ Structured resume analysis stored in session state")
        return {
            "success": True,
            "message": "Resume analysis stored successfully",
            "candidate_name": structured_resume.personal_info.name,
            "experience_years": structured_resume.total_experience_years,
            "skills_count": len(structured_resume.skills)
        }
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON format: {str(e)}"
        print(f"❌ {error_msg}")
        return {"success": False, "error": error_msg}
    except Exception as e:
        error_msg = f"Error storing resume analysis: {str(e)}"
        print(f"❌ {error_msg}")
        return {"success": False, "error": error_msg}


store_structured_resume_tool = FunctionTool(store_structured_resume)


RESUME_ANALYZER_PROMPT = """
You are a Resume Analyzer Agent that extracts structured data from resumes.

Your responsibilities:
1. Use pdf_reader_tool to read PDF resume files from the resume/ directory
2. Extract and analyze ALL resume content into structured JSON format
3. Use store_structured_resume_tool tool to save the data in proper format
4. Return a summary of the analysis completion

CRITICAL WORKFLOW:
1. IMMEDIATELY call pdf_reader_tool to read the resume
2. Analyze and extract ALL information into the exact JSON structure below
3. Call store_structured_resume_tool tool with the JSON data
4. Return a summary confirming analysis completion

REQUIRED JSON STRUCTURE (must be exact):
{
  "personal_info": {
    "name": "Full name from resume",
    "phone": "Phone number or null",
    "email": "Email address or null", 
    "location": "City, State/Country or null",
    "linkedin": "LinkedIn URL or null",
    "website": "Portfolio/website URL or null"
  },
  "professional_summary": "Professional summary/objective text or null",
  "work_experience": [
    {
      "company": "Company name",
      "position": "Job title",
      "duration": "Employment period (e.g., 'Jan 2020 - Dec 2022')",
      "location": "Work location or null",
      "achievements": ["Quantifiable achievement 1", "Achievement 2"],
      "technologies": ["Tech/tool used", "Programming language"]
    }
  ],
  "education": [
    {
      "institution": "School/University name",
      "degree": "Degree and field of study",
      "graduation": "Graduation year/date or null",
      "gpa": "GPA if mentioned or null",
      "honors": ["Academic honor 1", "Honor 2"]
    }
  ],
  "skills": ["Skill 1", "Programming language", "Framework"],
  "total_experience_years": 5,
  "key_achievements": ["Top quantifiable achievement 1", "Achievement 2"]
}

CRITICAL REQUIREMENTS:
- Extract ALL information available in the resume
- Use null for missing information, never omit fields
- Ensure JSON is valid and properly formatted
- Include quantifiable achievements with specific metrics when available
- Calculate total_experience_years based on work history
- Categorize skills appropriately (technical vs soft skills)

Always provide comprehensive, structured analysis that subsequent agents can easily consume.
"""

resume_analyzer_agent = LlmAgent(
    name="resume_analyzer",
    model=MODEL,
    description="Analyzes resume content and extracts structured information for cover letter personalization",
    instruction=RESUME_ANALYZER_PROMPT,
    tools=[pdf_reader_tool, store_structured_resume_tool],
)