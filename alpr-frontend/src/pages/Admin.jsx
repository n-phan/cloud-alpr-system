import { useState } from 'react';
import AdminSummaryCards from '../components/AdminSummaryCards';
import EventLogAdmin from '../components/EventLogAdmin';
import PermitManager from '../components/PermitManager';
import '../styles/Admin.css';

const TABS = [
  { id: 'events', label: 'Event Log' },
  { id: 'permits', label: 'Permit Management' },
];

export default function Admin() {
  const [activeTab, setActiveTab] = useState('events');

  return (
    <div className="admin-container">
      <h2>Admin Dashboard</h2>
      <p className="admin-subtitle">
        System administrators can view all events, monitor permit status, and manage permits.
      </p>

      <AdminSummaryCards />

      <div className="admin-tabs">
        {TABS.map(tab => (
          <button
            key={tab.id}
            className={`admin-tab${activeTab === tab.id ? ' admin-tab--active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="admin-tab-content">
        {activeTab === 'events' && <EventLogAdmin />}
        {activeTab === 'permits' && <PermitManager />}
      </div>
    </div>
  );
}
