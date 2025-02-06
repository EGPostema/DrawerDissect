import os
import csv
import logging
import asyncio
from anthropic import Anthropic, RateLimitError, APIError
from PIL import Image, ImageOps, ImageEnhance, UnidentifiedImageError
import base64
from io import BytesIO
from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple, Optional, Dict


@dataclass
class TranscriptionResult:
    tray_id: str
    content: Dict[str, str]
    processing_time: float = 0
    error: Optional[str] = None

    def to_dict(self):
        return {
            'tray_id': self.tray_id,
            **self.content,
            'processing_time': self.processing_time,
            'error': self.error
        }


@dataclass
class TranscriptionConfig:
    file_suffix: str
    csv_fields: List[str]
    validation_func: Optional[callable] = None


class ImageTranscriber:
    def __init__(self, api_key: str, max_retries: int = 7, retry_delay: float = 5.0):
        self.client = Anthropic(api_key=api_key)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.semaphore = asyncio.Semaphore(1)
        self.processed_files = set()
        
        # Suppress all external logging
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
                    if 'unit_barcode' in row and row['unit_barcode'] != 'ERROR':
                        self.processed_files.add(f"{row['tray_id']}_barcode.jpg")
                    if 'full_transcription' in row and row['full_transcription'] != 'ERROR':
                        self.processed_files.add(f"{row['tray_id']}_label.jpg")
        except Exception as e:
            print(f"Error loading processed files: {e}")

    def find_images(self, folder_path: str, suffix: str) -> List[str]:
        """Find all images with given suffix in folder and subfolders."""
        if not os.path.exists(folder_path):
            raise ValueError(f"Folder path does not exist: {folder_path}")
            
        image_files = []
        for root, _, files in os.walk(folder_path):
            if 'checkpoint' in root:
                continue
                
            for file in files:
                if 'checkpoint' in file:
                    continue
                    
                if file.endswith(suffix):
                    full_path = os.path.join(root, file)
                    image_files.append(full_path)
        
        if not image_files:
            print(f"No images with suffix {suffix} found in {folder_path}")
        
        return image_files

    def extract_tray_id(self, filepath: str, suffix: str) -> str:
        """Extract tray ID from filename, handling both barcode and label files."""
        try:
            filename = os.path.basename(filepath)
            if '_tray_' in filename:
                parts = filename.split('_tray_')[-1]  # Get everything after 'tray_'
                tray_id = parts.replace('_barcode.jpg', '').replace('_label.jpg', '')
                return tray_id
            return "unknown_tray"
        except Exception as e:
            print(f"Error extracting tray ID from {filepath}: {e}")
            return "unknown_tray"

    async def encode_image(self, image_path: str) -> str:
        """Encode and optimize image for API transmission."""
        try:
            with Image.open(image_path) as img:
                img = ImageOps.exif_transpose(img)
                img = img.convert('L')
                
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(2.0)
                
                brightness = ImageEnhance.Brightness(img)
                img = brightness.enhance(1.2)
    
                if max(img.size) > 1024:
                    ratio = 1024 / max(img.size)
                    img = img.resize(
                        (int(img.size[0] * ratio), int(img.size[1] * ratio)),
                        Image.Resampling.LANCZOS
                    )
    
                buffered = BytesIO()
                img.save(buffered, format='JPEG', quality=95, optimize=True)
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
                if e.status_code < 500:  # Don't retry client errors
                    raise
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
            except Exception as e:
                print(f"Unexpected error in API call: {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
    
    async def process_single_image(self, filepath: str, config: TranscriptionConfig, prompts: dict) -> TranscriptionResult:
        """Process a single image through Claude API and format the response."""
        start_time = asyncio.get_event_loop().time()
        tray_id = self.extract_tray_id(filepath, config.file_suffix)
    
        try:
            base64_image = await self.encode_image(filepath)
    
            response = await self.api_call_with_retry(
                model="claude-3-5-sonnet",
                max_tokens=1000,
                system=prompts['system'],
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompts['user']
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
    
            raw_content = response.content[0].text.strip()
            content = raw_content.replace('<userStyle>Normal</userStyle>', '').strip()
            
            if config.file_suffix == '_barcode.jpg':
                if config.validation_func:
                    content = config.validation_func(content)
                content = {'tray_id': tray_id, **content}
    
            elif config.file_suffix == '_label.jpg':
                try:
                    import ast
                    content = ast.literal_eval(content)
                    content = {'tray_id': tray_id, **content}
                except:
                    content = {
                        'tray_id': tray_id,
                        'full_transcription': 'ERROR',
                        'taxonomy': 'ERROR',
                        'authority': 'ERROR'
                    }
    
            return TranscriptionResult(
                tray_id=tray_id,
                content=content,
                processing_time=asyncio.get_event_loop().time() - start_time
            )
    
        except Exception as e:
            error_msg = f"Error processing {filepath}: {str(e)}"
            print(error_msg)
            return TranscriptionResult(
                tray_id=tray_id,
                content={
                    'tray_id': tray_id,
                    **{field: "ERROR" for field in config.csv_fields if field != 'tray_id'}
                },
                error=error_msg
            )

    def write_results(self, result: TranscriptionResult, output_csv: str, fields: List[str]):
        """Write transcription results to CSV file."""
        file_exists = os.path.exists(output_csv)
        
        with open(output_csv, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            if not file_exists:
                writer.writeheader()
            writer.writerow({field: result.content.get(field, '') for field in fields})

    async def process_images(self, folder_path: str, output_csv: str, config: TranscriptionConfig, prompts: dict) -> Tuple[List[TranscriptionResult], int]:
        """Process all images in a folder through Claude API."""
        self.load_processed_files(output_csv)
        image_files = self.find_images(folder_path, config.file_suffix)
        total_images = len(image_files)
        results = []
        skipped = 0
        
        print(f"\nProcessing {total_images} images...")
        
        for i, filepath in enumerate(image_files, 1):
            filename = os.path.basename(filepath)
            
            if filename in self.processed_files:
                skipped += 1
                continue
                
            print(f"Image {i}/{total_images}", end='\r')
            
            try:
                result = await self.process_single_image(filepath, config, prompts)
                results.append(result)
    
                if not result.error:
                    self.processed_files.add(filename)
                else:
                    print(f"\nError processing {filename}: {result.error}")
    
                self.write_results(result, output_csv, config.csv_fields)
    
            except Exception as e:
                print(f"\nUnexpected error processing {filename}: {e}")
                results.append(TranscriptionResult(
                    tray_id=self.extract_tray_id(filepath, config.file_suffix),
                    content={field: "ERROR" for field in config.csv_fields if field != 'tray_id'},
                    error=str(e)
                ))
    
        successful = len([r for r in results if not r.error])
        print(f"\nComplete: {successful} processed, {skipped} skipped")
        return results, successful


async def process_image_folder(folder_path: str, output_csv: str, api_key: str, prompts: dict) -> Tuple[List[TranscriptionResult], int]:
    """
    Process a folder of images using Claude API.
    
    Args:
        folder_path: Path to folder containing images
        output_csv: Path to output CSV file
        api_key: Anthropic API key
        prompts: Dictionary containing system and user prompts
    
    Returns:
        Tuple containing list of TranscriptionResult objects and count of successful reads
    """
    try:
        processor = ImageTranscriber(api_key)
        config = TranscriptionConfig(
            file_suffix='_barcode.jpg' if 'barcode' in output_csv else '_label.jpg',
            csv_fields=['tray_id', 'unit_barcode'] if 'barcode' in output_csv else ['tray_id', 'full_transcription', 'taxonomy', 'authority'],
            validation_func=lambda x: {'unit_barcode': 'no_barcode' if x.lower() == 'none' else x} if 'barcode' in output_csv else None
        )
        return await processor.process_images(folder_path, output_csv, config, prompts)
    except Exception as e:
        print(f"Failed to process images: {e}")
        raise
