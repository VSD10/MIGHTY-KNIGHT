import React from 'react';
import { ShieldCheck, CheckCircle2, Layers, Users, Calendar, Clock, Award, Sparkles, Check } from 'lucide-react';

export default function SettingsView({ config }) {
  const activeRules = [
    {
      id: 'RULE_BATCH_CAPACITY',
      name: 'Group Batch Capacity Bounds',
      category: 'Batch Capacity',
      description: 'Enforces student capacity limits per batch type during schedule generation.',
      details: [
        { label: 'Group Batch (G)', value: '4 – 10 Students' },
        { label: 'Limited Students Batch (L)', value: '1 – 4 Students' },
        { label: 'Individual Batch (I)', value: '1 Student' }
      ],
      status: 'ENFORCED HARD CONSTRAINT'
    },
    {
      id: 'RULE_STUDENT_DAILY_LIMIT',
      name: 'Student Daily Class Uniqueness',
      category: 'Student Limits',
      description: 'Prevents double-booking by limiting each student to at most 1 class per calendar day.',
      details: [
        { label: 'Max Classes / Student / Day', value: '1 Class Max' }
      ],
      status: 'ENFORCED HARD CONSTRAINT'
    },
    {
      id: 'RULE_SUNDAY_TOURNAMENT',
      name: 'Sunday Operating Hours & Tournament Cap',
      category: 'Sunday Rules',
      description: 'Restricts Sunday scheduling to end by 3:00 PM and reserves tournament coaches.',
      details: [
        { label: 'Sunday Max End Time', value: '3:00 PM (15:00)' },
        { label: 'Excluded Tournament Coaches', value: 'Dhaanush, Saravanan' },
        { label: 'Excluded Tournament Levels', value: 'Intermediate' }
      ],
      status: 'ENFORCED HARD CONSTRAINT'
    },
    {
      id: 'RULE_COACH_PRIORITY',
      name: 'Coach Capability & Level Priority Matrix',
      category: 'Coach Capability',
      description: 'Routes student levels strictly to qualified coaches ordered by preferred capability priority list.',
      details: [
        { label: 'Basic 1 & 2', value: 'Bathrinath → Abinaya → Manikandan → Prakash → Guruvanthana' },
        { label: 'Beginner 1', value: 'Bathrinath → Guruvanthana → Dhaanush → Manikandan → Abinaya → Prakash' },
        { label: 'Beginner 2 & 3', value: 'Guruvanthana → Dhaanush → Bathrinath → Prakash → Saravanan' },
        { label: 'Early Intermediate 1 & 2', value: 'Dhaanush → Saravanan → Arshath → Prakash → Guruvanthana' },
        { label: 'Intermediate', value: 'Arshath → Dhaanush → Prakash → Saravanan' }
      ],
      status: 'ENFORCED HARD CONSTRAINT'
    },
    {
      id: 'RULE_OPERATING_TIME_SLOTS',
      name: 'Academy Operating Time Slot Windows',
      category: 'Time Windows',
      description: 'Defines valid scheduling time slots for weekday and Sunday sessions.',
      details: [
        { label: 'Weekday Operating Slots', value: '06:00 AM – 10:00 PM (13 Slots)' },
        { label: 'Sunday Operating Slots', value: '09:00 AM – 03:00 PM (6 Slots)' }
      ],
      status: 'ENFORCED HARD CONSTRAINT'
    },
    {
      id: 'RULE_COACH_PREFERRED_TIMING',
      name: 'Coach Preferred Timing',
      category: 'Coach Capability',
      description: 'Enforces day-wise preferred time windows and optional daily class caps from Coach Sheet → Preferred Timings.',
      details: [
        { label: 'Source', value: 'Coach Sheet → Preferred Timings' },
        { label: 'Time Windows & Daily Max', value: 'Dynamic Day-wise Ranges & (max X) Caps' }
      ],
      status: 'ENFORCED'
    }
  ];

  return (
    <div className="glass-panel" style={{ padding: '32px' }}>
      {/* Header bar */}
      <div style={{ marginBottom: '24px', borderBottom: '1px solid var(--border-color)', paddingBottom: '18px' }}>
        <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '10px' }}>
          ⚙️ Settings — Active Scheduling Algorithm Constraints
        </h2>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
          Active rule architecture and constraints enforced by the Mighty Knight scheduling engine.
        </p>
      </div>

      {/* METRICS SUMMARY BAR */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px', marginBottom: '28px' }}>
        <div style={{ background: 'var(--bg-secondary)', padding: '14px 18px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
          <span style={{ fontSize: '0.725rem', color: 'var(--text-muted)', display: 'block', fontWeight: 700 }}>ENFORCED RULE COUNT</span>
          <strong style={{ fontSize: '1.3rem', color: '#fff' }}>{activeRules.length} Active Algorithm Rules</strong>
        </div>

        <div style={{ background: 'rgba(16, 185, 129, 0.12)', padding: '14px 18px', borderRadius: 'var(--radius-md)', border: '1px solid rgba(16, 185, 129, 0.35)' }}>
          <span style={{ fontSize: '0.725rem', color: '#6ee7b7', display: 'block', fontWeight: 700 }}>CONSTRAINT ENFORCEMENT</span>
          <strong style={{ fontSize: '1.3rem', color: '#10b981' }}>100% Hard Constraints</strong>
        </div>

        <div style={{ background: 'rgba(251, 191, 36, 0.12)', padding: '14px 18px', borderRadius: 'var(--radius-md)', border: '1px solid rgba(251, 191, 36, 0.35)' }}>
          <span style={{ fontSize: '0.725rem', color: '#fde68a', display: 'block', fontWeight: 700 }}>SCHEDULING LOGIC</span>
          <strong style={{ fontSize: '1.3rem', color: '#fbbf24' }}>Automated Engine Execution</strong>
        </div>
      </div>

      {/* ACTIVE RULE CARDS MATRIX */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {activeRules.map((rule) => (
          <div
            key={rule.id}
            style={{
              background: 'var(--bg-secondary)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-color)',
              padding: '22px'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px', marginBottom: '10px' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#ffffff' }}>
                    {rule.name}
                  </h3>
                  <span className="badge badge-gold" style={{ fontSize: '0.7rem' }}>
                    {rule.category}
                  </span>
                </div>
                <div style={{ fontSize: '0.725rem', color: '#fbbf24', fontFamily: 'monospace', marginTop: '2px' }}>
                  {rule.id}
                </div>
              </div>

              <span className="badge badge-success" style={{ fontSize: '0.75rem', padding: '4px 12px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                <CheckCircle2 size={14} /> {rule.status}
              </span>
            </div>

            <p style={{ fontSize: '0.85rem', color: '#cbd5e1', marginBottom: '16px' }}>
              {rule.description}
            </p>

            {/* Parameter Detail Pills */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '10px', background: 'rgba(0,0,0,0.3)', padding: '14px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.06)' }}>
              {rule.details.map((dt, i) => (
                <div key={i} style={{ fontSize: '0.8rem' }}>
                  <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.725rem', fontWeight: 700 }}>
                    {dt.label}:
                  </span>
                  <strong style={{ color: '#fbbf24', fontWeight: 800 }}>
                    {dt.value}
                  </strong>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
