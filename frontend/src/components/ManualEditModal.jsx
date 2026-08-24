import React, { useState, useEffect } from 'react';
import { AlertCircle, CheckCircle, X, ShieldAlert } from 'lucide-react';
import { validateManualOverride, applyManualEdit } from '../services/api';

export default function ManualEditModal({ isOpen, onClose, targetClass, scheduleId, onSaveSuccess }) {
  if (!isOpen || !targetClass) return null;

  const [coachName, setCoachName] = useState(targetClass.coach_name || '');
  const [studentLevel, setStudentLevel] = useState(targetClass.student_level || 'Basic 1');
  const [batchType, setBatchType] = useState(targetClass.batch_type || 'G');
  const [timeSlot, setTimeSlot] = useState(targetClass.time_slot || '');
  const [dateStr, setDateStr] = useState(targetClass.date || '');
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
    'Intermediate'
  ];

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
        student_ids: targetClass.student_ids
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
        student_ids: targetClass.student_ids
      });
      if (onSaveSuccess) onSaveSuccess();
      onClose();
    } catch (err) {
      alert('Failed to save manual edit: ' + (err.response?.data?.detail || err.message));
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
      <div className="glass-panel" style={{ width: '100%', maxWidth: '600px', padding: '28px', position: 'relative', maxHeight: '90vh', overflowY: 'auto' }}>
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
          Manually modify class coach, student level, batch type, date, or time slot. The engine checks for rule violations before saving.
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
              <option value="G">G — Group Batch (8–10 students)</option>
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

        {/* Current Students in Batch info */}
        <div style={{ background: 'var(--bg-secondary)', padding: '12px 14px', borderRadius: 'var(--radius-md)', marginBottom: '20px' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent-gold)' }}>
            STUDENTS IN THIS CLASS ({targetClass.student_names ? targetClass.student_names.length : 0}):
          </span>
          <p style={{ fontSize: '0.8rem', color: '#fff', marginTop: '4px' }}>
            {targetClass.students_formatted}
          </p>
        </div>

        {/* Live Rule Violations Warning Panel */}
        {validated && (
          <div style={{ marginBottom: '20px' }}>
            {warnings.length > 0 ? (
              <div style={{ background: 'var(--status-danger-bg)', border: '1px solid #ef4444', padding: '14px', borderRadius: 'var(--radius-md)' }}>
                <p style={{ fontWeight: 700, color: '#ef4444', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <AlertCircle size={16} /> Rule Violation Warnings ({warnings.length})
                </p>
                {warnings.map((w, idx) => (
                  <p key={idx} style={{ fontSize: '0.775rem', color: '#fca5a5', marginTop: '4px' }}>• {w}</p>
                ))}
              </div>
            ) : (
              <div style={{ background: 'var(--status-success-bg)', border: '1px solid #10b981', padding: '14px', borderRadius: 'var(--radius-md)', color: '#10b981', fontSize: '0.85rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
                <CheckCircle size={16} /> No Rule Violations Detected. Safe to Save!
              </div>
            )}
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
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
  );
}
