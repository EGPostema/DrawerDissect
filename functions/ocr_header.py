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
    system_prompt: str
    user_prompt: str
    csv_fields: List[str]
    validation_func: Optional[callable] = None


class ImageTranscriber:
    def __init__(self, api_key: str, max_retries: int = 7, retry_delay: float = 5.0):
        self.client = Anthropic(api_key=api_key)
        self.SONNET_RATE = 0.00025
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.semaphore = asyncio.Semaphore(1)
        self.processed_files = set()
        
        # Suppress verbose logs from external libraries
        logging.getLogger('anthropic').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('httpcore').setLevel(logging.WARNING)

        # Setup basic logging for our application
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
    
    def load_processed_files(self, csv_path: str) -> None:
        """Load list of already processed files from existing CSV."""
        if not os.path.exists(csv_path):
            return
            
        try:
            with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # For barcode files
                    if 'unit_barcode' in row and row['unit_barcode'] != 'ERROR':
                        self.processed_files.add(f"{row['tray_id']}_barcode.jpg")
                    # For label files
                    if 'full_transcription' in row and row['full_transcription'] != 'ERROR':
                        self.processed_files.add(f"{row['tray_id']}_label.jpg")
            
            self.logger.info(f"Loaded {len(self.processed_files)} previously processed files")
        except Exception as e:
            self.logger.warning(f"Error loading processed files from CSV: {e}")

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
        
        if not image_files:
            self.logger.warning(f"No images with suffix {suffix} found in {folder_path}")
        
        return sorted(image_files)

    def extract_tray_id(self, filepath: str, suffix: str) -> str:
        try:
            filename = os.path.basename(filepath)
            if '_tray_' in filename:
                # Split on either '_barcode.jpg' or '_label.jpg'
                parts = filename.replace('_barcode.jpg', '').replace('_label.jpg', '')
                return parts
            return "unknown_tray"
        except Exception as e:
            self.logger.error(f"Error extracting tray ID from {filepath}: {str(e)}")
            return "unknown_tray"

    async def encode_image(self, image_path: str) -> str:
        try:
            with Image.open(image_path) as img:
                # Auto-rotate based on EXIF data
                img = ImageOps.exif_transpose(img)
    
                # Convert to grayscale
                img = img.convert('L')
                
                # Enhance contrast
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(2.0)  # Increase contrast
                
                # Enhance brightness slightly
                brightness = ImageEnhance.Brightness(img)
                img = brightness.enhance(1.2)  # Slight brightness increase
    
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
            except Exception as e:
                self.logger.error(f"Unexpected error in API call: {str(e)}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
    
    async def process_single_image(self, filepath: str, config: TranscriptionConfig) -> TranscriptionResult:
        start_time = asyncio.get_event_loop().time()
        tray_id = self.extract_tray_id(filepath, config.file_suffix)
    
        try:
            base64_image = await self.encode_image(filepath)
    
            response = await self.api_call_with_retry(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                system=config.system_prompt,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": config.user_prompt
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
    
            # Get raw response and clean up any style tags
            raw_content = response.content[0].text.strip()
            content = raw_content.replace('<userStyle>Normal</userStyle>', '').strip()
            
            # For barcode processing
            if config.file_suffix == '_barcode.jpg':
                if config.validation_func:
                    content = config.validation_func(content)
                content = {
                    'tray_id': tray_id,
                    **content  # This will add the unit_barcode field
                }
    
            # For label processing
            if config.file_suffix == '_label.jpg':
                try:
                    import ast
                    content = ast.literal_eval(content)
                    content = {
                        'tray_id': tray_id,
                        **content  # This adds full_transcription, taxonomy, and authority
                    }
                except:
                    content = {
                        'tray_id': tray_id,
                        'full_transcription': 'ERROR',
                        'taxonomy': 'ERROR',
                        'authority': 'ERROR'
                    }
    
            processing_time = asyncio.get_event_loop().time() - start_time
            return TranscriptionResult(
                tray_id=tray_id,
                content=content,
                processing_time=processing_time
            )
    
        except Exception as e:
            error_msg = f"Error processing {filepath}: {str(e)}"
            self.logger.error(error_msg)
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

    async def process_images(self, folder_path: str, output_csv: str, config: TranscriptionConfig) -> Tuple[List[TranscriptionResult], int]:
        # Load already processed files at start
        self.load_processed_files(output_csv)
        
        image_files = self.find_images(folder_path, config.file_suffix)
        total_images = len(image_files)
        results = []
        skipped = 0
        
        for i, filepath in enumerate(image_files, 1):
            filename = os.path.basename(filepath)
            
            # Skip if already processed
            if filename in self.processed_files:
                self.logger.info(f"Skipping already processed image {i}/{total_images}: {filename}")
                skipped += 1
                continue
                
            self.logger.info(f"Processing image {i}/{total_images}: {filepath}")
            
            try:
                result = await self.process_single_image(filepath, config)
                results.append(result)

                if not result.error:
                    self.logger.info(
                        f"Image processed in {result.processing_time:.2f}s | "
                        f"Tray: {result.tray_id}"
                    )
                    self.processed_files.add(filename)  # Add to processed set after successful processing
                else:
                    self.logger.error(f"Failed to process {filepath}: {result.error}")

                self.write_results(result, output_csv, config.csv_fields)

            except Exception as e:
                self.logger.error(f"Unexpected error processing {filepath}: {str(e)}")
                results.append(TranscriptionResult(
                    tray_id=self.extract_tray_id(filepath, config.file_suffix),
                    content={field: "ERROR" for field in config.csv_fields if field != 'tray_id'},
                    error=str(e)
                ))

        successful = len([r for r in results if not r.error])
        self.logger.info(f"Processing complete. Successfully processed {successful}/{total_images} images")
        self.logger.info(f"Processed {len(results)} new images, skipped {skipped} previously processed images")
        return results, successful

# Example configs (you can modify the prompts as needed)
BARCODE_CONFIG = TranscriptionConfig(
    file_suffix='_barcode.jpg',
    system_prompt="You are a barcode reading tool. You should output only the number (or letter-number string) found in the image. If no valid barcode is found, output 'none'.",
    user_prompt="Read the barcode number. Output only the number, no explanations.",
    csv_fields=['tray_id', 'unit_barcode'],
    validation_func=lambda x: {'unit_barcode': 'no_barcode' if x.lower() == 'none' else x}
)

LABEL_CONFIG = TranscriptionConfig(
    file_suffix='_label.jpg',
    system_prompt="""You are a taxonomic label transcription tool specializing in natural history specimens. Your task is to:
1. Provide a complete transcription of the entire label
2. Extract the taxonomic name, including any genus, subgenus, species, and subspecies information
3. Extract the taxonomic authority (author and year)

For missing elements, output 'none'. Format your response as a structured dictionary with these three keys:
{
'full_transcription': 'complete text as shown',
'taxonomy': 'only taxonomic name (Genus (Subgenus) species subspecies)', 
'authority': 'author, year'
}""",
    user_prompt="Transcribe this taxonomic label, preserving the exact text and extracting the taxonomic name and authority. Output only the dictionary, no explanations.",
    csv_fields=['tray_id', 'full_transcription', 'taxonomy', 'authority']
)


async def process_images(folder_path: str, output_csv: str, api_key: str, config: TranscriptionConfig) -> Tuple[List[TranscriptionResult], int]:
    """
    Wrapper function to process a folder of images using Claude.
    
    Args:
        folder_path: Path to folder containing images
        output_csv: Path to output CSV file
        api_key: Anthropic API key
        config: TranscriptionConfig object specifying processing parameters
    
    Returns:
        Tuple containing list of TranscriptionResult objects and count of successful reads
    """
    try:
        processor = ImageTranscriber(api_key)
        return await processor.process_images(folder_path, output_csv, config)
    except Exception as e:
        logging.error(f"Failed to process images: {str(e)}")
        raise
