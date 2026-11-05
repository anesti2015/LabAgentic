import os
from enum import Enum
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client()
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

class SeverityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class LogAnalysis(BaseModel):
    severity: SeverityLevel = Field(
        description="Incident severity. CRITICAL if an attacker gained privileged (root/admin) access "
                    "or authentication was bypassed; HIGH for active exploitation attempts; "
                    "MEDIUM for suspicious but unsuccessful activity; LOW for routine events."
    )
    error_code: int = Field(
        description="Numeric error code copied exactly from the log (e.g. from 'ErrorCode=NNN'). "
                    "Use -1 if the log contains no error code."
    )
    is_compromised: bool = Field(
        description="True if the log shows a successful unauthorized access, a successful privileged login "
                    "from an external IP, or an authentication bypass. Otherwise false."
    )
    summary: str = Field(description="One-sentence technical summary of the event")
    recommended_fix: list[str] = Field(
        description="Ordered list of concrete remediation steps (one action or shell command per item)."
    )

SYSTEM_PROMPT = """
# ROLE
You are a senior SOC/SIEM analyst who triages raw Linux server logs for security incidents.

# CLASSIFICATION RULES
- A successful login as root from an external IP address is a security incident.
- Any mention of an authentication bypass (e.g. "bypassed", PAM bug) means the system IS compromised.
- Successful privileged access or authentication bypass => severity CRITICAL, is_compromised = true.
- Extract error_code exactly as the integer that appears in the log (e.g. "ErrorCode=401" -> 401).
  If no error code appears, use -1.

# OUTPUT CONTRACT
- Fill every field of the schema.
- summary: exactly one sentence.
- recommended_fix: at least one concrete, actionable step (e.g. disable root SSH login,
  block the source IP, patch PAM, rotate credentials, audit for persistence).
- Base every value only on evidence in the log; do not invent facts.
"""

def parse_server_log(raw_log: str) -> LogAnalysis:
    response = client.models.generate_content(
        model=MODEL,
        contents=f"Analyze the following raw server log:\n{raw_log}",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.0,
            response_mime_type="application/json",
            response_schema=LogAnalysis,
        ),
    )
    # Validate and deserialize JSON string directly into the Pydantic object
    return LogAnalysis.model_validate_json(response.text)

if __name__ == "__main__":
    sample = (
        "2026-10-15 02:11:44 [ALERT] sshd[9012]: Accepted password for root "
        "from 198.51.100.77 port 44122 ssh2 (ErrorCode=401 bypassed via PAM bug)"
    )
    print(parse_server_log(sample).model_dump_json(indent=2))

# --- Automated Unit Test (Run with: pytest test_module2_structured.py) ---
def test_ssh_breach_log_parsing():
    sample_log = (
        "2026-10-15 02:11:44 [ALERT] sshd[9012]: Accepted password for root "
        "from 198.51.100.77 port 44122 ssh2 (ErrorCode=401 bypassed via PAM bug)"
    )
    result = parse_server_log(sample_log)

    assert result.severity in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]
    assert result.error_code == 401
    assert result.is_compromised is True
    assert len(result.recommended_fix) >= 1