import React from 'react';
import { Calendar as CalendarIcon, Clock, ChevronRight } from 'lucide-react';

export default function CalendarPicker({ startDate, endDate, setStartDate, setEndDate, onRunScheduler, loading }) {
  
  const handlePreset = (type) => {
    const today = new Date('2026-08-24'); // Fixed test anchor or current date
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
    <div className="glass-panel" style={{ padding: '20px 24px', marginBottom: '24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <CalendarIcon size={20} style={{ color: 'var(--accent-gold)' }} />
          <div>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#fff' }}>Scheduling Period Selection</h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Select target date range to apply Mighty Knight rules (BRD Section 24–26)
            </p>
          </div>
        </div>

        {/* Quick presets */}
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <button onClick={() => handlePreset('today')} className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.8rem' }}>
            Today
          </button>
          <button onClick={() => handlePreset('tomorrow')} className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.8rem' }}>
            Tomorrow
          </button>
          <button onClick={() => handlePreset('week')} className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.8rem' }}>
            This Week
          </button>
          <button onClick={() => handlePreset('month')} className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.8rem' }}>
            Full Month
          </button>
        </div>
      </div>

      {/* Date Pickers */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginTop: '16px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>START DATE</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            style={{
              padding: '10px 14px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              color: '#fff',
              outline: 'none',
              fontWeight: 600
            }}
          />
        </div>

        <ChevronRight size={18} style={{ color: 'var(--text-muted)', marginTop: '16px' }} />

        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>END DATE</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            style={{
              padding: '10px 14px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              color: '#fff',
              outline: 'none',
              fontWeight: 600
            }}
          />
        </div>

        <button
          onClick={onRunScheduler}
          disabled={loading}
          className="btn btn-primary"
          style={{ marginTop: '18px', padding: '10px 24px' }}
        >
          {loading ? 'Processing Engine...' : 'Generate Schedule'}
        </button>
      </div>
    </div>
  );
}
