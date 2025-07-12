"""Structured data schemas for session state management."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class PersonalInfo(BaseModel):
    """Personal information from resume."""
    name: str = Field(description="Full name")
    phone: Optional[str] = Field(default=None, description="Phone number")
    email: Optional[str] = Field(default=None, description="Email address")
    location: Optional[str] = Field(default=None, description="City, State/Country")
    linkedin: Optional[str] = Field(default=None, description="LinkedIn profile URL")
    website: Optional[str] = Field(default=None, description="Personal website or portfolio")


class WorkExperience(BaseModel):
    """Work experience entry."""
    company: str = Field(description="Company name")
    position: str = Field(description="Job title")
    duration: str = Field(description="Employment duration (e.g., 'Jan 2020 - Dec 2022')")
    location: Optional[str] = Field(default=None, description="Work location")
    achievements: List[str] = Field(default_factory=list, description="Quantifiable achievements and responsibilities")
    technologies: List[str] = Field(default_factory=list, description="Technologies/tools used")


class Education(BaseModel):
    """Education entry."""
    institution: str = Field(description="School/University name")
    degree: str = Field(description="Degree type and field of study")
    graduation: Optional[str] = Field(default=None, description="Graduation year or date")
    gpa: Optional[str] = Field(default=None, description="GPA if mentioned")
    honors: List[str] = Field(default_factory=list, description="Academic honors or achievements")


class ResumeAnalysis(BaseModel):
    """Structured resume analysis output."""
    personal_info: PersonalInfo
    professional_summary: Optional[str] = Field(default=None, description="Professional summary or objective")
    work_experience: List[WorkExperience] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list, description="Skills and technologies")
    # soft_skills: List[str] = Field(default_factory=list, description="Soft skills and competencies")
    # certifications: List[str] = Field(default_factory=list, description="Professional certifications")
    # languages: List[str] = Field(default_factory=list, description="Spoken languages")
    total_experience_years: Optional[float] = Field(default=None, description="Total years of relevant experience")
    key_achievements: List[str] = Field(default_factory=list, description="Top quantifiable achievements")


class JobRequirements(BaseModel):
    """Job requirements and qualifications."""
    required_skills: List[str] = Field(default_factory=list, description="Must-have skills")
    preferred_skills: List[str] = Field(default_factory=list, description="Nice-to-have skills")
    experience_level: Optional[str] = Field(default=None, description="Required experience level")
    education_requirements: List[str] = Field(default_factory=list, description="Education requirements")
    # certifications: List[str] = Field(default_factory=list, description="Required/preferred certifications")


class JobDetails(BaseModel):
    """Core job posting information."""
    company: str = Field(description="Company name")
    job_title: str = Field(description="Position title")
    department: Optional[str] = Field(default=None, description="Department or team")
    location: Optional[str] = Field(default=None, description="Job location")
    employment_type: Optional[str] = Field(default=None, description="Full-time, Part-time, Contract, etc.")
    salary_range: Optional[str] = Field(default=None, description="Salary information if provided")
    job_description: str = Field(description="Main job description text")
    responsibilities: List[str] = Field(default_factory=list, description="Key responsibilities")
    requirements: JobRequirements = Field(default_factory=JobRequirements)
    # benefits: List[str] = Field(default_factory=list, description="Benefits and perks")
    application_deadline: Optional[str] = Field(default=None, description="Application deadline if mentioned")


class CompanyInfo(BaseModel):
    """Company research information."""
    name: str = Field(description="Company name")
    industry: Optional[str] = Field(default=None, description="Industry/sector")
    size: Optional[str] = Field(default=None, description="Company size (employees)")
    recent_news: List[str] = Field(default_factory=list, description="Recent company news/developments")
    main_business: Optional[str] = Field(default=None, description="Main business/products/services")
    notes: Optional[str] = Field(default=None, description="Additional company information (culture, values, mission, competitors, funding, etc.)")


class JobResearch(BaseModel):
    """Complete job and company research output."""
    job_details: JobDetails
    company_info: CompanyInfo
    job_url: Optional[str] = Field(default=None, description="Original job posting URL")
    market_insights: List[str] = Field(default_factory=list, description="Industry/market insights")
    application_tips: List[str] = Field(default_factory=list, description="Specific application advice")


class CoverLetterOutput(BaseModel):
    """Structured cover letter output."""
    content: str = Field(description="Complete cover letter text in markdown format")
    word_count: int = Field(description="Number of words in the cover letter")
    key_points_covered: List[str] = Field(default_factory=list, description="Key points addressed")
    company_specific_mentions: List[str] = Field(default_factory=list, description="Company-specific information mentioned")
    quantified_achievements: List[str] = Field(default_factory=list, description="Quantified achievements included")
    generated_date: Optional[str] = Field(default=None, description="When cover letter was generated (ISO format)")


class SessionState(BaseModel):
    """Complete session state structure."""
    resume_analysis: Optional[ResumeAnalysis] = Field(default=None, description="Structured resume analysis")
    job_research: Optional[JobResearch] = Field(default=None, description="Structured job and company research")
    cover_letter: Optional[CoverLetterOutput] = Field(default=None, description="Generated cover letter")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    created_at: Optional[str] = Field(default=None, description="Session creation time (ISO format)")
    updated_at: Optional[str] = Field(default=None, description="Last update time (ISO format)")