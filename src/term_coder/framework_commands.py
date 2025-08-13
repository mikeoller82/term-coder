from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import subprocess
import json

from .config import Config
from .language_aware import LanguageAwareContextEngine, FrameworkInfo


@dataclass
class FrameworkCommand:
    """Represents a framework-specific command."""
    name: str
    description: str
    command: List[str]
    working_dir: Optional[Path] = None
    env_vars: Optional[Dict[str, str]] = None
    requires_files: List[str] = None
    
    def execute(self, cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
        """Execute the framework command."""
        working_directory = cwd or self.working_dir or Path.cwd()
        env = dict(os.environ)
        if self.env_vars:
            env.update(self.env_vars)
        
        return subprocess.run(
            self.command,
            cwd=working_directory,
            env=env,
            capture_output=True,
            text=True
        )


class FrameworkCommandRegistry:
    """Registry for framework-specific commands."""
    
    def __init__(self, config: Config, language_engine: LanguageAwareContextEngine):
        self.config = config
        self.language_engine = language_engine
        self.commands: Dict[str, Dict[str, FrameworkCommand]] = {}
        self._register_default_commands()
    
    def _register_default_commands(self) -> None:
        """Register default framework commands."""
        self._register_django_commands()
        self._register_flask_commands()
        self._register_fastapi_commands()
        self._register_react_commands()
        self._register_vue_commands()
        self._register_angular_commands()
        self._register_spring_commands()
        self._register_rust_commands()
        self._register_go_commands()
        self._register_node_commands()
    
    def _register_django_commands(self) -> None:
        """Register Django-specific commands."""
        django_commands = {
            "runserver": FrameworkCommand(
                name="runserver",
                description="Start Django development server",
                command=["python", "manage.py", "runserver"],
                requires_files=["manage.py"]
            ),
            "migrate": FrameworkCommand(
                name="migrate",
                description="Apply database migrations",
                command=["python", "manage.py", "migrate"],
                requires_files=["manage.py"]
            ),
            "makemigrations": FrameworkCommand(
                name="makemigrations",
                description="Create new database migrations",
                command=["python", "manage.py", "makemigrations"],
                requires_files=["manage.py"]
            ),
            "shell": FrameworkCommand(
                name="shell",
                description="Start Django shell",
                command=["python", "manage.py", "shell"],
                requires_files=["manage.py"]
            ),
            "test": FrameworkCommand(
                name="test",
                description="Run Django tests",
                command=["python", "manage.py", "test"],
                requires_files=["manage.py"]
            ),
            "collectstatic": FrameworkCommand(
                name="collectstatic",
                description="Collect static files",
                command=["python", "manage.py", "collectstatic", "--noinput"],
                requires_files=["manage.py"]
            ),
            "createsuperuser": FrameworkCommand(
                name="createsuperuser",
                description="Create Django superuser",
                command=["python", "manage.py", "createsuperuser"],
                requires_files=["manage.py"]
            )
        }
        self.commands["django"] = django_commands
    
    def _register_flask_commands(self) -> None:
        """Register Flask-specific commands."""
        flask_commands = {
            "run": FrameworkCommand(
                name="run",
                description="Start Flask development server",
                command=["flask", "run"],
                env_vars={"FLASK_ENV": "development"}
            ),
            "shell": FrameworkCommand(
                name="shell",
                description="Start Flask shell",
                command=["flask", "shell"]
            ),
            "init-db": FrameworkCommand(
                name="init-db",
                description="Initialize database",
                command=["flask", "init-db"]
            )
        }
        self.commands["flask"] = flask_commands
    
    def _register_fastapi_commands(self) -> None:
        """Register FastAPI-specific commands."""
        fastapi_commands = {
            "dev": FrameworkCommand(
                name="dev",
                description="Start FastAPI development server",
                command=["uvicorn", "main:app", "--reload"],
                requires_files=["main.py"]
            ),
            "start": FrameworkCommand(
                name="start",
                description="Start FastAPI production server",
                command=["uvicorn", "main:app"],
                requires_files=["main.py"]
            )
        }
        self.commands["fastapi"] = fastapi_commands
    
    def _register_react_commands(self) -> None:
        """Register React-specific commands."""
        react_commands = {
            "start": FrameworkCommand(
                name="start",
                description="Start React development server",
                command=["npm", "start"],
                requires_files=["package.json"]
            ),
            "build": FrameworkCommand(
                name="build",
                description="Build React app for production",
                command=["npm", "run", "build"],
                requires_files=["package.json"]
            ),
            "test": FrameworkCommand(
                name="test",
                description="Run React tests",
                command=["npm", "test"],
                requires_files=["package.json"]
            ),
            "eject": FrameworkCommand(
                name="eject",
                description="Eject from Create React App",
                command=["npm", "run", "eject"],
                requires_files=["package.json"]
            )
        }
        self.commands["react"] = react_commands
    
    def _register_vue_commands(self) -> None:
        """Register Vue.js-specific commands."""
        vue_commands = {
            "serve": FrameworkCommand(
                name="serve",
                description="Start Vue development server",
                command=["npm", "run", "serve"],
                requires_files=["package.json"]
            ),
            "build": FrameworkCommand(
                name="build",
                description="Build Vue app for production",
                command=["npm", "run", "build"],
                requires_files=["package.json"]
            ),
            "test": FrameworkCommand(
                name="test",
                description="Run Vue tests",
                command=["npm", "run", "test:unit"],
                requires_files=["package.json"]
            )
        }
        self.commands["vue"] = vue_commands
    
    def _register_angular_commands(self) -> None:
        """Register Angular-specific commands."""
        angular_commands = {
            "serve": FrameworkCommand(
                name="serve",
                description="Start Angular development server",
                command=["ng", "serve"],
                requires_files=["angular.json"]
            ),
            "build": FrameworkCommand(
                name="build",
                description="Build Angular app",
                command=["ng", "build"],
                requires_files=["angular.json"]
            ),
            "test": FrameworkCommand(
                name="test",
                description="Run Angular tests",
                command=["ng", "test"],
                requires_files=["angular.json"]
            ),
            "e2e": FrameworkCommand(
                name="e2e",
                description="Run Angular e2e tests",
                command=["ng", "e2e"],
                requires_files=["angular.json"]
            ),
            "generate": FrameworkCommand(
                name="generate",
                description="Generate Angular component/service/etc",
                command=["ng", "generate"],
                requires_files=["angular.json"]
            )
        }
        self.commands["angular"] = angular_commands
    
    def _register_spring_commands(self) -> None:
        """Register Spring Boot-specific commands."""
        spring_commands = {
            "run": FrameworkCommand(
                name="run",
                description="Run Spring Boot application",
                command=["./mvnw", "spring-boot:run"],
                requires_files=["pom.xml"]
            ),
            "test": FrameworkCommand(
                name="test",
                description="Run Spring Boot tests",
                command=["./mvnw", "test"],
                requires_files=["pom.xml"]
            ),
            "package": FrameworkCommand(
                name="package",
                description="Package Spring Boot application",
                command=["./mvnw", "package"],
                requires_files=["pom.xml"]
            ),
            "clean": FrameworkCommand(
                name="clean",
                description="Clean Spring Boot project",
                command=["./mvnw", "clean"],
                requires_files=["pom.xml"]
            )
        }
        self.commands["spring"] = spring_commands
    
    def _register_rust_commands(self) -> None:
        """Register Rust-specific commands."""
        rust_commands = {
            "run": FrameworkCommand(
                name="run",
                description="Run Rust application",
                command=["cargo", "run"],
                requires_files=["Cargo.toml"]
            ),
            "build": FrameworkCommand(
                name="build",
                description="Build Rust application",
                command=["cargo", "build"],
                requires_files=["Cargo.toml"]
            ),
            "test": FrameworkCommand(
                name="test",
                description="Run Rust tests",
                command=["cargo", "test"],
                requires_files=["Cargo.toml"]
            ),
            "check": FrameworkCommand(
                name="check",
                description="Check Rust code",
                command=["cargo", "check"],
                requires_files=["Cargo.toml"]
            ),
            "clippy": FrameworkCommand(
                name="clippy",
                description="Run Rust linter",
                command=["cargo", "clippy"],
                requires_files=["Cargo.toml"]
            ),
            "fmt": FrameworkCommand(
                name="fmt",
                description="Format Rust code",
                command=["cargo", "fmt"],
                requires_files=["Cargo.toml"]
            )
        }
        self.commands["rust_web"] = rust_commands
    
    def _register_go_commands(self) -> None:
        """Register Go-specific commands."""
        go_commands = {
            "run": FrameworkCommand(
                name="run",
                description="Run Go application",
                command=["go", "run", "."],
                requires_files=["go.mod"]
            ),
            "build": FrameworkCommand(
                name="build",
                description="Build Go application",
                command=["go", "build"],
                requires_files=["go.mod"]
            ),
            "test": FrameworkCommand(
                name="test",
                description="Run Go tests",
                command=["go", "test", "./..."],
                requires_files=["go.mod"]
            ),
            "mod-tidy": FrameworkCommand(
                name="mod-tidy",
                description="Tidy Go modules",
                command=["go", "mod", "tidy"],
                requires_files=["go.mod"]
            ),
            "fmt": FrameworkCommand(
                name="fmt",
                description="Format Go code",
                command=["go", "fmt", "./..."],
                requires_files=["go.mod"]
            ),
            "vet": FrameworkCommand(
                name="vet",
                description="Vet Go code",
                command=["go", "vet", "./..."],
                requires_files=["go.mod"]
            )
        }
        self.commands["go_web"] = go_commands
    
    def _register_node_commands(self) -> None:
        """Register Node.js-specific commands."""
        node_commands = {
            "start": FrameworkCommand(
                name="start",
                description="Start Node.js application",
                command=["npm", "start"],
                requires_files=["package.json"]
            ),
            "dev": FrameworkCommand(
                name="dev",
                description="Start Node.js development server",
                command=["npm", "run", "dev"],
                requires_files=["package.json"]
            ),
            "test": FrameworkCommand(
                name="test",
                description="Run Node.js tests",
                command=["npm", "test"],
                requires_files=["package.json"]
            ),
            "install": FrameworkCommand(
                name="install",
                description="Install Node.js dependencies",
                command=["npm", "install"],
                requires_files=["package.json"]
            ),
            "audit": FrameworkCommand(
                name="audit",
                description="Audit Node.js dependencies",
                command=["npm", "audit"],
                requires_files=["package.json"]
            )
        }
        self.commands["node"] = node_commands
    
    def get_available_commands(self, framework: str) -> Dict[str, FrameworkCommand]:
        """Get available commands for a framework."""
        return self.commands.get(framework, {})
    
    def get_command(self, framework: str, command_name: str) -> Optional[FrameworkCommand]:
        """Get a specific command for a framework."""
        framework_commands = self.commands.get(framework, {})
        return framework_commands.get(command_name)
    
    def can_execute_command(self, framework: str, command_name: str, cwd: Path) -> bool:
        """Check if a command can be executed in the current directory."""
        command = self.get_command(framework, command_name)
        if not command:
            return False
        
        if command.requires_files:
            for required_file in command.requires_files:
                if not (cwd / required_file).exists():
                    return False
        
        return True
    
    def execute_command(self, framework: str, command_name: str, cwd: Optional[Path] = None, args: List[str] = None) -> subprocess.CompletedProcess:
        """Execute a framework command."""
        command = self.get_command(framework, command_name)
        if not command:
            raise ValueError(f"Command {command_name} not found for framework {framework}")
        
        working_dir = cwd or Path.cwd()
        if not self.can_execute_command(framework, command_name, working_dir):
            raise ValueError(f"Cannot execute {command_name} in {working_dir}")
        
        # Add additional arguments if provided
        full_command = command.command.copy()
        if args:
            full_command.extend(args)
        
        # Create a new command with the full command
        exec_command = FrameworkCommand(
            name=command.name,
            description=command.description,
            command=full_command,
            working_dir=working_dir,
            env_vars=command.env_vars,
            requires_files=command.requires_files
        )
        
        return exec_command.execute(working_dir)


class FrameworkCommandExtensions:
    """Framework-specific command extensions for term-coder."""
    
    def __init__(self, config: Config, root_path: Path):
        self.config = config
        self.root_path = root_path
        self.language_engine = LanguageAwareContextEngine(config, root_path)
        self.command_registry = FrameworkCommandRegistry(config, self.language_engine)
    
    def get_detected_frameworks(self) -> Dict[str, FrameworkInfo]:
        """Get detected frameworks in the project."""
        return self.language_engine.detected_frameworks
    
    def get_framework_commands(self, framework: str) -> Dict[str, FrameworkCommand]:
        """Get available commands for a framework."""
        return self.command_registry.get_available_commands(framework)
    
    def execute_framework_command(self, framework: str, command: str, args: List[str] = None) -> subprocess.CompletedProcess:
        """Execute a framework-specific command."""
        return self.command_registry.execute_command(framework, command, self.root_path, args)
    
    def suggest_commands_for_context(self, file_path: Optional[Path] = None) -> List[Tuple[str, str, str]]:
        """Suggest relevant commands based on current context."""
        suggestions = []
        
        # Get detected frameworks
        frameworks = self.get_detected_frameworks()
        
        for framework_name, framework_info in frameworks.items():
            commands = self.get_framework_commands(framework_name)
            
            for command_name, command in commands.items():
                # Check if command can be executed
                if self.command_registry.can_execute_command(framework_name, command_name, self.root_path):
                    suggestions.append((framework_name, command_name, command.description))
        
        return suggestions
    
    def get_framework_specific_context(self, file_path: Path) -> Dict[str, Any]:
        """Get framework-specific context for a file."""
        context = asyncio.run(self.language_engine.analyze_file(file_path))
        if not context or not context.framework_info:
            return {}
        
        framework_name = context.framework_info["framework"]
        framework_info = self.language_engine.detected_frameworks.get(framework_name)
        
        if not framework_info:
            return {}
        
        return {
            "framework": framework_name,
            "version": framework_info.version,
            "pattern_type": context.framework_info.get("pattern_type"),
            "available_commands": list(self.get_framework_commands(framework_name).keys()),
            "related_files": self.language_engine.get_related_files(file_path),
            "test_files": self.language_engine.get_test_files_for(file_path),
            "config_files": [str(cf) for cf in framework_info.config_files],
            "entry_points": [str(ep) for ep in framework_info.entry_points]
        }
    
    def generate_framework_specific_code(self, framework: str, template_type: str, name: str, **kwargs) -> Optional[str]:
        """Generate framework-specific code templates."""
        generators = {
            "django": self._generate_django_code,
            "flask": self._generate_flask_code,
            "fastapi": self._generate_fastapi_code,
            "react": self._generate_react_code,
            "vue": self._generate_vue_code,
            "angular": self._generate_angular_code,
            "spring": self._generate_spring_code
        }
        
        generator = generators.get(framework)
        if generator:
            return generator(template_type, name, **kwargs)
        
        return None
    
    def _generate_django_code(self, template_type: str, name: str, **kwargs) -> Optional[str]:
        """Generate Django-specific code."""
        if template_type == "model":
            return f'''from django.db import models


class {name}(models.Model):
    """Model for {name}."""
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "{name}"
        verbose_name_plural = "{name}s"
    
    def __str__(self):
        return f"{name} {{self.id}}"
'''
        
        elif template_type == "view":
            return f'''from django.shortcuts import render
from django.http import JsonResponse
from django.views import View


class {name}View(View):
    """View for {name}."""
    
    def get(self, request):
        """Handle GET request."""
        return render(request, '{name.lower()}.html')
    
    def post(self, request):
        """Handle POST request."""
        return JsonResponse({{'status': 'success'}})
'''
        
        elif template_type == "serializer":
            return f'''from rest_framework import serializers
from .models import {name}


class {name}Serializer(serializers.ModelSerializer):
    """Serializer for {name} model."""
    
    class Meta:
        model = {name}
        fields = '__all__'
'''
        
        return None
    
    def _generate_flask_code(self, template_type: str, name: str, **kwargs) -> Optional[str]:
        """Generate Flask-specific code."""
        if template_type == "route":
            return f'''from flask import Blueprint, render_template, request, jsonify

{name.lower()}_bp = Blueprint('{name.lower()}', __name__)


@{name.lower()}_bp.route('/{name.lower()}', methods=['GET'])
def {name.lower()}_list():
    """List {name.lower()} items."""
    return render_template('{name.lower()}/list.html')


@{name.lower()}_bp.route('/{name.lower()}', methods=['POST'])
def {name.lower()}_create():
    """Create a new {name.lower()}."""
    data = request.get_json()
    # Process data here
    return jsonify({{'status': 'success'}})
'''
        
        return None
    
    def _generate_fastapi_code(self, template_type: str, name: str, **kwargs) -> Optional[str]:
        """Generate FastAPI-specific code."""
        if template_type == "router":
            return f'''from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/{name.lower()}", tags=["{name.lower()}"])


class {name}Create(BaseModel):
    """Schema for creating {name}."""
    pass


class {name}Response(BaseModel):
    """Schema for {name} response."""
    id: int


@router.get("/", response_model=List[{name}Response])
async def list_{name.lower()}():
    """List all {name.lower()} items."""
    return []


@router.post("/", response_model={name}Response)
async def create_{name.lower()}(item: {name}Create):
    """Create a new {name.lower()}."""
    return {name}Response(id=1)
'''
        
        return None
    
    def _generate_react_code(self, template_type: str, name: str, **kwargs) -> Optional[str]:
        """Generate React-specific code."""
        if template_type == "component":
            return f'''import React from 'react';

interface {name}Props {{
  // Define props here
}}

const {name}: React.FC<{name}Props> = (props) => {{
  return (
    <div className="{name.lower()}">
      <h1>{name}</h1>
      {{/* Component content */}}
    </div>
  );
}};

export default {name};
'''
        
        elif template_type == "hook":
            return f'''import {{ useState, useEffect }} from 'react';

interface Use{name}Return {{
  // Define return type here
}}

export const use{name} = (): Use{name}Return => {{
  const [state, setState] = useState();
  
  useEffect(() => {{
    // Effect logic here
  }}, []);
  
  return {{
    // Return values here
  }};
}};
'''
        
        return None
    
    def _generate_vue_code(self, template_type: str, name: str, **kwargs) -> Optional[str]:
        """Generate Vue.js-specific code."""
        if template_type == "component":
            return f'''<template>
  <div class="{name.lower()}">
    <h1>{name}</h1>
    <!-- Component template -->
  </div>
</template>

<script lang="ts">
import {{ defineComponent }} from 'vue';

export default defineComponent({{
  name: '{name}',
  props: {{
    // Define props here
  }},
  setup(props) {{
    // Component logic here
    
    return {{
      // Return reactive data and methods
    }};
  }}
}});
</script>

<style scoped>
.{name.lower()} {{
  /* Component styles */
}}
</style>
'''
        
        return None
    
    def _generate_angular_code(self, template_type: str, name: str, **kwargs) -> Optional[str]:
        """Generate Angular-specific code."""
        if template_type == "component":
            return f'''import {{ Component }} from '@angular/core';

@Component({{
  selector: 'app-{name.lower()}',
  template: `
    <div class="{name.lower()}">
      <h1>{name}</h1>
      <!-- Component template -->
    </div>
  `,
  styleUrls: ['./{name.lower()}.component.css']
}})
export class {name}Component {{
  constructor() {{ }}
  
  ngOnInit(): void {{
    // Initialization logic
  }}
}}
'''
        
        elif template_type == "service":
            return f'''import {{ Injectable }} from '@angular/core';
import {{ HttpClient }} from '@angular/common/http';
import {{ Observable }} from 'rxjs';

@Injectable({{
  providedIn: 'root'
}})
export class {name}Service {{
  private apiUrl = '/api/{name.lower()}';
  
  constructor(private http: HttpClient) {{ }}
  
  getAll(): Observable<any[]> {{
    return this.http.get<any[]>(this.apiUrl);
  }}
  
  create(data: any): Observable<any> {{
    return this.http.post<any>(this.apiUrl, data);
  }}
}}
'''
        
        return None
    
    def _generate_spring_code(self, template_type: str, name: str, **kwargs) -> Optional[str]:
        """Generate Spring Boot-specific code."""
        if template_type == "controller":
            return f'''package com.example.controller;

import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import java.util.List;

@RestController
@RequestMapping("/api/{name.lower()}")
public class {name}Controller {{
    
    @GetMapping
    public ResponseEntity<List<{name}>> getAll() {{
        // Implementation here
        return ResponseEntity.ok().build();
    }}
    
    @PostMapping
    public ResponseEntity<{name}> create(@RequestBody {name} {name.lower()}) {{
        // Implementation here
        return ResponseEntity.ok().build();
    }}
    
    @GetMapping("/{{id}}")
    public ResponseEntity<{name}> getById(@PathVariable Long id) {{
        // Implementation here
        return ResponseEntity.ok().build();
    }}
}}
'''
        
        elif template_type == "entity":
            return f'''package com.example.entity;

import javax.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "{name.lower()}")
public class {name} {{
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(name = "created_at")
    private LocalDateTime createdAt;
    
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;
    
    // Constructors
    public {name}() {{}}
    
    // Getters and setters
    public Long getId() {{
        return id;
    }}
    
    public void setId(Long id) {{
        this.id = id;
    }}
    
    @PrePersist
    protected void onCreate() {{
        createdAt = LocalDateTime.now();
        updatedAt = LocalDateTime.now();
    }}
    
    @PreUpdate
    protected void onUpdate() {{
        updatedAt = LocalDateTime.now();
    }}
}}
'''
        
        return None
    
    async def shutdown(self) -> None:
        """Shutdown the framework command extensions."""
        await self.language_engine.shutdown()