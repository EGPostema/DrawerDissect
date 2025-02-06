import os
import csv
import logging
import asyncio
from anthropic import Anthropic, RateLimitError, APIError
from PIL import Image, ImageOps, UnidentifiedImageError
import base64
from io import BytesIO
from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple, Optional


@dataclass
class ProcessingResult:
    filename: str
    transcription: str
    location: str
    transcription_tokens: int = 0
    location_tokens: int = 0
    processing_time: float = 0
    error: Optional[str] = None

    def to_dict(self):
        return {
            field: getattr(self, field) 
            for field in self.__dataclass_fields__
        }


class ImageProcessor:
    def __init__(self, api_key: str, max_retries: int = 7, retry_delay: float = 5.0):
        self.client = Anthropic(api_key=api_key)
        self.SONNET_RATE = 0.00025
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.semaphore = asyncio.Semaphore(1)
        self.processed_files = set()
        
        # Suppress external logging
        logging.getLogger('anthropic').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('httpcore').setLevel(logging.WARNING)

    def load_processed_files(self, csv_path: str) -> None:
        """Load list of already processed files from existing CSV."""
        if not os.path.exists(csv_path):
            return
            
        try:
            with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['error'] is None or row['error'] == '':
                        self.processed_files.add(row['filename'])
        except Exception as e:
            print(f"Error loading processed files: {e}")
        
    def find_images(self, folder_path: str) -> List[str]:
        """Find all image files in folder and subfolders."""
        if not os.path.exists(folder_path):
            raise ValueError(f"Folder path does not exist: {folder_path}")
            
        image_files = []
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.tif', '.tiff')):
                    full_path = os.path.join(root, file)
                    image_files.append(full_path)
        
        if not image_files:
            print(f"No image files found in {folder_path}")
        
        return image_files

    async def encode_image(self, image_path: str) -> str:
        """Encode and optimize image for API transmission."""
        try:
            with Image.open(image_path) as img:
                img = ImageOps.exif_transpose(img)
                if img.mode == 'RGBA':
                    img = img.convert('RGB')

                if max(img.size) > 1024:
                    ratio = 1024 / max(img.size)
                    img = img.resize(
                        (int(img.size[0] * ratio), int(img.size[1] * ratio)),
                        Image.Resampling.LANCZOS
                    )

                buffered = BytesIO()
                img.save(buffered, format='JPEG', quality=85, optimize=True)
                return base64.b64encode(buffered.getvalue()).decode('utf-8')
                
        except UnidentifiedImageError:
            raise ValueError(f"Could not identify image file: {image_path}")
        except Exception as e:
            raise ValueError(f"Error processing image {image_path}: {str(e)}")

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

    async def process_single_image(self, filepath: str, prompts: dict) -> ProcessingResult:
        """Process a single image through Claude API for transcription and location."""
        start_time = asyncio.get_event_loop().time()
        filename = os.path.basename(filepath)

        try:
            base64_image = await self.encode_image(filepath)

            transcription_response = await self.api_call_with_retry(
                model="claude-3-5-sonnet",
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
            transcription_tokens = transcription_response.usage.output_tokens

            if transcription.lower() == "no text found":
                return ProcessingResult(
                    filename=filename,
                    transcription=transcription,
                    location="no location found",
                    transcription_tokens=transcription_tokens,
                    location_tokens=0,
                    processing_time=asyncio.get_event_loop().time() - start_time
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
            location_tokens = location_response.usage.output_tokens

            return ProcessingResult(
                filename=filename,
                transcription=transcription,
                location=location,
                transcription_tokens=transcription_tokens,
                location_tokens=location_tokens,
                processing_time=asyncio.get_event_loop().time() - start_time
            )

        except Exception as e:
            error_msg = f"Error processing {filepath}: {str(e)}"
            print(error_msg)
            return ProcessingResult(
                filename=filename,
                transcription="ERROR",
                location="ERROR",
                error=error_msg
            )

    def write_results(self, result: ProcessingResult, output_csv: str):
        """Write processing results to CSV file."""
        file_exists = os.path.exists(output_csv)
        
        with open(output_csv, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'filename', 'transcription', 'location',
                'transcription_tokens', 'location_tokens',
                'processing_time', 'error'
            ])
            if not file_exists:
                writer.writeheader()
            writer.writerow(result.to_dict())

    async def transcribe_images(self, folder_path: str, output_csv: str, prompts: dict) -> Tuple[List[ProcessingResult], float]:
        """Process all images in a folder through Claude API."""
        self.load_processed_files(output_csv)
        image_files = self.find_images(folder_path)
        total_images = len(image_files)
        results = []
        skipped = 0
        total_cost = 0

        print(f"\nProcessing {total_images} images...")
        
        for i, filepath in enumerate(image_files, 1):
            filename = os.path.basename(filepath)
            
            if filename in self.processed_files:
                skipped += 1
                continue
                
            print(f"Image {i}/{total_images}", end='\r')
            
            try:
                result = await self.process_single_image(filepath, prompts)
                results.append(result)

                if not result.error:
                    total_cost += (result.transcription_tokens + result.location_tokens) * self.SONNET_RATE
                    self.processed_files.add(filename)
                else:
                    print(f"\nError processing {filename}: {result.error}")

                self.write_results(result, output_csv)

            except Exception as e:
                print(f"\nUnexpected error processing {filename}: {e}")
                results.append(ProcessingResult(
                    filename=filename,
                    transcription="ERROR",
                    location="ERROR",
                    error=str(e)
                ))

        successful = len([r for r in results if not r.error])
        print(f"\nComplete: {successful} processed, {skipped} skipped (${total_cost:.2f})")
        return results, total_cost


async def process_specimen_labels(folder_path: str, output_csv: str, api_key: str, prompts: dict) -> Tuple[List[ProcessingResult], float]:
    """
    Process a folder of specimen label images using Claude API.
    
    Args:
        folder_path: Path to folder containing images
        output_csv: Path to output CSV file
        api_key: Anthropic API key
        prompts: Dictionary containing system and user prompts for transcription and location
    
    Returns:
        Tuple containing list of ProcessingResult objects and total cost
    """
    try:
        processor = ImageProcessor(api_key)
        return await processor.transcribe_images(folder_path, output_csv, prompts)
    except Exception as e:
        print(f"Failed to process images: {e}")
        raise

