"""
Pydantic models for structured JSON output types.
"""

from pydantic import BaseModel


class CodingOutput(BaseModel):
    code: str
    language: str
    explanation: str
