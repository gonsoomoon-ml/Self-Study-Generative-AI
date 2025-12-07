"""
Shared utilities for session management demos.
"""


class Colors:
    """Terminal color codes."""
    USER = "\033[94m"      # Blue
    AGENT = "\033[92m"     # Green
    SYSTEM = "\033[93m"    # Yellow
    ERROR = "\033[91m"     # Red
    SUCCESS = "\033[92m"   # Green
    BOLD = "\033[1m"
    RESET = "\033[0m"


def print_user(message: str):
    """Print user message with formatting."""
    print(f"\n{Colors.BOLD}{Colors.USER}[User]{Colors.RESET} {message}")


def print_agent(message: str):
    """Print agent response with formatting."""
    print(f"\n{Colors.BOLD}{Colors.AGENT}[Agent]{Colors.RESET} {message}\n")


def print_system(message: str):
    """Print system message with formatting."""
    print(f"\n{Colors.SYSTEM}>>> {message}{Colors.RESET}")


def print_error(message: str):
    """Print error message with formatting."""
    print(f"\n{Colors.BOLD}{Colors.ERROR}>>> {message}{Colors.RESET}")


def print_success(message: str):
    """Print success message with formatting."""
    print(f"\n{Colors.BOLD}{Colors.SUCCESS}>>> {message}{Colors.RESET}")


def print_header(title: str):
    """Print demo header."""
    print("=" * 60)
    print(f"{Colors.BOLD}{title}{Colors.RESET}")
    print("=" * 60)


def print_separator():
    """Print separator line."""
    print("\n" + "-" * 60)


def chat(agent, message: str):
    """Send message to agent and print conversation."""
    print_user(message)
    response = agent(message)
    print_agent(response)
    return response
