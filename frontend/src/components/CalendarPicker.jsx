import React, { useState } from 'react';
import { Calendar as CalendarIcon, ChevronLeft, ChevronRight, FileSpreadsheet, Play, Loader2, ChevronUp, ChevronDown } from 'lucide-react';

export default function CalendarPicker({ startDate, endDate, setStartDate, setEndDate, onRunScheduler, loading, onUploadClick }) {
  const [isShrunk, setIsShrunk] = useState(false);

  // Helper to get month bounds (YYYY-MM-01 to YYYY-MM-lastDay)
  const getMonthBounds = (year, monthIndex) => {
    const pad = (n) => String(n).padStart(2, '0');
    const firstDay = new Date(year, monthIndex, 1);
    const lastDay = new Date(year, monthIndex + 1, 0);
    const yStr = String(firstDay.getFullYear());
    const mStr = pad(firstDay.getMonth() + 1);
    const dStr = pad(lastDay.getDate());
    return {
      start: `${yStr}-${mStr}-01`,
      end: `${yStr}-${mStr}-${dStr}`,
      year: firstDay.getFullYear(),
      monthIndex: firstDay.getMonth(),
      monthName: firstDay.toLocaleString('default', { month: 'long' }),
      daysCount: lastDay.getDate(),
      monthInputValue: `${yStr}-${mStr}`
    };
  };

  // Derive current month info from startDate (default to today if missing)
  const currentDate = startDate ? new Date(startDate) : new Date();
  const validDate = isNaN(currentDate.getTime()) ? new Date() : currentDate;
  const currentMonthInfo = getMonthBounds(validDate.getFullYear(), validDate.getMonth());

  const applyMonth = (year, monthIndex) => {
    const bounds = getMonthBounds(year, monthIndex);
    setStartDate(bounds.start);
    setEndDate(bounds.end);
  };

  const handlePrevMonth = () => {
    applyMonth(currentMonthInfo.year, currentMonthInfo.monthIndex - 1);
  };

  const handleNextMonth = () => {
    applyMonth(currentMonthInfo.year, currentMonthInfo.monthIndex + 1);
  };

  const handleThisMonth = () => {
    const today = new Date();
    applyMonth(today.getFullYear(), today.getMonth());
  };

  const handleNextMonthPreset = () => {
    const today = new Date();
    applyMonth(today.getFullYear(), today.getMonth() + 1);
  };

  const handleMonthInputChange = (e) => {
    const val = e.target.value; // "YYYY-MM"
    if (!val) return;
    const [y, m] = val.split('-').map(Number);
    if (y && m) {
      applyMonth(y, m - 1);
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
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ color: 'var(--accent-gold)', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', fontWeight: 800 }}>
            <CalendarIcon size={16} />
            <span>Monthly Cycle: <span style={{ color: '#fff' }}>{currentMonthInfo.monthName} {currentMonthInfo.year}</span></span>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            ({startDate} to {endDate})
          </span>
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
                  <Play size={14} fill="currentColor" /> Run Monthly Engine
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
            title="Expand Month Controls"
            style={{ padding: '6px 10px', fontSize: '0.75rem', color: 'var(--accent-gold)', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '4px' }}
          >
            <ChevronDown size={16} /> Expand Controls
          </button>
        </div>
      </div>
    );
  }

  // FULL EXPANDED VIEW
  return (
    <div className="glass-panel" style={{ padding: '18px 24px', marginBottom: '24px', transition: 'all 0.3s ease' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
        
        {/* Left: Monthly Title & Active Date Span */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            width: '44px',
            height: '44px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, rgba(251, 191, 36, 0.25) 0%, rgba(217, 119, 6, 0.25) 100%)',
            border: '1px solid rgba(251, 191, 36, 0.4)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--accent-gold)',
            boxShadow: '0 0 15px rgba(251, 191, 36, 0.2)'
          }}>
            <CalendarIcon size={22} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 900, color: '#fff', letterSpacing: '-0.01em' }}>
                {currentMonthInfo.monthName} {currentMonthInfo.year} Schedule
              </h3>
              <span className="badge badge-gold" style={{ fontSize: '0.65rem', padding: '2px 8px', fontWeight: 800 }}>
                Monthly Mode
              </span>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Scheduling Cycle: <strong style={{ color: 'var(--accent-gold)' }}>{startDate}</strong> &rarr; <strong style={{ color: 'var(--accent-gold)' }}>{endDate}</strong> ({currentMonthInfo.daysCount} Days)
            </p>
          </div>
        </div>

        {/* Right: Month Switcher & Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          
          {/* Quick Month Navigator Bar */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            background: 'var(--bg-secondary)',
            padding: '4px',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-color)',
            gap: '4px'
          }}>
            <button
              onClick={handlePrevMonth}
              className="btn btn-secondary"
              title="Previous Month"
              style={{ padding: '6px 8px', fontSize: '0.75rem', border: 'none' }}
            >
              <ChevronLeft size={16} />
            </button>

            <button
              onClick={handleThisMonth}
              className="btn btn-secondary"
              style={{
                padding: '6px 12px',
                fontSize: '0.75rem',
                border: 'none',
                fontWeight: 700,
                background: currentMonthInfo.monthIndex === new Date().getMonth() && currentMonthInfo.year === new Date().getFullYear() ? 'rgba(251, 191, 36, 0.2)' : 'transparent',
                color: currentMonthInfo.monthIndex === new Date().getMonth() && currentMonthInfo.year === new Date().getFullYear() ? 'var(--accent-gold)' : 'var(--text-secondary)'
              }}
            >
              This Month
            </button>

            <button
              onClick={handleNextMonthPreset}
              className="btn btn-secondary"
              style={{ padding: '6px 12px', fontSize: '0.75rem', border: 'none', fontWeight: 700 }}
            >
              Next Month
            </button>

            <button
              onClick={handleNextMonth}
              className="btn btn-secondary"
              title="Next Month"
              style={{ padding: '6px 8px', fontSize: '0.75rem', border: 'none' }}
            >
              <ChevronRight size={16} />
            </button>
          </div>

          {/* HTML5 Month Selector Input */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            background: 'var(--bg-secondary)',
            padding: '4px 10px',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-color)',
            gap: '6px'
          }}>
            <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 800, textTransform: 'uppercase' }}>
              PICK MONTH:
            </span>
            <input
              type="month"
              value={currentMonthInfo.monthInputValue}
              onChange={handleMonthInputChange}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--accent-gold)',
                fontWeight: 800,
                fontSize: '0.85rem',
                cursor: 'pointer',
                outline: 'none'
              }}
            />
          </div>

          {/* PRIMARY ACTION: Run Monthly Engine */}
          {onRunScheduler && (
            <button
              onClick={onRunScheduler}
              disabled={loading}
              className="btn btn-primary"
              style={{
                padding: '8px 20px',
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
                  <Play size={16} fill="currentColor" /> Run Monthly Engine
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
