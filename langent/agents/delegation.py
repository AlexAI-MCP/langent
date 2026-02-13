"""
Sub-Agent Delegation — specialized task handlers
===================================================
Manages specialized agents (Researcher, Analyst, Coder, etc.)
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class SubAgent(BaseModel):
    name: str
    role: str
    goal: str
    backstory: str


class SubAgentManager:
    """서브에이전트 관리 및 위임"""
    
    def __init__(self):
        self.agents: Dict[str, SubAgent] = {
            "researcher": SubAgent(
                name="Research Agent",
                role="Senior Researcher",
                goal="Find and synthesize deep information from the knowledge base",
                backstory="You are an expert at searching across large datasets and identifying key insights."
            ),
            "analyst": SubAgent(
                name="Analysis Agent",
                role="Strategic Analyst",
                goal="Evaluate data and provide actionable recommendations",
                backstory="You have a background in data science and business strategy, focused on logical deduction."
            ),
            "creator": SubAgent(
                name="Creative Agent",
                role="Content Architect",
                goal="Draft beautiful reports, charts, and visualizations",
                backstory="You are a master of design and communication, turning complex data into stunning visuals."
            )
        }

    def select_agent(self, task: str) -> SubAgent:
        """태스크에 적합한 에이전트 선택 (간단한 키워드 기반)"""
        task_l = task.lower()
        if any(kw in task_l for kw in ["검색", "조사", "찾아", "research", "find"]):
            return self.agents["researcher"]
        if any(kw in task_l for kw in ["분석", "평가", "계획", "analyze", "evaluate"]):
            return self.agents["analyst"]
            
        return self.agents["creator"]
