import { useState } from 'react';
import { getCitationsByPlate } from '../services/api';
import '../styles/Citations.css';

function formatDate(timestampMs) {
  if (!timestampMs) return '—';
  return new Date(Number(timestampMs)).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function CitationItem({ citation }) {
  const status = citation.status || 'issued';
  const amount = citation.amount != null ? `$${Number(citation.amount).toFixed(2)}` : '—';

  return (
    <div className="citation-item">
      <div className="citation-item-header">
        <span className="citation-reason">{citation.reason || 'No reason provided'}</span>
        <span className={`citation-status ${status}`}>{status}</span>
      </div>
      <div className="citation-meta">
        <span>
          <span className="label">Citation ID</span>
          <span className="value">{citation.citation_id}</span>
        </span>
        <span>
          <span className="label">Plate</span>
          <span className="value">{citation.plate_text}</span>
        </span>
        <span>
          <span className="label">Issued</span>
          <span className="value">{formatDate(citation.issued_at)}</span>
        </span>
        <span>
          <span className="label">Amount Due</span>
          <span className="value citation-amount">{amount}</span>
        </span>
        {citation.issued_by && (
          <span>
            <span className="label">Issued By</span>
            <span className="value">{citation.issued_by}</span>
          </span>
        )}
      </div>
    </div>
  );
}

export default function Citations() {
  const [plate, setPlate] = useState('');
  const [citations, setCitations] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimmed = plate.trim().toUpperCase();
    if (!trimmed) return;

    setLoading(true);
    setError(null);
    setCitations(null);

    try {
      const data = await getCitationsByPlate(trimmed);
      setCitations(data.citations || []);
    } catch (err) {
      setError(err.message || 'Failed to retrieve citations. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="citations-page">
      <div className="citations-card">
        <h1>ALPR Parking System</h1>
        <p className="subtitle">Look up outstanding parking citations by license plate</p>

        <form className="lookup-form" onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="Enter license plate (e.g. ABC123)"
            value={plate}
            onChange={(e) => setPlate(e.target.value)}
            disabled={loading}
            maxLength={10}
            required
          />
          <button type="submit" disabled={loading}>
            {loading ? 'Searching...' : 'Search'}
          </button>
        </form>

        {error && <p className="error-message">{error}</p>}

        {citations !== null && citations.length === 0 && (
          <div className="no-citations">
            <div className="check-icon">✓</div>
            <p>No citations found for plate <strong>{plate.trim().toUpperCase()}</strong>.</p>
          </div>
        )}

        {citations && citations.length > 0 && (
          <>
            <p className="results-header">
              {citations.length} citation{citations.length !== 1 ? 's' : ''} found for{' '}
              <strong>{plate.trim().toUpperCase()}</strong>
            </p>
            <div className="citation-list">
              {citations.map((c) => (
                <CitationItem key={c.citation_id} citation={c} />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
