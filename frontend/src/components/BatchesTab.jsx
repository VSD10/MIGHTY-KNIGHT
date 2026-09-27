import React, { useState, useMemo } from 'react';
import { createPortal } from 'react-dom';
import {
  Layers, Users, Clock, Plus, Edit2, Trash2,
  Search, Check, AlertCircle, X, Save, UserCheck, Shield,
  ChevronDown, ChevronUp, UserPlus, Filter
} from 'lucide-react';

export default function BatchesTab({
  batches = [],
  allStudents = [],
  allCoaches = [],
  onSaveBatch,
  onDeleteBatch,
  loading = false
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('ALL'); // 'ALL' | 'G' | 'L' | 'I'
  const [levelFilter, setLevelFilter] = useState('ALL');
  const [trainerFilter, setTrainerFilter] = useState('ALL');
  const [expandedBatchId, setExpandedBatchId] = useState(null);

  // Modal State
  const [editingBatch, setEditingBatch] = useState(null);
  const [studentToAdd, setStudentToAdd] = useState({ batchId: null, studentId: '' });

  const uniqueTrainersList = useMemo(() => {
    const set = new Set();
    batches.forEach(b => {
      if (b.fixed_trainer && b.fixed_trainer !== 'Unassigned') set.add(b.fixed_trainer);
    });
    allCoaches.forEach(c => {
      if (c.coach_name) set.add(c.coach_name);
    });
    return Array.from(set).sort();
  }, [batches, allCoaches]);

  const uniqueLevelsList = useMemo(() => {
    const set = new Set();
    batches.forEach(b => {
      if (b.level) set.add(b.level);
    });
    return Array.from(set).sort();
  }, [batches]);

  // Filtering Logic
  const filteredBatches = useMemo(() => {
    return batches.filter(b => {
      if (typeFilter !== 'ALL' && b.batch_type !== typeFilter) return false;
      if (levelFilter !== 'ALL' && b.level !== levelFilter) return false;
      if (trainerFilter !== 'ALL' && b.fixed_trainer !== trainerFilter) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesName = (b.batch_name || '').toLowerCase().includes(q);
        const matchesId = (b.batch_id || '').toLowerCase().includes(q);
        const matchesTrainer = (b.fixed_trainer || '').toLowerCase().includes(q);
        const matchesLevel = (b.level || '').toLowerCase().includes(q);
        const matchesTiming = (b.schedule_timings || '').toLowerCase().includes(q);
        const matchesStudent = (b.students || []).some(s =>
          (s.student_name || '').toLowerCase().includes(q) ||
          (s.student_id || '').toLowerCase().includes(q)
        );
        return matchesName || matchesId || matchesTrainer || matchesLevel || matchesTiming || matchesStudent;
      }
      return true;
    });
  }, [batches, typeFilter, levelFilter, trainerFilter, searchQuery]);

  // Quick inline remove student from batch
  const handleRemoveStudentFromBatch = (batch, studentIdToRemove) => {
    const updatedStudents = (batch.students || []).filter(s => s.student_id !== studentIdToRemove);
    const updatedIds = (batch.student_ids || []).filter(id => id !== studentIdToRemove);
    const updatedBatch = {
      ...batch,
      students: updatedStudents,
      student_ids: updatedIds,
      student_count: updatedStudents.length
    };
    onSaveBatch(updatedBatch);
  };

  // Quick inline add student to batch
  const handleAddStudentToBatch = (batch, studentIdToAdd) => {
    if (!studentIdToAdd) return;
    const studentObj = allStudents.find(s => s.student_id === studentIdToAdd);
    const newStudent = studentObj
      ? {
          student_id: studentObj.student_id,
          student_name: studentObj.student_name,
          student_level: studentObj.student_level,
          mkca_rating: studentObj.mkca_rating || '-',
          fixed_trainer: batch.fixed_trainer
        }
      : {
          student_id: studentIdToAdd,
          student_name: studentIdToAdd,
          student_level: batch.level,
          mkca_rating: '-',
          fixed_trainer: batch.fixed_trainer
        };

    const currentStudents = batch.students || [];
    if (currentStudents.some(s => s.student_id === studentIdToAdd)) {
      alert('Student is already enrolled in this batch!');
      return;
    }

    const updatedStudents = [...currentStudents, newStudent];
    const updatedIds = Array.from(new Set([...(batch.student_ids || []), studentIdToAdd]));
    const updatedBatch = {
      ...batch,
      students: updatedStudents,
      student_ids: updatedIds,
      student_count: updatedStudents.length
    };
    onSaveBatch(updatedBatch);
    setStudentToAdd({ batchId: null, studentId: '' });
  };

  // Helper color tag for batch types
  const getBatchTypeBadge = (type) => {
    switch (type) {
      case 'G':
        return { label: 'Group (G)', bg: 'rgba(59, 130, 246, 0.2)', color: '#60a5fa', border: '#3b82f6' };
      case 'L':
        return { label: 'Limited (L)', bg: 'rgba(168, 85, 247, 0.2)', color: '#c084fc', border: '#a855f7' };
      case 'I':
        return { label: 'Individual (I)', bg: 'rgba(234, 179, 8, 0.2)', color: '#facc15', border: '#eab308' };
      default:
        return { label: type, bg: 'rgba(255,255,255,0.1)', color: '#fff', border: 'var(--border-color)' };
    }
  };

  return (
    <div>
      {/* SEARCH, FILTERS & ACTION ROW */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px', marginBottom: '18px', background: 'rgba(255,255,255,0.02)', padding: '14px', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
        {/* Search Bar */}
        <div style={{ position: 'relative', flex: 1, minWidth: '240px' }}>
          <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input
            type="text"
            placeholder="Search batch name, student, fixed trainer, or timings..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '9px 12px 9px 36px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              color: '#fff',
              fontSize: '0.85rem'
            }}
          />
        </div>

        {/* Filter Pills & Dropdowns */}
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          {/* Type Filter Pills */}
          <div style={{ display: 'flex', background: 'var(--bg-secondary)', padding: '3px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            {['ALL', 'G', 'L', 'I'].map(t => (
              <button
                key={t}
                onClick={() => setTypeFilter(t)}
                style={{
                  padding: '5px 12px',
                  borderRadius: '5px',
                  border: 'none',
                  background: typeFilter === t ? 'var(--accent-gold)' : 'transparent',
                  color: typeFilter === t ? '#000' : 'var(--text-secondary)',
                  fontWeight: 700,
                  fontSize: '0.75rem',
                  cursor: 'pointer'
                }}
              >
                {t === 'ALL' ? 'All Types' : (t === 'G' ? 'Group (G)' : (t === 'L' ? 'Limited (L)' : 'Individual (I)'))}
              </button>
            ))}
          </div>

          {/* Level Filter */}
          <select
            value={levelFilter}
            onChange={e => setLevelFilter(e.target.value)}
            style={{
              padding: '7px 12px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              color: '#fff',
              fontSize: '0.8rem'
            }}
          >
            <option value="ALL">All Levels</option>
            {uniqueLevelsList.map(lvl => (
              <option key={lvl} value={lvl}>{lvl}</option>
            ))}
          </select>

          {/* Trainer Filter */}
          <select
            value={trainerFilter}
            onChange={e => setTrainerFilter(e.target.value)}
            style={{
              padding: '7px 12px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              color: '#fff',
              fontSize: '0.8rem'
            }}
          >
            <option value="ALL">All Trainers</option>
            {uniqueTrainersList.map(t => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>

          {/* Create New Batch Button */}
          <button
            onClick={() => {
              const newId = `BAT_${Date.now().toString().slice(-4)}`;
              setEditingBatch({
                batch_id: newId,
                batch_name: '',
                batch_type: 'G',
                level: 'Beginner',
                capacity_min: 4,
                capacity_max: 10,
                fixed_trainer: 'Unassigned',
                schedule_timings: '',
                weekly_slots: [],
                student_ids: [],
                students: []
              });
            }}
            className="btn btn-primary"
            style={{
              padding: '9px 18px',
              fontWeight: 800,
              fontSize: '0.85rem',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
              border: 'none',
              color: '#000'
            }}
          >
            <Plus size={16} /> Create New Batch
          </button>
        </div>
      </div>

      {/* BATCHES DATA TABLE */}
      {filteredBatches.length === 0 ? (
        <div className="glass-panel" style={{ padding: '60px 20px', textAlign: 'center', color: 'var(--text-secondary)' }}>
          <Layers size={48} style={{ color: 'var(--border-color)', marginBottom: '16px' }} />
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff', marginBottom: '8px' }}>
            No batches found
          </h3>
          <p style={{ fontSize: '0.85rem', maxWidth: '400px', margin: '0 auto 20px auto' }}>
            {searchQuery || typeFilter !== 'ALL' || levelFilter !== 'ALL' || trainerFilter !== 'ALL'
              ? 'No batches match your filter criteria. Try resetting search or filters.'
              : 'Start by creating your academy master batches with assigned trainers and weekly timing slots.'}
          </p>
          <button
            onClick={() => {
              const newId = `BAT_${Date.now().toString().slice(-4)}`;
              setEditingBatch({
                batch_id: newId,
                batch_name: '',
                batch_type: 'G',
                level: 'Beginner',
                capacity_min: 4,
                capacity_max: 10,
                fixed_trainer: 'Unassigned',
                schedule_timings: '',
                weekly_slots: [],
                student_ids: [],
                students: []
              });
            }}
            className="btn btn-primary"
            style={{ padding: '10px 20px', fontWeight: 700, fontSize: '0.85rem' }}
          >
            <Plus size={16} /> + Create First Batch
          </button>
        </div>
      ) : (
        <div className="glass-panel" style={{ overflowX: 'auto', padding: '0', borderRadius: 'var(--radius-lg)' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                <th style={{ padding: '14px 16px', fontWeight: 700, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>Batch Name & ID</th>
                <th style={{ padding: '14px 16px', fontWeight: 700, color: 'var(--text-secondary)', whiteSpace: 'nowrap', minWidth: '110px' }}>Type</th>
                <th style={{ padding: '14px 16px', fontWeight: 700, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>Level</th>
                <th style={{ padding: '14px 16px', fontWeight: 700, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>Capacity</th>
                <th style={{ padding: '14px 16px', fontWeight: 700, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>Fixed Trainer</th>
                <th style={{ padding: '14px 16px', fontWeight: 700, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>Schedule Timings</th>
                <th style={{ padding: '14px 16px', fontWeight: 700, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>Enrolled Students</th>
                <th style={{ padding: '14px 16px', fontWeight: 700, color: 'var(--text-secondary)', textAlign: 'center', whiteSpace: 'nowrap' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredBatches.map(batch => {
                const typeBadge = getBatchTypeBadge(batch.batch_type);
                const enrolled = (batch.students || []).length || (batch.student_ids || []).length || 0;
                const capMin = batch.capacity_min || (batch.batch_type === 'G' ? 4 : 1);
                const capMax = batch.capacity_max || (batch.batch_type === 'I' ? 1 : (batch.batch_type === 'L' ? 4 : 10));
                const isExpanded = expandedBatchId === batch.batch_id;

                return (
                  <React.Fragment key={batch.batch_id}>
                    <tr
                      style={{
                        borderBottom: '1px solid rgba(255,255,255,0.05)',
                        transition: 'background 0.15s ease'
                      }}
                      onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
                      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                    >
                      <td style={{ padding: '14px 16px', whiteSpace: 'nowrap' }}>
                        <div style={{ fontWeight: 800, color: '#fff', fontSize: '0.9rem' }}>{batch.batch_name}</div>
                        <div style={{ fontSize: '0.725rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>{batch.batch_id}</div>
                      </td>

                      <td style={{ padding: '14px 16px', whiteSpace: 'nowrap' }}>
                        <span style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          whiteSpace: 'nowrap',
                          padding: '4px 10px',
                          borderRadius: '6px',
                          background: typeBadge.bg,
                          color: typeBadge.color,
                          border: `1px solid ${typeBadge.border}`,
                          fontWeight: 700,
                          fontSize: '0.75rem',
                          letterSpacing: '0.01em',
                          lineHeight: 1.2
                        }}>
                          {typeBadge.label}
                        </span>
                      </td>

                      <td style={{ padding: '14px 16px', whiteSpace: 'nowrap' }}>
                        <span style={{
                          padding: '3px 9px',
                          borderRadius: '12px',
                          background: 'rgba(255,255,255,0.06)',
                          color: '#e2e8f0',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          whiteSpace: 'nowrap'
                        }}>
                          {batch.level || 'Beginner'}
                        </span>
                      </td>

                      <td style={{ padding: '14px 16px', whiteSpace: 'nowrap' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{
                            fontWeight: 800,
                            color: enrolled > capMax ? '#ef4444' : (enrolled < capMin ? '#f59e0b' : '#10b981')
                          }}>
                            {enrolled}
                          </span>
                          <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>/ {capMin}-{capMax} max</span>
                        </div>
                      </td>

                      <td style={{ padding: '14px 16px', whiteSpace: 'nowrap' }}>
                        <span style={{
                          padding: '4px 10px',
                          borderRadius: '6px',
                          background: batch.fixed_trainer && batch.fixed_trainer !== 'Unassigned' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                          color: batch.fixed_trainer && batch.fixed_trainer !== 'Unassigned' ? '#10b981' : '#f87171',
                          fontWeight: 700,
                          fontSize: '0.8rem',
                          whiteSpace: 'nowrap'
                        }}>
                          {batch.fixed_trainer || 'Unassigned'}
                        </span>
                      </td>

                      <td style={{ padding: '14px 16px', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                        {batch.weekly_slots && batch.weekly_slots.length > 0 ? (
                          <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                            {batch.weekly_slots.map((s, sIdx) => (
                              <span key={sIdx} style={{ padding: '2px 6px', borderRadius: '4px', background: 'rgba(255,255,255,0.05)', color: 'var(--accent-gold)', fontSize: '0.725rem' }}>
                                {s}
                              </span>
                            ))}
                          </div>
                        ) : (
                          batch.schedule_timings || 'Flexible'
                        )}
                      </td>

                      <td style={{ padding: '14px 16px' }}>
                        <button
                          onClick={() => setExpandedBatchId(isExpanded ? null : batch.batch_id)}
                          style={{
                            background: 'rgba(255,255,255,0.04)',
                            border: '1px solid var(--border-color)',
                            borderRadius: '6px',
                            color: 'var(--accent-gold)',
                            padding: '4px 10px',
                            fontSize: '0.75rem',
                            fontWeight: 700,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px'
                          }}
                        >
                          <Users size={14} /> {enrolled} Students {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                        </button>
                      </td>

                      <td style={{ padding: '14px 16px', textAlign: 'center' }}>
                        <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
                          <button
                            onClick={() => setEditingBatch({ ...batch })}
                            style={{
                              padding: '6px 10px',
                              borderRadius: '6px',
                              background: 'rgba(96, 165, 250, 0.15)',
                              border: '1px solid rgba(96, 165, 250, 0.3)',
                              color: '#60a5fa',
                              cursor: 'pointer'
                            }}
                            title="Edit Batch"
                          >
                            <Edit2 size={14} />
                          </button>
                          <button
                            onClick={() => {
                              if (window.confirm(`Are you sure you want to delete batch "${batch.batch_name}"?`)) {
                                onDeleteBatch(batch.batch_id);
                              }
                            }}
                            style={{
                              padding: '6px 10px',
                              borderRadius: '6px',
                              background: 'rgba(239, 68, 68, 0.15)',
                              border: '1px solid rgba(239, 68, 68, 0.3)',
                              color: '#ef4444',
                              cursor: 'pointer'
                            }}
                            title="Delete Batch"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>

                    {/* EXPANDED STUDENTS PANEL */}
                    {isExpanded && (
                      <tr style={{ background: 'rgba(0,0,0,0.25)' }}>
                        <td colSpan={8} style={{ padding: '14px 20px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                            <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-secondary)' }}>
                              Students Enrolled in {batch.batch_name} ({enrolled}/{capMax}):
                            </span>

                            {/* Quick Add Student Dropdown */}
                            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                              <select
                                value={studentToAdd.batchId === batch.batch_id ? studentToAdd.studentId : ''}
                                onChange={e => setStudentToAdd({ batchId: batch.batch_id, studentId: e.target.value })}
                                style={{
                                  padding: '5px 10px',
                                  borderRadius: '6px',
                                  background: 'var(--bg-secondary)',
                                  border: '1px solid var(--border-color)',
                                  color: '#fff',
                                  fontSize: '0.75rem'
                                }}
                              >
                                <option value="">+ Add student to batch...</option>
                                {allStudents
                                  .filter(s => !(batch.student_ids || []).includes(s.student_id) && !(batch.students || []).some(x => x.student_id === s.student_id))
                                  .map(s => (
                                    <option key={s.student_id} value={s.student_id}>
                                      {s.student_name} ({s.student_id}) - {s.student_level}
                                    </option>
                                  ))}
                              </select>

                              {studentToAdd.batchId === batch.batch_id && studentToAdd.studentId && (
                                <button
                                  onClick={() => handleAddStudentToBatch(batch, studentToAdd.studentId)}
                                  className="btn btn-primary"
                                  style={{ padding: '5px 12px', fontSize: '0.75rem', fontWeight: 700 }}
                                >
                                  Add
                                </button>
                              )}
                            </div>
                          </div>

                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                            {(batch.students || []).length === 0 ? (
                              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                                No students enrolled yet. Select a student from the dropdown above to add them.
                              </span>
                            ) : (
                              (batch.students || []).map((stu, sIdx) => (
                                <div
                                  key={stu.student_id || sIdx}
                                  style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '8px',
                                    padding: '5px 10px',
                                    borderRadius: '6px',
                                    background: 'rgba(255,255,255,0.06)',
                                    border: '1px solid var(--border-color)',
                                    fontSize: '0.775rem'
                                  }}
                                >
                                  <span style={{ fontWeight: 700, color: '#fff' }}>{stu.student_name}</span>
                                  <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>({stu.student_id})</span>
                                  <button
                                    onClick={() => handleRemoveStudentFromBatch(batch, stu.student_id)}
                                    style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', padding: '0', display: 'flex' }}
                                    title="Remove student from batch"
                                  >
                                    <X size={14} />
                                  </button>
                                </div>
                              ))
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* CREATE / EDIT BATCH MODAL */}
      {editingBatch && (
        <BatchEditModal
          batch={editingBatch}
          allCoaches={allCoaches}
          allStudents={allStudents}
          onSave={onSaveBatch}
          onClose={() => setEditingBatch(null)}
        />
      )}
    </div>
  );
}

// ----------------------------------------------------
// BATCH EDIT / ADD MODAL
// ----------------------------------------------------
function BatchEditModal({ batch, allCoaches, allStudents, onSave, onClose }) {
  const [formData, setFormData] = useState({
    batch_id: batch.batch_id || `BAT_${Date.now().toString().slice(-4)}`,
    batch_name: batch.batch_name || '',
    batch_type: batch.batch_type || 'G',
    level: batch.level || 'Beginner',
    capacity_min: batch.capacity_min || (batch.batch_type === 'G' ? 4 : 1),
    capacity_max: batch.capacity_max || (batch.batch_type === 'I' ? 1 : (batch.batch_type === 'L' ? 4 : 10)),
    fixed_trainer: batch.fixed_trainer || 'Unassigned',
    schedule_timings: batch.schedule_timings || '',
    weekly_slots: batch.weekly_slots || [],
    notes: batch.notes || ''
  });

  const [selectedStudentIds, setSelectedStudentIds] = useState(
    batch.student_ids || (batch.students || []).map(s => s.student_id)
  );

  // New slot entry helper
  const [newSlotDay, setNewSlotDay] = useState('Mon');
  const [newSlotTime, setNewSlotTime] = useState('08:00 PM');

  const handleAddSlot = () => {
    const slotStr = `${newSlotDay} ${newSlotTime}`;
    if (!formData.weekly_slots.includes(slotStr)) {
      const updatedSlots = [...formData.weekly_slots, slotStr];
      setFormData({
        ...formData,
        weekly_slots: updatedSlots,
        schedule_timings: updatedSlots.join(', ')
      });
    }
  };

  const handleRemoveSlot = (slotStr) => {
    const updatedSlots = formData.weekly_slots.filter(s => s !== slotStr);
    setFormData({
      ...formData,
      weekly_slots: updatedSlots,
      schedule_timings: updatedSlots.join(', ')
    });
  };

  const handleTypeChange = (newType) => {
    let minCap = 4;
    let maxCap = 10;
    if (newType === 'I') {
      minCap = 1;
      maxCap = 1;
    } else if (newType === 'L') {
      minCap = 1;
      maxCap = 4;
    }
    setFormData({
      ...formData,
      batch_type: newType,
      capacity_min: minCap,
      capacity_max: maxCap
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!formData.batch_name.trim()) {
      alert('Batch Name is required');
      return;
    }

    const assignedStudents = allStudents
      .filter(s => selectedStudentIds.includes(s.student_id))
      .map(s => ({
        student_id: s.student_id,
        student_name: s.student_name,
        student_level: s.student_level,
        mkca_rating: s.mkca_rating || '-',
        fixed_trainer: formData.fixed_trainer || 'Unassigned'
      }));

    const finalBatch = {
      ...formData,
      student_ids: selectedStudentIds,
      students: assignedStudents,
      student_count: assignedStudents.length
    };

    onSave(finalBatch);
    onClose();
  };

  const toggleStudent = (sId) => {
    if (selectedStudentIds.includes(sId)) {
      setSelectedStudentIds(selectedStudentIds.filter(id => id !== sId));
    } else {
      setSelectedStudentIds([...selectedStudentIds, sId]);
    }
  };

  const modalContent = (
    <div
      onClick={onClose}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        width: '100vw',
        height: '100vh',
        background: 'rgba(0, 0, 0, 0.8)',
        backdropFilter: 'blur(8px)',
        WebkitBackdropFilter: 'blur(8px)',
        zIndex: 99999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
        boxSizing: 'border-box'
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: '#0d131f',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-lg)',
          width: '100%',
          maxWidth: '680px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)'
        }}
      >
        {/* Modal Header */}
        <div style={{ padding: '20px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 800, color: '#fff' }}>
              {batch.batch_name ? `Edit Batch: ${batch.batch_name}` : 'Create New Batch'}
            </h3>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Configure batch details, trainer assignment, weekly slots, and student enrollment
            </p>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
            <X size={20} />
          </button>
        </div>

        {/* Modal Form Body */}
        <form onSubmit={handleSubmit} style={{ overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Row 1: Batch ID & Name */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                Batch ID
              </label>
              <input
                type="text"
                value={formData.batch_id}
                onChange={e => setFormData({ ...formData, batch_id: e.target.value })}
                required
                style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.85rem' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                Batch Name *
              </label>
              <input
                type="text"
                value={formData.batch_name}
                onChange={e => setFormData({ ...formData, batch_name: e.target.value })}
                placeholder="e.g. G Intermediate 2"
                required
                style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.85rem' }}
              />
            </div>
          </div>

          {/* Row 2: Type, Level, Fixed Trainer */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                Batch Type
              </label>
              <select
                value={formData.batch_type}
                onChange={e => handleTypeChange(e.target.value)}
                style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.85rem' }}
              >
                <option value="G">Group (G)</option>
                <option value="L">Limited (L)</option>
                <option value="I">Individual (I)</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                Level
              </label>
              <select
                value={formData.level}
                onChange={e => setFormData({ ...formData, level: e.target.value })}
                style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.85rem' }}
              >
                {['Basic 1', 'Basic 2', 'Beginner', 'Beginner 1', 'Beginner 2', 'Beginner 3', 'Early Intermediate 1', 'Early Intermediate 2', 'Intermediate', 'Intermediate 1', 'Advanced'].map(l => (
                  <option key={l} value={l}>{l}</option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                Fixed Trainer
              </label>
              <select
                value={formData.fixed_trainer}
                onChange={e => setFormData({ ...formData, fixed_trainer: e.target.value })}
                style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.85rem' }}
              >
                <option value="Unassigned">Unassigned</option>
                {allCoaches.map(c => (
                  <option key={c.coach_name} value={c.coach_name}>{c.coach_name}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Row 3: Capacity Min & Max */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                Min Capacity
              </label>
              <input
                type="number"
                min="1"
                max="20"
                value={formData.capacity_min}
                onChange={e => setFormData({ ...formData, capacity_min: parseInt(e.target.value) || 1 })}
                style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.85rem' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                Max Capacity
              </label>
              <input
                type="number"
                min="1"
                max="30"
                value={formData.capacity_max}
                onChange={e => setFormData({ ...formData, capacity_max: parseInt(e.target.value) || 1 })}
                style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.85rem' }}
              />
            </div>
          </div>

          {/* Row 4: Weekly Recurring Slots */}
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '6px' }}>
              Weekly Recurring Timings & Slots
            </label>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
              <select
                value={newSlotDay}
                onChange={e => setNewSlotDay(e.target.value)}
                style={{ padding: '8px 12px', borderRadius: '6px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.85rem' }}
              >
                {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(d => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
              <select
                value={newSlotTime}
                onChange={e => setNewSlotTime(e.target.value)}
                style={{ flex: 1, padding: '8px 12px', borderRadius: '6px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.85rem' }}
              >
                {[
                  '09:00 AM', '10:00 AM', '11:00 AM', '12:00 PM',
                  '04:00 PM', '05:00 PM', '06:00 PM', '07:00 PM', '08:00 PM', '09:00 PM'
                ].map(t => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
              <button
                type="button"
                onClick={handleAddSlot}
                className="btn btn-secondary"
                style={{ padding: '8px 16px', fontSize: '0.85rem', fontWeight: 700 }}
              >
                + Add Slot
              </button>
            </div>

            {/* Render Slot Chips */}
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', minHeight: '32px' }}>
              {formData.weekly_slots.map((s, idx) => (
                <span
                  key={idx}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '4px 10px',
                    borderRadius: '6px',
                    background: 'rgba(234, 179, 8, 0.15)',
                    border: '1px solid rgba(234, 179, 8, 0.4)',
                    color: 'var(--accent-gold)',
                    fontSize: '0.8rem',
                    fontWeight: 700
                  }}
                >
                  <Clock size={12} /> {s}
                  <button
                    type="button"
                    onClick={() => handleRemoveSlot(s)}
                    style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', padding: 0 }}
                  >
                    <X size={13} />
                  </button>
                </span>
              ))}
            </div>
          </div>

          {/* Row 5: Enrolled Students Selection */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <label style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)' }}>
                Enrolled Students ({selectedStudentIds.length}/{formData.capacity_max})
              </label>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                Click student chip to toggle enrollment
              </span>
            </div>

            <div style={{
              maxHeight: '160px',
              overflowY: 'auto',
              border: '1px solid var(--border-color)',
              borderRadius: '6px',
              padding: '10px',
              background: 'var(--bg-secondary)',
              display: 'flex',
              flexWrap: 'wrap',
              gap: '6px'
            }}>
              {allStudents.length === 0 ? (
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                  No students created yet in Master Data Hub.
                </span>
              ) : (
                allStudents.map(s => {
                  const isSelected = selectedStudentIds.includes(s.student_id);
                  return (
                    <button
                      key={s.student_id}
                      type="button"
                      onClick={() => toggleStudent(s.student_id)}
                      style={{
                        padding: '4px 10px',
                        borderRadius: '6px',
                        border: isSelected ? '1px solid #10b981' : '1px solid var(--border-color)',
                        background: isSelected ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255,255,255,0.04)',
                        color: isSelected ? '#10b981' : '#fff',
                        fontSize: '0.75rem',
                        fontWeight: isSelected ? 700 : 500,
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}
                    >
                      {isSelected && <Check size={12} />}
                      {s.student_name} ({s.student_id})
                    </button>
                  );
                })
              )}
            </div>
          </div>

          {/* Modal Actions */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
            <button
              type="button"
              onClick={onClose}
              className="btn btn-secondary"
              style={{ padding: '8px 16px', fontSize: '0.85rem' }}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              style={{ padding: '8px 20px', fontSize: '0.85rem', fontWeight: 800 }}
            >
              <Save size={16} /> Save Batch
            </button>
          </div>
        </form>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}
