import { useState } from 'react';
import { uploadImageToS3 } from '../services/api';
import '../styles/ImageUpload.css';

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB
const MIN_DIMENSION = 100; // px — too small to contain a readable plate

function uid() {
  return Math.random().toString(36).slice(2, 9);
}

async function validateImage(file) {
  if (!file.type.startsWith('image/')) throw new Error('Must be an image file');
  if (file.size > MAX_FILE_SIZE) throw new Error('File must be under 10 MB');

  await new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(url);
      if (img.naturalWidth < MIN_DIMENSION || img.naturalHeight < MIN_DIMENSION) {
        reject(new Error(`Image must be at least ${MIN_DIMENSION}×${MIN_DIMENSION}px`));
      } else {
        resolve();
      }
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('File could not be decoded as an image'));
    };
    img.src = url;
  });
}

function createEntry(file) {
  return {
    id: uid(),
    file,
    previewUrl: URL.createObjectURL(file),
    status: 'pending', // pending | uploading | done | error
    result: null,
    error: null,
  };
}


export default function ImageUpload({ onResultReceived }) {
  const [entries, setEntries] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [dropError, setDropError] = useState(null);

  const updateEntry = (id, patch) =>
    setEntries(prev => prev.map(e => e.id === id ? { ...e, ...patch } : e));

  const addFiles = async (files) => {
    setDropError(null);
    const valid = [];
    const errors = [];

    for (const file of files) {
      try {
        await validateImage(file);
        valid.push(createEntry(file));
      } catch (err) {
        errors.push(`${file.name}: ${err.message}`);
      }
    }

    if (errors.length) setDropError(errors.join(' · '));
    if (valid.length) setEntries(prev => [...prev, ...valid]);
  };

  const handleFileChange = (e) => {
    const files = Array.from(e.target.files || []);
    e.target.value = '';
    addFiles(files);
  };

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
    addFiles(Array.from(e.dataTransfer.files || []));
  };

  const removeEntry = (id) => {
    setEntries(prev => {
      const entry = prev.find(e => e.id === id);
      if (entry) URL.revokeObjectURL(entry.previewUrl);
      return prev.filter(e => e.id !== id);
    });
  };

  const handleUpload = async () => {
    const pending = entries.filter(e => e.status === 'pending');
    if (!pending.length) return;

    setUploading(true);

    for (const entry of pending) {
      updateEntry(entry.id, { status: 'uploading', error: null });

      try {
        const base64 = await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(reader.result.split(',')[1]);
          reader.onerror = reject;
          reader.readAsDataURL(entry.file);
        });

        const s3Result = await uploadImageToS3(base64, entry.file.name);

        updateEntry(entry.id, { status: 'done', result: { imageUrl: s3Result.imageUrl } });
        if (onResultReceived) onResultReceived({ imageUrl: s3Result.imageUrl });
      } catch (err) {
        updateEntry(entry.id, { status: 'error', error: err.message || 'Upload failed' });
      }
    }

    setUploading(false);
  };

  const pendingCount = entries.filter(e => e.status === 'pending').length;

  return (
    <div className="image-upload-container">
      <h2>Upload Vehicle Images</h2>

      <div
        className="drop-zone"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="drop-text">
          <p>Drag and drop images here</p>
          <p>or</p>
          <label htmlFor="file-input" className="file-label">Select files</label>
          <input
            id="file-input"
            type="file"
            accept="image/*"
            multiple
            onChange={handleFileChange}
            disabled={uploading}
            style={{ display: 'none' }}
          />
          <p className="drop-hint">JPEG, PNG, WEBP · max 10 MB · min {MIN_DIMENSION}×{MIN_DIMENSION}px</p>
        </div>
      </div>

      {dropError && <div className="error-message">{dropError}</div>}

      {entries.length > 0 && (
        <div className="file-grid">
          {entries.map(entry => (
            <div key={entry.id} className={`file-card ${entry.status}`}>
              <div className="file-card-preview">
                <img src={entry.previewUrl} alt={entry.file.name} />
                {entry.status === 'pending' && (
                  <button
                    className="file-card-remove"
                    onClick={() => removeEntry(entry.id)}
                    disabled={uploading}
                    title="Remove"
                  >×</button>
                )}
                {entry.status === 'uploading' && (
                  <div className="file-card-overlay">Analyzing…</div>
                )}
              </div>

              <div className="file-card-info">
                <span className="file-card-name" title={entry.file.name}>{entry.file.name}</span>
                <span className={`file-card-status ${entry.status}`}>
                  {entry.status === 'pending' && 'Ready'}
                  {entry.status === 'uploading' && 'Processing…'}
                  {entry.status === 'done' && '✓ Done'}
                  {entry.status === 'error' && '✗ Failed'}
                </span>
              </div>

              {entry.status === 'error' && (
                <p className="file-card-error">{entry.error}</p>
              )}

              {entry.status === 'done' && (
                <div className="file-card-result file-card-result--success">
                  Uploaded and queued for processing.
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {pendingCount > 0 && (
        <button onClick={handleUpload} disabled={uploading} className="upload-button">
          {uploading
            ? 'Processing…'
            : `Upload & Analyze${pendingCount > 1 ? ` (${pendingCount} files)` : ''}`}
        </button>
      )}
    </div>
  );
}
