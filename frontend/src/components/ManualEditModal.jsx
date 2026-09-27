import React, { useState, useEffect, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { AlertCircle, CheckCircle, X, ShieldAlert, UserPlus, UserMinus, Trash2, Search, UserCheck } from 'lucide-react';
import { validateManualOverride, applyManualEdit, deleteClass, getMasterStudents } from '../services/api';
import { OFFICIAL_LEVELS } from '../constants/levels';

export default function ManualEditModal({
  isOpen,
  onClose,
  targetClass,
  scheduleId,
  onSaveSuccess,
  onRefreshSchedule,
  masterStudents = []
}) {
  const [coachName, setCoachName] = useState(targetClass?.coach_name || '');
  const [studentLevel, setStudentLevel] = useState(targetClass?.student_level || 'Basic 1');
  const [batchType, setBatchType] = useState(targetClass?.batch_type || 'G');
  const [timeSlot, setTimeSlot] = useState(targetClass?.time_slot || '');
  const [dateStr, setDateStr] = useState(targetClass?.date || '');

  // Student Re-Assignment state inside batch
  const [studentIds, setStudentIds] = useState(targetClass?.student_ids || []);
  const [studentNames, setStudentNames] = useState(targetClass?.student_names || []);

  // Master students data & selection
  const [allStudents, setAllStudents] = useState(masterStudents);
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

  // Filtered by user search term (matches name, id, level, or batch)
  const filteredStudents = useMemo(() => {
    if (!studentSearchTerm.trim()) return availableStudents;
    const term = studentSearchTerm.trim().toLowerCase();
    return availableStudents.filter(s =>
      (s.student_name || '').toLowerCase().includes(term) ||
      (s.student_id || '').toLowerCase().includes(term) ||
      (s.student_level || '').toLowerCase().includes(term) ||
      (s.batch || s.batch_name || '').toLowerCase().includes(term)
    );
  }, [availableStudents, studentSearchTerm]);

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

  const handleAddStudent = () => {
    setStudentError('');
    if (!selectedStudentId) {
      setStudentError('Please select a student from the dropdown list.');
      return;
    }

    // STRICT CHECK: Student must exist in the master student records
    const foundStudent = allStudents.find(s => s.student_id === selectedStudentId);
    if (!foundStudent) {
      setStudentError(`Selected student '${selectedStudentId}' does not exist in master records. Only registered students can be added.`);
      return;
    }

    if (studentIds.includes(foundStudent.student_id)) {
      setStudentError(`${foundStudent.student_name} (${foundStudent.student_id}) is already assigned to this batch.`);
      return;
    }

    // Capacity checking warning / notice
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

              {/* Master Students Dropdown List */}
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
                  {filteredStudents.length === 0
                    ? '-- No matching students available --'
                    : `-- Select student (${filteredStudents.length} available) --`}
                </option>
                {filteredStudents.map(stu => (
                  <option key={stu.student_id} value={stu.student_id} style={{ color: '#fff', background: '#1e293b' }}>
                    {stu.student_name} ({stu.student_id}) · {stu.student_level || 'Level'} · Batch: {stu.batch || stu.batch_type || 'G'}
                  </option>
                ))}
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
