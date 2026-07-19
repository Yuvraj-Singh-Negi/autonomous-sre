def process_data(data: dict) -> int:
    """Process input data and return computed result.
    
    Bug: Division by zero when data['count'] is 0.
    """
    total = data.get("total", 0)
    count = data.get("count", 0)
    result = total / count  # Bug: division by zero when count is 0
    return int(result)


def validate_input(data: dict) -> bool:
    """Validate input data has required fields."""
    return "total" in data and "count" in data