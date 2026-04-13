import { useState } from 'react';
import ImageUpload from '../components/ImageUpload';
import PermitDashboard from '../components/PermitDashboard';
import EventLogStaff from '../components/EventLogStaff';
import '../styles/Dashboard.css';

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState('upload');

  return (
    <div className="dashboard-container">
      <nav className="dashboard-nav">
        <button
          className={activeTab === 'upload' ? 'active' : ''}
          onClick={() => setActiveTab('upload')}
        >
          Upload Image
        </button>
        <button
          className={activeTab === 'lookup' ? 'active' : ''}
          onClick={() => setActiveTab('lookup')}
        >
          Check Permit
        </button>
        <button
          className={activeTab === 'events' ? 'active' : ''}
          onClick={() => setActiveTab('events')}
        >
          Recent Events
        </button>
      </nav>

      <div className="tab-content">
        {activeTab === 'upload' && <ImageUpload />}
        {activeTab === 'lookup' && <PermitDashboard />}
        {activeTab === 'events' && <EventLogStaff />}
      </div>
    </div>
  );
}
