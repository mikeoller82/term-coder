from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from term_coder.security import SecretDetector, SecretPattern, PrivacyManager, create_privacy_manager


class TestSecretDetector:
    """Test secret detection and redaction functionality."""
    
    def test_detect_openai_key(self):
        detector = SecretDetector()
        text = "My API key is sk-1234567890abcdef1234567890abcdef12345678"
        matches = detector.detect_secrets(text)
        
        assert len(matches) == 1
        assert matches[0].pattern_name == "openai_key"
        assert matches[0].severity == "high"
        assert "sk-" in matches[0].text
    
    def test_detect_anthropic_key(self):
        detector = SecretDetector()
        text = "ANTHROPIC_API_KEY=sk-ant-api03-abcdefghijklmnopqrstuvwxyz1234567890abcdefghijklmnopqrstuvwxyz1234567890abcdef"
        matches = detector.detect_secrets(text)
        
        assert len(matches) == 1
        assert matches[0].pattern_name == "anthropic_key"
        assert matches[0].severity == "high"
    
    def test_detect_github_token(self):
        detector = SecretDetector()
        text = "export GITHUB_TOKEN=ghp_1234567890abcdef1234567890abcdef12"
        matches = detector.detect_secrets(text)
        
        assert len(matches) == 1
        assert matches[0].pattern_name == "github_token"
        assert matches[0].severity == "high"
    
    def test_detect_aws_keys(self):
        detector = SecretDetector()
        text = """
        AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
        AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
        """
        matches = detector.detect_secrets(text)
        
        # Should detect both AWS keys
        assert len(matches) >= 1
        pattern_names = [m.pattern_name for m in matches]
        assert "aws_access_key" in pattern_names
    
    def test_detect_jwt_token(self):
        detector = SecretDetector()
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        matches = detector.detect_secrets(text)
        
        assert len(matches) == 1
        assert matches[0].pattern_name == "jwt_token"
        assert matches[0].severity == "medium"
    
    def test_detect_password_field(self):
        detector = SecretDetector()
        text = 'password="super_secret_password123"'
        matches = detector.detect_secrets(text)
        
        assert len(matches) == 1
        assert matches[0].pattern_name == "password_field"
        assert matches[0].severity == "high"
    
    def test_detect_email(self):
        detector = SecretDetector()
        text = "Contact us at support@example.com for help"
        matches = detector.detect_secrets(text)
        
        assert len(matches) == 1
        assert matches[0].pattern_name == "email"
        assert matches[0].severity == "low"
    
    def test_detect_phone_number(self):
        detector = SecretDetector()
        text = "Call us at +1-555-123-4567 or (555) 987-6543"
        matches = detector.detect_secrets(text)
        
        assert len(matches) >= 1
        pattern_names = [m.pattern_name for m in matches]
        assert "phone_number" in pattern_names
    
    def test_detect_credit_card(self):
        detector = SecretDetector()
        text = "Credit card: 4111111111111111"
        matches = detector.detect_secrets(text)
        
        assert len(matches) == 1
        assert matches[0].pattern_name == "credit_card"
        assert matches[0].severity == "high"
    
    def test_detect_ssn(self):
        detector = SecretDetector()
        text = "SSN: 123-45-6789"
        matches = detector.detect_secrets(text)
        
        assert len(matches) == 1
        assert matches[0].pattern_name == "ssn"
        assert matches[0].severity == "high"
    
    def test_redact_secrets(self):
        detector = SecretDetector()
        text = "My API key is sk-1234567890abcdef1234567890abcdef12345678 and email is test@example.com"
        
        redacted_text, matches = detector.redact_secrets(text)
        
        assert len(matches) == 2
        assert "sk-" not in redacted_text or "sk-**" in redacted_text  # Should be redacted
        assert "test@example.com" not in redacted_text or "te**@example.com" in redacted_text
    
    def test_custom_pattern(self):
        detector = SecretDetector()
        custom_pattern = SecretPattern(
            name="custom_secret",
            pattern=detector._load_default_patterns()[0].pattern.__class__(r'SECRET_[A-Z0-9]{10}'),
            description="Custom secret pattern",
            severity="high"
        )
        detector.add_custom_pattern(custom_pattern)
        
        text = "The secret is SECRET_ABCD123456"
        matches = detector.detect_secrets(text)
        
        pattern_names = [m.pattern_name for m in matches]
        assert "custom_secret" in pattern_names
    
    def test_overlapping_matches(self):
        detector = SecretDetector()
        # Create text where multiple patterns might match the same text
        text = "sk-1234567890abcdef1234567890abcdef12345678"  # This might match both openai_key and api_key patterns
        
        matches = detector.detect_secrets(text)
        
        # Should handle overlapping matches properly
        assert len(matches) >= 1
        # Higher severity matches should be preferred
        if len(matches) > 1:
            severities = [m.severity for m in matches]
            assert "high" in severities
    
    def test_no_secrets_found(self):
        detector = SecretDetector()
        text = "This is just normal text with no secrets."
        
        redacted_text, matches = detector.redact_secrets(text)
        
        assert len(matches) == 0
        assert redacted_text == text  # Should be unchanged


class TestPrivacyManager:
    """Test privacy management functionality."""
    
    def test_privacy_manager_initialization(self, tmp_path):
        config_dir = tmp_path / ".term-coder"
        privacy_manager = PrivacyManager(config_dir)
        
        assert privacy_manager.config_dir == config_dir
        assert privacy_manager.privacy_config_path.exists()
        assert privacy_manager.consent_path.exists()
    
    def test_default_privacy_settings(self, tmp_path):
        config_dir = tmp_path / ".term-coder"
        privacy_manager = PrivacyManager(config_dir)
        
        assert privacy_manager.should_redact_secrets() == True
        assert privacy_manager.should_log_prompts() == False
        assert privacy_manager.is_offline_mode() == False
        assert privacy_manager.get_audit_level() == "basic"
    
    def test_default_consent_settings(self, tmp_path):
        config_dir = tmp_path / ".term-coder"
        privacy_manager = PrivacyManager(config_dir)
        
        assert privacy_manager.can_collect_data() == False
        assert privacy_manager.can_send_analytics() == False
        assert privacy_manager.can_use_for_training() == False
        assert privacy_manager.can_report_errors() == False
    
    def test_update_privacy_setting(self, tmp_path):
        config_dir = tmp_path / ".term-coder"
        privacy_manager = PrivacyManager(config_dir)
        
        privacy_manager.update_privacy_setting("redact_secrets", False)
        assert privacy_manager.should_redact_secrets() == False
        
        privacy_manager.update_privacy_setting("offline_mode", True)
        assert privacy_manager.is_offline_mode() == True
        
        privacy_manager.update_privacy_setting("audit_level", "detailed")
        assert privacy_manager.get_audit_level() == "detailed"
    
    def test_update_consent(self, tmp_path):
        config_dir = tmp_path / ".term-coder"
        privacy_manager = PrivacyManager(config_dir)
        
        privacy_manager.update_consent("data_collection", True)
        assert privacy_manager.can_collect_data() == True
        
        privacy_manager.update_consent("analytics", True)
        assert privacy_manager.can_send_analytics() == True
        
        privacy_manager.update_consent("model_training", True)
        assert privacy_manager.can_use_for_training() == True
        
        privacy_manager.update_consent("error_reporting", True)
        assert privacy_manager.can_report_errors() == True
    
    def test_invalid_privacy_setting(self, tmp_path):
        config_dir = tmp_path / ".term-coder"
        privacy_manager = PrivacyManager(config_dir)
        
        with pytest.raises(ValueError, match="Unknown privacy setting"):
            privacy_manager.update_privacy_setting("invalid_setting", True)
    
    def test_invalid_consent_type(self, tmp_path):
        config_dir = tmp_path / ".term-coder"
        privacy_manager = PrivacyManager(config_dir)
        
        with pytest.raises(ValueError, match="Unknown consent type"):
            privacy_manager.update_consent("invalid_consent", True)
    
    def test_process_text_for_privacy_with_redaction(self, tmp_path):
        config_dir = tmp_path / ".term-coder"
        privacy_manager = PrivacyManager(config_dir)
        
        text = "My API key is sk-1234567890abcdef1234567890abcdef12345678"
        processed_text, metadata = privacy_manager.process_text_for_privacy(text, "test")
        
        assert metadata["redacted"] == True
        assert len(metadata["secrets_found"]) > 0
        assert metadata["secrets_found"][0]["pattern"] == "openai_key"
        assert "sk-" not in processed_text or "sk-**" in processed_text
    
    def test_process_text_for_privacy_without_redaction(self, tmp_path):
        config_dir = tmp_path / ".term-coder"
        privacy_manager = PrivacyManager(config_dir)
        privacy_manager.update_privacy_setting("redact_secrets", False)
        
        text = "My API key is sk-1234567890abcdef1234567890abcdef12345678"
        processed_text, metadata = privacy_manager.process_text_for_privacy(text, "test")
        
        assert metadata["redacted"] == False
        assert len(metadata["secrets_found"]) == 0
        assert processed_text == text
    
    def test_process_text_no_secrets(self, tmp_path):
        config_dir = tmp_path / ".term-coder"
        privacy_manager = PrivacyManager(config_dir)
        
        text = "This is just normal text with no secrets."
        processed_text, metadata = privacy_manager.process_text_for_privacy(text, "test")
        
        assert metadata["redacted"] == False
        assert len(metadata["secrets_found"]) == 0
        assert processed_text == text
    
    def test_persistence_of_settings(self, tmp_path):
        config_dir = tmp_path / ".term-coder"
        
        # Create first instance and modify settings
        privacy_manager1 = PrivacyManager(config_dir)
        privacy_manager1.update_privacy_setting("offline_mode", True)
        privacy_manager1.update_consent("data_collection", True)
        
        # Create second instance and verify settings persisted
        privacy_manager2 = PrivacyManager(config_dir)
        assert privacy_manager2.is_offline_mode() == True
        assert privacy_manager2.can_collect_data() == True
    
    def test_corrupted_config_files(self, tmp_path):
        config_dir = tmp_path / ".term-coder"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Create corrupted privacy config
        privacy_config_path = config_dir / "privacy.json"
        privacy_config_path.write_text("invalid json {")
        
        # Create corrupted consent config
        consent_path = config_dir / "consent.json"
        consent_path.write_text("also invalid json [")
        
        # Should handle corrupted files gracefully
        privacy_manager = PrivacyManager(config_dir)
        
        # Should fall back to defaults
        assert privacy_manager.should_redact_secrets() == True
        assert privacy_manager.can_collect_data() == False


class TestPrivacyManagerFactory:
    """Test the factory function for creating PrivacyManager instances."""
    
    def test_create_privacy_manager(self, tmp_path):
        config_dir = tmp_path / ".term-coder"
        privacy_manager = create_privacy_manager(config_dir)
        
        assert isinstance(privacy_manager, PrivacyManager)
        assert privacy_manager.config_dir == config_dir


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""
    
    def test_code_file_with_secrets(self, tmp_path):
        """Test processing a code file that contains secrets."""
        config_dir = tmp_path / ".term-coder"
        privacy_manager = PrivacyManager(config_dir)
        
        code_content = '''
import os
from openai import OpenAI

# Configuration
OPENAI_API_KEY = "sk-1234567890abcdef1234567890abcdef12345678"
DATABASE_PASSWORD = "super_secret_password123"
ADMIN_EMAIL = "admin@company.com"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", OPENAI_API_KEY))
        '''
        
        processed_content, metadata = privacy_manager.process_text_for_privacy(code_content, "code_file")
        
        assert metadata["redacted"] == True
        assert len(metadata["secrets_found"]) >= 2  # At least API key and password
        
        # Verify specific secrets are redacted
        secret_patterns = [s["pattern"] for s in metadata["secrets_found"]]
        assert "openai_key" in secret_patterns
        assert "password_field" in secret_patterns
    
    def test_config_file_with_multiple_secrets(self, tmp_path):
        """Test processing a configuration file with multiple types of secrets."""
        config_dir = tmp_path / ".term-coder"
        privacy_manager = PrivacyManager(config_dir)
        
        config_content = '''
[database]
host = "localhost"
username = "admin"
password = "my_secure_password"

[api_keys]
openai = "sk-1234567890abcdef1234567890abcdef12345678"
github = "ghp_1234567890abcdef1234567890abcdef12"

[contact]
support_email = "support@example.com"
phone = "+1-555-123-4567"

[aws]
access_key_id = "AKIAIOSFODNN7EXAMPLE"
secret_access_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        '''
        
        processed_content, metadata = privacy_manager.process_text_for_privacy(config_content, "config_file")
        
        assert metadata["redacted"] == True
        assert len(metadata["secrets_found"]) >= 4  # Multiple secrets should be found
        
        # Check that high-severity secrets are detected
        high_severity_secrets = [s for s in metadata["secrets_found"] if s["severity"] == "high"]
        assert len(high_severity_secrets) >= 2
    
    def test_offline_mode_behavior(self, tmp_path):
        """Test that offline mode affects privacy processing appropriately."""
        config_dir = tmp_path / ".term-coder"
        privacy_manager = PrivacyManager(config_dir)
        
        # Enable offline mode
        privacy_manager.update_privacy_setting("offline_mode", True)
        
        # Offline mode should still redact secrets by default
        text = "API key: sk-1234567890abcdef1234567890abcdef12345678"
        processed_text, metadata = privacy_manager.process_text_for_privacy(text, "offline_test")
        
        assert privacy_manager.is_offline_mode() == True
        assert metadata["redacted"] == True  # Should still redact in offline mode
    
    def test_audit_level_none_behavior(self, tmp_path):
        """Test behavior when audit level is set to none."""
        config_dir = tmp_path / ".term-coder"
        privacy_manager = PrivacyManager(config_dir)
        
        privacy_manager.update_privacy_setting("audit_level", "none")
        
        assert privacy_manager.get_audit_level() == "none"
        # Privacy processing should still work even with no auditing
        text = "Normal text without secrets"
        processed_text, metadata = privacy_manager.process_text_for_privacy(text, "no_audit_test")
        
        assert processed_text == text
        assert metadata["redacted"] == False