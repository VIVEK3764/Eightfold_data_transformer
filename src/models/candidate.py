from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class Skill(BaseModel):
    """
    Represents a normalized skill after merge and confidence assignment.
    """
    name: str
    confidence: float = 0.0
    confidence_reason: List[str] = Field(default_factory=list)

class Experience(BaseModel):
    """
    Represents a single work experience entry.
    """
    company: str
    title: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    summary: Optional[str] = None

class Education(BaseModel):
    """
    Represents a single education record.
    """
    institution: str
    degree: Optional[str] = None
    field: Optional[str] = None
    end_year: Optional[int] = None

class Provenance(BaseModel):
    """
    Tracks where every merged field originated.
    """
    field: str
    value: str
    source: str
    method: str
    source_confidence: float = 0.0

class Candidate(BaseModel):
    """
    Represents the final canonical candidate profile produced by the pipeline.
    """
    candidate_id: str
    full_name: Optional[str] = None
    emails: List[str] = Field(default_factory=list)
    phones: List[str] = Field(default_factory=list)
    location: Dict[str, Any] = Field(default_factory=dict)
    links: Dict[str, Any] = Field(default_factory=dict)
    headline: Optional[str] = None
    years_experience: Optional[int] = None
    skills: List[Skill] = Field(default_factory=list)
    experience: List[Experience] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    provenance: List[Provenance] = Field(default_factory=list)
    overall_confidence: float = 0.0
