# 📄 Voter List OCR Scanner - Client Package

## Quick Start Guide

Welcome! This package contains the complete Voter List OCR Scanner application. Follow these simple steps to get started:

### 🚀 Fastest Way to Deploy (Recommended)

#### For Windows Users:
1. **Double-click** `deploy.bat`
2. **Choose option 1** (Docker) when prompted
3. **Wait** for the application to start
4. **Open your browser** to http://localhost:8080

#### For Mac/Linux Users:
1. **Open Terminal** in this folder
2. **Run**: `./deploy.sh docker`
3. **Wait** for the application to start
4. **Open your browser** to http://localhost:8080

---

## 📋 What's Included

```
📁 voter-ocr-scanner/
├── 🚀 deploy.sh              # Mac/Linux deployment script
├── 🚀 deploy.bat             # Windows deployment script
├── 📖 DEPLOYMENT_GUIDE.md    # Detailed deployment guide
├── 📖 CLIENT_PACKAGE_README.md # This file
├── 🐳 Dockerfile             # Docker configuration
├── 🐳 docker-compose.yml     # Docker Compose setup
├── ⚙️ app.py                 # Development server
├── ⚙️ app_production.py      # Production server
├── 🧠 voter_list_ocr.py      # Core OCR engine
├── 📦 requirements.txt       # Python dependencies
├── 🌐 static/                # Web interface files
├── 🌐 templates/             # HTML templates
├── 📁 uploads/               # PDF upload folder (auto-created)
└── 📁 outputs/               # Excel output folder (auto-created)
```

---

## 🎯 Application Features

### ✅ What This Application Does
- **Extracts voter data** from Marathi PDF files
- **Converts to Excel** format with structured data
- **Web-based interface** - no technical knowledge required
- **Batch processing** - handles large PDF files efficiently
- **Real-time progress** tracking during processing
- **Data filtering** and preview before download

### 📊 Supported Data Fields
- Serial Number (Sr.No)
- Voter ID
- Name (नाव)
- Father's/Husband's Name (वडिलांचे नाव)
- House Number (घर क्रमांक)
- Age (वय)
- Gender (लिंग)
- Custom fields (मतदार संघ, Election Type, etc.)

---

## 🔧 Deployment Options

### Docker  🐳

**Advantages**:
- ✅ No dependency installation required
- ✅ Works on Windows, Mac, and Linux
- ✅ Consistent performance
- ✅ Easy updates

**Requirements**:
- Docker Desktop installed

**Steps**:
1. Install Docker Desktop from https://docker.com/get-started
2. Run deployment script (`deploy.bat` or `deploy.sh`)
3. Access application at http://localhost:8080

---

## 🖥️ System Requirements

### Minimum Requirements
- **RAM**: 4GB (8GB recommended for large files)
- **Storage**: 2GB free space
- **OS**: Windows 10, macOS 10.14, or Ubuntu 18.04+
- **Browser**: Chrome, Firefox, Safari, or Edge

### For Docker Deployment
- **Docker Desktop**: Latest version
- **Available RAM**: 2GB for Docker

---

## 📖 How to Use the Application

### Step 1: Upload PDF
1. **Open** http://localhost:8080 in your browser
2. **Select language** (Marathi is default)
3. **Upload PDF file** by dragging & dropping or clicking "Choose File"

### Step 2: Configure Processing
1. **Fill in required fields**:
   - मतदार संघ (Matadar Sangh)
   - Election Type
   - भाग क्रमांक (Ward Number)
2. **Select page range** (optional)
3. **Preview PDF pages** to verify content

### Step 3: Process & Download
1. **Click "Start Processing"**
2. **Wait for completion** (progress bar shows status)
3. **Review extracted data** in the table
4. **Filter data** if needed
5. **Download Excel file**

---

## 🆘 Troubleshooting

### Common Issues & Solutions

#### "Port 8080 already in use"
**Solution**: Another application is using port 8080
```bash
# Windows
netstat -ano | findstr :8080
# Kill the process using the PID shown

# Mac/Linux
lsof -ti:8080 | xargs kill -9
```

#### "Docker not found"
**Solution**: Install Docker Desktop
- Download from: https://docker.com/get-started
- Follow installation instructions for your OS

#### "Application won't start"
**Solutions**:
1. Check if port 8080 is available
2. Restart Docker Desktop
3. Run: `docker-compose down && docker-compose up -d`

#### "OCR accuracy is low"
**Solutions**:
1. Ensure PDF quality is good (not scanned at low resolution)
2. Try processing smaller page ranges
3. Check if PDF contains actual text (not just images)

#### "Out of memory errors"
**Solutions**:
1. Process smaller page ranges (e.g., 10-20 pages at a time)
2. Close other applications to free up RAM
3. Restart the application

---

### Performance Tips
- **Process large PDFs in smaller batches** (50-100 pages)
- **Close browser tabs** you're not using during processing
- **Ensure stable internet connection** for Docker downloads
- **Use high-quality PDF files** for better OCR accuracy

---

## 🔒 Security & Privacy

### Data Handling
- **Files are processed locally** - no data sent to external servers
- **Uploaded files are automatically deleted** after processing
- **Output files remain** until manually deleted
- **No personal data is logged** or transmitted

### Network Security
- **Application runs locally** on your machine
- **No external network access** required for processing
- **Firewall friendly** - only uses local ports

---

---

## 📋 Quick Reference

### Essential Commands

#### Docker Deployment
```bash
# Start application
docker-compose up -d

# Stop application
docker-compose down

# View logs
docker-compose logs -f

# Restart
docker-compose restart
```


### Important URLs
- **Application**: http://localhost:8080
- **Health Check**: http://localhost:8080/api/health

### Important Folders
- **Uploads**: `uploads/` (PDF files)
- **Outputs**: `outputs/` (Excel files)
- **Logs**: `voter_ocr_app.log`

---

**🎉 You're all set! Enjoy using the Voter List OCR Scanner!**

For detailed technical information, see `DEPLOYMENT_GUIDE.md`