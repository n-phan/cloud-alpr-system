import { useState, useEffect } from 'react';
import { getAllCitations, updateCitation } from '../services/api';
import '../styles/CitationManager.css';

const STATUS_FILTERS = [
  { value: null, label: 'All' },
  { value: 'issued', label: 'Issued' },
  { value: 'paid', label: 'Paid' },
  { value: 'disputed', label: 'Disputed' },
  { value: 'voided', label: 'Voided' },
];

const NEXT_STATUSES = {
  issued: ['paid', 'disputed', 'voided'],
  paid: ['disputed', 'voided'],
  disputed: ['issued', 'paid', 'voided'],
  voided: [],
};

function formatDate(ms) {
  if (!ms) return '—';
  return new Date(Number(ms)).toLocaleString();
}

function formatAmount(amount) {
  if (amount == null) return '—';
  return `$${Number(amount).toFixed(2)}`;
}

function truncateId(id) {
  if (!id) return '—';
  return id.length > 12 ? `${id.slice(0, 8)}…` : id;
}

function StatusBadge({ status }) {
  return (
    <span className={`cm-badge cm-badge--${status || 'unknown'}`}>
      {status || 'unknown'}
    </span>
  );
}

function CitationRow({ citation, onUpdate }) {
  const [editing, setEditing] = useState(false);
  const [newStatus, setNewStatus] = useState('');
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);

  const nextOptions = NEXT_STATUSES[citation.status] || [];

  const handleEdit = () => {
    setNewStatus(nextOptions[0] || '');
    setNotes('');
    setEditing(true);
  };

  const handleCancel = () => setEditing(false);

  const handleSave = async () => {
    if (!newStatus) return;
    setSaving(true);
    try {
      await onUpdate(citation.citation_id, { status: newStatus, notes });
      setEditing(false);
    } finally {
      setSaving(false);
    }
  };

  return (
    <tr className={`cm-row cm-row--${citation.status || 'unknown'}${editing ? ' cm-row--editing' : ''}`}>
      <td>
        <span className="cm-monospace" title={citation.citation_id}>
          {truncateId(citation.citation_id)}
        </span>
      </td>
      <td className="cm-monospace">{citation.plate_text || '—'}</td>
      <td>{citation.reason || '—'}</td>
      <td>{formatAmount(citation.amount)}</td>
      <td><StatusBadge status={citation.status} /></td>
      <td>{formatDate(citation.issued_at)}</td>
      <td>{citation.issued_by || '—'}</td>
      <td>
        {editing ? (
          <div className="cm-edit-row">
            <select
              className="cm-select"
              value={newStatus}
              onChange={(e) => setNewStatus(e.target.value)}
              disabled={saving}
            >
              {nextOptions.map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            <input
              className="cm-inline-input"
              placeholder="Notes (optional)"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              disabled={saving}
            />
            <div className="cm-edit-actions">
              <button
                className="cm-action cm-action--save"
                onClick={handleSave}
                disabled={saving || !newStatus}
              >
                {saving ? 'Saving…' : 'Save'}
              </button>
              <button
                className="cm-action cm-action--cancel"
                onClick={handleCancel}
                disabled={saving}
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <div className="cm-actions">
            {nextOptions.length > 0 && (
              <button className="cm-action cm-action--edit" onClick={handleEdit}>
                Process
              </button>
            )}
            {citation.notes && (
              <span className="cm-notes-indicator" title={citation.notes}>Notes</span>
            )}
          </div>
        )}
      </td>
    </tr>
  );
}

export default function CitationManager() {
  const [citations, setCitations] = useState([]);
  const [statusFilter, setStatusFilter] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchCitations();
  }, [statusFilter]);

  const fetchCitations = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getAllCitations(statusFilter);
      const sorted = (data.items || []).sort((a, b) => (b.issued_at || 0) - (a.issued_at || 0));
      setCitations(sorted);
    } catch {
      setError('Failed to load citations.');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async (citationId, updates) => {
    await updateCitation(citationId, updates);
    await fetchCitations();
  };

  const activeLabel = STATUS_FILTERS.find(f => f.value === statusFilter)?.label || 'All';

  return (
    <div className="citation-manager">
      <div className="cm-header">
        <h3>Citations</h3>
        <button className="cm-btn cm-btn--refresh" onClick={fetchCitations} disabled={loading}>
          {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>

      <div className="cm-filter-tabs">
        {STATUS_FILTERS.map(f => (
          <button
            key={String(f.value)}
            className={`cm-filter-tab${statusFilter === f.value ? ' active' : ''}`}
            onClick={() => setStatusFilter(f.value)}
          >
            {f.label}
          </button>
        ))}
      </div>

      {error && <div className="cm-error">{error}</div>}

      {!loading && citations.length === 0 && !error && (
        <div className="cm-empty">No {activeLabel.toLowerCase()} citations found.</div>
      )}

      {citations.length > 0 && (
        <div className="cm-table-wrapper">
          <table className="cm-table">
            <thead>
              <tr>
                <th>Citation ID</th>
                <th>Plate</th>
                <th>Reason</th>
                <th>Amount</th>
                <th>Status</th>
                <th>Issued At</th>
                <th>Issued By</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {citations.map(c => (
                <CitationRow key={c.citation_id} citation={c} onUpdate={handleUpdate} />
              ))}
            </tbody>
          </table>
          <p className="cm-count">{citations.length} citation{citations.length !== 1 ? 's' : ''}</p>
        </div>
      )}
    </div>
  );
}
