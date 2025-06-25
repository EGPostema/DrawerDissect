import os
import csv
import asyncio
from anthropic import Anthropic, RateLimitError, APIError
from PIL import Image, ImageOps, UnidentifiedImageError, ImageEnhance
import base64
from io import BytesIO
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any
from logging_utils import log, log_found, log_progress
import tempfile
import time
import logging

logging.getLogger("httpx").disabled = True
logging.getLogger("anthropic").disabled = True
logging.getLogger("httpcore").disabled = True

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
    def __init__(self, api_key: str, max_retries: int = 5, retry_delay: float = 3.0, 
                 max_size: int = 1000, convert_bw: bool = True, concurrent_api_calls: int = 12):
        self.client = Anthropic(api_key=api_key)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        # Increase concurrent API calls for better throughput
        self.semaphore = asyncio.Semaphore(concurrent_api_calls)
        self.processed_files = set()
        self.image_cache = {}
        self.max_size = max_size
        self.convert_bw = convert_bw
        self.temp_dir = tempfile.mkdtemp(prefix="image_processing_")
        
    def __del__(self):
        """Clean up temporary directory when done"""
        try:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except:
            pass
        
    def load_processed_files(self, csv_path: str) -> None:
        if not os.path.exists(csv_path):
            return
            
        try:
            with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not row.get('error') or row.get('error', '').lower() == 'none':
                        self.processed_files.add(row['filename'])
        except Exception as e:
            log(f"Failed to load processed files: {e}")
        
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

    async def create_optimized_image(self, image_path: str) -> str:
        """
        Creates an optimized version of the input image in a temp directory:
        - Resizes to fit within max_size x max_size square (maintains aspect ratio)
        - Optionally converts to black and white with enhanced contrast
        Returns the path to the temporary file.
        """
        try:
            with Image.open(image_path) as img:
                img = ImageOps.exif_transpose(img)
                
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                
                # Resize to fit within max_size x max_size square while maintaining aspect ratio
                width, height = img.size
                if width > self.max_size or height > self.max_size:
                    ratio = min(self.max_size / width, self.max_size / height)
                    new_width = int(width * ratio)
                    new_height = int(height * ratio)
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Convert to black and white and enhance contrast if enabled
                if self.convert_bw:
                    # Convert to grayscale
                    img = img.convert('L')
                    
                    # Enhance contrast to make text more readable
                    enhancer = ImageEnhance.Contrast(img)
                    img = enhancer.enhance(1.5)  # Increase contrast by 50%
                
                # Create a temporary filename based on original filename
                orig_basename = os.path.basename(image_path)
                temp_filename = f"temp_{orig_basename.split('.')[0]}.jpg"
                temp_path = os.path.join(self.temp_dir, temp_filename)
                
                # Save as JPEG with good quality
                img.save(temp_path, format='JPEG', quality=85, optimize=True)
                
                orig_size = os.path.getsize(image_path)/1024/1024
                new_size = os.path.getsize(temp_path)/1024/1024
                reduction = (1 - new_size/orig_size) * 100 if orig_size > 0 else 0
                
                log(f"Optimized {orig_basename}: {orig_size:.2f}MB → {new_size:.2f}MB ({reduction:.1f}% reduction)")
                
                return temp_path
                
        except UnidentifiedImageError:
            raise ValueError(f"Could not identify image file: {image_path}")
        except Exception as e:
            raise ValueError(f"Error processing image {image_path}: {str(e)}")

    async def encode_image(self, image_path: str) -> str:
        """
        Encodes an image file to base64 string
        """
        try:
            with open(image_path, 'rb') as img_file:
                return base64.b64encode(img_file.read()).decode('utf-8')
        except Exception as e:
            raise ValueError(f"Error encoding image {image_path}: {str(e)}")

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
                
                # Add jitter to prevent all retries happening simultaneously
                jitter = wait_time * 0.1 * (2 * (0.5 - (attempt % 2)))
                total_wait = max(0.1, wait_time + jitter)
                
                log(f"API error ({e.__class__.__name__}). Retrying in {total_wait:.2f}s (attempt {attempt+1}/{self.max_retries})")
                await asyncio.sleep(total_wait)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                wait_time = self.retry_delay * (2 ** attempt)
                await asyncio.sleep(wait_time)
        
        raise Exception("Max retries exceeded")

    async def process_single_image(self, filepath: str, prompts: dict, current: int, total: int) -> ProcessingResult:
        filename = os.path.basename(filepath)

        if filepath in self.image_cache:
            log_progress("transcribe_speclabels", current, total, f"Using cached result for {filename}")
            return self.image_cache[filepath]

        try:
            log_progress("transcribe_speclabels", current, total, f"Processing {filename}")
            
            # Create an optimized version of the image
            temp_image_path = await self.create_optimized_image(filepath)
            
            # Encode the optimized image
            base64_image = await self.encode_image(temp_image_path)

            # Process both transcription and location extraction concurrently if possible
            async def get_transcription():
                return await self.api_call_with_retry(
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

            # First step: Transcribe the image
            transcription_response = await get_transcription()
            transcription = transcription_response.content[0].text.strip()
            transcription = transcription.replace('<userStyle>Normal</userStyle>', '').strip()
            
            # Clean up temporary file
            try:
                os.remove(temp_image_path)
            except:
                pass  # Ignore cleanup errors

            # If no text found, skip location extraction
            if transcription.lower() == "no text found":
                return ProcessingResult(
                    filename=filename,
                    transcription=transcription,
                    location="no location found"
                )

            # Second step: Extract location from transcription
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
            location = location.replace('<userStyle>Normal</userStyle>', '').strip()

            # Create and cache result
            result = ProcessingResult(
                filename=filename,
                transcription=transcription,
                location=location
            )

            self.image_cache[filepath] = result
            return result

        except Exception as e:
            error_msg = f"Error: {filename} - {str(e)}"
            log(error_msg)
            
            return ProcessingResult(
                filename=filename,
                transcription="ERROR",
                location="ERROR",
                error=error_msg
            )

    def write_results(self, results: List[ProcessingResult], output_csv: str):
        """Write multiple results at once to reduce file I/O operations"""
        if not results:
            return
            
        file_exists = os.path.exists(output_csv)
        
        with open(output_csv, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'filename', 'transcription', 'location',
                'error', 'cached'
            ])
            if not file_exists:
                writer.writeheader()
            for result in results:
                writer.writerow(result.to_dict())

    async def transcribe_images(self, folder_path: str, output_csv: str, prompts: dict) -> List[ProcessingResult]:
        start_time = time.time()
        self.load_processed_files(output_csv)
        image_files = self.find_images(folder_path)
        total_images = len(image_files)
        
        if not total_images:
            log("No specimen images found to process")
            return []
            
        log_found("specimen images", total_images)
        
        # Filter out already processed files
        unprocessed_files = [
            filepath for filepath in image_files 
            if os.path.basename(filepath) not in self.processed_files
        ]
        
        skipped = total_images - len(unprocessed_files)
        if skipped > 0:
            log(f"Found {skipped} previously processed images")
        
        if not unprocessed_files:
            log("All images already processed")
            return []
        
        log(f"Processing {len(unprocessed_files)} images...")
        
        results = []
        processed = 0
        errors = 0
        
        # Process in larger batches with improved concurrency
        batch_size = 20  # Increased from 10
        pending_writes = []
        
        for i in range(0, len(unprocessed_files), batch_size):
            batch = unprocessed_files[i:i+batch_size]
            
            # Process batch in parallel
            batch_tasks = []
            for j, filepath in enumerate(batch, 1):
                task = self.process_single_image(
                    filepath, 
                    prompts, 
                    i + j,  # Adjust for overall progress 
                    len(unprocessed_files)
                )
                batch_tasks.append(task)
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Process results
            batch_to_write = []
            for filepath, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    log(f"Error processing {os.path.basename(filepath)}: {str(result)}")
                    errors += 1
                    continue
                    
                results.append(result)
                batch_to_write.append(result)
                
                if not result.error:
                    self.processed_files.add(result.filename)
                    processed += 1
                else:
                    errors += 1
            
            # Write batch of results at once
            self.write_results(batch_to_write, output_csv)
            
            # Report progress
            elapsed = time.time() - start_time
            images_per_sec = (processed + errors) / elapsed if elapsed > 0 else 0
            percent_done = (processed + errors) / len(unprocessed_files) * 100
            
            log(f"Progress: {processed + errors}/{len(unprocessed_files)} ({percent_done:.1f}%) - " +
                f"{images_per_sec:.2f} images/sec - ETA: {(len(unprocessed_files) - processed - errors) / max(0.1, images_per_sec):.1f}s")
            
            # Small pause between batches to avoid rate limits
            await asyncio.sleep(0.5)

async def process_specimen_labels(folder_path: str, output_csv: str, api_key: str, prompts: dict) -> List[ProcessingResult]:
    try:
        # Initialize with improved settings
        processor = ImageProcessor(
            api_key, 
            max_size=1000,           # Max dimension of 1000px
            convert_bw=True,         # Black and white for better text visibility
            concurrent_api_calls=12  # Increased concurrency for better throughput
        )
        return await processor.transcribe_images(folder_path, output_csv, prompts)
    except Exception as e:
        log(f"Failed to process folder: {e}")
        raise

