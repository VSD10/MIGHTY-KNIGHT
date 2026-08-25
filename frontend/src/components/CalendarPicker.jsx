import React, { useState } from 'react';
import { Calendar as CalendarIcon, ChevronRight, FileSpreadsheet, Play, Loader2, ChevronUp, ChevronDown } from 'lucide-react';

export default function CalendarPicker({ startDate, endDate, setStartDate, setEndDate, onRunScheduler, loading, onUploadClick }) {
  const [isShrunk, setIsShrunk] = useState(false);
  
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
    } else if (type === 'nextMonth') {
      const firstDayNext = new Date(today.getFullYear(), today.getMonth() + 1, 1);
      const lastDayNext = new Date(today.getFullYear(), today.getMonth() + 2, 0);
      setStartDate(formatDate(firstDayNext));
      setEndDate(formatDate(lastDayNext));
    } else if (type === '30days') {
      const s = formatDate(today);
      const end30 = new Date(today);
      end30.setDate(today.getDate() + 29);
      setStartDate(s);
      setEndDate(formatDate(end30));
    }
  };

  // SHRUNK / COLLAPSED VIEW
  if (isShrunk) {
    return (
      <div
        className="glass-panel"
        style={{
          padding: '10px 20px',
          marginBottom: '16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(15, 23, 42, 0.85)',
          backdropFilter: 'blur(12px)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-lg)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ color: 'var(--accent-gold)', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', fontWeight: 800 }}>
            <CalendarIcon size={16} />
            <span>Target Period: <span style={{ color: '#fff' }}>{startDate}</span> to <span style={{ color: '#fff' }}>{endDate}</span></span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {onRunScheduler && (
            <button
              onClick={onRunScheduler}
              disabled={loading}
              className="btn btn-primary"
              style={{ padding: '6px 14px', fontSize: '0.8rem', fontWeight: 800, boxShadow: '0 0 15px rgba(251, 191, 36, 0.4)' }}
            >
              {loading ? (
                <>
                  <Loader2 size={14} className="spin-loader" /> Running Engine...
                </>
              ) : (
                <>
                  <Play size={14} fill="currentColor" /> Run Engine
                </>
              )}
            </button>
          )}

          {onUploadClick && (
            <button
              onClick={onUploadClick}
              className="btn btn-secondary"
              style={{ padding: '6px 12px', fontSize: '0.8rem' }}
            >
              <FileSpreadsheet size={14} /> Upload Excel
            </button>
          )}

          <button
            onClick={() => setIsShrunk(false)}
            className="btn btn-secondary"
            title="Expand Date Controls"
            style={{ padding: '6px 10px', fontSize: '0.75rem', color: 'var(--accent-gold)', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '4px' }}
          >
            <ChevronDown size={16} /> Expand Date Picker
          </button>
        </div>
      </div>
    );
  }

  // FULL EXPANDED VIEW
  return (
    <div className="glass-panel" style={{ padding: '18px 24px', marginBottom: '24px', transition: 'all 0.3s ease' }}>
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

        {/* Date Inputs, Presets, Run Engine & Shrink Toggle */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          {/* Quick presets */}
          <div style={{ display: 'flex', gap: '4px', background: 'var(--bg-secondary)', padding: '4px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <button onClick={() => handlePreset('today')} className="btn btn-secondary" style={{ padding: '5px 10px', fontSize: '0.75rem', border: 'none' }}>
              Today
            </button>
            <button onClick={() => handlePreset('week')} className="btn btn-secondary" style={{ padding: '5px 10px', fontSize: '0.75rem', border: 'none' }}>
              This Week
            </button>
            <button onClick={() => handlePreset('month')} className="btn btn-secondary" style={{ padding: '5px 10px', fontSize: '0.75rem', border: 'none' }}>
              This Month
            </button>
            <button onClick={() => handlePreset('nextMonth')} className="btn btn-secondary" style={{ padding: '5px 10px', fontSize: '0.75rem', border: 'none' }}>
              Next Month
            </button>
            <button onClick={() => handlePreset('30days')} className="btn btn-secondary" style={{ padding: '5px 10px', fontSize: '0.75rem', border: 'none' }}>
              30 Days
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

          {/* PRIMARY ACTION: Run Scheduling Engine */}
          {onRunScheduler && (
            <button
              onClick={onRunScheduler}
              disabled={loading}
              className="btn btn-primary"
              style={{
                padding: '8px 18px',
                fontSize: '0.85rem',
                fontWeight: 800,
                boxShadow: '0 0 20px rgba(251, 191, 36, 0.4)'
              }}
            >
              {loading ? (
                <>
                  <Loader2 size={16} className="spin-loader" /> Running Engine...
                </>
              ) : (
                <>
                  <Play size={16} fill="currentColor" /> Run Engine
                </>
              )}
            </button>
          )}

          {/* SECONDARY ACTION: Upload Excel */}
          {onUploadClick && (
            <button
              onClick={onUploadClick}
              className="btn btn-secondary"
              style={{ padding: '8px 14px', fontSize: '0.8rem' }}
            >
              <FileSpreadsheet size={16} /> Upload Excel
            </button>
          )}

          {/* SHRINK / COLLAPSE BUTTON */}
          <button
            onClick={() => setIsShrunk(true)}
            className="btn btn-secondary"
            title="Shrink banner to save screen space"
            style={{ padding: '8px 10px', fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}
          >
            <ChevronUp size={16} /> Shrink
          </button>
        </div>
      </div>
    </div>
  );
}
