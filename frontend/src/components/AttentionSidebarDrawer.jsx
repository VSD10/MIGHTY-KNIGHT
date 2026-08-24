import React, { useState } from 'react';
import { ShieldAlert, X, ChevronRight, UserPlus, Sparkles, Check, AlertTriangle } from 'lucide-react';
import { assignStudentToClass, createClassForStudent } from '../services/api';

export default function AttentionSidebarDrawer({
  isOpen,
  onClose,
  attentionRecords,
  scheduleId,
  onRefreshSchedule,
  coachList
}) {
  const [assigningStudentId, setAssigningStudentId] = useState(null);
  const [selectedClassId, setSelectedClassId] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen) return null;

  const records = attentionRecords || [];

  const handleAssign = async (studentId, classId) => {
    if (!classId) {
      alert('Please select a target class slot');
      return;
    }
    setSubmitting(true);
    try {
      await assignStudentToClass(scheduleId, studentId, classId);
      setAssigningStudentId(null);
      setSelectedClassId('');
      if (onRefreshSchedule) await onRefreshSchedule(scheduleId);
    } catch (err) {
      alert('Assignment failed: ' + err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <aside
      className="glass-panel"
      style={{
        width: '380px',
        minWidth: '380px',
        height: 'calc(100vh - 48px)',
        position: 'sticky',
        top: '24px',
        display: 'flex',
        flexDirection: 'column',
        padding: '20px',
        border: '2px solid var(--status-danger)',
        boxShadow: '0 0 30px rgba(244, 63, 94, 0.2)',
        zIndex: 90,
        overflowY: 'auto'
      }}
    >
      {/* Drawer Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', paddingBottom: '12px', borderBottom: '1px solid var(--border-color)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <ShieldAlert size={22} className="pulse-icon" style={{ color: 'var(--status-danger)' }} />
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#fff' }}>
              Emergency Unscheduled Panel
            </h3>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              {records.length} students requiring assignment
            </p>
          </div>
        </div>

        <button
          onClick={onClose}
          style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
        >
          <X size={20} />
        </button>
      </div>

      {/* Unscheduled Students List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {records.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--status-success)' }}>
            <Check size={36} style={{ margin: '0 auto 10px auto', display: 'block' }} />
            <strong style={{ fontSize: '1rem', color: '#fff', display: 'block' }}>All Students Scheduled!</strong>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>100% accountability rate achieved.</span>
          </div>
        ) : (
          records.map((rec) => {
            const isSelected = assigningStudentId === rec.student_id;
            const recs = rec.recommendations || [];

            return (
              <div
                key={rec.student_id}
                draggable
                onDragStart={(e) => {
                  e.dataTransfer.setData("application/json", JSON.stringify({ type: "UNSCHEDULED_STUDENT", student: rec }));
                }}
                style={{
                  background: 'var(--bg-card)',
                  border: isSelected ? '1px solid var(--accent-gold)' : '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-md)',
                  padding: '14px',
                  cursor: 'grab',
                  transition: 'all 0.2s ease'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                  <div>
                    <h4 style={{ fontSize: '0.925rem', fontWeight: 800, color: '#fff' }}>
                      {rec.student_name}
                    </h4>
                    <div style={{ fontSize: '0.75rem', color: 'var(--accent-gold)', fontWeight: 700 }}>
                      ID: {rec.student_id} · Level: {rec.student_level}
                    </div>
                  </div>

                  <span className="badge badge-danger" style={{ fontSize: '0.65rem' }}>
                    {rec.batch_type} Batch
                  </span>
                </div>

                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '10px' }}>
                  Pref Days: {rec.preferred_days || 'All'} · Time: {rec.preferred_time || '05:00 PM'}
                </div>

                {/* Candidate Recommendations Dropdown / Quick Assign */}
                {recs.length > 0 && (
                  <div style={{ background: 'rgba(0,0,0,0.2)', padding: '10px', borderRadius: 'var(--radius-sm)', marginBottom: '10px' }}>
                    <div style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--accent-gold)', marginBottom: '6px' }}>
                      TOP RECOMMENDATIONS:
                    </div>
                    {recs.slice(0, 2).map((candidate, idx) => (
                      <div
                        key={idx}
                        onClick={() => handleAssign(rec.student_id, candidate.class_id)}
                        style={{
                          background: candidate.is_overtime ? 'rgba(244, 63, 94, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                          border: candidate.is_overtime ? '1px solid rgba(244, 63, 94, 0.3)' : '1px solid rgba(16, 185, 129, 0.3)',
                          borderRadius: '4px',
                          padding: '6px 8px',
                          marginBottom: '4px',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          fontSize: '0.725rem'
                        }}
                      >
                        <div>
                          <strong style={{ color: '#fff' }}>{candidate.coach_name}</strong>
                          <span style={{ color: 'var(--text-secondary)', marginLeft: '4px' }}>
                            ({candidate.day} {candidate.time_slot})
                          </span>
                        </div>
                        <span style={{ fontWeight: 800, color: candidate.is_overtime ? '#f43f5e' : '#10b981' }}>
                          Assign ✓
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
}
