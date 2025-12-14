"""
Simple calculator module to demonstrate Claude Code skills.
"""

def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b

def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

def calculate(operation, a, b):
    """
    Perform a calculation based on the operation type.

    Args:
        operation: One of 'add', 'subtract', 'multiply', 'divide'
        a: First number
        b: Second number

    Returns:
        Result of the calculation
    """
    operations = {
        'add': add,
        'subtract': subtract,
        'multiply': multiply,
        'divide': divide
    }

    if operation not in operations:
        raise ValueError(f"Unknown operation: {operation}")

    return operations[operation](a, b)


if __name__ == "__main__":
    print("Calculator Examples:")
    print(f"5 + 3 = {add(5, 3)}")
    print(f"10 - 4 = {subtract(10, 4)}")
    print(f"6 * 7 = {multiply(6, 7)}")
    print(f"20 / 4 = {divide(20, 4)}")
