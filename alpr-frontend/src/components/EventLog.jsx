import { useState, useEffect } from 'react';
import { getEvents } from '../services/api';
import '../styles/EventLog.css';

export default function EventLog() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('');
  const [permitStatusFilter, setPermitStatusFilter] = useState('');
  const [eventTypeFilter, setEventTypeFilter] = useState('');
  const [timeFilter, setTimeFilter] = useState('');
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

  const filteredEvents = events.filter((event) => {
    const search = filter.toLowerCase();
    const plate = event?.plateText != null ? String(event.plateText).toLowerCase() : '';
    const vehicleId = event?.vehicleId != null ? String(event.vehicleId).toLowerCase() : '';

    const matchesSearch = plate.includes(search) || vehicleId.includes(search);
    const matchesPermit = !permitStatusFilter || event?.permitStatus === permitStatusFilter;
    const matchesEventType = !eventTypeFilter || event?.eventType === eventTypeFilter;

    let matchesTime = true;
    if (timeFilter) {
      const cutoff = Date.now() / 1000 - parseInt(timeFilter) * 3600;
      const ts = typeof event.timestamp === 'string' ? parseInt(event.timestamp) : event.timestamp;
      matchesTime = ts >= cutoff;
    }

    return matchesSearch && matchesPermit && matchesEventType && matchesTime;
  });

  const formatTime = (timestamp) => {
    const ms = typeof timestamp === 'string' ? parseInt(timestamp) * 1000 : timestamp * 1000;
    return new Date(ms).toLocaleString('en-US', { timeZone: 'America/Los_Angeles' });
  };

  const handleViewEvent = (event) => setSelectedEvent(event);
  const handleCloseModal = () => setSelectedEvent(null);

  if (loading && events.length === 0) {
    return <div className="loading">Loading events...</div>;
  }

  return (
    <div className="event-log-container">
      <h2>Recent Events</h2>

      <div className="filter-controls">
        <input
          type="text"
          placeholder="Filter by vehicle ID or plate..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="filter-input"
        />
        <div className="filter-dropdowns">
          <select
            value={timeFilter}
            onChange={(e) => setTimeFilter(e.target.value)}
            className="filter-select"
          >
            <option value="">Time: All</option>
            <option value="1">Time: Last 1 Hour</option>
            <option value="6">Time: Last 6 Hours</option>
            <option value="24">Time: Last 24 Hours</option>
            <option value="168">Time: Last 7 Days</option>
          </select>
          <select
            value={permitStatusFilter}
            onChange={(e) => setPermitStatusFilter(e.target.value)}
            className="filter-select"
          >
            <option value="">Permit Status: All</option>
            <option value="VALID">Permit Status: Valid</option>
            <option value="EXPIRED">Permit Status: Expired</option>
            <option value="UNKNOWN">Permit Status: Unknown</option>
          </select>
          <select
            value={eventTypeFilter}
            onChange={(e) => setEventTypeFilter(e.target.value)}
            className="filter-select"
          >
            <option value="">Event Type: All</option>
            <option value="ENTRY">Event Type: Entry</option>
            <option value="EXIT">Event Type: Exit</option>
            <option value="DETECTION">Event Type: Detection</option>
          </select>
        </div>
      </div>

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
            {filteredEvents.length > 0 ? (
              filteredEvents.map((event, idx) => (
                <tr key={idx} className={`status-${(event.permitStatus || 'unknown').toLowerCase()}`}>
                  <td>{formatTime(event.timestamp)}</td>
                  <td>{event.vehicleId}</td>
                  <td>{event.plateText}</td>
                  <td>
                    <span className={`status-badge ${(event.permitStatus || 'unknown').toLowerCase()}`}>
                      {event.permitStatus || '—'}
                    </span>
                  </td>
                  <td>{event.eventType}</td>
                  <td>
                    <button onClick={() => handleViewEvent(event)} className="view-button">
                      View Event
                    </button>
                  </td>
                </tr>
              ))
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
