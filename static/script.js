// Global variables
let currentJobId = null;
let statusCheckInterval = null;
let tableData = [];
let filteredData = [];
let sortColumn = null;
let sortDirection = 'asc';
let columnFilters = {};
let currentFile = null;
let pdfTotalPages = 0;
let selectedLanguage = 'marathi';

// DOM Elements
const uploadSection = document.getElementById('uploadSection');
const configurationSection = document.getElementById('configurationSection');
const processingSection = document.getElementById('processingSection');
const resultsSection = document.getElementById('resultsSection');
const errorSection = document.getElementById('errorSection');
const fileInput = document.getElementById('fileInput');
const uploadBox = document.getElementById('uploadBox');
const fileInfo = document.getElementById('fileInfo');
const downloadBtn = document.getElementById('downloadBtn');
const resetBtn = document.getElementById('resetBtn');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    checkHealth();

    // Ensure modal is hidden on page load
    const modal = document.getElementById('imageModal');
    if (modal && !modal.classList.contains('hidden')) {
        modal.classList.add('hidden');
    }
});

function setupEventListeners() {
    // File input change
    fileInput.addEventListener('change', handleFileSelect);

    // Drag and drop
    uploadBox.addEventListener('dragover', handleDragOver);
    uploadBox.addEventListener('dragleave', handleDragLeave);
    uploadBox.addEventListener('drop', handleDrop);
    uploadBox.addEventListener('click', () => fileInput.click());

    // Download button
    downloadBtn.addEventListener('click', downloadFile);

    // Reset button
    resetBtn.addEventListener('click', resetForm);

    // Configuration buttons
    document.getElementById('startProcessingBtn').addEventListener('click', startProcessing);
    document.getElementById('cancelConfigBtn').addEventListener('click', () => showSection('upload'));

    // Page range inputs
    document.getElementById('startPage').addEventListener('input', updatePageRangeInfo);
    document.getElementById('endPage').addEventListener('input', updatePageRangeInfo);

    // Modal close
    document.getElementById('modalClose').addEventListener('click', closeModal);
    document.getElementById('modalOverlay').addEventListener('click', closeModal);
}

// Health check
async function checkHealth() {
    try {
        const response = await fetch('/api/health');
        const data = await response.json();
        console.log('Server health:', data);
    } catch (error) {
        console.error('Health check failed:', error);
    }
}

// File selection handler
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        currentFile = file;
        prepareConfiguration(file);
    }
}

// Drag and drop handlers
function handleDragOver(event) {
    event.preventDefault();
    uploadBox.classList.add('drag-over');
}

function handleDragLeave(event) {
    event.preventDefault();
    uploadBox.classList.remove('drag-over');
}

function handleDrop(event) {
    event.preventDefault();
    uploadBox.classList.remove('drag-over');

    const files = event.dataTransfer.files;
    if (files.length > 0) {
        const file = files[0];
        if (file.type === 'application/pdf') {
            currentFile = file;
            prepareConfiguration(file);
        } else {
            showError('Please upload a PDF file');
        }
    }
}

// Prepare configuration section (called after file selection)
async function prepareConfiguration(file) {
    // Validate file
    if (file.size > 500 * 1024 * 1024) {
        showError('File size exceeds 500MB limit');
        return;
    }

    // Update UI
    fileInfo.textContent = `Selected: ${file.name} (${formatFileSize(file.size)})`;

    // Show configuration section
    showSection('configuration');

    // Start generating PDF previews
    await generatePDFPreviews(file);
}

// Generate PDF thumbnails
async function generatePDFPreviews(file) {
    try {
        // Show loading
        document.getElementById('previewLoading').classList.remove('hidden');
        document.getElementById('previewContainer').classList.add('hidden');

        // Upload file first to get job ID
        const formData = new FormData();
        formData.append('file', file);

        const uploadResponse = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const uploadData = await uploadResponse.json();

        if (!uploadResponse.ok || !uploadData.success) {
            throw new Error(uploadData.error || 'Upload failed');
        }

        currentJobId = uploadData.job_id;

        // Fetch preview thumbnails
        const previewResponse = await fetch(`/api/preview/${currentJobId}`);
        const previewData = await previewResponse.json();

        if (!previewResponse.ok || !previewData.success) {
            throw new Error(previewData.error || 'Failed to generate previews');
        }

        // Store total pages
        pdfTotalPages = previewData.total_pages;

        // Update page range inputs
        document.getElementById('startPage').max = pdfTotalPages;
        document.getElementById('endPage').max = pdfTotalPages;
        document.getElementById('endPage').value = pdfTotalPages;
        updatePageRangeInfo();

        // Render thumbnails
        renderThumbnails(previewData.thumbnails);

        // Hide loading, show preview
        document.getElementById('previewLoading').classList.add('hidden');
        document.getElementById('previewContainer').classList.remove('hidden');

    } catch (error) {
        console.error('Preview generation error:', error);
        showError(`Failed to generate previews: ${error.message}`);
    }
}

// Render thumbnail gallery
function renderThumbnails(thumbnails) {
    const gallery = document.getElementById('previewGallery');
    gallery.innerHTML = '';

    thumbnails.forEach(thumb => {
        const div = document.createElement('div');
        div.className = 'preview-thumbnail';
        div.dataset.page = thumb.page;

        div.innerHTML = `
            <img src="data:image/png;base64,${thumb.data}" alt="Page ${thumb.page}">
            <p>Page ${thumb.page}</p>
        `;

        // Click to view full size
        div.addEventListener('click', () => showFullSizeImage(thumb.page, thumb.data));

        gallery.appendChild(div);
    });

    // Update selection highlight
    updateThumbnailSelection();
}

// Update thumbnail selection based on page range
function updateThumbnailSelection() {
    const startPage = parseInt(document.getElementById('startPage').value) || 1;
    const endPage = parseInt(document.getElementById('endPage').value) || pdfTotalPages;

    document.querySelectorAll('.preview-thumbnail').forEach(thumb => {
        const page = parseInt(thumb.dataset.page);
        if (page >= startPage && page <= endPage) {
            thumb.classList.add('selected');
        } else {
            thumb.classList.remove('selected');
        }
    });
}

// Update page range info
function updatePageRangeInfo() {
    const startPage = parseInt(document.getElementById('startPage').value) || 1;
    const endPage = parseInt(document.getElementById('endPage').value) || pdfTotalPages;

    // Validate
    if (startPage > endPage) {
        document.getElementById('startPage').value = endPage;
    }
    if (endPage > pdfTotalPages) {
        document.getElementById('endPage').value = pdfTotalPages;
    }
    if (startPage < 1) {
        document.getElementById('startPage').value = 1;
    }

    const validStart = parseInt(document.getElementById('startPage').value);
    const validEnd = parseInt(document.getElementById('endPage').value);
    const pageCount = validEnd - validStart + 1;

    document.getElementById('pageCount').textContent = pageCount;

    // Update thumbnail selection
    updateThumbnailSelection();
}

// Show full-size image in modal
function showFullSizeImage(pageNumber, imageData) {
    if (!imageData) {
        console.error('No image data provided');
        return;
    }
    document.getElementById('modalImage').src = `data:image/png;base64,${imageData}`;
    document.getElementById('modalPageInfo').textContent = `Page ${pageNumber}`;
    document.getElementById('imageModal').classList.remove('hidden');
}

// Close modal
function closeModal() {
    document.getElementById('imageModal').classList.add('hidden');
}

// Validate configuration form
function validateConfigForm() {
    const matadaarSangh = document.getElementById('matadaarSangh').value.trim();
    const electionType = document.getElementById('electionType').value.trim();
    const wardNumber = document.getElementById('wardNumber').value.trim();

    if (!matadaarSangh || !electionType || !wardNumber) {
        showError('Please fill in all required fields (Matadar Sangh, Election Type, Ward Number)');
        return false;
    }

    return true;
}

// Start processing with configuration
async function startProcessing() {
    // Validate form
    if (!validateConfigForm()) {
        return;
    }

    if (!currentJobId) {
        showError('No file uploaded');
        return;
    }

    // Get configuration values
    const matadaarSangh = document.getElementById('matadaarSangh').value.trim();
    const electionType = document.getElementById('electionType').value.trim();
    const wardNumber = document.getElementById('wardNumber').value.trim();
    const startPage = parseInt(document.getElementById('startPage').value);
    const endPage = parseInt(document.getElementById('endPage').value);

    // Show processing section
    showSection('processing');
    updateStatus('processing', 10, 'Starting processing...');

    try {
        // Send processing request with configuration
        const response = await fetch(`/api/process/${currentJobId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                matadaar_sangh: matadaarSangh,
                election_type: electionType,
                ward_number: wardNumber,
                start_page: startPage,
                end_page: endPage,
                language: selectedLanguage
            })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            updateStatus('processing', 20, 'Configuration received. Processing PDF...');
            startStatusPolling();
        } else {
            showError(data.error || 'Processing failed');
        }
    } catch (error) {
        console.error('Processing error:', error);
        showError('Failed to start processing. Please try again.');
    }
}

// Poll for status updates
function startStatusPolling() {
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
    }
    
    statusCheckInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/status/${currentJobId}`);
            const status = await response.json();
            
            updateStatus(
                status.status,
                status.progress || 0,
                status.message || 'Processing...',
                status
            );
            
            if (status.status === 'completed') {
                clearInterval(statusCheckInterval);
                showResults(status);
            } else if (status.status === 'error') {
                clearInterval(statusCheckInterval);
                showError(status.error || 'Processing failed');
            }
        } catch (error) {
            console.error('Status check error:', error);
        }
    }, 2000); // Check every 2 seconds
}

// Update status display
function updateStatus(status, progress, message, fullStatus = {}) {
    const statusIcon = document.getElementById('statusIcon');
    const statusText = document.getElementById('statusText');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const messageText = document.getElementById('messageText');
    
    // Update icon based on status
    if (status === 'uploading') {
        statusIcon.textContent = '📤';
        statusText.textContent = 'Uploading';
    } else if (status === 'processing') {
        statusIcon.textContent = '⏳';
        statusText.textContent = 'Processing';
    } else if (status === 'completed') {
        statusIcon.textContent = '✅';
        statusText.textContent = 'Completed';
    }
    
    // Update progress
    progressBar.style.width = `${progress}%`;
    progressText.textContent = `${progress}%`;
    messageText.textContent = message;
}

// Show results
async function showResults(status) {
    document.getElementById('resultFilename').textContent = status.filename || 'Unknown';
    document.getElementById('resultRecords').textContent = status.total_records || 0;

    // Fetch and display table data
    await fetchTableData();

    showSection('results');
}

// Fetch table data from server
async function fetchTableData() {
    try {
        const response = await fetch(`/api/data/${currentJobId}`);
        const result = await response.json();

        if (result.success) {
            tableData = result.data;
            filteredData = [...tableData];
            renderTable(result.headers);
            updateFilteredCount();
        } else {
            console.error('Failed to fetch data:', result.error);
        }
    } catch (error) {
        console.error('Error fetching table data:', error);
    }
}

// Render table with headers and data
function renderTable(headers) {
    const tableHeaders = document.getElementById('tableHeaders');
    const tableFilters = document.getElementById('tableFilters');
    const tableBody = document.getElementById('tableBody');

    // Clear existing content
    tableHeaders.innerHTML = '';
    tableFilters.innerHTML = '';
    tableBody.innerHTML = '';

    // Add "Our Sr.NO" as first column (UI only, not in data)
    const ourSrNoTh = document.createElement('th');
    ourSrNoTh.innerHTML = `
        <div class="header-cell" data-column="Our Sr.NO">
            <span class="header-text">  </span>
            <span class="sort-indicator"></span>
        </div>
    `;
    ourSrNoTh.style.cssText = 'background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); min-width: 80px;';
    tableHeaders.appendChild(ourSrNoTh);

    // Add empty filter cell for "Our Sr.NO" (no filtering on this column)
    const ourSrNoFilterTh = document.createElement('th');
    ourSrNoFilterTh.innerHTML = '<span style="opacity: 0.5; font-size: 0.85em;">-</span>';
    tableFilters.appendChild(ourSrNoFilterTh);

    // Create header row with sort indicators for actual data columns
    headers.forEach(header => {
        const th = document.createElement('th');
        th.innerHTML = `
            <div class="header-cell" data-column="${header}">
                <span class="header-text">${header}</span>
                <span class="sort-indicator">⇅</span>
            </div>
        `;
        th.addEventListener('click', () => handleSort(header));
        tableHeaders.appendChild(th);
    });

    // Create filter row for actual data columns
    headers.forEach(header => {
        const th = document.createElement('th');
        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'filter-input';
        input.placeholder = `Filter ${header}...`;
        input.dataset.column = header;
        input.addEventListener('input', handleFilter);
        th.appendChild(input);
        tableFilters.appendChild(th);
    });

    // Render data rows
    renderTableBody(headers);

    // Add clear filters event listener
    const clearFiltersBtn = document.getElementById('clearFiltersBtn');
    clearFiltersBtn.addEventListener('click', clearFilters);
}

// Render table body with current filtered data
function renderTableBody(headers) {
    const tableBody = document.getElementById('tableBody');
    tableBody.innerHTML = '';

    filteredData.forEach((row, index) => {
        const tr = document.createElement('tr');

        // Add "Our Sr.NO" as first cell (sequential number)
        const ourSrNoTd = document.createElement('td');
        ourSrNoTd.textContent = index + 1;
        ourSrNoTd.style.cssText = 'font-weight: 600; background: #f0fdf4; color: #059669; text-align: center;';
        tr.appendChild(ourSrNoTd);

        // Add actual data columns
        headers.forEach(header => {
            const td = document.createElement('td');
            td.textContent = row[header] || '';
            tr.appendChild(td);
        });
        tableBody.appendChild(tr);
    });
}

// Handle column sorting
function handleSort(column) {
    if (sortColumn === column) {
        // Toggle sort direction
        sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        sortColumn = column;
        sortDirection = 'asc';
    }

    // Sort the filtered data
    filteredData.sort((a, b) => {
        let aVal = a[column] || '';
        let bVal = b[column] || '';

        // Try to parse as number
        const aNum = parseFloat(aVal);
        const bNum = parseFloat(bVal);

        if (!isNaN(aNum) && !isNaN(bNum)) {
            return sortDirection === 'asc' ? aNum - bNum : bNum - aNum;
        }

        // String comparison
        aVal = String(aVal).toLowerCase();
        bVal = String(bVal).toLowerCase();

        if (sortDirection === 'asc') {
            return aVal.localeCompare(bVal);
        } else {
            return bVal.localeCompare(aVal);
        }
    });

    // Update sort indicators
    document.querySelectorAll('.header-cell').forEach(cell => {
        const indicator = cell.querySelector('.sort-indicator');
        if (cell.dataset.column === column) {
            indicator.textContent = sortDirection === 'asc' ? '▲' : '▼';
            cell.classList.add('sorted');
        } else {
            indicator.textContent = '⇅';
            cell.classList.remove('sorted');
        }
    });

    // Re-render table body
    const headers = Array.from(document.querySelectorAll('#tableHeaders th')).map(
        th => th.querySelector('.header-cell')?.dataset.column
    ).filter(h => h && h !== 'Our Sr.NO');
    renderTableBody(headers);
}

// Handle column filtering
function handleFilter(event) {
    const column = event.target.dataset.column;
    const value = event.target.value.toLowerCase().trim();

    // Update column filters
    if (value === '') {
        delete columnFilters[column];
    } else {
        columnFilters[column] = value;
    }

    // Apply all filters
    applyFilters();
}

// Apply all active filters
function applyFilters() {
    filteredData = tableData.filter(row => {
        // Check if row matches all filter conditions
        return Object.keys(columnFilters).every(column => {
            const cellValue = String(row[column] || '').toLowerCase();
            const filterValue = columnFilters[column];
            return cellValue.includes(filterValue);
        });
    });

    // Re-sort if a sort is active
    if (sortColumn) {
        handleSort(sortColumn);
        // Call handleSort again to maintain current direction
        if (sortDirection === 'desc') {
            handleSort(sortColumn);
        }
    } else {
        // Just re-render
        const headers = Array.from(document.querySelectorAll('#tableHeaders th')).map(
            th => th.querySelector('.header-cell')?.dataset.column
        ).filter(h => h && h !== 'Our Sr.NO');
        renderTableBody(headers);
    }

    updateFilteredCount();
}

// Clear all filters
function clearFilters() {
    columnFilters = {};
    filteredData = [...tableData];

    // Clear filter inputs
    document.querySelectorAll('.filter-input').forEach(input => {
        input.value = '';
    });

    // Re-render table
    const headers = Array.from(document.querySelectorAll('#tableHeaders th')).map(
        th => th.querySelector('.header-cell')?.dataset.column
    ).filter(h => h && h !== 'Our Sr.NO');
    renderTableBody(headers);
    updateFilteredCount();
}

// Update filtered record count
function updateFilteredCount() {
    document.getElementById('filteredRecords').textContent = filteredData.length;
}

// Download file
async function downloadFile() {
    if (!currentJobId) {
        showError('No file to download');
        return;
    }

    try {
        // Get headers from table, excluding "Our Sr.NO" (UI only column)
        const headers = Array.from(document.querySelectorAll('#tableHeaders th')).map(
            th => th.querySelector('.header-cell').dataset.column
        ).filter(header => header !== 'Our Sr.NO');

        // Use filtered data endpoint
        const response = await fetch(`/api/download-filtered/${currentJobId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                headers: headers,
                data: filteredData
            })
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;

            // Get filename from response headers or use default
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = 'voters_filtered.xlsx';
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="?(.+?)"?$/);
                if (filenameMatch) {
                    filename = filenameMatch[1];
                }
            }

            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            const error = await response.json();
            showError(error.error || 'Download failed');
        }
    } catch (error) {
        console.error('Download error:', error);
        showError('Failed to download file. Please try again.');
    }
}

// Show error
function showError(message) {
    document.getElementById('errorMessage').textContent = message;
    showSection('error');
    
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
    }
}

// Show specific section
function showSection(section) {
    uploadSection.classList.add('hidden');
    configurationSection.classList.add('hidden');
    processingSection.classList.add('hidden');
    resultsSection.classList.add('hidden');
    errorSection.classList.add('hidden');

    switch (section) {
        case 'upload':
            uploadSection.classList.remove('hidden');
            break;
        case 'configuration':
            configurationSection.classList.remove('hidden');
            break;
        case 'processing':
            processingSection.classList.remove('hidden');
            break;
        case 'results':
            resultsSection.classList.remove('hidden');
            break;
        case 'error':
            errorSection.classList.remove('hidden');
            break;
    }
}

// Reset form
function resetForm() {
    currentJobId = null;
    currentFile = null;
    pdfTotalPages = 0;
    fileInput.value = '';
    fileInfo.textContent = '';
    tableData = [];
    filteredData = [];
    sortColumn = null;
    sortDirection = 'asc';
    columnFilters = {};

    // Clear configuration form
    document.getElementById('matadaarSangh').value = '';
    document.getElementById('electionType').value = '';
    document.getElementById('wardNumber').value = '';
    document.getElementById('startPage').value = 1;
    document.getElementById('endPage').value = 1;
    document.getElementById('previewGallery').innerHTML = '';

    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
    }

    showSection('upload');
}

// Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

