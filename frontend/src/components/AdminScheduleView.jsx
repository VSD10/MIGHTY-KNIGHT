import React, { useState } from 'react';
import { Filter, AlertCircle, Edit3, UserCheck, Search } from 'lucide-react';

export default function AdminScheduleView({ adminScheduleData, onOpenManualEdit }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [levelFilter, setLevelFilter] = useState('ALL');

  if (!adminScheduleData || !adminScheduleData.detailed_classes) {
    return (
      <div className="glass-panel" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
        <p>No detailed administrative schedule available. Please generate a schedule first.</p>
      </div>
    );
  }

  const classes = adminScheduleData.detailed_classes;

  // Filter classes
  const filteredClasses = classes.filter(cls => {
    const matchesLevel = levelFilter === 'ALL' || cls.student_level === levelFilter;
    const matchesSearch =
      cls.coach_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      cls.students_formatted.toLowerCase().includes(searchQuery.toLowerCase()) ||
      cls.student_level.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesLevel && matchesSearch;
  });

  const levels = ['ALL', ...new Set(classes.map(c => c.student_level))];

  return (
    <div className="glass-panel" style={{ padding: '24px' }}>
      {/* Header & Controls */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
        <div>
          <h2 style={{ fontSize: '1.2rem', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
            📋 Output 2 — Detailed Administrative Schedule
          </h2>
          <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)' }}>
            Complete class details: Date, Day, Time, Coach, Level, Batch Type, Headcount, Student Names & IDs (BRD Section 35).
          </p>
        </div>

        {/* Search & Level Filter */}
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
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

      {/* Class Matrix Table */}
      <div style={{ overflowX: 'auto', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
        <table className="custom-table">
          <thead>
            <tr>
              <th>Date / Day / Time</th>
              <th>Assigned Coach</th>
              <th>Level & Batch</th>
              <th>Count</th>
              <th>Student Names & IDs</th>
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
                <tr key={cls.class_id}>
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
    </div>
  );
}
