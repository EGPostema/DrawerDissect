import time
from typing import Optional


def log(message: str) -> None:
    """Print a message to the console."""
    print(message)


def log_found(item_type: str, count: int) -> None:
    """Log how many items were found for processing."""
    log(f"Found {count} {item_type} to process")


def log_progress(step: str, current: int, total: int, message: Optional[str] = None) -> None:
    """
    Show a progress counter that updates in place on the same line.
    Moves to a new line when the last item is reached.
    """
    if message:
        print(f"\rProcessing {current}/{total} - {message}", end="", flush=True)
    else:
        print(f"\rProcessing {current}/{total}", end="", flush=True)

    if current == total:
        print()


class StepTimer:
    """
    Context manager (a 'with' block) that logs when a step starts,
    how long it took, and any errors that occurred.

    Usage:
        with StepTimer("find_trays"):
            ... do the work ...
    """

    def __init__(self, step_name: str):
        self.step_name = step_name
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        log(f"Starting {self.step_name}...")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            log(f"{self.step_name} complete! Total time: {duration:.2f}s")
            log("-" * 95)

        if exc_type:
            log(f"Error in {self.step_name}: {exc_val}")
            return False
        return True
