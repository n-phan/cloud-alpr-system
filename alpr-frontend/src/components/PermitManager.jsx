import { useState, useEffect } from 'react';
import { getPermits, createPermit, updatePermit } from '../services/api';
import '../styles/PermitManager.css';

const STATUS_BADGE = { VALID: 'valid', EXPIRED: 'expired', REVOKED: 'revoked' };

export default function PermitManager() {
  const [permits, setPermits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ vehicleId: '', owner: '', expiryDate: '' });
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({ owner: '', expiryDate: '' });

  useEffect(() => {
    fetchPermits();
  }, []);

  const fetchPermits = async () => {
    try {
      setLoading(true);
      const data = await getPermits();
      const items = data?.items ?? (Array.isArray(data) ? data : []);
      setPermits(items);
      setError(null);
    } catch (err) {
      setError('Failed to load permits. Make sure the /permits backend endpoint is deployed.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleFormChange = (field, value) => {
    setForm(f => ({ ...f, [field]: value }));
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setActionError(null);
    try {
      await createPermit(form);
      setForm({ vehicleId: '', owner: '', expiryDate: '' });
      setShowForm(false);
      await fetchPermits();
    } catch (err) {
      setActionError(err.response?.data?.error || 'Failed to create permit');
    } finally {
      setSubmitting(false);
    }
  };

  const startEdit = (permit) => {
    setEditingId(permit.vehicleId);
    setEditForm({ owner: permit.owner || '', expiryDate: permit.expiryDate || '' });
    setActionError(null);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditForm({ owner: '', expiryDate: '' });
  };

  const handleSaveEdit = async (vehicleId) => {
    setSubmitting(true);
    setActionError(null);
    try {
      await updatePermit(vehicleId, { owner: editForm.owner, expiryDate: editForm.expiryDate });
      setPermits(prev =>
        prev.map(p => p.vehicleId === vehicleId
          ? { ...p, owner: editForm.owner, expiryDate: editForm.expiryDate }
          : p
        )
      );
      setEditingId(null);
    } catch (err) {
      setActionError(err.response?.data?.error || 'Failed to save changes');
    } finally {
      setSubmitting(false);
    }
  };

  const handleStatusChange = async (vehicleId, newStatus) => {
    setActionError(null);
    try {
      await updatePermit(vehicleId, { status: newStatus });
      setPermits(prev =>
        prev.map(p => p.vehicleId === vehicleId ? { ...p, permitStatus: newStatus } : p)
      );
    } catch (err) {
      setActionError(err.response?.data?.error || 'Failed to update permit');
    }
  };

  const filtered = permits.filter(p =>
    (p.vehicleId || '').toUpperCase().includes(filter.toUpperCase()) ||
    (p.owner || '').toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className="permit-manager">
      <div className="permit-manager__header">
        <h3>Permit Management</h3>
        <button
          className={`pm-btn pm-btn--${showForm ? 'cancel' : 'add'}`}
          onClick={() => { setShowForm(v => !v); setActionError(null); }}
        >
          {showForm ? 'Cancel' : '+ Add Permit'}
        </button>
      </div>

      {showForm && (
        <form className="pm-form" onSubmit={handleCreate}>
          <div className="pm-form__row">
            <div className="pm-form__group">
              <label>Vehicle ID / Plate</label>
              <input
                required
                placeholder="e.g. ABC-1234"
                value={form.vehicleId}
                onChange={e => handleFormChange('vehicleId', e.target.value.toUpperCase())}
              />
            </div>
            <div className="pm-form__group">
              <label>Owner Name</label>
              <input
                required
                placeholder="Full name"
                value={form.owner}
                onChange={e => handleFormChange('owner', e.target.value)}
              />
            </div>
            <div className="pm-form__group">
              <label>Expiry Date</label>
              <input
                type="date"
                required
                value={form.expiryDate}
                onChange={e => handleFormChange('expiryDate', e.target.value)}
              />
            </div>
          </div>
          <button type="submit" className="pm-btn pm-btn--submit" disabled={submitting}>
            {submitting ? 'Creating…' : 'Create Permit'}
          </button>
        </form>
      )}

      {(error || actionError) && (
        <div className="pm-error">{error || actionError}</div>
      )}

      <input
        className="pm-filter"
        placeholder="Filter by vehicle ID or owner…"
        value={filter}
        onChange={e => setFilter(e.target.value)}
      />

      {loading ? (
        <div className="pm-loading">Loading permits…</div>
      ) : (
        <div className="pm-table-wrapper">
          <table className="pm-table">
            <thead>
              <tr>
                <th>Vehicle ID</th>
                <th>Owner</th>
                <th>Expiry Date</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length > 0 ? (
                filtered.map((permit, idx) => {
                  const statusKey = (permit.permitStatus || '').toUpperCase();
                  const badgeMod = STATUS_BADGE[statusKey] || 'unknown';
                  const isEditing = editingId === permit.vehicleId;
                  return (
                    <tr key={idx} className={`pm-row pm-row--${badgeMod}${isEditing ? ' pm-row--editing' : ''}`}>
                      <td className="pm-monospace">{permit.vehicleId}</td>
                      <td>
                        {isEditing ? (
                          <input
                            className="pm-inline-input"
                            value={editForm.owner}
                            onChange={e => setEditForm(f => ({ ...f, owner: e.target.value }))}
                            placeholder="Owner name"
                          />
                        ) : (permit.owner || '—')}
                      </td>
                      <td>
                        {isEditing ? (
                          <input
                            className="pm-inline-input"
                            type="date"
                            value={editForm.expiryDate}
                            onChange={e => setEditForm(f => ({ ...f, expiryDate: e.target.value }))}
                          />
                        ) : (permit.expiryDate || '—')}
                      </td>
                      <td>
                        <span className={`pm-badge pm-badge--${badgeMod}`}>
                          {permit.permitStatus || 'UNKNOWN'}
                        </span>
                      </td>
                      <td className="pm-actions">
                        {isEditing ? (
                          <>
                            <button
                              className="pm-action pm-action--save"
                              onClick={() => handleSaveEdit(permit.vehicleId)}
                              disabled={submitting}
                            >
                              {submitting ? '…' : 'Save'}
                            </button>
                            <button
                              className="pm-action pm-action--cancel-edit"
                              onClick={cancelEdit}
                              disabled={submitting}
                            >
                              Cancel
                            </button>
                          </>
                        ) : (
                          <>
                            <button
                              className="pm-action pm-action--edit"
                              onClick={() => startEdit(permit)}
                            >
                              Edit
                            </button>
                            {statusKey !== 'VALID' && (
                              <button
                                className="pm-action pm-action--activate"
                                onClick={() => handleStatusChange(permit.vehicleId, 'VALID')}
                              >
                                Activate
                              </button>
                            )}
                            {statusKey !== 'REVOKED' && (
                              <button
                                className="pm-action pm-action--revoke"
                                onClick={() => handleStatusChange(permit.vehicleId, 'REVOKED')}
                              >
                                Revoke
                              </button>
                            )}
                          </>
                        )}
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan="5" className="pm-empty">No permits found</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      <p className="pm-count">{filtered.length} permit{filtered.length !== 1 ? 's' : ''}</p>
    </div>
  );
}
