import os
import csv
import logging
import asyncio
from anthropic import Anthropic, RateLimitError, APIError
from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple, Optional, Dict

@dataclass
class ValidationResult:
    filename: str
    verbatim_text: str
    proposed_location: str
    validation_status: str
    final_location: str
    confidence_notes: str
    processing_time: float = 0
    error: Optional[str] = None

    def to_dict(self):
        return {
            field: getattr(self, field) 
            for field in self.__dataclass_fields__
        }

class LocationValidator:
    def __init__(self, api_key: str, max_retries: int = 7, retry_delay: float = 5.0):
        self.client = Anthropic(api_key=api_key)
        self.SONNET_RATE = 0.00025
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.semaphore = asyncio.Semaphore(1)
        self.processed_files = set()
        
        # Suppress verbose logs from external libraries
        logging.getLogger('anthropic').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('httpcore').setLevel(logging.WARNING)

        # Setup basic logging for our application
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def load_processed_files(self, output_csv: str) -> None:
        """Load list of already processed files from existing CSV."""
        if not os.path.exists(output_csv):
            return
            
        try:
            with open(output_csv, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['error'] is None or row['error'] == '':  # Only count successfully processed files
                        if row['validation_status'] != 'ERROR':  # And valid validations
                            self.processed_files.add(row['filename'])
        except Exception as e:
            print(f"Error loading processed files: {e}")

    async def api_call_with_retry(self, **kwargs) -> dict:
        """Make API call with exponential backoff retry logic."""
        for attempt in range(self.max_retries):
            try:
                async with self.semaphore:
                    response = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self.client.messages.create(**kwargs)
                    )
                    return response
            except RateLimitError:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
            except APIError as e:
                if attempt == self.max_retries - 1:
                    raise
                if e.status_code < 500:
                    raise
                await asyncio.sleep(self.retry_delay * (2 ** attempt))

    async def validate_single_entry(self, filename: str, transcription: str, location: str, prompts: dict) -> ValidationResult:
        """Validate a single location entry using Claude."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            response = await self.api_call_with_retry(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                system=prompts['system'],
                messages=[{
                    "role": "user",
                    "content": prompts['user'].format(
                        transcribed_text=transcription, 
                        proposed_location=location
                    )
                }]
            )

            try:
                # New approach to parse the response
                content = eval(response.content[0].text.strip())
            except:
                content = {
                    'verbatim_text': transcription,
                    'proposed_location': location,
                    'validation_status': 'ERROR',
                    'final_location': 'ERROR',
                    'confidence_notes': 'Failed to parse validation response'
                }

            processing_time = asyncio.get_event_loop().time() - start_time
            return ValidationResult(
                filename=filename,
                **content,
                processing_time=processing_time
            )

        except Exception as e:
            error_msg = f"Error validating {filename}: {str(e)}"
            print(error_msg)
            return ValidationResult(
                filename=filename,
                verbatim_text=transcription,
                proposed_location=location,
                validation_status='ERROR',
                final_location='ERROR',
                confidence_notes=str(e),
                error=error_msg
            )

    def write_results(self, results: List[ValidationResult], output_csv: str):
        """Write validation results to CSV file."""
        fieldnames = ['filename', 'verbatim_text', 'proposed_location', 
                     'validation_status', 'final_location', 'confidence_notes', 
                     'processing_time', 'error']
        
        file_exists = os.path.exists(output_csv)
        mode = 'a' if file_exists else 'w'
        
        with open(output_csv, mode, newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:  # Only write header for new files
                writer.writeheader()
            for result in results:
                writer.writerow(vars(result))

    async def validate_locations(self, input_csv: str, output_csv: str, prompts: dict) -> Tuple[List[ValidationResult], int]:
        """Validate locations from input CSV using Claude."""
        self.load_processed_files(output_csv)
        
        results = []
        successful = 0
        total_cost = 0
        skipped = 0
        
        with open(input_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            total_files = len(rows)
                
            for i, row in enumerate(rows, 1):
                # Skip if already processed
                if row['filename'] in self.processed_files:
                    skipped += 1
                    print(f"Image {i}/{total_files} (skipped)", end='\r')
                    continue
                
                print(f"Image {i}/{total_files}", end='\r')
                
                # Validate entry
                result = await self.validate_single_entry(
                    row['filename'],
                    row['transcription'],
                    row['location'],
                    prompts
                )
                
                input_tokens = len(f"Validate location data:\nTranscribed text: {row['transcription']}\nProposed location: {row['location']}".split())
                output_tokens = len(str(result.__dict__).split())
                cost = (input_tokens * 0.03 / 1000) + (output_tokens * 0.06 / 1000)
                total_cost += cost
                
                results.append(result)
                
                if not result.error and result.validation_status != 'ERROR':
                    successful += 1
                    self.processed_files.add(row['filename'])  # Add to processed set after successful validation
                
                self.write_results([result], output_csv)

        print(f"\nComplete: {successful} processed, {skipped} skipped (${total_cost:.2f})")
        return results, successful


async def validate_transcriptions(input_csv: str, output_csv: str, api_key: str, prompts: dict) -> Tuple[List[ValidationResult], int]:
    """
    Wrapper function to validate location interpretations using Claude.
    
    Args:
        input_csv: Path to input CSV with transcriptions and locations
        output_csv: Path to output CSV for validation results
        api_key: Anthropic API key
        prompts: Dictionary containing system and user prompts for validation
    
    Returns:
        Tuple containing list of ValidationResult objects and count of successful validations
    """
    try:
        validator = LocationValidator(api_key)
        return await validator.validate_locations(input_csv, output_csv, prompts)
    except Exception as e:
        print(f"Failed to validate locations: {str(e)}")
        raise
