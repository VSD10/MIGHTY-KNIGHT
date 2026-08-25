import React, { useState } from 'react';
import { Filter, AlertCircle, Edit3, Search, LayoutGrid, Table as TableIcon, Move, UserPlus, Calendar, X } from 'lucide-react';
import { applyManualEdit, assignStudentToClass } from '../services/api';

export default function AdminScheduleView({ adminScheduleData, onOpenManualEdit, scheduleId, onRefreshSchedule }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [levelFilter, setLevelFilter] = useState('ALL');
  const [coachFilter, setCoachFilter] = useState('ALL');
  const [startDateFilter, setStartDateFilter] = useState('');
  const [endDateFilter, setEndDateFilter] = useState('');
  const [sortBy, setSortBy] = useState('DATE');
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

  const STANDARD_STUDENT_LEVELS = [
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

  // Extract unique Coaches and Levels for Dropdown Filters
  const rawCoaches = Array.from(new Set(classes.map(c => c.coach_name).filter(Boolean))).sort();
  const coaches = ['ALL', ...rawCoaches];

  const rawLevels = Array.from(new Set(classes.map(c => c.student_level).filter(Boolean)));
  rawLevels.sort((a, b) => {
    const idxA = STANDARD_STUDENT_LEVELS.indexOf(a);
    const idxB = STANDARD_STUDENT_LEVELS.indexOf(b);
    if (idxA !== -1 && idxB !== -1) return idxA - idxB;
    if (idxA !== -1) return -1;
    if (idxB !== -1) return 1;
    return a.localeCompare(b);
  });
  const levels = ['ALL', ...rawLevels];

  // Calculate Schedule Date Span Summary
  const allDates = classes.map(c => c.date).filter(Boolean).sort();
  const minScheduleDate = allDates.length > 0 ? allDates[0] : '';
  const maxScheduleDate = allDates.length > 0 ? allDates[allDates.length - 1] : '';

  // Filter classes by Level, Coach, Date Range, and Search Query
  const filteredClasses = classes.filter(cls => {
    const matchesLevel = levelFilter === 'ALL' || cls.student_level === levelFilter;
    const matchesCoach = coachFilter === 'ALL' || (cls.coach_name || '').trim().toLowerCase() === coachFilter.trim().toLowerCase();
    const matchesStartDate = !startDateFilter || (cls.date && cls.date >= startDateFilter);
    const matchesEndDate = !endDateFilter || (cls.date && cls.date <= endDateFilter);
    const matchesSearch =
      (cls.coach_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (cls.students_formatted || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (cls.student_level || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (cls.date || '').toLowerCase().includes(searchQuery.toLowerCase());
    return matchesLevel && matchesCoach && matchesStartDate && matchesEndDate && matchesSearch;
  });

  // Dynamic Sorting Logic
  filteredClasses.sort((a, b) => {
    if (sortBy === 'COACH') {
      const cComp = (a.coach_name || '').localeCompare(b.coach_name || '');
      if (cComp !== 0) return cComp;
      const dComp = (a.date || '').localeCompare(b.date || '');
      if (dComp !== 0) return dComp;
      return getTimeSlotSortMinutes(a.time_slot) - getTimeSlotSortMinutes(b.time_slot);
    } else if (sortBy === 'LEVEL') {
      const idxA = STANDARD_STUDENT_LEVELS.indexOf(a.student_level);
      const idxB = STANDARD_STUDENT_LEVELS.indexOf(b.student_level);
      const lComp = (idxA !== -1 ? idxA : 99) - (idxB !== -1 ? idxB : 99);
      if (lComp !== 0) return lComp;
      const dComp = (a.date || '').localeCompare(b.date || '');
      if (dComp !== 0) return dComp;
      return getTimeSlotSortMinutes(a.time_slot) - getTimeSlotSortMinutes(b.time_slot);
    } else if (sortBy === 'STUDENTS') {
      const countA = Array.isArray(a.student_ids) ? a.student_ids.length : 0;
      const countB = Array.isArray(b.student_ids) ? b.student_ids.length : 0;
      const sComp = countB - countA;
      if (sComp !== 0) return sComp;
      const dComp = (a.date || '').localeCompare(b.date || '');
      if (dComp !== 0) return dComp;
      return getTimeSlotSortMinutes(a.time_slot) - getTimeSlotSortMinutes(b.time_slot);
    } else {
      // Default: DATE (Chronological)
      const dComp = (a.date || '').localeCompare(b.date || '');
      if (dComp !== 0) return dComp;
      return getTimeSlotSortMinutes(a.time_slot) - getTimeSlotSortMinutes(b.time_slot);
    }
  });

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
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '6px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.75rem', padding: '3px 10px', borderRadius: '4px', background: 'rgba(251, 191, 36, 0.15)', border: '1px solid var(--accent-gold)', color: 'var(--accent-gold)', fontWeight: 700 }}>
              📅 Schedule Date Span: {minScheduleDate || 'N/A'} to {maxScheduleDate || 'N/A'}
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              • Showing <strong>{filteredClasses.length}</strong> of <strong>{classes.length}</strong> classes
            </span>
          </div>
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

          {/* Date Range Filter Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--bg-secondary)', padding: '6px 12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <Calendar size={15} style={{ color: 'var(--accent-gold)' }} />
            <span style={{ fontSize: '0.775rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Filter Date:</span>
            <input
              type="date"
              value={startDateFilter}
              onChange={e => setStartDateFilter(e.target.value)}
              title="Filter Start Date"
              style={{ background: 'transparent', border: 'none', color: '#fff', fontSize: '0.8rem', cursor: 'pointer' }}
            />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>to</span>
            <input
              type="date"
              value={endDateFilter}
              onChange={e => setEndDateFilter(e.target.value)}
              title="Filter End Date"
              style={{ background: 'transparent', border: 'none', color: '#fff', fontSize: '0.8rem', cursor: 'pointer' }}
            />
            {(startDateFilter || endDateFilter) && (
              <button
                onClick={() => { setStartDateFilter(''); setEndDateFilter(''); }}
                style={{ background: 'none', border: 'none', color: 'var(--status-danger)', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '2px' }}
                title="Clear date filter"
              >
                <X size={14} /> Clear
              </button>
            )}
          </div>

          {/* Coach Filter Dropdown */}
          <select
            value={coachFilter}
            onChange={e => setCoachFilter(e.target.value)}
            style={{
              padding: '8px 14px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              color: '#fff',
              fontSize: '0.85rem'
            }}
          >
            {coaches.map(c => (
              <option key={c} value={c}>{c === 'ALL' ? 'All Coaches' : `Coach: ${c}`}</option>
            ))}
          </select>

          {/* Level Filter Dropdown */}
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

          {/* Sort By Selector */}
          <select
            value={sortBy}
            onChange={e => setSortBy(e.target.value)}
            style={{
              padding: '8px 14px',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(251, 191, 36, 0.15)',
              border: '1px solid var(--accent-gold)',
              color: 'var(--accent-gold)',
              fontSize: '0.85rem',
              fontWeight: 700
            }}
          >
            <option value="DATE" style={{ background: '#1e293b', color: '#fff' }}>📅 Sort by Date (Chronological)</option>
            <option value="COACH" style={{ background: '#1e293b', color: '#fff' }}>👨‍🏫 Sort by Coach Name</option>
            <option value="LEVEL" style={{ background: '#1e293b', color: '#fff' }}>🎓 Sort by Student Level</option>
            <option value="STUDENTS" style={{ background: '#1e293b', color: '#fff' }}>👥 Sort by Batch Size</option>
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
                <th>Student Names (Drop Target)</th>
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
                        {(Array.isArray(cls.student_names) && cls.student_names.length > 0 ? cls.student_names.join(' · ') : (cls.students_formatted || '')).replace(/\s*\([^)]*\)/g, '')}
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
                        {(Array.isArray(cls.student_names) && cls.student_names.length > 0 ? cls.student_names.join(' · ') : (cls.students_formatted || '')).replace(/\s*\([^)]*\)/g, '')}
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
