import EventLogAdmin from '../components/EventLogAdmin';
import '../styles/Admin.css';

export default function Admin() {
  return (
    <div className="admin-container">
      <h2>Admin Dashboard</h2>
      <p className="admin-subtitle">System administrators can view all events with confidence scores and event details.</p>
      <EventLogAdmin />
    </div>
  );
}
