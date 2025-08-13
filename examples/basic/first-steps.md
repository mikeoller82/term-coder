# First Steps with Term-Coder

A complete walkthrough of your first term-coder session.

## Prerequisites

- Python 3.10+ installed
- A code project to work with (or use our sample project)
- Basic familiarity with command line

## Step 1: Installation

```bash
# Install term-coder
pip install term-coder

# Verify installation
tc --version
```

Expected output:
```
term-coder version 1.0.0
```

## Step 2: Project Setup

Navigate to your project directory (or create a sample one):

```bash
# Option 1: Use existing project
cd your-existing-project

# Option 2: Create sample project
mkdir my-first-tc-project
cd my-first-tc-project

# Create some sample files
cat > main.py << 'EOF'
def greet(name):
    return f"Hello, {name}!"

def main():
    user_name = input("Enter your name: ")
    message = greet(user_name)
    print(message)

if __name__ == "__main__":
    main()
EOF

cat > utils.py << 'EOF'
import os
import json

def read_config(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def ensure_directory(path):
    os.makedirs(path, exist_ok=True)
EOF

# Initialize git (optional but recommended)
git init
git add .
git commit -m "Initial commit"
```

## Step 3: Initialize Term-Coder

```bash
# Initialize term-coder in your project
tc init
```

This creates:
- `.term-coder/config.yaml` - Configuration file
- `.term-coder/sessions/` - Chat session storage
- `.term-coder/index.tsv` - File index (created later)

## Step 4: Configure API Key (Optional)

If you want to use cloud AI models:

```bash
# Set OpenAI API key
export OPENAI_API_KEY="your-api-key-here"

# Or edit the config file
nano .term-coder/config.yaml
```

Add to config:
```yaml
llm:
  openai_api_key: "${OPENAI_API_KEY}"
  default_model: "openai:gpt-4o-mini"
```

For offline usage, you can skip this step and use local models later.

## Step 5: Build Search Index

```bash
# Build index of your project files
tc index
```

Expected output:
```
Indexed 2/2 files -> .term-coder/index.tsv
```

## Step 6: Your First Chat

```bash
# Ask about your project
tc chat "What does this project do?"
```

Expected interaction:
```
You: What does this project do?
AI: This project appears to be a simple Python application with two main components:

1. **main.py**: Contains a greeting application that:
   - Prompts the user to enter their name
   - Uses a `greet()` function to create a personalized greeting
   - Prints the greeting message

2. **utils.py**: Contains utility functions for:
   - Reading JSON configuration files
   - Creating directories safely

The main functionality is a basic interactive greeting program, with some utility functions that could be used for configuration management and file operations.
```

## Step 7: Search Your Code

```bash
# Search for specific functionality
tc search "greet"
```

Expected output:
```
main.py:1: def greet(name):
main.py:5: message = greet(user_name)
```

```bash
# Try semantic search
tc search "user input" --semantic
```

Expected output:
```
main.py: score=0.847
utils.py: score=0.234
```

## Step 8: Make Your First Edit

```bash
# Add error handling to the main function
tc edit "add try-catch error handling to the main function" --files main.py
```

Expected output:
```
Proposed Diff
─────────────────────────────────────────────────────────────────────────────
--- main.py
+++ main.py
@@ -3,8 +3,12 @@
 
 def main():
-    user_name = input("Enter your name: ")
-    message = greet(user_name)
-    print(message)
+    try:
+        user_name = input("Enter your name: ")
+        message = greet(user_name)
+        print(message)
+    except KeyboardInterrupt:
+        print("\nGoodbye!")
+    except Exception as e:
+        print(f"An error occurred: {e}")
 
 if __name__ == "__main__":

Summary
─────────────────────────────────────────────────────────────────────────────
Files: 1  +6 -4  Safety: 0.95
```

## Step 9: Review and Apply Changes

```bash
# Review the proposed changes
tc diff
```

```bash
# Apply the changes if they look good
tc apply
```

Expected output:
```
Applied. Backup: backup_20240101_120000_abc123
```

## Step 10: Verify Changes

```bash
# Check that the file was modified
cat main.py
```

You should see the error handling has been added.

```bash
# Test the modified code
python main.py
```

## Step 11: Explore More Features

### Git Integration
```bash
# Review your changes
tc review

# Generate a commit message
tc commit
```

### Code Explanation
```bash
# Explain a specific function
tc explain "main.py#greet"

# Explain a range of lines
tc explain "main.py:1:5"
```

### Testing
```bash
# Run tests (if you have any)
tc test

# Generate test suggestions
tc edit "create unit tests for the greet function" --files test_main.py
```

## Step 12: Session Management

```bash
# Start a new named session
tc chat "Let's discuss improvements" --session improvements

# Continue previous session
tc chat "What other features could we add?" --session improvements

# List sessions
ls .term-coder/sessions/
```

## Common First-Time Issues

### "Config not found"
```bash
# Make sure you're in the right directory
pwd
ls -la .term-coder/

# Re-initialize if needed
tc init
```

### "No API key"
```bash
# Check if API key is set
echo $OPENAI_API_KEY

# Use offline mode if no API key
tc privacy offline_mode true
```

### "No search results"
```bash
# Rebuild index
tc index

# Check index file
wc -l .term-coder/index.tsv
```

### "Permission denied"
```bash
# Check file permissions
ls -la .term-coder/

# Fix permissions if needed
chmod 755 .term-coder/
chmod 644 .term-coder/config.yaml
```

## Next Steps

Now that you've completed your first session:

1. **Read the [CLI Reference](../../docs/cli-reference.md)** - Learn all available commands
2. **Explore [Configuration](../../docs/configuration.md)** - Customize term-coder for your needs
3. **Try [Advanced Usage](../../docs/advanced-usage.md)** - Power user features
4. **Check out [Framework Examples](../frameworks/)** - Language-specific workflows

## Tips for Success

1. **Start Small**: Begin with simple questions and edits
2. **Review Everything**: Always check diffs before applying changes
3. **Use Sessions**: Organize conversations by topic
4. **Build Good Indexes**: Keep your search index updated
5. **Experiment**: Try different search modes and models
6. **Read Outputs**: Pay attention to AI explanations and suggestions

## Sample Session Transcript

Here's what a typical first session might look like:

```bash
$ tc init
Initialized .term-coder/config.yaml

$ tc index
Indexed 2/2 files -> .term-coder/index.tsv

$ tc chat "What files are in this project?"
You: What files are in this project?
AI: Based on the indexed files, this project contains:

1. **main.py** - The main application file with greeting functionality
2. **utils.py** - Utility functions for configuration and file operations

$ tc search "input"
main.py:5:    user_name = input("Enter your name: ")

$ tc edit "add a docstring to the greet function" --files main.py
[Shows diff with docstring added]

$ tc apply
Applied. Backup: backup_20240101_120000_abc123

$ tc chat "The code looks good now!"
You: The code looks good now!
AI: Great! The code is now more robust with error handling and better documentation. Some next steps you might consider:

1. Adding unit tests for the functions
2. Creating a configuration file for customizable greetings
3. Adding logging for better debugging
4. Creating a CLI interface with argument parsing

Would you like help with any of these improvements?
```

Congratulations! You've successfully completed your first term-coder session. You're now ready to explore more advanced features and integrate term-coder into your development workflow.