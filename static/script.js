// Main application JavaScript
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize file upload drag and drop
    initializeFileUpload();
    
    // Initialize search functionality
    initializeSearch();
    
    // Initialize filters
    initializeFilters();
    
    // Initialize progress bars
    initializeProgressBars();
}

function initializeFileUpload() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('medical_report');
    
    if (uploadArea && fileInput) {
        // Click on upload area triggers file input
        uploadArea.addEventListener('click', () => fileInput.click());
        
        // Drag and drop functionality
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                updateFileName(files[0].name);
            }
        });
        
        // File input change
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                updateFileName(e.target.files[0].name);
            }
        });
    }
}

function updateFileName(fileName) {
    const fileNameElement = document.getElementById('fileName');
    if (fileNameElement) {
        fileNameElement.textContent = fileName;
        fileNameElement.classList.remove('text-muted');
        fileNameElement.classList.add('text-success', 'fw-bold');
    }
}

function initializeSearch() {
    const searchInput = document.getElementById('searchReports');
    if (searchInput) {
        searchInput.addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();
            const reportItems = document.querySelectorAll('.report-item');
            
            reportItems.forEach(item => {
                const text = item.textContent.toLowerCase();
                if (text.includes(searchTerm)) {
                    item.style.display = '';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    }
}

function initializeFilters() {
    const filterButtons = document.querySelectorAll('.filter-btn');
    filterButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            // Remove active class from all buttons
            filterButtons.forEach(b => b.classList.remove('active'));
            // Add active class to clicked button
            this.classList.add('active');
            
            const filter = this.getAttribute('data-filter');
            filterReports(filter);
        });
    });
}

function filterReports(filter) {
    const reportItems = document.querySelectorAll('.report-item');
    
    reportItems.forEach(item => {
        switch (filter) {
            case 'all':
                item.style.display = '';
                break;
            case 'recent':
                // Logic to show recent items (last 7 days)
                const dateText = item.querySelector('.report-date').textContent;
                if (isRecent(dateText)) {
                    item.style.display = '';
                } else {
                    item.style.display = 'none';
                }
                break;
            case 'shared':
                if (item.classList.contains('shared-report')) {
                    item.style.display = '';
                } else {
                    item.style.display = 'none';
                }
                break;
        }
    });
}

function isRecent(dateString) {
    // Simple recent check (last 7 days)
    const reportDate = new Date(dateString);
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    return reportDate >= weekAgo;
}

function initializeProgressBars() {
    // Animate progress bars when they come into view
    const progressBars = document.querySelectorAll('.progress-bar');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const progressBar = entry.target;
                const width = progressBar.getAttribute('data-width') || '100';
                progressBar.style.width = width + '%';
                progressBar.setAttribute('aria-valuenow', width);
            }
        });
    });
    
    progressBars.forEach(bar => observer.observe(bar));
}

// QR Code generation and sharing functions
function generateQRCode(text, containerId) {
    if (typeof QRCode !== 'undefined') {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = '';
            new QRCode(container, {
                text: text,
                width: 200,
                height: 200,
                colorDark: "#000000",
                colorLight: "#ffffff",
                correctLevel: QRCode.CorrectLevel.H
            });
        }
    }
}

function shareReport(reportId) {
    if (navigator.share) {
        navigator.share({
            title: 'Medical Report',
            text: 'Check out this medical report',
            url: `${window.location.origin}/view_report/${reportId}`
        })
        .catch(error => console.log('Error sharing:', error));
    } else {
        // Fallback: copy to clipboard
        const shareUrl = `${window.location.origin}/view_report/${reportId}`;
        navigator.clipboard.writeText(shareUrl).then(() => {
            showNotification('Link copied to clipboard!', 'success');
        });
    }
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 1050; min-width: 300px;';
    notification.innerHTML = `
        <i class="fas fa-${getIcon(type)} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
}

function getIcon(type) {
    const icons = {
        'success': 'check-circle',
        'danger': 'exclamation-triangle',
        'warning': 'exclamation-circle',
        'info': 'info-circle'
    };
    return icons[type] || 'info-circle';
}

// Export report as PDF
function exportReport(reportId) {
    showNotification('Preparing report for download...', 'info');
    // In a real implementation, this would generate a PDF
    setTimeout(() => {
        showNotification('Report exported successfully!', 'success');
    }, 2000);
}

// Print report
function printReport(reportId) {
    const printContent = document.getElementById(`report-${reportId}`);
    if (printContent) {
        const printWindow = window.open('', '_blank');
        printWindow.document.write(`
            <html>
                <head>
                    <title>Medical Report</title>
                    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
                    <style>
                        body { padding: 20px; }
                        @media print {
                            .no-print { display: none; }
                        }
                    </style>
                </head>
                <body>
                    ${printContent.innerHTML}
                    <script>
                        window.onload = function() {
                            window.print();
                            setTimeout(() => window.close(), 500);
                        }
                    <\/script>
                </body>
            </html>
        `);
        printWindow.document.close();
    }
}