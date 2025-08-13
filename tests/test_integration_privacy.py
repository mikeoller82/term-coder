from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from term_coder.security import PrivacyManager, create_privacy_manager
from term_coder.audit import AuditLogger, create_audit_logger
from term_coder.llm import LLMOrchestrator


class TestPrivacySecurityIntegration:
    """Test integration between privacy, security, and audit systems."""
    
    def test_full_privacy_workflow(self):
        """Test complete privacy workflow with LLM integration."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_dir = Path(tmp_dir) / ".term-coder"
            
            # Create privacy manager and audit logger
            privacy_manager = create_privacy_manager(config_dir)
            audit_logger = create_audit_logger(config_dir, privacy_manager)
            
            # Create LLM orchestrator with privacy integration
            orchestrator = LLMOrchestrator(
                default_model="mock-llm",
                offline=False,
                privacy_manager=privacy_manager,
                audit_logger=audit_logger
            )
            
            # Test prompt with secrets
            prompt_with_secrets = """
            Please help me with this code:
            
            OPENAI_API_KEY = "sk-1234567890abcdef1234567890abcdef12345678"
            DATABASE_PASSWORD = "super_secret_password123"
            
            How can I make this more secure?
            """
            
            # Complete request should redact secrets and log security events
            response = orchestrator.complete(prompt_with_secrets)
            
            # Verify response is generated
            assert response.text is not None
            assert len(response.text) > 0
            
            # Check audit logs
            summary = audit_logger.get_audit_summary(days=1)
            assert summary["total_events"] >= 2  # LLM interaction + security events
            assert summary["security_events"] >= 1  # Should detect secrets
            
            # Verify security events were logged
            event_types = summary["event_types"]
            assert "llm" in event_types
            assert "security" in event_types
    
    def test_offline_mode_enforcement(self):
        """Test that offline mode prevents external API calls."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_dir = Path(tmp_dir) / ".term-coder"
            
            privacy_manager = create_privacy_manager(config_dir)
            audit_logger = create_audit_logger(config_dir, privacy_manager)
            
            # Enable offline mode
            privacy_manager.update_privacy_setting("offline_mode", True)
            
            # Create orchestrator with offline mode
            orchestrator = LLMOrchestrator(
                default_model="openai:gpt",  # Try to use external model
                offline=privacy_manager.is_offline_mode(),
                privacy_manager=privacy_manager,
                audit_logger=audit_logger
            )
            
            # Should fall back to local/mock model
            adapter = orchestrator.get("openai:gpt")
            # In offline mode, should not use OpenAI adapter
            assert adapter.model_name in ["qwen2.5-coder:7b", "mock-llm"]
    
    def test_audit_level_controls_logging(self):
        """Test that audit level controls what gets logged."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_dir = Path(tmp_dir) / ".term-coder"
            
            privacy_manager = create_privacy_manager(config_dir)
            
            # Test with audit level "none"
            privacy_manager.update_privacy_setting("audit_level", "none")
            audit_logger = create_audit_logger(config_dir, privacy_manager)
            
            # Log various events
            audit_logger.log_event("test", "action", privacy_level="basic")
            audit_logger.log_event("test", "action", privacy_level="detailed")
            
            # Should not log anything
            summary = audit_logger.get_audit_summary(days=1)
            assert summary["total_events"] == 0
            
            # Test with audit level "basic"
            privacy_manager.update_privacy_setting("audit_level", "basic")
            audit_logger = create_audit_logger(config_dir, privacy_manager)
            
            audit_logger.log_event("test", "basic_action", privacy_level="basic")
            audit_logger.log_event("test", "detailed_action", privacy_level="detailed")
            
            summary = audit_logger.get_audit_summary(days=1)
            # Should only log basic events (plus the privacy change event)
            assert summary["total_events"] >= 1
    
    def test_secret_redaction_in_llm_responses(self):
        """Test that secrets in LLM responses are also redacted."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_dir = Path(tmp_dir) / ".term-coder"
            
            privacy_manager = create_privacy_manager(config_dir)
            audit_logger = create_audit_logger(config_dir, privacy_manager)
            
            # Mock LLM adapter that returns secrets
            class MockAdapterWithSecrets:
                model_name = "mock-with-secrets"
                
                def complete(self, prompt, tools=None):
                    from term_coder.llm import Response
                    return Response(
                        text="Here's your API key: sk-1234567890abcdef1234567890abcdef12345678",
                        model=self.model_name
                    )
                
                def stream(self, prompt, tools=None):
                    yield "Here's your API key: sk-1234567890abcdef1234567890abcdef12345678"
                
                def estimate_tokens(self, text):
                    return len(text) // 4
            
            orchestrator = LLMOrchestrator(
                privacy_manager=privacy_manager,
                audit_logger=audit_logger
            )
            orchestrator.adapters["mock-with-secrets"] = MockAdapterWithSecrets()
            
            # Test completion
            response = orchestrator.complete("test prompt", model="mock-with-secrets")
            
            # Response should be redacted
            assert "sk-1234567890abcdef1234567890abcdef12345678" not in response.text
            assert "sk-12" in response.text and "78" in response.text  # Partial redaction
    
    def test_consent_management_workflow(self):
        """Test user consent management workflow."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_dir = Path(tmp_dir) / ".term-coder"
            
            privacy_manager = create_privacy_manager(config_dir)
            
            # Initially, no consent should be granted
            assert not privacy_manager.can_collect_data()
            assert not privacy_manager.can_send_analytics()
            assert not privacy_manager.can_use_for_training()
            assert not privacy_manager.can_report_errors()
            
            # Grant specific consents
            privacy_manager.update_consent("data_collection", True)
            privacy_manager.update_consent("error_reporting", True)
            
            # Verify consent state
            assert privacy_manager.can_collect_data()
            assert not privacy_manager.can_send_analytics()
            assert not privacy_manager.can_use_for_training()
            assert privacy_manager.can_report_errors()
            
            # Verify consent persists across instances
            privacy_manager2 = PrivacyManager(config_dir)
            assert privacy_manager2.can_collect_data()
            assert privacy_manager2.can_report_errors()
    
    def test_privacy_settings_persistence(self):
        """Test that privacy settings persist across restarts."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_dir = Path(tmp_dir) / ".term-coder"
            
            # Create first instance and modify settings
            privacy_manager1 = create_privacy_manager(config_dir)
            privacy_manager1.update_privacy_setting("redact_secrets", False)
            privacy_manager1.update_privacy_setting("offline_mode", True)
            privacy_manager1.update_privacy_setting("audit_level", "detailed")
            
            # Create second instance and verify settings
            privacy_manager2 = create_privacy_manager(config_dir)
            assert not privacy_manager2.should_redact_secrets()
            assert privacy_manager2.is_offline_mode()
            assert privacy_manager2.get_audit_level() == "detailed"
    
    def test_audit_log_cleanup_workflow(self):
        """Test audit log cleanup functionality."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_dir = Path(tmp_dir) / ".term-coder"
            
            privacy_manager = create_privacy_manager(config_dir)
            audit_logger = create_audit_logger(config_dir, privacy_manager)
            
            # Create some audit events
            for i in range(10):
                audit_logger.log_event("test", f"action_{i}")
            
            # Verify events were logged
            summary = audit_logger.get_audit_summary(days=1)
            assert summary["total_events"] >= 10
            
            # Test cleanup (with very short retention for testing)
            audit_logger.cleanup_old_logs(retention_days=0)
            
            # Should log the cleanup operation itself
            summary_after = audit_logger.get_audit_summary(days=1)
            # Events might be cleaned up, but cleanup event should be logged
            assert "maintenance" in summary_after.get("event_types", {})
    
    def test_error_handling_in_privacy_system(self):
        """Test that privacy system handles errors gracefully."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_dir = Path(tmp_dir) / ".term-coder"
            
            privacy_manager = create_privacy_manager(config_dir)
            audit_logger = create_audit_logger(config_dir, privacy_manager)
            
            # Test with invalid inputs
            try:
                privacy_manager.update_privacy_setting("invalid_setting", "value")
                assert False, "Should have raised ValueError"
            except ValueError:
                pass  # Expected
            
            try:
                privacy_manager.update_consent("invalid_consent", True)
                assert False, "Should have raised ValueError"
            except ValueError:
                pass  # Expected
            
            # Privacy system should still work after errors
            privacy_manager.update_privacy_setting("redact_secrets", False)
            assert not privacy_manager.should_redact_secrets()
    
    def test_comprehensive_secret_detection_scenarios(self):
        """Test various secret detection scenarios."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_dir = Path(tmp_dir) / ".term-coder"
            
            privacy_manager = create_privacy_manager(config_dir)
            
            # Test various types of content
            test_cases = [
                # Code files
                '''
                import os
                OPENAI_API_KEY = "sk-1234567890abcdef1234567890abcdef12345678"
                client = OpenAI(api_key=OPENAI_API_KEY)
                ''',
                
                # Configuration files
                '''
                [database]
                password = "my_secure_password"
                
                [api]
                github_token = "ghp_1234567890abcdef1234567890abcdef12"
                ''',
                
                # Environment files
                '''
                OPENAI_API_KEY=sk-1234567890abcdef1234567890abcdef12345678
                DATABASE_URL=postgresql://user:password@localhost/db
                JWT_SECRET=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abc
                ''',
                
                # Documentation with examples
                '''
                To use the API, set your key:
                export OPENAI_API_KEY="sk-1234567890abcdef1234567890abcdef12345678"
                
                Contact support at support@company.com or call +1-555-123-4567
                '''
            ]
            
            for i, content in enumerate(test_cases):
                processed, metadata = privacy_manager.process_text_for_privacy(content, f"test_case_{i}")
                
                # Should detect and redact secrets
                assert metadata["redacted"]
                assert len(metadata["secrets_found"]) > 0
                
                # High-severity secrets should be detected
                high_severity = [s for s in metadata["secrets_found"] if s["severity"] == "high"]
                assert len(high_severity) > 0