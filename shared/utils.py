def flatten(nested_list: list) -> list:
    """Flatten a nested list into a single-level list."""
    flat = []
    for item in nested_list:
        if isinstance(item, list):
            flat.extend(flatten(item))
        else:
            flat.append(item)
    return flat
