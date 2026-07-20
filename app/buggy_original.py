def process_data(data: dict) -> int:
    total = data.get("total", 0)
    count = data.get("count", 0)
    result = total / count
    return int(result)


def validate_input(data: dict) -> bool:
    return "total" in data and "count" in data
