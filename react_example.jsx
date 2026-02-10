// React Frontend Integration Example
// This file demonstrates how to use the Decentralized Storage Gateway API

import React, { useState, useEffect } from 'react';

const API_BASE_URL = 'http://localhost:8000';

// ============================================================================
// 1. Upload File Component
// ============================================================================
function FileUploader() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);

  const handleFileSelect = (event) => {
    setSelectedFile(event.target.files[0]);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploading(true);
    setUploadStatus(null);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      const response = await fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();

      if (response.ok) {
        setUploadStatus({
          type: 'success',
          message: `✓ ${result.filename} uploaded successfully!`,
          details: result
        });
      } else {
        setUploadStatus({
          type: 'error',
          message: `✗ Upload failed: ${result.detail}`
        });
      }
    } catch (error) {
      setUploadStatus({
        type: 'error',
        message: `✗ Network error: ${error.message}`
      });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="file-uploader">
      <h2>Upload File</h2>
      <input type="file" onChange={handleFileSelect} />
      <button onClick={handleUpload} disabled={!selectedFile || uploading}>
        {uploading ? 'Uploading...' : 'Upload'}
      </button>
      
      {uploadStatus && (
        <div className={`status ${uploadStatus.type}`}>
          <p>{uploadStatus.message}</p>
          {uploadStatus.details && (
            <div className="details">
              <p>Shards: {uploadStatus.details.shards_distributed}</p>
              <p>Recovery Threshold: {uploadStatus.details.recovery_threshold}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}


// ============================================================================
// 2. File List Component
// ============================================================================
function FileList() {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadFiles();
  }, []);

  const loadFiles = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/files`);
      const result = await response.json();

      if (response.ok) {
        setFiles(result.files);
      } else {
        setError(result.detail);
      }
    } catch (err) {
      setError(`Network error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = (filename) => {
    // Trigger download
    window.location.href = `${API_BASE_URL}/download/${filename}`;
  };

  if (loading) return <div>Loading files...</div>;
  if (error) return <div className="error">Error: {error}</div>;

  return (
    <div className="file-list">
      <h2>Stored Files ({files.length})</h2>
      <button onClick={loadFiles}>Refresh</button>
      
      <table>
        <thead>
          <tr>
            <th>Filename</th>
            <th>Size</th>
            <th>Upload Date</th>
            <th>Shards</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {files.map((file, index) => (
            <tr key={index}>
              <td>{file.filename}</td>
              <td>{formatBytes(file.size)}</td>
              <td>{new Date(file.upload_date).toLocaleString()}</td>
              <td>{file.shards_required}/{file.shards_total}</td>
              <td>
                <button onClick={() => handleDownload(file.filename)}>
                  Download
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}


// ============================================================================
// 3. System Health Dashboard Component
// ============================================================================
function HealthDashboard() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadHealth();
    // Refresh every 10 seconds
    const interval = setInterval(loadHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  const loadHealth = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      const result = await response.json();
      
      if (response.ok) {
        setHealth(result);
      }
    } catch (err) {
      console.error('Health check failed:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Checking system health...</div>;
  if (!health) return <div>Unable to load health status</div>;

  const getStatusColor = (status) => {
    switch (status) {
      case 'optimal': return 'green';
      case 'degraded': return 'orange';
      case 'critical': return 'red';
      default: return 'gray';
    }
  };

  return (
    <div className="health-dashboard">
      <h2>System Health</h2>
      
      <div className="system-status" style={{
        backgroundColor: getStatusColor(health.system_status),
        padding: '20px',
        borderRadius: '8px',
        color: 'white'
      }}>
        <h3>Status: {health.system_status.toUpperCase()}</h3>
        <p>Nodes Online: {health.nodes_online}/{health.nodes_total}</p>
        <p>Can Store: {health.capabilities.can_store_new_files ? '✓ Yes' : '✗ No'}</p>
        <p>Can Retrieve: {health.capabilities.can_retrieve_files ? '✓ Yes' : '✗ No'}</p>
      </div>

      <div className="nodes-grid">
        {health.nodes.map((node, index) => (
          <div 
            key={index} 
            className={`node-card ${node.status}`}
            style={{
              border: `2px solid ${node.healthy ? 'green' : 'red'}`,
              padding: '10px',
              margin: '5px',
              borderRadius: '4px'
            }}
          >
            <h4>Node {index + 1}</h4>
            <p>{node.url}</p>
            <p className={`status ${node.status}`}>
              {node.status === 'online' ? '✓ Online' : '✗ Offline'}
            </p>
          </div>
        ))}
      </div>

      <p className="last-updated">
        Last updated: {new Date(health.timestamp).toLocaleTimeString()}
      </p>
    </div>
  );
}


// ============================================================================
// 4. Main App Component
// ============================================================================
function App() {
  return (
    <div className="app">
      <header>
        <h1>🔐 Decentralized Storage System</h1>
        <p>Secure, distributed file storage with encryption and erasure coding</p>
      </header>

      <main>
        <HealthDashboard />
        <FileUploader />
        <FileList />
      </main>

      <footer>
        <p>Built with React + FastAPI + Python StorageEngine</p>
        <p>Security: AES-128 encryption | Fault tolerance: k=3, m=5</p>
      </footer>
    </div>
  );
}


// ============================================================================
// Helper Functions
// ============================================================================
function formatBytes(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}


export default App;


// ============================================================================
// CSS Styling (add to your CSS file)
// ============================================================================
/*
.app {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  font-family: Arial, sans-serif;
}

header {
  text-align: center;
  margin-bottom: 40px;
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 8px;
}

.health-dashboard,
.file-uploader,
.file-list {
  margin-bottom: 30px;
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background: white;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.nodes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 10px;
  margin-top: 20px;
}

.status.success {
  color: green;
  padding: 10px;
  background: #d4edda;
  border-radius: 4px;
}

.status.error {
  color: red;
  padding: 10px;
  background: #f8d7da;
  border-radius: 4px;
}

button {
  padding: 10px 20px;
  margin: 5px;
  border: none;
  border-radius: 4px;
  background: #667eea;
  color: white;
  cursor: pointer;
  font-size: 14px;
}

button:hover:not(:disabled) {
  background: #5568d3;
}

button:disabled {
  background: #ccc;
  cursor: not-allowed;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 15px;
}

th, td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

th {
  background: #f8f9fa;
  font-weight: bold;
}

tr:hover {
  background: #f8f9fa;
}
*/
