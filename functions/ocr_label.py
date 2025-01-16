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
        
        # Suppress verbose logs from external libraries
        logging.getLogger('anthropic').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)
        
        # Setup basic logging for our application
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def find_images(self, folder_path: str) -> List[str]:
        if not os.path.exists(folder_path):
            raise ValueError(f"Folder path does not exist: {folder_path}")
            
        image_files = []
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    full_path = os.path.join(root, file)
                    image_files.append(full_path)
        
        if not image_files:
            self.logger.warning(f"No image files found in {folder_path}")
        
        return image_files

    async def encode_image(self, image_path: str) -> str:
        try:
            with Image.open(image_path) as img:
                # Auto-rotate based on EXIF data
                img = ImageOps.exif_transpose(img)

                # Convert RGBA to RGB if necessary
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
        for attempt in range(self.max_retries):
            try:
                async with self.semaphore:
                    # Run the API call synchronously in a thread pool
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
                if e.status_code < 500:  # Don't retry client errors
                    raise
                await asyncio.sleep(self.retry_delay * (2 ** attempt))

    async def process_single_image(self, filepath: str) -> ProcessingResult:
        start_time = asyncio.get_event_loop().time()
        filename = os.path.basename(filepath)

        try:
            base64_image = await self.encode_image(filepath)

            transcription_response = await self.api_call_with_retry(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                system="You are a label transcription tool. You may encounter fragmented or handwritten text. Output text only, no descriptions or commentary.",
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Transcribe any visible text. Output 'no text found' if none visible. Transcribe text verbatim. No explanations, descriptions, or commentary."
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
                system="You are a geographic data extractor, reconstructing locations from fragments of text. Output locations only, no explanations.",
                messages=[{
                    "role": "user",
                    "content": f"Extract geographic location from this text: {transcription}. Format: largest to smallest unit, comma-separated. Output 'no location found' if none present. No explanations or notes."
                }]
            )
            
            location = location_response.content[0].text.strip()
            location_tokens = location_response.usage.output_tokens

            processing_time = asyncio.get_event_loop().time() - start_time
            return ProcessingResult(
                filename=filename,
                transcription=transcription,
                location=location,
                transcription_tokens=transcription_tokens,
                location_tokens=location_tokens,
                processing_time=processing_time
            )

        except Exception as e:
            error_msg = f"Error processing {filepath}: {str(e)}"
            self.logger.error(error_msg)
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
                'transcription_tokens', 'location_tokens',
                'processing_time', 'error'
            ])
            if not file_exists:  # Write header only if file is new
                writer.writeheader()
            writer.writerow(result.to_dict())

    async def transcribe_images(self, folder_path: str, output_csv: str) -> Tuple[List[ProcessingResult], float]:
        image_files = self.find_images(folder_path)
        total_images = len(image_files)
        results = []
        total_cost = 0

        for i, filepath in enumerate(image_files, 1):
            self.logger.info(f"Processing image {i}/{total_images}: {filepath}")
            
            try:
                result = await self.process_single_image(filepath)
                results.append(result)

                if not result.error:
                    total_cost += (result.transcription_tokens + result.location_tokens) * self.SONNET_RATE
                    self.logger.info(
                        f"Image processed in {result.processing_time:.2f}s | "
                        f"Tokens: {result.transcription_tokens + result.location_tokens} | "
                        f"Cost: ${(result.transcription_tokens + result.location_tokens) * self.SONNET_RATE:.3f}"
                    )
                else:
                    self.logger.error(f"Failed to process {filepath}: {result.error}")

                self.write_results(result, output_csv)

            except Exception as e:
                self.logger.error(f"Unexpected error processing {filepath}: {str(e)}")
                results.append(ProcessingResult(
                    filename=os.path.basename(filepath),
                    transcription="ERROR",
                    location="ERROR",
                    error=str(e)
                ))

        self.logger.info(f"Processing complete. Total cost: ${total_cost:.2f}")
        return results, total_cost


async def transcribe_images(folder_path: str, output_csv: str, api_key: str) -> Tuple[List[ProcessingResult], float]:
    """
    Wrapper function to process a folder of images and transcribe text using Claude.
    
    Args:
        folder_path: Path to folder containing images
        output_csv: Path to output CSV file
        api_key: Anthropic API key
    
    Returns:
        Tuple containing list of ProcessingResult objects and total cost
    """
    try:
        processor = ImageProcessor(api_key)
        return await processor.transcribe_images(folder_path, output_csv)
    except Exception as e:
        logging.error(f"Failed to process images: {str(e)}")
        raise


