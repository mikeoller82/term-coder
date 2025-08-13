from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import hashlib
import os


@dataclass
class AuditEvent:
    """Represents an audit event."""
    timestamp: str
    event_type: str
    user_id: str
    session_id: str
    action: str
    resource: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    success: bool = True
    error_message: Optional[str] = None
    privacy_level: str = "basic"  # "none", "basic", "detailed"


class AuditLogger:
    """Handles audit logging for security and compliance."""
    
    def __init__(self, config_dir: Path, privacy_manager=None):
        self.config_dir = config_dir
        self.audit_dir = config_dir / "audit"
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        
        self.privacy_manager = privacy_manager
        self.session_id = self._generate_session_id()
        self.user_id = self._get_user_id()
        
        # Set up file logging
        self.audit_file = self.audit_dir / f"audit_{datetime.now().strftime('%Y%m')}.jsonl"
        self.logger = self._setup_logger()
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def _get_user_id(self) -> str:
        """Get a consistent user identifier (hashed)."""
        # Use a combination of username and hostname for consistency
        import getpass
        import socket
        
        user_info = f"{getpass.getuser()}@{socket.gethostname()}"
        return hashlib.sha256(user_info.encode()).hexdigest()[:16]
    
    def _setup_logger(self) -> logging.Logger:
        """Set up the audit logger."""
        logger = logging.getLogger("term_coder_audit")
        logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # File handler for audit logs
        handler = logging.FileHandler(self.audit_file)
        handler.setLevel(logging.INFO)
        
        # JSON formatter
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        logger.propagate = False
        
        return logger
    
    def _should_log(self, privacy_level: str) -> bool:
        """Check if event should be logged based on privacy settings."""
        if not self.privacy_manager:
            return True
        
        audit_level = self.privacy_manager.get_audit_level()
        
        if audit_level == "none":
            return False
        elif audit_level == "basic":
            return privacy_level in ["none", "basic"]
        elif audit_level == "detailed":
            return True
        
        return False
    
    def _sanitize_details(self, details: Optional[Dict[str, Any]], privacy_level: str) -> Optional[Dict[str, Any]]:
        """Sanitize details based on privacy settings."""
        if not details or not self.privacy_manager:
            return details
        
        if not self.privacy_manager.should_log_prompts() and privacy_level == "detailed":
            # Remove sensitive content from detailed logs
            sanitized = {}
            for key, value in details.items():
                if key in ["prompt", "response", "content", "diff"]:
                    if isinstance(value, str):
                        sanitized[key] = f"<redacted:{len(value)} chars>"
                    else:
                        sanitized[key] = "<redacted>"
                else:
                    sanitized[key] = value
            return sanitized
        
        return details
    
    def log_event(
        self,
        event_type: str,
        action: str,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        privacy_level: str = "basic"
    ) -> None:
        """Log an audit event."""
        
        if not self._should_log(privacy_level):
            return
        
        # Sanitize details based on privacy settings
        sanitized_details = self._sanitize_details(details, privacy_level)
        
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            user_id=self.user_id,
            session_id=self.session_id,
            action=action,
            resource=resource,
            details=sanitized_details,
            success=success,
            error_message=error_message,
            privacy_level=privacy_level
        )
        
        # Log as JSON
        self.logger.info(json.dumps(asdict(event)))
    
    def log_command_execution(self, command: str, success: bool, details: Optional[Dict] = None) -> None:
        """Log command execution."""
        self.log_event(
            event_type="command",
            action="execute",
            resource=command,
            details=details,
            success=success,
            privacy_level="basic"
        )
    
    def log_file_access(self, file_path: str, action: str, success: bool = True) -> None:
        """Log file access operations."""
        self.log_event(
            event_type="file",
            action=action,
            resource=file_path,
            success=success,
            privacy_level="basic"
        )
    
    def log_llm_interaction(self, model: str, action: str, details: Optional[Dict] = None, success: bool = True) -> None:
        """Log LLM interactions."""
        self.log_event(
            event_type="llm",
            action=action,
            resource=model,
            details=details,
            success=success,
            privacy_level="detailed"
        )
    
    def log_config_change(self, key: str, old_value: Any, new_value: Any) -> None:
        """Log configuration changes."""
        self.log_event(
            event_type="config",
            action="update",
            resource=key,
            details={"old_value": str(old_value), "new_value": str(new_value)},
            privacy_level="basic"
        )
    
    def log_privacy_change(self, setting: str, new_value: Any) -> None:
        """Log privacy setting changes."""
        self.log_event(
            event_type="privacy",
            action="update",
            resource=setting,
            details={"new_value": str(new_value)},
            privacy_level="basic"
        )
    
    def log_security_event(self, event_description: str, severity: str, details: Optional[Dict] = None) -> None:
        """Log security-related events."""
        self.log_event(
            event_type="security",
            action=event_description,
            details={**(details or {}), "severity": severity},
            privacy_level="basic"
        )
    
    def log_error(self, error_type: str, error_message: str, details: Optional[Dict] = None) -> None:
        """Log error events."""
        self.log_event(
            event_type="error",
            action=error_type,
            error_message=error_message,
            details=details,
            success=False,
            privacy_level="basic"
        )
    
    def get_audit_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get audit summary for the last N days."""
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        events = []
        
        # Read recent audit files
        for audit_file in self.audit_dir.glob("audit_*.jsonl"):
            try:
                with open(audit_file) as f:
                    for line in f:
                        try:
                            event_data = json.loads(line.strip())
                            event_time = datetime.fromisoformat(event_data["timestamp"])
                            if event_time >= cutoff_date:
                                events.append(event_data)
                        except (json.JSONDecodeError, KeyError, ValueError):
                            continue
            except Exception:
                continue
        
        # Generate summary
        summary = {
            "total_events": len(events),
            "date_range": f"{cutoff_date.date()} to {datetime.now().date()}",
            "event_types": {},
            "success_rate": 0,
            "error_count": 0,
            "security_events": 0
        }
        
        if events:
            success_count = sum(1 for e in events if e.get("success", True))
            summary["success_rate"] = success_count / len(events)
            summary["error_count"] = len(events) - success_count
            
            # Count by event type
            for event in events:
                event_type = event.get("event_type", "unknown")
                summary["event_types"][event_type] = summary["event_types"].get(event_type, 0) + 1
                
                if event_type == "security":
                    summary["security_events"] += 1
        
        return summary
    
    def cleanup_old_logs(self, retention_days: int = 90) -> None:
        """Clean up old audit logs based on retention policy."""
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        for audit_file in self.audit_dir.glob("audit_*.jsonl"):
            try:
                # Extract date from filename (audit_YYYYMM.jsonl)
                date_str = audit_file.stem.split("_")[1]
                file_date = datetime.strptime(date_str + "01", "%Y%m%d")
                
                if file_date < cutoff_date:
                    audit_file.unlink()
                    self.log_event(
                        event_type="maintenance",
                        action="cleanup",
                        resource=str(audit_file),
                        details={"reason": "retention_policy"},
                        privacy_level="basic"
                    )
            except (ValueError, IndexError):
                # Skip files with unexpected naming
                continue


def create_audit_logger(config_dir: Path, privacy_manager=None) -> AuditLogger:
    """Factory function to create an AuditLogger instance."""
    return AuditLogger(config_dir, privacy_manager)