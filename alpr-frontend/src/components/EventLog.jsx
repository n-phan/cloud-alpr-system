import { useState, useEffect } from 'react';
import { getEvents } from '../services/api';
import '../styles/EventLog.css';

export default function EventLog() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('');

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

  const filteredEvents = events.filter(event =>
    event.vehicleId.includes(filter.toUpperCase()) ||
    event.plateText.includes(filter.toUpperCase())
  );

  const formatTime = (timestamp) => {
    return new Date(typeof timestamp === 'string' ? timestamp : timestamp * 1000).toLocaleString();
  };

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
              <th>Confidence</th>
              <th>Permit Status</th>
              <th>Event Type</th>
            </tr>
          </thead>
          <tbody>
            {filteredEvents.length > 0 ? (
              filteredEvents.map((event, idx) => (
                <tr key={idx} className={`status-${event.permitStatus.toLowerCase()}`}>
                  <td>{formatTime(event.timestamp)}</td>
                  <td>{event.vehicleId}</td>
                  <td>{event.plateText}</td>
                  <td>{(event.confidence * 100).toFixed(1)}%</td>
                  <td>
                    <span className={`status-badge ${event.permitStatus.toLowerCase()}`}>
                      {event.permitStatus}
                    </span>
                  </td>
                  <td>{event.eventType}</td>
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
    </div>
  );
}
