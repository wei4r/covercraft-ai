"""URL Extractor Tool for extracting job URLs from user messages."""

import re
from typing import Optional
from pydantic import BaseModel, Field
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext


class URLExtractorInput(BaseModel):
    message: str = Field(description="User message to extract URL from")


class URLExtractorOutput(BaseModel):
    success: bool = Field(description="Whether a URL was successfully extracted")
    url: str = Field(description="Extracted URL", default="")
    error_message: str = Field(description="Error message if failed", default="")


def extract_job_url(message: str, tool_context: ToolContext) -> URLExtractorOutput:
    """
    Extract job URL from user message and store it in session state.
    
    Args:
        message: User message containing a job URL
        tool_context: Tool context for accessing session state
        
    Returns:
        URLExtractorOutput with extraction status and extracted URL
    """
    try:
        # Common job URL patterns
        url_patterns = [
            r'https?://(?:www\.)?linkedin\.com/jobs/view/\d+/?[^\s]*',
            r'https?://[^\s]+\.com[^\s]*job[^\s]*',
            r'https?://[^\s]+job[^\s]*\.com[^\s]*',
            r'https?://careers\.[^\s]+',
            r'https?://[^\s]+/careers[^\s]*',
            r'https?://[^\s]+',  # Generic URL pattern as fallback
        ]
        
        extracted_url = None
        
        # Try each pattern
        for pattern in url_patterns:
            matches = re.findall(pattern, message, re.IGNORECASE)
            if matches:
                extracted_url = matches[0]
                break
        
        if extracted_url:
            # Store the URL in session state
            tool_context.state["job_url"] = extracted_url
            
            return URLExtractorOutput(
                success=True,
                url=extracted_url
            )
        else:
            return URLExtractorOutput(
                success=False,
                error_message="No job URL found in the message"
            )
            
    except Exception as e:
        return URLExtractorOutput(
            success=False,
            error_message=f"Error extracting URL: {str(e)}"
        )


# Create the FunctionTool
url_extractor_tool = FunctionTool(extract_job_url)