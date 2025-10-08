"""Main application module."""


def add(a: int, b: int) -> int:
    """Add two integers and return the result.

    Args:
        a: First integer
        b: Second integer

    Returns:
        Sum of a and b
    """
    return a + b


def main() -> None:
    """Entry point for the application."""
    result = add(2, 3)
    print(f"Result: {result}")


if __name__ == "__main__":
    main()
