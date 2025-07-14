"""Job Researcher Agent - Analyzes job descriptions and researches companies."""

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool, ToolContext
from ..tools.web_research import web_fetch_tool, perplexity_search_tool
from ..schemas import JobResearch, JobDetails, CompanyInfo, JobRequirements
import json
from typing import Dict, Any
from datetime import datetime

# MODEL = "gemini-2.5-flash-lite-preview-06-17"
MODEL = "gemini-2.5-flash"


async def store_structured_job_research(tool_context: ToolContext, structured_data: str) -> Dict[str, Any]:
    """Store structured job research in session state."""
    try:
        # Clean up the JSON string by handling problematic content
        cleaned_data = structured_data.strip()
        
        # Try to parse JSON directly first
        try:
            data_dict = json.loads(cleaned_data)
        except json.JSONDecodeError as e:
            print(f"❌ Initial JSON parse failed: {e}")
            print(f"❌ Problematic JSON snippet: \n{cleaned_data[:500]}...")
            
            # Try to fix common JSON issues
            import re
            
            # Method 1: Try to fix escape sequences by removing problematic ones
            # Replace invalid escape sequences with safe alternatives
            fixed_data = cleaned_data
            
            # Remove or replace problematic escape sequences
            # Look for backslashes followed by characters that aren't valid JSON escapes
            def fix_invalid_escapes(text):
                # Valid JSON escape sequences: \", \\, \/, \b, \f, \n, \r, \t, \uXXXX
                # Replace any other \x with just x
                result = ""
                i = 0
                while i < len(text):
                    if text[i] == '\\' and i + 1 < len(text):
                        next_char = text[i + 1]
                        if next_char in '"\\/:bfnrt':
                            # Valid escape sequence
                            result += text[i:i+2]
                            i += 2
                        elif next_char == 'u' and i + 5 < len(text):
                            # Unicode escape sequence
                            result += text[i:i+6]
                            i += 6
                        else:
                            # Invalid escape sequence, just keep the character
                            result += next_char
                            i += 2
                    else:
                        result += text[i]
                        i += 1
                return result
            
            fixed_data = fix_invalid_escapes(fixed_data)
            
            try:
                data_dict = json.loads(fixed_data)
                print("✅ JSON parsed successfully after escape sequence fix")
            except json.JSONDecodeError as e2:
                print(f"❌ JSON parse still failed after escape fix: {e2}")
                # As last resort, try to extract just the structure we need
                raise ValueError(f"Cannot parse JSON data: {e2}")
        
        # Add current timestamp if not provided
        if not data_dict.get("research_date"):
            data_dict["research_date"] = datetime.now().isoformat()
        
        # Create JobResearch object to validate the structure
        job_research = JobResearch(**data_dict)
        
        # Store the validated data in session state
        tool_context.state["job_research"] = job_research.model_dump()
        
        print(f"✅ Structured job research stored in session state")
        return {
            "success": True,
            "message": "Job research stored successfully",
            "company_name": job_research.job_details.company,
            "job_title": job_research.job_details.job_title,
            "industry": job_research.company_info.industry
        }
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON format: {str(e)}"
        print(f"❌ {error_msg}")
        print(f"❌ Problematic JSON snippet: {structured_data[:500]}...")
        return {"success": False, "error": error_msg}
    except Exception as e:
        error_msg = f"Error storing job research: {str(e)}"
        print(f"❌ {error_msg}")
        return {"success": False, "error": error_msg}


store_job_research_tool = FunctionTool(store_structured_job_research)


JOB_RESEARCHER_PROMPT = """
You are a comprehensive Job Researcher Agent that analyzes job postings and researches companies.

🚨 CRITICAL WORKFLOW REQUIREMENTS 🚨
You MUST complete ALL 4 steps in sequence. Do NOT skip any step. Each step builds on the previous one.

MANDATORY 4-STEP WORKFLOW:
STEP 1: Web Fetch
- Extract job URL from user input
- Call web_fetch_tool with the job URL to fetch job description
- The tool will store raw content in state["job_description"]

STEP 2: Company Research
- Extract company name from the fetched job description
- Call perplexity_search_tool with company name to research company
- The tool will store company research in state["company_research"]

STEP 3: Data Analysis & Structuring
- Analyze the fetched job description (from state["job_description"])
- Analyze the company research (from state["company_research"])
- Extract and structure all information into the required JSON format

STEP 4: Data Storage (MANDATORY)
- Call store_structured_job_research tool with the complete JSON data
- This is REQUIRED for the workflow to complete successfully
- Other agents depend on this stored data

🚨 CRITICAL REQUIREMENTS 🚨
- You MUST complete all 4 steps
- You MUST call store_structured_job_research tool - the workflow is NOT complete without this
- Use the exact JSON structure provided below
- Do not skip any tools - all tools must be used

REQUIRED JSON STRUCTURE (must be exact):
{
  "job_details": {
    "company": "Company name",
    "job_title": "Position title",
    "department": "Department/team or null",
    "location": "Job location or null",
    "employment_type": "Full-time/Part-time/Contract or null",
    "salary_range": "Salary information or null",
    "job_description": "Complete job description text",
    "responsibilities": ["Key responsibility 1", "Responsibility 2"],
    "requirements": {
      "required_skills": ["Must-have skill 1", "Required skill 2"],
      "preferred_skills": ["Nice-to-have skill 1", "Preferred skill 2"],
      "experience_level": "Years of experience required or level",
      "education_requirements": ["Degree requirement", "Educational background"],
    },
    "application_deadline": "Deadline if mentioned or null"
  },
  "company_info": {
    "name": "Company name",
    "industry": "Industry/sector or null",
    "size": "Company size (number of employees) or null",
    "recent_news": ["Recent development 1", "News item 2"],
    "main_business": "Main business/products/services description or null",
    "notes": "Additional info: culture, values, mission, competitors, funding, headquarters, website, etc."
  },
  "job_url": "Original job posting URL",
  "market_insights": ["Industry trend 1", "Market insight 2"],
  "application_tips": ["Specific tip 1", "Strategy 2"]
}

CRITICAL REQUIREMENTS:
- Extract ALL available information from job posting
- Use comprehensive company research via Perplexity for company_info
- Use null for missing information, never omit fields
- Ensure JSON is valid and properly formatted
- Include specific, actionable application tips
- Research market trends and industry insights
- Put additional company details (culture, values, mission, competitors, funding, headquarters, website, etc.) in the "notes" field
- Keep company_info focused on essential fields only

🔥 EXECUTION INSTRUCTIONS - FOLLOW EXACTLY 🔥

YOU MUST EXECUTE THESE TOOLS IN THIS EXACT ORDER:

1. **FIRST**: Call web_fetch_tool(url="[JOB_URL]")
   - Wait for response and confirm job description is fetched

2. **SECOND**: Call perplexity_search_tool(query="[COMPANY_NAME]", focus="company_overview")
   - Wait for response and confirm company research is completed

3. **THIRD**: Create complete JSON structure using fetched data

4. **FOURTH (MANDATORY)**: Call store_structured_job_research(structured_data="[COMPLETE_JSON]")
   - This tool MUST be called
   - The workflow is NOT complete without this step
   - Other agents require this stored data

⚠️ CRITICAL SUCCESS CRITERIA ⚠️
- The job_researcher agent is ONLY successful if store_structured_job_research tool is called
- You must use ALL tools: web_fetch_tool → perplexity_search_tool → store_structured_job_research
- Missing any tool call means FAILURE

Remember: The workflow is incomplete until store_structured_job_research stores the data in session state.
"""

job_researcher_agent = LlmAgent(
    name="job_researcher",
    model=MODEL,
    description="Analyzes job postings and researches companies to provide structured data for cover letter generation",
    instruction=JOB_RESEARCHER_PROMPT,
    tools=[web_fetch_tool, perplexity_search_tool, store_job_research_tool],
)