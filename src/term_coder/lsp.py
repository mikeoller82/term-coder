from __future__ import annotations

import asyncio
import json
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, Callable
from urllib.parse import urljoin
import logging

from .config import Config


@dataclass
class LSPPosition:
    """Represents a position in a document."""
    line: int
    character: int


@dataclass
class LSPRange:
    """Represents a range in a document."""
    start: LSPPosition
    end: LSPPosition


@dataclass
class LSPLocation:
    """Represents a location in a document."""
    uri: str
    range: LSPRange


@dataclass
class LSPDiagnostic:
    """Represents a diagnostic message."""
    range: LSPRange
    severity: int  # 1=Error, 2=Warning, 3=Information, 4=Hint
    code: Optional[str] = None
    source: Optional[str] = None
    message: str = ""
    related_information: List[Dict] = field(default_factory=list)


@dataclass
class LSPSymbol:
    """Represents a symbol in the code."""
    name: str
    kind: int  # SymbolKind enum
    location: LSPLocation
    container_name: Optional[str] = None
    detail: Optional[str] = None


@dataclass
class LSPCompletionItem:
    """Represents a completion item."""
    label: str
    kind: int  # CompletionItemKind enum
    detail: Optional[str] = None
    documentation: Optional[str] = None
    insert_text: Optional[str] = None
    sort_text: Optional[str] = None


@dataclass
class LSPHover:
    """Represents hover information."""
    contents: Union[str, List[str]]
    range: Optional[LSPRange] = None


class LSPClient:
    """Language Server Protocol client implementation."""
    
    def __init__(self, server_command: List[str], root_path: Path, language_id: str):
        self.server_command = server_command
        self.root_path = root_path
        self.language_id = language_id
        self.process: Optional[subprocess.Popen] = None
        self.request_id = 0
        self.pending_requests: Dict[int, asyncio.Future] = {}
        self.diagnostics: Dict[str, List[LSPDiagnostic]] = {}
        self.initialized = False
        self.shutdown = False
        self.logger = logging.getLogger(f"lsp.{language_id}")
        
        # Event handlers
        self.on_diagnostics: Optional[Callable[[str, List[LSPDiagnostic]], None]] = None
        self.on_log_message: Optional[Callable[[int, str], None]] = None
        
    async def start(self) -> bool:
        """Start the language server."""
        try:
            self.process = subprocess.Popen(
                self.server_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0
            )
            
            # Start reading responses in background
            asyncio.create_task(self._read_responses())
            
            # Initialize the server
            await self._initialize()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start LSP server: {e}")
            return False
    
    async def stop(self) -> None:
        """Stop the language server."""
        if not self.shutdown and self.process:
            try:
                await self._shutdown()
                await self._exit()
            except Exception as e:
                self.logger.error(f"Error during shutdown: {e}")
            
            if self.process:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                self.process = None
    
    async def _initialize(self) -> None:
        """Initialize the language server."""
        init_params = {
            "processId": None,
            "rootPath": str(self.root_path),
            "rootUri": f"file://{self.root_path}",
            "capabilities": {
                "textDocument": {
                    "completion": {"completionItem": {"snippetSupport": True}},
                    "hover": {"contentFormat": ["markdown", "plaintext"]},
                    "signatureHelp": {"signatureInformation": {"documentationFormat": ["markdown", "plaintext"]}},
                    "definition": {"linkSupport": True},
                    "references": {"context": True},
                    "documentSymbol": {"hierarchicalDocumentSymbolSupport": True},
                    "codeAction": {"codeActionLiteralSupport": {"codeActionKind": {"valueSet": []}}},
                    "rename": {"prepareSupport": True},
                    "publishDiagnostics": {"relatedInformation": True},
                },
                "workspace": {
                    "workspaceFolders": True,
                    "symbol": {"symbolKind": {"valueSet": list(range(1, 27))}},
                    "executeCommand": {},
                    "workspaceEdit": {"documentChanges": True},
                    "didChangeConfiguration": {"dynamicRegistration": True},
                }
            },
            "initializationOptions": {},
            "workspaceFolders": [{
                "uri": f"file://{self.root_path}",
                "name": self.root_path.name
            }]
        }
        
        response = await self._send_request("initialize", init_params)
        if response:
            self.initialized = True
            await self._send_notification("initialized", {})
    
    async def _shutdown(self) -> None:
        """Shutdown the language server."""
        await self._send_request("shutdown", {})
        self.shutdown = True
    
    async def _exit(self) -> None:
        """Exit the language server."""
        await self._send_notification("exit", {})
    
    async def _send_request(self, method: str, params: Dict) -> Optional[Dict]:
        """Send a request to the language server."""
        if not self.process or not self.process.stdin:
            return None
        
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params
        }
        
        # Create future for response
        future = asyncio.Future()
        self.pending_requests[self.request_id] = future
        
        try:
            message = json.dumps(request)
            content = f"Content-Length: {len(message)}\r\n\r\n{message}"
            self.process.stdin.write(content)
            self.process.stdin.flush()
            
            # Wait for response with timeout
            return await asyncio.wait_for(future, timeout=30.0)
            
        except Exception as e:
            self.logger.error(f"Error sending request {method}: {e}")
            self.pending_requests.pop(self.request_id, None)
            return None
    
    async def _send_notification(self, method: str, params: Dict) -> None:
        """Send a notification to the language server."""
        if not self.process or not self.process.stdin:
            return
        
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        
        try:
            message = json.dumps(notification)
            content = f"Content-Length: {len(message)}\r\n\r\n{message}"
            self.process.stdin.write(content)
            self.process.stdin.flush()
            
        except Exception as e:
            self.logger.error(f"Error sending notification {method}: {e}")
    
    async def _read_responses(self) -> None:
        """Read responses from the language server."""
        if not self.process or not self.process.stdout:
            return
        
        buffer = ""
        while self.process and self.process.poll() is None:
            try:
                chunk = self.process.stdout.read(1024)
                if not chunk:
                    break
                
                buffer += chunk
                
                # Process complete messages
                while True:
                    # Look for Content-Length header
                    if "Content-Length:" not in buffer:
                        break
                    
                    header_end = buffer.find("\r\n\r\n")
                    if header_end == -1:
                        break
                    
                    # Extract content length
                    header = buffer[:header_end]
                    content_length = None
                    for line in header.split("\r\n"):
                        if line.startswith("Content-Length:"):
                            content_length = int(line.split(":")[1].strip())
                            break
                    
                    if content_length is None:
                        break
                    
                    # Check if we have the complete message
                    message_start = header_end + 4
                    if len(buffer) < message_start + content_length:
                        break
                    
                    # Extract and process message
                    message_content = buffer[message_start:message_start + content_length]
                    buffer = buffer[message_start + content_length:]
                    
                    try:
                        message = json.loads(message_content)
                        await self._handle_message(message)
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Failed to parse JSON message: {e}")
                
            except Exception as e:
                self.logger.error(f"Error reading from LSP server: {e}")
                break
    
    async def _handle_message(self, message: Dict) -> None:
        """Handle a message from the language server."""
        if "id" in message:
            # Response to a request
            request_id = message["id"]
            if request_id in self.pending_requests:
                future = self.pending_requests.pop(request_id)
                if "error" in message:
                    future.set_exception(Exception(message["error"]))
                else:
                    future.set_result(message.get("result"))
        
        elif "method" in message:
            # Notification from server
            method = message["method"]
            params = message.get("params", {})
            
            if method == "textDocument/publishDiagnostics":
                await self._handle_diagnostics(params)
            elif method == "window/logMessage":
                await self._handle_log_message(params)
    
    async def _handle_diagnostics(self, params: Dict) -> None:
        """Handle diagnostic notifications."""
        uri = params.get("uri", "")
        diagnostics_data = params.get("diagnostics", [])
        
        diagnostics = []
        for diag_data in diagnostics_data:
            range_data = diag_data.get("range", {})
            start_data = range_data.get("start", {})
            end_data = range_data.get("end", {})
            
            diagnostic = LSPDiagnostic(
                range=LSPRange(
                    start=LSPPosition(start_data.get("line", 0), start_data.get("character", 0)),
                    end=LSPPosition(end_data.get("line", 0), end_data.get("character", 0))
                ),
                severity=diag_data.get("severity", 1),
                code=diag_data.get("code"),
                source=diag_data.get("source"),
                message=diag_data.get("message", ""),
                related_information=diag_data.get("relatedInformation", [])
            )
            diagnostics.append(diagnostic)
        
        self.diagnostics[uri] = diagnostics
        
        if self.on_diagnostics:
            self.on_diagnostics(uri, diagnostics)
    
    async def _handle_log_message(self, params: Dict) -> None:
        """Handle log message notifications."""
        message_type = params.get("type", 1)
        message = params.get("message", "")
        
        if self.on_log_message:
            self.on_log_message(message_type, message)
    
    # Document operations
    async def did_open(self, file_path: Path, content: str) -> None:
        """Notify server that a document was opened."""
        await self._send_notification("textDocument/didOpen", {
            "textDocument": {
                "uri": f"file://{file_path}",
                "languageId": self.language_id,
                "version": 1,
                "text": content
            }
        })
    
    async def did_change(self, file_path: Path, content: str, version: int) -> None:
        """Notify server that a document was changed."""
        await self._send_notification("textDocument/didChange", {
            "textDocument": {
                "uri": f"file://{file_path}",
                "version": version
            },
            "contentChanges": [{"text": content}]
        })
    
    async def did_close(self, file_path: Path) -> None:
        """Notify server that a document was closed."""
        await self._send_notification("textDocument/didClose", {
            "textDocument": {"uri": f"file://{file_path}"}
        })
    
    # Language features
    async def completion(self, file_path: Path, line: int, character: int) -> List[LSPCompletionItem]:
        """Get completion items at a position."""
        response = await self._send_request("textDocument/completion", {
            "textDocument": {"uri": f"file://{file_path}"},
            "position": {"line": line, "character": character}
        })
        
        if not response:
            return []
        
        items = response if isinstance(response, list) else response.get("items", [])
        
        completion_items = []
        for item in items:
            completion_items.append(LSPCompletionItem(
                label=item.get("label", ""),
                kind=item.get("kind", 1),
                detail=item.get("detail"),
                documentation=item.get("documentation"),
                insert_text=item.get("insertText"),
                sort_text=item.get("sortText")
            ))
        
        return completion_items
    
    async def hover(self, file_path: Path, line: int, character: int) -> Optional[LSPHover]:
        """Get hover information at a position."""
        response = await self._send_request("textDocument/hover", {
            "textDocument": {"uri": f"file://{file_path}"},
            "position": {"line": line, "character": character}
        })
        
        if not response:
            return None
        
        contents = response.get("contents", "")
        if isinstance(contents, list):
            contents = [str(c) for c in contents]
        else:
            contents = str(contents)
        
        range_data = response.get("range")
        hover_range = None
        if range_data:
            start_data = range_data.get("start", {})
            end_data = range_data.get("end", {})
            hover_range = LSPRange(
                start=LSPPosition(start_data.get("line", 0), start_data.get("character", 0)),
                end=LSPPosition(end_data.get("line", 0), end_data.get("character", 0))
            )
        
        return LSPHover(contents=contents, range=hover_range)
    
    async def definition(self, file_path: Path, line: int, character: int) -> List[LSPLocation]:
        """Get definition locations for a symbol."""
        response = await self._send_request("textDocument/definition", {
            "textDocument": {"uri": f"file://{file_path}"},
            "position": {"line": line, "character": character}
        })
        
        if not response:
            return []
        
        locations = response if isinstance(response, list) else [response]
        
        result = []
        for loc in locations:
            if not isinstance(loc, dict):
                continue
            
            range_data = loc.get("range", {})
            start_data = range_data.get("start", {})
            end_data = range_data.get("end", {})
            
            result.append(LSPLocation(
                uri=loc.get("uri", ""),
                range=LSPRange(
                    start=LSPPosition(start_data.get("line", 0), start_data.get("character", 0)),
                    end=LSPPosition(end_data.get("line", 0), end_data.get("character", 0))
                )
            ))
        
        return result
    
    async def references(self, file_path: Path, line: int, character: int, include_declaration: bool = True) -> List[LSPLocation]:
        """Get reference locations for a symbol."""
        response = await self._send_request("textDocument/references", {
            "textDocument": {"uri": f"file://{file_path}"},
            "position": {"line": line, "character": character},
            "context": {"includeDeclaration": include_declaration}
        })
        
        if not response:
            return []
        
        result = []
        for loc in response:
            if not isinstance(loc, dict):
                continue
            
            range_data = loc.get("range", {})
            start_data = range_data.get("start", {})
            end_data = range_data.get("end", {})
            
            result.append(LSPLocation(
                uri=loc.get("uri", ""),
                range=LSPRange(
                    start=LSPPosition(start_data.get("line", 0), start_data.get("character", 0)),
                    end=LSPPosition(end_data.get("line", 0), end_data.get("character", 0))
                )
            ))
        
        return result
    
    async def document_symbols(self, file_path: Path) -> List[LSPSymbol]:
        """Get symbols in a document."""
        response = await self._send_request("textDocument/documentSymbol", {
            "textDocument": {"uri": f"file://{file_path}"}
        })
        
        if not response:
            return []
        
        symbols = []
        for symbol_data in response:
            location_data = symbol_data.get("location", {})
            range_data = location_data.get("range", {})
            start_data = range_data.get("start", {})
            end_data = range_data.get("end", {})
            
            symbols.append(LSPSymbol(
                name=symbol_data.get("name", ""),
                kind=symbol_data.get("kind", 1),
                location=LSPLocation(
                    uri=location_data.get("uri", f"file://{file_path}"),
                    range=LSPRange(
                        start=LSPPosition(start_data.get("line", 0), start_data.get("character", 0)),
                        end=LSPPosition(end_data.get("line", 0), end_data.get("character", 0))
                    )
                ),
                container_name=symbol_data.get("containerName"),
                detail=symbol_data.get("detail")
            ))
        
        return symbols


class LSPManager:
    """Manages multiple LSP clients for different languages."""
    
    def __init__(self, config: Config, root_path: Path):
        self.config = config
        self.root_path = root_path
        self.clients: Dict[str, LSPClient] = {}
        self.server_configs = self._load_server_configs()
        self.logger = logging.getLogger("lsp.manager")
    
    def _load_server_configs(self) -> Dict[str, Dict]:
        """Load LSP server configurations."""
        default_configs = {
            "python": {
                "command": ["pylsp"],
                "extensions": [".py"],
                "language_id": "python"
            },
            "javascript": {
                "command": ["typescript-language-server", "--stdio"],
                "extensions": [".js", ".jsx", ".ts", ".tsx"],
                "language_id": "javascript"
            },
            "typescript": {
                "command": ["typescript-language-server", "--stdio"],
                "extensions": [".ts", ".tsx"],
                "language_id": "typescript"
            },
            "rust": {
                "command": ["rust-analyzer"],
                "extensions": [".rs"],
                "language_id": "rust"
            },
            "go": {
                "command": ["gopls"],
                "extensions": [".go"],
                "language_id": "go"
            },
            "java": {
                "command": ["jdtls"],
                "extensions": [".java"],
                "language_id": "java"
            },
            "cpp": {
                "command": ["clangd"],
                "extensions": [".cpp", ".cxx", ".cc", ".c", ".h", ".hpp"],
                "language_id": "cpp"
            }
        }
        
        # Override with user config if available
        user_configs = self.config.get("lsp.servers", {})
        for lang, user_config in user_configs.items():
            if lang in default_configs:
                default_configs[lang].update(user_config)
            else:
                default_configs[lang] = user_config
        
        return default_configs
    
    def get_language_for_file(self, file_path: Path) -> Optional[str]:
        """Get the language identifier for a file."""
        extension = file_path.suffix.lower()
        
        for lang, config in self.server_configs.items():
            if extension in config.get("extensions", []):
                return lang
        
        return None
    
    async def get_client(self, language: str) -> Optional[LSPClient]:
        """Get or create an LSP client for a language."""
        if language in self.clients:
            return self.clients[language]
        
        if language not in self.server_configs:
            return None
        
        config = self.server_configs[language]
        client = LSPClient(
            server_command=config["command"],
            root_path=self.root_path,
            language_id=config["language_id"]
        )
        
        if await client.start():
            self.clients[language] = client
            return client
        
        return None
    
    async def get_client_for_file(self, file_path: Path) -> Optional[LSPClient]:
        """Get an LSP client for a specific file."""
        language = self.get_language_for_file(file_path)
        if not language:
            return None
        
        return await self.get_client(language)
    
    async def shutdown_all(self) -> None:
        """Shutdown all LSP clients."""
        for client in self.clients.values():
            try:
                await client.stop()
            except Exception as e:
                self.logger.error(f"Error shutting down LSP client: {e}")
        
        self.clients.clear()
    
    def is_supported(self, file_path: Path) -> bool:
        """Check if a file is supported by any LSP server."""
        return self.get_language_for_file(file_path) is not None
    
    async def get_diagnostics(self, file_path: Path) -> List[LSPDiagnostic]:
        """Get diagnostics for a file."""
        client = await self.get_client_for_file(file_path)
        if not client:
            return []
        
        uri = f"file://{file_path}"
        return client.diagnostics.get(uri, [])
    
    async def get_completion(self, file_path: Path, line: int, character: int) -> List[LSPCompletionItem]:
        """Get completion items for a position in a file."""
        client = await self.get_client_for_file(file_path)
        if not client:
            return []
        
        return await client.completion(file_path, line, character)
    
    async def get_hover(self, file_path: Path, line: int, character: int) -> Optional[LSPHover]:
        """Get hover information for a position in a file."""
        client = await self.get_client_for_file(file_path)
        if not client:
            return None
        
        return await client.hover(file_path, line, character)
    
    async def get_definition(self, file_path: Path, line: int, character: int) -> List[LSPLocation]:
        """Get definition locations for a symbol."""
        client = await self.get_client_for_file(file_path)
        if not client:
            return []
        
        return await client.definition(file_path, line, character)
    
    async def get_references(self, file_path: Path, line: int, character: int) -> List[LSPLocation]:
        """Get reference locations for a symbol."""
        client = await self.get_client_for_file(file_path)
        if not client:
            return []
        
        return await client.references(file_path, line, character)
    
    async def get_symbols(self, file_path: Path) -> List[LSPSymbol]:
        """Get symbols in a document."""
        client = await self.get_client_for_file(file_path)
        if not client:
            return []
        
        return await client.document_symbols(file_path)