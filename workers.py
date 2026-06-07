from collections.abc import Generator
from threading import Event

from PySide6.QtCore import QThread, Signal


from pathlib import Path
from typing import override

from config import Settings

from humanize import naturalsize
from herogold.loops import parallel


class DeleteWorker(QThread):
    progress = Signal(int)
    # pyrefly: ignore [missing-override-decorator]
    finished = Signal()

    def __init__(self, paths: list[Path]) -> None:
        super().__init__()
        self.paths = paths

    @override
    def run(self) -> None:
        """Deletes the given paths in parallel, emitting progress updates."""
        # Issue, sometimes some items may not be removed
        # Permissions or WinErrors, these are ignored for now. We may want to catch and report them later.
        for index, _ in enumerate(parallel(Path.unlink, self.paths), 1):
            self.progress.emit(index)
        self.finished.emit()


class ScanWorker(QThread):
    progress = Signal(int)
    current_path = Signal(str)
    folder_found = Signal(str, str, str)  # path, size_human, size_bytes_str
    # pyrefly: ignore [missing-override-decorator]
    finished = Signal(int)  # total count

    def __init__(self, base_paths: list[Path], max_depth: int) -> None:
        super().__init__()
        self.base_paths = base_paths
        self.max_depth = max_depth
        self._stop_event = Event()

    def stop(self) -> None:
        self._stop_event.set()

    @override
    def run(self) -> None:
        """Scans the base paths in parallel, emitting progress and results."""
        count: int = 0
        for results in parallel(scan_path, self.base_paths):
            self.process_results(results)
        self.finished.emit(count)

    def process_results(self, results: set[Path]) -> None:
        """Processes the results from scanning a path, emitting folder_found signals for matches."""
        for i in filter_results(results):
            size = i.stat().st_size
            size_human = naturalsize(size, binary=True)
            self.folder_found.emit(str(i), size_human, str(size))


def filter_results(results: set[Path]) -> Generator[Path, None, None]:
    """Filters the scanned results for folders matching the keywords."""
    for i in results:
        if any(keyword in i.name.casefold() for keyword in Settings.KEYWORDS):
            yield i


def scan_path(path: Path, depth: int = 0) -> set[Path]:
    """Scans a single path recursively for folders matching keywords."""
    print(f"Scanning: {path}")
    scanned: set[Path] = set()
    if depth > Settings.MAX_DEPTH:
        return scanned

    try:
        path.iterdir()  # Check if we can access the directory
    except PermissionError, OSError:
        return scanned

    for i in path.iterdir():
        if i.is_dir():
            # Recursively scan subdirectories and include the current directory
            scanned.update(scan_path(i, depth + 1))
        scanned.add(i)
    return scanned
