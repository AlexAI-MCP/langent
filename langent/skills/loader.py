"""
Skill Loader — Discover and execute skills
============================================
Skills are defined in SKILL.md format and can be executed by agents.
"""
import os
import yaml
from typing import List, Dict, Any, Optional


class Skill:
    """단일 스킬 정의"""
    def __init__(self, name: str, description: str, instructions: str, metadata: Dict = None):
        self.name = name
        self.description = description
        self.instructions = instructions
        self.metadata = metadata or {}

    def __repr__(self):
        return f"<Skill(name='{self.name}')>"


class SkillLoader:
    """스킬 발견 및 로딩"""
    
    def __init__(self, skills_dir: Optional[str] = None):
        self.skills_dir = skills_dir or os.path.join(os.getcwd(), "skills")
        self.skills: Dict[str, Skill] = {}
        
    def discover(self) -> List[str]:
        """디렉토리에서 스킬을 발견합니다."""
        if not os.path.exists(self.skills_dir):
            return []
            
        found = []
        for item in os.listdir(self.skills_dir):
            item_path = os.path.join(self.skills_dir, item)
            if os.path.isdir(item_path):
                # Look for SKILL.md
                skill_md = os.path.join(item_path, "SKILL.md")
                if os.path.exists(skill_md):
                    found.append(item)
                    
        return found
        
    def load(self, skill_name: str) -> Optional[Skill]:
        """특정 스킬을 로드합니다."""
        skill_path = os.path.join(self.skills_dir, skill_name, "SKILL.md")
        if not os.path.exists(skill_path):
            return None
            
        with open(skill_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Parse YAML frontmatter (simplified)
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                metadata = yaml.safe_load(parts[1])
                instructions = parts[2].strip()
                skill = Skill(
                    name=metadata.get("name", skill_name),
                    description=metadata.get("description", ""),
                    instructions=instructions,
                    metadata=metadata
                )
                self.skills[skill_name] = skill
                return skill
        
        return None

    def load_all(self):
        """모든 스킬 로드"""
        for name in self.discover():
            self.load(name)
        return self.skills
