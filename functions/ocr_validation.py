import os
import csv
import logging
import asyncio
from anthropic import Anthropic, RateLimitError, APIError
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict

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
        
        # Suppress verbose logs from external libraries
        logging.getLogger('anthropic').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('httpcore').setLevel(logging.WARNING)

    def load_processed_files(self, output_csv: str) -> None:
        if not os.path.exists(output_csv):
            return
            
        try:
            with open(output_csv, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['error'] is None or row['error'] == '':
                        if row['validation_status'] != 'ERROR':
                            self.processed_files.add(row['filename'])
        except Exception as e:
            print(f"Error: Failed to load processed files - {e}")

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

    async def validate_single_entry(self, filename: str, transcription: str, location: str, prompts: dict) -> ValidationResult:
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
                content = eval(response.content[0].text.strip())
                content['verbatim_text'] = transcription
                content['proposed_location'] = location
            except:
                content = {
                    'verbatim_text': transcription,
                    'proposed_location': location,
                    'validation_status': 'ERROR',
                    'final_location': 'ERROR',
                    'confidence_notes': 'Failed to parse validation response'
                }
    
            return ValidationResult(
                filename=filename,
                **content
            )
    
        except Exception as e:
            error_msg = f"Error: {filename} - {str(e)}"
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
        fieldnames = ['filename', 'verbatim_text', 'proposed_location', 
                     'validation_status', 'final_location', 'confidence_notes', 
                     'error']
        
        file_exists = os.path.exists(output_csv)
        mode = 'a' if file_exists else 'w'
        
        with open(output_csv, mode, newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            for result in results:
                writer.writerow(vars(result))

    async def validate_locations(self, input_csv: str, output_csv: str, prompts: dict) -> Tuple[List[ValidationResult], int]:
        self.load_processed_files(output_csv)
        
        results = []
        successful = 0
        skipped = 0
        
        with open(input_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            total_files = len(rows)
            
            print(f"Found {total_files} entries to validate")
            
            for row in rows:
                if row['filename'] in self.processed_files:
                    skipped += 1
                    continue
                
                result = await self.validate_single_entry(
                    row['filename'],
                    row['transcription'],
                    row['location'],
                    prompts
                )
                
                results.append(result)
                
                if not result.error and result.validation_status != 'ERROR':
                    successful += 1
                    self.processed_files.add(row['filename'])
                else:
                    print(f"Error: {row['filename']} - Validation failed")
                
                self.write_results([result], output_csv)

        print(f"\nComplete. Processed: {successful}, Skipped: {skipped}, Errors: {len(results) - successful}")
        return results, successful

async def validate_transcriptions(input_csv: str, output_csv: str, api_key: str, prompts: dict) -> Tuple[List[ValidationResult], int]:
    try:
        validator = LocationValidator(api_key)
        return await validator.validate_locations(input_csv, output_csv, prompts)
    except Exception as e:
        print(f"Error: Failed to validate locations - {e}")
        raise
