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
        self.results_count = 0
        for base in self.base_paths:
            if self._stop_event.is_set():
                break
            self._scan_path(base, 0)
        self.finished.emit(self.results_count)

    def _scan_path(self, path: Path, depth: int) -> None:
        """Recursively scans the given path for folders matching keywords, emitting progress and results."""
        if (0 < depth <= self.max_depth) or self._stop_event.is_set():
            return
        try:
            self.current_path.emit(str(path))
            for entry in path.iterdir():
                if not entry.is_dir():
                    continue
                name = entry.name.lower()
                if any(kw in name for kw in Settings.KEYWORDS):
                    size = self._dir_size(entry)
                    # Skip folders with zero size
                    if size == 0:
                        continue
                    self.results_count += 1
                    size_human = naturalsize(size, binary=True)
                    self.folder_found.emit(str(entry), size_human, str(size))
                    self.progress.emit(self.results_count)
                    # Do not descend further inside this folder
                    continue
                # Recurse deeper
                self._scan_path(entry, depth + 1)
        except PermissionError:
            pass

    def _dir_size(self, directory: Path) -> int:
        return sum(f.stat().st_size for f in directory.rglob("*") if f.is_file())
