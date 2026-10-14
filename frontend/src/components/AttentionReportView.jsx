import React, { useState, useEffect } from 'react';
import {
  ShieldAlert, AlertTriangle, CheckCircle2, UserX, Info, Move, Sparkles, Check,
  Zap, Plus, X, Calendar, Clock, Award, Search, ChevronDown, ChevronUp, Layers,
  Lightbulb, RefreshCw, Undo2, ArrowRight, BookmarkCheck, FileText
} from 'lucide-react';
import {
  assignStudentToClass, createClassForStudent,
  getEngineSuggestions, acceptEngineSuggestion,
  getSmartBatches, getConsolidationAdvisor,
  getExceptionsList, revertException
} from '../services/api';

const DEFAULT_COACHES = ["ABINAYA", "SARAVANAN", "PRAKASH", "BATHRI", "DHAANUSH", "HEMA", "MANIKANDAN", "ARSHATH", "GURU"];

export default function AttentionReportView({ attentionData, scheduleId, onRefreshSchedule, coachList }) {
  const [assigningId, setAssigningId] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeSection, setActiveSection] = useState('unresolved'); // 'unresolved' | 'accepted_exceptions' | 'advisory'

  // Smart Batch Opportunities & Consolidation Advisor
  const [smartBatches, setSmartBatches] = useState([]);
  const [consolidationList, setConsolidationList] = useState([]);
  const [acceptedExceptions, setAcceptedExceptions] = useState([]);
  const [loadingExtras, setLoadingExtras] = useState(false);

  // Dynamic Engine suggestions per student: { [student_id]: suggestionsData }
  const [engineSuggestionsMap, setEngineSuggestionsMap] = useState({});
  const [loadingSuggestions, setLoadingSuggestions] = useState({});
  const [expandedNewSlot, setExpandedNewSlot] = useState({});

  // Custom Create New Class state per student
  const [activeNewClassStudentId, setActiveNewClassStudentId] = useState(null);
  const [newCoachName, setNewCoachName] = useState('BATHRI');
  const [newDate, setNewDate] = useState('2026-10-05');
  const [newTimeSlot, setNewTimeSlot] = useState('05:00 PM - 06:00 PM');
  const [newBatchType, setNewBatchType] = useState('G');
  const [creating, setCreating] = useState(false);

  const coachesOptions = (coachList && coachList.length > 0) ? coachList.map(c => typeof c === 'string' ? c.toUpperCase() : (c.coach_name || '').toUpperCase()) : DEFAULT_COACHES;

  useEffect(() => {
    fetchExtras();
  }, [scheduleId]);

  const fetchExtras = async () => {
    setLoadingExtras(true);
    try {
      const [sbRes, caRes, excRes] = await Promise.all([
        getSmartBatches('2026-10').catch(() => ({ opportunities: [] })),
        getConsolidationAdvisor('2026-10').catch(() => ({ advisories: [] })),
        getExceptionsList('2026-10', 'active').catch(() => ({ exceptions: [] }))
      ]);
      setSmartBatches(sbRes.opportunities || []);
      setConsolidationList(caRes.advisories || []);
      setAcceptedExceptions(excRes.exceptions || []);
    } catch (err) {
      console.warn('Failed to load extra intelligence:', err);
    } finally {
      setLoadingExtras(false);
    }
  };

  const loadStudentSuggestions = async (studentId, neededCount = 1) => {
    if (loadingSuggestions[studentId]) return;
    setLoadingSuggestions(prev => ({ ...prev, [studentId]: true }));
    try {
      const res = await getEngineSuggestions(studentId, neededCount, '2026-10');
      setEngineSuggestionsMap(prev => ({ ...prev, [studentId]: res }));
    } catch (err) {
      console.error(`Failed to load suggestions for ${studentId}:`, err);
    } finally {
      setLoadingSuggestions(prev => ({ ...prev, [studentId]: false }));
    }
  };

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
    attention_records = []
  } = attentionData;

  const scheduled_count = total_students_considered - unscheduled_count;

  // Accept a single suggestion item atomically
  const handleAcceptSuggestionItem = async (studentId, item, scheduleVersion) => {
    setAssigningId(`${studentId}_${item.class_id || item.start_time}`);
    try {
      await acceptEngineSuggestion({
        student_id: studentId,
        month: '2026-10',
        schedule_version: scheduleVersion || 1,
        suggestion_item: item,
        is_option_set: false
      });
      // Invalidate cached suggestions for this student
      setEngineSuggestionsMap(prev => {
        const copy = { ...prev };
        delete copy[studentId];
        return copy;
      });
      if (onRefreshSchedule) await onRefreshSchedule();
      fetchExtras();
    } catch (err) {
      alert('Failed to accept suggestion: ' + (err.response?.data?.detail || err.message));
    } finally {
      setAssigningId(null);
    }
  };

  // Accept an entire multi-class option set atomically
  const handleAcceptOptionSet = async (studentId, optionSet, scheduleVersion) => {
    setAssigningId(`${studentId}_set_${optionSet.set_id}`);
    try {
      await acceptEngineSuggestion({
        student_id: studentId,
        month: '2026-10',
        schedule_version: scheduleVersion || 1,
        is_option_set: true,
        option_set_items: optionSet.items
      });
      setEngineSuggestionsMap(prev => {
        const copy = { ...prev };
        delete copy[studentId];
        return copy;
      });
      if (onRefreshSchedule) await onRefreshSchedule();
      fetchExtras();
    } catch (err) {
      alert('Failed to accept option set: ' + (err.response?.data?.detail || err.message));
    } finally {
      setAssigningId(null);
    }
  };

  // Legacy fallback assignment handler
  const handleAcceptRecommendation = async (studentId, classId, isOvertime) => {
    if (isOvertime) {
      const confirmOvertime = window.confirm(
        "⚠️ EMERGENCY OVERTIME CONFIRMATION:\nThis assignment exceeds standard limits. Do you want to approve emergency overtime?"
      );
      if (!confirmOvertime) return;
    }
    setAssigningId(`${studentId}_${classId}`);
    try {
      await assignStudentToClass(scheduleId, studentId, classId);
      if (onRefreshSchedule) await onRefreshSchedule();
      fetchExtras();
    } catch (err) {
      alert('Failed to assign student: ' + (err.response?.data?.detail || err.message));
    } finally {
      setAssigningId(null);
    }
  };

  // Manual class creation
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
      fetchExtras();
    } catch (err) {
      alert('Failed to create new class: ' + (err.response?.data?.detail || err.message));
    } finally {
      setCreating(false);
    }
  };

  // Revert accepted exception
  const handleRevertExceptionRecord = async (exceptionId) => {
    if (!window.confirm(`Revert exception ${exceptionId}? This will safely remove this manual override.`)) return;
    try {
      await revertException(exceptionId, '2026-10');
      if (onRefreshSchedule) await onRefreshSchedule();
      fetchExtras();
    } catch (err) {
      alert('Failed to revert exception: ' + (err.response?.data?.detail || err.message));
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
              Output 3 — Attention (Exception & Assignment Layer)
            </h2>
            <p style={{ fontSize: '0.85rem', color: '#fca5a5', fontWeight: 500 }}>
              The central administrator-intervention hub. Option Ladder (T1–T7), Smart Batch Pooling, and Multi-Class Option Sets.
            </p>
          </div>
        </div>

        {/* Accountability Stat Badges */}
        <div style={{ display: 'flex', gap: '12px' }}>
          <div style={{ background: 'rgba(0,0,0,0.4)', padding: '10px 16px', borderRadius: 'var(--radius-md)', border: '1px solid rgba(255,255,255,0.1)' }}>
            <span style={{ fontSize: '0.7rem', color: '#d1d5db', display: 'block', fontWeight: 700 }}>TOTAL STUDENTS</span>
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

      {/* SECTION NAVIGATION TABS */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
        <button
          onClick={() => setActiveSection('unresolved')}
          className={`btn ${activeSection === 'unresolved' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ padding: '8px 16px', fontSize: '0.825rem', fontWeight: 800 }}
        >
          <ShieldAlert size={15} /> Unresolved Attention Records ({attention_records.length})
        </button>

        <button
          onClick={() => setActiveSection('accepted_exceptions')}
          className={`btn ${activeSection === 'accepted_exceptions' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ padding: '8px 16px', fontSize: '0.825rem', fontWeight: 800 }}
        >
          <BookmarkCheck size={15} /> Accepted Exceptions (ⓒ) ({acceptedExceptions.length})
        </button>

        <button
          onClick={() => setActiveSection('advisory')}
          className={`btn ${activeSection === 'advisory' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ padding: '8px 16px', fontSize: '0.825rem', fontWeight: 800 }}
        >
          <Lightbulb size={15} /> Consolidation Advisor ({consolidationList.length})
        </button>
      </div>

      {/* ==================================================================== */}
      {/* SECTION 1: SMART BATCH OPPORTUNITIES CARD (TOP)                       */}
      {/* ==================================================================== */}
      {activeSection === 'unresolved' && smartBatches.length > 0 && (
        <div style={{
          background: 'linear-gradient(135deg, rgba(234, 179, 8, 0.15) 0%, rgba(217, 119, 6, 0.1) 100%)',
          border: '1.5px solid var(--accent-gold)',
          borderRadius: 'var(--radius-lg)',
          padding: '18px 20px',
          marginBottom: '24px',
          boxShadow: '0 10px 25px -5px rgba(234, 179, 8, 0.2)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ background: 'var(--accent-gold)', color: '#000', padding: '6px', borderRadius: '8px' }}>
                <Sparkles size={20} />
              </div>
              <div>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 900, color: '#fff', margin: 0 }}>
                  Smart Batch Opportunities (Pooled Multi-Student Openings)
                </h3>
                <p style={{ fontSize: '0.75rem', color: '#fde68a', margin: '2px 0 0 0' }}>
                  The engine scanned unresolved records and found students sharing levels & availability that can be resolved together in 1 pooled slot.
                </p>
              </div>
            </div>
            <span className="badge badge-gold" style={{ fontSize: '0.75rem', padding: '4px 10px' }}>
              {smartBatches.length} Pooling Matches
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '12px' }}>
            {smartBatches.map(opp => (
              <div
                key={opp.opportunity_id}
                style={{
                  background: 'rgba(15, 23, 42, 0.85)',
                  border: '1px solid rgba(251, 191, 36, 0.4)',
                  borderRadius: 'var(--radius-md)',
                  padding: '14px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <strong style={{ fontSize: '0.9rem', color: '#fff' }}>{opp.title}</strong>
                  <span className="badge badge-gold" style={{ fontSize: '0.7rem' }}>
                    Resolves {opp.student_count} Students
                  </span>
                </div>
                <div style={{ fontSize: '0.775rem', color: '#cbd5e1' }}>
                  Suggested Coach: <strong style={{ color: 'var(--accent-gold)' }}>{opp.suggested_coach}</strong> · {opp.day} at {opp.time_slot}
                </div>
                <div style={{ fontSize: '0.725rem', color: '#94a3b8' }}>
                  Students: {opp.student_names.join(', ')}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#34d399', fontWeight: 700, marginTop: '4px' }}>
                  💡 {opp.impact_summary}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ==================================================================== */}
      {/* SECTION 2: ACCEPTED EXCEPTIONS (ⓒ) AUDIT SECTION                     */}
      {/* ==================================================================== */}
      {activeSection === 'accepted_exceptions' && (
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-lg)', padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#fff', margin: 0 }}>
                Accepted Exceptions (ⓒ Overlay Audit)
              </h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
                Single-occurrence administrative modifications and approved rule exceptions. These are active and not counted as unresolved.
              </p>
            </div>
            <button onClick={fetchExtras} className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.75rem' }}>
              <RefreshCw size={14} /> Refresh
            </button>
          </div>

          {acceptedExceptions.length === 0 ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
              No accepted exceptions currently recorded.
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.825rem' }}>
                <thead>
                  <tr style={{ background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                    <th style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>ID</th>
                    <th style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>Date & Slot</th>
                    <th style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>Coach</th>
                    <th style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>Action</th>
                    <th style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>Affected Students</th>
                    <th style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>Reason / Approved By</th>
                    <th style={{ padding: '10px 12px', color: 'var(--text-secondary)', textAlign: 'center' }}>Revert</th>
                  </tr>
                </thead>
                <tbody>
                  {acceptedExceptions.map(exc => (
                    <tr key={exc.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ padding: '10px 12px', fontFamily: 'monospace', color: 'var(--accent-gold)' }}>{exc.id}</td>
                      <td style={{ padding: '10px 12px' }}>{exc.date} · {exc.start_time}</td>
                      <td style={{ padding: '10px 12px', fontWeight: 700 }}>{exc.coach_id}</td>
                      <td style={{ padding: '10px 12px' }}>
                        <span className="badge badge-gold" style={{ fontSize: '0.675rem' }}>{exc.action_type}</span>
                      </td>
                      <td style={{ padding: '10px 12px' }}>{(exc.affected_student_ids || []).join(', ')}</td>
                      <td style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>
                        {exc.reason || 'Manual override'} <span style={{ opacity: 0.7 }}>({exc.created_by || 'Admin'})</span>
                      </td>
                      <td style={{ padding: '10px 12px', textAlign: 'center' }}>
                        <button
                          onClick={() => handleRevertExceptionRecord(exc.id)}
                          className="btn btn-secondary"
                          style={{ padding: '4px 10px', fontSize: '0.725rem', color: '#f87171', borderColor: 'rgba(239,68,68,0.4)' }}
                        >
                          <Undo2 size={13} /> Revert
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ==================================================================== */}
      {/* SECTION 3: READ-ONLY CONSOLIDATION ADVISOR                            */}
      {/* ==================================================================== */}
      {activeSection === 'advisory' && (
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-lg)', padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#fff', margin: 0 }}>
                Read-Only Consolidation Advisor (Section 9)
              </h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
                Lists underfilled batches (single-student Group/Limited) that could be merged next month with expected seat gain. Immutable baseline is never auto-applied.
              </p>
            </div>
            <button onClick={fetchExtras} className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.75rem' }}>
              <RefreshCw size={14} /> Refresh
            </button>
          </div>

          {consolidationList.length === 0 ? (
            <div style={{ padding: '40px', textAlign: 'center', color: '#10b981', fontWeight: 700 }}>
              🎉 Zero single-student underfilled Group/Limited batches found. Batch fill efficiency is optimal!
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '14px' }}>
              {consolidationList.map((adv, idx) => (
                <div
                  key={idx}
                  style={{
                    background: 'var(--bg-secondary)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-md)',
                    padding: '14px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span className="badge badge-gold" style={{ fontSize: '0.7rem' }}>
                      Batch {adv.batch_type} · {adv.student_level}
                    </span>
                    <span style={{ fontSize: '0.725rem', color: '#34d399', fontWeight: 700 }}>
                      +{adv.potential_seats_saved} Seat Gain
                    </span>
                  </div>
                  <strong style={{ fontSize: '0.85rem', color: '#fff' }}>
                    {adv.date} ({adv.day}) · {adv.time_slot} · Coach {adv.coach_name}
                  </strong>
                  <div style={{ fontSize: '0.775rem', color: 'var(--text-secondary)' }}>
                    Enrolled: <strong>{adv.enrolled_student}</strong>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#fde68a', marginTop: '4px' }}>
                    💡 {adv.suggestion}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ==================================================================== */}
      {/* SECTION 4: UNRESOLVED ATTENTION RECORDS LIST                          */}
      {/* ==================================================================== */}
      {activeSection === 'unresolved' && (
        <>
          {/* Search bar */}
          <div style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px', background: 'rgba(0, 0, 0, 0.25)', padding: '12px 18px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <div style={{ position: 'relative', flex: 1, minWidth: '280px', maxWidth: '500px' }}>
              <Search size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--accent-gold)' }} />
              <input
                type="text"
                placeholder="Search unscheduled student by name or ID..."
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
              }).length} of {attention_records.length} unresolved records
            </span>
          </div>

          {/* Cards List */}
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
                  const sid = rec.student_id;
                  const neededCount = rec.remaining_classes || (rec.required_classes - rec.scheduled_classes) || 1;
                  const dynSuggestions = engineSuggestionsMap[sid];
                  const isLoadingDyn = loadingSuggestions[sid];
                  const isCreatingNew = activeNewClassStudentId === sid;

                  return (
                    <div
                      key={sid}
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
                          <div style={{ background: 'rgba(251, 191, 36, 0.15)', padding: '8px', borderRadius: 'var(--radius-md)', color: 'var(--accent-gold)' }}>
                            <Move size={18} />
                          </div>
                          <div>
                            <h3 style={{ fontSize: '1.1rem', fontWeight: 900, color: '#fff', margin: 0 }}>
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
                            <AlertTriangle size={14} /> REASON FOR ATTENTION STATUS:
                          </div>
                          <div style={{ fontSize: '0.8rem', color: '#fecdd3', lineHeight: '1.4' }}>
                            {rec.failure_reason}
                          </div>
                        </div>

                        {/* Button to Load Engine Option Ladder Suggestions */}
                        {!dynSuggestions && (
                          <button
                            onClick={() => loadStudentSuggestions(sid, neededCount)}
                            disabled={isLoadingDyn}
                            className="btn btn-secondary"
                            style={{
                              padding: '8px 14px',
                              fontSize: '0.8rem',
                              fontWeight: 800,
                              borderColor: 'var(--accent-gold)',
                              color: 'var(--accent-gold)',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              gap: '6px'
                            }}
                          >
                            <Sparkles size={15} />
                            {isLoadingDyn ? 'Calculating Option Ladder...' : '⚡ Generate Ranked Suggestions'}
                          </button>
                        )}
                      </div>

                      {/* COLUMN 2: OPTION LADDER SUGGESTIONS & ACCEPTANCE */}
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        <div style={{ fontSize: '0.8rem', fontWeight: 800, color: 'var(--accent-gold)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <Sparkles size={16} /> ENGINE SUGGESTIONS (OPTION LADDER)
                          </span>
                          {dynSuggestions && (
                            <button
                              onClick={() => loadStudentSuggestions(sid, neededCount)}
                              style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.7rem' }}
                            >
                              <RefreshCw size={12} /> Refresh
                            </button>
                          )}
                        </div>

                        {/* CASE A: MULTI-CLASS OPTION SETS (NEEDED > 1) */}
                        {dynSuggestions?.mode === 'multi_class' && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                              Multi-class solver found <strong>{dynSuggestions.option_sets?.length || 0}</strong> complete option sets covering all {neededCount} required classes:
                            </div>
                            {(dynSuggestions.option_sets || []).map((setObj) => (
                              <div
                                key={setObj.set_id}
                                style={{
                                  background: 'var(--bg-secondary)',
                                  border: '1px solid var(--accent-gold)',
                                  borderRadius: 'var(--radius-md)',
                                  padding: '12px 14px',
                                  display: 'flex',
                                  flexDirection: 'column',
                                  gap: '8px'
                                }}
                              >
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                  <div>
                                    <strong style={{ fontSize: '0.85rem', color: '#fff' }}>{setObj.set_name}</strong>
                                    <div style={{ fontSize: '0.725rem', color: 'var(--text-secondary)' }}>{setObj.description}</div>
                                  </div>
                                  <button
                                    onClick={() => handleAcceptOptionSet(sid, setObj, dynSuggestions.schedule_version)}
                                    disabled={assigningId === `${sid}_set_${setObj.set_id}`}
                                    className="btn btn-primary"
                                    style={{ padding: '6px 12px', fontSize: '0.75rem', fontWeight: 800 }}
                                  >
                                    {assigningId === `${sid}_set_${setObj.set_id}` ? 'Accepting...' : '✓ Accept Complete Set'}
                                  </button>
                                </div>
                                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', fontSize: '0.7rem', color: '#cbd5e1' }}>
                                  <span>Seats Used: <strong style={{ color: '#34d399' }}>{setObj.existing_seats_used}</strong></span>
                                  <span>New Slots: <strong style={{ color: setObj.new_slots_needed > 0 ? '#f59e0b' : '#34d399' }}>{setObj.new_slots_needed}</strong></span>
                                  <span>Pattern Match: <strong>{setObj.pattern_match}</strong></span>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* CASE B: SINGLE-CLASS RANKED T1-T7 SUGGESTIONS */}
                        {dynSuggestions?.mode === 'single_class' && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            {/* 1. Existing batch options first (T1-T3) */}
                            {(() => {
                              const existingOptions = (dynSuggestions.suggestions || []).filter(s => ['T1', 'T2', 'T3'].includes(s.tier));
                              const newSlotOptions = (dynSuggestions.suggestions || []).filter(s => ['T4', 'T5', 'T6'].includes(s.tier));
                              const isNewExpanded = expandedNewSlot[sid] || existingOptions.length === 0;

                              return (
                                <>
                                  <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#34d399', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                    ✓ Join Existing Batch ({existingOptions.length} options)
                                  </div>
                                  {existingOptions.length === 0 ? (
                                    <div style={{ fontSize: '0.725rem', color: 'var(--text-muted)', background: 'rgba(0,0,0,0.2)', padding: '8px', borderRadius: '4px' }}>
                                      No viable existing batch vacancy available this month.
                                    </div>
                                  ) : (
                                    existingOptions.map((item, idx) => (
                                      <div
                                        key={idx}
                                        style={{
                                          background: 'var(--bg-secondary)',
                                          border: '1px solid var(--border-color)',
                                          borderRadius: 'var(--radius-md)',
                                          padding: '10px 12px',
                                          display: 'flex',
                                          alignItems: 'center',
                                          justifyContent: 'space-between',
                                          gap: '8px'
                                        }}
                                      >
                                        <div>
                                          <div style={{ fontSize: '0.825rem', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                            <span className="badge badge-gold" style={{ fontSize: '0.65rem' }}>{item.tier}</span>
                                            <span>Coach {item.coach_id}</span>
                                            <span style={{ color: 'var(--accent-gold)' }}>• {item.date}</span>
                                            <span>· {item.start_time}</span>
                                          </div>
                                          <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                                            Fill: {item.fill_before} → {item.fill_after} · Purity: {item.level_purity} · Coach Rank: {item.coach_priority_rank}
                                          </div>
                                        </div>
                                        <button
                                          onClick={() => handleAcceptSuggestionItem(sid, item, dynSuggestions.schedule_version)}
                                          disabled={assigningId === `${sid}_${item.class_id || item.start_time}`}
                                          className="btn btn-secondary"
                                          style={{ padding: '6px 12px', fontSize: '0.75rem', color: 'var(--accent-gold)', borderColor: 'var(--accent-gold)', fontWeight: 800 }}
                                        >
                                          {assigningId === `${sid}_${item.class_id || item.start_time}` ? 'Assigning...' : '✓ Accept'}
                                        </button>
                                      </div>
                                    ))
                                  )}

                                  {/* 2. New Slot options (T4-T6) collapsed unless expanded */}
                                  <div style={{ marginTop: '6px' }}>
                                    <button
                                      onClick={() => setExpandedNewSlot(prev => ({ ...prev, [sid]: !prev[sid] }))}
                                      style={{
                                        background: 'none',
                                        border: 'none',
                                        color: '#60a5fa',
                                        fontSize: '0.75rem',
                                        fontWeight: 700,
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '4px'
                                      }}
                                    >
                                      {isNewExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                                      {isNewExpanded ? 'Hide New Slot Suggestions' : `Open a New Slot (${newSlotOptions.length} proposed)`}
                                    </button>

                                    {isNewExpanded && (
                                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '6px' }}>
                                        {newSlotOptions.map((item, idx) => (
                                          <div
                                            key={idx}
                                            style={{
                                              background: 'rgba(59, 130, 246, 0.1)',
                                              border: '1px solid rgba(59, 130, 246, 0.3)',
                                              borderRadius: 'var(--radius-md)',
                                              padding: '10px 12px',
                                              display: 'flex',
                                              alignItems: 'center',
                                              justifyContent: 'space-between',
                                              gap: '8px'
                                            }}
                                          >
                                            <div>
                                              <div style={{ fontSize: '0.825rem', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                                <span className="badge badge-blue" style={{ fontSize: '0.65rem' }}>{item.tier}</span>
                                                <span>New Slot: Coach {item.coach_id}</span>
                                                <span style={{ color: '#60a5fa' }}>• {item.date}</span>
                                                <span>· {item.start_time}</span>
                                              </div>
                                              <div style={{ fontSize: '0.7rem', color: '#93c5fd', marginTop: '2px' }}>
                                                New slot opens back-to-back with coach's schedule
                                              </div>
                                            </div>
                                            <button
                                              onClick={() => handleAcceptSuggestionItem(sid, item, dynSuggestions.schedule_version)}
                                              disabled={assigningId === `${sid}_${item.class_id || item.start_time}`}
                                              className="btn btn-secondary"
                                              style={{ padding: '6px 12px', fontSize: '0.75rem', color: '#60a5fa', borderColor: '#60a5fa', fontWeight: 800 }}
                                            >
                                              {assigningId === `${sid}_${item.class_id || item.start_time}` ? 'Assigning...' : '✓ Open Slot'}
                                            </button>
                                          </div>
                                        ))}
                                      </div>
                                    )}
                                  </div>

                                  {/* 3. 'Why not an existing slot?' panel */}
                                  {dynSuggestions.reasons_rejected_summary && dynSuggestions.reasons_rejected_summary.length > 0 && (
                                    <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(255,255,255,0.06)', marginTop: '8px' }}>
                                      <strong style={{ fontSize: '0.725rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
                                        🔍 Why not an existing slot? (Evaluated batches):
                                      </strong>
                                      <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                                        {dynSuggestions.reasons_rejected_summary.map((r, rIdx) => (
                                          <div key={rIdx} style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                                            • {r}
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                                </>
                              );
                            })()}
                          </div>
                        )}

                        {/* Fallback to legacy recommendations if engine suggestions haven't been triggered */}
                        {!dynSuggestions && rec.recommendations && rec.recommendations.length > 0 && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            {rec.recommendations.map((item, idx) => (
                              <div
                                key={idx}
                                style={{
                                  background: 'var(--bg-secondary)',
                                  border: '1px solid var(--border-color)',
                                  borderRadius: 'var(--radius-md)',
                                  padding: '8px 12px',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'space-between',
                                  gap: '8px'
                                }}
                              >
                                <div>
                                  <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#fff' }}>
                                    {item.coach_name} · {item.date || item.day} · {item.time_slot}
                                  </div>
                                  <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                                    {item.reason} ({item.current_seats}/{item.max_seats} filled)
                                  </div>
                                </div>
                                <button
                                  onClick={() => handleAcceptRecommendation(sid, item.class_id, item.is_overtime)}
                                  className="btn btn-secondary"
                                  style={{ padding: '5px 10px', fontSize: '0.725rem', color: 'var(--accent-gold)' }}
                                >
                                  ✓ Accept
                                </button>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Custom Class Creator Panel Trigger */}
                        <button
                          onClick={() => {
                            setActiveNewClassStudentId(sid);
                            if (coachesOptions.length > 0) setNewCoachName(coachesOptions[0]);
                            setNewDate('2026-10-05');
                            setNewTimeSlot('05:00 PM - 06:00 PM');
                            setNewBatchType(rec.batch_type || 'G');
                          }}
                          className="btn btn-secondary"
                          style={{ padding: '8px 12px', fontSize: '0.8rem', borderColor: 'var(--accent-blue)', color: 'var(--accent-blue)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', fontWeight: 800, marginTop: '6px' }}
                        >
                          <Plus size={15} /> Create Custom Class Slot for {rec.student_name}
                        </button>
                      </div>
                    </div>
                  );
                })
            )}
          </div>
        </>
      )}
    </div>
  );
}
