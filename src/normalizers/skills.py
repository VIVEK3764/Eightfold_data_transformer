SKILL_MAP = {
    "cpp": "C++",
    "c plus plus": "C++",
    "cplusplus": "C++",
    "js": "JavaScript",
    "javascript": "JavaScript",
    "py": "Python",
    "nodejs": "Node.js",
    "node": "Node.js",
    "springboot": "Spring Boot",
    "spring boot": "Spring Boot"
}

def normalize_skill(skill: str) -> str:
    """
    Normalizes a skill name by trimming whitespace and lowercasing for lookup.
    Maps known aliases to canonical skill names, otherwise returns the cleaned skill.
    """
    if not skill:
        return ""
        
    cleaned = skill.strip()
    lower_cleaned = cleaned.lower()
    
    if lower_cleaned in SKILL_MAP:
        return SKILL_MAP[lower_cleaned]
        
    # Return cleaned skill (preserve original casing if mixed, or title-case if lowercase)
    if cleaned.islower():
        return cleaned.title()
    return cleaned
