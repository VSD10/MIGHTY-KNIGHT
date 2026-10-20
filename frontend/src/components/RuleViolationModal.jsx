import React, { useState } from 'react';
import { AlertTriangle, ShieldAlert, X, Check, Info } from 'lucide-react';

export default function RuleViolationModal({
  isOpen,
  onClose,
  violations = [],
  classDetails = {},
  onConfirm
}) {
  const [subtype, setSubtype] = useState('rule_exception'); // compensation | manual | rule_exception
  const [reason, setReason] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleAcknowledgeAndAccept = async () => {
    if (!reason.trim()) {
      setErrorMsg('A valid justification / reason is mandatory when saving a rule exception.');
      return;
    }
    setErrorMsg('');
    setIsSubmitting(true);
    try {
      await onConfirm({
        subtype,
        reason: reason.trim()
      });
      onClose();
    } catch (err) {
      setErrorMsg(err?.message || 'Failed to apply exception');
    } finally {
      setIsSubmitting(false);
    }
  };

  const hardCount = violations.filter(v => v.severity === 'hard').length;
  const softCount = violations.filter(v => v.severity === 'soft').length;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.85)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
        padding: '20px'
      }}
    >
      <div
        className="glass-panel"
        style={{
          width: '100%',
          maxWidth: '680px',
          background: '#0f172a',
          border: '1px solid rgba(239, 68, 68, 0.4)',
          borderRadius: '16px',
          boxShadow: '0 25px 50px -12px rgba(239, 68, 68, 0.25)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          maxHeight: '90vh'
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '20px 24px',
            background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(185, 28, 28, 0.25) 100%)',
            borderBottom: '1px solid rgba(239, 68, 68, 0.3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '40px',
                height: '40px',
                borderRadius: '10px',
                background: 'rgba(239, 68, 68, 0.2)',
                border: '1px solid #ef4444',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#ef4444'
              }}
            >
              <ShieldAlert size={24} />
            </div>
            <div>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#fff', margin: 0 }}>
                This change breaks academy rules
              </h2>
              <div style={{ fontSize: '0.8rem', color: '#fca5a5', marginTop: '2px' }}>
                {hardCount > 0 && <span style={{ marginRight: '8px' }}>● {hardCount} Hard Constraint{hardCount > 1 ? 's' : ''}</span>}
                {softCount > 0 && <span>○ {softCount} Soft Preference{softCount > 1 ? 's' : ''}</span>}
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              padding: '4px'
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Content body */}
        <div style={{ padding: '24px', overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '18px' }}>
          
          {/* Plain Notice (Part D3 non-negotiable notice) */}
          <div
            style={{
              background: 'rgba(245, 158, 11, 0.1)',
              border: '1px solid rgba(245, 158, 11, 0.3)',
              borderRadius: '10px',
              padding: '12px 16px',
              display: 'flex',
              gap: '12px',
              alignItems: 'flex-start'
            }}
          >
            <Info size={18} style={{ color: '#f59e0b', flexShrink: 0, marginTop: '2px' }} />
            <div style={{ fontSize: '0.85rem', color: '#fef3c7', lineHeight: '1.45' }}>
              <strong>Single-Occurrence Notice:</strong> Saving marks this class <strong style={{ color: '#f59e0b' }}>ⓒ</strong>. It applies to <strong>{classDetails.date || 'this date'}, {classDetails.time_slot || ''} with Coach {classDetails.coach_name || ''}</strong> only and will <em>not</em> repeat in later weeks or months.
            </div>
          </div>

          {/* List of Violated Rules */}
          <div>
            <label style={{ fontSize: '0.8rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px', display: 'block' }}>
              Violated Rules & Breakdown
            </label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {violations.map((v, idx) => (
                <div
                  key={idx}
                  style={{
                    background: 'rgba(30, 41, 59, 0.7)',
                    border: v.severity === 'hard' ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid rgba(245, 158, 11, 0.3)',
                    borderRadius: '8px',
                    padding: '12px 14px'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                    <div style={{ fontWeight: 700, fontSize: '0.9rem', color: '#fff' }}>
                      {v.rule_name}
                    </div>
                    <span
                      style={{
                        fontSize: '0.65rem',
                        fontWeight: 800,
                        padding: '2px 8px',
                        borderRadius: '4px',
                        textTransform: 'uppercase',
                        background: v.severity === 'hard' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                        color: v.severity === 'hard' ? '#f87171' : '#fbbf24',
                        border: v.severity === 'hard' ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid rgba(245, 158, 11, 0.4)'
                      }}
                    >
                      {v.severity}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.825rem', color: '#cbd5e1', marginBottom: '4px' }}>
                    {v.reason}
                  </div>
                  {v.exact_values && (
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8', fontStyle: 'italic' }}>
                      Diagnostic values: {v.exact_values}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Subtype Selector */}
          <div>
            <label style={{ fontSize: '0.8rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px', display: 'block' }}>
              Select ⓒ Exception Subtype
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
              {[
                { id: 'rule_exception', label: 'Rule Exception', desc: 'Authorized rule override' },
                { id: 'compensation', label: 'Compensation', desc: 'Make-up for missed session' },
                { id: 'manual', label: 'Manual Change', desc: 'Deliberate operations edit' }
              ].map(opt => (
                <button
                  type="button"
                  key={opt.id}
                  onClick={() => setSubtype(opt.id)}
                  style={{
                    background: subtype === opt.id ? 'rgba(245, 158, 11, 0.2)' : 'rgba(30, 41, 59, 0.5)',
                    border: subtype === opt.id ? '1px solid #f59e0b' : '1px solid #334155',
                    borderRadius: '8px',
                    padding: '10px',
                    cursor: 'pointer',
                    textAlign: 'left'
                  }}
                >
                  <div style={{ fontSize: '0.85rem', fontWeight: 700, color: subtype === opt.id ? '#f59e0b' : '#fff' }}>
                    {opt.label}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: '#94a3b8', marginTop: '2px' }}>
                    {opt.desc}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Reason Field */}
          <div>
            <label style={{ fontSize: '0.8rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px', display: 'block' }}>
              Reason & Administrative Justification <span style={{ color: '#ef4444' }}>*</span>
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Explain why this rule violation is being authorized (e.g. Approved by Head Coach BATHRI for tournament preparation)..."
              rows={3}
              style={{
                width: '100%',
                background: 'rgba(15, 23, 42, 0.8)',
                border: errorMsg ? '1px solid #ef4444' : '1px solid #334155',
                borderRadius: '8px',
                padding: '10px 12px',
                color: '#fff',
                fontSize: '0.85rem',
                resize: 'none'
              }}
            />
            {errorMsg && (
              <div style={{ fontSize: '0.75rem', color: '#f87171', marginTop: '4px' }}>
                {errorMsg}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div
          style={{
            padding: '16px 24px',
            background: 'rgba(15, 23, 42, 0.9)',
            borderTop: '1px solid #1e293b',
            display: 'flex',
            justifyContent: 'flex-end',
            gap: '12px'
          }}
        >
          <button
            onClick={onClose}
            disabled={isSubmitting}
            style={{
              padding: '10px 18px',
              borderRadius: '8px',
              background: 'rgba(51, 65, 85, 0.5)',
              border: '1px solid #475569',
              color: '#cbd5e1',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleAcknowledgeAndAccept}
            disabled={isSubmitting}
            style={{
              padding: '10px 20px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #ef4444 0%, #b91c1c 100%)',
              border: 'none',
              color: '#fff',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              boxShadow: '0 4px 12px rgba(239, 68, 68, 0.4)'
            }}
          >
            <Check size={18} /> {isSubmitting ? 'Saving...' : 'Acknowledge & Accept'}
          </button>
        </div>
      </div>
    </div>
  );
}
