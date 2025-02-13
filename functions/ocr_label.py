import os
import csv
import logging
import asyncio
from anthropic import Anthropic, RateLimitError, APIError
from PIL import Image, ImageOps, UnidentifiedImageError
import base64
from io import BytesIO
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any

@dataclass
class ProcessingResult:
    filename: str
    transcription: str
    location: str
    error: Optional[str] = None
    cached: bool = False

    def to_dict(self):
        return {
            field: getattr(self, field) 
            for field in self.__dataclass_fields__
        }

class ImageProcessor:
    def __init__(self, api_key: str, max_retries: int = 5, retry_delay: float = 3.0):
        self.client = Anthropic(api_key=api_key)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.semaphore = asyncio.Semaphore(5)
        self.processed_files = set()
        self.image_cache: Dict[str, ProcessingResult] = {}
        
        # Suppress external logging
        logging.getLogger('anthropic').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('httpcore').setLevel(logging.WARNING)

    def load_processed_files(self, csv_path: str) -> None:
        if not os.path.exists(csv_path):
            return
            
        try:
            with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not row['error'] or row['error'].lower() == 'none':
                        self.processed_files.add(row['filename'])
        except Exception as e:
            print(f"Error: Failed to load processed files - {e}")
        
    def find_images(self, folder_path: str) -> List[str]:
        if not os.path.exists(folder_path):
            raise ValueError(f"Folder path does not exist: {folder_path}")
            
        image_files = []
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.tif', '.tiff')):
                    full_path = os.path.join(root, file)
                    image_files.append(full_path)
        
        return image_files

    async def encode_image(self, image_path: str, max_size: int = 800) -> str:
        try:
            with Image.open(image_path) as img:
                img = ImageOps.exif_transpose(img)
                
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                
                if max(img.size) > max_size:
                    ratio = max_size / max(img.size)
                    img = img.resize(
                        (int(img.size[0] * ratio), int(img.size[1] * ratio)),
                        Image.Resampling.LANCZOS
                    )

                buffered = BytesIO()
                img.save(buffered, format='JPEG', quality=75, optimize=True)
                return base64.b64encode(buffered.getvalue()).decode('utf-8')
                
        except UnidentifiedImageError:
            raise ValueError(f"Could not identify image file: {image_path}")
        except Exception as e:
            raise ValueError(f"Error processing image {image_path}: {str(e)}")

    async def api_call_with_retry(self, **kwargs) -> dict:
        for attempt in range(self.max_retries):
            try:
                async with self.semaphore:
                    response = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self.client.messages.create(**kwargs)
                    )
                    return response
            except (RateLimitError, APIError) as e:
                if attempt == self.max_retries - 1:
                    raise
                wait_time = self.retry_delay * (2 ** attempt)
                await asyncio.sleep(wait_time)
        
        raise Exception("Max retries exceeded")

    async def process_single_image(self, filepath: str, prompts: dict) -> ProcessingResult:
        filename = os.path.basename(filepath)

        if filepath in self.image_cache:
            return self.image_cache[filepath]

        try:
            base64_image = await self.encode_image(filepath)

            transcription_response = await self.api_call_with_retry(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                system=prompts['transcription']['system'],
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompts['transcription']['user']
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": base64_image
                            }
                        }
                    ]
                }]
            )

            transcription = transcription_response.content[0].text.strip()

            if transcription.lower() == "no text found":
                return ProcessingResult(
                    filename=filename,
                    transcription=transcription,
                    location="no location found"
                )

            location_response = await self.api_call_with_retry(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                system=prompts['location']['system'],
                messages=[{
                    "role": "user",
                    "content": prompts['location']['user'].format(text=transcription)
                }]
            )
            
            location = location_response.content[0].text.strip()

            result = ProcessingResult(
                filename=filename,
                transcription=transcription,
                location=location
            )

            self.image_cache[filepath] = result
            return result

        except Exception as e:
            error_msg = f"Error: {filename} - {str(e)}"
            
            return ProcessingResult(
                filename=filename,
                transcription="ERROR",
                location="ERROR",
                error=error_msg
            )

    def write_results(self, result: ProcessingResult, output_csv: str):
        file_exists = os.path.exists(output_csv)
        
        with open(output_csv, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'filename', 'transcription', 'location',
                'error', 'cached'
            ])
            if not file_exists:
                writer.writeheader()
            writer.writerow(result.to_dict())

    async def transcribe_images(self, folder_path: str, output_csv: str, prompts: dict) -> List[ProcessingResult]:
        self.load_processed_files(output_csv)
        image_files = self.find_images(folder_path)
        total_images = len(image_files)
        
        unprocessed_files = [
            filepath for filepath in image_files 
            if os.path.basename(filepath) not in self.processed_files
        ]
        
        skipped = total_images - len(unprocessed_files)
        print(f"Found {len(unprocessed_files)} images to process")
        
        results = []
        
        batch_size = 10
        for i in range(0, len(unprocessed_files), batch_size):
            batch = unprocessed_files[i:i+batch_size]
            batch_tasks = [
                self.process_single_image(filepath, prompts) 
                for filepath in batch
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, ProcessingResult):
                    if not result.error:
                        self.processed_files.add(result.filename)
                    self.write_results(result, output_csv)
                    results.append(result)
            
            await asyncio.sleep(1)
        
        successful = len([r for r in results if not r.error])
        print(f"\nComplete. Processed: {successful}, Skipped: {skipped}, Errors: {len(results) - successful}")
        
        return results

async def process_specimen_labels(folder_path: str, output_csv: str, api_key: str, prompts: dict) -> List[ProcessingResult]:
    try:
        processor = ImageProcessor(api_key)
        return await processor.transcribe_images(folder_path, output_csv, prompts)
    except Exception as e:
        print(f"Error: Failed to process folder - {e}")
        raise


