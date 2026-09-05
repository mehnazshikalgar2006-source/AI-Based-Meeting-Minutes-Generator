"""
Security Sanitizer Module
Ensures API keys, tokens, credentials, and secrets are strictly redacted and never
exposed in meeting minutes, discussion points, action items, logs, error messages,
PDFs, Word documents, or UI views.
"""

import os
import re
from typing import Any, Dict, List, Union

REDACTED_LABEL = "[REDACTED_SECRET]"

SECRET_PATTERNS = [
    # Google API Keys (AIza... or AQ....)
    re.compile(r'\bAIza[0-9A-Za-z\-_]{25,50}\b'),
    re.compile(r'\bAQ\.[0-9A-Za-z\-_]{15,70}\b'),
    
    # OpenAI API Keys
    re.compile(r'\bsk-[A-Za-z0-9\-_]{15,70}\b'),
    
    # Anthropic API Keys
    re.compile(r'\bsk-ant-[A-Za-z0-9\-_]{15,70}\b'),
    
    # GitHub / GitLab / Slack Tokens
    re.compile(r'\bgh[pousr]_[A-Za-z0-9]{30,50}\b'),
    re.compile(r'\bxox[baprs]-[0-9A-Za-z\-]{10,}\b'),
    
    # AWS Access Keys
    re.compile(r'\bAKIA[0-9A-Z]{16}\b'),
    
    # Generic Private Keys
    re.compile(r'-----BEGIN [A-Z\s]+PRIVATE KEY-----[\s\S]*?-----END [A-Z\s]+PRIVATE KEY-----'),
    
    # Bearer Tokens / JWT
    re.compile(r'Bearer\s+[A-Za-z0-9\-_.~+/=]{15,}', re.IGNORECASE),
    re.compile(r'\beyJ[A-Za-z0-9\-_]{10,}\.[A-Za-z0-9\-_]{10,}\.[A-Za-z0-9\-_]{10,}\b'),
    
    # Sensitive assignment patterns like api_key=..., password=..., secret=...
    re.compile(r'(?i)(?:api[_-]?key|secret[_-]?key|auth[_-]?token|password|access[_-]?token)[\s:=]+["\']?([A-Za-z0-9\-_.~]{8,})["\']?')
]

def get_configured_env_secrets() -> List[str]:
    """Retrieves all non-empty API keys and secrets stored in environment."""
    secrets = []
    target_vars = [
        "GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY", "AWS_SECRET_ACCESS_KEY", "SECRET_KEY"
    ]
    for var in target_vars:
        val = os.getenv(var, "").strip()
        if val and len(val) >= 6:
            secrets.append(val)
    return secrets

def sanitize_text(text: str) -> str:
    """
    Redacts all secrets, API keys, credentials, and sensitive parameters from text.
    """
    if not text or not isinstance(text, str):
        return text if text is not None else ""

    sanitized = text

    # 1. Exact match against configured environment secrets
    for secret in get_configured_env_secrets():
        if secret in sanitized:
            sanitized = sanitized.replace(secret, REDACTED_LABEL)

    # 2. Pattern-based redaction
    for pattern in SECRET_PATTERNS:
        if pattern.groups > 0:
            def _replace_group(match):
                full = match.group(0)
                secret_val = match.group(1)
                return full.replace(secret_val, REDACTED_LABEL)
            sanitized = pattern.sub(_replace_group, sanitized)
        else:
            sanitized = pattern.sub(REDACTED_LABEL, sanitized)

    return sanitized

def sanitize_meeting_data(data: Union[Dict[str, Any], List[Any], str, Any]) -> Any:
    """
    Recursively traverses dictionaries, lists, and strings to sanitize all text fields.
    """
    if isinstance(data, str):
        return sanitize_text(data)
    elif isinstance(data, list):
        return [sanitize_meeting_data(item) for item in data]
    elif isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            cleaned[k] = sanitize_meeting_data(v)
        return cleaned
    return data

def mask_api_key(key: str) -> str:
    """
    Masks an API key for safe UI display (never reveals raw characters).
    """
    if not key or not key.strip():
        return ""
    return "••••••••••••••••"
