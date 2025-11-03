#!/usr/bin/env python3
"""
Marathi Voter List OCR Scanner
Extracts voter information from Marathi PDF files and exports to Excel
With incremental saving to prevent data loss
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import numpy as np
from datetime import datetime
import openpyxl
from openpyxl import Workbook


class VoterListOCR:
    """Main class for processing Marathi voter list PDFs"""

    def __init__(self, pdf_path: str, output_path: Optional[str] = None):
        """
        Initialize the OCR processor

        Args:
            pdf_path: Path to the PDF file to process
            output_path: Path for output Excel file
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

        # Devanagari to English number mapping
        self.devanagari_to_english = {
            '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
            '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'
        }

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
        
        # Write headers
        headers = ['Sr.No', 'Voter ID', 'नाव', 'वडिलांचे नाव', 'ColumnX', 'घर क्रमांक', 'वय', 'लिंग']
        ws.append(headers)
        
        # Save initial file
        wb.save(self.output_path)
        wb.close()
        
        print(f"✓ Excel file initialized: {self.output_path.name}")
    
    def append_voters_to_excel(self, voters: List[Dict[str, str]]):
        """
        Append voter records to Excel file incrementally
        
        Args:
            voters: List of voter dictionaries to append
        """
        if not voters:
            return
        
        try:
            # Load existing workbook
            wb = openpyxl.load_workbook(self.output_path)
            ws = wb.active
            
            # Append each voter record
            for voter in voters:
                row = [
                    voter.get('Sr.No', ''),
                    voter.get('Voter ID', ''),
                    voter.get('नाव', ''),
                    voter.get('वडिलांचे नाव', ''),
                    voter.get('ColumnX', ''),
                    voter.get('घर क्रमांक', ''),
                    voter.get('वय', ''),
                    voter.get('लिंग', '')
                ]
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
        
    def extract_text_from_pdf(self, dpi: int = 300) -> List[str]:
        """
        Convert PDF pages to images and extract text using OCR
        
        Args:
            dpi: Resolution for PDF to image conversion (higher = better quality but slower)
            
        Returns:
            List of extracted text from each page
        """
        print(f"\n{'='*70}")
        print(f"STEP 1: Converting PDF to Images (DPI: {dpi})")
        print(f"{'='*70}")
        
        start_time = datetime.now()
        images = convert_from_path(self.pdf_path, dpi=dpi)
        conversion_time = (datetime.now() - start_time).total_seconds()
        
        total_pages = len(images)
        print(f"✓ Converted {total_pages} pages in {conversion_time:.1f}s")
        
        print(f"\n{'='*70}")
        print(f"STEP 2: Extracting Text via OCR")
        print(f"{'='*70}")
        
        page_texts = []
        
        for i, image in enumerate(images, 1):
            # Progress bar
            self.print_progress_bar(
                i, 
                total_pages, 
                prefix=f'Page {i}/{total_pages}',
                suffix=f'Complete',
                length=40
            )
            
            # Configure Tesseract for Marathi language
            custom_config = r'--oem 3 --psm 6 -l mar+eng'
            text = pytesseract.image_to_string(image, config=custom_config)
            page_texts.append(text)
        
        print(f"✓ OCR completed for all {total_pages} pages")
        return page_texts
    
    def parse_voter_info(self, text: str) -> List[Dict[str, str]]:
        """
        Parse voter information from extracted text
        
        Args:
            text: Extracted text from a page
            
        Returns:
            List of voter records as dictionaries
        """
        voters = []
        
        # Split text into lines for processing
        lines = text.split('\n')
        
        # Find all voter IDs with their positions
        voter_id_pattern = r'(?:[A-Z5५$॥S]|5५)[A-Z5५M॥६४$0-9][A-ZF६८॥0-9][0-9SMFOI]{7}'
        voter_entries = []
        
        for i, line in enumerate(lines):
            # Find all voter IDs in this line
            matches = list(re.finditer(voter_id_pattern, line))
            
            for match in matches:
                voter_id = match.group()
                
                # Clean up OCR errors in voter ID
                voter_id = self.convert_marathi_numbers_to_english(voter_id)
                voter_id = (voter_id.replace('$', 'S').replace('॥', 'M')
                           .replace('le', '').replace('Ig', '').replace('log', '')
                           .replace('5५', 'SM'))

                # Fix the prefix
                if len(voter_id) >= 10:
                    if voter_id[:2] in ['55', '5S', 'S5']:
                        voter_id = 'SM' + voter_id[2:]

                    char1 = voter_id[0]
                    char2 = voter_id[1]
                    char3 = voter_id[2]

                    if char1 in '5485$':
                        char1 = 'S'
                    if char2 in 'S86$564':
                        char2 = 'M'
                    if char3 in 'M8676':
                        char3 = 'F'

                    prefix = char1 + char2 + char3

                    digits = voter_id[3:]
                    digits = (digits.replace('S', '5').replace('O', '0').replace('I', '1')
                             .replace('l', '1').replace('Z', '2').replace('F', '6')
                             .replace('B', '8').replace('G', '6'))

                    voter_id = prefix + digits
                
                # Try to find house number
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
            voter = {
                'Sr.No': '',
                'Voter ID': entry_info['voter_id'],
                'नाव': '',
                'वडिलांचे नाव': '',
                'ColumnX': entry_info['house_num'],
                'घर क्रमांक': '',
                'वय': '',
                'लिंग': ''
            }
            
            # Get context lines
            start_line = max(0, entry_info['line_num'] - 2)
            end_line = min(len(lines), entry_info['line_num'] + 8)
            
            if idx > 0 and voter_entries[idx-1]['line_num'] == entry_info['line_num']:
                start_line = max(0, entry_info['line_num'] - 2)
            
            context_lines = lines[start_line:end_line]
            context_text = '\n'.join(context_lines)
            
            # Extract details from context
            self._extract_voter_details_from_context(context_text, voter, entry_info['voter_id'])
            voters.append(voter)
        
        return voters
    
    def _extract_voter_details_from_context(self, context: str, voter: Dict[str, str], voter_id: str = ''):
        """
        Extract detailed voter information from context text.
        Handles columnar layout where 3 voters appear side-by-side.
        
        Args:
            context: Context text containing voter information
            voter: Dictionary to populate with voter details
            voter_id: The voter ID to help locate relevant information
        """
        lines = context.split('\n')
        
        columnx_value = voter.get('ColumnX', '')
        voter_column = 0
        voter_id_line = ''
        
        # Find the line containing ColumnX patterns
        for line in lines:
            if columnx_value and columnx_value in line:
                voter_id_line = line
                columnx_matches = list(re.finditer(r'\d+/\d+/\d+', line))
                for i, match in enumerate(columnx_matches):
                    if match.group() == columnx_value:
                        voter_column = i
                        break
                break
        
        # Extract serial number from ColumnX
        if columnx_value:
            parts = columnx_value.split('/')
            if len(parts) == 3:
                voter['Sr.No'] = parts[2]
        
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
   
    def process_pdf_incrementally(self) -> int:
        """
        Process the entire PDF and save voter information incrementally
        
        Returns:
            Total number of records processed
        """
        print(f"\n{'='*70}")
        print(f"Processing PDF: {self.pdf_path.name}")
        print(f"{'='*70}")
        
        # Initialize Excel file
        print(f"\nInitializing output file...")
        self.initialize_excel_file()
        
        # Extract text from all pages
        page_texts = self.extract_text_from_pdf()
        
        print(f"\n{'='*70}")
        print(f"STEP 3: Parsing and Saving Voter Data (Incremental)")
        print(f"{'='*70}")
        
        total_pages = len(page_texts)
        all_voters_count = 0
        
        for i, text in enumerate(page_texts, 1):
            # Progress bar for parsing
            self.print_progress_bar(
                i,
                total_pages,
                prefix=f'Page {i}/{total_pages}',
                suffix=f'[{self.total_records_saved} records saved]',
                length=40
            )
            
            try:
                # Parse voters from this page
                voters = self.parse_voter_info(text)
                
                if voters:
                    # Immediately save to Excel
                    self.append_voters_to_excel(voters)
                    all_voters_count += len(voters)
            
            except Exception as e:
                print(f"\n⚠ Error processing page {i}: {e}")
                print(f"  Continuing with next page...")
                continue
        
        print(f"\n✓ All pages processed and saved incrementally")
        
        print(f"\n{'='*70}")
        print(f"EXTRACTION SUMMARY")
        print(f"{'='*70}")
        print(f"Total Pages Processed: {total_pages}")
        print(f"Total Voters Extracted: {all_voters_count}")
        print(f"Total Records Saved to Excel: {self.total_records_saved}")
        print(f"Average per Page: {all_voters_count/total_pages:.1f}")
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
        print(" Marathi Voter List OCR Scanner (Incremental Save)")
        print("="*70)
        print("\nUsage: python voter_list_ocr.py <pdf_file_path> [output_excel_path]")
        print("\nExamples:")
        print("  python voter_list_ocr.py 'Jakhuri Voter List.pdf'")
        print("  python voter_list_ocr.py 'Jakhuri Voter List.pdf' output.xlsx")
        print("\nFeatures:")
        print("  ✓ Incremental saving - data is saved page by page")
        print("  ✓ Crash-safe - progress is not lost if interrupted")
        print("  ✓ Progress tracking with percentage and record count")
        print("="*70 + "\n")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    start_time = datetime.now()
    
    try:
        print("\n" + "="*70)
        print(" MARATHI VOTER LIST OCR SCANNER (INCREMENTAL MODE)")
        print("="*70)
        print(f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Input PDF: {Path(pdf_path).name}")
        
        # Create OCR processor
        ocr = VoterListOCR(pdf_path, output_path)
        
        # Process with incremental saving
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
        print("="*70 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n" + "="*70)
        print(" PROCESS INTERRUPTED BY USER")
        print("="*70)
        if 'ocr' in locals():
            print(f"✓ Data saved up to page currently being processed")
            print(f"✓ Total records saved: {ocr.total_records_saved}")
            print(f"✓ Output file: {ocr.output_path}")
            print("\nYou can resume by processing the PDF again.")
            print("The existing file will be overwritten.")
        print("="*70 + "\n")
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        if 'ocr' in locals():
            print(f"\n✓ Partial data may be saved in: {ocr.output_path}")
            print(f"✓ Records saved before error: {ocr.total_records_saved}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()