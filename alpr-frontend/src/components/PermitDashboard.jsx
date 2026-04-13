import { useState } from 'react';
import { getPermitStatus } from '../services/api';
import '../styles/PermitDashboard.css';

export default function PermitDashboard() {
  const [vehicleId, setVehicleId] = useState('');
  const [permit, setPermit] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleLookup = async () => {
    if (!vehicleId.trim()) {
      setError('Please enter a vehicle ID');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const permitData = await getPermitStatus(vehicleId);
      setPermit(permitData);
    } catch (err) {
      setError(`Vehicle not found: ${vehicleId}`);
      setPermit(null);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleLookup();
    }
  };

  return (
    <div className="permit-dashboard-container">
      <h2>Check Permit Status</h2>

      <div className="lookup-section">
        <input
          type="text"
          placeholder="Enter vehicle ID (e.g., ABC-1234)"
          value={vehicleId}
          onChange={(e) => setVehicleId(e.target.value.toUpperCase())}
          onKeyPress={handleKeyPress}
          disabled={loading}
          className="vehicle-input"
        />
        <button onClick={handleLookup} disabled={loading} className="lookup-button">
          {loading ? 'Searching...' : 'Lookup'}
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      {permit && (
        <div className={`permit-card status-${permit.permitStatus.toLowerCase()}`}>
          <h3>Permit Information</h3>
          <div className="permit-details">
            <p><strong>Vehicle ID:</strong> {permit.vehicleId}</p>
            <p><strong>Owner:</strong> {permit.owner}</p>
            <p>
              <strong>Status:</strong>
              <span className={`status-badge ${permit.permitStatus.toLowerCase()}`}>
                {permit.permitStatus}
              </span>
            </p>
            <p><strong>Expiry Date:</strong> {permit.expiryDate}</p>
          </div>
        </div>
      )}
    </div>
  );
}
