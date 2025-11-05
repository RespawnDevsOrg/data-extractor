# Voter List OCR - Client Deployment Guide

## Overview
This guide provides multiple deployment options for delivering the Voter List OCR application to your client. Choose the option that best fits your client's technical capabilities and infrastructure.

## 🐳 Docker Deployment

### Prerequisites
- Docker installed on the target system
- Docker Compose (usually included with Docker Desktop)

### Quick Start
1. **Extract the application package** to a directory on the client's system
2. **Open terminal/command prompt** in the application directory
3. **Run the application**:
   ```bash
   docker-compose up -d
   ```
4. **Access the application** at: http://localhost:8080

### Commands
```bash
# Start the application
docker-compose up -d

# Stop the application
docker-compose down

# View logs
docker-compose logs -f

# Restart the application
docker-compose restart

# Update the application (after receiving new version)
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Advantages
- ✅ **Zero dependency issues** - Everything is included
- ✅ **Consistent environment** - Works the same everywhere
- ✅ **Easy updates** - Just replace files and restart
- ✅ **Automatic restart** - Application restarts if it crashes
- ✅ **Cross-platform** - Works on Windows, macOS, Linux

---


## 📁 File Structure

```
voter-ocr-app/
├── app.py                 # Development server
├── app_production.py      # Production server
├── voter_list_ocr.py      # Core OCR logic
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker configuration
├── docker-compose.yml    # Docker Compose configuration
├── .dockerignore         # Docker ignore file
├── start.sh              # Linux/macOS startup script
├── start.bat             # Windows startup script
├── static/               # Frontend assets
│   ├── script.js
│   └── style.css
├── templates/            # HTML templates
│   └── index.html
├── uploads/              # Uploaded PDF files (auto-created)
├── outputs/              # Generated Excel files (auto-created)
└── DEPLOYMENT_GUIDE.md   # This file
```

---

## 🔧 Configuration

### Environment Variables
```bash
# Optional environment variables
FLASK_ENV=production          # Set to production for deployment
MAX_FILE_SIZE=500MB          # Maximum upload file size
UPLOAD_FOLDER=uploads        # Upload directory
OUTPUT_FOLDER=outputs        # Output directory
```

### Port Configuration
- Default port: **8080**
- To change port, modify `docker-compose.yml` or app startup

### Storage Configuration
- **Uploads**: Stored in `uploads/` directory
- **Outputs**: Stored in `outputs/` directory
- **Logs**: Stored in `voter_ocr_app.log`

---


#### Docker Issues
```bash
# Rebuild Docker image
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# View detailed logs
docker-compose logs -f voter-ocr-app

# Check container status
docker-compose ps
```

### Support
- Check application logs in `voter_ocr_app.log`
- Use health check endpoint: `http://localhost:8080/api/health`
- Monitor system resources during processing

---



**Version**: 1.0.0  
**Last Updated**: 5 November 2025
**Compatibility**: Windows 10+, macOS 10.14+, Ubuntu 18.04+