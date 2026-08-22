import re

COMMAND_PATTERNS = {
    "safety_stop": re.compile(r"\b(?:stop|halt|pause|freeze)\b", re.I),
    "safety_resume": re.compile(r"\b(?:resume|continue|start)\b", re.I),
    "shutdown": re.compile(r"\b(?:exit|quit|shutdown|terminate)\b", re.I),
    
    "pick_place": re.compile(r"pick\s+up\s+(?P<src>\w+)\s+and\s+(?:put|place)\s+(?:over|on|near)\s+(?P<dst>\w+)", re.I),
    "parallel": re.compile(r"place\s+(?P<src>\w+)\s+parallel\s+to\s+(?P<dst>\w+)", re.I),
    "rotate": re.compile(r"rotate\s+(?P<target>\w+)\s+(?P<angle>\d+)\s+degrees?", re.I),
    
    "save_preset": re.compile(r"save\s+preset\s+(?P<name>\w+)", re.I),
    "load_preset": re.compile(r"load\s+preset\s+(?P<name>\w+)", re.I),
}

def parse_transcript(text: str):
    """
    Parses a recognized Vosk string and returns (action_key, params_dict).
    Returns (None, {}) if no match is found.
    """
    cleaned = text.strip().lower()
    if not cleaned:
        return None, {}

    for action, pattern in COMMAND_PATTERNS.items():
        match = pattern.search(cleaned)
        if match:
            return action, match.groupdict()

    return "unknown", {"raw_text": cleaned}