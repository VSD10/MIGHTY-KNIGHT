import React, { useState, useEffect, useCallback } from 'react';
import {
  Trophy, Shield, ChevronUp, ChevronDown, ArrowUp, ArrowDown,
  RefreshCw, CheckCircle2, AlertCircle, Trash2, Plus, X, UserPlus
} from 'lucide-react';
import {
  getCoachPriorityMatrix,
  moveCoachPriority,
  deleteCoachPriority,
  addCoachToPriority,
  getMasterData
} from '../services/api';

const OFFICIAL_8_LEVELS = [
  'Basic 1',
  'Basic 2',
  'Beginner 1',
  'Beginner 2',
  'Early Intermediate 1',
  'Early Intermediate 2',
  'Intermediate 1',
  'Intermediate 2'
];

export default function TrainerPriorityMatrix({ onPriorityChanged }) {
  const [matrix, setMatrix] = useState({});
  const [loading, setLoading] = useState(true);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [busyKeys, setBusyKeys] = useState({});
  const [toast, setToast] = useState(null);
  const [allActiveCoaches, setAllActiveCoaches] = useState([]);
  const [addingLevel, setAddingLevel] = useState(null);
  const [selectedCoachToAdd, setSelectedCoachToAdd] = useState('');

  const fetchMatrix = useCallback(async () => {
    try {
      setLoading(true);
      const [matrixRes, masterRes] = await Promise.allSettled([
        getCoachPriorityMatrix(),
        getMasterData()
      ]);

      const coachSet = new Set();

      if (matrixRes.status === 'fulfilled' && matrixRes.value && matrixRes.value.matrix) {
        setMatrix(matrixRes.value.matrix);
        Object.values(matrixRes.value.matrix).forEach(list => {
          (list || []).forEach(c => {
            if (c.coach_name) coachSet.add(c.coach_name.trim().toUpperCase());
          });
        });
      }

      if (masterRes.status === 'fulfilled' && masterRes.value && masterRes.value.coaches) {
        (masterRes.value.coaches || []).forEach(c => {
          if (c.status !== 'INACTIVE' && c.coach_name) {
            coachSet.add(c.coach_name.trim().toUpperCase());
          }
        });
      }

      // Default fallback if master data empty
      ['ATHARVA', 'BATHRI', 'DHAANUSH', 'GURU', 'MUKUNDH', 'RITVIK', 'SHARVESH', 'VARSHINI'].forEach(c => {
        coachSet.add(c);
      });

      setAllActiveCoaches(Array.from(coachSet).sort());
    } catch (err) {
      console.error('Failed to load Coach Priority Matrix:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMatrix();
  }, [fetchMatrix]);

  const showToastMessage = (type, message) => {
    setToast({ type, message });
    setTimeout(() => setToast(null), 3500);
  };

  const handleMove = async (level, coachName, direction) => {
    const key = `move_${level}_${coachName}`;
    if (busyKeys[key]) return;

    // Optimistic Local Update
    const currentList = [...(matrix[level] || [])];
    const currIdx = currentList.findIndex(c => c.coach_name.toUpperCase() === coachName.toUpperCase());
    if (currIdx === -1) return;

    const targetIdx = direction === 'up' ? currIdx - 1 : currIdx + 1;
    if (targetIdx < 0 || targetIdx >= currentList.length) return;

    // Swap items locally
    const updatedList = [...currentList];
    const temp = updatedList[currIdx];
    updatedList[currIdx] = updatedList[targetIdx];
    updatedList[targetIdx] = temp;

    // Re-index priorities 1..N
    const reindexed = updatedList.map((item, idx) => ({
      ...item,
      priority: idx + 1,
      is_primary: idx === 0
    }));

    setMatrix(prev => ({
      ...prev,
      [level]: reindexed
    }));

    setBusyKeys(prev => ({ ...prev, [key]: true }));

    try {
      const res = await moveCoachPriority(level, coachName, direction);
      if (res && res.matrix) {
        setMatrix(res.matrix);
      }
      const movedItem = reindexed[targetIdx];
      const rankLabel = movedItem.is_primary ? 'Primary' : `Priority #${movedItem.priority}`;
      showToastMessage('success', `${level}: Coach ${coachName} moved to ${rankLabel}`);

      if (onPriorityChanged) {
        onPriorityChanged();
      }
    } catch (err) {
      console.error('Failed to update coach priority:', err);
      // Rollback on failure
      setMatrix(prev => ({ ...prev, [level]: currentList }));
      showToastMessage('error', `Failed to move ${coachName}: ${err.response?.data?.detail || err.message}`);
    } finally {
      setBusyKeys(prev => {
        const next = { ...prev };
        delete next[key];
        return next;
      });
    }
  };

  const handleDeleteCoach = async (level, coachName) => {
    const key = `del_${level}_${coachName}`;
    if (busyKeys[key]) return;

    const currentList = [...(matrix[level] || [])];
    const updatedList = currentList.filter(c => c.coach_name.toUpperCase() !== coachName.toUpperCase());
    const reindexed = updatedList.map((item, idx) => ({
      ...item,
      priority: idx + 1,
      is_primary: idx === 0
    }));

    // Optimistic update
    setMatrix(prev => ({
      ...prev,
      [level]: reindexed
    }));

    setBusyKeys(prev => ({ ...prev, [key]: true }));

    try {
      const res = await deleteCoachPriority(level, coachName);
      if (res && res.matrix) {
        setMatrix(res.matrix);
      }
      showToastMessage('success', `Coach ${coachName} removed from ${level} priority list`);

      if (onPriorityChanged) {
        onPriorityChanged();
      }
    } catch (err) {
      console.error('Failed to remove coach from level priority:', err);
      // Rollback on failure
      setMatrix(prev => ({ ...prev, [level]: currentList }));
      showToastMessage('error', `Failed to remove ${coachName}: ${err.response?.data?.detail || err.message}`);
    } finally {
      setBusyKeys(prev => {
        const next = { ...prev };
        delete next[key];
        return next;
      });
    }
  };

  const handleAddCoach = async (level) => {
    if (!selectedCoachToAdd) return;
    const coachName = selectedCoachToAdd.trim().toUpperCase();
    const key = `add_${level}_${coachName}`;
    if (busyKeys[key]) return;

    const currentList = matrix[level] || [];
    if (currentList.some(c => c.coach_name.toUpperCase() === coachName)) {
      showToastMessage('error', `Coach ${coachName} is already assigned to ${level}`);
      return;
    }

    setBusyKeys(prev => ({ ...prev, [key]: true }));

    try {
      const res = await addCoachToPriority(level, coachName);
      if (res && res.matrix) {
        setMatrix(res.matrix);
      } else {
        await fetchMatrix();
      }
      showToastMessage('success', `Coach ${coachName} added to ${level}`);
      setAddingLevel(null);
      setSelectedCoachToAdd('');

      if (onPriorityChanged) {
        onPriorityChanged();
      }
    } catch (err) {
      console.error('Failed to add coach to level priority:', err);
      showToastMessage('error', `Failed to add ${coachName}: ${err.response?.data?.detail || err.message}`);
    } finally {
      setBusyKeys(prev => {
        const next = { ...prev };
        delete next[key];
        return next;
      });
    }
  };

  return (
    <div
      className="glass-panel"
      style={{
        padding: '24px',
        marginBottom: '28px',
        background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(20, 27, 45, 0.95) 100%)',
        border: '1px solid rgba(234, 179, 8, 0.25)',
        borderRadius: '16px',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.45)'
      }}
    >
      {/* Toast Feedback Banner */}
      {toast && (
        <div
          style={{
            marginBottom: '16px',
            padding: '10px 16px',
            borderRadius: 'var(--radius-md)',
            background: toast.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
            border: `1.5px solid ${toast.type === 'success' ? '#10b981' : '#ef4444'}`,
            color: toast.type === 'success' ? '#34d399' : '#f87171',
            fontSize: '0.825rem',
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          {toast.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
          <span>{toast.message}</span>
        </div>
      )}

      {/* Header Bar matching Reference Screenshot */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '16px',
          marginBottom: isCollapsed ? '0px' : '22px'
        }}
      >
        {/* Left: Icon, Title & Badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              border: '1px solid rgba(234, 179, 8, 0.5)',
              background: 'rgba(234, 179, 8, 0.12)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fde047',
              boxShadow: '0 0 12px rgba(234, 179, 8, 0.2)'
            }}
          >
            <Trophy size={22} style={{ color: '#fde047' }} />
          </div>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
              <h3
                style={{
                  fontSize: '1.2rem',
                  fontWeight: 800,
                  color: '#ffffff',
                  letterSpacing: '0.3px',
                  margin: 0
                }}
              >
                Trainer Qualification & Priority Matrix
              </h3>
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '3px 10px',
                  borderRadius: '9999px',
                  border: '1px solid rgba(234, 179, 8, 0.5)',
                  background: 'rgba(234, 179, 8, 0.1)',
                  color: '#fde047',
                  fontSize: '0.675rem',
                  fontWeight: 800,
                  letterSpacing: '0.5px'
                }}
              >
                <Shield size={12} style={{ color: '#fde047' }} /> SINGLE SOURCE OF TRUTH
              </span>
            </div>
            <p
              style={{
                fontSize: '0.8rem',
                color: '#94a3b8',
                marginTop: '4px',
                marginBottom: 0
              }}
            >
              Operational priority matrix actively governing scheduler engine allocations • 8 Academy Levels
            </p>
          </div>
        </div>

        {/* Right: Expand / Collapse Button & Refresh */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={fetchMatrix}
            disabled={loading}
            className="btn btn-secondary"
            style={{
              padding: '6px 12px',
              borderRadius: '20px',
              background: 'rgba(30, 41, 59, 0.6)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              color: '#cbd5e1',
              fontSize: '0.78rem',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              cursor: 'pointer'
            }}
            title="Refresh authoritative matrix from database"
          >
            <RefreshCw size={13} className={loading ? 'spin' : ''} />
            Sync
          </button>

          <button
            onClick={() => setIsCollapsed(prev => !prev)}
            className="btn btn-secondary"
            style={{
              padding: '6px 14px',
              borderRadius: '20px',
              background: 'rgba(30, 41, 59, 0.8)',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              color: '#ffffff',
              fontSize: '0.8rem',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              cursor: 'pointer',
              transition: 'all 0.2s ease'
            }}
          >
            {isCollapsed ? <ChevronDown size={15} /> : <ChevronUp size={15} />}
            {isCollapsed ? 'Expand Matrix' : 'Collapse Matrix'}
          </button>
        </div>
      </div>

      {/* 8 Level Cards Grid */}
      {!isCollapsed && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '16px',
            alignItems: 'stretch'
          }}
        >
          {OFFICIAL_8_LEVELS.map(lvl => {
            const coaches = matrix[lvl] || [];
            const qualCount = coaches.length;
            const assignedCoachNames = new Set(coaches.map(c => c.coach_name.toUpperCase()));
            const availableCoaches = allActiveCoaches.filter(c => !assignedCoachNames.has(c));

            return (
              <div
                key={lvl}
                style={{
                  background: 'rgba(15, 23, 42, 0.7)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: '12px',
                  padding: '16px',
                  display: 'flex',
                  flexDirection: 'column',
                  transition: 'border-color 0.2s ease',
                  boxShadow: '0 4px 16px rgba(0, 0, 0, 0.25)'
                }}
              >
                {/* Level Card Header */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginBottom: '14px',
                    paddingBottom: '10px',
                    borderBottom: '1px solid rgba(255, 255, 255, 0.06)'
                  }}
                >
                  <span
                    style={{
                      fontSize: '0.95rem',
                      fontWeight: 800,
                      color: '#facc15',
                      letterSpacing: '0.3px'
                    }}
                  >
                    {lvl}
                  </span>

                  <span
                    style={{
                      fontSize: '0.68rem',
                      fontWeight: 800,
                      color: '#fde047',
                      background: 'rgba(234, 179, 8, 0.08)',
                      border: '1px solid rgba(234, 179, 8, 0.4)',
                      borderRadius: '9999px',
                      padding: '2px 8px',
                      letterSpacing: '0.5px'
                    }}
                  >
                    {qualCount} QUALIFIED
                  </span>
                </div>

                {/* Ordered Coaches List */}
                {coaches.length === 0 ? (
                  <div
                    style={{
                      padding: '20px 10px',
                      textAlign: 'center',
                      color: 'var(--text-muted)',
                      fontSize: '0.78rem',
                      fontStyle: 'italic'
                    }}
                  >
                    No coaches qualified for this level
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', flex: 1 }}>
                    {coaches.map((c, idx) => {
                      const isFirst = idx === 0;
                      const isLast = idx === coaches.length - 1;
                      const isPrimary = c.is_primary || isFirst;
                      const isBusy = Boolean(
                        busyKeys[`move_${lvl}_${c.coach_name}`] ||
                        busyKeys[`del_${lvl}_${c.coach_name}`]
                      );

                      return (
                        <div
                          key={c.coach_name}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            padding: '7px 10px',
                            borderRadius: '8px',
                            background: isPrimary ? 'rgba(234, 179, 8, 0.04)' : 'rgba(255, 255, 255, 0.03)',
                            border: isPrimary ? '1px solid rgba(234, 179, 8, 0.2)' : '1px solid rgba(255, 255, 255, 0.05)',
                            transition: 'all 0.15s ease'
                          }}
                        >
                          {/* Left: Numbered Circle Badge & Coach Name */}
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0, flex: 1 }}>
                            <div
                              style={{
                                width: '22px',
                                height: '22px',
                                borderRadius: '50%',
                                display: 'flex',
                                alignItems: 'center',
                                justifyCenter: 'center',
                                fontSize: '0.75rem',
                                fontWeight: isPrimary ? 900 : 700,
                                background: isPrimary ? '#facc15' : 'rgba(30, 41, 59, 0.9)',
                                color: isPrimary ? '#000000' : '#ffffff',
                                border: isPrimary ? 'none' : '1px solid rgba(255, 255, 255, 0.15)',
                                flexShrink: 0
                              }}
                            >
                              {c.priority || (idx + 1)}
                            </div>

                            <span
                              style={{
                                fontSize: '0.8rem',
                                fontWeight: 800,
                                color: '#ffffff',
                                letterSpacing: '0.5px',
                                textTransform: 'uppercase',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap'
                              }}
                              title={c.coach_name}
                            >
                              {c.coach_name}
                            </span>
                          </div>

                          {/* Right: Label & Controls (Up, Down, Delete) */}
                          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexShrink: 0 }}>
                            <span
                              style={{
                                fontSize: '0.72rem',
                                fontWeight: isPrimary ? 800 : 500,
                                color: isPrimary ? '#facc15' : '#94a3b8',
                                marginRight: '4px',
                                minWidth: '50px',
                                textAlign: 'right'
                              }}
                            >
                              {isPrimary ? 'Primary' : `Priority ${c.priority || (idx + 1)}`}
                            </span>

                            {/* Up Button */}
                            <button
                              disabled={isFirst || isBusy}
                              onClick={() => handleMove(lvl, c.coach_name, 'up')}
                              title={isFirst ? 'Already at top priority' : `Move ${c.coach_name} up`}
                              style={{
                                width: '22px',
                                height: '22px',
                                borderRadius: '4px',
                                background: 'rgba(255, 255, 255, 0.06)',
                                border: '1px solid rgba(255, 255, 255, 0.12)',
                                color: '#ffffff',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                cursor: isFirst || isBusy ? 'not-allowed' : 'pointer',
                                opacity: isFirst || isBusy ? 0.3 : 1,
                                padding: 0,
                                transition: 'all 0.15s ease'
                              }}
                            >
                              <ArrowUp size={12} />
                            </button>

                            {/* Down Button */}
                            <button
                              disabled={isLast || isBusy}
                              onClick={() => handleMove(lvl, c.coach_name, 'down')}
                              title={isLast ? 'Already at lowest priority' : `Move ${c.coach_name} down`}
                              style={{
                                width: '22px',
                                height: '22px',
                                borderRadius: '4px',
                                background: 'rgba(255, 255, 255, 0.06)',
                                border: '1px solid rgba(255, 255, 255, 0.12)',
                                color: '#ffffff',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                cursor: isLast || isBusy ? 'not-allowed' : 'pointer',
                                opacity: isLast || isBusy ? 0.3 : 1,
                                padding: 0,
                                transition: 'all 0.15s ease'
                              }}
                            >
                              <ArrowDown size={12} />
                            </button>

                            {/* Delete/Remove from Level Button */}
                            <button
                              disabled={isBusy}
                              onClick={() => handleDeleteCoach(lvl, c.coach_name)}
                              title={`Remove ${c.coach_name} from ${lvl}`}
                              style={{
                                width: '22px',
                                height: '22px',
                                borderRadius: '4px',
                                background: 'rgba(239, 68, 68, 0.1)',
                                border: '1px solid rgba(239, 68, 68, 0.3)',
                                color: '#f87171',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                cursor: isBusy ? 'not-allowed' : 'pointer',
                                opacity: isBusy ? 0.3 : 1,
                                padding: 0,
                                transition: 'all 0.15s ease'
                              }}
                              onMouseEnter={e => { if (!isBusy) e.currentTarget.style.background = 'rgba(239, 68, 68, 0.25)'; }}
                              onMouseLeave={e => { if (!isBusy) e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)'; }}
                            >
                              <Trash2 size={12} />
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Add Coach Control */}
                <div style={{ marginTop: '12px', borderTop: '1px solid rgba(255, 255, 255, 0.06)', paddingTop: '10px' }}>
                  {addingLevel === lvl ? (
                    <div
                      style={{
                        padding: '8px 10px',
                        borderRadius: '8px',
                        background: 'rgba(30, 41, 59, 0.9)',
                        border: '1px solid rgba(234, 179, 8, 0.4)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '8px'
                      }}
                    >
                      <div style={{ fontSize: '0.72rem', color: '#fde047', fontWeight: 700 }}>
                        Add Eligible Coach to {lvl}:
                      </div>
                      <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                        <select
                          value={selectedCoachToAdd}
                          onChange={e => setSelectedCoachToAdd(e.target.value)}
                          style={{
                            flex: 1,
                            background: '#0f172a',
                            color: '#ffffff',
                            border: '1px solid rgba(255, 255, 255, 0.2)',
                            borderRadius: '6px',
                            padding: '4px 8px',
                            fontSize: '0.75rem'
                          }}
                        >
                          <option value="">-- Select Coach --</option>
                          {availableCoaches.map(name => (
                            <option key={name} value={name}>{name}</option>
                          ))}
                        </select>

                        <button
                          disabled={!selectedCoachToAdd || Boolean(busyKeys[`add_${lvl}_${selectedCoachToAdd}`])}
                          onClick={() => handleAddCoach(lvl)}
                          style={{
                            padding: '4px 10px',
                            borderRadius: '6px',
                            background: '#facc15',
                            color: '#000000',
                            fontWeight: 800,
                            fontSize: '0.75rem',
                            border: 'none',
                            cursor: (!selectedCoachToAdd || Boolean(busyKeys[`add_${lvl}_${selectedCoachToAdd}`])) ? 'not-allowed' : 'pointer',
                            opacity: (!selectedCoachToAdd || Boolean(busyKeys[`add_${lvl}_${selectedCoachToAdd}`])) ? 0.4 : 1
                          }}
                        >
                          Add
                        </button>

                        <button
                          onClick={() => { setAddingLevel(null); setSelectedCoachToAdd(''); }}
                          style={{
                            padding: '4px 6px',
                            borderRadius: '6px',
                            background: 'rgba(255, 255, 255, 0.08)',
                            color: '#94a3b8',
                            border: '1px solid rgba(255, 255, 255, 0.1)',
                            cursor: 'pointer'
                          }}
                        >
                          <X size={13} />
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => {
                        setAddingLevel(lvl);
                        setSelectedCoachToAdd('');
                      }}
                      disabled={availableCoaches.length === 0}
                      style={{
                        width: '100%',
                        padding: '6px 10px',
                        borderRadius: '8px',
                        background: 'rgba(255, 255, 255, 0.03)',
                        border: '1px dashed rgba(234, 179, 8, 0.3)',
                        color: availableCoaches.length === 0 ? '#64748b' : '#fde047',
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '6px',
                        cursor: availableCoaches.length === 0 ? 'not-allowed' : 'pointer',
                        transition: 'all 0.2s ease'
                      }}
                      onMouseEnter={e => {
                        if (availableCoaches.length > 0) {
                          e.currentTarget.style.background = 'rgba(234, 179, 8, 0.08)';
                          e.currentTarget.style.borderColor = 'rgba(234, 179, 8, 0.6)';
                        }
                      }}
                      onMouseLeave={e => {
                        if (availableCoaches.length > 0) {
                          e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)';
                          e.currentTarget.style.borderColor = 'rgba(234, 179, 8, 0.3)';
                        }
                      }}
                    >
                      <Plus size={13} />
                      {availableCoaches.length === 0 ? 'All Coaches Assigned' : `+ Add Coach to ${lvl}`}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
