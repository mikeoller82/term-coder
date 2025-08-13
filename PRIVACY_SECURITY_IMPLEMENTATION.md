# Privacy and Security Implementation

This document summarizes the comprehensive privacy and security features implemented for term-coder.

## 🔒 Features Implemented

### 1. Secret Detection and Redaction System (`src/term_coder/security.py`)

**SecretDetector Class:**
- Detects 13 types of secrets including API keys, passwords, credit cards, SSNs, etc.
- Configurable patterns with severity levels (high, medium, low)
- Handles overlapping matches intelligently
- Supports custom pattern addition
- Redacts secrets while preserving context (shows first/last 2 characters)

**Supported Secret Types:**
- OpenAI API keys (`sk-...`)
- Anthropic API keys (`sk-ant-...`)
- GitHub tokens (`ghp_...`, `gho_...`, etc.)
- AWS access keys and secrets
- JWT tokens
- Password fields in configuration
- Private key headers
- Email addresses
- Phone numbers
- Credit card numbers
- Social Security Numbers
- Generic API keys

**PrivacyManager Class:**
- Centralized privacy settings management
- User consent tracking for data usage
- Configurable secret redaction
- Offline mode enforcement
- Audit level controls
- Persistent configuration storage

### 2. Comprehensive Audit Logging (`src/term_coder/audit.py`)

**AuditLogger Class:**
- Structured JSON logging with timestamps
- Privacy-aware log sanitization
- Configurable audit levels (none, basic, detailed)
- Automatic log rotation by month
- Log retention and cleanup policies
- Comprehensive event tracking

**Audit Event Types:**
- Command execution with resource limits and results
- File access operations (read, write, modify)
- LLM interactions with token counts and models
- Configuration changes with old/new values
- Privacy setting modifications
- Security events (secret detection, violations)
- Error events with context and stack traces

**Privacy Integration:**
- Respects user consent for logging
- Sanitizes sensitive content based on settings
- Redacts prompts/responses when configured
- Supports different privacy levels per event

### 3. LLM Integration with Privacy Controls

**Enhanced LLMOrchestrator:**
- Automatic secret detection in prompts
- Response redaction for sensitive content
- Audit logging for all LLM interactions
- Offline mode enforcement
- Security event logging when secrets detected

**Privacy-Aware Processing:**
- Pre-processes prompts to redact secrets
- Post-processes responses to remove sensitive data
- Logs security events when secrets are found
- Respects offline mode settings

### 4. CLI Commands for Privacy Management

**New Commands Added:**

```bash
# View and manage privacy settings
tc privacy                           # Show all settings
tc privacy redact_secrets true       # Enable secret redaction
tc privacy offline_mode true         # Enable offline mode
tc privacy data_collection true      # Grant data collection consent

# Scan for secrets in codebase
tc scan-secrets                      # Scan current directory
tc scan-secrets /path/to/scan        # Scan specific path
tc scan-secrets --fix                # Auto-redact found secrets
tc scan-secrets --include "*.py"     # Filter by file type

# Audit log management
tc audit                             # Show audit summary
tc audit --days 30                   # Show last 30 days
tc audit --export audit.json         # Export audit data

# Cleanup old data
tc cleanup                           # Clean old logs (90 day default)
tc cleanup --retention-days 30       # Custom retention period
```

### 5. Configuration Integration

**Privacy Settings in `.term-coder/config.yaml`:**
```yaml
privacy:
  offline: false
  redact_secrets: true
  log_prompts: false
  data_retention_days: 30
  audit_level: "basic"  # none, basic, detailed
```

**Separate Privacy Files:**
- `.term-coder/privacy.json` - Privacy settings
- `.term-coder/consent.json` - User consent data
- `.term-coder/audit/audit_YYYYMM.jsonl` - Monthly audit logs

### 6. Comprehensive Test Coverage

**Test Files Created:**
- `tests/test_security.py` - Secret detection and privacy management tests
- `tests/test_audit.py` - Audit logging functionality tests  
- `tests/test_integration_privacy.py` - End-to-end integration tests

**Test Coverage:**
- All secret detection patterns
- Privacy setting persistence
- Consent management workflow
- Audit logging with different privacy levels
- LLM integration with privacy controls
- Error handling and edge cases
- Configuration corruption recovery

## 🛡️ Security Features

### Data Protection
- **Secret Redaction**: Automatic detection and redaction of sensitive data
- **Offline Mode**: Complete isolation from external services when enabled
- **Audit Trail**: Comprehensive logging of all system operations
- **Data Retention**: Configurable retention policies with automatic cleanup

### Privacy Controls
- **Granular Consent**: Separate consent for data collection, analytics, training, error reporting
- **Configurable Logging**: Control what gets logged based on privacy preferences
- **Local Storage**: All sensitive data stored locally by default
- **Transparent Operations**: Full audit trail of what the system does with user data

### Access Controls
- **User Identification**: Consistent hashed user IDs across sessions
- **Session Tracking**: Unique session IDs for audit correlation
- **Resource Limits**: Sandboxed execution with CPU/memory limits
- **Network Isolation**: Optional network access restriction

## 🔧 Integration Points

### Existing System Integration
- **Config System**: Privacy settings integrated with main configuration
- **LLM Orchestrator**: All model interactions now privacy-aware
- **Command Runner**: Audit logging for all command executions
- **CLI Commands**: Privacy controls accessible via command line

### Backward Compatibility
- All existing functionality preserved
- Privacy features are opt-in by default
- Graceful degradation when privacy features unavailable
- No breaking changes to existing APIs

## 📊 Usage Examples

### Basic Privacy Setup
```bash
# Initialize with privacy-conscious defaults
tc init
tc privacy redact_secrets true
tc privacy offline_mode true
tc privacy audit_level basic
```

### Secret Scanning Workflow
```bash
# Scan for secrets before committing
tc scan-secrets --include "*.py" --include "*.js" --include "*.env"

# Auto-fix secrets in configuration files
tc scan-secrets config/ --fix

# Check specific file
tc scan-secrets .env --fix
```

### Audit and Compliance
```bash
# Regular audit review
tc audit --days 7

# Export for compliance
tc audit --export monthly_audit.json

# Cleanup old data
tc cleanup --retention-days 90
```

### Offline Development
```bash
# Enable offline mode
tc privacy offline_mode true

# Verify no external calls
tc chat "explain this code" --model local:ollama
```

## 🎯 Benefits

### For Developers
- **Peace of Mind**: Automatic secret detection prevents accidental exposure
- **Compliance Ready**: Comprehensive audit trails for security reviews
- **Privacy Control**: Full control over what data is shared and logged
- **Offline Capable**: Can work completely offline for sensitive projects

### For Organizations
- **Security Compliance**: Built-in secret scanning and audit logging
- **Data Governance**: Granular controls over data collection and usage
- **Audit Trail**: Complete record of all system operations
- **Risk Mitigation**: Automatic redaction reduces exposure risk

### For Privacy-Conscious Users
- **Transparency**: Clear visibility into what data is collected
- **Control**: Granular consent management for different data uses
- **Local-First**: All processing can be done locally
- **Minimal Data**: Only collect what's explicitly consented to

## 🚀 Future Enhancements

The implementation provides a solid foundation for additional privacy and security features:

- **Encryption**: Add encryption for stored audit logs and session data
- **Key Management**: Integration with external key management systems
- **Advanced Patterns**: Machine learning-based secret detection
- **Compliance Reports**: Automated generation of compliance reports
- **Data Anonymization**: Advanced techniques for data anonymization
- **External Auditing**: Integration with external audit systems

This implementation establishes term-coder as a privacy-first, security-conscious coding assistant that respects user data and provides transparency into all operations.