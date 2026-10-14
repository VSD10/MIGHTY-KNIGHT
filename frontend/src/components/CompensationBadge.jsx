import React, { useState, useRef, useEffect } from 'react';
import { ShieldAlert, RotateCcw, Clock, User, AlertTriangle, CheckCircle, Info } from 'lucide-react';
import { revertException } from '../services/api';

export default function CompensationBadge({
  cls,
  month = '2026-10',
  onRevertSuccess,
  size = 'md' // 'sm' | 'md'
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [reverting, setReverting] = useState(false);
  const [revertError, setRevertError] = useState('');
  const popoverRef = useRef(null);

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (popoverRef.current && !popoverRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  if (!cls?.is_compensation && !cls?.has_compensation && !cls?.exception_metadata) {
    return null;
  }

  const meta = cls.exception_metadata || {};
  const subtype = meta.subtype || 'manual';
  const author = meta.author || 'Admin';
  const createdAt = meta.created_at || 'Recently';
  const reason = meta.reason || 'Manual single-occurrence adjustment';
  const violatedRules = meta.violated_rules || [];
  const exceptionId = meta.exception_id;

  const handleRevert = async (e) => {
    e.stopPropagation();
    if (!exceptionId) {
      alert("No exception record ID available to revert.");
      return;
    }
    if (!window.confirm("Are you sure you want to revert this single-occurrence exception (ⓒ) and restore the baseline class?")) {
      return;
    }

    setReverting(true);
    setRevertError('');
    try {
      await revertException(exceptionId, month);
      setIsOpen(false);
      if (onRevertSuccess) {
        onRevertSuccess();
      }
    } catch (err) {
      setRevertError(err?.response?.data?.detail || err.message || "Failed to revert exception");
    } finally {
      setReverting(false);
    }
  };

  const getSubtypeLabel = (sub) => {
    if (sub === 'compensation') return 'Compensation Class';
    if (sub === 'rule_exception') return 'Rule Exception';
    return 'Manual Change';
  };

  const badgeFontSize = size === 'sm' ? '0.75rem' : '0.85rem';
  const badgePadding = size === 'sm' ? '1px 5px' : '2px 7px';

  return (
    <div style={{ position: 'relative', display: 'inline-block' }} ref={popoverRef}>
      {/* Interactive Circled ⓒ Badge */}
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setIsOpen(!isOpen);
        }}
        title="Single-occurrence manual exception (ⓒ) - Click for audit & revert options"
        style={{
          background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.25) 0%, rgba(217, 119, 6, 0.35) 100%)',
          color: '#fbbf24',
          border: '1px solid rgba(245, 158, 11, 0.6)',
          borderRadius: '9999px',
          fontWeight: 900,
          fontSize: badgeFontSize,
          padding: badgePadding,
          cursor: 'pointer',
          display: 'inline-flex',
          alignItems: 'center',
          gap: '3px',
          boxShadow: '0 0 10px rgba(245, 158, 11, 0.3)',
          transition: 'all 0.15s ease',
          lineHeight: 1
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'scale(1.08)';
          e.currentTarget.style.boxShadow = '0 0 14px rgba(245, 158, 11, 0.55)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'scale(1)';
          e.currentTarget.style.boxShadow = '0 0 10px rgba(245, 158, 11, 0.3)';
        }}
      >
        <span>ⓒ</span>
        {size !== 'sm' && <span style={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Exception</span>}
      </button>

      {/* Popover Card */}
      {isOpen && (
        <div
          onClick={(e) => e.stopPropagation()}
          className="glass-panel"
          style={{
            position: 'absolute',
            top: 'calc(100% + 8px)',
            left: 0,
            zIndex: 9999,
            width: '320px',
            background: '#090d16',
            border: '1px solid rgba(245, 158, 11, 0.5)',
            borderRadius: '12px',
            boxShadow: '0 20px 40px rgba(0, 0, 0, 0.75)',
            padding: '16px',
            animation: 'fadeIn 0.15s ease-out'
          }}
        >
          {/* Header */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '1.1rem', fontWeight: 900, color: '#fbbf24' }}>ⓒ</span>
              <span style={{ fontSize: '0.85rem', fontWeight: 800, color: '#fff' }}>Single-Occurrence</span>
            </div>
            <span
              style={{
                fontSize: '0.625rem',
                fontWeight: 800,
                padding: '2px 6px',
                borderRadius: '6px',
                background: subtype === 'rule_exception' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                color: subtype === 'rule_exception' ? '#f87171' : '#fbbf24',
                border: `1px solid ${subtype === 'rule_exception' ? 'rgba(239, 68, 68, 0.4)' : 'rgba(245, 158, 11, 0.4)'}`
              }}
            >
              {getSubtypeLabel(subtype)}
            </span>
          </div>

          {/* Scope notice banner */}
          <div
            style={{
              fontSize: '0.7rem',
              color: 'var(--text-muted)',
              background: 'rgba(255, 255, 255, 0.03)',
              padding: '8px',
              borderRadius: '6px',
              marginBottom: '12px',
              lineHeight: 1.4
            }}
          >
            ℹ️ Temporary manual override. Never repeats next week and does not alter the Absolute Schedule baseline.
          </div>

          {/* Details */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.75rem', marginBottom: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Author:</span>
              <span style={{ fontWeight: 700, color: '#fff' }}>{author}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Recorded At:</span>
              <span style={{ color: '#94a3b8' }}>{createdAt}</span>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', display: 'block', marginBottom: '3px' }}>Reason:</span>
              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '6px 8px', borderRadius: '4px', color: '#e2e8f0', fontStyle: 'italic', wordBreak: 'break-word' }}>
                "{reason}"
              </div>
            </div>

            {/* Violated Rules List if any */}
            {violatedRules && violatedRules.length > 0 && (
              <div style={{ marginTop: '4px' }}>
                <span style={{ color: '#f87171', fontWeight: 700, fontSize: '0.7rem', display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '4px' }}>
                  <AlertTriangle size={12} /> Violated Rules ({violatedRules.length}):
                </span>
                <div style={{ maxHeight: '90px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  {violatedRules.map((v, i) => (
                    <div key={i} style={{ fontSize: '0.675rem', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.25)', padding: '4px 6px', borderRadius: '4px', color: '#fca5a5' }}>
                      <strong>{v.rule}:</strong> {v.message}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {revertError && (
            <div style={{ fontSize: '0.7rem', color: '#f87171', background: 'rgba(239,68,68,0.15)', padding: '6px', borderRadius: '4px', marginBottom: '8px' }}>
              {revertError}
            </div>
          )}

          {/* Revert Action Button */}
          {exceptionId && (
            <button
              type="button"
              onClick={handleRevert}
              disabled={reverting}
              className="btn btn-secondary"
              style={{
                width: '100%',
                padding: '7px 10px',
                fontSize: '0.75rem',
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                borderColor: 'rgba(244, 63, 94, 0.4)',
                color: '#f43f5e'
              }}
            >
              <RotateCcw size={13} /> {reverting ? 'Reverting Exception...' : 'Revert ⓒ (Restore Baseline)'}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
