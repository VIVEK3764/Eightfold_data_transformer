import re
from typing import List, Dict, Any

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# Broad regex to capture various phone formats (digits, dots, dashes, spaces, parens)
PHONE_REGEX = re.compile(r"\+?[0-9][0-9\-.\s()]{8,18}[0-9]")

COMMON_SKILL_WORDS = [
    # Programming Languages
    "python", "py", "java", "javascript", "js", "cpp", "c++", "c plus plus", "cplusplus",
    "c#", "csharp", "ruby", "php", "go", "golang", "rust", "typescript", "ts", "swift", "kotlin", "scala",
    # Frameworks & Libraries
    "react", "angular", "vue", "nodejs", "node.js", "node", "express", "django", "flask", "springboot", 
    "spring boot", "spring", "hibernate", "laravel", "dotnet", "net core", "tensorflow", "pytorch",
    # Databases & Tools
    "sql", "mysql", "postgresql", "postgres", "mongodb", "redis", "elasticsearch", "sqlite", "oracle",
    "git", "docker", "kubernetes", "k8s", "aws", "gcp", "azure", "jenkins", "terraform", "ansible",
    # Concepts/Other
    "machine learning", "ml", "artificial intelligence", "ai", "deep learning", "nlp", "data science",
    "html", "css", "xml", "json", "rest", "api", "graphql", "microservices", "agile", "scrum"
]

def create_provenance(field: str, value: Any, source: str, method: str, source_confidence: float) -> Dict[str, Any]:
    """
    Creates a standardized raw provenance dictionary.
    """
    return {
        "field": field,
        "value": str(value) if value is not None else "",
        "source": source,
        "method": method,
        "source_confidence": source_confidence
    }

def clean_text(text: str) -> str:
    """
    Basic text cleaning (remove null bytes, fix line endings).
    """
    if not text:
        return ""
    return text.replace("\u0000", "").replace("\r\n", "\n")

def extract_emails(text: str) -> List[str]:
    """
    Helper to extract all emails from text.
    """
    if not text:
        return []
    return list(set(EMAIL_REGEX.findall(text)))

def extract_phones(text: str) -> List[str]:
    """
    Helper to extract all phone numbers from text.
    """
    if not text:
        return []
    # Find all matches
    matches = PHONE_REGEX.findall(text)
    # Deduplicate while preserving format
    cleaned_matches = []
    for m in matches:
        # Keep if it contains at least 5 digits
        if len(re.sub(r"\D", "", m)) >= 7:
            cleaned_matches.append(m.strip())
    return list(set(cleaned_matches))

def extract_skills(text: str) -> List[str]:
    """
    Helper to extract skills matching common skill words in a deterministic case-insensitive search.
    """
    if not text:
        return []
    
    found = []
    # Clean text to remove extra whitespace and punctuation for search
    search_text = " " + re.sub(r"[^\w\s+#.-]", " ", text.lower()) + " "
    
    for skill in COMMON_SKILL_WORDS:
        # Match as whole word, taking care of special characters like c++
        escaped = re.escape(skill)
        # Handle trailing special chars like ++ or #
        if skill.endswith("++") or skill.endswith("#"):
            pattern = rf"\b{escaped}(?=\s|\b)"
        else:
            pattern = rf"\b{escaped}\b"
            
        if re.search(pattern, search_text):
            found.append(skill)
            
    return list(set(found))

COUNTRY_CODES_MAP = {
    "united states": "US", "usa": "US", "us": "US", "united states of america": "US",
    "india": "IN", "ind": "IN", "in": "IN",
    "united kingdom": "GB", "uk": "GB", "gb": "GB", "great britain": "GB",
    "canada": "CA", "can": "CA", "ca": "CA",
    "germany": "DE", "deutschland": "DE", "de": "DE",
    "france": "FR", "fra": "FR", "fr": "FR",
    "australia": "AU", "aus": "AU", "au": "AU"
}

def parse_location(loc_str: str) -> Dict[str, Any]:
    """
    Parses a raw location string into {city, region, country} structure.
    Tries to map country to ISO-3166 alpha-2.
    """
    res = {"city": None, "region": None, "country": None}
    if not loc_str:
        return res
        
    parts = [p.strip() for p in loc_str.split(",") if p.strip()]
    
    if len(parts) == 3:
        res["city"] = parts[0]
        res["region"] = parts[1]
        country_candidate = parts[2]
    elif len(parts) == 2:
        res["city"] = parts[0]
        country_candidate = parts[1]
        norm_cc = country_candidate.lower()
        if norm_cc in COUNTRY_CODES_MAP or len(norm_cc) == 2:
            pass
        else:
            res["region"] = parts[1]
            country_candidate = None
    elif len(parts) == 1:
        norm_cc = parts[0].lower()
        if norm_cc in COUNTRY_CODES_MAP or len(norm_cc) == 2:
            country_candidate = parts[0]
        else:
            res["region"] = parts[0]
            country_candidate = None
    else:
        res["city"] = parts[0]
        res["region"] = parts[1]
        country_candidate = parts[2]
        
    if country_candidate:
        cc_clean = country_candidate.lower()
        if cc_clean in COUNTRY_CODES_MAP:
            res["country"] = COUNTRY_CODES_MAP[cc_clean]
        elif len(country_candidate) == 2:
            res["country"] = country_candidate.upper()
        else:
            res["country"] = country_candidate
            
    return res

def parse_links(links_list: List[str]) -> Dict[str, Any]:
    """
    Parses a list of URL strings into {linkedin, github, portfolio, other[]} links structure.
    """
    res = {
        "linkedin": None,
        "github": None,
        "portfolio": None,
        "other": []
    }
    if not links_list:
        return res
        
    for link in links_list:
        if not link:
            continue
        link_clean = link.strip()
        link_lower = link_clean.lower()
        
        if "linkedin.com" in link_lower:
            if not res["linkedin"]:
                res["linkedin"] = link_clean
            else:
                res["other"].append(link_clean)
        elif "github.com" in link_lower:
            if not res["github"]:
                res["github"] = link_clean
            else:
                res["other"].append(link_clean)
        elif "portfolio" in link_lower or "personal" in link_lower or "website" in link_lower:
            if not res["portfolio"]:
                res["portfolio"] = link_clean
            else:
                res["other"].append(link_clean)
        else:
            if not res["portfolio"] and not any(k in link_lower for k in ["linkedin", "github"]):
                res["portfolio"] = link_clean
            else:
                res["other"].append(link_clean)
                
    return res
