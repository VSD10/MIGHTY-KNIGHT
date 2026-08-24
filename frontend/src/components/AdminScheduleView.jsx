import React, { useState } from 'react';
import { Filter, AlertCircle, Edit3, Search, LayoutGrid, Table as TableIcon, Move, UserPlus } from 'lucide-react';
import { applyManualEdit, assignStudentToClass } from '../services/api';

export default function AdminScheduleView({ adminScheduleData, onOpenManualEdit, scheduleId, onRefreshSchedule }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [levelFilter, setLevelFilter] = useState('ALL');
  const [viewMode, setViewMode] = useState('table'); // 'table' or 'board'
  const [dragOverClassId, setDragOverClassId] = useState(null);

  if (!adminScheduleData || !adminScheduleData.detailed_classes) {
    return (
      <div className="glass-panel" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
        <p>No detailed administrative schedule available. Please generate a schedule first.</p>
      </div>
    );
  }

  const classes = adminScheduleData.detailed_classes;

const getTimeSlotSortMinutes = (timeSlotStr) => {
  if (!timeSlotStr) return 0;
  try {
    const startPart = timeSlotStr.split('-')[0].trim();
    const match = startPart.match(/^(\d{1,2}):(\d{2})\s*(AM|PM)$/i);
    if (!match) return 0;
    let hours = parseInt(match[1], 10);
    const minutes = parseInt(match[2], 10);
    const ampm = match[3].toUpperCase();
    if (ampm === 'PM' && hours < 12) hours += 12;
    if (ampm === 'AM' && hours === 12) hours = 0;
    return hours * 60 + minutes;
  } catch (e) {
    return 0;
  }
};

  // Filter & Sort classes chronologically
  const filteredClasses = classes.filter(cls => {
    const matchesLevel = levelFilter === 'ALL' || cls.student_level === levelFilter;
    const matchesSearch =
      cls.coach_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      cls.students_formatted.toLowerCase().includes(searchQuery.toLowerCase()) ||
      cls.student_level.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesLevel && matchesSearch;
  });

  filteredClasses.sort((a, b) => {
    const dateComp = (a.date || '').localeCompare(b.date || '');
    if (dateComp !== 0) return dateComp;
    return getTimeSlotSortMinutes(a.time_slot) - getTimeSlotSortMinutes(b.time_slot);
  });

  const levels = ['ALL', ...new Set(classes.map(c => c.student_level))];

  // Group classes by Date & Day for Board View
  const dateMap = {};
  filteredClasses.forEach(cls => {
    const key = `${cls.date} (${cls.day})`;
    if (!dateMap[key]) dateMap[key] = [];
    dateMap[key].push(cls);
  });

  // Handle Drag and Drop Assignment of Unscheduled Students onto Class
  const handleDropOnClass = async (e, targetClass) => {
    e.preventDefault();
    setDragOverClassId(null);
    try {
      const rawData = e.dataTransfer.getData("application/json");
      if (!rawData) return;
      const data = JSON.parse(rawData);

      if (data.type === "UNSCHEDULED_STUDENT" && data.student) {
        await assignStudentToClass(scheduleId, data.student.student_id, targetClass.class_id);
        if (onRefreshSchedule) onRefreshSchedule();
      } else if (data.class_id) {
        onOpenManualEdit(targetClass);
      }
    } catch (err) {
      console.error("Drop failed:", err);
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '24px' }}>
      {/* Header & Controls */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
        <div>
          <h2 style={{ fontSize: '1.2rem', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
            📋 Output 2 — Detailed Administrative Schedule
          </h2>
          <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)' }}>
            Complete class details. Drag & drop classes or drag unscheduled students to assign!
          </p>
        </div>

        {/* Controls: Search, Level Filter, View Mode Toggle */}
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
          {/* View Mode Toggle */}
          <div style={{ display: 'flex', background: 'var(--bg-secondary)', padding: '3px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <button
              onClick={() => setViewMode('table')}
              className={`btn ${viewMode === 'table' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ padding: '6px 12px', fontSize: '0.8rem' }}
            >
              <TableIcon size={14} /> Table View
            </button>
            <button
              onClick={() => setViewMode('board')}
              className={`btn ${viewMode === 'board' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ padding: '6px 12px', fontSize: '0.8rem' }}
            >
              <LayoutGrid size={14} /> Drag & Drop Board
            </button>
          </div>

          <div style={{ position: 'relative' }}>
            <Search size={16} style={{ position: 'absolute', left: '12px', top: '10px', color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Search coach, student, level..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              style={{
                padding: '8px 12px 8px 36px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border-color)',
                color: '#fff',
                fontSize: '0.85rem'
              }}
            />
          </div>

          <select
            value={levelFilter}
            onChange={e => setLevelFilter(e.target.value)}
            style={{
              padding: '8px 14px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              color: '#fff',
              fontSize: '0.85rem'
            }}
          >
            {levels.map(l => (
              <option key={l} value={l}>{l === 'ALL' ? 'All Student Levels' : l}</option>
            ))}
          </select>
        </div>
      </div>

      {/* VIEW MODE 1: TABLE VIEW */}
      {viewMode === 'table' ? (
        <div style={{ overflowX: 'auto', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
          <table className="custom-table">
            <thead>
              <tr>
                <th>Date / Day / Time</th>
                <th>Assigned Coach</th>
                <th>Level & Batch</th>
                <th>Count</th>
                <th>Student Names & IDs (Drop Target)</th>
                <th>Warnings / Flags</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredClasses.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '30px' }}>
                    No classes match the selected filter.
                  </td>
                </tr>
              ) : (
                filteredClasses.map(cls => (
                  <tr
                    key={cls.class_id}
                    onDragOver={e => { e.preventDefault(); setDragOverClassId(cls.class_id); }}
                    onDragLeave={() => setDragOverClassId(null)}
                    onDrop={e => handleDropOnClass(e, cls)}
                    style={{
                      background: dragOverClassId === cls.class_id ? 'rgba(245, 158, 11, 0.15)' : 'transparent',
                      transition: 'background 0.2s'
                    }}
                  >
                    <td>
                      <div style={{ fontWeight: 700, color: '#fff' }}>{cls.date} ({cls.day})</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--accent-gold)' }}>{cls.time_slot}</div>
                    </td>
                    <td>
                      <span className="badge badge-gold" style={{ fontSize: '0.85rem' }}>
                        {cls.coach_name}
                      </span>
                    </td>
                    <td>
                      <div style={{ fontWeight: 600, color: '#fff' }}>{cls.student_level}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                        Batch Type: <strong>{cls.batch_type}</strong>
                      </div>
                    </td>
                    <td>
                      <span style={{ fontWeight: 700, color: 'var(--accent-blue)' }}>{cls.student_count}</span>
                    </td>
                    <td style={{ maxWidth: '350px' }}>
                      <div style={{ fontSize: '0.825rem', color: 'var(--text-primary)', lineHeight: 1.4 }}>
                        {cls.students_formatted}
                      </div>
                    </td>
                    <td>
                      {cls.warnings && cls.warnings.length > 0 ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          {cls.warnings.map((w, wIdx) => (
                            <span key={wIdx} className="badge badge-warning" style={{ fontSize: '0.7rem' }}>
                              <AlertCircle size={12} style={{ marginRight: '4px' }} /> {w}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span style={{ fontSize: '0.75rem', color: 'var(--status-success)' }}>✓ Compatible</span>
                      )}
                    </td>
                    <td>
                      <button
                        onClick={() => onOpenManualEdit(cls)}
                        className="btn btn-secondary"
                        style={{ padding: '6px 12px', fontSize: '0.75rem' }}
                      >
                        <Edit3 size={14} /> Edit Class
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      ) : (
        /* VIEW MODE 2: INTERACTIVE DRAG & DROP BOARD */
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '20px' }}>
          {Object.keys(dateMap).length === 0 ? (
            <p style={{ color: 'var(--text-secondary)' }}>No classes available to display in board view.</p>
          ) : (
            Object.keys(dateMap).sort().map(dateGroup => (
              <div key={dateGroup} className="glass-card" style={{ padding: '16px' }}>
                <h3 style={{ fontSize: '0.95rem', fontWeight: 800, color: 'var(--accent-gold)', marginBottom: '12px', borderBottom: '1px solid var(--border-color)', pb: '8px' }}>
                  📅 {dateGroup} ({dateMap[dateGroup].length} classes)
                </h3>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {dateMap[dateGroup].map(cls => (
                    <div
                      key={cls.class_id}
                      draggable={true}
                      onDragStart={e => e.dataTransfer.setData("application/json", JSON.stringify(cls))}
                      onDragOver={e => { e.preventDefault(); setDragOverClassId(cls.class_id); }}
                      onDragLeave={() => setDragOverClassId(null)}
                      onDrop={e => handleDropOnClass(e, cls)}
                      style={{
                        background: dragOverClassId === cls.class_id ? 'rgba(245, 158, 11, 0.25)' : 'var(--bg-secondary)',
                        border: dragOverClassId === cls.class_id ? '2px dashed var(--accent-gold)' : '1px solid var(--border-color)',
                        borderRadius: 'var(--radius-md)',
                        padding: '14px',
                        cursor: 'grab',
                        transition: 'all 0.2s'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                        <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent-gold)' }}>
                          {cls.time_slot}
                        </span>
                        <span className="badge badge-gold" style={{ fontSize: '0.75rem' }}>
                          {cls.coach_name}
                        </span>
                      </div>

                      <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#fff', marginBottom: '4px' }}>
                        {cls.student_level} (Batch {cls.batch_type})
                      </div>

                      <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '10px', lineHeight: 1.3 }}>
                        {cls.students_formatted}
                      </p>

                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                          Drag student here to add
                        </span>
                        <button
                          onClick={() => onOpenManualEdit(cls)}
                          className="btn btn-secondary"
                          style={{ padding: '4px 10px', fontSize: '0.725rem' }}
                        >
                          <Edit3 size={12} /> Edit
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
