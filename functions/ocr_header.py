import os
import csv
import asyncio
from anthropic import Anthropic, RateLimitError, APIError
from PIL import Image, ImageOps, ImageEnhance, UnidentifiedImageError
import base64
from io import BytesIO
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any
from logging_utils import log, log_found, log_progress

@dataclass
class TranscriptionResult:
    tray_id: str
    content: Dict[str, str]
    error: Optional[str] = None

    def to_dict(self):
        return {
            'tray_id': self.tray_id,
            **self.content,
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
    
    def load_processed_files(self, csv_path: str) -> None:
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
            log(f"Failed to load processed files: {e}")

    def find_images(self, folder_path: str, suffix: str) -> List[str]:
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
        
        return image_files

    def extract_tray_id(self, filepath: str, suffix: str) -> str:
        try:
            filename = os.path.basename(filepath)
            # Remove the suffix (_barcode.jpg or _label.jpg)
            tray_id = filename.replace('_barcode.jpg', '').replace('_label.jpg', '')
            return tray_id
        except Exception as e:
            log(f"Failed to extract tray ID: {e}")
            return "unknown_tray"

    async def encode_image(self, image_path: str) -> str:
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
    
    async def process_single_image(self, filepath: str, config: TranscriptionConfig, prompts: dict, current: int, total: int) -> TranscriptionResult:
        tray_id = self.extract_tray_id(filepath, config.file_suffix)
        filename = os.path.basename(filepath)
    
        try:
            base64_image = await self.encode_image(filepath)
    
            log_progress("transcribe_" + config.file_suffix.replace("_", "").replace(".jpg", ""), 
                         current, total, f"Processing {filename}")
    
            response = await self.api_call_with_retry(
                model="claude-3-5-sonnet-20241022",
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
                content=content
            )
    
        except Exception as e:
            error_msg = f"Error: {os.path.basename(filepath)} - {str(e)}"
            log(error_msg)
            return TranscriptionResult(
                tray_id=tray_id,
                content={
                    'tray_id': tray_id,
                    **{field: "ERROR" for field in config.csv_fields if field != 'tray_id'}
                },
                error=error_msg
            )

    def write_results(self, result: TranscriptionResult, output_csv: str, fields: List[str]):
        file_exists = os.path.exists(output_csv)
        
        with open(output_csv, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            if not file_exists:
                writer.writeheader()
            writer.writerow({field: result.content.get(field, '') for field in fields})

    async def process_images(self, folder_path: str, output_csv: str, config: TranscriptionConfig, prompts: dict) -> Tuple[List[TranscriptionResult], int]:
        self.load_processed_files(output_csv)
        image_files = self.find_images(folder_path, config.file_suffix)
        total_images = len(image_files)
        
        if not total_images:
            log(f"No {config.file_suffix} images found to process")
            return [], 0
            
        log_found(f"{config.file_suffix} images", total_images)
        
        # Filter out already processed files
        unprocessed_files = [
            filepath for filepath in image_files 
            if os.path.basename(filepath) not in self.processed_files
        ]
        
        if len(unprocessed_files) < total_images:
            log(f"Found {total_images - len(unprocessed_files)} previously processed images")
        
        if not unprocessed_files:
            log("All images already processed")
            return [], 0
            
        results = []
        processed = 0
        skipped = total_images - len(unprocessed_files)
        errors = 0
        
        for i, filepath in enumerate(unprocessed_files, 1):            
            try:
                result = await self.process_single_image(filepath, config, prompts, i, len(unprocessed_files))
                results.append(result)

                if not result.error:
                    self.processed_files.add(os.path.basename(filepath))
                    processed += 1
                else:
                    errors += 1

                self.write_results(result, output_csv, config.csv_fields)

            except Exception as e:
                log(f"Error: {os.path.basename(filepath)} - {e}")
                errors += 1

        log(f"Complete. {processed} processed, {skipped} skipped, {errors} errors")
        return results, processed

async def process_image_folder(folder_path: str, output_csv: str, api_key: str, prompts: dict) -> Tuple[List[TranscriptionResult], int]:
    try:
        # Determine the type of processing based on the output CSV filename
        if 'barcode' in output_csv:
            config = TranscriptionConfig(
                file_suffix='_barcode.jpg',
                csv_fields=['tray_id', 'unit_barcode'],
                validation_func=lambda x: {'unit_barcode': 'no_barcode' if x.lower() == 'none' else x}
            )
        else:  # Taxonomy
            config = TranscriptionConfig(
                file_suffix='_label.jpg',
                csv_fields=['tray_id', 'full_transcription', 'taxonomy', 'authority']
            )
            
        processor = ImageTranscriber(api_key)
        return await processor.process_images(folder_path, output_csv, config, prompts)
    except Exception as e:
        log(f"Failed to process folder: {e}")
        raise