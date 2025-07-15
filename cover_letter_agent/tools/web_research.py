"""Web Research Tools for job descriptions and company information."""

import os
import json
import requests
import time
import random
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
    Fetch and extract content from a web URL with enhanced job board support.
    
    Args:
        url: The URL to fetch
        
    Returns:
        WebFetchOutput with extracted content
    """
    # print(f"🔍 fetch_url called with tool_context: {tool_context.state.to_dict()}, url: {url}")
    
    # Retry configuration
    max_retries = 3
    base_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            # Enhanced headers with user agent rotation
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
            ]
            
            headers = {
                'User-Agent': random.choice(user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0',
            }
            
            # Add random delay between retries
            if attempt > 0:
                delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0.1, 0.5)
                time.sleep(delay)
                print(f"🔍 Retry attempt {attempt + 1} for URL: {url}")
            
            # Make request with timeout
            response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
            response.raise_for_status()
            
            # Check if we got a valid response
            if response.status_code == 200 and response.content:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Get title
                title = soup.title.string.strip() if soup.title else ""
                
                # Step 1: Try to extract structured data (JSON-LD JobPosting schema)
                content = _extract_structured_job_data(soup)
                
                # Step 2: If no structured data, try job-specific selectors
                if not content:
                    content = _extract_job_content_with_selectors(soup, url)
                
                # Step 3: If still no content, try general content selectors
                if not content:
                    content = _extract_general_content(soup)
                
                # Step 4: Final fallback - get body text
                if not content:
                    content = soup.get_text(strip=True, separator='\n')
                
                # Clean up and validate content
                content = _clean_and_validate_content(content)
                
                # Validate that we got meaningful content
                if len(content) < 50:
                    if attempt < max_retries - 1:
                        print(f"🔍 Content too short ({len(content)} chars), retrying...")
                        continue
                    else:
                        print(f"🔍 Warning: Content is very short ({len(content)} chars)")
                
                print(f"🔍 Storing job_description in tool_context.state, content length: {len(content)}")
                tool_context.state["job_description"] = content
                print(f"🔍 Successfully stored job_description in state")

                return WebFetchOutput(
                    success=True,
                    content=content,
                    title=title
                )
            
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                print(f"🔍 Timeout on attempt {attempt + 1}, retrying...")
                continue
            else:
                return WebFetchOutput(
                    success=False,
                    error_message=f"Timeout error after {max_retries} attempts"
                )
        
        except requests.exceptions.TooManyRedirects:
            return WebFetchOutput(
                success=False,
                error_message="Too many redirects - URL might be invalid"
            )
        
        except requests.exceptions.ConnectionError as e:
            if attempt < max_retries - 1:
                print(f"🔍 Connection error on attempt {attempt + 1}, retrying...")
                continue
            else:
                return WebFetchOutput(
                    success=False,
                    error_message=f"Connection error after {max_retries} attempts: {str(e)}"
                )
        
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in [429, 503, 502, 504]:  # Rate limiting or server errors
                if attempt < max_retries - 1:
                    print(f"🔍 HTTP error {e.response.status_code} on attempt {attempt + 1}, retrying...")
                    continue
                else:
                    return WebFetchOutput(
                        success=False,
                        error_message=f"HTTP error {e.response.status_code} after {max_retries} attempts"
                    )
            else:
                return WebFetchOutput(
                    success=False,
                    error_message=f"HTTP error: {str(e)}"
                )
        
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"🔍 General error on attempt {attempt + 1}, retrying: {str(e)}")
                continue
            else:
                return WebFetchOutput(
                    success=False,
                    error_message=f"Error processing URL after {max_retries} attempts: {str(e)}"
                )
    
    # If we get here, all retries failed
    return WebFetchOutput(
        success=False,
        error_message=f"Failed to fetch URL after {max_retries} attempts"
    )


def _extract_structured_job_data(soup: BeautifulSoup) -> str:
    """Extract job data from JSON-LD structured data."""
    try:
        # Look for JSON-LD structured data
        json_scripts = soup.find_all('script', type='application/ld+json')
        
        for script in json_scripts:
            try:
                data = json.loads(script.string)
                
                # Handle both single objects and arrays
                if isinstance(data, list):
                    data = data[0] if data else {}
                
                # Look for JobPosting schema
                if data.get('@type') == 'JobPosting' or (isinstance(data.get('@type'), list) and 'JobPosting' in data.get('@type')):
                    job_content = []
                    
                    if data.get('title'):
                        job_content.append(f"Job Title: {data['title']}")
                    
                    if data.get('description'):
                        job_content.append(f"Description: {data['description']}")
                    
                    if data.get('hiringOrganization', {}).get('name'):
                        job_content.append(f"Company: {data['hiringOrganization']['name']}")
                    
                    if data.get('jobLocation'):
                        location = data['jobLocation']
                        if isinstance(location, dict):
                            addr = location.get('address', {})
                            if addr.get('addressLocality'):
                                job_content.append(f"Location: {addr['addressLocality']}")
                    
                    if data.get('baseSalary'):
                        salary = data['baseSalary']
                        if isinstance(salary, dict) and salary.get('value'):
                            job_content.append(f"Salary: {salary['value']}")
                    
                    if data.get('employmentType'):
                        job_content.append(f"Employment Type: {data['employmentType']}")
                    
                    if data.get('qualifications'):
                        job_content.append(f"Qualifications: {data['qualifications']}")
                    
                    if job_content:
                        return '\n'.join(job_content)
                        
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
                
    except Exception:
        pass
    
    return ""


def _extract_job_content_with_selectors(soup: BeautifulSoup, url: str) -> str:
    """Extract job content using job board specific selectors."""
    
    # Job board specific selectors based on research
    job_selectors = {
        'linkedin.com': [
            '[data-testid="job-description"]',
            '.job-details-jobs-unified-top-card__company-name',
            '.jobs-description-content__text',
            '.jobs-box__html-content'
        ],
        'indeed.com': [
            '[data-testid="job-description"]',
            '.jobsearch-JobComponent-description',
            '.jobsearch-jobDescriptionText',
            '.job_seen_beacon',
            '.jobDescription'
        ],
        'glassdoor.com': [
            '[data-test="job-description"]',
            '.jobDescriptionContent',
            '.desc',
            '.jobDescription',
            '.jobView-section'
        ],
        'ziprecruiter.com': [
            '.job_description',
            '.job_content',
            '.job-description-wrapper',
            '.jobDescriptionSection',
            '.job_details'
        ],
        'wellfound.com': [
            '[data-cy="job-description"]',
            '.job-description',
            '.startup-job-description',
            '.job-details'
        ],
        'angellist.com': [
            '[data-cy="job-description"]',
            '.job-description',
            '.startup-job-description',
            '.job-details'
        ]
    }
    
    # Determine which selectors to use based on URL
    domain = None
    for key in job_selectors.keys():
        if key in url.lower():
            domain = key
            break
    
    # Try domain-specific selectors first
    if domain:
        for selector in job_selectors[domain]:
            elements = soup.select(selector)
            if elements:
                content = elements[0].get_text(strip=True, separator='\n')
                if _is_quality_job_content(content):
                    return content
    
    # Try all selectors if domain-specific didn't work
    all_selectors = []
    for selectors in job_selectors.values():
        all_selectors.extend(selectors)
    
    for selector in all_selectors:
        elements = soup.select(selector)
        if elements:
            content = elements[0].get_text(strip=True, separator='\n')
            if _is_quality_job_content(content):
                return content
    
    return ""


def _extract_general_content(soup: BeautifulSoup) -> str:
    """Extract content using general content selectors."""
    general_selectors = [
        '.description',
        '.job-description',
        '.content',
        'main',
        'article',
        '.post-content',
        '.entry-content',
        '.main-content',
        '#content',
        '.page-content'
    ]
    
    for selector in general_selectors:
        elements = soup.select(selector)
        if elements:
            content = elements[0].get_text(strip=True, separator='\n')
            if len(content) > 100:  # Basic length check
                return content
    
    return ""


def _is_quality_job_content(content: str) -> bool:
    """Check if the extracted content appears to be quality job-related content."""
    if not content or len(content) < 100:
        return False
    
    # Job-related keywords to look for
    job_keywords = [
        'responsibilities', 'requirements', 'qualifications', 'experience',
        'skills', 'position', 'role', 'job', 'candidate', 'apply',
        'salary', 'benefits', 'company', 'team', 'work', 'employment'
    ]
    
    content_lower = content.lower()
    keyword_count = sum(1 for keyword in job_keywords if keyword in content_lower)
    
    # Content should have at least 3 job-related keywords
    return keyword_count >= 3


def _clean_and_validate_content(content: str) -> str:
    """Clean up and validate extracted content."""
    if not content:
        return ""
    
    # Remove common navigation and footer elements
    unwanted_phrases = [
        'Skip to main content',
        'Sign in',
        'Sign up',
        'Login',
        'Register',
        'Cookie policy',
        'Privacy policy',
        'Terms of service',
        'All rights reserved',
        'Follow us on',
        'Subscribe to',
        'Newsletter'
    ]
    
    lines = content.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if line and not any(phrase.lower() in line.lower() for phrase in unwanted_phrases):
            cleaned_lines.append(line)
    
    # Remove excessive whitespace and empty lines
    cleaned_content = '\n'.join(cleaned_lines)
    
    # Limit content length to avoid excessive data
    if len(cleaned_content) > 10000:
        cleaned_content = cleaned_content[:10000] + "...(truncated)"
    
    return cleaned_content


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