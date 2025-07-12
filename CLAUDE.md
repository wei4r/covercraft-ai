# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Cover Letter Agent V2 built with Google's Agent Development Kit (ADK). It's a multi-agent system that analyzes resumes, researches jobs/companies, and generates personalized cover letters using a context-driven data flow architecture.

## Core Architecture

The system uses a **multi-agent orchestration pattern** with a coordinator and five specialized sub-agents:

1. **Root Agent** (`cover_letter_agent/agent.py`): `cover_letter_coordinator` - orchestrates the entire workflow
2. **Resume Analyzer** (`sub_agents/resume_analyzer.py`): Extracts structured data from PDF resumes
3. **Job Researcher** (`sub_agents/job_researcher.py`): Analyzes job descriptions and researches companies
4. **Experience Researcher** (`sub_agents/experience_researcher.py`): Finds insights about application strategies
5. **Cover Letter Generator** (`sub_agents/cover_letter_generator.py`): Creates personalized cover letters
6. **Cover Letter Saver** (`sub_agents/cover_letter_saver.py`): Saves generated cover letters to artifacts

All agents use the model `gemini-2.5-flash-lite-preview-06-17` and follow the ADK `LlmAgent` pattern.

### Context-Driven Data Flow

The system uses `tool_context.state` for seamless data sharing between agents:
- Each agent stores its output in the shared context state
- Subsequent agents automatically access previous agents' data from state
- No manual data passing required between workflow steps
- Enables fully automated execution from job URL to final cover letter

## Key Development Commands

### Running the Agent
```bash
# Run via ADK CLI (primary method)
adk run cover_letter_agent

# Run with web interface
adk web cover_letter_agent
```

### Testing & Development
```bash
# Run comprehensive tests (various test scenarios)
pytest

# Specific test files for different components
python test_real_workflow.py          # End-to-end workflow test
python test_job_researcher.py         # Job research functionality
python test_artifacts.py              # Artifact management test
python test_cover_letter_state.py     # State management test

# Quick agent initialization test
python test_agent.py
```

### Installation & Setup
```bash
# Install with poetry (recommended)
poetry install

# Or install with pip
pip install google-adk google-generativeai pymupdf requests beautifulsoup4 python-dotenv openai

# Setup environment variables
cp .env.example .env
# Edit .env with your API keys
```

## Environment Configuration

Required environment variables (copy from `.env.example`):
- `GEMINI_API_KEY`: For Gemini model access (required)
- `PERPLEXITY_API_KEY`: For enhanced company research (optional but recommended)
- `GOOGLE_CUSTOM_SEARCH_API_KEY`: For fallback search (optional)
- `GOOGLE_CUSTOM_SEARCH_ENGINE_ID`: Custom search engine ID (optional)

## Key Technical Patterns

### Agent Tool Integration
Each sub-agent is integrated using `AgentTool` from `google.adk.tools.agent_tool`:
```python
tools=[
    AgentTool(resume_analyzer_agent, "resume_analyzer"),
    AgentTool(job_researcher_agent, "job_researcher"),
    AgentTool(experience_researcher_agent, "experience_researcher"),
    AgentTool(cover_letter_generator_agent, "cover_letter_generator"),
    # ...
]
```

### Tool Architecture
- **PDF Processing**: Uses PyMuPDF (`fitz`) for resume text extraction from `resume/` directory
- **Web Research**: Custom tools for URL fetching, Perplexity API, and Google Search
- **Artifact Management**: Tools for saving cover letters as both markdown and PDF formats
- **Shared Libraries**: `text_utils.py` contains common text processing functions

### Data Flow (Context-Driven)
1. User provides job URL (resume is auto-detected from `resume/` directory)
2. Resume Analyzer extracts structured candidate data → stores in `tool_context.state['resume_analysis']`
3. Job Researcher fetches job description and researches company → stores in `tool_context.state['job_research']`
4. Experience Researcher finds application insights → stores in `tool_context.state['experience_insights']`
5. Cover Letter Generator synthesizes all state data → stores in `tool_context.state['cover_letter']`
6. Cover Letter Saver saves final output to `artifacts/` directory

## File Structure Context

- `cover_letter_agent/agent.py`: Main coordinator with fully automated workflow orchestration
- `cover_letter_agent/sub_agents/`: Five specialized agents, each with specific prompts and tools
- `cover_letter_agent/tools/`: Tools for PDF processing, web research, and artifact management
- `cover_letter_agent/shared_libraries/`: Common utilities (mainly `text_utils.py`)
- `resume/`: Directory for storing resume PDFs to process (PDF reader auto-detects files here)
- `output/`: Directory for generated cover letters (legacy)
- `artifacts/`: Directory for saved cover letters (current)
- `test_*.py`: Various test files for different components and workflows

## Model Configuration

All agents use `gemini-2.5-flash-lite-preview-06-17`. The model is configured in each agent file's `MODEL` constant. When updating models, change in all agent files consistently:

```python
MODEL = "gemini-2.5-flash-lite-preview-06-17"
```

## External Dependencies

Critical third-party integrations:
- **Google ADK**: Core agent framework (`google-adk>=1.0.0`)
- **PyMuPDF**: PDF text extraction (`pymupdf>=1.24.0`)
- **Perplexity API**: Enhanced company research via OpenAI client (`openai>=1.0.0`)
- **Google Custom Search API**: Fallback search capabilities
- **BeautifulSoup**: HTML parsing for web scraping (`beautifulsoup4>=4.12.0`)
- **Requests**: HTTP requests for web fetching (`requests>=2.32.0`)

## Perplexity API Integration

The Perplexity search tool has been refined based on working implementations:

- **Model**: Uses "sonar" model for real-time web search
- **Client**: OpenAI client with `base_url="https://api.perplexity.ai"`
- **Focus Areas**: company_overview, recent_news, culture_values, hiring_trends
- **System Context**: Optimized for precise, factual company research with structured prompts

## Development Notes

- The system is designed for fully automated execution - no user interaction required after providing job URL
- All agents store their outputs in `tool_context.state` for seamless data sharing
- The coordinator executes all 5 steps in sequence automatically
- Resume PDFs should be placed in the `resume/` directory before running
- Generated cover letters are saved to both markdown and PDF formats in `artifacts/`
- Test files provide comprehensive coverage of individual components and full workflows