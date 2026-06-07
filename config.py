from pathlib import Path
from confkit import Config, Set

Config.set_file(Path("config.ini"))


class Settings:
    # You can customize these keywords to target specific folder names
    KEYWORDS = Config(
        Set({"cache", "temp", "crash", "report", "dump", "crashes", "pending"})
    )
