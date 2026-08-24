import React from 'react';
import { ShieldAlert, AlertTriangle, CheckCircle2, UserX, Info, Move } from 'lucide-react';

export default function AttentionReportView({ attentionData, onOpenManualEditForStudent }) {
  if (!attentionData) {
    return (
      <div className="glass-panel" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
        <p>No unscheduled report generated yet. Please run the scheduling engine.</p>
      </div>
    );
  }

  const {
    total_students_considered,
    unscheduled_count,
    accountability_passed,
    attention_records
  } = attentionData;

  const scheduled_count = total_students_considered - unscheduled_count;

  return (
    <div className="unscheduled-banner" style={{ padding: '28px', marginBottom: '24px' }}>
      {/* Banner Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            width: '48px', height: '48px', borderRadius: '12px',
            background: '#ef4444', display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 20px rgba(239, 68, 68, 0.6)'
          }}>
            <ShieldAlert size={28} style={{ color: '#fff' }} className="pulse-icon" />
          </div>
          <div>
            <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#fff', letterSpacing: '-0.01em' }}>
              ■ Unscheduled — Administrator Attention Required
            </h2>
            <p style={{ fontSize: '0.85rem', color: '#fca5a5', fontWeight: 500 }}>
              Mandatory Student Accountability Rule (BRD Section 28 & 29). Drag unscheduled students into Output 2 classes!
            </p>
          </div>
        </div>

        {/* Accountability Stat Badges */}
        <div style={{ display: 'flex', gap: '12px' }}>
          <div style={{ background: 'rgba(0,0,0,0.4)', padding: '10px 16px', borderRadius: 'var(--radius-md)', border: '1px solid rgba(255,255,255,0.1)' }}>
            <span style={{ fontSize: '0.7rem', color: '#d1d5db', display: 'block' }}>TOTAL CONSIDERED</span>
            <strong style={{ fontSize: '1.2rem', color: '#fff' }}>{total_students_considered}</strong>
          </div>
          <div style={{ background: 'rgba(16, 185, 129, 0.2)', padding: '10px 16px', borderRadius: 'var(--radius-md)', border: '1px solid rgba(16, 185, 129, 0.4)' }}>
            <span style={{ fontSize: '0.7rem', color: '#a7f3d0', display: 'block' }}>SCHEDULED</span>
            <strong style={{ fontSize: '1.2rem', color: '#10b981' }}>{scheduled_count}</strong>
          </div>
          <div style={{ background: 'rgba(239, 68, 68, 0.3)', padding: '10px 16px', borderRadius: 'var(--radius-md)', border: '1px solid #ef4444' }}>
            <span style={{ fontSize: '0.7rem', color: '#fca5a5', display: 'block' }}>ATTENTION REQUIRED</span>
            <strong style={{ fontSize: '1.2rem', color: '#ef4444' }}>{unscheduled_count}</strong>
          </div>
        </div>
      </div>

      {/* Accountability status note */}
      <div style={{ background: 'rgba(0, 0, 0, 0.3)', padding: '12px 18px', borderRadius: 'var(--radius-md)', marginBottom: '24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {accountability_passed ? (
            <CheckCircle2 size={18} style={{ color: '#10b981' }} />
          ) : (
            <AlertTriangle size={18} style={{ color: '#f59e0b' }} />
          )}
          <span style={{ fontSize: '0.85rem', color: '#f3f4f6' }}>
            <strong>Accountability Rule Check:</strong> {accountability_passed ? 'PASSED — 100% of input students accounted for.' : 'WARNING — Mismatch in student counting.'}
          </span>
        </div>
        <span style={{ fontSize: '0.75rem', color: 'var(--accent-gold)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Move size={14} /> Tip: Drag any student row onto a class in Output 2 to assign them!
        </span>
      </div>

      {/* Unscheduled Students Table */}
      <div style={{ overflowX: 'auto', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
        <table className="custom-table">
          <thead>
            <tr>
              <th>Drag Handle</th>
              <th>Student Info</th>
              <th>Level & Batch</th>
              <th>Required</th>
              <th>Scheduled</th>
              <th>Remaining</th>
              <th>Reason for Scheduling Failure</th>
              <th>Preferred Days & Timings</th>
            </tr>
          </thead>
          <tbody>
            {attention_records.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ textAlign: 'center', color: '#10b981', padding: '30px', fontWeight: 600 }}>
                  🎉 All students were successfully scheduled! No administrative attention required.
                </td>
              </tr>
            ) : (
              attention_records.map(rec => (
                <tr
                  key={rec.student_id}
                  draggable={true}
                  onDragStart={(e) => {
                    e.dataTransfer.setData("application/json", JSON.stringify({ type: "UNSCHEDULED_STUDENT", student: rec }));
                  }}
                  style={{ cursor: 'grab' }}
                >
                  <td style={{ color: 'var(--accent-gold)' }}>
                    <Move size={16} title="Drag to assign to class in Output 2" />
                  </td>
                  <td>
                    <div style={{ fontWeight: 700, color: '#fff' }}>{rec.student_name}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--accent-gold)' }}>ID: {rec.student_id}</div>
                  </td>
                  <td>
                    <div style={{ fontWeight: 600, color: '#fff' }}>{rec.student_level}</div>
                    <span className="badge badge-gold" style={{ fontSize: '0.7rem' }}>Batch {rec.batch_type}</span>
                  </td>
                  <td>
                    <span style={{ fontWeight: 700 }}>{rec.required_classes}</span>
                  </td>
                  <td>
                    <span style={{ fontWeight: 700, color: '#10b981' }}>{rec.scheduled_classes}</span>
                  </td>
                  <td>
                    <span className="badge badge-danger" style={{ fontSize: '0.85rem' }}>
                      {rec.remaining_classes} Missing
                    </span>
                  </td>
                  <td>
                    <div style={{ color: '#ef4444', fontWeight: 600, fontSize: '0.825rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <AlertTriangle size={14} /> {rec.failure_reason}
                    </div>
                  </td>
                  <td style={{ maxWidth: '250px' }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      {rec.preferred_days}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
