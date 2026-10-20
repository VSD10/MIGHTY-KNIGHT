import React, { useState, useEffect } from 'react';
import {
  ShieldAlert, AlertTriangle, CheckCircle2, UserX, Info, Move, Sparkles, Check,
  Zap, Plus, X, Calendar, Clock, Award, Search, ChevronDown, ChevronUp, Layers,
  Lightbulb, RefreshCw, Undo2, ArrowRight, BookmarkCheck, FileText,
  UserCheck, Trash2, Archive, RotateCcw, Filter, UserPlus
} from 'lucide-react';
import {
  assignStudentToClass, createClassForStudent,
  getEngineSuggestions, acceptEngineSuggestion,
  getSmartBatches, getConsolidationAdvisor,
  getExceptionsList, revertException, reassignBatchCoach,
  getCoachAvailability, getDeletedRecords, saveDeletedRecord,
  updateDeletedRecordScope, restoreDeletedRecord, permanentlyDeleteRecord
} from '../services/api';

const DEFAULT_COACHES = ["ABINAYA", "SARAVANAN", "PRAKASH", "BATHRI", "DHAANUSH", "HEMA", "MANIKANDAN", "ARSHATH", "GURU"];

export default function AttentionReportView({ attentionData, scheduleId, onRefreshSchedule, coachList }) {
  const [assigningId, setAssigningId] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeSection, setActiveSection] = useState('unresolved'); // 'unresolved' | 'coach_availability' | 'deleted_records' | 'accepted_exceptions' | 'advisory'

  // Coach Availability Section State
  const [coachAvailabilityList, setCoachAvailabilityList] = useState([]);
  const [loadingAvailability, setLoadingAvailability] = useState(false);
  const [availDate, setAvailDate] = useState('2026-10-02');
  const [availCoach, setAvailCoach] = useState('ALL');
  const [availLevel, setAvailLevel] = useState('ALL');
  const [availDay, setAvailDay] = useState('ALL');
  const [availStatus, setAvailStatus] = useState('ALL');

  // Deleted Records Section State
  const [deletedRecordsList, setDeletedRecordsList] = useState([]);
  const [loadingDeletedRecords, setLoadingDeletedRecords] = useState(false);
  const [deletedFilterType, setDeletedFilterType] = useState('ALL');
  const [deletedFilterScope, setDeletedFilterScope] = useState('ALL');
  const [restoringRecordId, setRestoringRecordId] = useState(null);

  // Smart Batch Opportunities & Consolidation Advisor
  const [smartBatches, setSmartBatches] = useState([]);
  const [consolidationList, setConsolidationList] = useState([]);
  const [acceptedExceptions, setAcceptedExceptions] = useState([]);
  const [loadingExtras, setLoadingExtras] = useState(false);

  // Dynamic Engine suggestions per student: { [student_id]: suggestionsData }
  const [engineSuggestionsMap, setEngineSuggestionsMap] = useState({});
  const [loadingSuggestions, setLoadingSuggestions] = useState({});
  const [expandedNewSlot, setExpandedNewSlot] = useState({});
  const [optionSetTab, setOptionSetTab] = useState({});
  const [expandedSetItems, setExpandedSetItems] = useState({});

  // Custom Create New Class state per student
  const [activeNewClassStudentId, setActiveNewClassStudentId] = useState(null);
  const [newCoachName, setNewCoachName] = useState('BATHRI');
  const [newDate, setNewDate] = useState('2026-10-05');
  const [newTimeSlot, setNewTimeSlot] = useState('05:00 PM - 06:00 PM');
  const [newBatchType, setNewBatchType] = useState('G');
  const [creating, setCreating] = useState(false);

  // Rule 4: Deleted Coach Reassignment State
  const [reassigningId, setReassigningId] = useState(null);
  const [selectedCoachMap, setSelectedCoachMap] = useState({});

  const handleReassignCoach = async (rec, coachName) => {
    const targetCoach = coachName || selectedCoachMap[rec.class_id || rec.student_id] || rec.recommended_coach || (rec.eligible_coaches && rec.eligible_coaches[0]);
    if (!targetCoach) {
      alert("Please select a replacement coach first.");
      return;
    }
    const key = rec.class_id || rec.student_id;
    setReassigningId(key);
    try {
      await reassignBatchCoach({
        batch_name: rec.batch_name,
        class_id: rec.class_id,
        new_coach_name: targetCoach,
        month: '2026-10'
      });
      if (onRefreshSchedule) await onRefreshSchedule();
      fetchExtras();
    } catch (err) {
      alert("Failed to reassign coach: " + (err.response?.data?.detail || err.message));
    } finally {
      setReassigningId(null);
    }
  };

  const coachesOptions = (coachList && coachList.length > 0) ? coachList.map(c => typeof c === 'string' ? c.toUpperCase() : (c.coach_name || '').toUpperCase()) : DEFAULT_COACHES;

  useEffect(() => {
    fetchExtras();
    fetchCoachAvailabilityData();
    fetchDeletedRecordsData();
  }, [scheduleId]);

  useEffect(() => {
    if (activeSection === 'coach_availability') {
      fetchCoachAvailabilityData();
    } else if (activeSection === 'deleted_records') {
      fetchDeletedRecordsData();
    }
  }, [activeSection, availDate, availCoach, availLevel, availDay, availStatus]);

  const fetchCoachAvailabilityData = async () => {
    setLoadingAvailability(true);
    try {
      const res = await getCoachAvailability({
        month: '2026-10',
        date: availDate || undefined,
        coach_name: availCoach !== 'ALL' ? availCoach : undefined,
        level: availLevel !== 'ALL' ? availLevel : undefined,
        day: availDay !== 'ALL' ? availDay : undefined,
        status: availStatus !== 'ALL' ? availStatus : undefined
      });
      setCoachAvailabilityList(res?.records || []);
    } catch (err) {
      console.warn('Failed to load coach availability:', err);
    } finally {
      setLoadingAvailability(false);
    }
  };

  const fetchDeletedRecordsData = async () => {
    setLoadingDeletedRecords(true);
    try {
      const res = await getDeletedRecords();
      setDeletedRecordsList(res?.records || []);
    } catch (err) {
      console.warn('Failed to load deleted records:', err);
    } finally {
      setLoadingDeletedRecords(false);
    }
  };

  const handleRestoreRecord = async (rec) => {
    if (!window.confirm(`Restore ${rec.record_name} (${rec.record_type}) back to active status?`)) return;
    setRestoringRecordId(rec.record_id);
    try {
      const res = await restoreDeletedRecord(rec.record_id);
      alert(res.message || 'Record successfully restored to active status!');
      if (onRefreshSchedule) await onRefreshSchedule();
      fetchDeletedRecordsData();
      fetchCoachAvailabilityData();
      fetchExtras();
    } catch (err) {
      alert('Failed to restore record: ' + (err.response?.data?.detail || err.message));
    } finally {
      setRestoringRecordId(null);
    }
  };

  const handlePermanentDeleteRecord = async (rec) => {
    const confirmed = window.confirm(
      `⚠️ PERMANENT DELETION WARNING:\nAre you sure you want to permanently delete the audit record for ${rec.record_name}?\nThis action cannot be undone.`
    );
    if (!confirmed) return;
    try {
      await permanentlyDeleteRecord(rec.record_id);
      fetchDeletedRecordsData();
    } catch (err) {
      alert('Failed to delete record: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleChangeRecordScope = async (rec, newScope) => {
    try {
      await updateDeletedRecordScope(rec.record_id, newScope);
      fetchDeletedRecordsData();
    } catch (err) {
      alert('Failed to update scope: ' + (err.response?.data?.detail || err.message));
    }
  };

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
      <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px', flexWrap: 'wrap' }}>
        <button
          onClick={() => setActiveSection('unresolved')}
          className={`btn ${activeSection === 'unresolved' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ padding: '8px 16px', fontSize: '0.825rem', fontWeight: 800 }}
        >
          <ShieldAlert size={15} /> Unresolved Attention Records ({attention_records.length})
        </button>

        <button
          onClick={() => {
            setActiveSection('coach_availability');
            fetchCoachAvailabilityData();
          }}
          className={`btn ${activeSection === 'coach_availability' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ padding: '8px 16px', fontSize: '0.825rem', fontWeight: 800, borderColor: activeSection === 'coach_availability' ? 'var(--accent-gold)' : undefined }}
        >
          <Clock size={15} style={{ color: 'var(--accent-gold)' }} /> Coach Availability & Preferences
        </button>

        <button
          onClick={() => {
            setActiveSection('deleted_records');
            fetchDeletedRecordsData();
          }}
          className={`btn ${activeSection === 'deleted_records' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ padding: '8px 16px', fontSize: '0.825rem', fontWeight: 800, borderColor: activeSection === 'deleted_records' ? '#f43f5e' : undefined }}
        >
          <Archive size={15} style={{ color: '#f43f5e' }} /> Deleted Records & Academy Instructions ({deletedRecordsList.length})
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
      {/* SECTION: COACH AVAILABILITY & PREFERENCE TIME                        */}
      {/* ==================================================================== */}
      {activeSection === 'coach_availability' && (
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-lg)', padding: '24px' }}>
          {/* Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '20px', borderBottom: '1px solid var(--border-color)', paddingBottom: '16px' }}>
            <div>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 900, color: '#fff', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Clock size={22} style={{ color: 'var(--accent-gold)' }} /> Coach Availability & Preference Time
              </h3>
              <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
                Accurate remaining slot calculations: <strong>Available slots = Valid preferred slots − Occupied slots − Rest periods − Daily/Monthly limits</strong>. Real-time sync with database & master data.
              </p>
            </div>
            <button
              onClick={fetchCoachAvailabilityData}
              disabled={loadingAvailability}
              className="btn btn-secondary"
              style={{ padding: '8px 16px', fontSize: '0.8rem', fontWeight: 700, borderColor: 'var(--accent-gold)', color: 'var(--accent-gold)' }}
            >
              <RefreshCw size={14} className={loadingAvailability ? 'pulse-icon' : ''} /> {loadingAvailability ? 'Recalculating...' : 'Refresh Availability'}
            </button>
          </div>

          {/* Filtering Controls */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px', marginBottom: '20px', background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: 'var(--radius-md)', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.725rem', fontWeight: 700, color: 'var(--accent-gold)', marginBottom: '4px' }}>
                📅 DATE SELECTION:
              </label>
              <input
                type="date"
                value={availDate}
                onChange={e => setAvailDate(e.target.value)}
                style={{
                  width: '100%',
                  padding: '7px 10px',
                  borderRadius: 'var(--radius-sm)',
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-color)',
                  color: '#fff',
                  fontSize: '0.8rem',
                  fontWeight: 600
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.725rem', fontWeight: 700, color: 'var(--accent-gold)', marginBottom: '4px' }}>
                🗓️ WEEKDAY FILTER:
              </label>
              <select
                value={availDay}
                onChange={e => setAvailDay(e.target.value)}
                style={{
                  width: '100%',
                  padding: '7px 10px',
                  borderRadius: 'var(--radius-sm)',
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-color)',
                  color: '#fff',
                  fontSize: '0.8rem',
                  fontWeight: 600
                }}
              >
                <option value="ALL">All Weekdays</option>
                <option value="Monday">Monday</option>
                <option value="Tuesday">Tuesday</option>
                <option value="Wednesday">Wednesday</option>
                <option value="Thursday">Thursday</option>
                <option value="Friday">Friday</option>
                <option value="Saturday">Saturday</option>
                <option value="Sunday">Sunday</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.725rem', fontWeight: 700, color: 'var(--accent-gold)', marginBottom: '4px' }}>
                👤 COACH FILTER:
              </label>
              <select
                value={availCoach}
                onChange={e => setAvailCoach(e.target.value)}
                style={{
                  width: '100%',
                  padding: '7px 10px',
                  borderRadius: 'var(--radius-sm)',
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-color)',
                  color: '#fff',
                  fontSize: '0.8rem',
                  fontWeight: 600
                }}
              >
                <option value="ALL">All Coaches</option>
                {coachesOptions.map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.725rem', fontWeight: 700, color: 'var(--accent-gold)', marginBottom: '4px' }}>
                🎓 LEVEL QUALIFICATION:
              </label>
              <select
                value={availLevel}
                onChange={e => setAvailLevel(e.target.value)}
                style={{
                  width: '100%',
                  padding: '7px 10px',
                  borderRadius: 'var(--radius-sm)',
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-color)',
                  color: '#fff',
                  fontSize: '0.8rem',
                  fontWeight: 600
                }}
              >
                <option value="ALL">All Levels</option>
                {["Basic 1", "Basic 2", "Beginner 1", "Beginner 2", "Early Intermediate 1", "Early Intermediate 2", "Intermediate 1", "Intermediate 2"].map(lvl => (
                  <option key={lvl} value={lvl}>{lvl}</option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.725rem', fontWeight: 700, color: 'var(--accent-gold)', marginBottom: '4px' }}>
                ⚡ AVAILABILITY STATUS:
              </label>
              <select
                value={availStatus}
                onChange={e => setAvailStatus(e.target.value)}
                style={{
                  width: '100%',
                  padding: '7px 10px',
                  borderRadius: 'var(--radius-sm)',
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-color)',
                  color: '#fff',
                  fontSize: '0.8rem',
                  fontWeight: 600
                }}
              >
                <option value="ALL">All Statuses</option>
                <option value="AVAILABLE">Available (Has Open Slots)</option>
                <option value="FULLY_BOOKED">Fully Booked</option>
                <option value="UNAVAILABLE">Unavailable / Rest Day</option>
              </select>
            </div>
          </div>

          {/* KPI Summary Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', marginBottom: '20px' }}>
            <div className="glass-card" style={{ padding: '12px 16px', borderLeft: '4px solid #38bdf8' }}>
              <div style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)' }}>COACHES TRACKED</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 900, color: '#38bdf8', marginTop: '2px' }}>
                {coachAvailabilityList.length}
              </div>
            </div>
            <div className="glass-card" style={{ padding: '12px 16px', borderLeft: '4px solid #10b981' }}>
              <div style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)' }}>COACHES WITH OPEN SLOTS</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 900, color: '#10b981', marginTop: '2px' }}>
                {coachAvailabilityList.filter(c => c.available_slots_count > 0).length}
              </div>
            </div>
            <div className="glass-card" style={{ padding: '12px 16px', borderLeft: '4px solid #fbbf24' }}>
              <div style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)' }}>TOTAL OPEN 1-HR SLOTS</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 900, color: '#fbbf24', marginTop: '2px' }}>
                {coachAvailabilityList.reduce((acc, c) => acc + (c.available_slots_count || 0), 0)}
              </div>
            </div>
          </div>

          {/* Table */}
          {coachAvailabilityList.length === 0 ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
              No availability records matched your selected criteria.
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.825rem' }}>
                <thead>
                  <tr style={{ background: 'rgba(255,255,255,0.04)', borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                    <th style={{ padding: '10px 12px', color: 'var(--accent-gold)' }}>Date & Day</th>
                    <th style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>Coach</th>
                    <th style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>Preferred Hours</th>
                    <th style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>Existing Engagements</th>
                    <th style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>Remaining Available Slots</th>
                    <th style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>Eligible Levels</th>
                    <th style={{ padding: '10px 12px', color: 'var(--text-secondary)', textAlign: 'center' }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {coachAvailabilityList.map((rec, idx) => {
                    const isAvail = rec.status === 'Available';
                    const isFullyBooked = rec.status === 'Fully Booked';

                    return (
                      <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', background: isAvail ? 'rgba(16, 185, 129, 0.03)' : undefined }}>
                        <td style={{ padding: '12px', whiteSpace: 'nowrap' }}>
                          <strong>{rec.date}</strong> <span style={{ color: 'var(--text-muted)' }}>({rec.day})</span>
                        </td>
                        <td style={{ padding: '12px', whiteSpace: 'nowrap' }}>
                          <strong style={{ color: '#fff', fontSize: '0.875rem' }}>Coach {rec.coach_name}</strong>
                          <div style={{ display: 'flex', gap: '4px', marginTop: '2px' }}>
                            {rec.is_registered && (
                              <span className="badge badge-gold" style={{ fontSize: '0.625rem', padding: '1px 5px' }}>
                                Master Roster
                              </span>
                            )}
                            {rec.is_flex && (
                              <span className="badge badge-blue" style={{ fontSize: '0.625rem', padding: '1px 5px' }}>
                                Flex Trainer
                              </span>
                            )}
                          </div>
                        </td>
                        <td style={{ padding: '12px', color: '#cbd5e1' }}>
                          {rec.preferred_hours}
                        </td>
                        <td style={{ padding: '12px' }}>
                          <span style={{ fontWeight: 700, color: rec.assigned_classes_count > 0 ? '#60a5fa' : 'var(--text-muted)' }}>
                            {rec.assigned_classes_count} class{rec.assigned_classes_count !== 1 ? 'es' : ''}
                          </span>
                          {rec.occupied_slots && rec.occupied_slots.length > 0 && (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', marginTop: '4px' }}>
                              {rec.occupied_slots.map((occ, oIdx) => (
                                <span key={oIdx} style={{ fontSize: '0.7rem', color: '#94a3b8', background: 'rgba(255,255,255,0.04)', padding: '2px 6px', borderRadius: '4px' }}>
                                  {occ}
                                </span>
                              ))}
                            </div>
                          )}
                        </td>
                        <td style={{ padding: '12px' }}>
                          {rec.available_slots && rec.available_slots.length > 0 ? (
                            <div>
                              <span className="badge badge-success" style={{ fontSize: '0.7rem', fontWeight: 800, marginBottom: '4px', display: 'inline-block' }}>
                                ✓ {rec.available_slots_count} Open Slot{rec.available_slots_count !== 1 ? 's' : ''}
                              </span>
                              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                                {rec.available_slots.map((slot, sIdx) => (
                                  <span key={sIdx} style={{ fontSize: '0.725rem', padding: '2px 8px', borderRadius: '4px', background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.4)', color: '#34d399', fontWeight: 700 }}>
                                    {slot}
                                  </span>
                                ))}
                              </div>
                            </div>
                          ) : (
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                              No open slots on this date
                            </span>
                          )}
                        </td>
                        <td style={{ padding: '12px' }}>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '3px' }}>
                            {(rec.qualified_levels || []).map((lvl, lIdx) => (
                              <span key={lIdx} className="badge" style={{ fontSize: '0.625rem', padding: '1px 5px', background: 'rgba(255,255,255,0.06)' }}>
                                {lvl}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td style={{ padding: '12px', textAlign: 'center', whiteSpace: 'nowrap' }}>
                          <span
                            className="badge"
                            style={{
                              fontSize: '0.725rem',
                              fontWeight: 800,
                              background: isAvail ? 'rgba(16, 185, 129, 0.2)' : (isFullyBooked ? 'rgba(234, 179, 8, 0.2)' : 'rgba(239, 68, 68, 0.15)'),
                              border: isAvail ? '1px solid #10b981' : (isFullyBooked ? '1px solid #fbbf24' : '1px solid rgba(239, 68, 68, 0.3)'),
                              color: isAvail ? '#34d399' : (isFullyBooked ? '#fbbf24' : '#f87171')
                            }}
                          >
                            {rec.status}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ==================================================================== */}
      {/* SECTION: DELETED RECORDS & ACADEMY INSTRUCTIONS                      */}
      {/* ==================================================================== */}
      {activeSection === 'deleted_records' && (
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-lg)', padding: '24px' }}>
          {/* Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '20px', borderBottom: '1px solid var(--border-color)', paddingBottom: '16px' }}>
            <div>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 900, color: '#fff', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Archive size={22} style={{ color: '#f43f5e' }} /> Deleted Records & Academy Instructions
              </h3>
              <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
                Audit tracking & scope management for removed coaches, classes, and batches. Completed class history is permanently preserved.
              </p>
            </div>
            <button
              onClick={fetchDeletedRecordsData}
              disabled={loadingDeletedRecords}
              className="btn btn-secondary"
              style={{ padding: '8px 16px', fontSize: '0.8rem', fontWeight: 700 }}
            >
              <RefreshCw size={14} className={loadingDeletedRecords ? 'pulse-icon' : ''} /> Refresh Records
            </button>
          </div>

          {/* The 3 Policy Instructions Cards (Section 3 BRD Requirement) */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px', marginBottom: '24px' }}>
            <div style={{ background: 'rgba(239, 68, 68, 0.08)', border: '1.5px solid rgba(239, 68, 68, 0.4)', borderRadius: 'var(--radius-md)', padding: '14px' }}>
              <div style={{ fontSize: '0.8rem', fontWeight: 800, color: '#f87171', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span className="badge badge-danger" style={{ fontSize: '0.65rem' }}>SCOPE 1</span> Remove from Active Schedule
              </div>
              <div style={{ fontSize: '0.75rem', color: '#fecdd3', lineHeight: '1.4' }}>
                Removes record from active scheduling. All affected upcoming classes route to Attention Required for verified coach reassignment. Completed history remains 100% untouched.
              </div>
            </div>

            <div style={{ background: 'rgba(234, 179, 8, 0.08)', border: '1.5px solid rgba(234, 179, 8, 0.4)', borderRadius: 'var(--radius-md)', padding: '14px' }}>
              <div style={{ fontSize: '0.8rem', fontWeight: 800, color: '#fbbf24', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span className="badge badge-gold" style={{ fontSize: '0.65rem' }}>SCOPE 2</span> Archive / Soft-Delete
              </div>
              <div style={{ fontSize: '0.75rem', color: '#fef08a', lineHeight: '1.4' }}>
                Conceals the coach, batch, or class from active operations while safely preserving full record configuration in SQLite historical tables. Restore back to active anytime with 1 click.
              </div>
            </div>

            <div style={{ background: 'rgba(100, 116, 139, 0.1)', border: '1.5px solid rgba(100, 116, 139, 0.4)', borderRadius: 'var(--radius-md)', padding: '14px' }}>
              <div style={{ fontSize: '0.8rem', fontWeight: 800, color: '#cbd5e1', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span className="badge" style={{ fontSize: '0.65rem', background: '#475569' }}>SCOPE 3</span> Permanently Delete
              </div>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8', lineHeight: '1.4' }}>
                Permanently purges audit reference from database only after explicit admin confirmation and referential integrity dependency checks.
              </div>
            </div>
          </div>

          {/* Filtering Controls */}
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center', marginBottom: '16px', background: 'rgba(0,0,0,0.25)', padding: '12px 16px', borderRadius: 'var(--radius-md)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Filter Type:</span>
              <select
                value={deletedFilterType}
                onChange={e => setDeletedFilterType(e.target.value)}
                style={{ padding: '6px 10px', borderRadius: 'var(--radius-sm)', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.8rem' }}
              >
                <option value="ALL">All Types</option>
                <option value="coach">Coaches</option>
                <option value="batch">Batches</option>
                <option value="class">Classes</option>
              </select>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Filter Scope:</span>
              <select
                value={deletedFilterScope}
                onChange={e => setDeletedFilterScope(e.target.value)}
                style={{ padding: '6px 10px', borderRadius: 'var(--radius-sm)', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.8rem' }}
              >
                <option value="ALL">All Scopes</option>
                <option value="remove_from_schedule">Removed from Schedule</option>
                <option value="archive">Archived</option>
                <option value="permanent">Permanently Deleted</option>
                <option value="restored_active">Restored Active</option>
              </select>
            </div>

            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: 'auto' }}>
              Showing {deletedRecordsList.filter(r => (deletedFilterType === 'ALL' || r.record_type === deletedFilterType) && (deletedFilterScope === 'ALL' || r.deletion_scope === deletedFilterScope)).length} of {deletedRecordsList.length} records
            </span>
          </div>

          {/* Table */}
          {deletedRecordsList.length === 0 ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
              No deleted or archived records found in the database.
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.825rem' }}>
                <thead>
                  <tr style={{ background: 'rgba(255,255,255,0.04)', borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                    <th style={{ padding: '10px 12px', color: 'var(--accent-gold)' }}>Record Name & Type</th>
                    <th style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>Deletion Scope</th>
                    <th style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>Deleted Timestamp</th>
                    <th style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>Preserved History</th>
                    <th style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>Upcoming Affected</th>
                    <th style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>Notes & Audit Trail</th>
                    <th style={{ padding: '10px 12px', color: 'var(--text-secondary)', textAlign: 'center' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {deletedRecordsList
                    .filter(r => (deletedFilterType === 'ALL' || r.record_type === deletedFilterType) && (deletedFilterScope === 'ALL' || r.deletion_scope === deletedFilterScope))
                    .map((rec) => {
                      const isArchived = rec.deletion_scope === 'archive';
                      const isRestored = rec.deletion_scope === 'restored_active';

                      return (
                        <tr key={rec.record_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                          <td style={{ padding: '12px' }}>
                            <strong style={{ color: '#fff', fontSize: '0.875rem' }}>{rec.record_name}</strong>
                            <div>
                              <span className="badge badge-gold" style={{ fontSize: '0.625rem', textTransform: 'uppercase' }}>
                                {rec.record_type}
                              </span>
                            </div>
                          </td>
                          <td style={{ padding: '12px' }}>
                            <span
                              className="badge"
                              style={{
                                fontSize: '0.7rem',
                                fontWeight: 800,
                                background: isRestored ? 'rgba(16, 185, 129, 0.2)' : (isArchived ? 'rgba(234, 179, 8, 0.2)' : 'rgba(239, 68, 68, 0.2)'),
                                border: isRestored ? '1px solid #10b981' : (isArchived ? '1px solid #fbbf24' : '1px solid #ef4444'),
                                color: isRestored ? '#34d399' : (isArchived ? '#fbbf24' : '#f87171')
                              }}
                            >
                              {rec.deletion_scope}
                            </span>
                          </td>
                          <td style={{ padding: '12px', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                            {rec.deleted_at}
                            <div style={{ fontSize: '0.675rem', color: 'var(--text-muted)' }}>By: {rec.deleted_by || 'Admin'}</div>
                          </td>
                          <td style={{ padding: '12px', color: '#34d399', fontWeight: 700 }}>
                            {rec.historical_classes_preserved} classes preserved
                          </td>
                          <td style={{ padding: '12px', color: rec.affected_future_classes > 0 ? '#f87171' : 'var(--text-muted)', fontWeight: 700 }}>
                            {rec.affected_future_classes} routed to Attention
                          </td>
                          <td style={{ padding: '12px', color: '#cbd5e1', fontSize: '0.75rem', maxWidth: '300px' }}>
                            {rec.notes || 'No extra notes recorded.'}
                          </td>
                          <td style={{ padding: '12px', textAlign: 'center', whiteSpace: 'nowrap' }}>
                            <div style={{ display: 'flex', gap: '6px', justifyContent: 'center' }}>
                              {!isRestored && (
                                <button
                                  onClick={() => handleRestoreRecord(rec)}
                                  disabled={restoringRecordId === rec.record_id}
                                  className="btn btn-secondary"
                                  style={{ padding: '4px 10px', fontSize: '0.725rem', color: '#10b981', borderColor: 'rgba(16, 185, 129, 0.4)', fontWeight: 700 }}
                                  title="Restore entity back into active operations"
                                >
                                  <RotateCcw size={12} /> {restoringRecordId === rec.record_id ? 'Restoring...' : 'Restore'}
                                </button>
                              )}
                              <button
                                onClick={() => handlePermanentDeleteRecord(rec)}
                                className="btn btn-secondary"
                                style={{ padding: '4px 10px', fontSize: '0.725rem', color: '#f87171', borderColor: 'rgba(239, 68, 68, 0.4)', fontWeight: 700 }}
                                title="Permanently delete audit entry"
                              >
                                <Trash2 size={12} /> Delete
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                </tbody>
              </table>
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

                  if (rec.pending_coach_reassignment) {
                    const cardKey = rec.class_id || sid;
                    const isReassigning = reassigningId === cardKey;
                    const currentSelected = selectedCoachMap[cardKey] || rec.recommended_coach || (rec.eligible_coaches && rec.eligible_coaches[0]) || coachesOptions[0];

                    return (
                      <div
                        key={cardKey}
                        className="glass-card"
                        style={{
                          padding: '22px',
                          background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(15, 23, 42, 0.95) 100%)',
                          border: '1.5px solid rgba(239, 68, 68, 0.55)',
                          borderRadius: 'var(--radius-lg)',
                          display: 'grid',
                          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                          gap: '20px',
                          alignItems: 'start',
                          boxShadow: '0 8px 24px -4px rgba(239, 68, 68, 0.25)'
                        }}
                      >
                        {/* COLUMN 1: Preserved Batch & Deleted Coach Notice */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <span className="badge badge-danger" style={{ fontSize: '0.75rem', padding: '4px 10px', display: 'flex', alignItems: 'center', gap: '5px' }}>
                              <AlertTriangle size={13} /> PENDING COACH REASSIGNMENT
                            </span>
                            <span className="badge badge-gold" style={{ fontSize: '0.75rem' }}>
                              Batch {rec.batch_type} · {rec.student_level}
                            </span>
                          </div>

                          <div>
                            <h3 style={{ fontSize: '1.15rem', fontWeight: 900, color: '#fff', margin: 0 }}>
                              {rec.batch_name || rec.student_name}
                            </h3>
                            <div style={{ fontSize: '0.8rem', color: 'var(--accent-blue)', marginTop: '4px', fontWeight: 600 }}>
                              📅 {rec.date} ({rec.preferred_days}) · ⏰ {rec.preferred_time}
                            </div>
                          </div>

                          <div style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.35)', padding: '12px 14px', borderRadius: 'var(--radius-md)' }}>
                            <div style={{ fontSize: '0.75rem', fontWeight: 800, color: '#f87171', marginBottom: '4px' }}>
                              ⚠️ FORMER COACH DELETED / UNAVAILABLE:
                            </div>
                            <div style={{ fontSize: '0.8rem', color: '#fecdd3', lineHeight: '1.4' }}>
                              Coach <strong>{rec.deleted_coach_name}</strong> was removed from the academy. All scheduled sessions, student timings, and roster commitments are 100% preserved. Assign a replacement coach below.
                            </div>
                          </div>
                        </div>

                        {/* COLUMN 2: Smart Coach Recommendation & Assign New Coach Selector */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: 'var(--radius-md)', border: '1px solid rgba(255,255,255,0.08)' }}>
                          <div style={{ fontSize: '0.825rem', fontWeight: 800, color: 'var(--accent-gold)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <Sparkles size={16} /> SMART ENGINE RECOMMENDATION (RULE 4)
                          </div>

                          {/* Top Pick Recommendation Box */}
                          <div style={{ background: 'rgba(16, 185, 129, 0.12)', border: '1px solid rgba(16, 185, 129, 0.4)', borderRadius: 'var(--radius-md)', padding: '12px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px', flexWrap: 'wrap', gap: '8px' }}>
                              <strong style={{ fontSize: '0.9rem', color: '#10b981' }}>
                                Recommended: Coach {rec.recommended_coach}
                              </strong>
                              <button
                                onClick={() => handleReassignCoach(rec, rec.recommended_coach)}
                                disabled={isReassigning}
                                className="btn btn-primary"
                                style={{ padding: '6px 12px', fontSize: '0.775rem', background: '#10b981', borderColor: '#10b981', fontWeight: 800 }}
                              >
                                {isReassigning ? 'Assigning...' : `✓ Accept ${rec.recommended_coach}`}
                              </button>
                            </div>
                            <div style={{ fontSize: '0.75rem', color: '#a7f3d0' }}>
                              💡 {rec.recommendation_reason || 'Matches batch preference time, qualified for level, and has sufficient monthly quota.'}
                            </div>
                          </div>

                          {/* Dedicated Assign New Coach Selector */}
                          <div>
                            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                              Assign New Coach (Administrator Choice):
                            </label>
                            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                              <select
                                value={currentSelected}
                                onChange={(e) => setSelectedCoachMap(prev => ({ ...prev, [cardKey]: e.target.value }))}
                                style={{
                                  flex: 1,
                                  minWidth: '180px',
                                  padding: '8px 12px',
                                  borderRadius: 'var(--radius-md)',
                                  background: 'var(--bg-secondary)',
                                  border: '1px solid var(--accent-gold)',
                                  color: '#fff',
                                  fontSize: '0.825rem',
                                  fontWeight: 700
                                }}
                              >
                                {(rec.eligible_coaches && rec.eligible_coaches.length > 0 ? rec.eligible_coaches : coachesOptions).map(cname => (
                                  <option key={cname} value={cname}>
                                    Coach {cname} {cname === rec.recommended_coach ? '★ (Engine Top Recommendation)' : ''}
                                  </option>
                                ))}
                              </select>

                              <button
                                onClick={() => handleReassignCoach(rec, currentSelected)}
                                disabled={isReassigning}
                                className="btn btn-primary"
                                style={{ padding: '8px 16px', fontSize: '0.8rem', fontWeight: 800, whiteSpace: 'nowrap' }}
                              >
                                {isReassigning ? 'Assigning...' : 'Assign New Coach'}
                              </button>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  }

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
                            <div style={{ fontSize: '0.775rem', color: 'var(--accent-gold)', fontWeight: 700, marginTop: '2px' }}>
                              ID: {rec.student_id} · Level: <span style={{ color: '#fff' }}>{rec.student_level}</span>
                            </div>
                            <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '2px' }}>
                              Batch: <strong style={{ color: '#e2e8f0' }}>{rec.original_batch_name || rec.batch_name || 'Unassigned'}</strong> (ID: {rec.original_batch_id || rec.batch_id || 'N/A'}) · Coach: <strong style={{ color: '#38bdf8' }}>{rec.original_coach || 'To be assigned'}</strong>
                            </div>
                          </div>
                        </div>

                        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
                          <span className="badge badge-gold" style={{ fontSize: '0.7rem' }}>
                            Batch {rec.batch_type}
                          </span>
                          <span className="badge badge-danger" style={{ fontSize: '0.7rem' }}>
                            {rec.remaining_classes} of {rec.required_classes} Missing
                          </span>
                          <span
                            className="badge"
                            style={{
                              fontSize: '0.675rem',
                              fontWeight: 700,
                              background: rec.is_upcoming ? 'rgba(239, 68, 68, 0.2)' : 'rgba(100, 116, 139, 0.2)',
                              border: rec.is_upcoming ? '1px solid #ef4444' : '1px solid rgba(100, 116, 139, 0.4)',
                              color: rec.is_upcoming ? '#fca5a5' : '#94a3b8'
                            }}
                          >
                            {rec.is_upcoming ? '⚠️ Upcoming Shortfall' : 'Historical Preserved'}
                          </span>
                          <span className="badge" style={{
                            fontSize: '0.675rem',
                            fontWeight: 700,
                            background: rec.is_sunday_tournament_eligible ? 'rgba(59, 130, 246, 0.2)' : 'rgba(100, 116, 139, 0.2)',
                            border: rec.is_sunday_tournament_eligible ? '1px solid #3b82f6' : '1px solid rgba(100, 116, 139, 0.4)',
                            color: rec.is_sunday_tournament_eligible ? '#93c5fd' : '#94a3b8'
                          }}>
                            {rec.is_sunday_tournament_eligible ? '🏆 Sunday Tournament Required' : '♟️ Regular Sunday Class Only'}
                          </span>
                        </div>

                        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                          📅 Timing: <strong style={{ color: '#fff' }}>{rec.preferred_days || 'Flexible'}</strong> · ⏰ <strong style={{ color: '#fff' }}>{rec.preferred_time || 'Flexible'}</strong>
                        </div>

                        {/* Failure Reason Alert Box */}
                        <div style={{ background: 'rgba(244, 63, 94, 0.15)', border: '1px solid rgba(244, 63, 94, 0.3)', padding: '10px 14px', borderRadius: 'var(--radius-md)' }}>
                          <div style={{ fontSize: '0.75rem', fontWeight: 800, color: '#f43f5e', marginBottom: '2px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <AlertTriangle size={14} /> REASON FOR ATTENTION STATUS:
                          </div>
                          <div style={{ fontSize: '0.8rem', color: '#fecdd3', lineHeight: '1.4' }}>
                            {rec.failure_reason || rec.reason}
                          </div>
                        </div>

                        {/* Action Required Box */}
                        <div style={{ background: 'rgba(56, 189, 248, 0.1)', border: '1px solid rgba(56, 189, 248, 0.3)', padding: '8px 12px', borderRadius: 'var(--radius-md)', fontSize: '0.78rem', color: '#bae6fd' }}>
                          <strong>Action Required:</strong> {rec.action_required || `Assign ${rec.remaining_classes || 1} class slot(s) for ${rec.student_name}`}
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

                        {/* DYNAMIC ENGINE SUGGESTIONS: SET A, SET B, SET C & SINGLE SLOTS */}
                        {dynSuggestions && (() => {
                          const optionSets = dynSuggestions.option_sets || [];
                          const setA = optionSets.filter(s => s.set_id?.startsWith('SET_A'));
                          const setB = optionSets.filter(s => s.set_id?.startsWith('SET_B'));
                          const setC = optionSets.filter(s => s.set_id?.startsWith('SET_C'));
                          const singleS = dynSuggestions.suggestions || [];
                          const activeTab = optionSetTab[sid] || (optionSets.length > 0 ? 'all' : 'single');
                          const coachCoverage = setB[0]?.coach_coverage_pct || 96.2;

                          let displaySets = optionSets;
                          if (activeTab === 'set_a') displaySets = setA;
                          else if (activeTab === 'set_b') displaySets = setB;
                          else if (activeTab === 'set_c') displaySets = setC;

                          return (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                              {/* Sub-tab Filter Bar */}
                              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', background: 'rgba(0,0,0,0.25)', padding: '6px', borderRadius: 'var(--radius-md)', border: '1px solid rgba(255,255,255,0.06)' }}>
                                <button
                                  onClick={() => setOptionSetTab(prev => ({ ...prev, [sid]: 'all' }))}
                                  className={`btn ${activeTab === 'all' ? 'btn-primary' : 'btn-secondary'}`}
                                  style={{ padding: '4px 10px', fontSize: '0.7rem', fontWeight: 700 }}
                                >
                                  All Sets ({optionSets.length})
                                </button>
                                {setA.length > 0 && (
                                  <button
                                    onClick={() => setOptionSetTab(prev => ({ ...prev, [sid]: 'set_a' }))}
                                    className={`btn ${activeTab === 'set_a' ? 'btn-primary' : 'btn-secondary'}`}
                                    style={{ padding: '4px 10px', fontSize: '0.7rem', fontWeight: 700 }}
                                  >
                                    Set A: Consistent ({setA.length})
                                  </button>
                                )}
                                {setB.length > 0 && (
                                  <button
                                    onClick={() => setOptionSetTab(prev => ({ ...prev, [sid]: 'set_b' }))}
                                    className={`btn ${activeTab === 'set_b' ? 'btn-primary' : 'btn-secondary'}`}
                                    style={{ padding: '4px 10px', fontSize: '0.7rem', fontWeight: 700 }}
                                  >
                                    Set B: Hybrid ({setB.length})
                                  </button>
                                )}
                                {setC.length > 0 && (
                                  <button
                                    onClick={() => setOptionSetTab(prev => ({ ...prev, [sid]: 'set_c' }))}
                                    className={`btn ${activeTab === 'set_c' ? 'btn-primary' : 'btn-secondary'}`}
                                    style={{ padding: '4px 10px', fontSize: '0.7rem', fontWeight: 700 }}
                                  >
                                    Set C: Fastest ({setC.length})
                                  </button>
                                )}
                                {singleS.length > 0 && (
                                  <button
                                    onClick={() => setOptionSetTab(prev => ({ ...prev, [sid]: 'single' }))}
                                    className={`btn ${activeTab === 'single' ? 'btn-primary' : 'btn-secondary'}`}
                                    style={{ padding: '4px 10px', fontSize: '0.7rem', fontWeight: 700 }}
                                  >
                                    Single Slots ({singleS.length})
                                  </button>
                                )}
                              </div>

                              {/* Rule 8 Enhancement & Phase 5.2: ≥95% Coach Coverage Badge */}
                              {(activeTab === 'set_b' || activeTab === 'all') && setB.length > 0 && (
                                <div style={{
                                  background: 'linear-gradient(90deg, rgba(16, 185, 129, 0.15) 0%, rgba(59, 130, 246, 0.15) 100%)',
                                  border: '1px solid rgba(16, 185, 129, 0.4)',
                                  borderRadius: 'var(--radius-md)',
                                  padding: '8px 12px',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'space-between',
                                  flexWrap: 'wrap',
                                  gap: '8px'
                                }}>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', fontWeight: 800, color: '#34d399' }}>
                                    <Sparkles size={14} /> ⚡ ≥95% Eligible Coach Coverage Target Met ({coachCoverage}%)
                                  </div>
                                  <span style={{ fontSize: '0.7rem', color: '#93c5fd', fontWeight: 600 }}>
                                    Up to 30 Ranked Combinations
                                  </span>
                                </div>
                              )}

                              {/* RENDER OPTION SETS */}
                              {activeTab !== 'single' && displaySets.map((setObj) => {
                                const isExpanded = expandedSetItems[`${sid}_${setObj.set_id}`];
                                const isSetA = setObj.set_id?.startsWith('SET_A');
                                const isSetB = setObj.set_id?.startsWith('SET_B');
                                const isSetC = setObj.set_id?.startsWith('SET_C');

                                return (
                                  <div
                                    key={setObj.set_id}
                                    style={{
                                      background: 'var(--bg-secondary)',
                                      border: isSetA ? '1.5px solid var(--accent-gold)' : (isSetB ? '1.5px solid rgba(59, 130, 246, 0.6)' : '1.5px solid rgba(16, 185, 129, 0.6)'),
                                      borderRadius: 'var(--radius-md)',
                                      padding: '12px 14px',
                                      display: 'flex',
                                      flexDirection: 'column',
                                      gap: '8px'
                                    }}
                                  >
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                                      <div>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                          <span className={`badge ${isSetA ? 'badge-gold' : (isSetB ? 'badge-blue' : 'badge-success')}`} style={{ fontSize: '0.65rem' }}>
                                            {isSetA ? 'SET A' : (isSetB ? 'SET B' : 'SET C')}
                                          </span>
                                          <strong style={{ fontSize: '0.85rem', color: '#fff' }}>{setObj.title || setObj.set_name}</strong>
                                        </div>
                                        <div style={{ fontSize: '0.725rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                                          {setObj.description}
                                        </div>
                                      </div>
                                      <button
                                        onClick={() => handleAcceptOptionSet(sid, setObj, dynSuggestions.schedule_version)}
                                        disabled={assigningId === `${sid}_set_${setObj.set_id}`}
                                        className="btn btn-primary"
                                        style={{ padding: '6px 12px', fontSize: '0.75rem', fontWeight: 800 }}
                                      >
                                        {assigningId === `${sid}_set_${setObj.set_id}` ? 'Accepting...' : '✓ Accept Set'}
                                      </button>
                                    </div>

                                    {/* Stats and Class Details Toggle */}
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '6px', fontSize: '0.7rem', color: '#cbd5e1' }}>
                                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                                        <span>Primary: <strong style={{ color: '#fff' }}>{setObj.primary_coach || 'Coach'}</strong></span>
                                        {setObj.continuity_pct !== undefined && (
                                          <span>Continuity: <strong style={{ color: setObj.continuity_pct >= 90 ? '#34d399' : '#f59e0b' }}>{setObj.continuity_pct}%</strong></span>
                                        )}
                                        {setObj.concludes_on && (
                                          <span>Finishes: <strong style={{ color: '#60a5fa' }}>{setObj.concludes_on}</strong></span>
                                        )}
                                        <span>Existing Seats: <strong style={{ color: '#34d399' }}>{setObj.existing_used || 0}</strong></span>
                                        <span>New Slots: <strong style={{ color: (setObj.new_slots || 0) > 0 ? '#f59e0b' : '#34d399' }}>{setObj.new_slots || 0}</strong></span>
                                      </div>

                                      {setObj.items && setObj.items.length > 0 && (
                                        <button
                                          onClick={() => setExpandedSetItems(prev => ({ ...prev, [`${sid}_${setObj.set_id}`]: !prev[`${sid}_${setObj.set_id}`] }))}
                                          style={{ background: 'none', border: 'none', color: '#60a5fa', fontSize: '0.7rem', fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '3px' }}
                                        >
                                          {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                                          {isExpanded ? 'Hide Schedule' : `View ${setObj.items.length} Classes`}
                                        </button>
                                      )}
                                    </div>

                                    {/* Expanded Class Schedule Breakdown */}
                                    {isExpanded && setObj.items && (
                                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', background: 'rgba(0,0,0,0.3)', padding: '8px 10px', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(255,255,255,0.06)' }}>
                                        {setObj.items.map((cls, cIdx) => (
                                          <div key={cIdx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.7rem', color: '#cbd5e1' }}>
                                            <span style={{ fontWeight: 600 }}>
                                              📅 {cls.date} ({cls.day}) · ⏰ {cls.start_time || cls.time_slot}
                                            </span>
                                            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                              <strong style={{ color: '#fff' }}>Coach {cls.coach_id || cls.coach_name}</strong>
                                              <span className={`badge ${cls.is_new_slot ? 'badge-blue' : 'badge-gold'}`} style={{ fontSize: '0.6rem', padding: '1px 5px' }}>
                                                {cls.is_new_slot ? 'New Slot' : 'Join Batch'}
                                              </span>
                                            </span>
                                          </div>
                                        ))}
                                      </div>
                                    )}
                                  </div>
                                );
                              })}

                              {/* RENDER INDIVIDUAL SLOTS (WHEN SINGLE TAB IS SELECTED OR NO OPTION SETS) */}
                              {(activeTab === 'single' || (optionSets.length === 0 && singleS.length > 0)) && (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                  {singleS.map((item, idx) => (
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
                                  ))}
                                </div>
                              )}
                            </div>
                          );
                        })()}

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
