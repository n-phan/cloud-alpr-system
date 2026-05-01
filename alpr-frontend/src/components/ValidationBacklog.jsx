import { useState, useEffect } from 'react';
import { getValidationBacklog, updateValidationReview } from '../services/api';
import '../styles/ValidationBacklog.css';

const STATUS_FILTERS = [
  { value: 'pending_review', label: 'Pending' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
];

function formatDate(ms) {
  if (!ms) return '—';
  return new Date(Number(ms)).toLocaleString();
}

function ConfidenceBar({ value }) {
  const pct = (value * 100).toFixed(1);
  const color = value >= 0.6 ? '#f59e0b' : '#dc2626';
  return (
    <div className="confidence-bar-wrap">
      <div className="confidence-bar-track">
        <div className="confidence-bar-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="confidence-label">{pct}%</span>
    </div>
  );
}

function BacklogCard({ item, onAction }) {
  const [notes, setNotes] = useState('');
  const [acting, setActing] = useState(false);

  const handleAction = async (status) => {
    setActing(true);
    try {
      await onAction(item.backlog_id, status, notes);
    } finally {
      setActing(false);
    }
  };

  const isPending = item.status === 'pending_review';

  return (
    <div className={`backlog-card status-${item.status}`}>
      <div className="backlog-card-main">
        {item.image_url ? (
          <img className="backlog-image" src={item.image_url} alt={item.plate_text} />
        ) : (
          <div className="backlog-image-placeholder">No image</div>
        )}

        <div className="backlog-details">
          <div className="backlog-plate">{item.plate_text}</div>

          <div className="backlog-meta">
            <span><span className="meta-label">Vehicle ID</span> {item.vehicle_id}</span>
            <span><span className="meta-label">Submitted</span> {formatDate(item.created_at)}</span>
            {item.permit_status && (
              <span><span className="meta-label">Permit</span> {item.permit_status}</span>
            )}
            {item.event_type && (
              <span><span className="meta-label">Event</span> {item.event_type}</span>
            )}
            {!isPending && item.reviewed_at && (
              <span><span className="meta-label">Reviewed</span> {formatDate(item.reviewed_at)}</span>
            )}
            {item.reviewed_by && (
              <span><span className="meta-label">Reviewed by</span> {item.reviewed_by}</span>
            )}
          </div>

          <div className="backlog-confidence">
            <span className="meta-label">Confidence</span>
            <ConfidenceBar value={item.confidence} />
          </div>

          {item.notes && !isPending && (
            <p className="backlog-notes-display"><span className="meta-label">Notes</span> {item.notes}</p>
          )}

          {isPending && (
            <div className="backlog-actions">
              <textarea
                className="backlog-notes-input"
                placeholder="Optional notes…"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                disabled={acting}
                rows={2}
              />
              <div className="backlog-action-buttons">
                <button
                  className="action-btn approve"
                  onClick={() => handleAction('approved')}
                  disabled={acting}
                >
                  {acting ? 'Saving…' : 'Approve'}
                </button>
                <button
                  className="action-btn reject"
                  onClick={() => handleAction('rejected')}
                  disabled={acting}
                >
                  {acting ? 'Saving…' : 'Reject'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className={`backlog-status-badge ${item.status}`}>
        {item.status.replace('_', ' ')}
      </div>
    </div>
  );
}

export default function ValidationBacklog() {
  const [items, setItems] = useState([]);
  const [statusFilter, setStatusFilter] = useState('pending_review');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchItems();
  }, [statusFilter]);

  const fetchItems = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getValidationBacklog(statusFilter);
      const sorted = (data.items || []).sort((a, b) => b.created_at - a.created_at);
      setItems(sorted);
    } catch (err) {
      setError('Failed to load validation backlog.');
    } finally {
      setLoading(false);
    }
  };

  const handleAction = async (backlogId, status, notes) => {
    await updateValidationReview(backlogId, { status, notes });
    setItems(prev => prev.filter(i => i.backlog_id !== backlogId));
  };

  return (
    <div className="validation-backlog-container">
      <div className="backlog-header">
        <h2>Validation Backlog</h2>
        <button className="refresh-btn" onClick={fetchItems} disabled={loading}>
          {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>

      <div className="backlog-filters">
        {STATUS_FILTERS.map(f => (
          <button
            key={f.value}
            className={`filter-btn ${statusFilter === f.value ? 'active' : ''}`}
            onClick={() => setStatusFilter(f.value)}
          >
            {f.label}
          </button>
        ))}
      </div>

      {error && <div className="error-message">{error}</div>}

      {!loading && items.length === 0 && (
        <div className="backlog-empty">No {statusFilter.replace('_', ' ')} items.</div>
      )}

      <div className="backlog-list">
        {items.map(item => (
          <BacklogCard key={item.backlog_id} item={item} onAction={handleAction} />
        ))}
      </div>
    </div>
  );
}
