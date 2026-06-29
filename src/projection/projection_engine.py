import re
from typing import Any, Dict, List

class ProjectionError(Exception):
    """
    Raised when projection path resolution fails and the policy is 'error'.
    """
    pass

def resolve_path(data: Any, path_parts: List[str]) -> Any:
    """
    Recursively resolves a list of path parts against a candidate object/dict structure.
    Supports index offsets like emails[0] and list mapping like skills[].name.
    """
    if not path_parts:
        return data
        
    part = path_parts[0]
    remaining = path_parts[1:]
    
    # Handle list mapping operator, e.g. 'skills[]'
    if part.endswith("[]"):
        attr = part[:-2]
        if isinstance(data, dict):
            val = data.get(attr)
        else:
            val = getattr(data, attr, None)
            
        if val is None:
            return []
        if not isinstance(val, list):
            raise TypeError(f"Expected list at '{attr}', got '{type(val).__name__}'")
            
        # Map remaining path onto all items in the list
        results = []
        for item in val:
            try:
                res = resolve_path(item, remaining)
                results.append(res)
            except (KeyError, IndexError, TypeError, AttributeError):
                results.append(None)
        return results

    # Handle standard attribute with optional index, e.g., 'emails[0]' or 'full_name'
    match = re.match(r"^([a-zA-Z0-9_]+)(?:\[(\d+)\])?$", part)
    if not match:
        raise KeyError(f"Invalid path component: {part}")
        
    attr, index_str = match.groups()
    
    # Extract attribute/key
    if isinstance(data, dict):
        if attr not in data:
            raise KeyError(f"Key not found: {attr}")
        val = data[attr]
    else:
        if not hasattr(data, attr):
            raise KeyError(f"Attribute not found: {attr}")
        val = getattr(data, attr)
        
    # Apply list indexing if index was provided
    if index_str is not None:
        index = int(index_str)
        if not isinstance(val, list):
            raise TypeError(f"Expected list at '{attr}', got '{type(val).__name__}'")
        if index < 0 or index >= len(val):
            raise IndexError(f"Index {index} out of range for list '{attr}'")
        val = val[index]
        
    return resolve_path(val, remaining)

def project_field(candidate: Any, from_path: str) -> Any:
    """
    Resolves the value of a single field from Candidate using resolve_path.
    """
    # Candidate can be converted to dict to be general, or we can pass the candidate object directly.
    # To keep it fully robust, we convert Candidate model to dict.
    # We do a quick check if candidate has model_dump method.
    if hasattr(candidate, "model_dump"):
        candidate_dict = candidate.model_dump()
    else:
        candidate_dict = candidate
        
    parts = from_path.split(".")
    return resolve_path(candidate_dict, parts)

def apply_missing_policy(path: str, policy: str) -> Any:
    """
    Applies the specified missing value policy (null, omit, error).
    """
    policy = policy.lower().strip()
    if policy == "null":
        return None
    elif policy == "omit":
        # Handled in the parent loop by not setting the field
        return None
    elif policy == "error":
        raise ProjectionError(f"Field path '{path}' was missing or could not be resolved.")
    else:
        return None

def project(candidate: Any, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Projects a Candidate profile into a customized output structure based on config.
    Does not modify the candidate object.
    """
    fields_config = config.get("fields", [])
    include_confidence = config.get("include_confidence", False)
    include_provenance = config.get("include_provenance", False)
    on_missing = config.get("on_missing", "null").lower().strip()
    
    output = {}
    
    # 1. Project specified fields
    for field in fields_config:
        path = field.get("path")
        from_path = field.get("from") or path
        
        if not path:
            continue
            
        try:
            val = project_field(candidate, from_path)
            # If the path resolved successfully, set it
            output[path] = val
        except (KeyError, IndexError, TypeError, AttributeError):
            # Resolve missing policy
            if on_missing == "omit":
                continue
            elif on_missing == "error":
                raise ProjectionError(f"Required path '{from_path}' is missing.")
            else:
                output[path] = None
                
    # 2. Confidence Toggle
    if include_confidence:
        overall_conf = getattr(candidate, "overall_confidence", 0.0)
        output["overall_confidence"] = overall_conf
        
    # 3. Provenance Toggle
    if include_provenance:
        prov = getattr(candidate, "provenance", [])
        # Serialize Provenance objects to dictionary list
        output["provenance"] = [
            p.model_dump() if hasattr(p, "model_dump") else p
            for p in prov
        ]
        
    return output
