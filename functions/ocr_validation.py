import os
import csv
import asyncio
import logging
import json
import re
from anthropic import Anthropic, RateLimitError, APIError
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
from logging_utils import log, log_found, log_progress

# Silence HTTP request logging
logging.getLogger("httpx").disabled = True
logging.getLogger("anthropic").disabled = True
logging.getLogger("httpcore").disabled = True

@dataclass
class ValidationResult:
    filename: str
    verbatim_text: str
    proposed_location: str
    validation_status: str
    final_location: str
    confidence_notes: str = ""
    error: Optional[str] = None

    def to_dict(self):
        return {
            field: getattr(self, field) 
            for field in self.__dataclass_fields__
        }

def safe_parse_response(response_text: str) -> dict:
    """
    Safely parse Claude's response without using eval()
    """
    # First, try to extract a dictionary-like structure from the text
    dictionary_pattern = r'\{.*?\}'
    # Use re.DOTALL to make '.' match newlines as well
    matches = re.findall(dictionary_pattern, response_text, re.DOTALL)
    
    if matches:
        # Take the longest match, which is likely the most complete dictionary
        longest_match = max(matches, key=len)
        
        # Try parsing with JSON first (more secure than eval)
        try:
            # Replace single quotes with double quotes for JSON compatibility
            json_compatible = longest_match.replace("'", '"')
            # Handle trailing commas in the dictionary which are not valid JSON
            json_compatible = re.sub(r',\s*}', '}', json_compatible)
            return json.loads(json_compatible)
        except json.JSONDecodeError:
            pass
    
    # If we can't extract a clean dictionary, look for key fields individually
    result = {}
    
    # Extract validation_status
    status_pattern = r"'validation_status':\s*'([^']*)'|\"validation_status\":\s*\"([^\"]*)\""
    status_match = re.search(status_pattern, response_text)
    if status_match:
        status = status_match.group(1) or status_match.group(2)
        result['validation_status'] = status
    else:
        # Default to UNKNOWN if we can't extract
        result['validation_status'] = 'UNKNOWN'
    
    # Extract final_location
    location_pattern = r"'final_location':\s*'([^']*)'|\"final_location\":\s*\"([^\"]*)\""
    location_match = re.search(location_pattern, response_text)
    if location_match:
        location = location_match.group(1) or location_match.group(2)
        result['final_location'] = location
    else:
        # Default to UNKNOWN if we can't extract
        result['final_location'] = 'UNKNOWN'
    
    # Extract confidence_notes
    notes_pattern = r"'confidence_notes':\s*'([^']*)'|\"confidence_notes\":\s*\"([^\"]*)\""
    notes_match = re.search(notes_pattern, response_text)
    if notes_match:
        notes = notes_match.group(1) or notes_match.group(2)
        result['confidence_notes'] = notes
    else:
        result['confidence_notes'] = ""
        
    return result

class LocationValidator:
    def __init__(self, api_key: str, max_retries: int = 7, retry_delay: float = 5.0, concurrent_api_calls: int = 12):
        self.client = Anthropic(api_key=api_key)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        # Increase concurrency since CSV validation is very lightweight
        self.semaphore = asyncio.Semaphore(concurrent_api_calls)
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

    async def api_call_with_retry(self, model_config: dict, **kwargs) -> dict:
        for attempt in range(self.max_retries):
            try:
                async with self.semaphore:
                    call_kwargs = {
                        'model': model_config['model'],
                        'max_tokens': model_config['max_tokens'],
                        **kwargs
                    }
                    response = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self.client.messages.create(**call_kwargs)
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

    async def validate_single_entry(self, filename: str, transcription: str, location: str, prompts: dict, model_config: dict, current: int, total: int) -> ValidationResult:
        try:
            log_progress("validate_speclabels", current, total, f"Processing {filename}")
            
            response = await self.api_call_with_retry(
                model_config,  # Add model_config
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
            
            # Use our robust parser instead of eval()
            try:
                content = safe_parse_response(content_text)
                
                # Ensure required fields are present and have values
                if not content.get('validation_status'):
                    content['validation_status'] = 'UNKNOWN'
                if not content.get('final_location'):
                    content['final_location'] = 'UNKNOWN'
                if not content.get('confidence_notes'):
                    content['confidence_notes'] = ""
                
                # Normalize validation status
                status = content['validation_status'].upper()
                if status not in ['VERIFIED', 'UNRELIABLE', 'UNKNOWN']:
                    if 'VERIF' in status:
                        status = 'VERIFIED'
                    elif 'UNRELIABLE' in status:
                        status = 'UNRELIABLE'
                    else:
                        status = 'UNKNOWN'
                content['validation_status'] = status
                
                # Make sure final location is "UNKNOWN" for non-verified status
                if status != 'VERIFIED' and content['final_location'] != 'UNKNOWN':
                    content['final_location'] = 'UNKNOWN'
                
                return ValidationResult(
                    filename=filename,
                    verbatim_text=transcription,
                    proposed_location=location,
                    validation_status=content['validation_status'],
                    final_location=content['final_location'],
                    confidence_notes=content.get('confidence_notes', "")
                )
            except Exception as e:
                # Create a backup simple result based on patterns
                log(f"Using fallback parsing for {filename}: {e}")
                
                # Default to UNKNOWN status
                status = 'UNKNOWN'
                final_location = 'UNKNOWN'
                
                # Look for status indicators in the text
                if 'VERIFIED' in content_text or 'verified' in content_text.lower():
                    status = 'VERIFIED'
                    # If verified, try to use the proposed location
                    final_location = location
                elif 'UNRELIABLE' in content_text or 'unreliable' in content_text.lower():
                    status = 'UNRELIABLE'
                
                return ValidationResult(
                    filename=filename,
                    verbatim_text=transcription,
                    proposed_location=location,
                    validation_status=status,
                    final_location=final_location,
                    confidence_notes="Parsed with fallback method."
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
                confidence_notes="",
                error=error_msg
            )

    def write_results(self, results: List[ValidationResult], output_csv: str):
        """Write multiple results at once to reduce file I/O operations"""
        if not results:
            return
            
        fieldnames = ['filename', 'verbatim_text', 'proposed_location', 
                     'validation_status', 'final_location', 'confidence_notes',
                     'error']
        
        file_exists = os.path.exists(output_csv)
        
        with open(output_csv, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            for result in results:
                writer.writerow(vars(result))

    async def validate_locations(self, input_csv: str, output_csv: str, prompts: dict, model_config: dict) -> Tuple[List[ValidationResult], int]:
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
        
        # Process entries in batches for better performance
        batch_size = 20
        for i in range(0, len(unprocessed_rows), batch_size):
            batch = unprocessed_rows[i:min(i+batch_size, len(unprocessed_rows))]
            
            # Process batch concurrently
            batch_tasks = []
            for j, row in enumerate(batch, 1):
                task = self.validate_single_entry(
                    row['filename'],
                    row['transcription'],
                    row['location'],
                    prompts,
                    model_config,  # Add model_config
                    i + j,  # Adjust for overall progress
                    len(unprocessed_rows)
                )
                batch_tasks.append(task)
            
            batch_results = await asyncio.gather(*batch_tasks)
            
            # Handle results
            batch_to_write = []
            for result in batch_results:
                results.append(result)
                batch_to_write.append(result)
                
                if not result.error and result.validation_status != 'ERROR':
                    self.processed_files.add(result.filename)
                    processed += 1
                else:
                    errors += 1
            
            # Write batch of results at once
            self.write_results(batch_to_write, output_csv)
            
            # Small pause between batches to prevent rate limiting
            await asyncio.sleep(0.5)

        log(f"Complete. {processed} processed, {skipped} skipped, {errors} errors")
        return results, processed

async def validate_transcriptions(input_csv: str, output_csv: str, api_key: str, prompts: dict, model_config: dict) -> Tuple[List[ValidationResult], int]:
    try:
        # Initialize with higher concurrency since this is just text processing
        validator = LocationValidator(
            api_key,
            concurrent_api_calls=12  # Increased from 1 to 12
        )
        return await validator.validate_locations(input_csv, output_csv, prompts, model_config)
    except Exception as e:
        log(f"Failed to validate locations: {e}")
        raise
