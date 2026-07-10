from flask import Flask, request, jsonify, send_from_directory, render_template_string
from flask_cors import CORS
import os
import uuid
import json
from datetime import datetime
import webbrowser
import threading
import time
import shutil
import mimetypes

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

UPLOAD_FOLDER = 'uploads'
TRASH_FOLDER = 'trash'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TRASH_FOLDER, exist_ok=True)

METADATA_FILE = 'file_metadata.json'
TRASH_METADATA_FILE = 'trash_metadata.json'
DOWNLOAD_HISTORY_FILE = 'download_history.json'

def load_metadata():
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_metadata(metadata):
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)

def load_trash_metadata():
    if os.path.exists(TRASH_METADATA_FILE):
        with open(TRASH_METADATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_trash_metadata(metadata):
    with open(TRASH_METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)

def load_download_history():
    if os.path.exists(DOWNLOAD_HISTORY_FILE):
        with open(DOWNLOAD_HISTORY_FILE, 'r') as f:
            return json.load(f)
    return []

def save_download_history(history):
    with open(DOWNLOAD_HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

file_metadata = load_metadata()
trash_metadata = load_trash_metadata()
download_history = load_download_history()

def format_size(bytes):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024.0:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.1f} PB"

def get_file_type(filename):
    """Determine file type for preview/display"""
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    image_exts = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp', 'ico']
    video_exts = ['mp4', 'webm', 'ogg', 'avi', 'mov', 'wmv', 'flv', 'mkv']
    audio_exts = ['mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a']
    pdf_exts = ['pdf']
    text_exts = ['txt', 'csv', 'log', 'md', 'json', 'xml', 'yaml', 'yml']
    code_exts = ['py', 'js', 'html', 'css', 'php', 'java', 'cpp', 'c', 'h', 'rb', 'go', 'rs', 'ts', 'jsx', 'tsx']
    doc_exts = ['doc', 'docx', 'odt']
    sheet_exts = ['xls', 'xlsx', 'ods']
    presentation_exts = ['ppt', 'pptx', 'odp']
    archive_exts = ['zip', 'rar', '7z', 'tar', 'gz']
    
    if ext in image_exts:
        return 'image'
    elif ext in video_exts:
        return 'video'
    elif ext in audio_exts:
        return 'audio'
    elif ext in pdf_exts:
        return 'pdf'
    elif ext in text_exts:
        return 'text'
    elif ext in code_exts:
        return 'code'
    elif ext in doc_exts:
        return 'document'
    elif ext in sheet_exts:
        return 'spreadsheet'
    elif ext in presentation_exts:
        return 'presentation'
    elif ext in archive_exts:
        return 'archive'
    else:
        return 'other'

@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>☁️ CloudDrive</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #f0f4f8;
                padding: 20px;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                padding: 30px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.08);
            }
            .header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-wrap: wrap;
                gap: 15px;
                padding-bottom: 20px;
                border-bottom: 2px solid #f1f5f9;
                margin-bottom: 25px;
            }
            .brand h1 { font-size: 1.8rem; color: #0f172a; }
            .brand span { color: #64748b; font-size: 0.9rem; }

            .tabs {
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
                margin-bottom: 20px;
            }
            .tab {
                padding: 10px 24px;
                border: none;
                background: #f1f5f9;
                border-radius: 30px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
                color: #64748b;
                font-size: 0.95rem;
            }
            .tab:hover { background: #e2e8f0; }
            .tab.active { background: #3b82f6; color: white; }
            .tab .badge {
                background: #ef4444;
                color: white;
                font-size: 0.7rem;
                padding: 1px 10px;
                border-radius: 20px;
                margin-left: 6px;
            }

            .stats {
                display: flex;
                gap: 20px;
                flex-wrap: wrap;
                margin-bottom: 20px;
            }
            .stat {
                background: #f8fafc;
                padding: 12px 24px;
                border-radius: 12px;
                border: 1px solid #e2e8f0;
            }
            .stat .num { font-size: 1.4rem; font-weight: 700; color: #0f172a; }
            .stat .label { font-size: 0.8rem; color: #94a3b8; }

            .search-box {
                display: flex;
                align-items: center;
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 50px;
                padding: 8px 18px;
                gap: 10px;
                margin-bottom: 20px;
            }
            .search-box input {
                border: none;
                outline: none;
                font-size: 0.95rem;
                width: 100%;
                background: transparent;
            }
            .search-box i { color: #94a3b8; }

            .upload-zone {
                border: 2px dashed #cbd5e1;
                border-radius: 16px;
                padding: 35px 20px;
                text-align: center;
                background: #fafcff;
                cursor: pointer;
                transition: all 0.3s;
                margin-bottom: 25px;
            }
            .upload-zone:hover { border-color: #3b82f6; background: #f0f7ff; }
            .upload-zone i { font-size: 2.8rem; color: #94a3b8; margin-bottom: 8px; }
            .upload-zone h3 { color: #0f172a; font-size: 1.1rem; }
            .upload-zone p { color: #94a3b8; font-size: 0.9rem; }
            .btn-upload {
                margin-top: 12px;
                background: linear-gradient(135deg, #3b82f6, #8b5cf6);
                color: white;
                border: none;
                padding: 10px 36px;
                border-radius: 50px;
                font-weight: 600;
                font-size: 0.95rem;
                cursor: pointer;
                box-shadow: 0 4px 16px rgba(59,130,246,0.3);
            }
            .btn-upload:hover { transform: translateY(-2px); }

            .progress-wrap {
                display: none;
                background: #f1f5f9;
                border-radius: 50px;
                padding: 8px 16px;
                align-items: center;
                gap: 14px;
                margin-bottom: 20px;
            }
            .progress-wrap.visible { display: flex; }
            .progress-bar { flex: 1; height: 6px; background: #e2e8f0; border-radius: 20px; overflow: hidden; }
            .progress-fill { height: 100%; width: 0%; background: linear-gradient(90deg, #3b82f6, #8b5cf6); border-radius: 20px; transition: width 0.4s; }
            .progress-text { font-weight: 700; color: #0f172a; min-width: 44px; text-align: right; }

            .files-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                gap: 16px;
            }
            .file-card {
                background: white;
                border: 1px solid #e9eef3;
                border-radius: 14px;
                padding: 18px;
                transition: all 0.3s;
                position: relative;
            }
            .file-card:hover { transform: translateY(-3px); box-shadow: 0 8px 24px rgba(0,0,0,0.06); }
            
            .file-icon-wrapper {
                display: flex;
                align-items: center;
                gap: 12px;
                margin-bottom: 8px;
            }
            .file-icon-wrapper .file-icon { font-size: 2.2rem; }
            .file-extension-badge {
                background: #f1f5f9;
                padding: 2px 12px;
                border-radius: 20px;
                font-size: 0.7rem;
                font-weight: 700;
                color: #475569;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                border: 1px solid #e2e8f0;
            }
            .file-type-label {
                font-size: 0.65rem;
                color: #94a3b8;
                text-transform: uppercase;
                letter-spacing: 0.3px;
                padding: 2px 10px;
                border-radius: 12px;
                background: #f8fafc;
                display: inline-block;
            }
            
            .file-card .file-name { 
                font-weight: 600; 
                color: #0f172a; 
                font-size: 0.95rem; 
                word-break: break-word;
                margin: 4px 0;
            }
            .file-card .file-meta { 
                color: #94a3b8; 
                font-size: 0.8rem; 
                margin: 4px 0 12px 0; 
            }
            .file-card .file-actions { 
                display: flex; 
                gap: 8px; 
                flex-wrap: wrap; 
            }
            .file-card .file-actions button {
                flex: 1;
                border: none;
                padding: 8px 0;
                border-radius: 30px;
                font-weight: 600;
                font-size: 0.8rem;
                cursor: pointer;
                transition: all 0.2s;
                min-width: 60px;
            }
            .btn-download { background: #eef2ff; color: #3b82f6; }
            .btn-download:hover { background: #3b82f6; color: white; }
            .btn-view { background: #f0fdf4; color: #22c55e; }
            .btn-view:hover { background: #22c55e; color: white; }
            .btn-delete { background: #fef2f2; color: #ef4444; }
            .btn-delete:hover { background: #ef4444; color: white; }
            .btn-restore { background: #dcfce7; color: #22c55e; }
            .btn-restore:hover { background: #22c55e; color: white; }

            .empty-state {
                grid-column: 1 / -1;
                text-align: center;
                padding: 50px 20px;
                color: #94a3b8;
            }
            .empty-state i { font-size: 3.5rem; color: #cbd5e1; display: block; margin-bottom: 12px; }

            .modal {
                display: none;
                position: fixed;
                inset: 0;
                background: rgba(0,0,0,0.4);
                backdrop-filter: blur(8px);
                align-items: center;
                justify-content: center;
                z-index: 1000;
                padding: 20px;
            }
            .modal.active { display: flex; }
            .modal-box {
                background: white;
                max-width: 380px;
                width: 100%;
                border-radius: 20px;
                padding: 30px;
                text-align: center;
            }
            .modal-box i { font-size: 2.8rem; margin-bottom: 10px; }
            .modal-box i.success { color: #22c55e; }
            .modal-box i.error { color: #ef4444; }
            .modal-box h3 { font-size: 1.2rem; color: #0f172a; margin-bottom: 6px; }
            .modal-box p { color: #64748b; margin-bottom: 18px; }
            .modal-box .btn-close {
                background: #0f172a;
                color: white;
                border: none;
                padding: 8px 40px;
                border-radius: 50px;
                font-weight: 600;
                font-size: 0.9rem;
                cursor: pointer;
            }
            .modal-box .btn-close:hover { background: #1e293b; }

            /* Viewer Modal */
            .viewer-modal {
                display: none;
                position: fixed;
                inset: 0;
                background: rgba(0,0,0,0.8);
                backdrop-filter: blur(8px);
                align-items: center;
                justify-content: center;
                z-index: 2000;
                padding: 20px;
            }
            .viewer-modal.active { display: flex; }
            .viewer-content {
                background: white;
                max-width: 900px;
                width: 100%;
                max-height: 90vh;
                border-radius: 20px;
                overflow: hidden;
                position: relative;
            }
            .viewer-header {
                padding: 15px 25px;
                border-bottom: 1px solid #e9eef3;
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: white;
                flex-wrap: wrap;
                gap: 10px;
            }
            .viewer-header .file-info-left {
                display: flex;
                align-items: center;
                gap: 12px;
                flex: 1;
                min-width: 0;
            }
            .viewer-header h3 {
                font-size: 1rem;
                color: #0f172a;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                max-width: 60%;
            }
            .viewer-header .viewer-extension {
                background: #f1f5f9;
                padding: 4px 14px;
                border-radius: 20px;
                font-size: 0.7rem;
                font-weight: 700;
                color: #475569;
                text-transform: uppercase;
                border: 1px solid #e2e8f0;
                white-space: nowrap;
            }
            .viewer-header .viewer-type {
                font-size: 0.7rem;
                color: #94a3b8;
                padding: 3px 12px;
                background: #f8fafc;
                border-radius: 12px;
                white-space: nowrap;
            }
            .viewer-header .btn-close-viewer {
                background: none;
                border: none;
                font-size: 1.8rem;
                cursor: pointer;
                color: #64748b;
                padding: 0 5px;
            }
            .viewer-header .btn-close-viewer:hover { color: #0f172a; }
            .viewer-body {
                padding: 20px;
                max-height: calc(90vh - 80px);
                overflow: auto;
                display: flex;
                align-items: center;
                justify-content: center;
                background: #f8fafc;
                min-height: 300px;
            }
            .viewer-body img {
                max-width: 100%;
                max-height: 70vh;
                object-fit: contain;
            }
            .viewer-body video {
                max-width: 100%;
                max-height: 70vh;
            }
            .viewer-body audio {
                width: 100%;
                padding: 20px;
            }
            .viewer-body iframe {
                width: 100%;
                height: 70vh;
                border: none;
            }
            .viewer-body .text-content {
                width: 100%;
                max-height: 70vh;
                overflow: auto;
                background: white;
                padding: 20px;
                border-radius: 10px;
                font-family: 'Courier New', monospace;
                font-size: 0.9rem;
                white-space: pre-wrap;
                word-wrap: break-word;
            }
            .viewer-body .file-info {
                text-align: center;
                padding: 40px;
            }
            .viewer-body .file-info i {
                font-size: 4rem;
                color: #94a3b8;
            }
            .viewer-body .file-info p {
                margin-top: 10px;
                color: #64748b;
            }
            .viewer-body .file-info .file-detail {
                background: #f8fafc;
                padding: 10px 20px;
                border-radius: 10px;
                display: inline-block;
                margin-top: 10px;
            }
            .viewer-body .file-info .file-detail span {
                display: inline-block;
                margin: 0 8px;
                color: #0f172a;
                font-weight: 600;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="brand">
                    <h1>☁️ CloudDrive</h1>
                    <span>Personal Cloud Storage</span>
                </div>
            </div>

            <div class="tabs">
                <button class="tab active" id="tabAll">📁 All Files</button>
                <button class="tab" id="tabRecent">🕐 Recent</button>
                <button class="tab" id="tabTrash">🗑️ Trash <span class="badge" id="trashCount">0</span></button>
            </div>

            <div class="stats">
                <div class="stat"><div class="num" id="totalFiles">0</div><div class="label">Total Files</div></div>
                <div class="stat"><div class="num" id="totalSize">0 B</div><div class="label">Storage Used</div></div>
                <div class="stat"><div class="num" id="recentCount">0</div><div class="label">Recent Files</div></div>
            </div>

            <div class="search-box">
                <i class="fas fa-search"></i>
                <input type="text" id="searchInput" placeholder="Search files by name or extension...">
            </div>

            <div class="upload-zone" id="uploadZone">
                <i class="fas fa-cloud-upload-alt"></i>
                <h3>Drop files here or click to upload</h3>
                <p>Any file type · Up to 100 GB per file</p>
                <button class="btn-upload" id="uploadBtn"><i class="fas fa-plus-circle"></i> Choose Files</button>
                <input type="file" id="fileInput" multiple style="display:none;">
            </div>

            <div class="progress-wrap" id="progressWrap">
                <span id="progressFileName">Uploading...</span>
                <div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div>
                <span class="progress-text" id="progressText">0%</span>
            </div>

            <div class="files-grid" id="filesGrid">
                <div class="empty-state">
                    <i class="fas fa-inbox"></i>
                    <h4>No files yet</h4>
                    <p>Upload your first file to get started</p>
                </div>
            </div>
        </div>

        <!-- Notification Modal -->
        <div class="modal" id="modal">
            <div class="modal-box">
                <i class="fas fa-check-circle success" id="modalIcon"></i>
                <h3 id="modalTitle">Success</h3>
                <p id="modalMessage">Action completed successfully.</p>
                <button class="btn-close" id="modalCloseBtn">Got it</button>
            </div>
        </div>

        <!-- File Viewer Modal -->
        <div class="viewer-modal" id="viewerModal">
            <div class="viewer-content">
                <div class="viewer-header">
                    <div class="file-info-left">
                        <h3 id="viewerFileName">File Viewer</h3>
                        <span class="viewer-extension" id="viewerExtension">.ext</span>
                        <span class="viewer-type" id="viewerType">Type</span>
                    </div>
                    <button class="btn-close-viewer" id="viewerCloseBtn">&times;</button>
                </div>
                <div class="viewer-body" id="viewerBody">
                    <div class="file-info">
                        <i class="fas fa-file"></i>
                        <p>Loading file...</p>
                    </div>
                </div>
            </div>
        </div>

        <script>
        // ===== SIMPLE WORKING JAVASCRIPT =====
        console.log('🚀 CloudDrive loaded!');

        // ===== DOM ELEMENTS =====
        const tabAll = document.getElementById('tabAll');
        const tabRecent = document.getElementById('tabRecent');
        const tabTrash = document.getElementById('tabTrash');
        const searchInput = document.getElementById('searchInput');
        const uploadZone = document.getElementById('uploadZone');
        const uploadBtn = document.getElementById('uploadBtn');
        const fileInput = document.getElementById('fileInput');
        const filesGrid = document.getElementById('filesGrid');
        const totalFiles = document.getElementById('totalFiles');
        const totalSize = document.getElementById('totalSize');
        const recentCount = document.getElementById('recentCount');
        const trashCount = document.getElementById('trashCount');
        const progressWrap = document.getElementById('progressWrap');
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        const progressFileName = document.getElementById('progressFileName');
        const modal = document.getElementById('modal');
        const modalIcon = document.getElementById('modalIcon');
        const modalTitle = document.getElementById('modalTitle');
        const modalMessage = document.getElementById('modalMessage');
        const modalCloseBtn = document.getElementById('modalCloseBtn');
        const viewerModal = document.getElementById('viewerModal');
        const viewerBody = document.getElementById('viewerBody');
        const viewerFileName = document.getElementById('viewerFileName');
        const viewerExtension = document.getElementById('viewerExtension');
        const viewerType = document.getElementById('viewerType');
        const viewerCloseBtn = document.getElementById('viewerCloseBtn');

        let allFiles = [];
        let trashFiles = [];
        let downloadHistory = [];
        let currentView = 'all';

        // ===== FORMAT BYTES =====
        function formatBytes(bytes) {
            if (bytes === 0) return '0 B';
            const units = ['B', 'KB', 'MB', 'GB', 'TB'];
            const k = 1024;
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return (bytes / Math.pow(k, i)).toFixed(1) + ' ' + units[i];
        }

        // ===== GET FILE EXTENSION =====
        function getFileExtension(filename) {
            if (!filename) return '';
            const parts = filename.split('.');
            return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : '';
        }

        // ===== GET FILE TYPE NAME =====
        function getFileTypeName(ext) {
            const types = {
                'jpg': 'Image', 'jpeg': 'Image', 'png': 'Image', 'gif': 'Image', 
                'bmp': 'Image', 'svg': 'Image', 'webp': 'Image', 'ico': 'Image',
                'mp4': 'Video', 'webm': 'Video', 'ogg': 'Video', 'avi': 'Video',
                'mov': 'Video', 'wmv': 'Video', 'flv': 'Video', 'mkv': 'Video',
                'mp3': 'Audio', 'wav': 'Audio', 'flac': 'Audio', 'aac': 'Audio',
                'm4a': 'Audio', 'pdf': 'PDF Document',
                'txt': 'Text', 'csv': 'CSV', 'log': 'Log', 'md': 'Markdown',
                'json': 'JSON', 'xml': 'XML', 'yaml': 'YAML', 'yml': 'YAML',
                'py': 'Python', 'js': 'JavaScript', 'html': 'HTML', 'css': 'CSS',
                'php': 'PHP', 'java': 'Java', 'cpp': 'C++', 'c': 'C',
                'h': 'Header', 'rb': 'Ruby', 'go': 'Go', 'rs': 'Rust',
                'ts': 'TypeScript', 'jsx': 'React JSX', 'tsx': 'React TSX',
                'doc': 'Word Doc', 'docx': 'Word Doc', 'odt': 'OpenDocument',
                'xls': 'Excel', 'xlsx': 'Excel', 'ods': 'OpenDocument',
                'ppt': 'PowerPoint', 'pptx': 'PowerPoint', 'odp': 'OpenDocument',
                'zip': 'Archive', 'rar': 'Archive', '7z': 'Archive',
                'tar': 'Archive', 'gz': 'Archive'
            };
            return types[ext] || 'File';
        }

        // ===== MODAL =====
        function showModal(icon, title, message, isSuccess) {
            modalIcon.className = 'fas ' + icon + (isSuccess ? ' success' : ' error');
            modalTitle.textContent = title;
            modalMessage.textContent = message;
            modal.classList.add('active');
        }

        modalCloseBtn.onclick = function() {
            modal.classList.remove('active');
        };

        modal.onclick = function(e) {
            if (e.target === this) {
                modal.classList.remove('active');
            }
        };

        // ===== VIEWER =====
        function openViewer(fileId) {
            console.log('Opening viewer for:', fileId);
            const file = allFiles.find(f => f.file_id === fileId);
            if (!file) {
                showModal('fa-exclamation-circle', 'Error', 'File not found', false);
                return;
            }

            const ext = getFileExtension(file.original_name);
            const typeName = getFileTypeName(ext);
            
            viewerFileName.textContent = file.original_name;
            viewerExtension.textContent = '.' + ext;
            viewerType.textContent = typeName;
            viewerModal.classList.add('active');
            
            const viewUrl = '/api/view/' + fileId;
            
            let html = '';
            
            // Image files
            if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp', 'ico'].includes(ext)) {
                html = `<img src="${viewUrl}" alt="${file.original_name}" loading="lazy">`;
            }
            // Video files
            else if (['mp4', 'webm', 'ogg', 'avi', 'mov', 'wmv', 'flv', 'mkv'].includes(ext)) {
                html = `<video controls autoplay><source src="${viewUrl}" type="video/${ext}">Your browser doesn't support video playback.</video>`;
            }
            // Audio files
            else if (['mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a'].includes(ext)) {
                html = `<audio controls autoplay><source src="${viewUrl}" type="audio/${ext}">Your browser doesn't support audio playback.</audio>`;
            }
            // PDF files
            else if (ext === 'pdf') {
                html = `<iframe src="${viewUrl}#toolbar=1" allowfullscreen></iframe>`;
            }
            // Text and code files
            else if (['txt', 'csv', 'log', 'md', 'json', 'xml', 'yaml', 'yml', 'py', 'js', 'html', 'css', 'php', 'java', 'cpp', 'c', 'h', 'rb', 'go', 'rs', 'ts', 'jsx', 'tsx'].includes(ext)) {
                fetch(viewUrl)
                    .then(res => res.text())
                    .then(text => {
                        viewerBody.innerHTML = `<pre class="text-content">${escapeHtml(text)}</pre>`;
                    })
                    .catch(() => {
                        viewerBody.innerHTML = `<div class="file-info"><i class="fas fa-exclamation-circle"></i><p>Failed to load file content</p></div>`;
                    });
                return;
            }
            // Other files
            else {
                html = `
                    <div class="file-info">
                        <i class="fas fa-file"></i>
                        <p><strong>${file.original_name}</strong></p>
                        <div class="file-detail">
                            <span>📄 ${ext.toUpperCase()}</span>
                            <span>📦 ${formatBytes(file.size)}</span>
                            <span>📅 ${new Date(file.upload_date).toLocaleString()}</span>
                        </div>
                        <p style="margin-top: 15px; font-size: 0.9rem; color: #94a3b8;">
                            <i class="fas fa-info-circle"></i> 
                            This file type cannot be previewed directly.
                            <br><button class="btn-download" style="padding: 10px 30px; margin-top: 10px;" onclick="downloadFile('${fileId}')">
                                <i class="fas fa-download"></i> Download
                            </button>
                        </p>
                    </div>
                `;
            }
            
            viewerBody.innerHTML = html;
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        viewerCloseBtn.onclick = function() {
            viewerModal.classList.remove('active');
            viewerBody.innerHTML = '<div class="file-info"><i class="fas fa-file"></i><p>Loading file...</p></div>';
        };

        viewerModal.onclick = function(e) {
            if (e.target === this) {
                viewerModal.classList.remove('active');
                viewerBody.innerHTML = '<div class="file-info"><i class="fas fa-file"></i><p>Loading file...</p></div>';
            }
        };

        // ===== TABS =====
        function switchTab(view) {
            console.log('Switching to tab:', view);
            currentView = view;
            
            tabAll.classList.remove('active');
            tabRecent.classList.remove('active');
            tabTrash.classList.remove('active');
            
            if (view === 'all') tabAll.classList.add('active');
            else if (view === 'recent') tabRecent.classList.add('active');
            else if (view === 'trash') tabTrash.classList.add('active');
            
            loadFiles();
        }

        tabAll.onclick = function() { switchTab('all'); };
        tabRecent.onclick = function() { switchTab('recent'); };
        tabTrash.onclick = function() { switchTab('trash'); };

        // ===== UPLOAD =====
        uploadBtn.onclick = function(e) {
            e.stopPropagation();
            console.log('Upload button clicked');
            fileInput.click();
        };

        uploadZone.onclick = function() {
            console.log('Upload zone clicked');
            fileInput.click();
        };

        uploadZone.ondragover = function(e) {
            e.preventDefault();
            this.style.borderColor = '#3b82f6';
        };

        uploadZone.ondragleave = function(e) {
            e.preventDefault();
            this.style.borderColor = '#cbd5e1';
        };

        uploadZone.ondrop = function(e) {
            e.preventDefault();
            this.style.borderColor = '#cbd5e1';
            if (e.dataTransfer.files.length) {
                console.log('Files dropped:', e.dataTransfer.files.length);
                handleFiles(e.dataTransfer.files);
            }
        };

        fileInput.onchange = function(e) {
            if (this.files.length) {
                console.log('Files selected:', this.files.length);
                handleFiles(this.files);
            }
            this.value = '';
        };

        // ===== SEARCH =====
        searchInput.oninput = function() {
            console.log('Searching:', this.value);
            loadFiles();
        };

        // ===== HANDLE FILES UPLOAD =====
        async function handleFiles(files) {
            if (!files.length) return;
            console.log('Handling upload of', files.length, 'files');
            
            progressWrap.classList.add('visible');
            let uploaded = 0;
            const total = files.length;

            for (let file of files) {
                progressFileName.textContent = file.name;
                const formData = new FormData();
                formData.append('file', file);

                try {
                    const resp = await fetch('/api/upload', { method: 'POST', body: formData });
                    const data = await resp.json();
                    console.log('Upload response:', data);
                    
                    if (resp.ok) {
                        uploaded++;
                        const pct = Math.round((uploaded / total) * 100);
                        progressFill.style.width = pct + '%';
                        progressText.textContent = pct + '%';
                        if (uploaded === total) {
                            showModal('fa-check-circle', 'Upload Complete!', 'Successfully uploaded ' + total + ' file(s).', true);
                        }
                        loadFiles();
                    } else {
                        showModal('fa-exclamation-circle', 'Upload Failed', data.error || 'Something went wrong.', false);
                        break;
                    }
                } catch (err) {
                    console.error('Upload error:', err);
                    showModal('fa-exclamation-circle', 'Error', err.message || 'Network error.', false);
                    break;
                }
            }

            setTimeout(() => {
                progressWrap.classList.remove('visible');
                progressFill.style.width = '0%';
                progressText.textContent = '0%';
            }, 1200);
        }

        // ===== LOAD FILES =====
        async function loadFiles() {
            console.log('Loading files...');
            try {
                const resp = await fetch('/api/files');
                const data = await resp.json();
                if (resp.ok) {
                    allFiles = data.files || [];
                    console.log('Loaded', allFiles.length, 'files');
                }

                const trashResp = await fetch('/api/trash-files');
                const trashData = await trashResp.json();
                if (trashResp.ok) {
                    trashFiles = trashData.files || [];
                    console.log('Loaded', trashFiles.length, 'trash files');
                }

                const historyResp = await fetch('/api/download-history');
                const historyData = await historyResp.json();
                downloadHistory = historyData.history || [];

                renderFiles();
                updateStats();
            } catch (err) {
                console.error('Load error:', err);
            }
        }

        function renderFiles() {
            console.log('Rendering files for view:', currentView);
            let files = [];
            const searchTerm = searchInput.value.toLowerCase();

            if (currentView === 'trash') {
                files = trashFiles.slice();
            } else {
                files = allFiles.slice();
                if (currentView === 'recent') {
                    const sevenDaysAgo = new Date();
                    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
                    files = files.filter(f => new Date(f.upload_date) >= sevenDaysAgo);
                }
            }

            if (searchTerm) {
                files = files.filter(f => {
                    const name = f.original_name.toLowerCase();
                    const ext = getFileExtension(f.original_name);
                    return name.includes(searchTerm) || ext.includes(searchTerm);
                });
            }

            if (!files || files.length === 0) {
                filesGrid.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-inbox"></i>
                        <h4>No files found</h4>
                        <p>${searchTerm ? 'Try a different search term' : 'Upload your first file to get started'}</p>
                    </div>
                `;
                return;
            }

            let html = '';
            files.forEach(file => {
                const ext = getFileExtension(file.original_name);
                const typeName = getFileTypeName(ext);
                
                const icons = {
                    pdf: 'fa-file-pdf', doc: 'fa-file-word', docx: 'fa-file-word',
                    xls: 'fa-file-excel', xlsx: 'fa-file-excel',
                    txt: 'fa-file-alt', csv: 'fa-file-csv',
                    png: 'fa-file-image', jpg: 'fa-file-image', jpeg: 'fa-file-image', 
                    gif: 'fa-file-image', svg: 'fa-file-image', webp: 'fa-file-image',
                    mp4: 'fa-file-video', webm: 'fa-file-video', avi: 'fa-file-video', mov: 'fa-file-video',
                    mp3: 'fa-file-audio', wav: 'fa-file-audio', ogg: 'fa-file-audio',
                    zip: 'fa-file-archive', rar: 'fa-file-archive', '7z': 'fa-file-archive', 
                    tar: 'fa-file-archive', gz: 'fa-file-archive',
                    py: 'fa-file-code', js: 'fa-file-code', html: 'fa-file-code', 
                    css: 'fa-file-code', java: 'fa-file-code', cpp: 'fa-file-code'
                };
                const icon = icons[ext] || 'fa-file';
                const colors = {
                    pdf: '#ef4444', doc: '#3b82f6', docx: '#3b82f6',
                    xls: '#22c55e', xlsx: '#22c55e',
                    zip: '#f59e0b', rar: '#f59e0b', '7z': '#f59e0b',
                    py: '#8b5cf6', js: '#8b5cf6', html: '#8b5cf6',
                    png: '#ec4899', jpg: '#ec4899', jpeg: '#ec4899', gif: '#ec4899',
                    mp4: '#8b5cf6', webm: '#8b5cf6',
                    mp3: '#06b6d4', wav: '#06b6d4',
                    txt: '#64748b', csv: '#64748b'
                };
                const color = colors[ext] || '#64748b';

                const isTrash = currentView === 'trash';
                const canView = !isTrash && ['jpg','jpeg','png','gif','bmp','svg','webp','ico',
                    'mp4','webm','ogg','avi','mov','wmv','flv','mkv',
                    'mp3','wav','ogg','flac','aac','m4a',
                    'pdf','txt','csv','log','md','json','xml','yaml','yml',
                    'py','js','html','css','php','java','cpp','c','h','rb','go','rs','ts','jsx','tsx'
                ].includes(ext);

                html += `
                    <div class="file-card">
                        <div class="file-icon-wrapper">
                            <div class="file-icon" style="color:${color}"><i class="fas ${icon}"></i></div>
                            <span class="file-extension-badge">${ext || 'file'}</span>
                            <span class="file-type-label">${typeName}</span>
                        </div>
                        <div class="file-name">${file.original_name}</div>
                        <div class="file-meta">${formatBytes(file.size)} · ${new Date(file.upload_date).toLocaleDateString()}</div>
                        <div class="file-actions">
                            ${isTrash ? `
                                <button class="btn-restore" onclick="restoreFile('${file.file_id}')"><i class="fas fa-undo"></i> Restore</button>
                                <button class="btn-delete" onclick="deletePermanent('${file.file_id}')"><i class="fas fa-trash"></i> Delete</button>
                            ` : `
                                ${canView ? `<button class="btn-view" onclick="openViewer('${file.file_id}')"><i class="fas fa-eye"></i> View</button>` : ''}
                                <button class="btn-download" onclick="downloadFile('${file.file_id}')"><i class="fas fa-download"></i> Download</button>
                                <button class="btn-delete" onclick="moveToTrash('${file.file_id}')"><i class="fas fa-trash"></i> Delete</button>
                            `}
                        </div>
                    </div>
                `;
            });

            filesGrid.innerHTML = html;
        }

        function updateStats() {
            totalFiles.textContent = allFiles.length;
            trashCount.textContent = trashFiles.length;
            const total = allFiles.reduce((sum, f) => sum + (f.size || 0), 0);
            totalSize.textContent = formatBytes(total);
            const sevenDaysAgo = new Date();
            sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
            const recent = allFiles.filter(f => new Date(f.upload_date) >= sevenDaysAgo);
            recentCount.textContent = recent.length;
        }

        // ===== DOWNLOAD =====
        async function downloadFile(fileId) {
            console.log('Downloading file:', fileId);
            try {
                const resp = await fetch('/api/download/' + fileId);
                if (!resp.ok) {
                    const data = await resp.json();
                    showModal('fa-exclamation-circle', 'Download Failed', data.error || 'File not found', false);
                    return;
                }

                await fetch('/api/download-history', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ file_id: fileId })
                });

                const blob = await resp.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                const cd = resp.headers.get('content-disposition');
                let name = 'file';
                if (cd) {
                    const match = cd.match(/filename[^;=\\n]*=((['"]).*?\\2|[^;\\n]*)/);
                    if (match && match[1]) name = match[1].replace(/['"]/g, '');
                }
                a.download = name;
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(url);
                showModal('fa-check-circle', 'Download Started', 'File "' + name + '" is being downloaded.', true);
                loadFiles();
            } catch (err) {
                console.error('Download error:', err);
                showModal('fa-exclamation-circle', 'Error', 'Failed to download file.', false);
            }
        }

        // ===== MOVE TO TRASH =====
        async function moveToTrash(fileId) {
            console.log('Moving to trash:', fileId);
            if (!confirm('Move this file to trash?')) return;
            try {
                const resp = await fetch('/api/move-to-trash/' + fileId, { method: 'POST' });
                if (resp.ok) {
                    showModal('fa-check-circle', 'Moved to Trash', 'File moved to trash successfully.', true);
                    loadFiles();
                } else {
                    const data = await resp.json();
                    showModal('fa-exclamation-circle', 'Error', data.error || 'Could not move file to trash.', false);
                }
            } catch (err) {
                console.error('Move to trash error:', err);
                showModal('fa-exclamation-circle', 'Error', 'Network error.', false);
            }
        }

        // ===== RESTORE =====
        async function restoreFile(fileId) {
            console.log('Restoring file:', fileId);
            try {
                const resp = await fetch('/api/restore/' + fileId, { method: 'POST' });
                if (resp.ok) {
                    showModal('fa-check-circle', 'Restored', 'File restored successfully.', true);
                    loadFiles();
                } else {
                    const data = await resp.json();
                    showModal('fa-exclamation-circle', 'Error', data.error || 'Could not restore file.', false);
                }
            } catch (err) {
                console.error('Restore error:', err);
                showModal('fa-exclamation-circle', 'Error', 'Network error.', false);
            }
        }

        // ===== DELETE PERMANENT =====
        async function deletePermanent(fileId) {
            console.log('Deleting permanently:', fileId);
            if (!confirm('Delete this file permanently? This cannot be undone!')) return;
            try {
                const resp = await fetch('/api/delete-permanent/' + fileId, { method: 'DELETE' });
                if (resp.ok) {
                    showModal('fa-check-circle', 'Deleted', 'File permanently deleted.', true);
                    loadFiles();
                } else {
                    const data = await resp.json();
                    showModal('fa-exclamation-circle', 'Error', data.error || 'Could not delete file.', false);
                }
            } catch (err) {
                console.error('Delete permanent error:', err);
                showModal('fa-exclamation-circle', 'Error', 'Network error.', false);
            }
        }

        // ===== INIT =====
        console.log('Loading initial files...');
        loadFiles();
        console.log('✅ CloudDrive ready!');
        </script>
    </body>
    </html>
    ''')

# ===== API ENDPOINTS =====

@app.route('/api/files', methods=['GET', 'OPTIONS'])
def get_files():
    if request.method == 'OPTIONS':
        return '', 200
    files = []
    for file_id, metadata in file_metadata.items():
        file_path = os.path.join(UPLOAD_FOLDER, metadata['filename'])
        if os.path.exists(file_path):
            metadata['size'] = os.path.getsize(file_path)
            metadata['id'] = file_id
            files.append(metadata)
    files.sort(key=lambda x: x['upload_date'], reverse=True)
    return jsonify({'files': files})

@app.route('/api/trash-files', methods=['GET', 'OPTIONS'])
def get_trash_files():
    if request.method == 'OPTIONS':
        return '', 200
    files = []
    for file_id, metadata in trash_metadata.items():
        file_path = os.path.join(TRASH_FOLDER, metadata['filename'])
        if os.path.exists(file_path):
            metadata['size'] = os.path.getsize(file_path)
            metadata['id'] = file_id
            files.append(metadata)
    files.sort(key=lambda x: x['upload_date'], reverse=True)
    return jsonify({'files': files})

@app.route('/api/download-history', methods=['GET', 'POST', 'OPTIONS'])
def handle_download_history():
    global download_history
    if request.method == 'OPTIONS':
        return '', 200
    if request.method == 'GET':
        return jsonify({'history': download_history})
    if request.method == 'POST':
        data = request.json
        file_id = data.get('file_id')
        if file_id and file_id not in download_history:
            download_history.append(file_id)
            save_download_history(download_history)
        return jsonify({'history': download_history})

@app.route('/api/upload', methods=['POST', 'OPTIONS'])
def upload_file():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        file_id = str(uuid.uuid4())
        original_filename = file.filename
        unique_filename = f"{file_id}_{original_filename}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(file_path)
        file_metadata[file_id] = {
            'filename': unique_filename,
            'original_name': original_filename,
            'upload_date': datetime.now().isoformat(),
            'size': os.path.getsize(file_path),
            'file_id': file_id
        }
        save_metadata(file_metadata)
        return jsonify({'message': 'File uploaded successfully', 'file_id': file_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/view/<file_id>', methods=['GET', 'OPTIONS'])
def view_file(file_id):
    """Stream file for viewing in browser"""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        if file_id in file_metadata:
            metadata = file_metadata[file_id]
            folder = UPLOAD_FOLDER
        elif file_id in trash_metadata:
            metadata = trash_metadata[file_id]
            folder = TRASH_FOLDER
        else:
            return jsonify({'error': 'File not found'}), 404
        
        file_path = os.path.join(folder, metadata['filename'])
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found on server'}), 404
        
        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(metadata['original_name'])
        if not mime_type:
            mime_type = 'application/octet-stream'
        
        return send_from_directory(
            folder, 
            metadata['filename'], 
            as_attachment=False,
            mimetype=mime_type
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<file_id>', methods=['GET', 'OPTIONS'])
def download_file(file_id):
    if request.method == 'OPTIONS':
        return '', 200
    try:
        if file_id in file_metadata:
            metadata = file_metadata[file_id]
            folder = UPLOAD_FOLDER
        elif file_id in trash_metadata:
            metadata = trash_metadata[file_id]
            folder = TRASH_FOLDER
        else:
            return jsonify({'error': 'File not found'}), 404
        file_path = os.path.join(folder, metadata['filename'])
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found on server'}), 404
        return send_from_directory(folder, metadata['filename'], as_attachment=True, download_name=metadata['original_name'])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/move-to-trash/<file_id>', methods=['POST', 'OPTIONS'])
def move_to_trash(file_id):
    if request.method == 'OPTIONS':
        return '', 200
    try:
        if file_id not in file_metadata:
            return jsonify({'error': 'File not found'}), 404
        metadata = file_metadata[file_id]
        source_path = os.path.join(UPLOAD_FOLDER, metadata['filename'])
        if not os.path.exists(source_path):
            return jsonify({'error': 'File not found on server'}), 404
        trash_path = os.path.join(TRASH_FOLDER, metadata['filename'])
        shutil.move(source_path, trash_path)
        trash_metadata[file_id] = metadata
        save_trash_metadata(trash_metadata)
        del file_metadata[file_id]
        save_metadata(file_metadata)
        return jsonify({'message': 'File moved to trash'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/restore/<file_id>', methods=['POST', 'OPTIONS'])
def restore_file(file_id):
    if request.method == 'OPTIONS':
        return '', 200
    try:
        if file_id not in trash_metadata:
            return jsonify({'error': 'File not found in trash'}), 404
        metadata = trash_metadata[file_id]
        trash_path = os.path.join(TRASH_FOLDER, metadata['filename'])
        if not os.path.exists(trash_path):
            return jsonify({'error': 'File not found in trash'}), 404
        restore_path = os.path.join(UPLOAD_FOLDER, metadata['filename'])
        shutil.move(trash_path, restore_path)
        file_metadata[file_id] = metadata
        save_metadata(file_metadata)
        del trash_metadata[file_id]
        save_trash_metadata(trash_metadata)
        return jsonify({'message': 'File restored successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete-permanent/<file_id>', methods=['DELETE', 'OPTIONS'])
def delete_permanent(file_id):
    if request.method == 'OPTIONS':
        return '', 200
    try:
        if file_id in trash_metadata:
            metadata = trash_metadata[file_id]
            file_path = os.path.join(TRASH_FOLDER, metadata['filename'])
            if os.path.exists(file_path):
                os.remove(file_path)
            del trash_metadata[file_id]
            save_trash_metadata(trash_metadata)
            if file_id in download_history:
                download_history.remove(file_id)
                save_download_history(download_history)
            return jsonify({'message': 'File permanently deleted'}), 200
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        print("=" * 60)
        print("☁️  CloudDrive  —  Professional Cloud Storage")
        print("=" * 60)
        print("📁 Server: http://localhost:5000")
        print("💾 Max file size: 100 GB per file")
        print("🗑️  Trash feature enabled")
        print("👁️  File viewer enabled (images, videos, audio, PDF, text, code)")
        print("📋 File extensions and types are displayed")
        print("🌐 Opening browser automatically...")
        print("🔄 Press Ctrl+C to stop the server")
        print("=" * 60)

        def open_browser():
            time.sleep(1.5)
            webbrowser.open("http://localhost:5000")

        threading.Thread(target=open_browser, daemon=True).start()

    app.run(debug=True, host='0.0.0.0', port=5000)