import React from 'react';
import { Calendar as CalendarIcon, Clock, ChevronRight, Sparkles } from 'lucide-react';

export default function CalendarPicker({ startDate, endDate, setStartDate, setEndDate, onRunScheduler, loading }) {
  
  const handlePreset = (type) => {
    const today = new Date();
    const formatDate = (d) => d.toISOString().split('T')[0];

    if (type === 'today') {
      const s = formatDate(today);
      setStartDate(s);
      setEndDate(s);
    } else if (type === 'tomorrow') {
      const tom = new Date(today);
      tom.setDate(today.getDate() + 1);
      const s = formatDate(tom);
      setStartDate(s);
      setEndDate(s);
    } else if (type === 'week') {
      const s = formatDate(today);
      const endW = new Date(today);
      endW.setDate(today.getDate() + 6);
      setStartDate(s);
      setEndDate(formatDate(endW));
    } else if (type === 'month') {
      const s = formatDate(today);
      const endM = new Date(today.getFullYear(), today.getMonth() + 1, 0);
      setStartDate(s);
      setEndDate(formatDate(endM));
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '20px 28px', marginBottom: '28px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: '12px',
            background: 'rgba(251, 191, 36, 0.15)',
            border: '1px solid rgba(251, 191, 36, 0.35)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--accent-gold)'
          }}>
            <CalendarIcon size={22} />
          </div>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#fff' }}>Scheduling Date Range Selection</h3>
            <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)' }}>
              Configure target period dates for automated class slot matching & capacity enforcement
            </p>
          </div>
        </div>

        {/* Date Inputs & Presets Bar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
          {/* Quick presets */}
          <div style={{ display: 'flex', gap: '6px', background: 'var(--bg-secondary)', padding: '4px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <button onClick={() => handlePreset('today')} className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.775rem', border: 'none' }}>
              Today
            </button>
            <button onClick={() => handlePreset('tomorrow')} className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.775rem', border: 'none' }}>
              Tomorrow
            </button>
            <button onClick={() => handlePreset('week')} className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.775rem', border: 'none' }}>
              This Week
            </button>
            <button onClick={() => handlePreset('month')} className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.775rem', border: 'none' }}>
              Full Month
            </button>
          </div>

          {/* Date Range Inputs */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', background: 'var(--bg-secondary)', padding: '6px 14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '0.675rem', color: 'var(--text-muted)', fontWeight: 700 }}>START DATE</span>
              <input
                type="date"
                value={startDate}
                onChange={e => setStartDate(e.target.value)}
                style={{ padding: '2px 6px', background: 'transparent', border: 'none', color: 'var(--accent-gold)', fontWeight: 800, fontSize: '0.875rem' }}
              />
            </div>

            <ChevronRight size={16} style={{ color: 'var(--text-muted)' }} />

            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '0.675rem', color: 'var(--text-muted)', fontWeight: 700 }}>END DATE</span>
              <input
                type="date"
                value={endDate}
                onChange={e => setEndDate(e.target.value)}
                style={{ padding: '2px 6px', background: 'transparent', border: 'none', color: 'var(--accent-gold)', fontWeight: 800, fontSize: '0.875rem' }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
