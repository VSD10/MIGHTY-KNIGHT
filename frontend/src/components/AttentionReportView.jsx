import React, { useState } from 'react';
import { ShieldAlert, AlertTriangle, CheckCircle2, UserX, Info, Move, Sparkles, Check, Zap, Plus, X, Calendar, Clock, Award, Search } from 'lucide-react';
import { assignStudentToClass, createClassForStudent } from '../services/api';

const DEFAULT_COACHES = ["PRAKASH", "RAVEENA", "GURUVANTHANA", "BATHRINATH", "KARTHIK"];

export default function AttentionReportView({ attentionData, scheduleId, onRefreshSchedule, coachList }) {
  const [assigningId, setAssigningId] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Custom Create New Class state per student
  const [activeNewClassStudentId, setActiveNewClassStudentId] = useState(null);
  const [newCoachName, setNewCoachName] = useState('BATHRINATH');
  const [newDate, setNewDate] = useState('2026-08-24');
  const [newTimeSlot, setNewTimeSlot] = useState('05:00 PM - 06:00 PM');
  const [newBatchType, setNewBatchType] = useState('G');
  const [creating, setCreating] = useState(false);

  const coachesOptions = (coachList && coachList.length > 0) ? coachList : DEFAULT_COACHES;

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

  const handleAcceptRecommendation = async (studentId, classId, isOvertime) => {
    if (isOvertime) {
      const confirmOvertime = window.confirm(
        "⚠️ EMERGENCY OVERTIME CONFIRMATION:\nThis assignment exceeds the standard capacity limit for this class batch. Do you want to approve emergency overtime for this coach?"
      );
      if (!confirmOvertime) return;
    }

    setAssigningId(`${studentId}_${classId}`);
    try {
      await assignStudentToClass(scheduleId, studentId, classId);
      if (onRefreshSchedule) await onRefreshSchedule();
    } catch (err) {
      alert('Failed to assign student: ' + (err.response?.data?.detail || err.message));
    } finally {
      setAssigningId(null);
    }
  };

  const handleCreateNewClassForStudent = async (student) => {
    setCreating(true);
    try {
      await createClassForStudent(scheduleId, {
        student_id: student.student_id,
        coach_name: newCoachName,
        date: newDate,
        time_slot: newTimeSlot,
        student_level: student.student_level,
        batch_type: newBatchType
      });
      setActiveNewClassStudentId(null);
      if (onRefreshSchedule) await onRefreshSchedule();
    } catch (err) {
      alert('Failed to create new class for student: ' + (err.response?.data?.detail || err.message));
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="unscheduled-banner" style={{ padding: '28px', marginBottom: '24px' }}>
      {/* Banner Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            width: '48px', height: '48px', borderRadius: '14px',
            background: 'var(--status-danger)', display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 24px rgba(244, 63, 94, 0.5)'
          }}>
            <ShieldAlert size={28} style={{ color: '#fff' }} className="pulse-icon" />
          </div>
          <div>
            <h2 style={{ fontSize: '1.4rem', fontWeight: 900, color: '#fff', letterSpacing: '-0.01em' }}>
              Unscheduled — Administrator Attention Required
            </h2>
            <p style={{ fontSize: '0.85rem', color: '#fca5a5', fontWeight: 500 }}>
              Mandatory Student Accountability Rule (BRD Section 28 & 29). One-click assignment or create a new custom class below!
            </p>
          </div>
        </div>

        {/* Accountability Stat Badges */}
        <div style={{ display: 'flex', gap: '12px' }}>
          <div style={{ background: 'rgba(0,0,0,0.4)', padding: '10px 16px', borderRadius: 'var(--radius-md)', border: '1px solid rgba(255,255,255,0.1)' }}>
            <span style={{ fontSize: '0.7rem', color: '#d1d5db', display: 'block', fontWeight: 700 }}>TOTAL CONSIDERED</span>
            <strong style={{ fontSize: '1.2rem', color: '#fff' }}>{total_students_considered}</strong>
          </div>
          <div style={{ background: 'rgba(16, 185, 129, 0.2)', padding: '10px 16px', borderRadius: 'var(--radius-md)', border: '1px solid rgba(16, 185, 129, 0.4)' }}>
            <span style={{ fontSize: '0.7rem', color: '#a7f3d0', display: 'block', fontWeight: 700 }}>SCHEDULED</span>
            <strong style={{ fontSize: '1.2rem', color: '#10b981' }}>{scheduled_count}</strong>
          </div>
          <div style={{ background: 'rgba(244, 63, 94, 0.3)', padding: '10px 16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--status-danger)' }}>
            <span style={{ fontSize: '0.7rem', color: '#fca5a5', display: 'block', fontWeight: 700 }}>ATTENTION REQUIRED</span>
            <strong style={{ fontSize: '1.2rem', color: '#f43f5e' }}>{unscheduled_count}</strong>
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
        <span style={{ fontSize: '0.75rem', color: 'var(--accent-gold)', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Zap size={14} /> One-click accept or create a brand new class directly below!
        </span>
      </div>

      {/* SEARCH OPTION FOR UNSCHEDULED STUDENTS */}
      <div style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px', background: 'rgba(0, 0, 0, 0.25)', padding: '12px 18px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: '280px', maxWidth: '500px' }}>
          <Search size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--accent-gold)' }} />
          <input
            type="text"
            placeholder="Search unscheduled student by name or ID (e.g. Harshitha, MKS00074)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '10px 14px 10px 38px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              color: '#fff',
              fontSize: '0.85rem',
              fontWeight: 500
            }}
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              style={{
                position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)',
                background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer'
              }}
            >
              <X size={16} />
            </button>
          )}
        </div>
        <span style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
          Showing {attention_records.filter(r => {
            const q = searchQuery.toLowerCase().trim();
            if (!q) return true;
            return (r.student_name || '').toLowerCase().includes(q) || (r.student_id || '').toLowerCase().includes(q) || (r.student_level || '').toLowerCase().includes(q);
          }).length} of {attention_records.length} unscheduled students
        </span>
      </div>

      {/* UNSCHEDULED STUDENT CARDS LAYOUT (NO OVERLAPPING!) */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {attention_records.length === 0 ? (
          <div style={{ background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.3)', borderRadius: 'var(--radius-md)', textAlign: 'center', color: '#10b981', padding: '30px', fontWeight: 700 }}>
            🎉 All students were successfully scheduled! No administrative attention required.
          </div>
        ) : (
          attention_records
            .filter(rec => {
              const q = searchQuery.toLowerCase().trim();
              if (!q) return true;
              return (
                (rec.student_name || '').toLowerCase().includes(q) ||
                (rec.student_id || '').toLowerCase().includes(q) ||
                (rec.student_level || '').toLowerCase().includes(q) ||
                (rec.failure_reason || '').toLowerCase().includes(q)
              );
            })
            .map(rec => {
              const recs = rec.recommendations || [];
              const isCreatingNew = activeNewClassStudentId === rec.student_id;

            return (
              <div
                key={rec.student_id}
                draggable={true}
                onDragStart={(e) => {
                  e.dataTransfer.setData("application/json", JSON.stringify({ type: "UNSCHEDULED_STUDENT", student: rec }));
                }}
                className="glass-card"
                style={{
                  padding: '20px',
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-lg)',
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                  gap: '20px',
                  alignItems: 'start'
                }}
              >
                {/* COLUMN 1: Student Metadata & Failure Analysis */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ background: 'rgba(251, 191, 36, 0.15)', padding: '8px', borderRadius: 'var(--radius-md)', color: 'var(--accent-gold)', cursor: 'grab' }}>
                      <Move size={18} title="Drag to assign to class slot in Output 2" />
                    </div>
                    <div>
                      <h3 style={{ fontSize: '1.1rem', fontWeight: 900, color: '#fff' }}>
                        {rec.student_name}
                      </h3>
                      <div style={{ fontSize: '0.775rem', color: 'var(--accent-gold)', fontWeight: 700 }}>
                        ID: {rec.student_id} · Level: <span style={{ color: '#fff' }}>{rec.student_level}</span>
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <span className="badge badge-gold" style={{ fontSize: '0.7rem' }}>
                      Batch {rec.batch_type}
                    </span>
                    <span className="badge badge-danger" style={{ fontSize: '0.7rem' }}>
                      {rec.remaining_classes} of {rec.required_classes} Missing
                    </span>
                  </div>

                  {/* Failure Reason Alert Box */}
                  <div style={{ background: 'rgba(244, 63, 94, 0.15)', border: '1px solid rgba(244, 63, 94, 0.3)', padding: '10px 14px', borderRadius: 'var(--radius-md)' }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: 800, color: '#f43f5e', marginBottom: '2px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <AlertTriangle size={14} /> REASON FOR UNSCHEDULED STATUS:
                    </div>
                    <div style={{ fontSize: '0.8rem', color: '#fecdd3', lineHeight: '1.4' }}>
                      {rec.failure_reason}
                    </div>
                  </div>

                  {/* Preferred Days & Times */}
                  <div style={{ fontSize: '0.775rem', color: 'var(--text-secondary)', background: 'rgba(0,0,0,0.2)', padding: '10px 14px', borderRadius: 'var(--radius-md)' }}>
                    <strong style={{ color: '#fff', display: 'block', marginBottom: '2px' }}>📅 PREFERRED DAYS & TIMES:</strong>
                    <div>{rec.preferred_days || 'All Days'} · {rec.preferred_time || '05:00 PM'}</div>
                  </div>
                </div>

                {/* COLUMN 2: SMART RECOMMENDATIONS & NEW CLASS BUILDER */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 800, color: 'var(--accent-gold)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Sparkles size={16} /> QUALIFIED COACH OPTIONS & EMERGENCY OVERTIME
                  </div>

                  {isCreatingNew ? (
                    <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--accent-gold)', borderRadius: 'var(--radius-md)', padding: '14px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                        <span style={{ fontSize: '0.85rem', fontWeight: 800, color: 'var(--accent-gold)' }}>
                          ➕ Create Custom Class for {rec.student_name}:
                        </span>
                        <button onClick={() => setActiveNewClassStudentId(null)} style={{ background: 'none', border: 'none', color: '#9ca3af', cursor: 'pointer' }}>
                          <X size={16} />
                        </button>
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '12px' }}>
                        <div>
                          <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '2px' }}>COACH</label>
                          <select
                            value={newCoachName}
                            onChange={e => setNewCoachName(e.target.value)}
                            style={{ width: '100%', padding: '6px', fontSize: '0.8rem', borderRadius: 'var(--radius-sm)', background: 'var(--bg-card)', border: '1px solid var(--border-color)', color: '#fff' }}
                          >
                            {coachesOptions.map((c, i) => (
                              <option key={i} value={c}>{c}</option>
                            ))}
                          </select>
                        </div>

                        <div>
                          <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '2px' }}>DATE</label>
                          <input
                            type="date"
                            value={newDate}
                            onChange={e => setNewDate(e.target.value)}
                            style={{ width: '100%', padding: '6px', fontSize: '0.8rem', borderRadius: 'var(--radius-sm)', background: 'var(--bg-card)', border: '1px solid var(--border-color)', color: '#fff' }}
                          />
                        </div>

                        <div>
                          <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '2px' }}>TIME SLOT</label>
                          <select
                            value={newTimeSlot}
                            onChange={e => setNewTimeSlot(e.target.value)}
                            style={{ width: '100%', padding: '6px', fontSize: '0.8rem', borderRadius: 'var(--radius-sm)', background: 'var(--bg-card)', border: '1px solid var(--border-color)', color: '#fff' }}
                          >
                            <option value="05:00 PM - 06:00 PM">05:00 PM - 06:00 PM</option>
                            <option value="06:00 PM - 07:00 PM">06:00 PM - 07:00 PM</option>
                            <option value="07:00 PM - 08:00 PM">07:00 PM - 08:00 PM</option>
                            <option value="04:00 PM - 05:00 PM">04:00 PM - 05:00 PM</option>
                          </select>
                        </div>

                        <div>
                          <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '2px' }}>BATCH TYPE</label>
                          <select
                            value={newBatchType}
                            onChange={e => setNewBatchType(e.target.value)}
                            style={{ width: '100%', padding: '6px', fontSize: '0.8rem', borderRadius: 'var(--radius-sm)', background: 'var(--bg-card)', border: '1px solid var(--border-color)', color: '#fff' }}
                          >
                            <option value="G">Group (G)</option>
                            <option value="L">Limited (L)</option>
                            <option value="I">Individual (I)</option>
                          </select>
                        </div>
                      </div>

                      <button
                        onClick={() => handleCreateNewClassForStudent(rec)}
                        disabled={creating}
                        className="btn btn-primary"
                        style={{ width: '100%', padding: '8px', fontSize: '0.825rem' }}
                      >
                        {creating ? 'Creating Class...' : '✓ Create & Assign New Class'}
                      </button>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {recs.length === 0 ? (
                        <div style={{ fontSize: '0.775rem', color: 'var(--text-muted)', background: 'rgba(0,0,0,0.2)', padding: '10px', borderRadius: 'var(--radius-sm)' }}>
                          No standard class slots found for level "{rec.student_level}". Use the button below to create a new custom class slot!
                        </div>
                      ) : (
                        recs.map((item, idx) => {
                          const isAssigning = assigningId === `${rec.student_id}_${item.class_id}`;
                          const isOvertime = item.is_overtime;
                          return (
                            <div
                              key={idx}
                              style={{
                                background: 'var(--bg-secondary)',
                                border: isOvertime
                                  ? '1px dashed #f59e0b'
                                  : item.day_matched
                                    ? '1px solid var(--accent-gold)'
                                    : '1px solid var(--border-color)',
                                borderRadius: 'var(--radius-md)',
                                padding: '10px 14px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                gap: '12px'
                              }}
                            >
                              <div>
                                <div style={{ fontSize: '0.85rem', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                                  <span>{item.coach_name}</span>
                                  <span style={{ color: 'var(--accent-gold)', fontWeight: 700 }}>
                                    • {item.date ? `${item.date} (${item.day})` : item.day}
                                  </span>
                                  <span style={{ opacity: 0.85, color: '#fff' }}>
                                    · {item.time_slot}
                                  </span>
                                  <span className="badge badge-gold" style={{ fontSize: '0.675rem', padding: '2px 6px' }}>
                                    {item.coach_day_classes} {item.coach_day_classes === 1 ? 'class' : 'classes'}
                                  </span>
                                </div>
                                <div style={{ fontSize: '0.75rem', color: isOvertime ? '#f59e0b' : item.day_matched ? 'var(--accent-gold)' : 'var(--text-secondary)', marginTop: '2px' }}>
                                  {item.reason} ({item.current_seats}/{item.max_seats} filled)
                                </div>
                              </div>

                              <button
                                onClick={() => handleAcceptRecommendation(rec.student_id, item.class_id, isOvertime)}
                                disabled={isAssigning}
                                className="btn btn-secondary"
                                style={{
                                  padding: '6px 12px',
                                  fontSize: '0.775rem',
                                  borderColor: isOvertime ? '#f59e0b' : 'var(--accent-gold)',
                                  color: isOvertime ? '#f59e0b' : 'var(--accent-gold)',
                                  whiteSpace: 'nowrap',
                                  fontWeight: 800
                                }}
                              >
                                {isAssigning
                                  ? 'Assigning...'
                                  : isOvertime
                                    ? '⚠️ Overtime Accept'
                                    : '✓ Accept & Assign'}
                              </button>
                            </div>
                          );
                        })
                      )}

                      {/* Button to open New Class Creator Panel */}
                      <button
                        onClick={() => {
                          setActiveNewClassStudentId(rec.student_id);
                          if (coachesOptions.length > 0) setNewCoachName(coachesOptions[0]);
                          setNewDate('2026-08-24');
                          setNewTimeSlot('05:00 PM - 06:00 PM');
                          setNewBatchType(rec.batch_type || 'G');
                        }}
                        className="btn btn-secondary"
                        style={{ padding: '8px 12px', fontSize: '0.8rem', borderColor: 'var(--accent-blue)', color: 'var(--accent-blue)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', fontWeight: 800, marginTop: '4px' }}
                      >
                        <Plus size={16} /> Create New Class Slot for {rec.student_name}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
