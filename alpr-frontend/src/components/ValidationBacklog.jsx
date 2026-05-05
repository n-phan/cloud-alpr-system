import { useState, useEffect } from 'react';
import { getValidationBacklog, updateValidationReview, createCitation } from '../services/api';
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

function BacklogCard({ item, onAction, isAdmin, username }) {
  const [notes, setNotes] = useState('');
  const [acting, setActing] = useState(false);
  const [rereviewing, setRereviewing] = useState(false);

  const [citingManually, setCitingManually] = useState(false);
  const [citationReason, setCitationReason] = useState('No valid permit');
  const [citationAmount, setCitationAmount] = useState('100');
  const [citationNotes, setCitationNotes] = useState('');
  const [citationError, setCitationError] = useState(null);
  const [citationAlreadyIssued, setCitationAlreadyIssued] = useState(false);

  const handleAction = async (status) => {
    setActing(true);
    try {
      await onAction(item.backlog_id, status, notes);
    } finally {
      setActing(false);
      setRereviewing(false);
    }
  };

  const handleOpenRereview = () => {
    setNotes('');
    setRereviewing(true);
    setCitingManually(false);
  };

  const handleOpenCitation = () => {
    setCitationReason('No valid permit');
    setCitationAmount('100');
    setCitationNotes('');
    setCitationError(null);
    setCitingManually(true);
    setRereviewing(false);
  };

  const handleIssueCitation = async () => {
    if (!citationReason.trim()) {
      setCitationError('Reason is required.');
      return;
    }
    const amount = parseFloat(citationAmount);
    if (isNaN(amount) || amount < 0) {
      setCitationError('Amount must be a non-negative number.');
      return;
    }
    setActing(true);
    setCitationError(null);
    try {
      await createCitation({
        vehicleId: item.vehicle_id,
        plateText: item.plate_text,
        reason: citationReason.trim(),
        amount,
        notes: citationNotes || undefined,
        issuedBy: username || undefined,
        imageUrl: item.image_url || undefined,
        relatedBacklogId: item.backlog_id,
      });
      setCitingManually(false);
      setCitationAlreadyIssued(true);
    } catch {
      setCitationError('Failed to issue citation. Please try again.');
    } finally {
      setActing(false);
    }
  };

  const isPending = item.status === 'pending_review';
  const isApproved = item.status === 'approved';
  const showActionPanel = isPending || rereviewing;

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

          {item.notes && !showActionPanel && !citingManually && (
            <p className="backlog-notes-display"><span className="meta-label">Notes</span> {item.notes}</p>
          )}

          {showActionPanel && (
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
                {rereviewing && (
                  <button
                    className="action-btn cancel"
                    onClick={() => setRereviewing(false)}
                    disabled={acting}
                  >
                    Cancel
                  </button>
                )}
              </div>
            </div>
          )}

          {citingManually && (
            <div className="citation-issue-form">
              <div className="citation-form-row">
                <label className="citation-form-label">Reason</label>
                <input
                  className="citation-form-input"
                  type="text"
                  value={citationReason}
                  onChange={(e) => setCitationReason(e.target.value)}
                  disabled={acting}
                  placeholder="e.g. No valid permit"
                />
              </div>
              <div className="citation-form-row">
                <label className="citation-form-label">Amount ($)</label>
                <input
                  className="citation-form-input citation-form-amount"
                  type="number"
                  min="0"
                  step="0.01"
                  value={citationAmount}
                  onChange={(e) => setCitationAmount(e.target.value)}
                  disabled={acting}
                />
              </div>
              <div className="citation-form-row">
                <label className="citation-form-label">Notes</label>
                <textarea
                  className="backlog-notes-input"
                  placeholder="Optional notes…"
                  value={citationNotes}
                  onChange={(e) => setCitationNotes(e.target.value)}
                  disabled={acting}
                  rows={2}
                />
              </div>
              {citationError && <p className="citation-form-error">{citationError}</p>}
              <div className="backlog-action-buttons">
                <button
                  className="action-btn issue-citation"
                  onClick={handleIssueCitation}
                  disabled={acting}
                >
                  {acting ? 'Issuing…' : 'Issue Citation'}
                </button>
                <button
                  className="action-btn cancel"
                  onClick={() => setCitingManually(false)}
                  disabled={acting}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {!isPending && !rereviewing && !citingManually && isAdmin && (
            <div className="backlog-admin-actions">
              <button className="rereview-btn" onClick={handleOpenRereview}>
                Re-review
              </button>
              {isApproved && (
                <button
                  className={`issue-citation-btn${citationAlreadyIssued ? ' already-issued' : ''}`}
                  onClick={citationAlreadyIssued ? undefined : handleOpenCitation}
                  disabled={citationAlreadyIssued}
                >
                  {citationAlreadyIssued ? 'Citation Already Issued' : 'Issue Citation'}
                </button>
              )}
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

export default function ValidationBacklog({ isAdmin = false, username = '' }) {
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
          <BacklogCard
            key={item.backlog_id}
            item={item}
            onAction={handleAction}
            isAdmin={isAdmin}
            username={username}
          />
        ))}
      </div>
    </div>
  );
}
