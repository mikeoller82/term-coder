from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from term_coder.audit import AuditLogger, AuditEvent, create_audit_logger


class TestAuditEvent:
    """Test AuditEvent dataclass functionality."""
    
    def test_audit_event_creation(self):
        event = AuditEvent(
            timestamp="2024-01-01T12:00:00",
            event_type="test",
            user_id="user123",
            session_id="session456",
            action="test_action",
            resource="test_resource",
            details={"key": "value"},
            success=True,
            privacy_level="basic"
        )
        
        assert event.timestamp == "2024-01-01T12:00:00"
        assert event.event_type == "test"
        assert event.user_id == "user123"
        assert event.session_id == "session456"
        assert event.action == "test_action"
        assert event.resource == "test_resource"
        assert event.details == {"key": "value"}
        assert event.success == True
        assert event.privacy_level == "basic"
    
    def test_audit_event_defaults(self):
        event = AuditEvent(
            timestamp="2024-01-01T12:00:00",
            event_type="test",
            user_id="user123",
            session_id="session456",
            action="test_action"
        )
        
        assert event.resource is None
        assert event.details is None
        assert event.success == True
        assert event.error_message is None
        assert event.privacy_level == "basic"


class TestAuditLogger:
    """Test AuditLogger functionality."""
    
    def test_audit_logger_initialization(self, tmp_path):
        config_dir = tmp_path / ".term-coder"
        audit_logger = AuditLogger(config_dir)
        
        assert audit_logger.config_dir == config_dir
        assert audit_logger.audit_dir.exists()
        assert audit_logger.session_id is not None
        assert audit_logger.user_id is not None
        assert len(audit_logger.session_id) == 8  # Should be 8 characters
        assert len(audit_logger.user_id) == 16   # Should be 16 characters (hashed)
    
    def test_session_id_uniqueness(self, tmp_path):
        config_dir = tmp_path / ".term-coder"
        
        logger1 = AuditLogger(config_dir)
        logger2 = AuditLogger(config_dir)
        
        # Each instance should have a unique session ID
        assert logger1.session_id != logger2.session_id
    
    def test_user_id_consistency(self, tmp_path):
        config_dir = tmp_path / ".term-coder"
        
        logger1 = AuditLogger(config_dir)
        logger2 = AuditLogger(config_dir)
        
        # User ID should be consistent across instances
        assert logger1.user_id == logger2.user_id
    
    def test_log_event_basic(self, tmp_path):
        config_dir = tmp_path / ".term-coder"
        audit_logger = AuditLogger(config_dir)
        
        audit_logger.log_event(
            event_type="test",
            action="test_action",
            resource="test_resource",
            success=True
        )
        
        # Check that log file was created and contains the event
        log_files = list(audit_logger.audit_dir.glob("audit_*.jsonl"))
        assert len(log_files) == 1
        
        log_content = log_files[0].read_text()
        log_lines = [line for line in log_content.strip().split('\n') if line]
        assert len(log_lines) == 1
        
        event_data = json.loads(log_lines[0])
        assert event_data["event_type"] == "test"
        assert event_data["action"] == "test_action"
        assert event_data["resource"] == "test_resource"
        assert event_data["success"] == True
    
    def test_log_event_with_details(self, tmp_path):
        config_dir = tmp_path / ".term-coder"
        audit_logger = AuditLogger(config_dir)
        
        details = {"key1": "value1", "key2": 42, "key3": True}
        audit_logger.log_event(
            event_type="test",
            action="test_action",
            details=details
        )
        
        log_files = list(audit_logger.audit_dir.glob("audit_*.jsonl"))
        log_content = log_files[0].read_text()
        event_data = json.loads(log_content.strip())
        
        assert event_data["details"] == details
    
    def test_log_event_with_error(self, tmp_path):
        config_dir = tmp_path / ".term-coder"
        audit_logger = AuditLogger(config_dir)
        
        audit_logger.log_event(
            event_type="error",
            action="test_error",
            success=False,
            error_message="Test error message"
        )
        
        log_files = list(audit_logger.audit_dir.glob("audit_*.jsonl"))
        log_content = log_files[0].read_text()
        event_data = json.loads(log_content.strip())
        
        assert event_data["success"] == False
        assert event_data["error_message"] == "Test error message"
    
    def test_log_command_execution(self, tmp_path):
        config_dir = tmp_path / ".term-coder"
        audit_logger = AuditLogger(config_dir)
        
        audit_logger.log_command_execution(
            command="python test.py",
            success=True,
            details={"exit_code": 0, "duration": 1.5}
        )
        
        log_files = list(audit_logger.audit_dir.glob("audit_*.jsonl"))
        log_content = log_files[0].read_text()
        event_data = json.loads(log_content.strip())
        
        assert event_data["event_type"] == "command"
        assert event_data["action"] == "execute"
        assert event_data["resource"] == "python test.py"
        assert event_data["details"]["exit_code"] == 0
        assert event_data["details"]["duration"] == 1.5
    
    def test_log_file_access(self, tmp_path):
        config_dir = tmp_path / ".term-coder"
        audit_logger = AuditLogger(config_dir)
        
        audit_logger.log_file_access("/path/to/file.py", "read")
        
        log_files = list(audit_logger.audit_dir.glob("audit_*.jsonl"))
        log_content = log_files[0].read_text()
        event_data = json.loads(log_content.strip())
        
        assert event_data["event_type"] == "file"
        assert event_data["action"] == "read"
        assert event_data["resource"] == "/path/to/file.py"
    
    def test_log_llm_interaction(self, tmp_path):
        config_dir = tmp_path / ".term-coder"
        audit_logger = AuditLogger(config_dir)
        
        audit_logger.log_llm_interaction(
            model="gpt-4",
            action="complete",
            details={"prompt_length": 100, "response_length": 200}
        )
        
        log_files = list(audit_logger.audit_dir.glob("audit_*.jsonl"))
        log_content = log_files[0].read_text()
        event_data = json.loads(log_content.strip())
        
        assert event_data["event_type"] == "llm"
        assert event_data["action"] == "complete"
        assert event_data["resource"] == "gpt-4"
        assert event_data["privacy_level"] == "detailed"
    
    def test_log_config_change(self, tmp_path):
        config_dir = tmp_path / ".term-coder"
        audit_logger = AuditLogger(config_dir)
        
        audit_logger.log_config_change("model.default", "gpt-3.5", "gpt-4")
        
        log_files = list(audit_logger.audit_dir.glob("audit_*.jsonl"))
        log_content = log_files[0].read_text()
        event_data = json.loads(log_content.strip())
        
        assert event_data["event_type"] == "config"
        assert event_data["action"] == "update"
        assert event_data["resource"] == "model.default"
        assert event_data["details"]["old_value"] == "gpt-3.5"
        assert event_data["details"]["new_value"] == "gpt-4"
    
    def test_log_privacy_change(self, tmp_path):
        config_dir = tmp_path / ".term-coder"
        audit_logger = AuditLogger(config_dir)
        
        audit_logger.log_privacy_change("redact_secrets", True)
        
        log_files = list(audit_logger.audit_dir.glob("audit_*.jsonl"))
        log_content = log_files[0].read_text()
        event_data = json.loads(log_content.strip())
        
        assert event_data["event_type"] == "privacy"
        assert event_data["action"] == "update"
        assert event_data["resource"] == "redact_secrets"
        assert event_data["details"]["new_value"] == "True"
    
    def test_log_security_event(self, tmp_path):
        config_dir = tmp_path / ".term-coder"
        audit_logger = AuditLogger(config_dir)
        
        audit_logger.log_security_event(
            "secrets_detected",
            "high",
            {"secret_count": 3, "file": "config.py"}
        )
        
        log_files = list(audit_logger.audit_dir.glob("audit_*.jsonl"))
        log_content = log_files[0].read_text()
        event_data = json.loads(log_content.strip())
        
        assert event_data["event_type"] == "security"
        assert event_data["action"] == "secrets_detected"
        assert event_data["details"]["severity"] == "high"
        assert event_data["details"]["secret_count"] == 3
    
    def test_log_error(self, tmp_path):
        config_dir = tmp_path / ".term-coder"
        audit_logger = AuditLogger(config_dir)
        
        audit_logger.log_error(
            "file_not_found",
            "Could not find file: missing.py",
            {"file_path": "missing.py"}
        )
        
        log_files = list(audit_logger.audit_dir.glob("audit_*.jsonl"))
        log_content = log_files[0].read_text()
        event_data = json.loads(log_content.strip())
        
        assert event_data["event_type"] == "error"
        assert event_data["action"] == "file_not_found"
        assert event_data["success"] == False
        assert event_data["error_message"] == "Could not find file: missing.py"
        assert event_data["details"]["file_path"] == "missing.py"


class TestAuditLoggerWithPrivacyManager:
    """Test AuditLogger integration with PrivacyManager."""
    
    def test_privacy_manager_integration(self, tmp_path):
        from term_coder.security import PrivacyManager
        
        config_dir = tmp_path / ".term-coder"
        privacy_manager = PrivacyManager(config_dir)
        audit_logger = AuditLogger(config_dir, privacy_manager)
        
        assert audit_logger.privacy_manager == privacy_manager
    
    def test_audit_level_none_blocks_logging(self, tmp_path):
        from term_coder.security import PrivacyManager
        
        config_dir = tmp_path / ".term-coder"
        privacy_manager = PrivacyManager(config_dir)
        privacy_manager.update_privacy_setting("audit_level", "none")
        
        audit_logger = AuditLogger(config_dir, privacy_manager)
        audit_logger.log_event("test", "action")
        
        # No log files should be created when audit level is "none"
        log_files = list(audit_logger.audit_dir.glob("audit_*.jsonl"))
        if log_files:
            log_content = log_files[0].read_text().strip()
            assert log_content == ""  # File might exist but should be empty
    
    def test_audit_level_basic_allows_basic_events(self, tmp_path):
        from term_coder.security import PrivacyManager
        
        config_dir = tmp_path / ".term-coder"
        privacy_manager = PrivacyManager(config_dir)
        privacy_manager.update_privacy_setting("audit_level", "basic")
        
        audit_logger = AuditLogger(config_dir, privacy_manager)
        audit_logger.log_event("test", "action", privacy_level="basic")
        
        log_files = list(audit_logger.audit_dir.glob("audit_*.jsonl"))
        assert len(log_files) == 1
        log_content = log_files[0].read_text().strip()
        assert log_content != ""
    
    def test_audit_level_basic_blocks_detailed_events(self, tmp_path):
        from term_coder.security import PrivacyManager
        
        config_dir = tmp_path / ".term-coder"
        privacy_manager = PrivacyManager(config_dir)
        privacy_manager.update_privacy_setting("audit_level", "basic")
        
        audit_logger = AuditLogger(config_dir, privacy_manager)
        audit_logger.log_event("test", "action", privacy_level="detailed")
        
        log_files = list(audit_logger.audit_dir.glob("audit_*.jsonl"))
        if log_files:
            log_content = log_files[0].read_text().strip()
            assert log_content == ""  # Should not log detailed events
    
    def test_prompt_logging_disabled_sanitizes_details(self, tmp_path):
        from term_coder.security import PrivacyManager
        
        config_dir = tmp_path / ".term-coder"
        privacy_manager = PrivacyManager(config_dir)
        privacy_manager.update_privacy_setting("log_prompts", False)
        
        audit_logger = AuditLogger(config_dir, privacy_manager)
        audit_logger.log_event(
            "test",
            "action",
            details={"prompt": "sensitive prompt content", "other": "normal data"},
            privacy_level="detailed"
        )
        
        log_files = list(audit_logger.audit_dir.glob("audit_*.jsonl"))
        if log_files and log_files[0].read_text().strip():
            log_content = log_files[0].read_text()
            event_data = json.loads(log_content.strip())
            
            # Prompt should be redacted
            assert "sensitive prompt content" not in str(event_data["details"])
            assert "<redacted:" in str(event_data["details"]["prompt"])
            # Other data should remain
            assert event_data["details"]["other"] == "normal data"


class TestAuditSummary:
    """Test audit summary and reporting functionality."""
    
    def test_get_audit_summary_empty(self, tmp_path):
        config_dir = tmp_path / ".term-coder"
        audit_logger = AuditLogger(config_dir)
        
        summary = audit_logger.get_audit_summary(days=7)
        
        assert summary["total_events"] == 0
        assert summary["success_rate"] == 0
        assert summary["error_count"] == 0
        assert summary["security_events"] == 0
        assert summary["event_types"] == {}
    
    def test_get_audit_summary_with_events(self, tmp_path):
        config_dir = tmp_path / ".term-coder"
        audit_logger = AuditLogger(config_dir)
        
        # Log various types of events
        audit_logger.log_event("command", "execute", success=True)
        audit_logger.log_event("file", "read", success=True)
        audit_logger.log_event("llm", "complete", success=False, error_message="API error")
        audit_logger.log_security_event("secrets_detected", "medium")
        
        summary = audit_logger.get_audit_summary(days=7)
        
        assert summary["total_events"] == 4
        assert summary["success_rate"] == 0.75  # 3 success, 1 failure
        assert summary["error_count"] == 1
        assert summary["security_events"] == 1
        assert summary["event_types"]["command"] == 1
        assert summary["event_types"]["file"] == 1
        assert summary["event_types"]["llm"] == 1
        assert summary["event_types"]["security"] == 1
    
    def test_get_audit_summary_date_filtering(self, tmp_path):
        config_dir = tmp_path / ".term-coder"
        audit_logger = AuditLogger(config_dir)
        
        # Mock datetime to create events with specific timestamps
        with patch('term_coder.audit.datetime') as mock_datetime:
            # Create an old event (outside the 7-day window)
            old_time = datetime.now() - timedelta(days=10)
            mock_datetime.now.return_value = old_time
            mock_datetime.fromisoformat = datetime.fromisoformat
            
            audit_logger.log_event("old", "action")
            
            # Create a recent event (within the 7-day window)
            recent_time = datetime.now() - timedelta(days=3)
            mock_datetime.now.return_value = recent_time
            
            audit_logger.log_event("recent", "action")
        
        # Get summary for last 7 days
        summary = audit_logger.get_audit_summary(days=7)
        
        # Should only include the recent event
        assert summary["total_events"] == 1
        assert "recent" in summary["event_types"]
        assert "old" not in summary["event_types"]


class TestAuditLogCleanup:
    """Test audit log cleanup functionality."""
    
    def test_cleanup_old_logs(self, tmp_path):
        config_dir = tmp_path / ".term-coder"
        audit_logger = AuditLogger(config_dir)
        
        # Create old log files
        old_log = audit_logger.audit_dir / "audit_202301.jsonl"
        old_log.write_text('{"test": "old_data"}\n')
        
        recent_log = audit_logger.audit_dir / "audit_202412.jsonl"
        recent_log.write_text('{"test": "recent_data"}\n')
        
        # Cleanup with 30-day retention
        audit_logger.cleanup_old_logs(retention_days=30)
        
        # Old log should be deleted, recent log should remain
        assert not old_log.exists()
        assert recent_log.exists()
    
    def test_cleanup_logs_with_invalid_names(self, tmp_path):
        config_dir = tmp_path / ".term-coder"
        audit_logger = AuditLogger(config_dir)
        
        # Create files with invalid naming patterns
        invalid_log = audit_logger.audit_dir / "invalid_log.jsonl"
        invalid_log.write_text('{"test": "data"}\n')
        
        # Should not crash on invalid file names
        audit_logger.cleanup_old_logs(retention_days=30)
        
        # Invalid log should remain (not deleted due to naming)
        assert invalid_log.exists()


class TestAuditLoggerFactory:
    """Test the factory function for creating AuditLogger instances."""
    
    def test_create_audit_logger(self, tmp_path):
        config_dir = tmp_path / ".term-coder"
        audit_logger = create_audit_logger(config_dir)
        
        assert isinstance(audit_logger, AuditLogger)
        assert audit_logger.config_dir == config_dir
    
    def test_create_audit_logger_with_privacy_manager(self, tmp_path):
        from term_coder.security import PrivacyManager
        
        config_dir = tmp_path / ".term-coder"
        privacy_manager = PrivacyManager(config_dir)
        audit_logger = create_audit_logger(config_dir, privacy_manager)
        
        assert isinstance(audit_logger, AuditLogger)
        assert audit_logger.privacy_manager == privacy_manager


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""
    
    def test_full_workflow_audit_trail(self, tmp_path):
        """Test a complete workflow and verify audit trail."""
        from term_coder.security import PrivacyManager
        
        config_dir = tmp_path / ".term-coder"
        privacy_manager = PrivacyManager(config_dir)
        audit_logger = AuditLogger(config_dir, privacy_manager)
        
        # Simulate a complete workflow
        audit_logger.log_command_execution("tc chat 'hello'", True, {"duration": 2.5})
        audit_logger.log_llm_interaction("gpt-4", "complete", {"prompt_length": 50})
        audit_logger.log_file_access("src/main.py", "read")
        audit_logger.log_config_change("model.default", "gpt-3.5", "gpt-4")
        audit_logger.log_security_event("secrets_detected", "low", {"count": 1})
        
        # Verify complete audit trail
        summary = audit_logger.get_audit_summary(days=1)
        
        assert summary["total_events"] == 5
        assert summary["success_rate"] == 1.0
        assert summary["security_events"] == 1
        assert len(summary["event_types"]) == 5
    
    def test_error_handling_in_audit_logging(self, tmp_path):
        """Test that audit logging handles errors gracefully."""
        config_dir = tmp_path / ".term-coder"
        audit_logger = AuditLogger(config_dir)
        
        # Test with various problematic inputs
        audit_logger.log_event("test", "action", details={"complex": {"nested": "data"}})
        audit_logger.log_event("test", "action", details=None)
        audit_logger.log_event("test", "action", resource="")
        
        # Should not crash and should log events
        summary = audit_logger.get_audit_summary(days=1)
        assert summary["total_events"] == 3