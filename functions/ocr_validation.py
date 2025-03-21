import os
import csv
import asyncio
from anthropic import Anthropic, RateLimitError, APIError
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
from logging_utils import log, log_found, log_progress

@dataclass
class ValidationResult:
    filename: str
    verbatim_text: str
    proposed_location: str
    validation_status: str
    final_location: str
    confidence_notes: str
    error: Optional[str] = None

    def to_dict(self):
        return {
            field: getattr(self, field) 
            for field in self.__dataclass_fields__
        }

class LocationValidator:
    def __init__(self, api_key: str, max_retries: int = 7, retry_delay: float = 5.0):
        self.client = Anthropic(api_key=api_key)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.semaphore = asyncio.Semaphore(1)
        self.processed_files = set()
        
    def load_processed_files(self, output_csv: str) -> None:
        if not os.path.exists(output_csv):
            return
            
        try:
            with open(output_csv, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    error = row.get('error')
                    if (error is None or error == '' or error == 'None') and row.get('validation_status') != 'ERROR':
                        self.processed_files.add(row['filename'])
        except Exception as e:
            log(f"Failed to load processed files: {e}")

    async def api_call_with_retry(self, **kwargs) -> dict:
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
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(self.retry_delay * (2 ** attempt))

    async def validate_single_entry(self, filename: str, transcription: str, location: str, prompts: dict, current: int, total: int) -> ValidationResult:
        try:
            log_progress("validate_speclabels", current, total, f"Processing {filename}")
            
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
    
            # Parse the response
            content_text = response.content[0].text.strip()
            content_text = content_text.replace('<userStyle>Normal</userStyle>', '').strip()
            
            try:
                content = eval(content_text)
                
                # Ensure required fields are present
                content['verbatim_text'] = transcription
                content['proposed_location'] = location
                
                return ValidationResult(
                    filename=filename,
                    **content
                )
            except Exception as e:
                # Handle parsing errors
                log(f"Failed to parse validation response: {e}")
                return ValidationResult(
                    filename=filename,
                    verbatim_text=transcription,
                    proposed_location=location,
                    validation_status='ERROR',
                    final_location='ERROR',
                    confidence_notes=f'Failed to parse validation response: {e}',
                    error=f'Parsing error: {str(e)}'
                )
    
        except Exception as e:
            error_msg = f"Error: {filename} - {str(e)}"
            log(error_msg)
            return ValidationResult(
                filename=filename,
                verbatim_text=transcription,
                proposed_location=location,
                validation_status='ERROR',
                final_location='ERROR',
                confidence_notes=str(e),
                error=error_msg
            )

    def write_results(self, result: ValidationResult, output_csv: str):
        fieldnames = ['filename', 'verbatim_text', 'proposed_location', 
                     'validation_status', 'final_location', 'confidence_notes', 
                     'error']
        
        file_exists = os.path.exists(output_csv)
        
        with open(output_csv, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(vars(result))

    async def validate_locations(self, input_csv: str, output_csv: str, prompts: dict) -> Tuple[List[ValidationResult], int]:
        self.load_processed_files(output_csv)
        
        if not os.path.exists(input_csv):
            log(f"Input CSV not found: {input_csv}")
            return [], 0
            
        # Read all entries from input CSV
        with open(input_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        if not rows:
            log(f"No entries found in input CSV: {input_csv}")
            return [], 0
            
        log_found("entries to validate", len(rows))
        
        # Filter out already processed files
        unprocessed_rows = [
            row for row in rows 
            if row['filename'] not in self.processed_files
        ]
        
        skipped = len(rows) - len(unprocessed_rows)
        if skipped > 0:
            log(f"Found {skipped} previously processed entries")
        
        if not unprocessed_rows:
            log("All entries already processed")
            return [], 0
        
        results = []
        processed = 0
        errors = 0
        
        # Process each entry
        for i, row in enumerate(unprocessed_rows, 1):
            result = await self.validate_single_entry(
                row['filename'],
                row['transcription'],
                row['location'],
                prompts,
                i,
                len(unprocessed_rows)
            )
            
            results.append(result)
            
            if not result.error and result.validation_status != 'ERROR':
                self.processed_files.add(row['filename'])
                processed += 1
            else:
                errors += 1
            
            self.write_results(result, output_csv)

        log(f"Complete. {processed} processed, {skipped} skipped, {errors} errors")
        return results, processed

async def validate_transcriptions(input_csv: str, output_csv: str, api_key: str, prompts: dict) -> Tuple[List[ValidationResult], int]:
    try:
        validator = LocationValidator(api_key)
        return await validator.validate_locations(input_csv, output_csv, prompts)
    except Exception as e:
        log(f"Failed to validate locations: {e}")
        raise