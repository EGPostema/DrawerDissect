import time
import os
from typing import Optional

# Singleton to track active steps
_ACTIVE_STEPS = {}

def log(message: str) -> None:
    """
    Simple log function to print a message without duplication.
    """
    print(message)
    
def start_step(step_name: str) -> None:
    """
    Start tracking a pipeline step.
    
    Args:
        step_name: Name of the step that's starting
    """
    _ACTIVE_STEPS[step_name] = {
        'start_time': time.time(),
        'processed': 0,
        'skipped': 0
    }
    log(f"Starting {step_name}...")

def end_step(step_name: str) -> None:
    """
    Mark the end of a pipeline step.
    
    Args:
        step_name: Name of the step that's ending
    """
    if step_name not in _ACTIVE_STEPS:
        return
    
    step_data = _ACTIVE_STEPS.pop(step_name)
    duration = time.time() - step_data['start_time']
    processed = step_data.get('processed', 0)
    skipped = step_data.get('skipped', 0)
    
    # Only log final summary if we actually tracked counts
    if processed > 0 or skipped > 0:
        log(f"{step_name} complete! {processed} processed, {skipped} skipped, {duration:.2f}s")
    else:
        log(f"{step_name} complete! Total time: {duration:.2f}s")

def log_found(item_type: str, count: int) -> None:
    """
    Log that items were found for processing.
    
    Args:
        item_type: Type of item found (e.g., "images", "files")
        count: Number of items found
    """
    log(f"Found {count} {item_type} to process")

def log_found_previous(item_type: str, count: int) -> None:
    """
    Log that previously processed items were found.
    
    Args:
        item_type: Type of item found (e.g., "images", "files")
        count: Number of items found
    """
    log(f"Found {count} previously processed {item_type}")

def log_progress(step: str, current: int, total: int, message: Optional[str] = None) -> None:
    """
    Log progress of current step.
    
    Args:
        step: Name of the current processing step
        current: Current item number
        total: Total items to process
        message: Optional message about current item
    """
    if message:
        print(f"\rProcessing {current}/{total} - {message}", end="", flush=True)
    else:
        print(f"\rProcessing {current}/{total}", end="", flush=True)
    
    # Print a newline when complete
    if current == total:
        print()

def log_skipped(item: str, reason: str) -> None:
    """
    Log a skipped item.
    
    Args:
        item: The item that was skipped
        reason: Why it was skipped
    """
    log(f"Skipped {item}: {reason}")

def increment_processed(step: str) -> None:
    """Increment processed count for a step."""
    if step in _ACTIVE_STEPS:
        _ACTIVE_STEPS[step]['processed'] = _ACTIVE_STEPS[step].get('processed', 0) + 1

def increment_skipped(step: str) -> None:
    """Increment skipped count for a step."""
    if step in _ACTIVE_STEPS:
        _ACTIVE_STEPS[step]['skipped'] = _ACTIVE_STEPS[step].get('skipped', 0) + 1

class StepTimer:
    """Context manager for timing steps with clean logging."""
    
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
            # Add a thin divider after each step completes
            log("-" * 95)
        
        if exc_type:
            log(f"Error in {self.step_name}: {exc_val}")
            return False
        return True
