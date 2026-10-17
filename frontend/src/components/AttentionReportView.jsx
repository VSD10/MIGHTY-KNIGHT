import React, { useState, useEffect } from 'react';
import {
  ShieldAlert, AlertTriangle, CheckCircle2, UserX, Info, Move, Sparkles, Check,
  Zap, Plus, X, Calendar, Clock, Award, Search, ChevronDown, ChevronUp, Layers,
  Lightbulb, RefreshCw, Undo2, ArrowRight, BookmarkCheck, FileText, UserCheck
} from 'lucide-react';
import {
  assignStudentToClass, createClassForStudent,
  getEngineSuggestions, acceptEngineSuggestion,
  getSmartBatches, getConsolidationAdvisor,
  getExceptionsList, revertException, applyException,
  resolveDeletedPastClass, getCoachAvailabilityExplorer,
  reassignBatchCoach
} from '../services/api';

const DEFAULT_COACHES = ["ABINAYA", "SARAVANAN", "PRAKASH", "BATHRI", "DHAANUSH", "HEMA", "MANIKANDAN", "ARSHATH", "GURU", "VIGNESH"];

export default function AttentionReportView({ attentionData, scheduleId, onRefreshSchedule, coachList, activeMonth = '2026-10' }) {
  const [assigningId, setAssigningId] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeSection, setActiveSection] = useState('unresolved'); // 'unresolved' | 'accepted_exceptions' | 'advisory'

  // Smart Batch Opportunities, Trainer Proposals, Deleted Past Classes, Coach Explorer & Consolidation Advisor
  const [smartBatches, setSmartBatches] = useState([]);
  const [trainerProposals, setTrainerProposals] = useState([]);
  const [deletedPastClasses, setDeletedPastClasses] = useState([]);
  const [coachExplorerDays, setCoachExplorerDays] = useState([]);
  const [selectedExplorerDate, setSelectedExplorerDate] = useState(`${activeMonth}-15`);
  const [resolvingExcId, setResolvingExcId] = useState(null);
  const [engineVersion, setEngineVersion] = useState(1);
  const [consolidationList, setConsolidationList] = useState([]);
  const [acceptedExceptions, setAcceptedExceptions] = useState([]);
  const [loadingExtras, setLoadingExtras] = useState(false);

  // Dynamic Engine suggestions per student: { [student_id]: suggestionsData }
  const [engineSuggestionsMap, setEngineSuggestionsMap] = useState({});
  const [loadingSuggestions, setLoadingSuggestions] = useState({});
  const [expandedNewSlot, setExpandedNewSlot] = useState({});

  // Rule 4: Deleted coach batch reassignment state
  const [reassignCoachMap, setReassignCoachMap] = useState({});
  const [reassigningId, setReassigningId] = useState(null);

  // Custom Create New Class state per student
  const [activeNewClassStudentId, setActiveNewClassStudentId] = useState(null);
  const [newCoachName, setNewCoachName] = useState('BATHRI');
  const [newDate, setNewDate] = useState('2026-10-05');
  const [newTimeSlot, setNewTimeSlot] = useState('05:00 PM - 06:00 PM');
  const [newBatchType, setNewBatchType] = useState('G');
  const [creating, setCreating] = useState(false);

  const handleReassignBatchCoach = async (classId, batchName, coachName, applyToEntireBatch) => {
    if (!coachName) {
      alert("Please select a replacement coach.");
      return;
    }
    setReassigningId(`${classId}_${applyToEntireBatch ? 'all' : 'single'}`);
    try {
      await reassignBatchCoach({
        class_id: classId,
        batch_name: batchName,
        new_coach_name: coachName,
        apply_to_entire_batch: applyToEntireBatch,
        month: activeMonth
      });
      if (onRefreshSchedule) await onRefreshSchedule();
      await fetchExtras();
    } catch (err) {
      alert("Failed to reassign coach: " + (err?.response?.data?.detail || err?.message));
    } finally {
      setReassigningId(null);
    }
  };

  const coachesOptions = (coachList && coachList.length > 0)
    ? coachList.map(c => typeof c === 'string' ? c.toUpperCase() : (c.coach_name || '').toUpperCase())
    : DEFAULT_COACHES;

  useEffect(() => {
    if (attentionData) {
      if (attentionData.smart_batch_opportunities) setSmartBatches(attentionData.smart_batch_opportunities);
      if (attentionData.trainer_proposals) setTrainerProposals(attentionData.trainer_proposals);
      if (attentionData.consolidation_advisory) setConsolidationList(attentionData.consolidation_advisory);
      if (attentionData.accepted_exceptions) setAcceptedExceptions(attentionData.accepted_exceptions);
      if (attentionData.deleted_past_classes) setDeletedPastClasses(attentionData.deleted_past_classes);
      if (attentionData.coach_availability_explorer?.days) setCoachExplorerDays(attentionData.coach_availability_explorer.days);
      if (attentionData.schedule_version) setEngineVersion(attentionData.schedule_version);
    }
    fetchExtras();
  }, [scheduleId, attentionData, activeMonth]);

  useEffect(() => {
    if (!selectedExplorerDate.startsWith(activeMonth)) {
      setSelectedExplorerDate(`${activeMonth}-01`);
    }
  }, [activeMonth]);

  // Pre-load ranked engine suggestions for first few unresolved regular students (staggered to prevent latency)
  useEffect(() => {
    const records = (attentionData?.attention_records || []).filter(
      rec => !rec.needs_coach_reassignment && rec.record_type !== 'coach_reassignment' && rec.student_id && rec.student_id !== 'N/A'
    );
    records.slice(0, 2).forEach((rec, idx) => {
      const sid = rec.student_id;
      if (!engineSuggestionsMap[sid] && !loadingSuggestions[sid]) {
        const neededCount = rec.remaining_classes || (rec.required_classes - rec.scheduled_classes) || 1;
        setTimeout(() => loadStudentSuggestions(sid, neededCount), idx * 300);
      }
    });
  }, [attentionData, activeMonth]);

  const fetchExtras = async () => {
    setLoadingExtras(true);
    try {
      const [sbRes, caRes, excRes, expRes] = await Promise.all([
        getSmartBatches(activeMonth).catch(() => ({ opportunities: [], trainer_proposals: [] })),
        getConsolidationAdvisor(activeMonth).catch(() => ({ advisories: [] })),
        getExceptionsList(activeMonth, 'active').catch(() => ({ exceptions: [] })),
        getCoachAvailabilityExplorer(activeMonth).catch(() => ({ days: [] }))
      ]);
      setSmartBatches(sbRes.opportunities || []);
      setTrainerProposals(sbRes.trainer_proposals || []);
      if (sbRes.schedule_version) setEngineVersion(sbRes.schedule_version);
      setConsolidationList(caRes.advisories || []);
      setAcceptedExceptions(excRes.exceptions || []);
      if (expRes.days) setCoachExplorerDays(expRes.days);
    } catch (err) {
      console.warn('Failed to load extra intelligence:', err);
    } finally {
      setLoadingExtras(false);
    }
  };

  const handleResolveDeletedClass = async (exceptionId, choice) => {
    setResolvingExcId(`${exceptionId}_${choice}`);
    try {
      await resolveDeletedPastClass({
        exception_id: exceptionId,
        month: activeMonth,
        resolution_choice: choice
      });
      setEngineSuggestionsMap({});
      if (onRefreshSchedule) await onRefreshSchedule();
      await fetchExtras();
    } catch (err) {
      alert('Failed to resolve deleted class: ' + (err.response?.data?.detail || err.message));
    } finally {
      setResolvingExcId(null);
    }
  };

  const loadStudentSuggestions = async (studentId, neededCount = 1) => {
    if (!studentId || studentId === 'N/A' || loadingSuggestions[studentId]) return;
    setLoadingSuggestions(prev => ({ ...prev, [studentId]: true }));
    try {
      const res = await getEngineSuggestions(studentId, neededCount, activeMonth);
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
    setAssigningId(`${studentId}_${item.class_id || item.date}_${item.start_time}`);
    try {
      await acceptEngineSuggestion({
        student_id: studentId,
        month: activeMonth,
        schedule_version: scheduleVersion || engineVersion || 1,
        suggestion_item: item,
        is_option_set: false
      });
      setEngineSuggestionsMap(prev => {
        const copy = { ...prev };
        delete copy[studentId];
        return copy;
      });
      if (onRefreshSchedule) await onRefreshSchedule();
      await fetchExtras();
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
        month: activeMonth,
        schedule_version: scheduleVersion || engineVersion || 1,
        is_option_set: true,
        option_set_items: optionSet.items
      });
      setEngineSuggestionsMap(prev => {
        const copy = { ...prev };
        delete copy[studentId];
        return copy;
      });
      if (onRefreshSchedule) await onRefreshSchedule();
      await fetchExtras();
    } catch (err) {
      alert('Failed to accept option set: ' + (err.response?.data?.detail || err.message));
    } finally {
      setAssigningId(null);
    }
  };

  // Accept a New Trainer Engagement Proposal (single slot or all slots)
  const handleAcceptTrainerProposal = async (coachName, slotsToApply) => {
    setAssigningId(`trainer_${coachName}`);
    try {
      await acceptEngineSuggestion({
        student_id: 'TRAINER_PROPOSAL',
        month: activeMonth,
        schedule_version: engineVersion || 1,
        is_option_set: true,
        option_set_items: slotsToApply,
        user: 'Admin'
      });
      setEngineSuggestionsMap({});
      if (onRefreshSchedule) await onRefreshSchedule();
      await fetchExtras();
    } catch (err) {
      alert('Failed to accept trainer schedule proposal: ' + (err.response?.data?.detail || err.message));
    } finally {
      setAssigningId(null);
    }
  };

  // Accept a Smart Batch Pooled Opportunity
  const handleAcceptSmartBatch = async (opp) => {
    setAssigningId(`pool_${opp.opportunity_id}`);
    try {
      // Find first occurrence of opp.day in 2026-10
      const dayMap = { Thursday: '2026-10-01', Friday: '2026-10-02', Saturday: '2026-10-03', Sunday: '2026-10-04', Monday: '2026-10-05', Tuesday: '2026-10-06', Wednesday: '2026-10-07' };
      const targetDate = dayMap[opp.day] || '2026-10-05';
      await applyException({
        month: activeMonth,
        date: targetDate,
        time_slot: opp.time_slot,
        coach_name: opp.suggested_coach,
        action_type: 'add',
        affected_student_ids: opp.student_ids || [],
        after: {
          student_level: opp.level,
          batch_type: opp.batch_type || 'G',
          student_ids: opp.student_ids || [],
          day: opp.day
        },
        subtype: 'normal_assignment',
        reason: `Accepted Smart Batch Opportunity (${opp.title})`,
        created_by: 'Admin'
      });
      setEngineSuggestionsMap({});
      if (onRefreshSchedule) await onRefreshSchedule();
      await fetchExtras();
    } catch (err) {
      alert('Failed to accept pooled batch: ' + (err.response?.data?.detail || err.message));
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
      await fetchExtras();
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
      setEngineSuggestionsMap(prev => {
        const copy = { ...prev };
        delete copy[student.student_id];
        return copy;
      });
      if (onRefreshSchedule) await onRefreshSchedule();
      await fetchExtras();
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
      await revertException(exceptionId, activeMonth);
      setEngineSuggestionsMap({});
      if (onRefreshSchedule) await onRefreshSchedule();
      await fetchExtras();
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
              The central administrator-intervention hub. Option Ladder (T1–T7), Smart Batch Pooling, Multi-Class Option Sets, and New Trainer Proposals.
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
          onClick={() => setActiveSection('past_deletions')}
          className={`btn ${activeSection === 'past_deletions' ? 'btn-primary' : 'btn-secondary'}`}
          style={{
            padding: '8px 16px',
            fontSize: '0.825rem',
            fontWeight: 800,
            borderColor: deletedPastClasses.length > 0 ? '#f43f5e' : undefined
          }}
        >
          <AlertTriangle size={15} /> Past / Deleted Class Review ({deletedPastClasses.length})
        </button>

        <button
          onClick={() => setActiveSection('coach_explorer')}
          className={`btn ${activeSection === 'coach_explorer' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ padding: '8px 16px', fontSize: '0.825rem', fontWeight: 800 }}
        >
          <Calendar size={15} /> Coach Daily Availability & Free Slots Explorer
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
      {/* NEW SECTION A: PAST / DELETED CLASS REVIEW (3-OPTION ADMIN PROMPT)   */}
      {/* ==================================================================== */}
      {activeSection === 'past_deletions' && (
        <div style={{ background: 'var(--bg-card)', border: '1px solid rgba(244, 63, 94, 0.45)', borderRadius: 'var(--radius-lg)', padding: '20px', marginBottom: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '10px' }}>
            <div>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 900, color: '#fff', margin: 0 }}>
                🗑️ Past Data & Deleted Classes Resolution Center
              </h3>
              <p style={{ fontSize: '0.8rem', color: '#fda4af', margin: '4px 0 0 0' }}>
                Whenever a past or scheduled class is deleted, choose how the engine should account for the students, attendance history, and trainer class totals:
              </p>
            </div>
            <button onClick={fetchExtras} className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.75rem' }}>
              <RefreshCw size={14} /> Refresh
            </button>
          </div>

          {deletedPastClasses.length === 0 ? (
            <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)', background: 'rgba(0,0,0,0.2)', borderRadius: '8px' }}>
              No deleted classes in {activeMonth}. If you delete any class from Daily Planner or Coach Workload, it will appear here immediately for resolution.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {deletedPastClasses.map((dpc) => (
                <div
                  key={dpc.exception_id}
                  style={{
                    background: 'rgba(15, 23, 42, 0.9)',
                    border: dpc.resolution_choice === 'pending' ? '1.5px solid #f43f5e' : '1px solid rgba(52, 211, 153, 0.4)',
                    borderRadius: '12px',
                    padding: '16px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '10px' }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                        <span className="badge badge-danger" style={{ fontSize: '0.7rem' }}>
                          {dpc.is_past_date ? 'PAST CLASS DELETED' : 'SCHEDULED CLASS DELETED'}
                        </span>
                        <strong style={{ fontSize: '0.95rem', color: '#fff' }}>
                          {dpc.date} ({dpc.day}) · {dpc.time_slot} · Coach {dpc.coach_name}
                        </strong>
                        <span className="badge badge-gold" style={{ fontSize: '0.7rem' }}>
                          Batch {dpc.batch_name} ({dpc.student_level})
                        </span>
                      </div>
                      <div style={{ fontSize: '0.8rem', color: '#cbd5e1', marginTop: '6px' }}>
                        Affected Students ({dpc.affected_student_ids?.length || 0}):{' '}
                        <strong style={{ color: '#fbbf24' }}>
                          {(dpc.affected_student_names || []).map((n, i) => `${n} (${dpc.affected_student_ids?.[i]})`).join(' · ') || 'None'}
                        </strong>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span
                        className="badge"
                        style={{
                          background: dpc.resolution_choice === 'pending' ? 'rgba(244, 63, 94, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                          color: dpc.resolution_choice === 'pending' ? '#fda4af' : '#6ee7b7',
                          border: '1px solid currentColor',
                          fontSize: '0.7rem'
                        }}
                      >
                        Status: {dpc.resolution_choice === 'pending' ? 'Awaiting Admin Choice' : dpc.resolution_choice}
                      </span>
                      <button
                        onClick={() => handleRevertExceptionRecord(dpc.exception_id)}
                        className="btn btn-secondary"
                        style={{ padding: '4px 10px', fontSize: '0.72rem', color: '#38bdf8' }}
                        title="Restore this deleted class back into the schedule"
                      >
                        <Undo2 size={13} /> Restore Class
                      </button>
                    </div>
                  </div>

                  {/* Admin 3-Question Resolution Prompt */}
                  <div style={{ background: 'rgba(0,0,0,0.35)', padding: '12px 14px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.08)' }}>
                    <div style={{ fontSize: '0.78rem', fontWeight: 800, color: '#fde68a', marginBottom: '8px' }}>
                      Hey Admin — You removed this class. How should the Academy Engine handle it?
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '10px' }}>
                      <button
                        onClick={() => handleResolveDeletedClass(dpc.exception_id, 'compensate_future')}
                        disabled={resolvingExcId === `${dpc.exception_id}_compensate_future`}
                        className="btn btn-secondary"
                        style={{
                          padding: '10px 12px',
                          fontSize: '0.75rem',
                          fontWeight: 800,
                          textAlign: 'left',
                          borderColor: dpc.resolution_choice === 'compensate_future' ? '#fbbf24' : 'rgba(251, 191, 36, 0.4)',
                          background: dpc.resolution_choice === 'compensate_future' ? 'rgba(251, 191, 36, 0.22)' : 'rgba(15, 23, 42, 0.8)',
                          color: '#fde68a'
                        }}
                      >
                        <div>(i) Give Future Compensation Class (ⓒ)</div>
                        <div style={{ fontSize: '0.68rem', color: '#cbd5e1', fontWeight: 500, marginTop: '3px' }}>
                          Flags all {dpc.affected_student_ids?.length || 0} student(s) in Unresolved Attention Records so you can assign a future make-up slot.
                        </div>
                      </button>

                      <button
                        onClick={() => handleResolveDeletedClass(dpc.exception_id, 'remove_attendance_only')}
                        disabled={resolvingExcId === `${dpc.exception_id}_remove_attendance_only`}
                        className="btn btn-secondary"
                        style={{
                          padding: '10px 12px',
                          fontSize: '0.75rem',
                          fontWeight: 800,
                          textAlign: 'left',
                          borderColor: dpc.resolution_choice === 'remove_attendance_only' ? '#38bdf8' : 'rgba(56, 189, 248, 0.4)',
                          background: dpc.resolution_choice === 'remove_attendance_only' ? 'rgba(56, 189, 248, 0.22)' : 'rgba(15, 23, 42, 0.8)',
                          color: '#bae6fd'
                        }}
                      >
                        <div>(ii) Delete from Student Attendance History Only</div>
                        <div style={{ fontSize: '0.68rem', color: '#cbd5e1', fontWeight: 500, marginTop: '3px' }}>
                          Removes this session from the student's Actual Attended Classes log without requiring a future make-up.
                        </div>
                      </button>

                      <button
                        onClick={() => handleResolveDeletedClass(dpc.exception_id, 'delete_entirely')}
                        disabled={resolvingExcId === `${dpc.exception_id}_delete_entirely`}
                        className="btn btn-secondary"
                        style={{
                          padding: '10px 12px',
                          fontSize: '0.75rem',
                          fontWeight: 800,
                          textAlign: 'left',
                          borderColor: dpc.resolution_choice === 'delete_entirely' ? '#10b981' : 'rgba(16, 185, 129, 0.4)',
                          background: dpc.resolution_choice === 'delete_entirely' ? 'rgba(16, 185, 129, 0.22)' : 'rgba(15, 23, 42, 0.8)',
                          color: '#a7f3d0'
                        }}
                      >
                        <div>(iii) Delete Class Entirely (-1 Academy & -1 Trainer)</div>
                        <div style={{ fontSize: '0.68rem', color: '#cbd5e1', fontWeight: 500, marginTop: '3px' }}>
                          Cancels this batch session completely: reduces Academy Total Classes by -1 and Coach {dpc.coach_name}'s count by -1.
                        </div>
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ==================================================================== */}
      {/* NEW SECTION B: COACH DAILY AVAILABILITY & FREE SLOTS EXPLORER        */}
      {/* ==================================================================== */}
      {activeSection === 'coach_explorer' && (
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-gold)', borderRadius: 'var(--radius-lg)', padding: '20px', marginBottom: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', marginBottom: '16px' }}>
            <div>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 900, color: '#fff', margin: 0 }}>
                ♟️ Coach Daily Availability, Priority & Free Timings Explorer ({activeMonth})
              </h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
                Select any date to see which coaches are free, their preferred timing windows, and exceptional operating hours (acknowledgement required). New coaches sit at the bottom of existing batch priority and are prioritized for New Slots.
              </p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <label style={{ fontSize: '0.78rem', fontWeight: 800, color: 'var(--accent-gold)' }}>SELECT DATE:</label>
              <select
                value={selectedExplorerDate}
                onChange={(e) => setSelectedExplorerDate(e.target.value)}
                className="input-field"
                style={{ padding: '6px 12px', fontSize: '0.82rem', fontWeight: 800 }}
              >
                {coachExplorerDays.map(dObj => (
                  <option key={dObj.date} value={dObj.date}>
                    {dObj.date} ({dObj.day}) — {dObj.available_coaches_count} Coaches Free
                  </option>
                ))}
              </select>
            </div>
          </div>

          {(() => {
            const dayData = coachExplorerDays.find(d => d.date === selectedExplorerDate) || coachExplorerDays[0];
            if (!dayData) {
              return <div style={{ padding: '24px', color: 'var(--text-muted)' }}>Loading coach availability across {activeMonth}...</div>;
            }
            return (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '14px' }}>
                {(dayData.coaches || []).map((cItem) => (
                  <div
                    key={cItem.coach_name}
                    style={{
                      background: 'rgba(15, 23, 42, 0.9)',
                      border: cItem.is_new_coach ? '1.5px solid #a855f7' : '1px solid var(--border-color)',
                      borderRadius: '10px',
                      padding: '14px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '8px'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <strong style={{ fontSize: '0.95rem', color: '#fff' }}>Coach {cItem.coach_name}</strong>
                        {cItem.is_new_coach && (
                          <span className="badge" style={{ background: 'rgba(168, 85, 247, 0.2)', color: '#c084fc', border: '1px solid #a855f7', fontSize: '0.65rem' }}>
                            NEW COACH (High Priority for New Slots)
                          </span>
                        )}
                      </div>
                      <span className="badge badge-gold" style={{ fontSize: '0.7rem' }}>
                        Day Load: {cItem.daily_assigned}/{cItem.daily_limit} · Mo: {cItem.monthly_assigned}/{cItem.monthly_limit || 'Flex'}
                      </span>
                    </div>

                    <div style={{ fontSize: '0.74rem', color: '#93c5fd' }}>
                      <strong>Qualified Levels:</strong> {(cItem.levels_handled || []).join(', ') || 'Tournament Only'}
                    </div>
                    <div style={{ fontSize: '0.74rem', color: '#fde68a' }}>
                      <strong>Preferred Window ({dayData.day}):</strong> {cItem.preferred_window}
                    </div>

                    {/* Free Preferred Timings */}
                    <div>
                      <div style={{ fontSize: '0.7rem', fontWeight: 800, color: '#34d399', marginBottom: '4px' }}>
                        ✓ FREE PREFERRED SLOTS ({cItem.free_preferred_slots?.length || 0}):
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
                        {(cItem.free_preferred_slots || []).length === 0 ? (
                          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>No preferred slots free</span>
                        ) : (
                          cItem.free_preferred_slots.map(t => (
                            <span
                              key={t}
                              style={{
                                background: 'rgba(16, 185, 129, 0.15)',
                                border: '1px solid rgba(52, 211, 153, 0.4)',
                                color: '#6ee7b7',
                                padding: '2px 7px',
                                borderRadius: '6px',
                                fontSize: '0.7rem',
                                fontWeight: 700
                              }}
                            >
                              {t}
                            </span>
                          ))
                        )}
                      </div>
                    </div>

                    {/* Exceptional Operating Timings */}
                    {cItem.free_exceptional_slots?.length > 0 && (
                      <div>
                        <div style={{ fontSize: '0.68rem', fontWeight: 800, color: '#f59e0b', marginBottom: '4px' }}>
                          ⚠️ EXCEPTIONAL FREE SLOTS (Outside Preference — Admin Acknowledgement):
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                          {cItem.free_exceptional_slots.slice(0, 6).map(t => (
                            <span
                              key={t}
                              style={{
                                background: 'rgba(245, 158, 11, 0.12)',
                                border: '1px solid rgba(245, 158, 11, 0.35)',
                                color: '#fcd34d',
                                padding: '2px 6px',
                                borderRadius: '6px',
                                fontSize: '0.68rem'
                              }}
                            >
                              {t}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            );
          })()}
        </div>
      )}

      {/* ==================================================================== */}
      {/* SECTION 0: NEW TRAINER ENGAGEMENT PROPOSALS (ADMIN ACCEPTANCE)        */}
      {/* ==================================================================== */}
      {activeSection === 'unresolved' && trainerProposals.length > 0 && (
        <div style={{
          background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.16) 0%, rgba(59, 130, 246, 0.12) 100%)',
          border: '1.5px solid #a855f7',
          borderRadius: 'var(--radius-lg)',
          padding: '18px 20px',
          marginBottom: '24px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ background: '#a855f7', color: '#fff', padding: '6px', borderRadius: '8px' }}>
                <UserCheck size={20} />
              </div>
              <div>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 900, color: '#fff', margin: 0 }}>
                  New Trainer Schedule Proposals (Awaiting Administrator Acceptance)
                </h3>
                <p style={{ fontSize: '0.75rem', color: '#e9d5ff', margin: '2px 0 0 0' }}>
                  Engine matched newly added or unscheduled trainers with qualified levels, free availability windows, and waiting students.
                </p>
              </div>
            </div>
            <span className="badge badge-gold" style={{ fontSize: '0.75rem', padding: '4px 10px' }}>
              {trainerProposals.length} Trainer Proposal(s)
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '14px' }}>
            {trainerProposals.map(tp => (
              <div
                key={tp.coach_name}
                style={{
                  background: 'rgba(15, 23, 42, 0.9)',
                  border: '1px solid rgba(168, 85, 247, 0.45)',
                  borderRadius: 'var(--radius-md)',
                  padding: '14px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px' }}>
                  <div>
                    <strong style={{ fontSize: '0.95rem', color: '#fff' }}>Coach {tp.coach_name}</strong>
                    <div style={{ fontSize: '0.725rem', color: '#c084fc' }}>
                      Qualified Levels: {tp.levels_handled.join(', ')}
                    </div>
                  </div>
                  <button
                    onClick={() => handleAcceptTrainerProposal(tp.coach_name, tp.proposed_slots)}
                    disabled={assigningId === `trainer_${tp.coach_name}`}
                    className="btn btn-primary"
                    style={{ padding: '6px 12px', fontSize: '0.75rem', fontWeight: 800 }}
                  >
                    {assigningId === `trainer_${tp.coach_name}` ? 'Assigning...' : `✓ Approve All ${tp.proposed_slots.length} Slots`}
                  </button>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {(tp.proposed_slots || []).map((slot, sIdx) => (
                    <div
                      key={sIdx}
                      style={{
                        background: 'rgba(255,255,255,0.03)',
                        border: '1px solid rgba(255,255,255,0.08)',
                        borderRadius: '6px',
                        padding: '6px 10px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        fontSize: '0.75rem'
                      }}
                    >
                      <div>
                        <strong style={{ color: '#fff' }}>{slot.date} ({slot.day.slice(0, 3)}) · {slot.start_time}</strong>
                        <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>
                          Level: {slot.student_level} ({slot.batch_type})
                          {slot.student_names?.length > 0 ? ` · Student: ${slot.student_names.join(', ')}` : ' · Open Batch Slot'}
                        </div>
                      </div>
                      <button
                        onClick={() => handleAcceptTrainerProposal(tp.coach_name, [slot])}
                        className="btn btn-secondary"
                        style={{ padding: '4px 8px', fontSize: '0.7rem', color: '#c084fc', borderColor: '#c084fc' }}
                      >
                        ✓ Accept Slot
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

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
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
                  <strong style={{ fontSize: '0.9rem', color: '#fff' }}>{opp.title}</strong>
                  <span className="badge badge-gold" style={{ fontSize: '0.7rem', whiteSpace: 'nowrap' }}>
                    Resolves {opp.student_count} Students
                  </span>
                </div>
                <div style={{ fontSize: '0.775rem', color: '#cbd5e1' }}>
                  Suggested Coach: <strong style={{ color: 'var(--accent-gold)' }}>{opp.suggested_coach}</strong> · {opp.day} at {opp.time_slot}
                </div>
                <div style={{ fontSize: '0.725rem', color: '#94a3b8' }}>
                  Students: {opp.student_names.join(', ')}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '6px', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '8px' }}>
                  <span style={{ fontSize: '0.74rem', color: '#34d399', fontWeight: 700, lineHeight: 1.35 }}>
                    💡 {opp.impact_summary}
                  </span>
                  <button
                    onClick={() => handleAcceptSmartBatch(opp)}
                    disabled={assigningId === `pool_${opp.opportunity_id}`}
                    className="btn btn-primary"
                    style={{
                      width: '100%',
                      padding: '8px 14px',
                      fontSize: '0.8rem',
                      fontWeight: 900,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '6px',
                      boxShadow: '0 0 12px rgba(251, 191, 36, 0.35)'
                    }}
                  >
                    <CheckCircle2 size={15} />
                    <span>{assigningId === `pool_${opp.opportunity_id}` ? 'Creating Pooled Slot...' : `✓ Approve Pooled Slot (${opp.student_count} Students)`}</span>
                  </button>
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
                Single-occurrence administrative modifications, compensation classes, and approved rule exceptions.
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
                placeholder="Search unscheduled student by name, ID, batch code, or level..."
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
                return (r.student_name || '').toLowerCase().includes(q) || (r.student_id || '').toLowerCase().includes(q) || (r.student_level || '').toLowerCase().includes(q) || (r.batch_name || '').toLowerCase().includes(q);
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
                    (rec.batch_name || '').toLowerCase().includes(q) ||
                    (rec.failure_reason || '').toLowerCase().includes(q)
                  );
                })
                .map(rec => {
                  const sid = rec.student_id;
                  const neededCount = rec.remaining_classes || (rec.required_classes - rec.scheduled_classes) || 1;
                  const dynSuggestions = engineSuggestionsMap[sid];
                  const isLoadingDyn = loadingSuggestions[sid];
                  const isCreatingNew = activeNewClassStudentId === sid;

                  // Rule 4: Dedicated Deleted Coach Batch Reassignment Card
                  if (rec.record_type === 'coach_reassignment' || rec.needs_coach_reassignment) {
                    const selectedCoach = reassignCoachMap[rec.class_id] || rec.recommended_coach || '';
                    const isReassigningSingle = reassigningId === `${rec.class_id}_single`;
                    const isReassigningBatch = reassigningId === `${rec.class_id}_all`;
                    return (
                      <div
                        key={`reassign_${rec.class_id}_${rec.batch_name}`}
                        className="glass-card"
                        style={{
                          padding: '22px',
                          background: 'rgba(15, 23, 42, 0.95)',
                          border: '1.5px solid #f43f5e',
                          borderRadius: 'var(--radius-lg)',
                          display: 'grid',
                          gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
                          gap: '24px',
                          alignItems: 'start',
                          boxShadow: '0 8px 30px rgba(244, 63, 94, 0.15)'
                        }}
                      >
                        {/* COLUMN 1: Affected Class, Batch & Students */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                            <div style={{ background: 'rgba(244, 63, 94, 0.2)', padding: '10px', borderRadius: 'var(--radius-md)', color: '#f43f5e' }}>
                              <UserX size={22} />
                            </div>
                            <div>
                              <span className="badge badge-danger" style={{ fontSize: '0.65rem', marginBottom: '4px' }}>
                                COACH REASSIGNMENT REQUIRED (RULE 4)
                              </span>
                              <h3 style={{ fontSize: '1.15rem', fontWeight: 900, color: '#fff', margin: '2px 0 0 0' }}>
                                Batch: {rec.batch_name}
                              </h3>
                              <div style={{ fontSize: '0.78rem', color: '#fda4af', marginTop: '2px' }}>
                                Original Coach: <strong style={{ color: '#fff' }}>{rec.deleted_coach_name}</strong> (Deleted from academy)
                              </div>
                            </div>
                          </div>

                          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                            <span className="badge badge-gold" style={{ fontSize: '0.72rem' }}>
                              {rec.date} ({rec.day}) · {rec.time_slot}
                            </span>
                            <span className="badge" style={{ background: 'rgba(56, 189, 248, 0.2)', color: '#38bdf8', border: '1px solid #0284c7', fontSize: '0.72rem' }}>
                              Level: {rec.student_level} (Batch {rec.batch_type})
                            </span>
                          </div>

                          <div style={{ background: 'rgba(0, 0, 0, 0.35)', padding: '10px 14px', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
                            <div style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                              Preserved Students ({rec.student_names?.length || rec.required_classes || 0}):
                            </div>
                            <div style={{ fontSize: '0.85rem', color: '#f1f5f9', marginTop: '3px', fontWeight: 600 }}>
                              {rec.student_names?.join(', ') || rec.student_name}
                            </div>
                          </div>

                          <div style={{ fontSize: '0.75rem', color: '#cbd5e1', lineHeight: '1.45', background: 'rgba(244, 63, 94, 0.1)', padding: '10px 14px', borderRadius: '8px', border: '1px solid rgba(244, 63, 94, 0.25)' }}>
                            <strong>Rule 4 Protection:</strong> Classes and student rosters are strictly preserved. Select a replacement coach below to reassign this session or the entire monthly quota for this batch.
                          </div>
                        </div>

                        {/* COLUMN 2: Engine Recommendation & Dedicated Reassignment Selector */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                          {/* Engine Suggestion Card */}
                          <div style={{
                            background: 'linear-gradient(135deg, rgba(234, 179, 8, 0.15) 0%, rgba(16, 185, 129, 0.12) 100%)',
                            border: '1.5px solid var(--accent-gold)',
                            borderRadius: '10px',
                            padding: '14px'
                          }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-gold)', fontWeight: 800, fontSize: '0.85rem' }}>
                              <Sparkles size={16} />
                              <span>⭐ Engine Suggested Replacement Coach</span>
                            </div>
                            <div style={{ fontSize: '1rem', fontWeight: 900, color: '#fff', marginTop: '6px' }}>
                              Coach {rec.recommended_coach}
                            </div>
                            <p style={{ fontSize: '0.75rem', color: '#fde68a', margin: '4px 0 0 0', lineHeight: '1.4' }}>
                              {rec.details || `Meets batch time (${rec.time_slot}), qualified for ${rec.student_level}, and free on ${rec.date}.`}
                            </p>
                          </div>

                          {/* Dedicated "Assign New Coach" Field */}
                          <div>
                            <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 800, color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                              Assign New Coach:
                            </label>
                            <select
                              value={selectedCoach}
                              onChange={(e) => setReassignCoachMap(prev => ({ ...prev, [rec.class_id]: e.target.value }))}
                              style={{
                                width: '100%',
                                padding: '10px 14px',
                                background: 'rgba(15, 23, 42, 0.85)',
                                border: '1.5px solid var(--accent-gold)',
                                borderRadius: '8px',
                                color: '#fff',
                                fontSize: '0.875rem',
                                fontWeight: 700
                              }}
                            >
                              <option value="">-- Select Replacement Coach --</option>
                              {rec.suggested_coaches && rec.suggested_coaches.length > 0 && (
                                <optgroup label="⭐ Engine Ranked Matches (Level Qualified & Free)">
                                  {rec.suggested_coaches.map(sc => (
                                    <option key={sc.coach_name} value={sc.coach_name}>
                                      Coach {sc.coach_name} (Rank #{sc.priority_rank} · Free at {rec.time_slot}) {sc.is_recommended ? '⭐ Best Match' : ''}
                                    </option>
                                  ))}
                                </optgroup>
                              )}
                              <optgroup label="All Academy Coaches">
                                {(coachList || DEFAULT_COACHES).filter(c => c !== rec.deleted_coach_name).map(cName => (
                                  <option key={cName} value={cName}>
                                    Coach {cName}
                                  </option>
                                ))}
                              </optgroup>
                            </select>
                          </div>

                          {/* Action Buttons */}
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            <button
                              onClick={() => handleReassignBatchCoach(rec.class_id, rec.batch_name, selectedCoach, true)}
                              disabled={!selectedCoach || isReassigningBatch || isReassigningSingle}
                              className="btn btn-primary"
                              style={{
                                padding: '10px 16px',
                                fontSize: '0.825rem',
                                fontWeight: 900,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: '8px',
                                background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                                color: '#000',
                                border: 'none',
                                boxShadow: '0 4px 14px rgba(16, 185, 129, 0.3)'
                              }}
                            >
                              <CheckCircle2 size={16} />
                              <span>{isReassigningBatch ? 'Reassigning Batch...' : `✓ Assign Coach for Entire Batch (All Remaining Classes)`}</span>
                            </button>

                            <button
                              onClick={() => handleReassignBatchCoach(rec.class_id, rec.batch_name, selectedCoach, false)}
                              disabled={!selectedCoach || isReassigningBatch || isReassigningSingle}
                              className="btn btn-secondary"
                              style={{
                                padding: '8px 14px',
                                fontSize: '0.8rem',
                                fontWeight: 800,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: '6px'
                              }}
                            >
                              <span>{isReassigningSingle ? 'Reassigning...' : `Assign for ${rec.date} Only`}</span>
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  }

                  return (
                    <div
                      key={`${sid}_${rec.class_id || ''}`}
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
                            Batch {rec.batch_type} {rec.batch_name ? `(${rec.batch_name})` : ''}
                          </span>
                          <span className="badge badge-danger" style={{ fontSize: '0.7rem' }}>
                            {rec.remaining_classes} of {rec.required_classes} Missing ({rec.scheduled_classes} Scheduled)
                          </span>
                        </div>

                        {/* Rule 9: Sunday Tournament Eligibility & Requirement Diagnosis */}
                        {rec.sunday_tournament_eligible ? (
                          <div style={{
                            background: 'rgba(59, 130, 246, 0.12)',
                            border: '1px solid rgba(59, 130, 246, 0.35)',
                            borderRadius: '6px',
                            padding: '6px 10px',
                            fontSize: '0.74rem',
                            color: '#93c5fd',
                            lineHeight: 1.35
                          }}>
                            <span style={{ fontWeight: 800, color: '#60a5fa' }}>🏆 Sunday Tournament Eligible:</span> {rec.tournament_requirement || 'Eligible for Sunday tournaments (09:00 AM – 02:30 PM, cap 20).'}
                          </div>
                        ) : (
                          <div style={{
                            background: 'rgba(148, 163, 184, 0.08)',
                            border: '1px solid rgba(148, 163, 184, 0.2)',
                            borderRadius: '6px',
                            padding: '5px 8px',
                            fontSize: '0.7rem',
                            color: '#94a3b8'
                          }}>
                            <span>📌 Non-Tournament: Regular class only ({rec.batch_type === 'I' ? 'Individual 1-on-1 private batch' : rec.student_level})</span>
                          </div>
                        )}

                        {/* Failure Reason Alert Box */}
                        <div style={{ background: 'rgba(244, 63, 94, 0.15)', border: '1px solid rgba(244, 63, 94, 0.3)', padding: '10px 14px', borderRadius: 'var(--radius-md)' }}>
                          <div style={{ fontSize: '0.75rem', fontWeight: 800, color: '#f43f5e', marginBottom: '2px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <AlertTriangle size={14} /> REASON FOR ATTENTION STATUS:
                          </div>
                          <div style={{ fontSize: '0.8rem', color: '#fecdd3', lineHeight: '1.4' }}>
                            {rec.failure_reason}
                          </div>
                        </div>

                        {/* Button to Load / Refresh Engine Option Ladder Suggestions */}
                        {!dynSuggestions && sid && sid !== 'N/A' && (
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
                              Engine generated <strong>{dynSuggestions.option_sets?.length || 0}</strong> complete schedule sets for {rec.student_name} ({neededCount} classes needed):
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
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                                  <div>
                                    <strong style={{ fontSize: '0.85rem', color: '#fff' }}>{setObj.set_name}</strong>
                                    <div style={{ fontSize: '0.725rem', color: 'var(--text-secondary)' }}>{setObj.description}</div>
                                  </div>
                                  <button
                                    onClick={() => handleAcceptOptionSet(sid, setObj, dynSuggestions.schedule_version)}
                                    disabled={assigningId === `${sid}_set_${setObj.set_id}`}
                                    className="btn btn-primary"
                                    style={{ padding: '6px 12px', fontSize: '0.75rem', fontWeight: 800, whiteSpace: 'nowrap' }}
                                  >
                                    {assigningId === `${sid}_set_${setObj.set_id}` ? 'Accepting...' : `✓ Accept All ${setObj.items?.length || 0} Classes`}
                                  </button>
                                </div>

                                <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', fontSize: '0.7rem', color: '#cbd5e1' }}>
                                  <span>Existing Batch Seats: <strong style={{ color: '#34d399' }}>{setObj.existing_seats_used}</strong></span>
                                  <span>New Slots Opened: <strong style={{ color: setObj.new_slots_needed > 0 ? '#60a5fa' : '#34d399' }}>{setObj.new_slots_needed}</strong></span>
                                  <span>Pattern: <strong>{setObj.pattern_match}</strong></span>
                                </div>

                                {/* Detailed Proposed Class Rows inside Option Set */}
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', maxHeight: '165px', overflowY: 'auto', paddingRight: '4px', marginTop: '4px', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '6px' }}>
                                  {(setObj.items || []).map((itm, iIdx) => (
                                    <div
                                      key={iIdx}
                                      style={{
                                        display: 'flex',
                                        justifyContent: 'space-between',
                                        alignItems: 'center',
                                        fontSize: '0.725rem',
                                        padding: '4px 8px',
                                        borderRadius: '4px',
                                        background: itm.is_new_slot ? 'rgba(59, 130, 246, 0.1)' : 'rgba(16, 185, 129, 0.08)',
                                        border: `1px solid ${itm.is_new_slot ? 'rgba(59, 130, 246, 0.25)' : 'rgba(16, 185, 129, 0.25)'}`
                                      }}
                                    >
                                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                                        <span className={`badge ${itm.is_new_slot ? 'badge-blue' : 'badge-gold'}`} style={{ fontSize: '0.6rem', padding: '1px 5px' }}>
                                          {itm.is_new_slot ? `New Slot (${itm.tier})` : `Existing (${itm.tier})`}
                                        </span>
                                        <strong style={{ color: '#fff' }}>{itm.date} ({itm.day?.slice(0, 3)})</strong>
                                        <span style={{ color: 'var(--accent-gold)' }}>· {itm.start_time}</span>
                                        <span style={{ color: '#cbd5e1' }}>· Coach {itm.coach_id}</span>
                                        {itm.fill_before && <span style={{ color: '#94a3b8', fontSize: '0.675rem' }}>({itm.fill_before}→{itm.fill_after})</span>}
                                      </div>
                                      <button
                                        onClick={() => handleAcceptSuggestionItem(sid, itm, dynSuggestions.schedule_version)}
                                        disabled={assigningId === `${sid}_${itm.class_id || itm.date}_${itm.start_time}`}
                                        style={{
                                          background: 'none',
                                          border: '1px solid rgba(251, 191, 36, 0.4)',
                                          borderRadius: '4px',
                                          color: 'var(--accent-gold)',
                                          padding: '2px 7px',
                                          fontSize: '0.675rem',
                                          fontWeight: 700,
                                          cursor: 'pointer'
                                        }}
                                      >
                                        ✓ Accept 1
                                      </button>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* CASE B: SINGLE-CLASS RANKED T1-T7 SUGGESTIONS */}
                        {dynSuggestions?.mode === 'single_class' && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
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
                                      No viable existing batch vacancy available for this student — see conflict-free New Slots below.
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
                                          <div style={{ fontSize: '0.825rem', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                                            <span className="badge badge-gold" style={{ fontSize: '0.65rem' }}>{item.tier}</span>
                                            <span>Coach {item.coach_id}</span>
                                            <span style={{ color: 'var(--accent-gold)' }}>• {item.date} ({item.day?.slice(0, 3)})</span>
                                            <span>· {item.start_time}</span>
                                          </div>
                                          <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                                            Fill: {item.fill_before} → {item.fill_after} · Purity: {item.level_purity} · Coach Rank: {item.coach_priority_rank}
                                          </div>
                                        </div>
                                        <button
                                          onClick={() => handleAcceptSuggestionItem(sid, item, dynSuggestions.schedule_version)}
                                          disabled={assigningId === `${sid}_${item.class_id || item.date}_${item.start_time}`}
                                          className="btn btn-secondary"
                                          style={{ padding: '6px 12px', fontSize: '0.75rem', color: 'var(--accent-gold)', borderColor: 'var(--accent-gold)', fontWeight: 800 }}
                                        >
                                          {assigningId === `${sid}_${item.class_id || item.date}_${item.start_time}` ? 'Assigning...' : '✓ Accept'}
                                        </button>
                                      </div>
                                    ))
                                  )}

                                  {/* 2. New Slot options (T4-T6) collapsed unless expanded or no existing options */}
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
                                              <div style={{ fontSize: '0.825rem', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                                                <span className="badge badge-blue" style={{ fontSize: '0.65rem' }}>{item.tier}</span>
                                                <span>New Slot: Coach {item.coach_id}</span>
                                                <span style={{ color: '#60a5fa' }}>• {item.date} ({item.day?.slice(0, 3)})</span>
                                                <span>· {item.start_time}</span>
                                              </div>
                                              <div style={{ fontSize: '0.7rem', color: '#93c5fd', marginTop: '2px' }}>
                                                Trainer & student available · Fill: {item.fill_before} → {item.fill_after}
                                              </div>
                                            </div>
                                            <button
                                              onClick={() => handleAcceptSuggestionItem(sid, item, dynSuggestions.schedule_version)}
                                              disabled={assigningId === `${sid}_${item.class_id || item.date}_${item.start_time}`}
                                              className="btn btn-secondary"
                                              style={{ padding: '6px 12px', fontSize: '0.75rem', color: '#60a5fa', borderColor: '#60a5fa', fontWeight: 800 }}
                                            >
                                              {assigningId === `${sid}_${item.class_id || item.date}_${item.start_time}` ? 'Assigning...' : '✓ Open Slot'}
                                            </button>
                                          </div>
                                        ))}
                                      </div>
                                    )}
                                  </div>

                                  {/* 3. 'Why not an existing slot?' panel */}
                                  {(() => {
                                    const rawReasons = dynSuggestions.reasons_rejected_summary;
                                    const reasonsArr = Array.isArray(rawReasons)
                                      ? rawReasons
                                      : (rawReasons && typeof rawReasons === 'object'
                                          ? Object.entries(rawReasons).map(([k, v]) => `${k}: ${v} batch(es)`)
                                          : []);
                                    if (reasonsArr.length === 0) return null;
                                    return (
                                      <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(255,255,255,0.06)', marginTop: '8px' }}>
                                        <strong style={{ fontSize: '0.725rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
                                          🔍 Why not other existing slots? (Evaluated batches):
                                        </strong>
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                                          {reasonsArr.map((r, rIdx) => (
                                            <div key={rIdx} style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                                              • {r}
                                            </div>
                                          ))}
                                        </div>
                                      </div>
                                    );
                                  })()}
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

                        {/* Custom Class Creator Panel Trigger & Form */}
                        {!isCreatingNew ? (
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
                        ) : (
                          <div style={{ background: 'rgba(15, 23, 42, 0.9)', border: '1px solid var(--accent-blue)', borderRadius: 'var(--radius-md)', padding: '12px', marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <strong style={{ fontSize: '0.8rem', color: '#60a5fa' }}>New Custom Slot for {rec.student_name}</strong>
                              <button onClick={() => setActiveNewClassStudentId(null)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                                <X size={14} />
                              </button>
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                              <div>
                                <label style={{ fontSize: '0.675rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '2px' }}>Coach</label>
                                <select value={newCoachName} onChange={e => setNewCoachName(e.target.value)} style={{ width: '100%', padding: '6px', fontSize: '0.75rem' }}>
                                  {coachesOptions.map(c => <option key={c} value={c}>{c}</option>)}
                                </select>
                              </div>
                              <div>
                                <label style={{ fontSize: '0.675rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '2px' }}>Date</label>
                                <input type="date" value={newDate} onChange={e => setNewDate(e.target.value)} style={{ width: '100%', padding: '6px', fontSize: '0.75rem' }} />
                              </div>
                              <div>
                                <label style={{ fontSize: '0.675rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '2px' }}>Time Slot</label>
                                <input type="text" value={newTimeSlot} onChange={e => setNewTimeSlot(e.target.value)} style={{ width: '100%', padding: '6px', fontSize: '0.75rem' }} />
                              </div>
                              <div>
                                <label style={{ fontSize: '0.675rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '2px' }}>Batch Type</label>
                                <select value={newBatchType} onChange={e => setNewBatchType(e.target.value)} style={{ width: '100%', padding: '6px', fontSize: '0.75rem' }}>
                                  <option value="G">Group (G) — 1 to 8</option>
                                  <option value="L">Limited (L) — 1 to 3</option>
                                  <option value="I">Individual (I) — 1</option>
                                </select>
                              </div>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                              <button type="button" onClick={() => setActiveNewClassStudentId(null)} className="btn btn-secondary" style={{ padding: '5px 10px', fontSize: '0.75rem' }}>Cancel</button>
                              <button type="button" onClick={() => handleCreateNewClassForStudent(rec)} disabled={creating} className="btn btn-primary" style={{ padding: '5px 12px', fontSize: '0.75rem', fontWeight: 800 }}>
                                {creating ? 'Creating...' : '✓ Save & Assign'}
                              </button>
                            </div>
                          </div>
                        )}
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
