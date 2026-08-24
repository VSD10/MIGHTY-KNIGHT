import React, { useState } from 'react';
import { AlertCircle, CheckCircle, X, ShieldAlert } from 'lucide-react';
import { validateManualOverride } from '../services/api';

export default function ManualEditModal({ isOpen, onClose, targetClass, scheduleId, onSaveSuccess }) {
  if (!isOpen || !targetClass) return null;

  const [coachName, setCoachName] = useState(targetClass.coach_name || '');
  const [timeSlot, setTimeSlot] = useState(targetClass.time_slot || '');
  const [dateStr, setDateStr] = useState(targetClass.date || '');
  const [warnings, setWarnings] = useState([]);
  const [validating, setValidating] = useState(false);
  const [validated, setValidated] = useState(false);

  const handleValidate = async () => {
    setValidating(true);
    setWarnings([]);
    try {
      const res = await validateManualOverride(scheduleId, {
        class_id: targetClass.class_id,
        coach_name: coachName,
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

  const handleSave = () => {
    alert(`Manual edit applied for class ${targetClass.class_id}. Warnings acknowledged: ${warnings.length}`);
    if (onSaveSuccess) onSaveSuccess();
    onClose();
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
      <div className="glass-panel" style={{ width: '100%', maxWidth: '550px', padding: '28px', position: 'relative' }}>
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
          Manually edit class coach or slot. The engine will warn on rule violations (coach overlap, daily caps, Sunday restrictions) before saving.
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginBottom: '20px' }}>
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

          <div>
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
            <button onClick={handleSave} className="btn btn-primary">
              Acknowledge & Save Override
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
