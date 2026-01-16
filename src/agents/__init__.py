"""
Agent 系统
"""
from src.agents.base_agent import BaseAgent
from src.agents.pathologist import PathologistAgent
from src.agents.geneticist import GeneticistAgent
from src.agents.recruiter import RecruiterAgent
from src.agents.oncologist import OncologistAgent
from src.agents.chair import ChairAgent

__all__ = [
    "BaseAgent",
    "PathologistAgent",
    "GeneticistAgent",
    "RecruiterAgent",
    "OncologistAgent",
    "ChairAgent"
]
