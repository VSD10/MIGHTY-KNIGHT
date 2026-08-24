import React from 'react';
import { Calendar as CalendarIcon, ChevronRight, FileSpreadsheet } from 'lucide-react';

export default function CalendarPicker({ startDate, endDate, setStartDate, setEndDate, onRunScheduler, loading, onUploadClick }) {
  
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
    <div className="glass-panel" style={{ padding: '18px 24px', marginBottom: '24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
        {/* Left Title */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            width: '40px',
            height: '40px',
            borderRadius: '12px',
            background: 'rgba(251, 191, 36, 0.15)',
            border: '1px solid rgba(251, 191, 36, 0.35)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--accent-gold)'
          }}>
            <CalendarIcon size={20} />
          </div>
          <div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 800, color: '#fff' }}>Scheduling Date Range Selection</h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Configure target period dates for automated class slot matching
            </p>
          </div>
        </div>

        {/* Date Inputs, Presets & Top-Right Upload Action */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          {/* Quick presets */}
          <div style={{ display: 'flex', gap: '4px', background: 'var(--bg-secondary)', padding: '4px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <button onClick={() => handlePreset('today')} className="btn btn-secondary" style={{ padding: '5px 10px', fontSize: '0.75rem', border: 'none' }}>
              Today
            </button>
            <button onClick={() => handlePreset('tomorrow')} className="btn btn-secondary" style={{ padding: '5px 10px', fontSize: '0.75rem', border: 'none' }}>
              Tomorrow
            </button>
            <button onClick={() => handlePreset('week')} className="btn btn-secondary" style={{ padding: '5px 10px', fontSize: '0.75rem', border: 'none' }}>
              This Week
            </button>
            <button onClick={() => handlePreset('month')} className="btn btn-secondary" style={{ padding: '5px 10px', fontSize: '0.75rem', border: 'none' }}>
              Full Month
            </button>
          </div>

          {/* Date Range Inputs */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--bg-secondary)', padding: '4px 12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '0.625rem', color: 'var(--text-muted)', fontWeight: 700 }}>START DATE</span>
              <input
                type="date"
                value={startDate}
                onChange={e => setStartDate(e.target.value)}
                style={{ padding: '0px 4px', background: 'transparent', border: 'none', color: 'var(--accent-gold)', fontWeight: 800, fontSize: '0.85rem' }}
              />
            </div>

            <ChevronRight size={14} style={{ color: 'var(--text-muted)' }} />

            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '0.625rem', color: 'var(--text-muted)', fontWeight: 700 }}>END DATE</span>
              <input
                type="date"
                value={endDate}
                onChange={e => setEndDate(e.target.value)}
                style={{ padding: '0px 4px', background: 'transparent', border: 'none', color: 'var(--accent-gold)', fontWeight: 800, fontSize: '0.85rem' }}
              />
            </div>
          </div>

          {/* Top-Right Upload Excel Data Button */}
          {onUploadClick && (
            <button onClick={onUploadClick} className="btn btn-primary" style={{ padding: '8px 16px', fontSize: '0.8rem' }}>
              <FileSpreadsheet size={16} /> Upload Excel
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
