# Marathi Voter List OCR Scanner

Extract voter information from Marathi PDF files and export to Excel with high accuracy. This tool uses OCR (Optical Character Recognition) to read voter ID cards from PDF documents and converts them into structured Excel spreadsheets.

## Features

- ✅ **High accuracy OCR** - Handles Marathi/Devanagari script and English text
- ✅ **Robust error handling** - Corrects common OCR misreadings automatically
- ✅ **Incremental saving** - Data saved page-by-page to prevent data loss
- ✅ **Progress tracking** - Real-time progress bars and status updates
- ✅ **Handles malformed IDs** - Automatically cleans OCR errors in voter IDs
<<<<<<< HEAD
<<<<<<< HEAD
=======
- ✅ **Web Interface** - Modern, user-friendly web UI for easy PDF processing
- ✅ **Background Processing** - Asynchronous processing with real-time status updates
- ✅ **Download Ready** - Processed Excel files ready for download
>>>>>>> f8e8f2b (changes for showing table/filtering)
=======
- ✅ **Web Interface** - Modern, user-friendly web UI for easy PDF processing
- ✅ **Background Processing** - Asynchronous processing with real-time status updates
- ✅ **Download Ready** - Processed Excel files ready for download
=======
>>>>>>> b3e6614 (added readme)
>>>>>>> dbc1894 (added readme)

## Prerequisites

### System Requirements

- **Python**: 3.8 or higher
- **Tesseract OCR**: Required for text extraction
- **Poppler**: Required for PDF to image conversion

### Installing Tesseract OCR

#### macOS
```bash
brew install tesseract
brew install tesseract-lang  # For Marathi language support
brew install poppler
```

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-mar poppler-utils
```

#### Windows
1. Download Tesseract installer from: https://github.com/UB-Mannheim/tesseract/wiki
2. Download Poppler from: https://github.com/oschwartz10612/poppler-windows/releases
3. Add both to your system PATH

## Installation

### 1. Clone or download this repository

```bash
cd /path/to/data-extractor
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
```

### 3. Activate the virtual environment

#### macOS/Linux
```bash
source venv/bin/activate
```

#### Windows
```bash
venv\Scripts\activate
```

### 4. Install Python dependencies

```bash
pip install -r requirements.txt
```

## Usage

<<<<<<< HEAD
<<<<<<< HEAD
### Basic Usage

=======
=======
>>>>>>> dbc1894 (added readme)
### Web Interface (Recommended)

The easiest way to use this tool is through the web interface:

1. **Start the web server:**
   ```bash
   source venv/bin/activate
   python app.py
   ```

2. **Open your browser:**
   Navigate to `http://localhost:8080`

3. **Upload and process:**
   - Click "Choose File" or drag and drop a PDF file
   - Wait for processing to complete
   - Download the generated Excel file

The web interface provides:
- Drag-and-drop file upload
- Real-time progress tracking
- Automatic file processing
- Direct Excel file download

### Command Line Usage

**Basic Usage:**
<<<<<<< HEAD
>>>>>>> f8e8f2b (changes for showing table/filtering)
=======
=======
### Basic Usage

>>>>>>> b3e6614 (added readme)
>>>>>>> dbc1894 (added readme)
```bash
source venv/bin/activate  # Activate virtual environment first
python voter_list_ocr.py <pdf_file> [output_file.xlsx]
```

<<<<<<< HEAD
<<<<<<< HEAD
### Examples

**Process a PDF with automatic output filename:**
=======
**Examples:**

Process a PDF with automatic output filename:
>>>>>>> f8e8f2b (changes for showing table/filtering)
=======
**Examples:**

Process a PDF with automatic output filename:
=======
### Examples

**Process a PDF with automatic output filename:**
>>>>>>> b3e6614 (added readme)
>>>>>>> dbc1894 (added readme)
```bash
python voter_list_ocr.py "Voter List.pdf"
# Creates: Voter List_voters.xlsx
```

<<<<<<< HEAD
<<<<<<< HEAD
**Specify custom output filename:**
=======
Specify custom output filename:
>>>>>>> f8e8f2b (changes for showing table/filtering)
=======
Specify custom output filename:
=======
**Specify custom output filename:**
>>>>>>> b3e6614 (added readme)
>>>>>>> dbc1894 (added readme)
```bash
python voter_list_ocr.py "Voter List.pdf" output.xlsx
```

<<<<<<< HEAD
<<<<<<< HEAD
**Process the main PDF:**
=======
Process the main PDF:
>>>>>>> f8e8f2b (changes for showing table/filtering)
=======
Process the main PDF:
=======
**Process the main PDF:**
>>>>>>> b3e6614 (added readme)
>>>>>>> dbc1894 (added readme)
```bash
python voter_list_ocr.py main_pdf.pdf main_output.xlsx
```

## Output Format

The script generates an Excel file with the following columns:

| Column | Description |
|--------|-------------|
| Sr.No | Serial number from the voter list |
| Voter ID | Cleaned and validated voter ID (e.g., SMF2132058) |
| नाव | Voter's full name (in Marathi) |
| वडिलांचे नाव | Father's/Husband's name (in Marathi) |
| ColumnX | House number pattern (e.g., 217/47/34) |
| घर क्रमांक | House number |
| वय | Age |
| लिंग | Gender (पुरुष/स्त्री) |

## Performance

- **Speed**: Approximately 5-6 seconds per page
- **Accuracy**: ~98% voter ID capture rate
- **Test results**: 323 out of 330 records extracted from test PDF

### Sample Performance
- 11 pages: ~56 seconds
- 100 pages: ~8-9 minutes
- 600 pages: ~50-60 minutes

## How It Works

1. **PDF to Image Conversion**: Converts each PDF page to high-resolution images (300 DPI)
2. **OCR Processing**: Extracts text using Tesseract with Marathi + English language models
3. **Pattern Matching**: Identifies voter IDs using advanced regex patterns
4. **Error Correction**: Automatically fixes common OCR errors:
   - Devanagari numerals (०-९) → English (0-9)
   - Character misreadings ($, ॥, 5) → Correct prefix (SMF)
   - Lowercase → Uppercase
   - Malformed prefixes (507, 571, etc.) → SMF
5. **Data Extraction**: Extracts voter details from surrounding context
6. **Incremental Saving**: Saves records page-by-page to Excel

## Common OCR Errors Handled

The script automatically corrects these patterns:

| OCR Output | Corrected To | Issue |
|------------|--------------|-------|
| `$॥॥॥6724645` | `SMF6724645` | Dollar sign, Devanagari pipes |
| `smf6120331` | `SMF6120331` | Lowercase |
| `50८6920474` | `SMF6920474` | Devanagari digit in ID |
| `5076376966` | `SMF6376966` | 7 misread as F |
| `57१6991145` | `SMF6991145` | 7 misread, Devanagari digit |

## Troubleshooting

### "Tesseract not found" error
- Ensure Tesseract is installed: `tesseract --version`
- Check PATH includes Tesseract directory

### "PDF conversion failed" error
- Ensure Poppler is installed
- Check PDF file is not corrupted: `pdfinfo yourfile.pdf`

### Low extraction rate
- Check PDF quality - blurry images reduce accuracy
- Verify Marathi language pack: `tesseract --list-langs` should show `mar`

### Out of memory errors
- Reduce DPI in `extract_text_from_pdf()` method (line 153) from 300 to 200
- Process smaller page ranges at a time


## Development

### Running Tests

```bash
# Test on small PDF
python voter_list_ocr.py test3.pdf test_output.xlsx

# Check extraction quality
python -c "import pandas as pd; df = pd.read_excel('test_output.xlsx'); print(f'Records: {len(df)}'); print(df.head())"
```

### Updating Dependencies

```bash
pip freeze > requirements.txt
```
