import { useState } from 'react';
import { getPresignedUrl, submitPlateResult } from '../services/api';
import '../styles/ImageUpload.css';

export default function ImageUpload({ onResultReceived }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  /**
   * Handle file selection
   */
  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      setError('Please select an image file');
      return;
    }

    // Validate file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      setError('File size must be less than 10MB');
      return;
    }

    setSelectedFile(file);
    setError(null);

    // Create preview
    const reader = new FileReader();
    reader.onloadend = () => {
      setPreviewUrl(reader.result);
    };
    reader.readAsDataURL(file);
  };

  /**
   * Handle drag and drop
   */
  const handleDragOver = (e) => {
    e.preventDefault();
    e.currentTarget.classList.add('drag-over');
  };

  const handleDragLeave = (e) => {
    e.currentTarget.classList.remove('drag-over');
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.currentTarget.classList.remove('drag-over');

    const file = e.dataTransfer.files?.[0];
    if (file) {
      setSelectedFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreviewUrl(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  /**
   * Upload file and submit result
   */
  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a file');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      // Step 1: Get pre-signed URL
      console.log('Getting pre-signed URL...');
      const { uploadUrl } = await getPresignedUrl();

      // Step 2: Upload to S3 (or mock)
      console.log('Uploading to S3...');
      // For MVP, we'll mock this. In Phase 3, you'll actually upload to S3.

      // Step 3: Mock plate recognition result
      // In Phase 6B, this will call the real ECS inference API
      const mockResult = {
        vehicleId: 'ABC-1234',
        plateText: 'ABC-1234',
        confidence: 0.98,
        permitStatus: 'VALID',
        eventType: 'ENTRY'
      };

      // Step 4: Submit result to backend
      console.log('Submitting result...');
      await submitPlateResult(mockResult);

      setResult(mockResult);
      if (onResultReceived) {
        onResultReceived(mockResult);
      }

      // Clear form
      setSelectedFile(null);
      setPreviewUrl(null);
    } catch (err) {
      console.error('Upload error:', err);
      setError(err.message || 'Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="image-upload-container">
      <h2>Upload Vehicle Image</h2>

      {/* Drag and drop area */}
      <div
        className="drop-zone"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {previewUrl ? (
          <div className="preview">
            <img src={previewUrl} alt="Preview" />
            <p>{selectedFile?.name}</p>
          </div>
        ) : (
          <div className="drop-text">
            <p>Drag and drop your image here</p>
            <p>or</p>
            <label htmlFor="file-input" className="file-label">
              Click to select
            </label>
            <input
              id="file-input"
              type="file"
              accept="image/*"
              onChange={handleFileChange}
              disabled={uploading}
              style={{ display: 'none' }}
            />
          </div>
        )}
      </div>

      {/* Error message */}
      {error && <div className="error-message">{error}</div>}

      {/* Upload button */}
      <button
        onClick={handleUpload}
        disabled={!selectedFile || uploading}
        className="upload-button"
      >
        {uploading ? 'Uploading...' : 'Upload & Analyze'}
      </button>

      {/* Result */}
      {result && (
        <div className="result-card">
          <h3>Recognition Result</h3>
          <p><strong>Plate Text:</strong> {result.plateText}</p>
          <p><strong>Confidence:</strong> {(result.confidence * 100).toFixed(2)}%</p>
          <p><strong>Permit Status:</strong> {result.permitStatus}</p>
          <p><strong>Event Type:</strong> {result.eventType}</p>
        </div>
      )}
    </div>
  );
}
