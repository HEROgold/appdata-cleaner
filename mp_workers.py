from queue import Queue
from threading import Event
import multiprocessing  # Added for IPC Queue

from PySide6.QtCore import QThread, Signal

from pathlib import Path
from typing import override

from config import Settings

from humanize import naturalsize
from herogold.loops import (
    parallel,
    cpu_count,
)  # Imported cpu_count for executor management
from concurrent.futures import ProcessPoolExecutor


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
        """Scans the base paths in parallel, streaming results back via a MP Queue."""
        count: int = 0

        # Use a Manager Queue so it can be shared cleanly across process pools
        with multiprocessing.Manager() as manager:
            queue: Queue[Path] = manager.Queue()

            # Start processes via executor
            with ProcessPoolExecutor(max_workers=cpu_count) as executor:
                # Submit jobs. Workers will now stream paths directly into the queue
                futures = [
                    # pyrefly: ignore [bad-argument-type]
                    executor.submit(scan_path, path, queue, 0, self.max_depth)  # ty:ignore[invalid-argument-type] # pyright: ignore[reportArgumentType]
                    for path in self.base_paths
                ]

                # While workers run, read from the queue live in the QThread
                # Stop if our thread is explicitly cancelled or when all tasks finish
                while not self._stop_event.is_set() and (
                    not all(f.done() for f in futures) or not queue.empty()
                ):
                    try:
                        # Short timeout lets us frequently check self._stop_event or f.done()
                        found_path = queue.get(timeout=0.05)
                        self.process_single_result(found_path)
                        count += 1
                        self.progress.emit(count)
                    except Exception:
                        # Queue was empty on this poll tick, loop around
                        continue

                # Ensure background workers terminate if stopped early
                if self._stop_event.is_set():
                    executor.shutdown(wait=False, cancel_futures=True)

        self.finished.emit(count)

    def process_single_result(self, path: Path) -> None:
        """Processes a single matching path and emits the folder_found signal."""
        try:
            size = path.stat().st_size
            size_human = naturalsize(size, binary=True)
            self.folder_found.emit(str(path), size_human, str(size))
        except PermissionError, OSError:
            # Safe catch if the file was deleted/locked since the scan found it
            pass


def is_match(path: Path) -> bool:
    """Helper to check if a path's name matches our filter keywords."""
    if path in Settings.EXCLUDE:
        return False
    name_lower = path.name.casefold()
    return any(keyword in name_lower for keyword in Settings.KEYWORDS)


def scan_path(
    path: Path, queue: multiprocessing.Queue[Path], depth: int = 0, max_depth: int = 3
) -> None:
    """Scans a single path recursively, pushing matched folders to the queue instantly."""
    if depth > max_depth:
        return

    try:
        # Resolve files cleanly without doing multiple disk lookups
        children = list(path.iterdir())
    except PermissionError, OSError:
        return

    for i in children:
        # Check against keywords immediately as items come in
        if is_match(i):
            queue.put(i)

        if i.is_dir():
            # Recursively scan down subdirectories
            scan_path(i, queue, depth + 1, max_depth)
