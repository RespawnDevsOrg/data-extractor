#!/usr/bin/env python3
"""
Marathi Voter List OCR Scanner
Extracts voter information from Marathi PDF files and exports to Excel
With incremental saving to prevent data loss
Optimized with batch processing and threading
"""

import re
import sys
import gc
import threading
import logging
from pathlib import Path
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import numpy as np
from datetime import datetime
import openpyxl
from openpyxl import Workbook

# Configure logger for this module - will use the same handlers as app.py
logger = logging.getLogger(__name__)

# Create a print function that logs to both console and file
def log_print(message, level='INFO'):
    """Print to console and log to file"""
    # Also print without timestamp for backward compatibility with existing UI
    print(message)
    # Log with timestamp to file
    if level == 'INFO':
        logger.info(message)
    elif level == 'WARNING':
        logger.warning(message)
    elif level == 'ERROR':
        logger.error(message)
    elif level == 'DEBUG':
        logger.debug(message)


class VoterListOCR:
    """Main class for processing Marathi voter list PDFs with optimized batch processing"""

    def __init__(self, pdf_path: str, output_path: Optional[str] = None,
                 matadaar_sangh: str = '', election_type: str = '', ward_number: str = ''):
        """
        Initialize the OCR processor

        Args:
            pdf_path: Path to the PDF file to process
            output_path: Path for output Excel file
            matadaar_sangh: Matadar Sangh value (user input)
            election_type: Election Type value (user input)
            ward_number: Ward Number value (user input)
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # Set output path
        if output_path:
            self.output_path = Path(output_path)
        else:
            self.output_path = Path(self.pdf_path.stem + '_voters.xlsx')

        self.voters_data = []
        self.total_records_saved = 0

        # Store user configuration
        self.matadaar_sangh = matadaar_sangh
        self.election_type = election_type
        self.ward_number = ward_number

        # Statistics tracking
        self.total_patterns_found = 0
        self.total_valid_ids = 0
        self.total_rejected_ids = 0
        self.all_sr_numbers = []  # Track all extracted Sr. No. for sequence validation

        # Dynamic batch sizing with advanced memory management
        self.initial_batch_size = 6  # Start with larger batch size
        self.min_batch_size = 2     # Minimum batch size
        self.max_batch_size = 10    # Maximum batch size
        self.current_batch_size = self.initial_batch_size
        self.max_workers = min(3, (threading.active_count() or 1) + 2)
        self.lock = threading.Lock()  # For thread-safe Excel writing
        
        # Advanced memory monitoring
        self._memory_threshold_low = 400 * 1024 * 1024   # 400MB - reduce batch size
        self._memory_threshold_high = 600 * 1024 * 1024  # 600MB - force cleanup
        self._memory_threshold_critical = 800 * 1024 * 1024  # 800MB - emergency cleanup
        self._batch_performance_history = []  # Track batch performance
        self._memory_usage_history = []       # Track memory usage

        # Devanagari to English number mapping
        self.devanagari_to_english = {
            '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
            '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'
        }

    def _get_memory_usage_mb(self):
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0  # Can't measure without psutil

    def _check_memory_usage(self):
        """Advanced memory monitoring with dynamic response"""
        memory_mb = self._get_memory_usage_mb()
        self._memory_usage_history.append(memory_mb)
        
        # Keep only last 10 measurements
        if len(self._memory_usage_history) > 10:
            self._memory_usage_history.pop(0)
        
        if memory_mb > self._memory_threshold_critical:
            print(f"🚨 CRITICAL memory usage: {memory_mb:.1f}MB - emergency cleanup")
            gc.collect()
            # Reduce batch size aggressively
            self.current_batch_size = max(1, self.current_batch_size // 2)
            return True
        elif memory_mb > self._memory_threshold_high:
            print(f"⚠ High memory usage: {memory_mb:.1f}MB - forcing cleanup")
            gc.collect()
            # Reduce batch size moderately
            self.current_batch_size = max(self.min_batch_size, self.current_batch_size - 1)
            return True
        elif memory_mb > self._memory_threshold_low:
            print(f"📊 Moderate memory usage: {memory_mb:.1f}MB - reducing batch size")
            # Reduce batch size slightly
            self.current_batch_size = max(self.min_batch_size, self.current_batch_size - 1)
            gc.collect()
            return False
        else:
            # Memory usage is low, can potentially increase batch size
            if len(self._memory_usage_history) >= 3:
                avg_memory = sum(self._memory_usage_history[-3:]) / 3
                if avg_memory < self._memory_threshold_low * 0.7:  # Well below threshold
                    self.current_batch_size = min(self.max_batch_size, self.current_batch_size + 1)
                    print(f"📈 Low memory usage: {memory_mb:.1f}MB - increasing batch size to {self.current_batch_size}")
            return False

    def _optimize_batch_size_based_on_performance(self, batch_time, batch_size):
        """Dynamically optimize batch size based on performance metrics"""
        performance_metric = batch_size / batch_time  # pages per second
        self._batch_performance_history.append({
            'batch_size': batch_size,
            'time': batch_time,
            'performance': performance_metric,
            'memory': self._get_memory_usage_mb()
        })
        
        # Keep only last 5 measurements
        if len(self._batch_performance_history) > 5:
            self._batch_performance_history.pop(0)
        
        # Analyze performance trend
        if len(self._batch_performance_history) >= 3:
            recent_performance = [p['performance'] for p in self._batch_performance_history[-3:]]
            recent_memory = [p['memory'] for p in self._batch_performance_history[-3:]]
            
            avg_performance = sum(recent_performance) / len(recent_performance)
            avg_memory = sum(recent_memory) / len(recent_memory)
            
            # If performance is good and memory is reasonable, try increasing batch size
            if (avg_performance > 1.0 and  # Good performance (>1 page/sec)
                avg_memory < self._memory_threshold_low and  # Low memory usage
                self.current_batch_size < self.max_batch_size):
                self.current_batch_size = min(self.max_batch_size, self.current_batch_size + 1)
                print(f"🚀 Performance optimization: increasing batch size to {self.current_batch_size}")

    def convert_marathi_numbers_to_english(self, text: str) -> str:
        """Convert Marathi/Devanagari numerals to English numerals"""
        for dev, eng in self.devanagari_to_english.items():
            text = text.replace(dev, eng)
        return text
    
    def print_progress_bar(self, current: int, total: int, prefix: str = '', suffix: str = '', length: int = 50):
        """
        Print a progress bar to console
        
        Args:
            current: Current progress value
            total: Total value
            prefix: Prefix text
            suffix: Suffix text
            length: Length of progress bar
        """
        percent = 100 * (current / float(total))
        filled_length = int(length * current // total)
        bar = '█' * filled_length + '-' * (length - filled_length)
        print(f'\r{prefix} |{bar}| {percent:.1f}% {suffix}', end='', flush=True)
        if current == total:
            print()
    
    def initialize_excel_file(self):
        """Initialize Excel file with headers"""
        wb = Workbook()
        ws = wb.active
        ws.title = "Voter Data"

        # Write headers - Updated with new column order
        headers = [
            'Sr.No',
            'Voter ID',
            'नाव',
            'वडिलांचे नाव',
            'ColumnX',
            'घर क्रमांक',
            'वय',
            'लिंग',
            'मतदार संघ',  # User input
            'Election Type',  # User input
            'भाग क्रमांक',  # User input (Ward Number)
            'मतदार संघ २',  # From ColumnX split (part 1)
            'यादी क्रमांक',  # From ColumnX split (part 2)
            'यादी अनु. क्र.'  # From ColumnX split (part 3)
        ]
        ws.append(headers)

        # Save initial file
        wb.save(self.output_path)
        wb.close()

        print(f"✓ Excel file initialized: {self.output_path.name}")
    
    def append_voters_to_excel(self, voters: List[Dict[str, str]]):
        """
        Thread-safe append voter records to Excel file incrementally
        
        Args:
            voters: List of voter dictionaries to append
        """
        if not voters:
            return
        
        # Use lock for thread-safe Excel writing
        with self.lock:
            try:
                # Load existing workbook
                wb = openpyxl.load_workbook(self.output_path)
                ws = wb.active
                
                # Batch append for better performance
                rows_to_append = []
                for voter in voters:
                    row = [
                        voter.get('Sr.No', ''),
                        voter.get('Voter ID', ''),
                        voter.get('नाव', ''),
                        voter.get('वडिलांचे नाव', ''),
                        voter.get('ColumnX', ''),
                        voter.get('घर क्रमांक', ''),
                        voter.get('वय', ''),
                        voter.get('लिंग', ''),
                        voter.get('मतदार संघ', ''),  # User input
                        voter.get('Election Type', ''),  # User input
                        voter.get('भाग क्रमांक', ''),  # User input
                        voter.get('मतदार संघ २', ''),  # From ColumnX split
                        voter.get('यादी क्रमांक', ''),  # From ColumnX split
                        voter.get('यादी अनु. क्र.', '')  # From ColumnX split
                    ]
                    rows_to_append.append(row)
                
                # Batch append all rows
                for row in rows_to_append:
                    ws.append(row)

                # Save workbook
                wb.save(self.output_path)
                wb.close()
                
                self.total_records_saved += len(voters)
                
            except Exception as e:
                print(f"\n⚠ Warning: Could not save {len(voters)} records: {e}")
                # Try to save to a backup file
                backup_path = self.output_path.parent / f"{self.output_path.stem}_backup.xlsx"
                try:
                    df = pd.DataFrame(voters)
                    df.to_excel(backup_path, index=False, mode='a', header=False)
                    print(f"✓ Saved to backup: {backup_path}")
                except:
                    pass
        
    def _optimize_image_for_ocr(self, image):
        """Optimize image for OCR while reducing memory footprint"""
        try:
            # Convert to grayscale if not already (reduces memory by ~66%)
            if image.mode != 'L':
                image = image.convert('L')
            
            # Resize if image is too large (OCR works well with smaller images)
            width, height = image.size
            max_dimension = 2000  # Reasonable size for OCR
            
            if width > max_dimension or height > max_dimension:
                # Calculate new size maintaining aspect ratio
                if width > height:
                    new_width = max_dimension
                    new_height = int(height * max_dimension / width)
                else:
                    new_height = max_dimension
                    new_width = int(width * max_dimension / height)
                
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            return image
        except Exception as e:
            print(f"⚠ Image optimization failed: {e}")
            return image

    def _process_image_batch(self, image_batch: List[tuple]) -> List[tuple]:
        """
        Process a batch of images with OCR - advanced memory optimization
        
        Args:
            image_batch: List of (page_num, image) tuples
            
        Returns:
            List of (page_num, text) tuples
        """
        results = []
        
        def process_single_image(page_data):
            page_num, image = page_data
            try:
                # Optimize image for memory efficiency
                optimized_image = self._optimize_image_for_ocr(image)
                
                # Clear original image immediately
                if image != optimized_image:
                    image.close() if hasattr(image, 'close') else None
                    del image
                
                # Check memory before OCR processing
                memory_mb = self._get_memory_usage_mb()
                if memory_mb > self._memory_threshold_low:
                    gc.collect()
                
                # Configure Tesseract for Marathi language with optimized settings
                custom_config = r'--oem 3 --psm 6 -l mar+eng -c tessedit_do_invert=0'
                text = pytesseract.image_to_string(optimized_image, config=custom_config)
                
                # Immediately clear optimized image from memory
                optimized_image.close() if hasattr(optimized_image, 'close') else None
                del optimized_image
                
                return (page_num, text)
            except MemoryError as e:
                print(f"\n❌ Memory error processing page {page_num}: {e}")
                # Emergency cleanup
                try:
                    if 'image' in locals():
                        image.close() if hasattr(image, 'close') else None
                        del image
                    if 'optimized_image' in locals():
                        optimized_image.close() if hasattr(optimized_image, 'close') else None
                        del optimized_image
                except:
                    pass
                gc.collect()
                return (page_num, "")
            except Exception as e:
                print(f"\n⚠ Error processing page {page_num}: {e}")
                return (page_num, "")
        
        # Adaptive parallel processing based on batch size and memory
        memory_mb = self._get_memory_usage_mb()
        batch_size = len(image_batch)
        
        # Determine optimal worker count based on memory and batch size
        if memory_mb > self._memory_threshold_high:
            # High memory usage - process sequentially
            max_workers = 1
        elif memory_mb > self._memory_threshold_low:
            # Moderate memory usage - limited parallelism
            max_workers = min(2, batch_size)
        else:
            # Low memory usage - can use more workers for larger batches
            max_workers = min(3, batch_size, self.max_workers)
        
        if max_workers == 1 or batch_size == 1:
            # Sequential processing
            for page_data in image_batch:
                try:
                    result = process_single_image(page_data)
                    results.append(result)
                except Exception as e:
                    page_num = page_data[0]
                    print(f"\n⚠ Error processing page {page_num}: {e}")
                    results.append((page_num, ""))
        else:
            # Parallel processing with dynamic worker count
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_page = {executor.submit(process_single_image, page_data): page_data[0]
                                 for page_data in image_batch}
                
                for future in as_completed(future_to_page):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        page_num = future_to_page[future]
                        print(f"\n⚠ Error in thread for page {page_num}: {e}")
                        results.append((page_num, ""))
        
        # Intelligent cleanup based on memory usage
        if memory_mb > self._memory_threshold_low or batch_size >= 4:
            gc.collect()
        
        # Sort results by page number
        results.sort(key=lambda x: x[0])
        return results

    def extract_text_from_pdf_batched(self, dpi: int = 300, start_page: int = None, end_page: int = None) -> List[str]:
        """
        Convert PDF pages to images and extract text using OCR with aggressive memory management
        Optimized to prevent malloc errors

        Args:
            dpi: Resolution for PDF to image conversion (reduced default for memory safety)
            start_page: Starting page number (1-indexed), None means start from page 1
            end_page: Ending page number (1-indexed), None means process till last page

        Returns:
            List of extracted text from each page
        """
        log_print(f"\n{'='*70}")
        if start_page or end_page:
            log_print(f"STEP 1: Converting PDF to Images (DPI: {dpi}, Pages: {start_page or 1}-{end_page or 'end'}) [MEMORY SAFE MODE]")
            log_print(f"Page Range Selected: {start_page or 1} to {end_page or 'last page'}")
        else:
            log_print(f"STEP 1: Converting PDF to Images (DPI: {dpi}) [MEMORY SAFE MODE]")
        log_print(f"{'='*70}")

        start_time = datetime.now()

        # Check initial memory
        self._check_memory_usage()

        # Optimized PDF conversion with better error handling and speed
        try:
            log_print(f"🔄 Converting PDF pages to images...")
            # First try with optimized parameters for speed and memory balance
            images = convert_from_path(
                self.pdf_path,
                dpi=dpi,
                first_page=start_page,
                last_page=end_page,
                thread_count=2,  # Use 2 threads for better speed
                grayscale=True,  # Use grayscale to reduce memory
                use_cropbox=True
            )
            log_print(f"✓ PDF conversion successful (primary method)")
        except Exception as e:
            log_print(f"⚠ Primary PDF conversion failed: {e}", 'WARNING')
            log_print(f"🔄 Trying fallback method with lower DPI...")
            # Fallback with minimal parameters
            try:
                images = convert_from_path(
                    self.pdf_path,
                    dpi=200,
                    first_page=start_page,
                    last_page=end_page
                )
                log_print(f"✓ PDF conversion successful (fallback method, DPI=200)")
            except Exception as e2:
                log_print(f"⚠ Fallback conversion also failed: {e2}", 'WARNING')
                log_print(f"🔄 Trying final fallback without page range...")
                # Final fallback - basic conversion
                try:
                    images = convert_from_path(self.pdf_path, dpi=150)
                    # If we got all pages but only wanted a range, slice them
                    if start_page or end_page:
                        start_idx = (start_page - 1) if start_page else 0
                        end_idx = end_page if end_page else len(images)
                        log_print(f"📄 Loaded all pages, slicing to range: {start_idx+1} to {end_idx}")
                        images = images[start_idx:end_idx]
                    log_print(f"✓ PDF conversion successful (basic method, DPI=150)")
                except Exception as e3:
                    log_print(f"❌ All conversion methods failed: {e3}", 'ERROR')
                    raise MemoryError(f"PDF conversion failed: {e3}")

        conversion_time = (datetime.now() - start_time).total_seconds()
        total_pages = len(images)
        log_print(f"✓ Converted {total_pages} pages in {conversion_time:.1f}s")
        log_print(f"   Image list: len(images) = {len(images)}, type = {type(images)}")

        if start_page and end_page:
            expected_pages = end_page - start_page + 1
            if total_pages != expected_pages:
                log_print(f"⚠ WARNING: Expected {expected_pages} pages (from {start_page} to {end_page}), but got {total_pages} pages", 'WARNING')
                log_print(f"   This means the PDF conversion returned {total_pages - expected_pages} {'extra' if total_pages > expected_pages else 'fewer'} pages than expected")

        if total_pages == 0:
            log_print(f"❌ ERROR: No pages were converted from PDF", 'ERROR')
            return []

        # Verify all images are valid
        none_count = sum(1 for img in images if img is None)
        if none_count > 0:
            log_print(f"⚠ WARNING: {none_count} images out of {total_pages} are None after conversion!", 'WARNING')
        else:
            log_print(f"✓ All {total_pages} images are valid (none are None)")
        
        # Force cleanup after conversion
        gc.collect()
        
        print(f"\n{'='*70}")
        print(f"STEP 2: Extracting Text via OCR (Memory Safe Batch Processing)")
        print(f"{'='*70}")
        
        page_texts = [""] * total_pages  # Pre-allocate list
        
        # Dynamic batch processing with adaptive sizing
        batch_start = 0
        batch_number = 1
        
        while batch_start < total_pages:
            # Dynamic batch size based on current memory and performance
            current_batch_size = self.current_batch_size
            batch_end = min(batch_start + current_batch_size, total_pages)
            batch_pages = list(range(batch_start, batch_end))
            
            # Advanced memory check with dynamic response
            memory_action_taken = self._check_memory_usage()
            if memory_action_taken:
                print(f"🔧 Adjusted batch size to {self.current_batch_size} based on memory usage")
                # Recalculate batch_end with new batch size
                batch_end = min(batch_start + self.current_batch_size, total_pages)
                batch_pages = list(range(batch_start, batch_end))
            
            try:
                # Record batch start time for performance optimization
                batch_start_time = datetime.now()

                # Create batch with page numbers - ensure we don't go beyond image list bounds
                image_batch = []
                for i in batch_pages:
                    if i < len(images) and images[i] is not None:
                        image_batch.append((i + 1, images[i]))
                    else:
                        # Log if we're trying to access an image that doesn't exist
                        if i >= len(images):
                            log_print(f"⚠ Warning: Batch {batch_number} page {i+1} index {i} exceeds image list length {len(images)}", 'WARNING')
                        elif images[i] is None:
                            log_print(f"⚠ Warning: Batch {batch_number} page {i+1} image is None (already cleared?)", 'WARNING')

                if image_batch:
                    # Progress update with dynamic batch info
                    progress = (batch_end / total_pages) * 100
                    memory_mb = self._get_memory_usage_mb()
                    print(f"Processing batch {batch_number} (size: {len(image_batch)}, pages {batch_start + 1}-{batch_end}) "
                          f"- {progress:.1f}% complete, Memory: {memory_mb:.1f}MB")

                    # Process batch
                    batch_results = self._process_image_batch(image_batch)

                    # Store results
                    for page_num, text in batch_results:
                        if page_num - 1 < len(page_texts):
                            page_texts[page_num - 1] = text
                        else:
                            print(f"⚠ Warning: Page number {page_num} exceeds page_texts length {len(page_texts)}")

                    # Calculate batch performance
                    batch_time = (datetime.now() - batch_start_time).total_seconds()
                    self._optimize_batch_size_based_on_performance(batch_time, len(image_batch))
                else:
                    log_print(f"⚠ Warning: Batch {batch_number} has no images to process (all None or out of bounds)", 'WARNING')
                
                # Clear processed images from memory immediately
                for i in batch_pages:
                    if i < len(images) and images[i] is not None:
                        # Just set to None - don't delete (which would shrink the list)
                        images[i] = None
                
                # Intelligent garbage collection
                if batch_number % 3 == 0:  # Every 3 batches
                    gc.collect()
                
                batch_start = batch_end
                batch_number += 1
                
            except Exception as e:
                print(f"⚠ Error processing batch {batch_number}: {e}")
                # Set empty text for failed pages
                for i in batch_pages:
                    if i < len(page_texts):
                        page_texts[i] = ""
                
                # Move to next batch even if this one failed
                batch_start = batch_end
                batch_number += 1
                continue
        
        # Final cleanup
        del images
        gc.collect()
        
        print(f"✓ OCR completed for all {total_pages} pages using memory-safe processing")
        return page_texts

    # Keep the old method for backward compatibility
    def extract_text_from_pdf(self, dpi: int = 300, start_page: int = None, end_page: int = None) -> List[str]:
        """Legacy method - redirects to optimized batch processing"""
        return self.extract_text_from_pdf_batched(dpi, start_page, end_page)
    
    def parse_voter_info(self, text: str, debug: bool = False) -> List[Dict[str, str]]:
        """
        Parse voter information from extracted text using voter ID-based extraction
        Supports multiple formats: SMF, SMM, LJZ, ITJ, and other patterns

        Args:
            text: Extracted text from a page
            debug: Enable debug logging

        Returns:
            List of voter records as dictionaries
        """
        voters = []

        # Split text into lines for processing
        lines = text.split('\n')

        # Debug counters
        total_matches_found = 0
        valid_ids_count = 0
        rejected_count = 0

        # MULTI-FORMAT VOTER ID PATTERNS
        # These patterns catch various voter ID formats with OCR error tolerance

        # Pattern 1: SMF/SMM format (S + M + F/M + 7 digits)
        pattern_smf = r'\b[S5$s][M०m6८६eE][FfM०m6८६]{1}[0-9०-९OILZSBCG]{7,8}\b'

        # Pattern 2: LJZ format (L + J/I + Z/2 + 7 digits)
        pattern_ljz = r'\b[LlI1][JjIi1][Zz2][0-9०-९OILZSBCG]{7,8}\b'

        # Pattern 3: ITJ format (I + T + J + 7 digits)
        pattern_itj = r'\b[IiLl1][Tt7][JjIi1][0-9०-९OILZSBCG]{7,8}\b'

        # Pattern 4: Generic 3-letter + 7-digit format (catch any other formats)
        pattern_generic = r'\b[A-Z][A-Z][A-Z][0-9]{7}\b'

        # Pattern 5: Ultra-flexible for badly OCR'd IDs
        pattern_flexible = r'\b[A-Z0-9]{3}[0-9]{7}\b'

        voter_entries = []
        processed_positions = set()  # Track positions to avoid duplicates

        for i, line in enumerate(lines):
            # Try all patterns and combine results
            all_matches = []
            all_matches.extend(list(re.finditer(pattern_smf, line)))
            all_matches.extend(list(re.finditer(pattern_ljz, line)))
            all_matches.extend(list(re.finditer(pattern_itj, line)))
            all_matches.extend(list(re.finditer(pattern_generic, line)))
            all_matches.extend(list(re.finditer(pattern_flexible, line)))

            # Sort by position and remove duplicates
            matches = []
            seen_starts = set()
            for match in sorted(all_matches, key=lambda m: m.start()):
                if match.start() not in seen_starts:
                    matches.append(match)
                    seen_starts.add(match.start())

            for match in matches:
                # Skip if we already processed this position
                if (i, match.start()) in processed_positions:
                    continue

                processed_positions.add((i, match.start()))
                voter_id_original = match.group().strip()
                voter_id = voter_id_original

                total_matches_found += 1

                # Clean up OCR errors in voter ID
                voter_id = voter_id.upper()

                # Convert Devanagari numerals to English
                voter_id = self.convert_marathi_numbers_to_english(voter_id)

                # Clean up common OCR misrecognitions
                voter_id = (voter_id.replace('$', 'S').replace('॥', '')
                           .replace('०', '0').replace(' ', ''))

                # Fix common letter/digit confusions in the numeric portion
                if len(voter_id) >= 10:
                    prefix = voter_id[:3]
                    digits = voter_id[3:]

                    # Clean the prefix based on common patterns
                    # SMF/SMM variations
                    if prefix[0] in '5$':
                        prefix = 'S' + prefix[1:]
                    if len(prefix) > 1 and prefix[1] in '8605':
                        prefix = prefix[0] + 'M' + prefix[2:]

                    # LJZ variations
                    if prefix[0] in 'I1':
                        prefix = 'L' + prefix[1:]
                    if len(prefix) > 1 and prefix[1] in 'I1i':
                        prefix = prefix[0] + 'J' + prefix[2:]
                    if len(prefix) > 2 and prefix[2] in '2':
                        prefix = prefix[0:2] + 'Z'

                    # ITJ variations
                    if prefix[0] in 'L1l' and len(prefix) > 1 and prefix[1] in 'T7t':
                        prefix = 'I' + 'T' + prefix[2:]

                    # Clean digits
                    digits = (digits.replace('O', '0').replace('I', '1').replace('l', '1')
                             .replace('Z', '2').replace('S', '5')
                             .replace('B', '8').replace('G', '6').replace('C', '0'))

                    voter_id = prefix + digits

                # Ensure exactly 10 characters
                if len(voter_id) > 10:
                    voter_id = voter_id[:10]
                elif len(voter_id) < 10:
                    rejected_count += 1
                    continue

                # Validate: Check if numeric part has at least 5 actual digits
                numeric_part = voter_id[3:]
                digit_count = sum(1 for c in numeric_part if c.isdigit())

                if digit_count < 5:
                    rejected_count += 1
                    continue

                # Successfully validated
                valid_ids_count += 1

                # Try to find house number (ColumnX pattern)
                house_num = ''
                remaining_line = line[match.end():]
                house_match = re.search(r'(\d+/\d+/\d+)', remaining_line)
                if house_match:
                    house_num = house_match.group(1)

                voter_entries.append({
                    'line_num': i,
                    'voter_id': voter_id,
                    'house_num': house_num,
                    'line': line,
                    'position': match.start()
                })
        
        # Process each voter entry
        for idx, entry_info in enumerate(voter_entries):
            # Split ColumnX (house_num) into three parts: 217/134/537
            matadaar_sangh_2 = ''
            yadi_number = ''
            yadi_sr_no = ''

            if entry_info['house_num']:
                # Try to split the 217/134/537 format
                parts = entry_info['house_num'].split('/')
                if len(parts) == 3:
                    matadaar_sangh_2 = parts[0]  # 217
                    yadi_number = parts[1]  # 134
                    yadi_sr_no = parts[2]  # 537

            voter = {
                'Sr.No': yadi_sr_no,  # Use third part from ColumnX as Sr.No
                'Voter ID': entry_info['voter_id'],
                'नाव': '',
                'वडिलांचे नाव': '',
                'ColumnX': entry_info['house_num'],  # Keep original format (217/134/537)
                'घर क्रमांक': '',
                'वय': '',
                'लिंग': '',
                'मतदार संघ': self.matadaar_sangh,  # User input
                'Election Type': self.election_type,  # User input
                'भाग क्रमांक': self.ward_number,  # User input
                'मतदार संघ २': matadaar_sangh_2,  # From ColumnX split (217)
                'यादी क्रमांक': yadi_number,  # From ColumnX split (134)
                'यादी अनु. क्र.': yadi_sr_no  # From ColumnX split (537)
            }

            # Get context lines for this voter
            start_line = max(0, entry_info['line_num'] - 2)
            end_line = min(len(lines), entry_info['line_num'] + 8)

            if idx > 0 and voter_entries[idx-1]['line_num'] == entry_info['line_num']:
                start_line = max(0, entry_info['line_num'] - 2)

            context_lines = lines[start_line:end_line]
            context_text = '\n'.join(context_lines)

            # Extract details from context
            self._extract_voter_details_from_context(context_text, voter, entry_info['voter_id'], entry_info['house_num'])
            voters.append(voter)

            # Track Sr. No. for sequence validation (if available)
            if yadi_sr_no:
                try:
                    sr_no_int = int(yadi_sr_no)
                    self.all_sr_numbers.append(sr_no_int)
                except ValueError:
                    pass

        # Update overall statistics
        self.total_patterns_found += total_matches_found
        self.total_valid_ids += valid_ids_count
        self.total_rejected_ids += rejected_count

        # Always log statistics to track extraction quality
        if len(voters) > 0 or total_matches_found > 0:
            print(f"  📊 Page Stats: {total_matches_found} voter IDs found, {valid_ids_count} valid, {rejected_count} rejected, {len(voters)} voters extracted")

        return voters

    def _extract_voter_details_from_context(self, context: str, voter: Dict[str, str], voter_id: str = '', house_num: str = ''):
        """
        Extract detailed voter information from context text.
        Handles columnar layout where 3 voters appear side-by-side.

        Args:
            context: Context text containing voter information
            voter: Dictionary to populate with voter details
            voter_id: The voter ID to help locate relevant information
            house_num: The house number pattern (217/134/537) to help locate voter column
        """
        lines = context.split('\n')

        voter_column = 0
        voter_id_line = ''

        # Find the line containing house number patterns to determine voter column
        for line in lines:
            if house_num and house_num in line:
                voter_id_line = line
                house_matches = list(re.finditer(r'\d+/\d+/\d+', line))
                for i, match in enumerate(house_matches):
                    if match.group() == house_num:
                        voter_column = i
                        break
                break
        
        # Extract voter name
        for line in lines:
            if 'मतदाराचे' in line and 'पूर्ण' in line:
                matches = list(re.finditer(r'मतदाराचे\s*(?:पूर्ण|[\(]?of\s+ee)\s*[:\-]?\s*[\'\']?(.+?)(?=\s*मतदाराचे|\s*$)', line))
                if len(matches) > voter_column:
                    name = matches[voter_column].group(1).strip()
                    name = re.sub(r'\s+', ' ', name)
                    name = name.replace("'", "").replace("'", "").strip()
                    name = name.replace('\u200d', '')
                    voter['नाव'] = name
                break
        
        # Extract father's/husband's name
        for line in lines:
            if ('वडिलांचे' in line or 'पतीचे' in line) and 'नाव' in line and ':' in line:
                matches = list(re.finditer(r'(?:वडिलांचे|पतीचे)\s*नावा?\s*[:]\s*([\u0900-\u097F\s]+?)(?:\s*[|\|]*\s*[Aa]vailable)', line, re.IGNORECASE))
                if len(matches) > voter_column:
                    name = matches[voter_column].group(1).strip()
                    name = re.sub(r'\s+', ' ', name)
                    name = name.replace('।', '').replace('|', '').strip()
                    voter['वडिलांचे नाव'] = name
                break
        
        # Extract house number
        for line in lines:
            if 'घर' in line and 'क्रमांक' in line:
                matches = list(re.finditer(r'घर\s*क्रमांक\s*[:]\s*([A-Z0-9/\-]+)', line))
                if len(matches) > voter_column:
                    voter['घर क्रमांक'] = matches[voter_column].group(1).strip()
                break
        
        # Extract age and gender
        for line in lines:
            if 'वय' in line and 'लिंग' in line:
                matches = list(re.finditer(r'वय\s*:?\s*([०-९\d]{1,3})\s+लिंग\s*:\s*([^\s]+)', line))
                if len(matches) > voter_column:
                    match = matches[voter_column]
                    age_text = match.group(1)
                    voter['वय'] = self.convert_marathi_numbers_to_english(age_text)
                    gender_text = match.group(2).strip()
                    if re.search(r'पु(?:\b|\s|$)|पुरुष', gender_text):
                        voter['लिंग'] = 'पुरुष'
                    elif re.search(r'स्+[\s\.]*री|स्त्री|महिला|स्री|स््री', gender_text):
                        voter['लिंग'] = 'स्त्री'
                break

    def validate_sequence_and_find_gaps(self) -> tuple:
        """
        Validate Sr. No. sequence and find missing numbers

        Returns:
            Tuple of (min_sr, max_sr, missing_ranges, coverage_percent)
        """
        if not self.all_sr_numbers:
            return (0, 0, [], 0.0)

        # Sort and get unique Sr. No.
        sorted_sr = sorted(set(self.all_sr_numbers))

        if not sorted_sr:
            return (0, 0, [], 0.0)

        min_sr = sorted_sr[0]
        max_sr = sorted_sr[-1]
        expected_count = max_sr - min_sr + 1
        actual_count = len(sorted_sr)

        # Find missing ranges
        missing_ranges = []
        current_missing_start = None

        for expected in range(min_sr, max_sr + 1):
            if expected not in sorted_sr:
                if current_missing_start is None:
                    current_missing_start = expected
            else:
                if current_missing_start is not None:
                    # End of a missing range
                    missing_end = expected - 1
                    if current_missing_start == missing_end:
                        missing_ranges.append(str(current_missing_start))
                    else:
                        missing_ranges.append(f"{current_missing_start}-{missing_end}")
                    current_missing_start = None

        # Handle case where missing range extends to the end
        if current_missing_start is not None:
            if current_missing_start == max_sr:
                missing_ranges.append(str(current_missing_start))
            else:
                missing_ranges.append(f"{current_missing_start}-{max_sr}")

        # Calculate coverage percentage
        coverage_percent = (actual_count / expected_count * 100) if expected_count > 0 else 0.0

        return (min_sr, max_sr, missing_ranges, coverage_percent)

    def _process_text_batch(self, text_batch: List[tuple]) -> List[Dict[str, str]]:
        """
        Process a batch of page texts to extract voter information in parallel
        
        Args:
            text_batch: List of (page_num, text) tuples
            
        Returns:
            List of voter dictionaries
        """
        all_voters = []
        
        def process_single_text(page_data):
            page_num, text = page_data
            try:
                voters = self.parse_voter_info(text)
                return (page_num, voters)
            except Exception as e:
                print(f"\n⚠ Error parsing page {page_num}: {e}")
                return (page_num, [])
        
        # Use ThreadPoolExecutor for parallel text processing
        with ThreadPoolExecutor(max_workers=min(len(text_batch), self.max_workers)) as executor:
            future_to_page = {executor.submit(process_single_text, page_data): page_data[0]
                             for page_data in text_batch}
            
            for future in as_completed(future_to_page):
                try:
                    page_num, voters = future.result()
                    all_voters.extend(voters)
                except Exception as e:
                    page_num = future_to_page[future]
                    print(f"\n⚠ Error in parsing thread for page {page_num}: {e}")
        
        return all_voters

    def process_pdf_incrementally(self, start_page: int = None, end_page: int = None) -> int:
        """
        Process the entire PDF and save voter information incrementally with memory-safe processing
        Ultra-conservative approach to prevent malloc errors

        Args:
            start_page: Starting page number (1-indexed), None means start from page 1
            end_page: Ending page number (1-indexed), None means process till last page

        Returns:
            Total number of records processed
        """
        log_print(f"\n{'='*70}")
        if start_page or end_page:
            log_print(f"Processing PDF: {self.pdf_path.name} (Pages: {start_page or 1} to {end_page or 'end'}) [MEMORY SAFE MODE]")
        else:
            log_print(f"Processing PDF: {self.pdf_path.name} (MEMORY SAFE MODE)")
        log_print(f"{'='*70}")

        # Check initial memory
        self._check_memory_usage()

        # Initialize Excel file
        log_print(f"\nInitializing output file...")
        self.initialize_excel_file()

        # Extract text from specified pages using memory-safe batch processing
        page_texts = self.extract_text_from_pdf_batched(start_page=start_page, end_page=end_page)

        log_print(f"\n{'='*70}")
        log_print(f"STEP 3: Parsing and Saving Voter Data (Memory Safe Processing)")
        log_print(f"{'='*70}")

        total_pages = len(page_texts)
        all_voters_count = 0

        # Log page range info
        if start_page or end_page:
            expected_pages = (end_page or total_pages) - (start_page or 1) + 1
            log_print(f"Page Range: {start_page or 1} to {end_page or total_pages}")
            log_print(f"Expected Pages: {expected_pages}, Extracted Pages: {total_pages}")
        
        # Process texts one by one for maximum memory safety
        pages_with_content = 0
        pages_skipped_empty = 0

        for i, text in enumerate(page_texts):
            # Check memory before processing each page
            if self._check_memory_usage():
                print(f"⚠ Memory cleanup performed before page {i + 1}")

            # Progress update
            progress = ((i + 1) / total_pages) * 100
            print(f"Processing page {i + 1}/{total_pages} - {progress:.1f}% complete")

            if not text.strip():
                print(f"  ⚠ Page {i + 1} skipped: No OCR text extracted (empty page or OCR failed)")
                pages_skipped_empty += 1
                continue

            pages_with_content += 1

            try:
                # Process single page text
                voters = self.parse_voter_info(text)

                if voters:
                    # Save immediately to Excel
                    self.append_voters_to_excel(voters)
                    all_voters_count += len(voters)

                    print(f"  ✓ Page {i + 1} processed: {len(voters)} voters found, {self.total_records_saved} total saved")
                else:
                    print(f"  ℹ Page {i + 1} processed: 0 voters found (page has text but no voter IDs matched)")

                # Clear text from memory
                page_texts[i] = ""

                # Force garbage collection after each page
                gc.collect()
                
            except MemoryError as e:
                print(f"\n❌ Memory error processing page {i + 1}: {e}")
                print(f"  Forcing cleanup and continuing...")
                gc.collect()
                continue
                
            except Exception as e:
                print(f"\n⚠ Error processing page {i + 1}: {e}")
                print(f"  Continuing with next page...")
                continue
        
        # Final cleanup
        del page_texts
        gc.collect()
        
        print(f"\n✓ All pages processed and saved incrementally using memory-safe processing")

        # Validate sequence and find gaps
        min_sr, max_sr, missing_ranges, coverage_percent = self.validate_sequence_and_find_gaps()

        log_print(f"\n{'='*70}")
        log_print(f"EXTRACTION SUMMARY")
        log_print(f"{'='*70}")
        if start_page or end_page:
            log_print(f"Page Range Selected: {start_page or 1} to {end_page or 'last'}")
        log_print(f"Total Pages Processed: {total_pages}")
        log_print(f"Pages with Content: {pages_with_content}")
        log_print(f"Pages Skipped (Empty OCR): {pages_skipped_empty}")
        log_print(f"Total Voters Extracted: {all_voters_count}")
        log_print(f"Total Records Saved to Excel: {self.total_records_saved}")
        if pages_with_content > 0:
            log_print(f"Average per Page with Content: {all_voters_count/pages_with_content:.1f}")
        else:
            log_print(f"Average per Page: N/A")

        print(f"\nSequence Validation:")
        if min_sr > 0:
            print(f"  Sr. No. Range: {min_sr} to {max_sr}")
            print(f"  Expected Voters: {max_sr - min_sr + 1}")
            print(f"  Extracted Voters: {len(set(self.all_sr_numbers))}")
            print(f"  Coverage: {coverage_percent:.1f}%")
            if missing_ranges:
                # Limit display to first 20 missing ranges
                if len(missing_ranges) <= 20:
                    print(f"  Missing Sr. No.: {', '.join(missing_ranges)}")
                else:
                    print(f"  Missing Sr. No.: {', '.join(missing_ranges[:20])}... ({len(missing_ranges)} total gaps)")
            else:
                print(f"  Missing Sr. No.: None - Complete sequence! ✓")

        print(f"\nPattern Matching Statistics:")
        print(f"  Total Voter IDs Found: {self.total_patterns_found}")
        print(f"  Valid IDs Extracted: {self.total_valid_ids}")
        print(f"  Rejected IDs: {self.total_rejected_ids}")
        if self.total_patterns_found > 0:
            success_rate = (self.total_valid_ids / self.total_patterns_found) * 100
            print(f"  Success Rate: {success_rate:.1f}%")

        print(f"\nProcessing Mode:")
        print(f"  Memory Safe Mode: Single page processing")
        print(f"  Max Workers: {self.max_workers} (sequential processing)")
        print(f"{'='*70}")
        
        return self.total_records_saved
    
    def verify_excel_output(self):
        """Verify the Excel file and show statistics"""
        try:
            df = pd.read_excel(self.output_path, engine='openpyxl')
            
            print(f"\n{'='*70}")
            print(f"EXCEL FILE VERIFICATION")
            print(f"{'='*70}")
            print(f"File: {self.output_path.name}")
            print(f"File Size: {self.output_path.stat().st_size / 1024:.1f} KB")
            print(f"Total Rows (including header): {len(df) + 1}")
            print(f"Total Records: {len(df)}")
            print(f"Columns: {', '.join(df.columns)}")
            
            # Show data quality stats
            print(f"\nData Quality:")
            print(f"  Voter IDs: {df['Voter ID'].notna().sum()} / {len(df)}")
            print(f"  Names: {df['नाव'].notna().sum()} / {len(df)}")
            print(f"  Ages: {df['वय'].notna().sum()} / {len(df)}")
            print(f"  Genders: {df['लिंग'].notna().sum()} / {len(df)}")
            
            print(f"{'='*70}")
            
            return True
        except Exception as e:
            print(f"⚠ Could not verify Excel file: {e}")
            return False


def main():
    """Main entry point for the script"""
    if len(sys.argv) < 2:
        print("\n" + "="*70)
        print(" Marathi Voter List OCR Scanner (Optimized Batch Processing)")
        print("="*70)
        print("\nUsage: python voter_list_ocr.py <pdf_file_path> [output_excel_path]")
        print("\nExamples:")
        print("  python voter_list_ocr.py 'Jakhuri Voter List.pdf'")
        print("  python voter_list_ocr.py 'Jakhuri Voter List.pdf' output.xlsx")
        print("\nFeatures:")
        print("  ✓ Optimized batch processing with threading")
        print("  ✓ Incremental saving - data is saved batch by batch")
        print("  ✓ Memory efficient - prevents malloc errors")
        print("  ✓ Crash-safe - progress is not lost if interrupted")
        print("  ✓ Progress tracking with percentage and record count")
        print("="*70 + "\n")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    start_time = datetime.now()
    
    try:
        print("\n" + "="*70)
        print(" MARATHI VOTER LIST OCR SCANNER (OPTIMIZED MODE)")
        print("="*70)
        print(f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Input PDF: {Path(pdf_path).name}")
        
        # Create OCR processor with optimizations
        ocr = VoterListOCR(pdf_path, output_path)
        print(f"Batch Size: {ocr.batch_size}, Max Workers: {ocr.max_workers}")
        
        # Process with optimized batch processing
        total_saved = ocr.process_pdf_incrementally()
        
        # Verify output
        ocr.verify_excel_output()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print("\n" + "="*70)
        print(" PROCESSING COMPLETED SUCCESSFULLY!")
        print("="*70)
        print(f"Output File: {ocr.output_path.absolute()}")
        print(f"Total Records: {total_saved}")
        print(f"End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
        print(f"Performance: {total_saved/duration:.1f} records/second")
        print("="*70 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n" + "="*70)
        print(" PROCESS INTERRUPTED BY USER")
        print("="*70)
        if 'ocr' in locals():
            print(f"✓ Data saved up to batch currently being processed")
            print(f"✓ Total records saved: {ocr.total_records_saved}")
            print(f"✓ Output file: {ocr.output_path}")
            print("\nYou can resume by processing the PDF again.")
            print("The existing file will be overwritten.")
        print("="*70 + "\n")
        # Force cleanup
        gc.collect()
        sys.exit(0)
        
    except MemoryError as e:
        print(f"\n❌ Memory Error: {e}", file=sys.stderr)
        print("Try reducing batch size or processing smaller page ranges.")
        if 'ocr' in locals():
            print(f"\n✓ Partial data may be saved in: {ocr.output_path}")
            print(f"✓ Records saved before error: {ocr.total_records_saved}")
        # Force cleanup
        gc.collect()
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        if 'ocr' in locals():
            print(f"\n✓ Partial data may be saved in: {ocr.output_path}")
            print(f"✓ Records saved before error: {ocr.total_records_saved}")
        import traceback
        traceback.print_exc()
        # Force cleanup
        gc.collect()
        sys.exit(1)


if __name__ == "__main__":
    main()
