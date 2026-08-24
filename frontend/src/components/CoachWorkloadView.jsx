import React, { useState } from 'react';
import { Clock, Users, Award, AlertTriangle, CheckCircle2, Search, BarChart2, Download, MessageSquare, ChevronDown, ChevronUp, Copy, Check, Calendar, BookOpen } from 'lucide-react';
import { getCoachExcelUrl, getCoachWhatsAppMsg } from '../services/api';

export default function CoachWorkloadView({ coachSummaries, detailedClasses, scheduleId }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [expandedCoach, setExpandedCoach] = useState(null);
  const [copiedCoach, setCopiedCoach] = useState(null);

  if (!coachSummaries || coachSummaries.length === 0) {
    return (
      <div className="glass-panel" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
        <p>No coach workload summary available. Please run the scheduling engine first.</p>
      </div>
    );
  }

  // Filter coach summaries
  const filteredSummaries = coachSummaries.filter(c => {
    const matchesSearch = c.coach_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.levels_taught && c.levels_taught.join(' ').toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesStatus = statusFilter === 'ALL' || c.status.includes(statusFilter);
    return matchesSearch && matchesStatus;
  });

  // Global Statistics Calculations
  const totalCoaches = coachSummaries.length;
  const totalHours = coachSummaries.reduce((acc, c) => acc + c.total_hours, 0);
  const totalClasses = coachSummaries.reduce((acc, c) => acc + c.assigned_classes, 0);
  const avgUtilization = Math.round(
    coachSummaries.reduce((acc, c) => acc + c.utilization_pct, 0) / (totalCoaches || 1)
  );

  const toggleExpand = (coachName) => {
    if (expandedCoach === coachName) {
      setExpandedCoach(null);
    } else {
      setExpandedCoach(coachName);
    }
  };

  const handleCopyWhatsApp = async (coachName) => {
    try {
      const res = await getCoachWhatsAppMsg(scheduleId, coachName);
      if (res && res.whatsapp_text) {
        await navigator.clipboard.writeText(res.whatsapp_text);
        setCopiedCoach(coachName);
        setTimeout(() => setCopiedCoach(null), 3000);
      }
    } catch (err) {
      alert('Failed to format WhatsApp text: ' + err.message);
    }
  };

  const handleOpenWhatsAppWeb = async (coachName) => {
    try {
      const res = await getCoachWhatsAppMsg(scheduleId, coachName);
      if (res && res.whatsapp_text) {
        const encoded = encodeURIComponent(res.whatsapp_text);
        window.open(`https://wa.me/?text=${encoded}`, '_blank');
      }
    } catch (err) {
      alert('Failed to open WhatsApp: ' + err.message);
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
            Full periodic timetables, student rosters, one-click Excel downloads, and WhatsApp dispatches per coach.
          </p>
        </div>

        {/* Global Metric Cards */}
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
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

          // Find all classes assigned to this coach
          const coachClasses = (detailedClasses || []).filter(
            cls => (cls.coach_name || '').trim().toLowerCase() === (coach.coach_name || '').trim().toLowerCase()
          );

          // Sort classes by date & time
          coachClasses.sort((a, b) => (a.date + a.time_slot).localeCompare(b.date + b.time_slot));

          const excelUrl = getCoachExcelUrl(scheduleId, coach.coach_name);

          return (
            <div
              key={index}
              style={{
                background: 'var(--bg-secondary)',
                borderRadius: 'var(--radius-md)',
                border: coach.status.includes('Exceeded')
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
                    {coach.coach_name.charAt(0).toUpperCase()}
                  </div>

                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#fff' }}>
                        Coach {coach.coach_name}
                      </h3>
                      <span
                        className="badge"
                        style={{
                          background: coach.status_color + '22',
                          color: coach.status_color,
                          border: `1px solid ${coach.status_color}`,
                          fontSize: '0.75rem',
                          padding: '3px 10px'
                        }}
                      >
                        {coach.status}
                      </span>
                    </div>

                    <div style={{ display: 'flex', gap: '16px', marginTop: '6px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                      <span>📚 Assigned: <strong style={{ color: '#fff' }}>{coach.assigned_classes} classes</strong> ({coach.total_hours} hrs)</span>
                      <span>👥 Student Reach: <strong style={{ color: 'var(--accent-gold)' }}>{coach.total_student_reach || coach.unique_students} students</strong></span>
                      <span>Target: <strong style={{ color: '#fff' }}>{coach.monthly_capacity_max} max/wk</strong></span>
                    </div>
                  </div>
                </div>

                {/* Center: Utilization Progress Bar */}
                <div style={{ minWidth: '180px', flex: 1, maxWidth: '260px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '4px' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>Utilization</span>
                    <strong style={{ color: coach.status_color }}>{coach.utilization_pct}%</strong>
                  </div>
                  <div style={{ width: '100%', height: '8px', background: 'rgba(255,255,255,0.1)', borderRadius: '4px', overflow: 'hidden' }}>
                    <div
                      style={{
                        width: `${Math.min(coach.utilization_pct, 100)}%`,
                        height: '100%',
                        background: coach.status_color,
                        transition: 'width 0.3s ease'
                      }}
                    />
                  </div>
                </div>

                {/* Right: Actions Bar */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                  {/* Excel Export Button */}
                  <a
                    href={excelUrl}
                    download={`mighty_knight_${coach.coach_name}_schedule.xlsx`}
                    className="btn btn-secondary"
                    style={{ textDecoration: 'none', color: '#fff', padding: '6px 12px', fontSize: '0.775rem', display: 'flex', alignItems: 'center', gap: '6px' }}
                    title="Download Excel Timetable & Student Roster for this Coach"
                  >
                    <Download size={14} /> Excel Sheet
                  </a>

                  {/* WhatsApp Direct Open */}
                  <button
                    onClick={() => handleOpenWhatsAppWeb(coach.coach_name)}
                    className="btn btn-secondary"
                    style={{ padding: '6px 12px', fontSize: '0.775rem', borderColor: '#25D366', color: '#25D366', display: 'flex', alignItems: 'center', gap: '6px' }}
                    title="Send Schedule via WhatsApp"
                  >
                    <MessageSquare size={14} /> WhatsApp
                  </button>

                  {/* Copy Text */}
                  <button
                    onClick={() => handleCopyWhatsApp(coach.coach_name)}
                    className="btn btn-secondary"
                    style={{ padding: '6px 10px', fontSize: '0.775rem' }}
                    title="Copy formatted WhatsApp text"
                  >
                    {isCopied ? <Check size={14} style={{ color: '#10b981' }} /> : <Copy size={14} />}
                  </button>

                  {/* Expand / Collapse Timetable Toggle */}
                  <button
                    onClick={() => toggleExpand(coach.coach_name)}
                    className="btn btn-primary"
                    style={{ padding: '6px 14px', fontSize: '0.775rem', display: 'flex', alignItems: 'center', gap: '6px' }}
                  >
                    <Calendar size={14} />
                    {isExpanded ? 'Hide Timetable' : 'View Timetable'}
                    {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>
                </div>
              </div>

              {/* EXPANDABLE SECTION: Detailed Timetable & Student Rosters */}
              {isExpanded && (
                <div style={{ padding: '20px 24px', borderTop: '1px solid var(--border-color)', background: 'var(--bg-card)' }}>
                  <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--accent-gold)', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <BookOpen size={16} /> Detailed Periodic Timetable & Student Rosters for Coach {coach.coach_name}
                  </h4>

                  {coachClasses.length === 0 ? (
                    <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                      No active class sessions currently assigned to Coach {coach.coach_name}.
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '14px' }}>
                      {coachClasses.map((cls, idx) => (
                        <div
                          key={idx}
                          style={{
                            background: 'var(--bg-secondary)',
                            borderRadius: 'var(--radius-sm)',
                            border: '1px solid var(--border-color)',
                            padding: '14px'
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                            <span style={{ fontSize: '0.85rem', fontWeight: 800, color: '#fff' }}>
                              {cls.day} ({cls.date})
                            </span>
                            <span className="badge badge-gold" style={{ fontSize: '0.7rem' }}>
                              Batch {cls.batch_type}
                            </span>
                          </div>

                          <div style={{ fontSize: '0.8rem', color: 'var(--accent-blue)', fontWeight: 600, marginBottom: '6px' }}>
                            ⏰ {cls.time_slot}
                          </div>

                          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '10px' }}>
                            🎓 Level: <strong style={{ color: '#fff' }}>{cls.student_level}</strong>
                          </div>

                          {/* Student Roster Box */}
                          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.05)' }}>
                            <div style={{ fontSize: '0.725rem', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '6px', display: 'flex', justifyContent: 'space-between' }}>
                              <span>STUDENT ROSTER</span>
                              <span>{cls.student_ids.length} Students</span>
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                              {cls.student_names.map((sname, sidx) => (
                                <div key={sidx} style={{ fontSize: '0.775rem', color: '#fff', display: 'flex', justifyContent: 'space-between' }}>
                                  <span>• {sname}</span>
                                  <span style={{ fontSize: '0.7rem', color: 'var(--accent-gold)' }}>ID: {cls.student_ids[sidx]}</span>
                                </div>
                              ))}
                            </div>
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
    </div>
  );
}
