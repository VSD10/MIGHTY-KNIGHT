import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { AlertCircle, CheckCircle, X, ShieldAlert, UserPlus, UserMinus, Trash2 } from 'lucide-react';
import { validateManualOverride, applyManualEdit, deleteClass } from '../services/api';

export default function ManualEditModal({ isOpen, onClose, targetClass, scheduleId, onSaveSuccess, onRefreshSchedule }) {
  useEffect(() => {
    if (isOpen) {
      const originalOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = originalOverflow;
      };
    }
  }, [isOpen]);

  if (!isOpen || !targetClass) return null;

  const triggerRefresh = () => {
    if (onSaveSuccess) onSaveSuccess();
    if (onRefreshSchedule) onRefreshSchedule();
  };

  const [coachName, setCoachName] = useState(targetClass.coach_name || '');
  const [studentLevel, setStudentLevel] = useState(targetClass.student_level || 'Basic 1');
  const [batchType, setBatchType] = useState(targetClass.batch_type || 'G');
  const [timeSlot, setTimeSlot] = useState(targetClass.time_slot || '');
  const [dateStr, setDateStr] = useState(targetClass.date || '');
  
  // Student Re-Assignment state inside batch
  const [studentIds, setStudentIds] = useState(targetClass.student_ids || []);
  const [studentNames, setStudentNames] = useState(targetClass.student_names || []);
  const [newStudentInput, setNewStudentInput] = useState('');

  const [warnings, setWarnings] = useState([]);
  const [validating, setValidating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [validated, setValidated] = useState(false);

  useEffect(() => {
    if (targetClass) {
      setCoachName(targetClass.coach_name || '');
      setStudentLevel(targetClass.student_level || 'Basic 1');
      setBatchType(targetClass.batch_type || 'G');
      setTimeSlot(targetClass.time_slot || '');
      setDateStr(targetClass.date || '');
      setStudentIds(targetClass.student_ids || []);
      setStudentNames(targetClass.student_names || []);
      setNewStudentInput('');
      setValidated(false);
      setWarnings([]);
    }
  }, [targetClass]);

  const levels = [
    'Basic 1',
    'Basic 2',
    'Beginner 1',
    'Beginner 2',
    'Beginner 3',
    'Early Intermediate 1',
    'Early Intermediate 2',
    'Intermediate 1',
    'Intermediate'
  ];

  const handleRemoveStudent = (index) => {
    const updatedIds = studentIds.filter((_, idx) => idx !== index);
    const updatedNames = studentNames.filter((_, idx) => idx !== index);
    setStudentIds(updatedIds);
    setStudentNames(updatedNames);
    setValidated(false);
  };

  const handleAddStudent = () => {
    if (!newStudentInput.trim()) return;
    const sId = newStudentInput.trim().toUpperCase();
    if (studentIds.includes(sId)) {
      alert(`Student ${sId} is already in this class batch.`);
      return;
    }
    setStudentIds([...studentIds, sId]);
    setStudentNames([...studentNames, sId]); // Use ID as fallback name
    setNewStudentInput('');
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

  return (
    <div style={{
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0, 0, 0, 0.8)',
      backdropFilter: 'blur(6px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '20px'
    }}>
      <div className="glass-panel" style={{ width: '100%', maxWidth: '650px', padding: '28px', position: 'relative', maxHeight: '90vh', overflowY: 'auto' }}>
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
              <option value="L">L — Limited Students Batch (1–3 students)</option>
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
        <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '14px', marginBottom: '16px' }}>
          <div style={{ fontSize: '0.8rem', fontWeight: 800, color: 'var(--accent-gold)', marginBottom: '10px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span>STUDENTS ASSIGNED TO THIS BATCH ({studentIds.length})</span>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Group Batch Capacity Target: 4–10</span>
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '12px' }}>
            {studentIds.map((sId, idx) => (
              <div
                key={idx}
                style={{
                  background: 'rgba(251, 191, 36, 0.15)',
                  border: '1px solid var(--accent-gold)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '4px 8px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '0.775rem',
                  color: '#fff'
                }}
              >
                <span>{studentNames[idx] || sId}</span>
                <button
                  type="button"
                  onClick={() => handleRemoveStudent(idx)}
                  style={{ background: 'none', border: 'none', color: '#f43f5e', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
                  title="Remove student from this batch"
                >
                  <UserMinus size={13} />
                </button>
              </div>
            ))}
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <input
              type="text"
              placeholder="Enter Student ID to add (e.g. MKS00074)..."
              value={newStudentInput}
              onChange={e => setNewStudentInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); handleAddStudent(); } }}
              style={{ flex: 1, padding: '6px 10px', fontSize: '0.775rem', background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', color: '#fff' }}
            />
            <button
              type="button"
              onClick={handleAddStudent}
              className="btn btn-secondary"
              style={{ padding: '6px 12px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px' }}
            >
              <UserPlus size={14} /> Add Student
            </button>
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
