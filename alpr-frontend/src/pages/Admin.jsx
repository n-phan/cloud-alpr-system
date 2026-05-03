import { useState } from 'react';
import AdminSummaryCards from '../components/AdminSummaryCards';
import PermitManager from '../components/PermitManager';
import CitationManager from '../components/CitationManager';
import '../styles/Admin.css';

const TABS = [
  { id: 'permits', label: 'Permit Management' },
  { id: 'citations', label: 'Citations' },
];

export default function Admin() {
  const [activeTab, setActiveTab] = useState('permits');

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
        {activeTab === 'permits' && <PermitManager />}
        {activeTab === 'citations' && <CitationManager />}
      </div>
    </div>
  );
}
