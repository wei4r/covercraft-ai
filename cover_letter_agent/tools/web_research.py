"""Web Research Tools for job descriptions and company information."""

import os
import json
import requests
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from google.adk.tools import FunctionTool
from bs4 import BeautifulSoup
from google.adk.tools import ToolContext

class WebFetchInput(BaseModel):
    url: str = Field(description="URL to fetch content from")


class WebFetchOutput(BaseModel):
    success: bool = Field(description="Whether the URL was successfully fetched")
    content: str = Field(description="Extracted text content", default="")
    title: str = Field(description="Page title", default="")
    error_message: str = Field(description="Error message if failed", default="")


class PerplexitySearchInput(BaseModel):
    query: str = Field(description="Search query for company research")
    focus: str = Field(description="Research focus (e.g., 'company_overview', 'recent_news')", default="company_overview")


class PerplexitySearchOutput(BaseModel):
    success: bool = Field(description="Whether the search was successful")
    content: str = Field(description="Research findings", default="")
    sources: list = Field(description="Source URLs", default_factory=list)
    error_message: str = Field(description="Error message if failed", default="")


def fetch_url(tool_context: ToolContext, url: str) -> WebFetchOutput:
    """
    Fetch and extract content from a web URL.
    
    Args:
        url: The URL to fetch
        
    Returns:
        WebFetchOutput with extracted content
    """
    # print(f"🔍 fetch_url called with tool_context: {tool_context.state.to_dict()}, url: {url}")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get title
        title = soup.title.string.strip() if soup.title else ""
        
        # Extract main content - try common content containers
        content_selectors = [
            '.job-details-jobs-unified-top-card__company-name',  # LinkedIn
            '[data-testid="job-description"]',  # LinkedIn
            '.description',
            '.job-description',
            '.content',
            'main',
            'article',
            '.post-content',
            '.entry-content'
        ]
        
        content = ""
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                content = elements[0].get_text(strip=True, separator='\n')
                break
        
        # If no specific content found, get body text
        if not content:
            content = soup.get_text(strip=True, separator='\n')
        
        # Clean up content
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        content = '\n'.join(lines)
        
        print(f"🔍 Storing job_description in tool_context.state, content length: {len(content)}")
        tool_context.state["job_description"] = content
        print(f"🔍 Successfully stored job_description in state")

        return WebFetchOutput(
            success=True,
            content=content,
            title=title
        )
        
    except requests.RequestException as e:
        return WebFetchOutput(
            success=False,
            error_message=f"Network error: {str(e)}"
        )
    except Exception as e:
        return WebFetchOutput(
            success=False,
            error_message=f"Error processing URL: {str(e)}"
        )


def search_perplexity(tool_context: ToolContext, query: str, focus: str = "company_overview") -> PerplexitySearchOutput:
    """
    Search using Perplexity API for company research, based on working implementation.
    
    Args:
        query: Search query (company name or research topic)
        focus: Research focus area
        
    Returns:
        PerplexitySearchOutput with research findings
    """
    try:
        # Import OpenAI client for Perplexity API (following working example)
        from openai import OpenAI
        
        api_key = os.getenv('PERPLEXITY_API_KEY')
        if not api_key:
            return PerplexitySearchOutput(
                success=False,
                error_message="PERPLEXITY_API_KEY environment variable not set"
            )
        
        # Initialize OpenAI client with Perplexity base URL (as per working example)
        client = OpenAI(api_key=api_key, base_url="https://api.perplexity.ai")
        
        # Construct focused messages based on focus area and working example
        focus_prompts = {
            "company_overview": (
                f"Analyze {query} and provide:\n\n"
                "1. **Industry Information**: Industry sector, market size, growth trends, key drivers\n"
                "2. **4P Marketing Mix**:\n"
                "   - Product: Core offerings, features, positioning\n"
                "   - Price: Pricing strategy, market positioning\n"
                "   - Place: Distribution channels, market presence\n"
                "   - Promotion: Marketing strategies, brand positioning\n"
                "3. **Competitive Analysis**: Main competitors, market share, competitive advantages, SWOT comparison\n\n"
                "Focus on recent data (2023-2025) and include specific metrics where available."
            )
        }
        
        
        # Use the message structure from the working example
        messages = [
            {
                "role": "system",
                "content": (
                    "Be precise and concise. Return a short, factual summary and a bulleted list of the most relevant facts or news about the company. "
                    "If possible, include a link to the company's official website."
                ),
            },
            {
                "role": "user",
                "content": "Research the company " + query + " with focus on " + focus_prompts.get(focus, focus_prompts["company_overview"])
            },
        ]
        
        response = client.chat.completions.create(
            model="sonar",
            messages=messages,
            max_tokens=3000,
            temperature=0.2,
            stream=False
        )
        
        content = response.choices[0].message.content
        sources = []
        
        # Extract content from response
        tool_context.state["company_research"] = content
        
        return PerplexitySearchOutput(
            success=True,
            content=content,
            sources=sources
        )
        
    except ImportError:
        return PerplexitySearchOutput(
            success=False,
            error_message="OpenAI library not installed. Run: pip install openai"
        )
    except Exception as e:
        return PerplexitySearchOutput(
            success=False,
            error_message=f"Error during Perplexity search: {str(e)}"
        )


# Create the FunctionTools
web_fetch_tool = FunctionTool(fetch_url)
perplexity_search_tool = FunctionTool(search_perplexity)