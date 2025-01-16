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

class LocationValidator:
    def __init__(self, api_key: str, max_retries: int = 7, retry_delay: float = 5.0):
        self.client = Anthropic(api_key=api_key)
        self.SONNET_RATE = 0.00025
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.semaphore = asyncio.Semaphore(1)
        
        # Suppress verbose logs from external libraries
        logging.getLogger('anthropic').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)
        
        # Setup basic logging for our application
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

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
            except Exception as e:
                self.logger.error(f"Unexpected error in API call: {str(e)}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(self.retry_delay * (2 ** attempt))

    async def validate_single_entry(self, filename: str, transcription: str, location: str) -> ValidationResult:
        start_time = asyncio.get_event_loop().time()
        
        try:
            response = await self.api_call_with_retry(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                system=VALIDATION_PROMPT,
                messages=[{
                    "role": "user",
                    "content": f"Validate this location data:\nTranscribed text: {transcription}\nProposed location: {location}"
                }]
            )

            try:
                import ast
                content = ast.literal_eval(response.content[0].text.strip())
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
            self.logger.error(error_msg)
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
                     'processing_time', 'error']
        
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for result in results:
                writer.writerow(vars(result))

    async def validate_locations(self, input_csv: str, output_csv: str) -> Tuple[List[ValidationResult], int]:
        results = []
        successful = 0
        total_cost = 0
        
        with open(input_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            for i, row in enumerate(rows, 1):
                self.logger.info(f"Validating entry {i}/{len(rows)}: {row['filename']}")
                
                # Count input tokens (rough estimation)
                input_tokens = len(f"Validate this location data:\nTranscribed text: {row['transcription']}\nProposed location: {row['location']}".split())
                
                result = await self.validate_single_entry(
                    row['filename'],
                    row['transcription'],
                    row['location']
                )
                
                # Count output tokens (rough estimation)
                output_tokens = len(str(result.__dict__).split())
                
                # Calculate approximate cost
                cost = (input_tokens * 0.03 / 1000) + (output_tokens * 0.06 / 1000)
                total_cost += cost
                
                results.append(result)
                if not result.error and result.validation_status != 'ERROR':
                    successful += 1
                    self.logger.info(
                        f"Validated in {result.processing_time:.2f}s | "
                        f"Status: {result.validation_status} | "
                        f"Estimated cost: ${cost:.4f}"
                    )
                else:
                    self.logger.error(f"Failed to validate {row['filename']}: {result.error}")
    
            self.write_results(results, output_csv)
            self.logger.info(f"Validation complete. Successfully validated {successful}/{len(rows)} entries")
            self.logger.info(f"Total estimated cost: ${total_cost:.4f} (${total_cost/len(rows):.4f} per row)")
            return results, successful

VALIDATION_PROMPT = """You are a geographic data validator specializing in museum specimen labels. Your task is to:
1. Examine the transcribed text and interpreted location for consistency
2. Make a final location determination considering:
   - The verbatim transcribed text
   - The proposed location interpretation
   - Your knowledge of geographic conventions in natural history collections
   - Historical place names and abbreviations
   - Locations derived from 'Field Museum' or 'FMNH' or 'Chicago Field Museum' are INVALID, as this is where the specimens are housed

Respond in this format:
{
'verbatim_text': 'exact text as transcribed',
'proposed_location': 'location as interpreted',
'validation_status': 'VALID/UNCERTAIN/INVALID/INSUFFICIENT',
'final_location': 'your final location determination, 'UNKNOWN' if unknown/missing/invalid',
'confidence_notes': 'brief explanation of your reasoning'
}

Consider:
- State/country abbreviations (e.g., IL = Illinois)
- Common collector shorthand (e.g., 'Co.' = County)
- Historical place names
- Level of certainty needed for scientific records"""

async def validate_transcriptions(input_csv: str, output_csv: str, api_key: str) -> Tuple[List[ValidationResult], int]:
    """
    Wrapper function to validate location interpretations using Claude.
    
    Args:
        input_csv: Path to input CSV with transcriptions and locations
        output_csv: Path to output CSV for validation results
        api_key: Anthropic API key
    
    Returns:
        Tuple containing list of ValidationResult objects and count of successful validations
    """
    try:
        validator = LocationValidator(api_key)
        return await validator.validate_locations(input_csv, output_csv)
    except Exception as e:
        logging.error(f"Failed to validate locations: {str(e)}")
        raise
