import { useState, useEffect } from 'react';
import { getEvents } from '../services/api';
import '../styles/EventLog.css';

export default function EventLogStaff() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('');
  const [selectedEvent, setSelectedEvent] = useState(null);

  useEffect(() => {
    fetchEvents();
    const interval = setInterval(fetchEvents, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchEvents = async () => {
    try {
      const data = await getEvents(50);
      const sorted = (Array.isArray(data) ? data : []).sort(
        (a, b) => b.timestamp - a.timestamp
      );
      setEvents(sorted);
      setError(null);
    } catch (err) {
      console.error('Error fetching events:', err);
      setEvents(mockEvents());
    } finally {
      setLoading(false);
    }
  };

  const mockEvents = () => [
    {
      timestamp: Date.now() - 5 * 60000,
      vehicleId: 'ABC-1234',
      plateText: 'ABC-1234',
      confidence: 0.98,
      permitStatus: 'VALID',
      eventType: 'ENTRY'
    },
    {
      timestamp: Date.now() - 15 * 60000,
      vehicleId: 'XYZ-5678',
      plateText: 'XYZ-5678',
      confidence: 0.95,
      permitStatus: 'EXPIRED',
      eventType: 'ENTRY'
    },
    {
      timestamp: Date.now() - 25 * 60000,
      vehicleId: 'DEF-9012',
      plateText: 'DEF-9012',
      confidence: 0.92,
      permitStatus: 'VALID',
      eventType: 'EXIT'
    }
  ];

  const filteredEvents = events.filter(event => {
    const plate = event?.plateText != null
      ? String(event.plateText).toLowerCase()
      : "";

    return plate.includes(filter.toLowerCase());
  })

  const formatTime = (timestamp) => {
    return new Date(typeof timestamp === 'string' ? timestamp : timestamp * 1000).toLocaleString();
  };

  const handleViewEvent = (event) => setSelectedEvent(event);
  const handleCloseModal = () => setSelectedEvent(null);

  if (loading && events.length === 0) {
    return <div className="loading">Loading events...</div>;
  }

  return (
    <div className="event-log-container">
      <h2>Recent Events</h2>

      <input
        type="text"
        placeholder="Filter by vehicle ID or plate..."
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        className="filter-input"
      />

      {error && <div className="error-message">{error}</div>}

      <div className="events-table-wrapper">
        <table className="events-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Vehicle ID</th>
              <th>Plate Text</th>
              <th>Permit Status</th>
              <th>Event Type</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredEvents && filteredEvents.length > 0 ? (
              filteredEvents.map((event, idx) => {
                // 1. Double check the event object exists
                if (!event) return null;

                // 2. Safely parse the permit status with explicit string fallbacks
                const status = event.permitStatus != null
                  ? String(event.permitStatus).toLowerCase()
                  : 'unknown';

                // 3. Prevent crash if plateText or vehicleId are null/undefined
                const safePlateText = event.plateText != null ? String(event.plateText) : '—';
                const safeVehicleId = event.vehicleId != null ? String(event.vehicleId) : '—';
                const safeEventType = event.eventType != null ? String(event.eventType) : '—';

                return (
                  <tr key={idx} className={`status-${status}`}>
                    <td>{event.timestamp ? formatTime(event.timestamp) : '—'}</td>
                    <td>{safeVehicleId}</td>
                    <td>{safePlateText}</td>
                    <td>
                      <span className={`status-badge ${status}`}>
                        {event.permitStatus || '—'}
                      </span>
                    </td>
                    <td>{safeEventType}</td>
                    <td>
                      <button onClick={() => handleViewEvent(event)} className="view-button">
                        View Event
                      </button>
                    </td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan="6" className="no-events">No events found</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <p className="event-count">Total events: {filteredEvents.length}</p>

      {selectedEvent && (
        <div className="modal-overlay" onClick={handleCloseModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Event Details</h3>
              <button className="close-button" onClick={handleCloseModal}>×</button>
            </div>
            <div className="modal-body">
              <div className="event-detail-item">
                <strong>Time:</strong>
                <span>{formatTime(selectedEvent.timestamp)}</span>
              </div>
              <div className="event-detail-item">
                <strong>Vehicle ID:</strong>
                <span>{selectedEvent.vehicleId}</span>
              </div>
              <div className="event-detail-item">
                <strong>Plate Text:</strong>
                <span>{selectedEvent.plateText}</span>
              </div>
              <div className="event-detail-item">
                <strong>Permit Status:</strong>
                <span className={`status-badge ${(selectedEvent.permitStatus || 'unknown').toLowerCase()}`}>
                  {selectedEvent.permitStatus || '—'}
                </span>
              </div>
              <div className="event-detail-item">
                <strong>Event Type:</strong>
                <span>{selectedEvent.eventType}</span>
              </div>
              <div className="event-detail-item">
                <strong>Captured Image:</strong>
                {selectedEvent.imageUrl ? (
                  <img
                    src={selectedEvent.imageUrl}
                    alt={`Vehicle ${selectedEvent.vehicleId}`}
                    className="license-plate-image"
                  />
                ) : (
                  <div className="image-placeholder">
                    <span>No Image Available</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
