import React, { useState, useMemo } from 'react';
import {
  Search, Download, Calendar, ShieldCheck, Sparkles, Clock, BookOpen,
  Copy, Check, Filter, CheckCircle2, AlertCircle, ChevronDown, ChevronUp, UserCheck, Lock
} from 'lucide-react';
import { getStudentIcsUrl } from '../services/api';

const LEVEL_LIST = [
  'ALL',
  'Basic 1',
  'Basic 2',
  'Beginner 1',
  'Beginner 2',
  'Early Intermediate 1',
  'Early Intermediate 2',
  'Intermediate 1',
  'Intermediate 2'
];

export default function StudentScheduleView({ studentScheduleData, detailedClasses = [], scheduleId }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedLevelFilter, setSelectedLevelFilter] = useState('ALL');
  const [expandedStudentId, setExpandedStudentId] = useState(null);
  const [copiedId, setCopiedId] = useState(null);
  const [icsLockStudent, setIcsLockStudent] = useState(null);

  // Extract dynamic student schedules from backend API output
  const rawList = useMemo(() => {
    if (studentScheduleData?.student_schedules && studentScheduleData.student_schedules.length > 0) {
      return studentScheduleData.student_schedules;
    }

    // Fallback: derive dynamically from detailedClasses if studentScheduleData is not yet fetched
    const studentMap = {};
    (detailedClasses || []).forEach(cls => {
      (cls.student_ids || []).forEach((sid, idx) => {
        if (!studentMap[sid]) {
          const sname = (cls.student_names && cls.student_names[idx]) || sid;
          studentMap[sid] = {
            student_id: sid,
            student_name: sname,
            student_level: cls.student_level || 'Beginner 1',
            batch_type: cls.batch_type || 'G',
            required_classes: 8,
            scheduled_classes_count: 0,
            classes: []
          };
        }
        studentMap[sid].scheduled_classes_count += 1;
        studentMap[sid].classes.push(cls);
      });
    });

    return Object.values(studentMap);
  }, [studentScheduleData, detailedClasses]);

  // Sort alphabetically by student name
  const sortedStudents = useMemo(() => {
    return [...rawList].sort((a, b) => (a.student_name || '').localeCompare(b.student_name || ''));
  }, [rawList]);

  // Filter by search and level
  const filteredStudents = useMemo(() => {
    return sortedStudents.filter(s => {
      const q = searchQuery.toLowerCase().trim();
      const matchesSearch = !q ||
        (s.student_name || '').toLowerCase().includes(q) ||
        (s.student_id || '').toLowerCase().includes(q) ||
        (s.student_level || '').toLowerCase().includes(q);

      const matchesLevel = selectedLevelFilter === 'ALL' || s.student_level === selectedLevelFilter;
      return matchesSearch && matchesLevel;
    });
  }, [sortedStudents, searchQuery, selectedLevelFilter]);

  const handleCopyId = (id) => {
    navigator.clipboard.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const toggleExpand = (sid) => {
    setExpandedStudentId(prev => (prev === sid ? null : sid));
  };

  // Stats calculation
  const totalStudents = sortedStudents.length;
  const fullyScheduledStudents = sortedStudents.filter(s => (s.scheduled_classes_count || 0) >= (s.required_classes || 8)).length;
  const totalAssignedSessions = sortedStudents.reduce((sum, s) => sum + (s.scheduled_classes_count || 0), 0);
  const avgCompletionPct = totalStudents > 0
    ? Math.round(sortedStudents.reduce((sum, s) => sum + Math.min(100, Math.round(((s.scheduled_classes_count || 0) / (s.required_classes || 8)) * 100)), 0) / totalStudents)
    : 0;

  return (
    <div className="glass-panel" style={{ padding: '24px' }}>
      {/* 1. Header & Controls */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px', marginBottom: '24px', borderBottom: '1px solid var(--border-color)', paddingBottom: '16px' }}>
        <div>
          <h2 style={{ fontSize: '1.35rem', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '10px' }}>
            🎓 Output 5 — Dynamic Student Schedules & Calendars
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
            100% dynamic timetable per enrolled student • Quota tracking • Individual .ics calendar synchronization.
          </p>
        </div>

        {/* Global Metric Cards */}
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ background: 'var(--bg-secondary)', padding: '10px 16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <span style={{ fontSize: '0.7rem', color: '#d1d5db', display: 'block' }}>ENROLLED STUDENTS</span>
            <strong style={{ fontSize: '1.2rem', color: '#fff' }}>{totalStudents}</strong>
          </div>

          <div style={{ background: 'rgba(16, 185, 129, 0.15)', padding: '10px 16px', borderRadius: 'var(--radius-md)', border: '1px solid rgba(16, 185, 129, 0.4)' }}>
            <span style={{ fontSize: '0.7rem', color: '#a7f3d0', display: 'block' }}>FULL QUOTA MET</span>
            <strong style={{ fontSize: '1.2rem', color: '#34d399' }}>{fullyScheduledStudents} / {totalStudents}</strong>
          </div>

          <div style={{ background: 'rgba(59, 130, 246, 0.15)', padding: '10px 16px', borderRadius: 'var(--radius-md)', border: '1px solid rgba(59, 130, 246, 0.4)' }}>
            <span style={{ fontSize: '0.7rem', color: '#bfdbfe', display: 'block' }}>AVG QUOTA FULFILLMENT</span>
            <strong style={{ fontSize: '1.2rem', color: 'var(--accent-blue)' }}>{avgCompletionPct}%</strong>
          </div>
        </div>
      </div>

      {/* 2. Filter & Search Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px', marginBottom: '24px' }}>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center', flex: 1 }}>
          <div style={{ position: 'relative', minWidth: '280px', maxWidth: '420px', flex: 1 }}>
            <Search size={16} style={{ position: 'absolute', left: '12px', top: '10px', color: 'var(--accent-gold)' }} />
            <input
              type="text"
              placeholder="Search student by name or ID..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px 8px 36px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border-color)',
                color: '#fff',
                fontSize: '0.85rem'
              }}
            />
          </div>

          {/* Level Filter Dropdown */}
          <select
            value={selectedLevelFilter}
            onChange={e => setSelectedLevelFilter(e.target.value)}
            style={{
              padding: '8px 14px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              color: '#fff',
              fontSize: '0.85rem'
            }}
          >
            {LEVEL_LIST.map(lvl => (
              <option key={lvl} value={lvl}>{lvl === 'ALL' ? 'All Levels' : lvl}</option>
            ))}
          </select>
        </div>

        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          Showing {filteredStudents.length} of {totalStudents} students
        </span>
      </div>

      {/* 3. Students List Grid */}
      {filteredStudents.length === 0 ? (
        <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)', background: 'rgba(0,0,0,0.2)', borderRadius: 'var(--radius-lg)' }}>
          <p>No student schedules match your search query or filter.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {filteredStudents.map(student => {
            const sid = student.student_id;
            const sname = student.student_name;
            const lvl = student.student_level || 'Beginner 1';
            const btype = student.batch_type || 'G';
            const schCount = student.scheduled_classes_count || (student.classes ? student.classes.length : 0);
            const reqCount = student.required_classes || 8;
            const completionPct = Math.min(100, Math.round((schCount / reqCount) * 100));
            const isFullyScheduled = schCount >= reqCount;
            const isExpanded = expandedStudentId === sid;

            const classesList = student.classes || (detailedClasses || []).filter(c => (c.student_ids || []).includes(sid));

            // .ics calendar link
            const icsUrl = getStudentIcsUrl(scheduleId || 'ACTIVE_LATEST', sid);

            return (
              <div
                key={sid}
                style={{
                  background: 'var(--bg-secondary)',
                  borderRadius: 'var(--radius-md)',
                  border: isExpanded ? '1px solid var(--accent-gold)' : '1px solid var(--border-color)',
                  overflow: 'hidden',
                  transition: 'border-color 0.2s ease'
                }}
              >
                {/* Banner Summary Row */}
                <div
                  style={{
                    padding: '16px 20px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: '14px'
                  }}
                >
                  {/* Left: Identity & Badges */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '14px', minWidth: '240px' }}>
                    <div
                      style={{
                        width: '40px',
                        height: '40px',
                        borderRadius: '50%',
                        background: isFullyScheduled ? 'rgba(16, 185, 129, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                        border: `1px solid ${isFullyScheduled ? '#10b981' : '#f59e0b'}`,
                        color: isFullyScheduled ? '#34d399' : '#fbbf24',
                        fontWeight: 800,
                        fontSize: '1rem',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                      }}
                    >
                      {sname.charAt(0).toUpperCase()}
                    </div>

                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <h4 style={{ fontSize: '1rem', fontWeight: 800, color: '#fff', margin: 0 }}>
                          {sname}
                        </h4>
                        <span className="badge badge-gold" style={{ fontSize: '0.675rem' }}>
                          Batch {btype}
                        </span>
                        <span
                          className="badge"
                          style={{
                            fontSize: '0.675rem',
                            background: isFullyScheduled ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.15)',
                            color: isFullyScheduled ? '#34d399' : '#f87171',
                            border: `1px solid ${isFullyScheduled ? '#10b981' : 'rgba(239, 68, 68, 0.4)'}`
                          }}
                        >
                          {schCount} / {reqCount} Classes
                        </span>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '4px', fontSize: '0.775rem', color: 'var(--text-secondary)' }}>
                        <span
                          onClick={() => handleCopyId(sid)}
                          style={{ cursor: 'pointer', fontFamily: 'monospace', color: 'var(--accent-gold)' }}
                          title="Click to copy Student ID"
                        >
                          ID: {sid} {copiedId === sid ? '✓' : ''}
                        </span>
                        <span>•</span>
                        <span>Level: <strong style={{ color: '#fff' }}>{lvl}</strong></span>
                      </div>
                    </div>
                  </div>

                  {/* Middle: Quota Progress Bar */}
                  <div style={{ minWidth: '160px', flex: 1, maxWidth: '240px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.725rem', marginBottom: '4px' }}>
                      <span style={{ color: 'var(--text-muted)' }}>Monthly Quota</span>
                      <strong style={{ color: isFullyScheduled ? '#34d399' : '#fbbf24' }}>{completionPct}%</strong>
                    </div>
                    <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden' }}>
                      <div
                        style={{
                          width: `${completionPct}%`,
                          height: '100%',
                          background: isFullyScheduled ? '#10b981' : '#f59e0b',
                          transition: 'width 0.3s ease'
                        }}
                      />
                    </div>
                  </div>

                  {/* Right: Actions */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {/* Individual .ics Sync Download (Enforce 100% Quota Section 3) */}
                    {isFullyScheduled ? (
                      <a
                        href={icsUrl}
                        download={`mighty_knight_${sid}_calendar.ics`}
                        className="btn btn-secondary"
                        style={{
                          padding: '6px 12px',
                          fontSize: '0.75rem',
                          textDecoration: 'none',
                          color: '#34d399',
                          borderColor: '#10b981',
                          background: 'rgba(16, 185, 129, 0.1)',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '5px'
                        }}
                        title="Download .ics Calendar for this student (100% Quota Completed)"
                      >
                        <Calendar size={13} style={{ color: '#10b981' }} /> .ics Sync
                      </a>
                    ) : (
                      <button
                        onClick={() => setIcsLockStudent({
                          student_id: sid,
                          student_name: sname,
                          schCount,
                          reqCount,
                          completionPct
                        })}
                        className="btn btn-secondary"
                        style={{
                          padding: '6px 12px',
                          fontSize: '0.75rem',
                          color: '#94a3b8',
                          background: 'rgba(255, 255, 255, 0.04)',
                          borderColor: 'rgba(245, 158, 11, 0.35)',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '5px',
                          cursor: 'pointer'
                        }}
                        title={`ICS Sync Locked: ${completionPct}% completed (100% quota required)`}
                      >
                        <Lock size={13} style={{ color: '#f59e0b' }} /> .ics Sync (Locked)
                      </button>
                    )}

                    {/* Expand / View Timetable */}
                    <button
                      onClick={() => toggleExpand(sid)}
                      className="btn btn-primary"
                      style={{
                        padding: '6px 12px',
                        fontSize: '0.75rem',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '5px'
                      }}
                    >
                      {isExpanded ? 'Hide Sessions' : `View Sessions (${classesList.length})`}
                      {isExpanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                    </button>
                  </div>
                </div>

                {/* Expanded Detailed Timetable */}
                {isExpanded && (
                  <div style={{ padding: '16px 20px', borderTop: '1px solid var(--border-color)', background: 'var(--bg-card)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                      <h5 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-gold)', margin: 0, display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <BookOpen size={14} /> Scheduled Sessions for {sname} ({classesList.length} session{classesList.length !== 1 ? 's' : ''})
                      </h5>
                      <span style={{ fontSize: '0.725rem', color: 'var(--text-muted)' }}>
                        Status: {isFullyScheduled ? '✅ Full Monthly Quota Met' : `⚠️ Shortfall of ${Math.max(0, reqCount - schCount)} classes`}
                      </span>
                    </div>

                    {classesList.length === 0 ? (
                      <div style={{ padding: '16px', textAlign: 'center', color: 'var(--text-muted)', fontStyle: 'italic', background: 'rgba(0,0,0,0.2)', borderRadius: '6px', fontSize: '0.8rem' }}>
                        No scheduled classes yet for this student. Use Attention Required or Admin Matrix to assign sessions.
                      </div>
                    ) : (
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '10px' }}>
                        {classesList.map((cls, cIdx) => (
                          <div
                            key={cIdx}
                            style={{
                              background: 'var(--bg-secondary)',
                              padding: '12px',
                              borderRadius: '6px',
                              border: cls.is_compensation ? '1px solid rgba(251, 191, 36, 0.4)' : '1px solid var(--border-color)',
                              display: 'flex',
                              flexDirection: 'column',
                              gap: '6px'
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <strong style={{ fontSize: '0.825rem', color: '#fff' }}>
                                📅 {cls.day} ({cls.date})
                              </strong>
                              {cls.is_compensation && (
                                <span style={{ padding: '1px 5px', borderRadius: '3px', background: 'rgba(56, 189, 248, 0.2)', color: '#38bdf8', fontSize: '0.65rem' }}>
                                  ⓒ
                                </span>
                              )}
                            </div>

                            <div style={{ fontSize: '0.775rem', color: 'var(--accent-blue)', fontWeight: 600 }}>
                              ⏰ {cls.time_slot}
                            </div>

                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                              <span>Trainer: <strong style={{ color: 'var(--accent-gold)' }}>Coach {cls.coach_name}</strong></span>
                              <span>{cls.batch_name || `Batch ${btype}`}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Student ICS Synchronization Ineligible / Locked Modal */}
      {icsLockStudent && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(5px)',
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
              maxWidth: '500px',
              width: '100%',
              padding: '24px',
              background: 'linear-gradient(135deg, rgba(20, 27, 45, 0.98) 0%, rgba(15, 23, 42, 0.98) 100%)',
              border: '1.5px solid #f59e0b',
              borderRadius: '16px',
              boxShadow: '0 16px 40px rgba(0, 0, 0, 0.6)'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px', color: '#f59e0b' }}>
              <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'rgba(245, 158, 11, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Lock size={22} style={{ color: '#f59e0b' }} />
              </div>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 800, color: '#fff' }}>
                  Student Calendar Sync Locked
                </h3>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                  Academy Quota Rule Enforcement
                </span>
              </div>
            </div>

            <p style={{ fontSize: '0.875rem', color: '#cbd5e1', lineHeight: '1.5', marginBottom: '14px' }}>
              Student <strong>{icsLockStudent.student_name}</strong> (<code>{icsLockStudent.student_id}</code>) currently has{' '}
              <strong style={{ color: '#f59e0b' }}>{icsLockStudent.schCount} of {icsLockStudent.reqCount}</strong> required monthly classes scheduled ({icsLockStudent.completionPct}% completed).
            </p>

            <div
              style={{
                background: 'rgba(245, 158, 11, 0.1)',
                border: '1px solid rgba(245, 158, 11, 0.3)',
                borderRadius: '8px',
                padding: '12px 14px',
                marginBottom: '18px',
                fontSize: '0.8rem',
                color: '#fde68a',
                lineHeight: '1.4'
              }}
            >
              ⚠️ <strong>Mandatory Requirement:</strong> Student .ics calendar synchronization is restricted until the student's monthly quota reaches <strong>100%</strong> and any pending Attention Required assignments or unassigned sessions are fully confirmed.
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                onClick={() => setIcsLockStudent(null)}
                className="btn btn-primary"
                style={{ padding: '8px 20px', fontSize: '0.85rem', fontWeight: 700 }}
              >
                Understood
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
