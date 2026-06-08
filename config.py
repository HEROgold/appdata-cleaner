from pathlib import Path
from confkit import Config, Set

Config.set_file(Path("config.ini"))


class Settings:
    # You can customize these keywords to target specific folder names
    KEYWORDS = Config(
        Set({"cache", "temp", "crash", "report", "dump", "crashes", "pending"})
    )
    MAX_DEPTH = Config(3)
    AUTO_SCAN = Config(True)
    EXCLUDE = Config(
        Set(
            {
                Path("C:/Windows"),
                Path("C:/Program Files"),
                Path("C:/Program Files (x86)"),
            }
        )
    )
