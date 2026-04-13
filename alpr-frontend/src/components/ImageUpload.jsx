import { useState } from 'react';
import { getPresignedUrl, getPermitStatus, submitPlateResult, uploadImageToS3 } from '../services/api';
import '../styles/ImageUpload.css';

export default function ImageUpload({ onResultReceived }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  /**
   * Mock plate recognition
   * Simulates YOLO + OCR without real ML model
   * In Phase 6, replace this with real ECS inference service
   */
  const mockRecognizeImage = async (imageUrl) => {
    // Simulate inference delay (real YOLO takes 2-5 seconds)
    await new Promise(resolve => setTimeout(resolve, 2000));

    // Mock plates database - ONLY vehicles that exist in DynamoDB Permits table
    const mockPlates = [
      { plate: 'ABC-1234', confidence: 0.98 },
      { plate: 'XYZ-5678', confidence: 0.95 },
      { plate: 'DEF-9012', confidence: 0.92 },
    ];

    // Randomly select a plate from mock database
    const detected = mockPlates[Math.floor(Math.random() * mockPlates.length)];

    return {
      plateText: detected.plate,
      confidence: detected.confidence,
      imageUrl: imageUrl,
      timestamp: Date.now(),
      model: 'mock-yolo-v8'
    };
  };

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
   * Phase 4: Mock recognition flow (backend submission skipped temporarily)
   */
  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a file');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      // Step 1: Convert file to base64
      console.log('Step 1: Converting image to base64...');
      const reader = new FileReader();
      
      const base64Promise = new Promise((resolve, reject) => {
        reader.onload = () => {
          const base64String = reader.result.split(',')[1];
          resolve(base64String);
        };
        reader.onerror = reject;
        reader.readAsDataURL(selectedFile);
      });
      
      const base64Image = await base64Promise;
      console.log('✓ Image converted to base64');

      // Step 2: Upload file to S3 via Lambda
      console.log('Step 2: Uploading image to S3 via Lambda...');
      const s3Result = await uploadImageToS3(base64Image, selectedFile.name);
      const imageUrl = s3Result.imageUrl;
      console.log('✓ Image uploaded to S3:', imageUrl);

      // Step 3: Mock plate recognition
      console.log('Step 3: Running mock plate recognition (2 second simulation)...');
      const recognitionResult = await mockRecognizeImage(imageUrl);
      console.log('✓ Mock recognition result:', recognitionResult);

      // Step 4: Check permit status for detected plate
      console.log('Step 4: Checking permit status for', recognitionResult.plateText);
      const permitData = await getPermitStatus(recognitionResult.plateText);
      console.log('✓ Permit check result:', permitData);

      // Step 5: Display result to user
      console.log('Step 5: Displaying recognition result...');
      setResult({
        vehicleId: recognitionResult.plateText,
        plateText: recognitionResult.plateText,
        confidence: recognitionResult.confidence,
        permitStatus: permitData.permitStatus,
        eventType: 'ENTRY',
        owner: permitData.owner,
        expiryDate: permitData.expiryDate,
        imageUrl: imageUrl
      });

      if (onResultReceived) {
        onResultReceived({
          vehicleId: recognitionResult.plateText,
          plateText: recognitionResult.plateText,
          confidence: recognitionResult.confidence,
          permitStatus: permitData.permitStatus,
          eventType: 'ENTRY',
          imageUrl: imageUrl
        });
      }

      console.log('✓ Phase 4 complete - Full flow working!');

      // Clear form after successful submission
      setTimeout(() => {
        setSelectedFile(null);
        setPreviewUrl(null);
      }, 2000);

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
        {uploading ? 'Uploading & Analyzing...' : 'Upload & Analyze'}
      </button>

      {/* Result */}
      {result && (
        <div className="result-card">
          <h3>Recognition Result</h3>
          <p><strong>Owner:</strong> {result.owner}</p>
          <p><strong>Plate Text:</strong> {result.plateText}</p>
          <p><strong>Confidence:</strong> {(result.confidence * 100).toFixed(2)}%</p>
          <p><strong>Permit Status:</strong> <span className={result.permitStatus === 'VALID' ? 'status-valid' : 'status-invalid'}>{result.permitStatus}</span></p>
          <p><strong>Expiry Date:</strong> {result.expiryDate}</p>
          <p><strong>Event Type:</strong> {result.eventType}</p>
          <p style={{ fontSize: '0.85em', color: '#666', marginTop: '10px' }}>
            <em>Mock Recognition (Phase 4) - Will use real YOLO model in Phase 6</em>
          </p>
        </div>
      )}
    </div>
  );
}
