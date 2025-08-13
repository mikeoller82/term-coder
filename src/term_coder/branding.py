"""
Branding and visual elements for term-coder.
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.columns import Columns
import random
import time


def get_ascii_logo() -> str:
    """Get the awesome ASCII logo for term-coder."""
    return """
╔╦╗╔═╗╦═╗╔╦╗   ╔═╗╔═╗╔╦╗╔═╗╦═╗
 ║ ║╣ ╠╦╝║║║───║  ║ ║ ║║║╣ ╠╦╝
 ╩ ╚═╝╩╚═╩ ╩   ╚═╝╚═╝═╩╝╚═╝╩╚═
    """


def get_alternative_logo() -> str:
    """Alternative ASCII logo."""
    return """
████████╗ ██████╗
╚══██╔══╝██╔════╝
   ██║   ██║     
   ██║   ██║     
   ██║   ╚██████╗
   ╚═╝    ╚═════╝
    """


def get_compact_logo() -> str:
    """Compact ASCII logo for smaller spaces."""
    return """
▀█▀ ▄▀█
 █  █▄▀
    """


def show_welcome_screen(console: Console):
    """Show the awesome welcome screen with logo and introduction."""
    
    # Clear screen for dramatic effect
    console.clear()
    
    # Main logo with gradient colors
    logo_text = Text(get_ascii_logo(), style="bold cyan")
    
    # Tagline
    tagline = Text("🤖 Your AI Coding Companion", style="bold magenta")
    tagline_2 = Text("Just talk naturally - I'll understand what you want to do!", style="dim cyan")
    
    # Version and status
    version_text = Text("v1.0.0", style="dim green")
    status_text = Text("● Ready to assist", style="bold green")
    
    # Create the main panel
    welcome_content = Align.center(
        Text.assemble(
            logo_text, "\n\n",
            tagline, "\n",
            tagline_2, "\n\n",
            Text("Examples:", style="bold yellow"), "\n",
            Text("  • ", style="dim"), Text("debug for errors", style="cyan"), "\n",
            Text("  • ", style="dim"), Text("fix the authentication bug", style="cyan"), "\n", 
            Text("  • ", style="dim"), Text("explain how login works", style="cyan"), "\n",
            Text("  • ", style="dim"), Text("add error handling to main.py", style="cyan"), "\n\n",
            Text("Type ", style="dim"), Text("help", style="bold yellow"), Text(" for more commands or just start chatting!", style="dim"), "\n\n",
            version_text, Text("  ", style="dim"), status_text
        )
    )
    
    # Show the welcome panel
    welcome_panel = Panel(
        welcome_content,
        title="🚀 Welcome to Term-Coder",
        title_align="center",
        border_style="bright_cyan",
        padding=(1, 2),
        expand=False
    )
    
    console.print(welcome_panel)
    console.print()


def show_init_screen(console: Console):
    """Show initialization screen with logo."""
    console.clear()
    
    # Show logo
    logo = Text(get_ascii_logo(), style="bold cyan")
    console.print(Align.center(logo))
    console.print()
    
    # Initialization message
    init_text = Text.assemble(
        Text("🎉 Welcome to ", style="bold green"),
        Text("Term-Coder", style="bold cyan"),
        Text("!", style="bold green"), "\n\n",
        Text("Setting up your AI coding assistant...", style="dim cyan")
    )
    
    init_panel = Panel(
        Align.center(init_text),
        title="🔧 Initialization",
        border_style="green",
        padding=(1, 2)
    )
    
    console.print(init_panel)
    console.print()


def get_witty_comments() -> dict:
    """Get witty comments for different operations."""
    return {
        "searching": [
            "🔍 Hunting through your code like a digital detective...",
            "🕵️ Scanning files faster than you can say 'grep'...",
            "🔎 Looking for clues in your codebase...",
            "📚 Speed-reading your entire project...",
            "🎯 Targeting the perfect matches...",
            "🧭 Navigating the maze of your code...",
            "🔬 Analyzing code with scientific precision...",
            "🏃 Racing through files at light speed...",
        ],
        
        "indexing": [
            "📇 Building a map of your code universe...",
            "🗂️ Organizing files like a digital librarian...",
            "📊 Creating a searchable index of awesomeness...",
            "🏗️ Constructing the foundation for lightning-fast search...",
            "📋 Cataloging every line of code...",
            "🎯 Preparing for precision targeting...",
            "🧠 Teaching the AI about your codebase...",
            "⚡ Supercharging search capabilities...",
        ],
        
        "thinking": [
            "🤔 Pondering the mysteries of your code...",
            "🧠 Neural networks firing at full capacity...",
            "💭 Contemplating the perfect solution...",
            "🎭 Channeling my inner coding genius...",
            "🔮 Consulting the oracle of algorithms...",
            "⚡ Synapses sparking with brilliant ideas...",
            "🎨 Crafting the perfect response...",
            "🚀 Launching into deep thought mode...",
            "🎪 Performing computational acrobatics...",
            "🧙 Weaving code magic...",
        ],
        
        "analyzing": [
            "🔬 Putting your code under the microscope...",
            "🕵️ Sherlock Holmes-ing your codebase...",
            "📊 Crunching numbers and patterns...",
            "🎯 Zeroing in on the important bits...",
            "🧪 Running experiments on your code...",
            "📈 Analyzing trends and patterns...",
            "🎨 Appreciating the artistry of your code...",
            "🏛️ Studying the architecture like a scholar...",
        ],
        
        "fixing": [
            "🔧 Rolling up sleeves and getting to work...",
            "🩹 Applying digital band-aids to code wounds...",
            "⚡ Zapping bugs with laser precision...",
            "🛠️ Fine-tuning your code like a master craftsman...",
            "🎯 Targeting issues with surgical accuracy...",
            "🧰 Opening the toolkit of solutions...",
            "💊 Prescribing the perfect code medicine...",
            "🎪 Performing debugging magic tricks...",
        ],
        
        "generating": [
            "✨ Conjuring code from the digital ether...",
            "🎨 Painting with pixels and semicolons...",
            "🏗️ Architecting your digital dreams...",
            "🎭 Performing the ancient art of code creation...",
            "🌟 Birthing beautiful code into existence...",
            "🎪 Pulling code rabbits out of algorithmic hats...",
            "🚀 Launching your ideas into code reality...",
            "🧙 Weaving spells of syntax and logic...",
        ],
        
        "testing": [
            "🧪 Mixing potions in the testing laboratory...",
            "🎯 Taking aim at potential bugs...",
            "🔍 Investigating code like CSI: Codebase...",
            "🏃 Running tests faster than Usain Bolt...",
            "🎪 Performing quality assurance acrobatics...",
            "🛡️ Defending your code against the forces of chaos...",
            "🎨 Painting a picture of code quality...",
            "⚡ Stress-testing at the speed of light...",
        ],
        
        "committing": [
            "📝 Crafting the perfect commit message...",
            "💾 Saving your masterpiece to git history...",
            "🎯 Targeting the perfect commit...",
            "📚 Adding another chapter to your code story...",
            "🏆 Celebrating another milestone...",
            "🎪 Performing git magic...",
            "⚡ Lightning-fast version control...",
            "🎨 Creating art in the git timeline...",
        ],
        
        "loading": [
            "⏳ Loading awesomeness...",
            "🎪 Preparing the show...",
            "🚀 Initializing rocket boosters...",
            "⚡ Charging up the AI engines...",
            "🎯 Calibrating precision instruments...",
            "🧠 Warming up the neural networks...",
            "🎨 Preparing the digital canvas...",
            "🔮 Consulting the code crystal ball...",
        ]
    }


def get_random_comment(category: str) -> str:
    """Get a random witty comment for the given category."""
    comments = get_witty_comments()
    if category in comments:
        return random.choice(comments[category])
    return "🤖 Working on it..."


def show_progress_with_wit(console: Console, category: str, duration: float = 2.0):
    """Show progress with witty comments."""
    comment = get_random_comment(category)
    
    # Show the comment
    console.print(f"[dim]{comment}[/dim]")
    
    # Simple progress simulation
    import time
    time.sleep(duration)


def show_completion_message(console: Console, category: str, success: bool = True):
    """Show completion message with appropriate emoji and style."""
    if success:
        messages = {
            "searching": "🎯 Found what you're looking for!",
            "indexing": "📇 Index built successfully!",
            "thinking": "💡 Eureka! I've got it!",
            "analyzing": "📊 Analysis complete!",
            "fixing": "🔧 All fixed up!",
            "generating": "✨ Code generated successfully!",
            "testing": "🧪 Tests completed!",
            "committing": "📝 Changes committed!",
            "loading": "⚡ Ready to go!"
        }
        
        message = messages.get(category, "✅ Task completed!")
        console.print(f"[bold green]{message}[/bold green]")
    else:
        console.print(f"[bold red]❌ Oops! Something went wrong.[/bold red]")


def show_easter_eggs(console: Console, trigger: str):
    """Show fun easter eggs for special inputs."""
    easter_eggs = {
        "hello": [
            "👋 Well hello there, fellow code wizard!",
            "🎩 *tips digital hat* Greetings, human!",
            "🤖 Hello! Ready to write some amazing code together?",
        ],
        "thanks": [
            "🎉 You're very welcome! Happy to help!",
            "😊 Anytime! That's what I'm here for!",
            "🚀 My pleasure! Let's build something awesome!",
        ],
        "awesome": [
            "🎪 You're pretty awesome yourself!",
            "⭐ Aww, you're making my circuits blush!",
            "🎯 Right back at you, coding superstar!",
        ],
        "magic": [
            "🧙‍♂️ *waves digital wand* Abracadabra!",
            "✨ The real magic is in your code!",
            "🎩 *pulls a bug fix out of hat*",
        ]
    }
    
    trigger_lower = trigger.lower()
    for key, messages in easter_eggs.items():
        if key in trigger_lower:
            message = random.choice(messages)
            console.print(f"[bold magenta]{message}[/bold magenta]")
            return True
    
    return False


def show_tips_and_tricks(console: Console):
    """Show helpful tips and tricks."""
    tips = [
        "💡 Tip: Be specific! Instead of 'fix bug', try 'fix the authentication timeout issue'",
        "🎯 Pro tip: Mention file names for better context - 'add logging to auth.py'",
        "🚀 Speed tip: Use 'tc' without arguments to start interactive mode",
        "🔍 Search tip: Try semantic search with 'find code that handles user authentication'",
        "🛡️ Safety tip: Always review changes with 'tc diff' before applying",
        "⚡ Quick tip: Use natural language - 'debug for errors' works better than 'debug'",
        "🎨 Style tip: I understand context - 'clean up the messy auth code' vs 'clean up old files'",
        "🧠 Smart tip: Ask questions! 'How does the login system work?' gets detailed explanations",
    ]
    
    tip = random.choice(tips)
    console.print(f"\n[dim]{tip}[/dim]")


def animate_logo(console: Console):
    """Animate the logo for fun."""
    frames = [
        "🤖 Term-Coder",
        "⚡ Term-Coder", 
        "🚀 Term-Coder",
        "✨ Term-Coder",
        "🎯 Term-Coder",
    ]
    
    for frame in frames:
        console.clear()
        console.print(Align.center(Text(frame, style="bold cyan")))
        time.sleep(0.3)


def show_feature_highlight(console: Console):
    """Show a random feature highlight."""
    features = [
        "🔍 I can search your entire codebase semantically - try 'find authentication logic'",
        "🛡️ I always create backups before making changes - your code is safe with me!",
        "🧠 I understand context - mention files, functions, or describe what you want",
        "⚡ I work with any programming language and framework",
        "🎯 I can debug, fix, explain, refactor, test, and generate code",
        "🔒 I respect your privacy - enable offline mode for complete local operation",
        "🎪 I have a sense of humor - coding should be fun!",
        "🚀 I learn from your codebase to give better suggestions",
    ]
    
    feature = random.choice(features)
    console.print(f"\n[bold blue]Did you know?[/bold blue] [dim]{feature}[/dim]")


def show_motivational_message(console: Console):
    """Show a motivational coding message."""
    messages = [
        "🌟 Every bug you fix makes you a better developer!",
        "🚀 Great code is written one line at a time!",
        "💪 You've got this! Let's tackle that challenge together!",
        "🎯 Clean code is not written by following a set of rules. Clean code is written by someone who cares!",
        "⚡ The best error message is the one that never shows up!",
        "🧠 Code is poetry written for machines but read by humans!",
        "🎨 Programming is an art form that fights back!",
        "🏆 Today's impossible is tomorrow's breakthrough!",
    ]
    
    message = random.choice(messages)
    console.print(f"\n[bold yellow]{message}[/bold yellow]")