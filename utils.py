def parse_size(human: str) -> int:
    """Convert a human-readable size string (e.g., '10 MiB') to bytes."""
    try:
        multipliers = {
            "B": 1,
            "Bytes": 1,
            "KiB": 1024,
            "MiB": 1024**2,
            "GiB": 1024**3,
            "TiB": 1024**4,
            "kB": 1000,
            "MB": 1000**2,
            "GB": 1000**3,
            "TB": 1000**4,
        }
        parts = human.split()
        if len(parts) != 2:
            return 0
        number, unit = parts
        return int(float(number) * multipliers.get(unit, 1))
    except ValueError, KeyError, IndexError:
        return 0
