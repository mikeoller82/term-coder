from __future__ import annotations

import re
import hashlib
from dataclasses import dataclass
from typing import Dict, List, Optional, Pattern, Set, Tuple
from pathlib import Path
import json


@dataclass
class SecretPattern:
    """Defines a pattern for detecting secrets."""
    name: str
    pattern: Pattern[str]
    description: str
    severity: str  # "high", "medium", "low"


@dataclass
class SecretMatch:
    """Represents a detected secret."""
    pattern_name: str
    text: str
    start: int
    end: int
    severity: str
    redacted_text: str


class SecretDetector:
    """Detects and redacts secrets from text content."""
    
    def __init__(self):
        self.patterns = self._load_default_patterns()
        self.custom_patterns: List[SecretPattern] = []
    
    def _load_default_patterns(self) -> List[SecretPattern]:
        """Load default secret detection patterns."""
        return [
            SecretPattern(
                name="api_key",
                pattern=re.compile(r'\b[A-Za-z0-9]{20,}\b', re.IGNORECASE),
                description="Generic API key pattern",
                severity="medium"
            ),
            SecretPattern(
                name="openai_key",
                pattern=re.compile(r'sk-[A-Za-z0-9]{48}', re.IGNORECASE),
                description="OpenAI API key",
                severity="high"
            ),
            SecretPattern(
                name="anthropic_key", 
                pattern=re.compile(r'sk-ant-[A-Za-z0-9\-_]{95}', re.IGNORECASE),
                description="Anthropic API key",
                severity="high"
            ),
            SecretPattern(
                name="github_token",
                pattern=re.compile(r'gh[pousr]_[A-Za-z0-9]{36}', re.IGNORECASE),
                description="GitHub token",
                severity="high"
            ),
            SecretPattern(
                name="aws_access_key",
                pattern=re.compile(r'AKIA[0-9A-Z]{16}', re.IGNORECASE),
                description="AWS Access Key ID",
                severity="high"
            ),
            SecretPattern(
                name="aws_secret_key",
                pattern=re.compile(r'[A-Za-z0-9/+=]{40}', re.IGNORECASE),
                description="AWS Secret Access Key",
                severity="high"
            ),
            SecretPattern(
                name="jwt_token",
                pattern=re.compile(r'eyJ[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_.+/=]*', re.IGNORECASE),
                description="JWT Token",
                severity="medium"
            ),
            SecretPattern(
                name="password_field",
                pattern=re.compile(r'(?:password|passwd|pwd)\s*[:=]\s*["\']?([^"\'\s]+)', re.IGNORECASE),
                description="Password in configuration",
                severity="high"
            ),
            SecretPattern(
                name="private_key",
                pattern=re.compile(r'-----BEGIN [A-Z ]+PRIVATE KEY-----', re.IGNORECASE),
                description="Private key header",
                severity="high"
            ),
            SecretPattern(
                name="email",
                pattern=re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
                description="Email address",
                severity="low"
            ),
            SecretPattern(
                name="phone_number",
                pattern=re.compile(r'\b\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'),
                description="Phone number",
                severity="low"
            ),
            SecretPattern(
                name="credit_card",
                pattern=re.compile(r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b'),
                description="Credit card number",
                severity="high"
            ),
            SecretPattern(
                name="ssn",
                pattern=re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
                description="Social Security Number",
                severity="high"
            ),
        ]
    
    def add_custom_pattern(self, pattern: SecretPattern) -> None:
        """Add a custom secret detection pattern."""
        self.custom_patterns.append(pattern)
    
    def detect_secrets(self, text: str) -> List[SecretMatch]:
        """Detect secrets in the given text."""
        matches = []
        all_patterns = self.patterns + self.custom_patterns
        
        for pattern in all_patterns:
            for match in pattern.pattern.finditer(text):
                redacted = self._redact_match(match.group(), pattern.name)
                matches.append(SecretMatch(
                    pattern_name=pattern.name,
                    text=match.group(),
                    start=match.start(),
                    end=match.end(),
                    severity=pattern.severity,
                    redacted_text=redacted
                ))
        
        # Sort by position to handle overlapping matches
        matches.sort(key=lambda x: x.start)
        return self._remove_overlapping_matches(matches)
    
    def _remove_overlapping_matches(self, matches: List[SecretMatch]) -> List[SecretMatch]:
        """Remove overlapping matches, keeping higher severity ones."""
        if not matches:
            return matches
        
        severity_order = {"high": 3, "medium": 2, "low": 1}
        result = []
        
        for match in matches:
            # Check if this match overlaps with any existing match
            overlaps = False
            for existing in result:
                if (match.start < existing.end and match.end > existing.start):
                    # Overlapping - keep the higher severity one
                    if severity_order.get(match.severity, 0) > severity_order.get(existing.severity, 0):
                        result.remove(existing)
                        result.append(match)
                    overlaps = True
                    break
            
            if not overlaps:
                result.append(match)
        
        return sorted(result, key=lambda x: x.start)
    
    def _redact_match(self, text: str, pattern_name: str) -> str:
        """Generate redacted version of matched text."""
        if len(text) <= 4:
            return "[REDACTED]"
        
        # Show first 2 and last 2 characters for context
        return f"{text[:2]}{'*' * (len(text) - 4)}{text[-2:]}"
    
    def redact_secrets(self, text: str) -> Tuple[str, List[SecretMatch]]:
        """Redact secrets from text and return redacted text with matches."""
        matches = self.detect_secrets(text)
        
        if not matches:
            return text, matches
        
        # Apply redactions from end to start to preserve positions
        redacted_text = text
        for match in reversed(matches):
            redacted_text = (
                redacted_text[:match.start] + 
                match.redacted_text + 
                redacted_text[match.end:]
            )
        
        return redacted_text, matches


class PrivacyManager:
    """Manages privacy settings and data handling policies."""
    
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.privacy_config_path = config_dir / "privacy.json"
        self.consent_path = config_dir / "consent.json"
        self.detector = SecretDetector()
        self._load_privacy_config()
        self._load_consent_data()
    
    def _load_privacy_config(self) -> None:
        """Load privacy configuration."""
        default_config = {
            "redact_secrets": True,
            "log_prompts": False,
            "offline_mode": False,
            "data_retention_days": 30,
            "allowed_domains": [],
            "blocked_patterns": [],
            "audit_level": "basic"  # "none", "basic", "detailed"
        }
        
        if self.privacy_config_path.exists():
            try:
                with open(self.privacy_config_path) as f:
                    loaded = json.load(f)
                self.privacy_config = {**default_config, **loaded}
            except Exception:
                self.privacy_config = default_config
        else:
            self.privacy_config = default_config
            self._save_privacy_config()
    
    def _save_privacy_config(self) -> None:
        """Save privacy configuration."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.privacy_config_path, 'w') as f:
            json.dump(self.privacy_config, f, indent=2)
    
    def _load_consent_data(self) -> None:
        """Load user consent data."""
        default_consent = {
            "data_collection": False,
            "analytics": False,
            "model_training": False,
            "error_reporting": False,
            "consent_version": "1.0",
            "consent_date": None
        }
        
        if self.consent_path.exists():
            try:
                with open(self.consent_path) as f:
                    loaded = json.load(f)
                self.consent_data = {**default_consent, **loaded}
            except Exception:
                self.consent_data = default_consent
        else:
            self.consent_data = default_consent
    
    def _save_consent_data(self) -> None:
        """Save user consent data."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.consent_path, 'w') as f:
            json.dump(self.consent_data, f, indent=2)
    
    def update_privacy_setting(self, key: str, value: any) -> None:
        """Update a privacy setting."""
        if key in self.privacy_config:
            self.privacy_config[key] = value
            self._save_privacy_config()
        else:
            raise ValueError(f"Unknown privacy setting: {key}")
    
    def update_consent(self, consent_type: str, granted: bool) -> None:
        """Update user consent for a specific data usage type."""
        if consent_type in self.consent_data:
            self.consent_data[consent_type] = granted
            if granted and not self.consent_data.get("consent_date"):
                from datetime import datetime
                self.consent_data["consent_date"] = datetime.now().isoformat()
            self._save_consent_data()
        else:
            raise ValueError(f"Unknown consent type: {consent_type}")
    
    def can_collect_data(self) -> bool:
        """Check if data collection is allowed."""
        return self.consent_data.get("data_collection", False)
    
    def can_send_analytics(self) -> bool:
        """Check if analytics can be sent."""
        return self.consent_data.get("analytics", False)
    
    def can_use_for_training(self) -> bool:
        """Check if data can be used for model training."""
        return self.consent_data.get("model_training", False)
    
    def can_report_errors(self) -> bool:
        """Check if error reporting is allowed."""
        return self.consent_data.get("error_reporting", False)
    
    def should_redact_secrets(self) -> bool:
        """Check if secrets should be redacted."""
        return self.privacy_config.get("redact_secrets", True)
    
    def should_log_prompts(self) -> bool:
        """Check if prompts should be logged."""
        return self.privacy_config.get("log_prompts", False)
    
    def is_offline_mode(self) -> bool:
        """Check if offline mode is enabled."""
        return self.privacy_config.get("offline_mode", False)
    
    def get_audit_level(self) -> str:
        """Get the current audit logging level."""
        return self.privacy_config.get("audit_level", "basic")
    
    def process_text_for_privacy(self, text: str, context: str = "") -> Tuple[str, Dict]:
        """Process text according to privacy settings."""
        metadata = {
            "original_length": len(text),
            "context": context,
            "redacted": False,
            "secrets_found": []
        }
        
        if self.should_redact_secrets():
            redacted_text, matches = self.detector.redact_secrets(text)
            if matches:
                metadata["redacted"] = True
                metadata["secrets_found"] = [
                    {
                        "pattern": match.pattern_name,
                        "severity": match.severity,
                        "position": f"{match.start}-{match.end}"
                    }
                    for match in matches
                ]
            return redacted_text, metadata
        
        return text, metadata


def create_privacy_manager(config_dir: Path) -> PrivacyManager:
    """Factory function to create a PrivacyManager instance."""
    return PrivacyManager(config_dir)