import React, { useState } from 'react';
import { Copy, Check, MessageSquare, Calendar } from 'lucide-react';

export default function CoachScheduleView({ coachScheduleData }) {
  const [copied, setCopied] = useState(false);

  if (!coachScheduleData || !coachScheduleData.coach_slots) {
    return (
      <div className="glass-panel" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
        <p>No coach schedule generated yet. Please select a date range and click "Run Engine".</p>
      </div>
    );
  }

  const handleCopyWhatsApp = () => {
    if (coachScheduleData.whatsapp_plain_text) {
      navigator.clipboard.writeText(coachScheduleData.whatsapp_plain_text);
      setCopied(true);
      setTimeout(() => setCopied(false), 3000);
    }
  };

  // Group slots by Date
  const dateGroups = {};
  coachScheduleData.coach_slots.forEach(slot => {
    if (!dateGroups[slot.date]) {
      dateGroups[slot.date] = { day: slot.day, slots: [] };
    }
    dateGroups[slot.date].slots.push(slot);
  });

  return (
    <div className="glass-panel" style={{ padding: '24px' }}>
      {/* Header bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px', marginBottom: '24px', borderBottom: '1px solid var(--border-color)', pb: '16px' }}>
        <div>
          <h2 style={{ fontSize: '1.2rem', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
            📱 Output 1 — Coach Communication Schedule
          </h2>
          <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)' }}>
            Date, Day, Time, and Coach names only (BRD Section 33 & 34). Formatted for instant WhatsApp copying.
          </p>
        </div>

        {/* Copy Action */}
        <button
          onClick={handleCopyWhatsApp}
          className="btn btn-whatsapp"
          style={{ padding: '10px 20px', fontSize: '0.9rem' }}
        >
          {copied ? <Check size={18} /> : <Copy size={18} />}
          {copied ? 'Copied WhatsApp Text!' : 'Copy Coach Schedule (WhatsApp Ready)'}
        </button>
      </div>

      {/* Schedule Grid */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {Object.keys(dateGroups).length === 0 ? (
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>No slots scheduled for this period.</p>
        ) : (
          Object.keys(dateGroups).sort().map(dateStr => {
            const group = dateGroups[dateStr];
            return (
              <div key={dateStr} className="glass-card" style={{ padding: '20px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px', borderBottom: '1px solid var(--border-color)', paddingBottom: '10px' }}>
                  <Calendar size={18} style={{ color: 'var(--accent-gold)' }} />
                  <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#fff' }}>
                    {group.day}, {dateStr}
                  </h3>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '12px' }}>
                  {group.slots.map((s, idx) => (
                    <div
                      key={idx}
                      style={{
                        background: 'var(--bg-secondary)',
                        padding: '12px 16px',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--border-color)'
                      }}
                    >
                      <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent-gold)', display: 'block', marginBottom: '4px' }}>
                        {s.time_slot}
                      </span>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                        {s.coaches.map((c, cIdx) => (
                          <span key={cIdx} className="badge badge-gold" style={{ fontSize: '0.8rem', padding: '4px 8px' }}>
                            {c}
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
