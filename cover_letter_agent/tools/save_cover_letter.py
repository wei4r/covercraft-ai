"""Save Cover Letter Functions - Normal functions for use in callbacks."""

import datetime
from google.genai import types
from typing import Dict, Any

async def save_cover_letter_function(callback_context, filename: str) -> Dict[str, Any]:
    """
    Saves the generated cover letter as an artifact with comprehensive metadata.
    
    Args:
        callback_context: CallbackContext with state and save_artifact method
        filename: Name for the cover letter file (will be auto-enhanced if basic)
        
    Returns:
        Dictionary with save status and details
    """
    try:
        # Extract cover letter content from context state
        print(f"🔍 save_cover_letter_function called with callback_context state, filename: {filename}")
        cover_letter_content = callback_context.state.get("cover_letter")
        if not cover_letter_content:
            return {
                'status': 'failed',
                'error': 'No cover letter found in context state. Generate a cover letter first.'
            }

        # Extract metadata from context state
        job_data = callback_context.state.get("job_research", {})
        resume_data = callback_context.state.get("resume_analysis", {})
        
        # Extract company and job details
        job_details = job_data.get("job_details", {})
        company_name = job_details.get("company", "Unknown_Company")
        job_title = job_details.get("title", "Unknown_Position")
        
        # Extract candidate details
        personal_info = resume_data.get("personal_info", {})
        candidate_name = personal_info.get("name", "Unknown_Candidate")
        candidate_email = personal_info.get("email", "")
        
        # Generate timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        # Clean company name for filename
        safe_company = "".join(c for c in company_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_company = safe_company.replace(' ', '_')
        
        # Auto-generate descriptive filename if basic one provided
        if not filename or filename == "cover_letter.txt":
            filename = f"cover_letter_{safe_company}_{timestamp}.txt"
        elif not filename.startswith('cover_letter_'):
            filename = f"cover_letter_{filename}"
        if not filename.endswith('.txt'):
            filename = f"{filename}.txt"
        
        # Create comprehensive metadata header
        metadata_header = f"""# Cover Letter - {company_name}
## Generated with ADK Cover Letter Agent
##
## Candidate: {candidate_name}
## Email: {candidate_email}
## Company: {company_name}
## Position: {job_title}
## Generated: {timestamp}
## Filename: {filename}
##
## This cover letter was generated using Context-driven data flow
## combining resume analysis, job research, and strategic insights.
##
===============================================================

"""
        
        # Combine metadata and content
        full_content = metadata_header + cover_letter_content

        # Save as artifact using CallbackContext.save_artifact
        await callback_context.save_artifact(
            filename,
            types.Part(text=full_content)
        )
        
        # Store save confirmation in context state
        save_status = {
            "success": True,
            "filename": filename,
            "company": company_name,
            "position": job_title,
            "candidate": candidate_name,
            "timestamp": timestamp
        }
        callback_context.state["save_status"] = save_status
        
        return {
            'status': 'success',
            'detail': f'Cover letter saved successfully as {filename}',
            'filename': filename,
            'company': company_name,
            'position': job_title,
            'timestamp': timestamp
        }
        
    except Exception as e:
        error_msg = f"Error saving cover letter: {str(e)}"
        callback_context.state["save_status"] = {
            "success": False,
            "error": error_msg
        }
        return {
            'status': 'failed',
            'error': error_msg
        }

# Legacy tool wrapper - now using save_cover_letter_function directly in callbacks
from google.adk.tools import FunctionTool, ToolContext

async def save_cover_letter(tool_context: ToolContext, filename: str):
    """Legacy wrapper for backward compatibility."""
    return await save_cover_letter_function(tool_context, filename)

save_cover_letter_tool = FunctionTool(save_cover_letter)
