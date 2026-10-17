import React, { useState } from 'react';
import { Copy, Check, Calendar, AlertCircle, CheckCircle, Users, Layers, Trophy } from 'lucide-react';
import { formatCoachSlotsForDayWhatsApp, copyTextToClipboard } from '../utils/dayScheduleFormatter';

const getTimeSlotSortMinutes = (timeSlotStr) => {
  if (!timeSlotStr) return 0;
  try {
    const match = timeSlotStr.match(/(\d{1,2}):(\d{2})\s*(AM|PM)/i);
    if (!match) return 0;
    let hours = parseInt(match[1], 10);
    const minutes = parseInt(match[2], 10);
    const ampm = match[3].toUpperCase();
    if (ampm === 'PM' && hours < 12) hours += 12;
    if (ampm === 'AM' && hours === 12) hours = 0;
    return hours * 60 + minutes;
  } catch (e) {
    return 0;
  }
};

export default function CoachScheduleView({ coachScheduleData, onRunScheduler, loading }) {
  const [copied, setCopied] = useState(false);
  const [copiedDay, setCopiedDay] = useState(null);
  const [hideCompensationMarkers, setHideCompensationMarkers] = useState(false);

  if (!coachScheduleData || !coachScheduleData.coach_slots) {
    return (
      <div className="glass-panel" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
        <p>No coach schedule generated yet. Please select a date range and click "Run Engine".</p>
      </div>
    );
  }

  const totalClasses = coachScheduleData.total_classes ?? 0;
  const quotasCompleted = coachScheduleData.quotas_completed ?? 0;
  const studentSeats = coachScheduleData.student_seats ?? 0;
  const needAttention = coachScheduleData.need_attention ?? 0;

  const handleCopyWhatsApp = () => {
    let text = coachScheduleData.whatsapp_plain_text || '';
    if (hideCompensationMarkers) {
      // Strip circled ⓒ markers for clean parent/trainer communication if desired
      text = text.replace(/ⓒ/g, '').replace(/  +/g, ' ');
    }
    if (text) {
      navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 3000);
    }
  };

  const handleCopySingleDayWhatsApp = async (e, dateStr, dayStr, daySlots) => {
    e.stopPropagation();
    e.preventDefault();
    let text = formatCoachSlotsForDayWhatsApp(dateStr, dayStr, daySlots);
    if (hideCompensationMarkers) {
      text = text.replace(/ⓒ/g, '').replace(/\[ⓒ\]/g, '').replace(/  +/g, ' ');
    }
    const ok = await copyTextToClipboard(text);
    if (ok) {
      setCopiedDay(dateStr);
      setTimeout(() => {
        setCopiedDay(prev => (prev === dateStr ? null : prev));
      }, 2500);
    } else {
      alert("Failed to copy schedule to clipboard. Please check clipboard permissions.");
    }
  };

  // Group slots by Date
  const dateGroups = {};
  (coachScheduleData.coach_slots || []).forEach(slot => {
    if (!dateGroups[slot.date]) {
      dateGroups[slot.date] = { day: slot.day, slots: [] };
    }
    dateGroups[slot.date].slots.push(slot);
  });

  return (
    <div className="glass-panel" style={{ padding: '24px' }}>
      {/* 1. Header bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px', marginBottom: '20px', borderBottom: '1px solid var(--border-color)', paddingBottom: '16px' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
            📱 Output 1 — Coach Communication Schedule (WhatsApp)
          </h2>
          <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Single source of truth communication layer • Date, Day, Time, and Coach names in strict chronological order.
          </p>
        </div>

        {/* Copy Action & Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: 'var(--text-secondary)', cursor: 'pointer', background: 'var(--bg-secondary)', padding: '6px 12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <input
              type="checkbox"
              checked={hideCompensationMarkers}
              onChange={e => setHideCompensationMarkers(e.target.checked)}
              style={{ accentColor: 'var(--accent-gold)', cursor: 'pointer' }}
            />
            <span>Hide ⓒ markers in copy</span>
          </label>

          {onRunScheduler && (
            <button
              onClick={onRunScheduler}
              disabled={loading}
              className="btn btn-secondary"
              style={{ padding: '8px 14px', fontSize: '0.85rem', fontWeight: 700 }}
            >
              ⚡ Run Monthly Engine
            </button>
          )}

          <button
            onClick={handleCopyWhatsApp}
            className="btn btn-whatsapp"
            style={{ padding: '10px 20px', fontSize: '0.9rem' }}
          >
            {copied ? <Check size={18} /> : <Copy size={18} />}
            {copied ? 'Copied WhatsApp Text!' : 'Copy Coach Schedule (WhatsApp Ready)'}
          </button>
        </div>
      </div>

      {/* 2. Executive Single-Source Header Cards (F5 Requirement) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px', marginBottom: '24px' }}>
        <div className="glass-card" style={{ padding: '14px 18px', borderLeft: '4px solid #38bdf8' }}>
          <div style={{ fontSize: '0.725rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
            Total Classes (Batches)
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 900, color: '#38bdf8', marginTop: '4px' }}>
            {totalClasses}
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            Across all active training slots
          </div>
        </div>

        <div className="glass-card" style={{ padding: '14px 18px', borderLeft: '4px solid #10b981' }}>
          <div style={{ fontSize: '0.725rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
            Quotas Completed
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 900, color: '#10b981', marginTop: '4px' }}>
            {quotasCompleted}%
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            Academy monthly requirement delivery
          </div>
        </div>

        <div className="glass-card" style={{ padding: '14px 18px', borderLeft: '4px solid #c084fc' }}>
          <div style={{ fontSize: '0.725rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
            Student Seats Filled
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 900, color: '#c084fc', marginTop: '4px' }}>
            {studentSeats}
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            Total student attendance instances
          </div>
        </div>

        <div className="glass-card" style={{
          padding: '14px 18px',
          borderLeft: `4px solid ${needAttention > 0 ? '#ef4444' : '#10b981'}`,
          background: needAttention > 0 ? 'rgba(239, 68, 68, 0.08)' : undefined
        }}>
          <div style={{ fontSize: '0.725rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
            Need Attention
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 900, color: needAttention > 0 ? '#f87171' : '#34d399', marginTop: '4px' }}>
            {needAttention}
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            {needAttention === 0 ? 'All student requirements fulfilled' : 'Synchronized with Output 3 count'}
          </div>
        </div>
      </div>

      {/* 3. Schedule Grid */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {Object.keys(dateGroups).length === 0 ? (
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>No slots scheduled for this period.</p>
        ) : (
          Object.keys(dateGroups).sort().map(dateStr => {
            const group = dateGroups[dateStr];
            const sortedSlots = [...group.slots].sort(
              (a, b) => getTimeSlotSortMinutes(a.time_slot) - getTimeSlotSortMinutes(b.time_slot)
            );
            return (
              <div key={dateStr} className="glass-card" style={{ padding: '20px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', borderBottom: '1px solid var(--border-color)', paddingBottom: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <Calendar size={18} style={{ color: 'var(--accent-gold)' }} />
                    <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#fff', margin: 0 }}>
                      {group.day}, {dateStr}
                    </h3>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => handleCopySingleDayWhatsApp(e, dateStr, group.day, group.slots)}
                    title="Copy this day's schedule formatted for WhatsApp"
                    className="btn btn-secondary"
                    style={{
                      padding: '4px 10px',
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '5px',
                      background: copiedDay === dateStr ? 'rgba(16, 185, 129, 0.25)' : 'rgba(255, 255, 255, 0.05)',
                      borderColor: copiedDay === dateStr ? '#10b981' : 'var(--border-color)',
                      color: copiedDay === dateStr ? '#10b981' : 'var(--text-secondary)',
                      cursor: 'pointer',
                      borderRadius: 'var(--radius-sm)'
                    }}
                  >
                    {copiedDay === dateStr ? <Check size={12} color="#10b981" /> : <Copy size={12} />}
                    <span>{copiedDay === dateStr ? 'Copied!' : 'Copy Day'}</span>
                  </button>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '12px' }}>
                  {sortedSlots.map((s, idx) => (
                    <div
                      key={idx}
                      style={{
                        background: 'var(--bg-secondary)',
                        padding: '12px 16px',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--border-color)'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                        <span style={{ fontSize: '0.775rem', fontWeight: 800, color: 'var(--accent-gold)', display: 'block' }}>
                          {s.time_slot}
                        </span>
                        <div style={{ display: 'flex', gap: '4px' }}>
                          {s.is_tournament && (
                            <span style={{ padding: '2px 6px', borderRadius: '4px', background: 'rgba(234, 179, 8, 0.2)', color: '#fbbf24', fontSize: '0.68rem', fontWeight: 800 }}>
                              🏆 (Tournament)
                            </span>
                          )}
                          {s.has_compensation && (
                            <span style={{ padding: '2px 6px', borderRadius: '4px', background: 'rgba(56, 189, 248, 0.2)', color: '#38bdf8', fontSize: '0.68rem', fontWeight: 800 }}>
                              ⓒ
                            </span>
                          )}
                        </div>
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                        {s.coaches.map((c, cIdx) => (
                          <span key={cIdx} className="badge badge-gold" style={{ fontSize: '0.8rem', padding: '4px 8px' }}>
                            Coach {c}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
