def add(a: int, b: int) -> int:
    return a + b


def divide(a: float, b: float) -> float:
    return a / b


def calculate_average(numbers: list) -> float:
    if len(numbers) == 0:
        return 0
    return sum(numbers) / len(numbers)


def is_even(num: int) -> bool:
    return num % 2 == 0


def reverse_string(text: str) -> str:
    return text[::-1]
