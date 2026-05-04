import { useState } from 'react';
import ImageUpload from '../components/ImageUpload';
import ValidationBacklog from '../components/ValidationBacklog';
import EventLog from '../components/EventLog';
import '../styles/Dashboard.css';

export default function Dashboard({ isAdmin = false, username = '' }) {
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
          Validation Backlog
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
        {activeTab === 'lookup' && <ValidationBacklog isAdmin={isAdmin} username={username} />}
        {activeTab === 'events' && <EventLog />}
      </div>
    </div>
  );
}
