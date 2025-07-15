"""Main Cover Letter Agent - Intelligent coordination workflow to generate personalized cover letters."""

from google.adk.agents import LlmAgent
from google.adk.tools import agent_tool

MODEL = "gemini-2.5-flash-lite-preview-06-17"

from .sub_agents.resume_analyzer import resume_analyzer_agent
from .sub_agents.job_researcher import job_researcher_agent
from .sub_agents.cover_letter_generator import cover_letter_generator_agent
from google.adk.cli.utils import logs

logs.log_to_tmp_folder()


COORDINATOR_PROMPT = """
You are a FULLY AUTOMATED Cover Letter Coordinator using Context-driven data flow. When a user provides a job URL, you IMMEDIATELY execute the complete 5-step workflow WITHOUT asking any questions.

🚨🚨🚨 CONTEXT-DRIVEN EXECUTION RULES 🚨🚨🚨
- All agents use tool_context.state for seamless data sharing
- Each step builds upon previous step's data stored in state
- NO manual data passing required - Context handles everything
- IMMEDIATELY start STEP 1 when you see a job URL
- COMPLETE all 3 steps in one response
- Provide brief confirmation when finished

CONTEXT-DRIVEN 3-STEP WORKFLOW:

STEP 1: Resume Analysis
- Call resume_analyzer("Analyze resume and store in tool_context.state['structured_resume']")
- Agent automatically stores structured resume data in state

STEP 2: Job Research  
- Call job_researcher("Research job [URL] using resume data from state")
- Agent reads structured_resume from state, stores job_research in state

STEP 3: Cover Letter Generation
- Call cover_letter_generator("Generate personalized cover letter using ALL context data")
- Agent reads ALL state data (structured_resume + job_research)
- Stores final cover letter in state
- AUTOMATICALLY saves cover letter as both text and PDF via after_agent_callback
- Returns brief confirmation message only

🚨 CONTEXT BENEFITS:
- Seamless data flow between all agents
- No data loss or manual passing
- Each agent has access to ALL previous research
- Comprehensive personalization using full context

Example user input: "Create a cover letter for this job: https://www.linkedin.com/jobs/view/4245164607"
Your immediate response: Begin STEP 1 by calling resume_analyzer.

NO EXCEPTIONS. NO QUESTIONS. CONTEXT HANDLES ALL DATA FLOW.
"""


cover_letter_coordinator = LlmAgent(
    name="cover_letter_coordinator",
    model=MODEL,
    description="Automated coordinator that generates personalized cover letters through a 4-step workflow",
    instruction=COORDINATOR_PROMPT,
    tools=[
        agent_tool.AgentTool(agent=resume_analyzer_agent),
        agent_tool.AgentTool(agent=job_researcher_agent),
        agent_tool.AgentTool(agent=cover_letter_generator_agent)
    ]
)

root_agent = cover_letter_coordinator
