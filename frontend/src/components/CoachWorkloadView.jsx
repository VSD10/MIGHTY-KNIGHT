import React, { useState } from 'react';
import {
  Clock, Users, Award, AlertTriangle, CheckCircle2, Search, BarChart2,
  Download, MessageSquare, ChevronDown, ChevronUp, Copy, Check, Calendar,
  BookOpen, Share2, Edit3, Trash2, Plus, Zap
} from 'lucide-react';
import { getCoachExcelUrl, getCoachIcsUrl, getCoachWhatsAppMsg, deleteClass, applyException } from '../services/api';
import CoachDispatchModal from './CoachDispatchModal';
import TrainerPriorityMatrix from './TrainerPriorityMatrix';

const getTimeSlotSortMinutes = (timeSlotStr) => {
  if (!timeSlotStr) return 0;
  try {
    const match = timeSlotStr.match(/(\d{1,2}):(\d{2})\s*(AM|PM)/i);
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

const isMatchingCoach = (coachA, coachB) => {
  if (!coachA || !coachB) return false;
  const a = coachA.trim().toUpperCase();
  const b = coachB.trim().toUpperCase();
  if (a === b) return true;
  if ((a === 'BATHRI' || a === 'BATHRINATH') && (b === 'BATHRI' || b === 'BATHRINATH')) return true;
  if ((a === 'GURU' || a === 'GURUVANTHANA') && (b === 'GURU' || b === 'GURUVANTHANA')) return true;
  if ((a === 'DHAANUSH' || a === 'DHANUSH') && (b === 'DHAANUSH' || b === 'DHANUSH')) return true;
  return false;
};

export default function CoachWorkloadView({
  coachSummaries = [],
  detailedClasses = [],
  scheduleId,
  onOpenManualEdit,
  onRefreshSchedule
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [expandedCoach, setExpandedCoach] = useState(null);
  const [copiedCoach, setCopiedCoach] = useState(null);
  
  // Modal state
  const [dispatchCoachName, setDispatchCoachName] = useState(null);

  if (!coachSummaries || coachSummaries.length === 0) {
    return (
      <div className="glass-panel" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
        <p>No coach workload summary available. Please run the scheduling engine first.</p>
      </div>
    );
  }

  // Filter coach summaries safely
  const filteredSummaries = coachSummaries.filter(c => {
    const coachName = c.coach_name || '';
    const status = c.status || 'Optimal';
    const matchesSearch = coachName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.levels_taught && c.levels_taught.join(' ').toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesStatus = statusFilter === 'ALL' || status.includes(statusFilter);
    return matchesSearch && matchesStatus;
  });

  // Global Statistics Calculations with safe fallbacks
  const totalCoaches = coachSummaries.length;
  const totalHours = coachSummaries.reduce((acc, c) => acc + (c.total_hours || 0), 0);
  const totalClasses = coachSummaries.reduce((acc, c) => acc + (c.assigned_classes || c.classes_scheduled || 0), 0);
  const avgUtilization = Math.round(
    coachSummaries.reduce((acc, c) => acc + (c.utilization_pct || 0), 0) / (totalCoaches || 1)
  );

  const toggleExpand = (coachName) => {
    if (expandedCoach === coachName) {
      setExpandedCoach(null);
    } else {
      setExpandedCoach(coachName);
    }
  };

  const handleDeleteCoachClass = async (cls) => {
    if (!cls?.class_id) return;
    const confirmMsg = `Cancel and delete class on ${cls.date} at ${cls.time_slot} for Coach ${cls.coach_name}?\nAll assigned students will return to Attention Required shortfall immediately.`;
    if (!window.confirm(confirmMsg)) return;

    try {
      const month = cls.date ? cls.date.substring(0, 7) : '2026-10';
      await applyException({
        month,
        date: cls.date,
        time_slot: cls.time_slot,
        coach_name: cls.coach_name,
        class_id: cls.class_id,
        class_key: `${cls.date}||${cls.time_slot}||${cls.coach_name}`,
        action_type: 'delete',
        affected_student_ids: cls.student_ids || [],
        before: cls,
        after: null,
        subtype: 'manual',
        violated_rules: [],
        reason: 'Class removed from Coach Workload View by Administrator',
        created_by: 'Admin'
      });
    } catch (excErr) {
      console.warn("Exception deletion note:", excErr);
    }

    try {
      if (scheduleId) {
        await deleteClass(scheduleId, cls.class_id);
      }
    } catch (legErr) {
      console.warn("Legacy delete note:", legErr);
    }

    if (onRefreshSchedule) {
      await onRefreshSchedule();
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px', marginBottom: '24px' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '10px' }}>
            📊 Individual Coach Portals & Workload Timetables
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Full periodic timetables, interactive CRUD operations, student rosters, one-click Excel downloads, and WhatsApp dispatches per coach.
          </p>
        </div>

        {/* Global Metric Cards */}
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ background: 'var(--bg-secondary)', padding: '10px 16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <span style={{ fontSize: '0.7rem', color: '#d1d5db', display: 'block' }}>TOTAL COACHES</span>
            <strong style={{ fontSize: '1.2rem', color: '#fff' }}>{totalCoaches}</strong>
          </div>

          <div style={{ background: 'rgba(245, 158, 11, 0.15)', padding: '10px 16px', borderRadius: 'var(--radius-md)', border: '1px solid rgba(245, 158, 11, 0.4)' }}>
            <span style={{ fontSize: '0.7rem', color: '#fde68a', display: 'block' }}>TOTAL TEACHING HOURS</span>
            <strong style={{ fontSize: '1.2rem', color: 'var(--accent-gold)' }}>{totalHours} hrs</strong>
          </div>

          <div style={{ background: 'rgba(59, 130, 246, 0.15)', padding: '10px 16px', borderRadius: 'var(--radius-md)', border: '1px solid rgba(59, 130, 246, 0.4)' }}>
            <span style={{ fontSize: '0.7rem', color: '#bfdbfe', display: 'block' }}>AVG CAPACITY UTILIZATION</span>
            <strong style={{ fontSize: '1.2rem', color: 'var(--accent-blue)' }}>{avgUtilization}%</strong>
          </div>
        </div>
      </div>

      {/* Centralized Trainer Qualification & Priority Matrix (Single Source of Truth) */}
      <TrainerPriorityMatrix onPriorityChanged={onRefreshSchedule} />

      {/* Controls: Search and Status Filter */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px', marginBottom: '24px' }}>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ position: 'relative' }}>
            <Search size={16} style={{ position: 'absolute', left: '12px', top: '10px', color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Search coach by name or level..."
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
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            style={{
              padding: '8px 14px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              color: '#fff',
              fontSize: '0.85rem'
            }}
          >
            <option value="ALL">All Statuses</option>
            <option value="Optimal">Optimal</option>
            <option value="Under-Utilized">Under-Utilized</option>
            <option value="Capacity Exceeded">Capacity Exceeded (Overtime)</option>
          </select>
        </div>

        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          Showing {filteredSummaries.length} of {totalCoaches} coaches
        </span>
      </div>

      {/* COACH INDIVIDUAL SECTIONS & CARDS */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {filteredSummaries.map((coach, index) => {
          const isExpanded = expandedCoach === coach.coach_name;
          const isCopied = copiedCoach === coach.coach_name;
          const status = coach.status || 'Optimal';
          const statusColor = coach.status_color || '#10b981';
          const assignedClasses = coach.assigned_classes ?? coach.classes_scheduled ?? 0;
          const totalCoachHours = coach.total_hours ?? assignedClasses;
          const utilPct = coach.utilization_pct ?? 0;

          // Find all classes assigned to this coach using robust matching
          const coachClasses = (detailedClasses || []).filter(
            cls => isMatchingCoach(cls.coach_name, coach.coach_name)
          );

          // Sort classes chronologically by Date -> Time Slot
          coachClasses.sort((a, b) => {
            const dateComp = (a.date || '').localeCompare(b.date || '');
            if (dateComp !== 0) return dateComp;
            return getTimeSlotSortMinutes(a.time_slot) - getTimeSlotSortMinutes(b.time_slot);
          });

          const excelUrl = getCoachExcelUrl(scheduleId, coach.coach_name);

          return (
            <div
              key={index}
              style={{
                background: 'var(--bg-secondary)',
                borderRadius: 'var(--radius-md)',
                border: status.includes('Exceeded')
                  ? '1px solid #ef4444'
                  : isExpanded
                    ? '1px solid var(--accent-gold)'
                    : '1px solid var(--border-color)',
                overflow: 'hidden'
              }}
            >
              {/* Coach Summary Banner Header */}
              <div
                style={{
                  padding: '18px 24px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: '16px',
                  background: 'rgba(0,0,0,0.2)'
                }}
              >
                {/* Left: Coach Identity & Badges */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                  <div
                    style={{
                      width: '44px',
                      height: '44px',
                      borderRadius: '50%',
                      background: 'var(--accent-gold)',
                      color: '#000',
                      fontWeight: 800,
                      fontSize: '1.2rem',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      boxShadow: '0 0 12px rgba(234, 179, 8, 0.4)'
                    }}
                  >
                    {(coach.coach_name || 'C').charAt(0).toUpperCase()}
                  </div>

                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#fff' }}>
                        Coach {coach.coach_name}
                      </h3>
                      <span
                        className="badge"
                        style={{
                          background: statusColor + '22',
                          color: statusColor,
                          border: `1px solid ${statusColor}`,
                          fontSize: '0.75rem',
                          padding: '3px 10px'
                        }}
                      >
                        {status}
                      </span>
                    </div>

                    <div style={{ display: 'flex', gap: '16px', marginTop: '6px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                      <span>📚 Assigned: <strong style={{ color: '#fff' }}>{assignedClasses} classes</strong> ({totalCoachHours} hrs)</span>
                      <span>👥 Student Reach: <strong style={{ color: 'var(--accent-gold)' }}>{coach.total_student_reach || coach.unique_students || 0} students</strong></span>
                      <span>Target: <strong style={{ color: '#fff' }}>{coach.monthly_capacity_max || 100} max/mo</strong></span>
                    </div>
                  </div>
                </div>

                {/* Center: Utilization Progress Bar */}
                <div style={{ minWidth: '180px', flex: 1, maxWidth: '260px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '4px' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>Utilization</span>
                    <strong style={{ color: statusColor }}>{utilPct}%</strong>
                  </div>
                  <div style={{ width: '100%', height: '8px', background: 'rgba(255,255,255,0.1)', borderRadius: '4px', overflow: 'hidden' }}>
                    <div
                      style={{
                        width: `${Math.min(utilPct, 100)}%`,
                        height: '100%',
                        background: statusColor,
                        transition: 'width 0.3s ease'
                      }}
                    />
                  </div>
                </div>

                {/* Right: Actions Bar & Interactive CRUD */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                  {/* + Add Class for this Coach */}
                  <button
                    onClick={() => {
                      if (onOpenManualEdit) {
                        onOpenManualEdit({
                          coach_name: coach.coach_name,
                          date: '2026-10-01',
                          time_slot: '06:00 PM - 07:00 PM',
                          student_level: (coach.levels_taught && coach.levels_taught[0]) || 'Beginner 1',
                          batch_type: 'G',
                          student_ids: [],
                          student_names: []
                        });
                      }
                    }}
                    className="btn btn-secondary"
                    style={{ padding: '6px 10px', fontSize: '0.775rem', borderColor: 'var(--accent-gold)', color: 'var(--accent-gold)', display: 'flex', alignItems: 'center', gap: '4px' }}
                    title={`Create a new class for Coach ${coach.coach_name}`}
                  >
                    <Plus size={14} /> Add Class
                  </button>

                  {/* Dispatch Modal Opener */}
                  <button
                    onClick={() => setDispatchCoachName(coach.coach_name)}
                    className="btn btn-secondary"
                    style={{ padding: '6px 12px', fontSize: '0.775rem', borderColor: 'var(--accent-gold)', color: 'var(--accent-gold)', display: 'flex', alignItems: 'center', gap: '6px' }}
                    title="Dispatch schedule via WhatsApp, .ics Calendar, Excel, or PDF"
                  >
                    <Share2 size={14} /> Dispatch & Share
                  </button>

                  {/* iCalendar (.ics) Direct Sync */}
                  <a
                    href={getCoachIcsUrl(scheduleId, coach.coach_name)}
                    download={`mighty_knight_${coach.coach_name}_calendar.ics`}
                    className="btn btn-secondary"
                    style={{ textDecoration: 'none', color: '#fff', padding: '6px 10px', fontSize: '0.775rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                    title="Download .ics File to sync with Google Calendar / Outlook"
                  >
                    <Calendar size={14} style={{ color: 'var(--accent-blue)' }} /> .ics Sync
                  </a>

                  {/* Excel Export Button */}
                  <a
                    href={excelUrl}
                    download={`mighty_knight_${coach.coach_name}_schedule.xlsx`}
                    className="btn btn-secondary"
                    style={{ textDecoration: 'none', color: '#fff', padding: '6px 10px', fontSize: '0.775rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                    title="Download Excel Timetable & Student Roster for this Coach"
                  >
                    <Download size={14} /> Excel
                  </a>

                  {/* Expand / Collapse Timetable Toggle */}
                  <button
                    onClick={() => toggleExpand(coach.coach_name)}
                    className="btn btn-primary"
                    style={{ padding: '6px 12px', fontSize: '0.775rem', display: 'flex', alignItems: 'center', gap: '6px' }}
                  >
                    {isExpanded ? 'Hide Timetable' : 'View Timetable'}
                    {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>
                </div>
              </div>

              {/* EXPANDABLE SECTION: Detailed Timetable & Student Rosters with Interactive CRUD */}
              {isExpanded && (
                <div style={{ padding: '20px 24px', borderTop: '1px solid var(--border-color)', background: 'var(--bg-card)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '10px' }}>
                    <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--accent-gold)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <BookOpen size={16} /> Detailed Periodic Timetable & Student Rosters for Coach {coach.coach_name} ({coachClasses.length} sessions)
                    </h4>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      Click "Edit Class" to modify or "Cancel Class" to immediately update real-time attendance & Attention Required
                    </span>
                  </div>

                  {coachClasses.length === 0 ? (
                    <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', fontStyle: 'italic', background: 'rgba(0,0,0,0.2)', borderRadius: '8px' }}>
                      No active class sessions currently assigned to Coach {coach.coach_name}. Use "+ Add Class" above to create one.
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '16px' }}>
                      {coachClasses.map((cls, idx) => (
                        <div
                          key={cls.class_id || idx}
                          style={{
                            background: 'var(--bg-secondary)',
                            borderRadius: 'var(--radius-sm)',
                            border: cls.is_compensation ? '1px solid rgba(251, 191, 36, 0.45)' : '1px solid var(--border-color)',
                            padding: '16px',
                            display: 'flex',
                            flexDirection: 'column',
                            justifyContent: 'space-between',
                            gap: '12px'
                          }}
                        >
                          <div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                              <span style={{ fontSize: '0.875rem', fontWeight: 800, color: '#fff' }}>
                                {cls.day} ({cls.date})
                              </span>
                              <span className="badge badge-gold" style={{ fontSize: '0.7rem' }}>
                                Batch {cls.batch_type}
                              </span>
                            </div>

                            <div style={{ fontSize: '0.825rem', color: 'var(--accent-blue)', fontWeight: 600, marginBottom: '6px' }}>
                              ⏰ {cls.time_slot}
                            </div>

                            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '10px' }}>
                              🎓 Level: <strong style={{ color: '#fff' }}>{cls.student_level}</strong>
                            </div>

                            {/* Student Roster Box */}
                            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.05)' }}>
                              <div style={{ fontSize: '0.725rem', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '6px', display: 'flex', justifyContent: 'space-between' }}>
                                <span>STUDENT ROSTER</span>
                                <span>{(cls.student_ids || []).length} Students</span>
                              </div>
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                {(cls.student_names || []).map((sname, sidx) => (
                                  <div key={sidx} style={{ fontSize: '0.775rem', color: '#fff', display: 'flex', justifyContent: 'space-between' }}>
                                    <span>• {sname}</span>
                                    <span style={{ fontSize: '0.7rem', color: 'var(--accent-gold)' }}>ID: {cls.student_ids[sidx]}</span>
                                  </div>
                                ))}
                                {(!cls.student_names || cls.student_names.length === 0) && (
                                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>Open / Unassigned</span>
                                )}
                              </div>
                            </div>
                          </div>

                          {/* INTERACTIVE CLASS CRUD ACTION BUTTONS */}
                          <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '10px' }}>
                            <button
                              onClick={() => onOpenManualEdit && onOpenManualEdit(cls)}
                              className="btn btn-secondary"
                              style={{ padding: '5px 10px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                              title="Edit this class session"
                            >
                              <Edit3 size={12} /> Edit Class
                            </button>
                            <button
                              onClick={() => handleDeleteCoachClass(cls)}
                              className="btn"
                              style={{
                                padding: '5px 10px',
                                fontSize: '0.75rem',
                                background: 'rgba(239, 68, 68, 0.15)',
                                border: '1px solid rgba(239, 68, 68, 0.4)',
                                color: '#f87171',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '4px'
                              }}
                              title="Cancel and remove this class"
                            >
                              <Trash2 size={12} /> Cancel Class
                            </button>
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

      {/* Interactive Coach Schedule Dispatch Modal */}
      <CoachDispatchModal
        isOpen={Boolean(dispatchCoachName)}
        onClose={() => setDispatchCoachName(null)}
        coachName={dispatchCoachName}
        scheduleId={scheduleId}
      />
    </div>
  );
}
