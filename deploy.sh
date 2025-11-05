#!/bin/bash

# Voter List OCR - Deployment Script
# This script helps deploy the application using different methods

set -e

echo "=============================================="
echo "  Voter List OCR - Deployment Script"
echo "=============================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to deploy with Docker
deploy_docker() {
    echo "🐳 Deploying with Docker..."
    
    if ! command_exists docker; then
        echo "❌ Docker is not installed. Please install Docker first."
        echo "   Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! command_exists docker-compose; then
        echo "❌ Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    echo "✓ Docker and Docker Compose found"
    
    # Stop any existing containers
    echo "🛑 Stopping any existing containers..."
    docker-compose down 2>/dev/null || true
    
    # Build and start the application
    echo "🔨 Building and starting the application..."
    docker-compose up --build -d
    
    # Wait for the application to start
    echo "⏳ Waiting for application to start..."
    sleep 10
    
    # Check if the application is running
    if curl -f http://localhost:8080/api/health >/dev/null 2>&1; then
        echo "✅ Application deployed successfully!"
        echo "🌐 Access the application at: http://localhost:8080"
        echo "📊 View logs with: docker-compose logs -f"
        echo "🛑 Stop with: docker-compose down"
    else
        echo "❌ Application failed to start. Check logs with: docker-compose logs"
        exit 1
    fi
}

# Function to deploy natively
deploy_native() {
    echo "No support for native deployment. Contact Omkar Deshpande for this..."
    # echo "💻 Deploying natively..."
    
    # # Check Python
    # if ! command_exists python3; then
    #     echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    #     exit 1
    # fi
    
    # # Check Tesseract
    # if ! command_exists tesseract; then
    #     echo "❌ Tesseract OCR is not installed."
    #     echo "   Install with:"
    #     echo "   - macOS: brew install tesseract tesseract-lang"
    #     echo "   - Ubuntu: sudo apt install tesseract-ocr tesseract-ocr-mar"
    #     echo "   - Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki"
    #     exit 1
    # fi
    
    # # Check Poppler
    # if ! command_exists pdftoppm; then
    #     echo "❌ Poppler utilities are not installed."
    #     echo "   Install with:"
    #     echo "   - macOS: brew install poppler"
    #     echo "   - Ubuntu: sudo apt install poppler-utils"
    #     echo "   - Windows: Download from https://github.com/oschwartz10612/poppler-windows/releases"
    #     exit 1
    # fi
    
    # echo "✓ Python, Tesseract, and Poppler found"
    
    # # Install Python dependencies
    # echo "📦 Installing Python dependencies..."
    # pip3 install -r requirements.txt
    
    # # Create necessary directories
    # mkdir -p uploads outputs
    
    # # Start the application
    # echo "🚀 Starting the application..."
    # echo "🌐 Application will be available at: http://localhost:8080"
    # echo "🛑 Press Ctrl+C to stop"
    # python3 app.py
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [docker|native|help]"
    echo ""
    echo "Options:"
    echo "  docker    Deploy using Docker (recommended)"
    echo "  native    Deploy natively with Python"
    echo "  help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 docker     # Deploy with Docker"
    echo "  $0 native     # Deploy natively"
}

# Main script logic
case "${1:-docker}" in
    docker)
        deploy_docker
        ;;
    native)
        deploy_native
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        echo "❌ Unknown option: $1"
        show_usage
        exit 1
        ;;
esac