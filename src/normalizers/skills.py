SKILL_MAP = {
    # C++
    "cpp": "C++",
    "c plus plus": "C++",
    "cplusplus": "C++",
    "c++": "C++",
    # JavaScript / TypeScript
    "js": "JavaScript",
    "javascript": "JavaScript",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    # Python
    "py": "Python",
    "python": "Python",
    # Java
    "java": "Java",
    # Node.js
    "nodejs": "Node.js",
    "node": "Node.js",
    "node.js": "Node.js",
    # Spring
    "springboot": "Spring Boot",
    "spring boot": "Spring Boot",
    "spring": "Spring",
    # React
    "react": "React",
    "reactjs": "React",
    "react.js": "React",
    # Vue
    "vue": "Vue.js",
    "vuejs": "Vue.js",
    "vue.js": "Vue.js",
    # Angular
    "angular": "Angular",
    "angularjs": "Angular",
    # Cloud
    "aws": "AWS",
    "amazon web services": "AWS",
    "gcp": "GCP",
    "google cloud": "GCP",
    "google cloud platform": "GCP",
    "azure": "Azure",
    "microsoft azure": "Azure",
    # Containers / Infra
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "terraform": "Terraform",
    "ansible": "Ansible",
    # Data
    "sql": "SQL",
    "mysql": "MySQL",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "mongodb": "MongoDB",
    "mongo": "MongoDB",
    "redis": "Redis",
    # ML / AI
    "ml": "Machine Learning",
    "machine learning": "Machine Learning",
    "deep learning": "Deep Learning",
    "dl": "Deep Learning",
    "nlp": "NLP",
    "natural language processing": "NLP",
    # Tools
    "git": "Git",
    "github": "GitHub",
    "linux": "Linux",
    "bash": "Bash",
    "go": "Go",
    "golang": "Go",
    "rust": "Rust",
    "kotlin": "Kotlin",
    "swift": "Swift",
    "scala": "Scala",
}


def normalize_skill(skill: str) -> str:
    """
    Normalises a skill name:
      1. Strip whitespace.
      2. Look up in SKILL_MAP (case-insensitive).
      3. Fall back to title-case for all-lowercase input, otherwise preserve casing.
    """
    if not skill:
        return ""

    cleaned = skill.strip()
    lower_cleaned = cleaned.lower()

    if lower_cleaned in SKILL_MAP:
        return SKILL_MAP[lower_cleaned]

    # Preserve original casing for mixed-case (e.g. "GraphQL"), title-case pure lowercase
    if cleaned.islower():
        return cleaned.title()
    return cleaned
