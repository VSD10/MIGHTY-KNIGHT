import React, { useState, useEffect, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { AlertCircle, CheckCircle, X, ShieldAlert, UserPlus, UserMinus, Trash2, Search, UserCheck, Sparkles, Award } from 'lucide-react';
import { validateManualOverride, applyManualEdit, deleteClass, getMasterStudents, getMasterBatches } from '../services/api';
import { OFFICIAL_LEVELS } from '../constants/levels';

export default function ManualEditModal({
  isOpen,
  onClose,
  targetClass,
  scheduleId,
  onSaveSuccess,
  onRefreshSchedule,
  masterStudents = [],
  masterBatches = []
}) {
  const [coachName, setCoachName] = useState(targetClass?.coach_name || '');
  const [studentLevel, setStudentLevel] = useState(targetClass?.student_level || 'Basic 1');
  const [batchType, setBatchType] = useState(targetClass?.batch_type || 'G');
  const [timeSlot, setTimeSlot] = useState(targetClass?.time_slot || '');
  const [dateStr, setDateStr] = useState(targetClass?.date || '');

  // Student Re-Assignment state inside batch
  const [studentIds, setStudentIds] = useState(targetClass?.student_ids || []);
  const [studentNames, setStudentNames] = useState(targetClass?.student_names || []);

  // Master students & batches data
  const [allStudents, setAllStudents] = useState(masterStudents);
  const [allBatches, setAllBatches] = useState(masterBatches);
  const [selectedStudentId, setSelectedStudentId] = useState('');
  const [studentSearchTerm, setStudentSearchTerm] = useState('');
  const [studentError, setStudentError] = useState('');

  const [warnings, setWarnings] = useState([]);
  const [validating, setValidating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [validated, setValidated] = useState(false);

  useEffect(() => {
    if (isOpen) {
      const originalOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = originalOverflow;
      };
    }
  }, [isOpen]);

  // Load master students if not passed as prop
  useEffect(() => {
    if (masterStudents && masterStudents.length > 0) {
      setAllStudents(masterStudents);
    } else if (isOpen) {
      getMasterStudents()
        .then(res => {
          if (res && res.students) {
            setAllStudents(res.students);
          }
        })
        .catch(err => console.error("Error loading master students:", err));
    }
  }, [isOpen, masterStudents]);

  // Load master batches if not passed as prop
  useEffect(() => {
    if (masterBatches && masterBatches.length > 0) {
      setAllBatches(masterBatches);
    } else if (isOpen) {
      getMasterBatches()
        .then(res => {
          if (res && res.batches) {
            setAllBatches(res.batches);
          }
        })
        .catch(err => console.error("Error loading master batches:", err));
    }
  }, [isOpen, masterBatches]);

  // Sync state when targetClass or allStudents changes
  useEffect(() => {
    if (targetClass) {
      setCoachName(targetClass.coach_name || '');
      setStudentLevel(targetClass.student_level || 'Basic 1');
      setBatchType(targetClass.batch_type || 'G');
      setTimeSlot(targetClass.time_slot || '');
      setDateStr(targetClass.date || '');

      const rawIds = targetClass.student_ids || [];
      setStudentIds(rawIds);

      // Resolve student names from master students if available
      const resolvedNames = rawIds.map((sid, idx) => {
        const found = allStudents.find(s => s.student_id === sid);
        if (found && found.student_name) return found.student_name;
        if (targetClass.student_names && targetClass.student_names[idx]) return targetClass.student_names[idx];
        return sid;
      });
      setStudentNames(resolvedNames);

      setSelectedStudentId('');
      setStudentSearchTerm('');
      setStudentError('');
      setValidated(false);
      setWarnings([]);
    }
  }, [targetClass, allStudents]);

  // List of all registered students who are NOT already assigned to this batch
  const availableStudents = useMemo(() => {
    const assignedSet = new Set(studentIds);
    return allStudents.filter(s => !assignedSet.has(s.student_id));
  }, [allStudents, studentIds]);

  // Resolve matching batch object from master batches
  const currentBatchObj = useMemo(() => {
    if (!targetClass) return null;
    const bName = (targetClass.batch_name || '').toLowerCase().trim();
    return allBatches.find(b =>
      (b.batch_name || '').toLowerCase().trim() === bName ||
      (b.batch_id || '').toLowerCase().trim() === bName
    ) || null;
  }, [allBatches, targetClass]);

  // Enrolled student IDs for this batch
  const batchEnrolledIds = useMemo(() => {
    if (!currentBatchObj) return new Set();
    const ids = currentBatchObj.student_ids || [];
    return new Set(ids);
  }, [currentBatchObj]);

  // Group available students into:
  // 1. Batch Enrolled (highest priority suggestions)
  // 2. Level Match (matching skill level)
  // 3. Other Available Students
  const { suggestedEnrolled, suggestedLevelMatch, otherStudents } = useMemo(() => {
    const enrolled = [];
    const levelMatch = [];
    const others = [];

    const targetLvl = (studentLevel || targetClass?.student_level || '').toLowerCase().trim();

    availableStudents.forEach(stu => {
      // 1. Is this student explicitly enrolled in this batch?
      if (batchEnrolledIds.has(stu.student_id) || (stu.batch && currentBatchObj && stu.batch.toLowerCase() === currentBatchObj.batch_name?.toLowerCase())) {
        enrolled.push(stu);
      }
      // 2. Or is student's level matching this class?
      else if (stu.student_level && stu.student_level.toLowerCase().trim() === targetLvl) {
        levelMatch.push(stu);
      }
      // 3. Otherwise other registered students
      else {
        others.push(stu);
      }
    });

    return {
      suggestedEnrolled: enrolled,
      suggestedLevelMatch: levelMatch,
      otherStudents: others
    };
  }, [availableStudents, batchEnrolledIds, currentBatchObj, studentLevel, targetClass]);

  // Filter lists by search term
  const filterListByTerm = (list) => {
    if (!studentSearchTerm.trim()) return list;
    const term = studentSearchTerm.trim().toLowerCase();
    return list.filter(s =>
      (s.student_name || '').toLowerCase().includes(term) ||
      (s.student_id || '').toLowerCase().includes(term) ||
      (s.student_level || '').toLowerCase().includes(term) ||
      (s.batch || s.batch_name || '').toLowerCase().includes(term)
    );
  };

  const filteredSuggestedEnrolled = useMemo(() => filterListByTerm(suggestedEnrolled), [suggestedEnrolled, studentSearchTerm]);
  const filteredSuggestedLevelMatch = useMemo(() => filterListByTerm(suggestedLevelMatch), [suggestedLevelMatch, studentSearchTerm]);
  const filteredOtherStudents = useMemo(() => filterListByTerm(otherStudents), [otherStudents, studentSearchTerm]);
  const totalFilteredCount = filteredSuggestedEnrolled.length + filteredSuggestedLevelMatch.length + filteredOtherStudents.length;

  if (!isOpen || !targetClass) return null;

  const triggerRefresh = () => {
    if (onSaveSuccess) onSaveSuccess();
    if (onRefreshSchedule) onRefreshSchedule();
  };

  const levels = OFFICIAL_LEVELS;

  const handleRemoveStudent = (index) => {
    const updatedIds = studentIds.filter((_, idx) => idx !== index);
    const updatedNames = studentNames.filter((_, idx) => idx !== index);
    setStudentIds(updatedIds);
    setStudentNames(updatedNames);
    setStudentError('');
    setValidated(false);
  };

  // Unified add student logic
  const addStudentById = (studentId) => {
    setStudentError('');
    if (!studentId) {
      setStudentError('Please select a student from the dropdown list or suggestions.');
      return;
    }

    const foundStudent = allStudents.find(s => s.student_id === studentId);
    if (!foundStudent) {
      setStudentError(`Selected student '${studentId}' does not exist in master records.`);
      return;
    }

    if (studentIds.includes(foundStudent.student_id)) {
      setStudentError(`${foundStudent.student_name} (${foundStudent.student_id}) is already assigned to this batch session.`);
      return;
    }

    const maxCap = batchType === 'I' ? 1 : (batchType === 'L' ? 4 : 10);
    if (studentIds.length >= maxCap) {
      if (!window.confirm(`Notice: Adding another student will exceed the standard ${batchType} capacity (${maxCap} max). Do you want to proceed?`)) {
        return;
      }
    }

    setStudentIds([...studentIds, foundStudent.student_id]);
    setStudentNames([...studentNames, foundStudent.student_name]);
    setSelectedStudentId('');
    setStudentSearchTerm('');
    setStudentError('');
    setValidated(false);
  };

  const handleAddStudent = () => {
    addStudentById(selectedStudentId);
  };

  const handleAddSuggestedStudent = (stu) => {
    addStudentById(stu.student_id);
  };

  const handleValidate = async () => {
    setValidating(true);
    setWarnings([]);
    try {
      const res = await validateManualOverride(scheduleId, {
        class_id: targetClass.class_id,
        coach_name: coachName,
        student_level: studentLevel,
        batch_type: batchType,
        date: dateStr,
        time_slot: timeSlot,
        student_ids: studentIds
      });
      setWarnings(res.warnings || []);
      setValidated(true);
    } catch (err) {
      setWarnings(['Failed to validate manual override rules.']);
    } finally {
      setValidating(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await applyManualEdit(scheduleId, {
        class_id: targetClass.class_id,
        coach_name: coachName,
        student_level: studentLevel,
        batch_type: batchType,
        date: dateStr,
        time_slot: timeSlot,
        student_ids: studentIds
      });
      triggerRefresh();
      onClose();
    } catch (err) {
      alert('Failed to save manual edit: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteClass = async () => {
    if (!window.confirm(`Are you sure you want to remove Class ${targetClass.class_id} (${targetClass.coach_name} - ${targetClass.time_slot}) from Output 2?`)) return;
    setSaving(true);
    try {
      await deleteClass(scheduleId, targetClass.class_id);
      triggerRefresh();
      onClose();
    } catch (err) {
      alert('Failed to delete class: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSaving(false);
    }
  };

  const modalContent = (
    <div style={{
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0, 0, 0, 0.82)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '20px'
    }}>
      <div className="glass-panel" style={{ width: '100%', maxWidth: '680px', padding: '28px', position: 'relative', maxHeight: '90vh', overflowY: 'auto' }}>
        <button
          onClick={onClose}
          style={{ position: 'absolute', top: '20px', right: '20px', background: 'none', border: 'none', color: '#9ca3af', cursor: 'pointer' }}
        >
          <X size={20} />
        </button>

        <h2 style={{ fontSize: '1.2rem', fontWeight: 800, color: '#fff', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ShieldAlert style={{ color: 'var(--accent-gold)' }} /> Manual Administrative Override (Section 37)
        </h2>
        <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', marginBottom: '20px' }}>
          Manually modify class coach, student level, batch type, date, time slot, or student roster.
        </p>

        {/* Form Controls */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginBottom: '20px' }}>
          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>ASSIGNED COACH</label>
            <input
              type="text"
              value={coachName}
              onChange={e => { setCoachName(e.target.value); setValidated(false); }}
              style={{
                width: '100%', padding: '10px', borderRadius: 'var(--radius-md)',
                background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontWeight: 600
              }}
            />
          </div>

          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>STUDENT LEVEL</label>
            <select
              value={studentLevel}
              onChange={e => { setStudentLevel(e.target.value); setValidated(false); }}
              style={{
                width: '100%', padding: '10px', borderRadius: 'var(--radius-md)',
                background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontWeight: 600
              }}
            >
              {levels.map(lvl => (
                <option key={lvl} value={lvl}>{lvl}</option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>BATCH TYPE</label>
            <select
              value={batchType}
              onChange={e => { setBatchType(e.target.value); setValidated(false); }}
              style={{
                width: '100%', padding: '10px', borderRadius: 'var(--radius-md)',
                background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontWeight: 600
              }}
            >
              <option value="G">G — Group Batch (4–10 students)</option>
              <option value="L">L — Limited Students Batch (1–4 students)</option>
              <option value="I">I — Individual Batch (1 student)</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>DATE</label>
            <input
              type="date"
              value={dateStr}
              onChange={e => { setDateStr(e.target.value); setValidated(false); }}
              style={{
                width: '100%', padding: '10px', borderRadius: 'var(--radius-md)',
                background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontWeight: 600
              }}
            />
          </div>

          <div style={{ gridColumn: 'span 2' }}>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>TIME SLOT</label>
            <input
              type="text"
              value={timeSlot}
              onChange={e => { setTimeSlot(e.target.value); setValidated(false); }}
              style={{
                width: '100%', padding: '10px', borderRadius: 'var(--radius-md)',
                background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontWeight: 600
              }}
            />
          </div>
        </div>

        {/* STUDENT BATCH RE-ASSIGNMENT PANEL */}
        <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '16px', marginBottom: '16px' }}>
          <div style={{ fontSize: '0.8rem', fontWeight: 800, color: 'var(--accent-gold)', marginBottom: '10px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span>STUDENTS ASSIGNED TO THIS BATCH ({studentIds.length})</span>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              Batch Target: {batchType === 'I' ? '1 student (Individual)' : (batchType === 'L' ? '1–4 students (Limited)' : '4–10 students (Group)')}
            </span>
          </div>

          {/* Current Roster Badges */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '14px', minHeight: '36px' }}>
            {studentIds.length === 0 ? (
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic', padding: '6px 0' }}>
                No students currently assigned to this batch. Select a student below to add.
              </span>
            ) : (
              studentIds.map((sId, idx) => {
                const sObj = allStudents.find(s => s.student_id === sId);
                const sName = studentNames[idx] || sObj?.student_name || sId;
                const sLevel = sObj?.student_level;
                return (
                  <div
                    key={idx}
                    style={{
                      background: 'rgba(251, 191, 36, 0.12)',
                      border: '1px solid var(--accent-gold)',
                      borderRadius: 'var(--radius-sm)',
                      padding: '5px 10px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      fontSize: '0.775rem',
                      color: '#fff'
                    }}
                  >
                    <span style={{ fontWeight: 600 }}>{sName}</span>
                    <span style={{ fontSize: '0.675rem', color: 'var(--text-muted)' }}>({sId})</span>
                    {sLevel && (
                      <span style={{ fontSize: '0.675rem', background: 'rgba(255, 255, 255, 0.1)', padding: '1px 5px', borderRadius: '4px', color: 'var(--accent-gold)' }}>
                        {sLevel}
                      </span>
                    )}
                    <button
                      type="button"
                      onClick={() => handleRemoveStudent(idx)}
                      style={{ background: 'none', border: 'none', color: '#f43f5e', cursor: 'pointer', display: 'flex', alignItems: 'center', padding: '0 2px' }}
                      title={`Remove ${sName} from this batch`}
                    >
                      <UserMinus size={14} />
                    </button>
                  </div>
                );
              })
            )}
          </div>

          {/* SMART BATCH SUGGESTIONS PANEL */}
          <div
            style={{
              marginBottom: '14px',
              background: 'rgba(234, 179, 8, 0.06)',
              border: '1px solid rgba(234, 179, 8, 0.25)',
              borderRadius: 'var(--radius-md)',
              padding: '12px'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', flexWrap: 'wrap', gap: '6px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Sparkles size={14} style={{ color: 'var(--accent-gold)' }} />
                <span style={{ fontSize: '0.8rem', fontWeight: 800, color: 'var(--accent-gold)' }}>
                  Suggested for this Batch ({targetClass.batch_name || targetClass.student_level}):
                </span>
                {suggestedEnrolled.length > 0 && (
                  <span style={{ fontSize: '0.7rem', padding: '2px 7px', borderRadius: '4px', background: 'rgba(16, 185, 129, 0.2)', color: '#34d399', fontWeight: 700 }}>
                    {suggestedEnrolled.length} Enrolled in Batch
                  </span>
                )}
              </div>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                Click any student below to immediately add
              </span>
            </div>

            {suggestedEnrolled.length === 0 && suggestedLevelMatch.length === 0 ? (
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic', padding: '4px 0' }}>
                ✓ All enrolled students for this batch are already in this session.
              </div>
            ) : (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {/* 1. Primary: Students Enrolled in this Batch */}
                {suggestedEnrolled.map(stu => (
                  <button
                    key={stu.student_id}
                    type="button"
                    onClick={() => handleAddSuggestedStudent(stu)}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '5px 10px',
                      borderRadius: '6px',
                      background: 'rgba(16, 185, 129, 0.15)',
                      border: '1px solid rgba(16, 185, 129, 0.4)',
                      color: '#fff',
                      fontSize: '0.75rem',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease'
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = 'rgba(16, 185, 129, 0.3)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'rgba(16, 185, 129, 0.15)'}
                    title={`Click to add ${stu.student_name} (Enrolled in ${targetClass.batch_name})`}
                  >
                    <UserPlus size={13} style={{ color: '#34d399' }} />
                    <span style={{ fontWeight: 700 }}>{stu.student_name}</span>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.675rem' }}>({stu.student_id})</span>
                    <span style={{ fontSize: '0.65rem', background: 'rgba(16, 185, 129, 0.3)', color: '#34d399', padding: '1px 5px', borderRadius: '3px', fontWeight: 700 }}>
                      Batch
                    </span>
                  </button>
                ))}

                {/* 2. Secondary: Level Matching (Show up to 6 quick chips) */}
                {suggestedLevelMatch.slice(0, 6).map(stu => (
                  <button
                    key={stu.student_id}
                    type="button"
                    onClick={() => handleAddSuggestedStudent(stu)}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '5px 10px',
                      borderRadius: '6px',
                      background: 'rgba(59, 130, 246, 0.12)',
                      border: '1px solid rgba(59, 130, 246, 0.35)',
                      color: '#fff',
                      fontSize: '0.75rem',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease'
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = 'rgba(59, 130, 246, 0.25)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'rgba(59, 130, 246, 0.12)'}
                    title={`Click to add ${stu.student_name} (Level Match: ${stu.student_level})`}
                  >
                    <UserPlus size={13} style={{ color: '#60a5fa' }} />
                    <span style={{ fontWeight: 700 }}>{stu.student_name}</span>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.675rem' }}>({stu.student_id})</span>
                    <span style={{ fontSize: '0.65rem', background: 'rgba(59, 130, 246, 0.25)', color: '#93c5fd', padding: '1px 5px', borderRadius: '3px', fontWeight: 700 }}>
                      {stu.student_level}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Add Registered Student Selector */}
          <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <label style={{ fontSize: '0.725rem', fontWeight: 700, color: 'var(--text-secondary)' }}>
                SELECT STUDENT TO ADD ({availableStudents.length} AVAILABLE FROM MASTER DATA)
              </label>
              {availableStudents.length > 0 && (
                <span style={{ fontSize: '0.675rem', color: 'var(--text-muted)' }}>
                  Only registered master students can be enrolled
                </span>
              )}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr auto', gap: '8px', alignItems: 'center' }}>
              {/* Quick Search Filter */}
              <div style={{ position: 'relative' }}>
                <Search size={13} style={{ position: 'absolute', left: '8px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                <input
                  type="text"
                  placeholder="Filter name or ID..."
                  value={studentSearchTerm}
                  onChange={e => { setStudentSearchTerm(e.target.value); setStudentError(''); }}
                  style={{
                    width: '100%',
                    padding: '8px 8px 8px 26px',
                    fontSize: '0.75rem',
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-sm)',
                    color: '#fff'
                  }}
                />
              </div>

              {/* Master Students Dropdown List Grouped by Batch Suggestion */}
              <select
                value={selectedStudentId}
                onChange={e => { setSelectedStudentId(e.target.value); setStudentError(''); }}
                style={{
                  width: '100%',
                  padding: '8px 10px',
                  fontSize: '0.75rem',
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-sm)',
                  color: selectedStudentId ? '#fff' : 'var(--text-muted)',
                  fontWeight: selectedStudentId ? 600 : 400
                }}
              >
                <option value="">
                  {totalFilteredCount === 0
                    ? '-- No matching students available --'
                    : `-- Select student (${totalFilteredCount} available) --`}
                </option>

                {/* 1. Group: Enrolled in this Batch */}
                {filteredSuggestedEnrolled.length > 0 && (
                  <optgroup label={`⭐ SUGGESTED: ENROLLED IN THIS BATCH (${filteredSuggestedEnrolled.length})`}>
                    {filteredSuggestedEnrolled.map(stu => (
                      <option key={stu.student_id} value={stu.student_id} style={{ color: '#34d399', background: '#1e293b', fontWeight: 700 }}>
                        ★ {stu.student_name} ({stu.student_id}) · {stu.student_level} · Batch: {targetClass.batch_name}
                      </option>
                    ))}
                  </optgroup>
                )}

                {/* 2. Group: Level Match */}
                {filteredSuggestedLevelMatch.length > 0 && (
                  <optgroup label={`🎯 LEVEL MATCH: ${studentLevel || targetClass.student_level} (${filteredSuggestedLevelMatch.length})`}>
                    {filteredSuggestedLevelMatch.map(stu => (
                      <option key={stu.student_id} value={stu.student_id} style={{ color: '#93c5fd', background: '#1e293b' }}>
                        {stu.student_name} ({stu.student_id}) · {stu.student_level}
                      </option>
                    ))}
                  </optgroup>
                )}

                {/* 3. Group: Other Master Students */}
                {filteredOtherStudents.length > 0 && (
                  <optgroup label={`OTHER REGISTERED STUDENTS (${filteredOtherStudents.length})`}>
                    {filteredOtherStudents.map(stu => (
                      <option key={stu.student_id} value={stu.student_id} style={{ color: '#cbd5e1', background: '#1e293b' }}>
                        {stu.student_name} ({stu.student_id}) · {stu.student_level || 'Level'} · {stu.batch || stu.batch_type || 'G'}
                      </option>
                    ))}
                  </optgroup>
                )}
              </select>

              {/* Add Student Button */}
              <button
                type="button"
                onClick={handleAddStudent}
                disabled={!selectedStudentId}
                className="btn btn-primary"
                style={{
                  padding: '8px 14px',
                  fontSize: '0.75rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '5px',
                  whiteSpace: 'nowrap',
                  opacity: selectedStudentId ? 1 : 0.5,
                  cursor: selectedStudentId ? 'pointer' : 'not-allowed'
                }}
              >
                <UserPlus size={14} /> Add Student
              </button>
            </div>

            {studentError && (
              <div style={{ marginTop: '8px', fontSize: '0.725rem', color: '#f43f5e', display: 'flex', alignItems: 'center', gap: '5px' }}>
                <AlertCircle size={13} /> {studentError}
              </div>
            )}
          </div>
        </div>

        {/* Warning Messages */}
        {warnings.length > 0 && (
          <div style={{ background: 'rgba(244, 63, 94, 0.15)', border: '1px solid rgba(244, 63, 94, 0.3)', borderRadius: 'var(--radius-md)', padding: '12px', marginBottom: '16px' }}>
            <div style={{ fontSize: '0.8rem', fontWeight: 800, color: '#f43f5e', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <AlertCircle size={16} /> Constraint Rule Warnings Detected:
            </div>
            <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '0.775rem', color: '#fca5a5' }}>
              {warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          </div>
        )}

        {validated && warnings.length === 0 && (
          <div style={{ background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.3)', borderRadius: 'var(--radius-md)', padding: '10px 14px', marginBottom: '16px', color: '#10b981', fontSize: '0.8rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px' }}>
            <CheckCircle size={16} /> Rule Validation Passed: No hard constraint conflicts!
          </div>
        )}

        {/* Actions */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '20px' }}>
          <button
            onClick={handleDeleteClass}
            disabled={saving}
            className="btn btn-secondary"
            style={{ borderColor: '#ef4444', color: '#ef4444', display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Trash2 size={14} /> Delete Class
          </button>

          <div style={{ display: 'flex', gap: '12px' }}>
            <button onClick={onClose} className="btn btn-secondary">Cancel</button>
            {!validated ? (
              <button onClick={handleValidate} disabled={validating} className="btn btn-secondary" style={{ borderColor: 'var(--accent-gold)', color: 'var(--accent-gold)' }}>
                {validating ? 'Checking Rules...' : 'Validate Rules'}
              </button>
            ) : (
              <button onClick={handleSave} disabled={saving} className="btn btn-primary">
                {saving ? 'Saving...' : 'Acknowledge & Save Override'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}
