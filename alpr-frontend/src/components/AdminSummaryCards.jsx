import { useState, useEffect } from 'react';
import { getEvents, getValidationBacklog } from '../services/api';
import '../styles/AdminSummaryCards.css';

export default function AdminSummaryCards() {
  const [stats, setStats] = useState({ total: 0, valid: 0, invalid: 0, pending: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchStats = async () => {
    try {
      const [eventsRaw, backlogRaw] = await Promise.all([
        getEvents(200),
        getValidationBacklog('pending_review', 100),
      ]);

      const events = Array.isArray(eventsRaw) ? eventsRaw : [];
      const backlog = backlogRaw?.items ?? (Array.isArray(backlogRaw) ? backlogRaw : []);

      const valid = events.filter(e => e.permitStatus === 'VALID').length;
      const invalid = events.filter(e =>
        ['EXPIRED', 'REVOKED', 'INVALID'].includes(e.permitStatus)
      ).length;

      setStats({ total: events.length, valid, invalid, pending: backlog.length });
    } catch (err) {
      console.error('Error fetching admin stats:', err);
    } finally {
      setLoading(false);
    }
  };

  const cards = [
    { label: 'Total Events', value: stats.total, mod: 'total' },
    { label: 'Valid Permits', value: stats.valid, mod: 'valid' },
    { label: 'Expired / Revoked', value: stats.invalid, mod: 'invalid' },
    { label: 'Pending Validation', value: stats.pending, mod: 'pending' },
  ];

  if (loading) {
    return (
      <div className="summary-cards">
        {cards.map(c => (
          <div key={c.label} className={`summary-card summary-card--${c.mod} summary-card--loading`}>
            <span className="summary-card__value">—</span>
            <span className="summary-card__label">{c.label}</span>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="summary-cards">
      {cards.map(c => (
        <div key={c.label} className={`summary-card summary-card--${c.mod}`}>
          <span className="summary-card__value">{c.value}</span>
          <span className="summary-card__label">{c.label}</span>
        </div>
      ))}
    </div>
  );
}
