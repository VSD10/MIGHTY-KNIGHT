import React, { useState } from 'react';
import { Search, Download, Calendar, User, Award, CheckCircle, ShieldCheck, Sparkles, Layers, Image, FolderArchive, Clock, BookOpen, Palette, Check } from 'lucide-react';
import html2canvas from 'html2canvas';
import JSZip from 'jszip';
import { getStudentIcsUrl } from '../services/api';

export default function StudentScheduleView({ studentScheduleData, detailedClasses, scheduleId }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [downloadingId, setDownloadingId] = useState(null);
  const [isBulkDownloading, setIsBulkDownloading] = useState(false);
  const [zipProgress, setZipProgress] = useState('');
  const [selectedTheme, setSelectedTheme] = useState('executive'); // 'executive', 'royal', 'timeline'

  // If studentScheduleData from output5 is passed:
  let studentSchedules = studentScheduleData?.student_schedules || [];

  // Fallback: If output5 endpoint data is not present, compute from detailedClasses
  if ((!studentSchedules || studentSchedules.length === 0) && detailedClasses && detailedClasses.length > 0) {
    const studentMap = {};
    detailedClasses.forEach(cls => {
      const sIds = cls.student_ids || [];
      const sNames = cls.student_names || [];
      sIds.forEach((sid, idx) => {
        const sname = sNames[idx] || sid;
        if (!studentMap[sid]) {
          studentMap[sid] = {
            student_id: sid,
            student_name: sname,
            student_level: cls.student_level || 'Basic 1',
            batch_type: cls.batch_type || 'G',
            sessions: []
          };
        }
        // Format date string to DD/MM/YYYY if YYYY-MM-DD
        let formattedDate = cls.date;
        if (cls.date && cls.date.includes('-')) {
          const parts = cls.date.split('-');
          if (parts.length === 3) {
            formattedDate = `${parts[2]}/${parts[1]}/${parts[0]}`;
          }
        }
        // Format time string to start time e.g. 4:00 PM
        let formattedTime = cls.time_slot || '';
        const tMatch = formattedTime.match(/(\d{1,2}:\d{2}\s*[AP]M)/i);
        if (tMatch) {
          formattedTime = tMatch[1];
        }
        if (formattedTime.startsWith('0') && formattedTime.length > 1 && !isNaN(formattedTime[1])) {
          formattedTime = formattedTime.substring(1);
        }

        studentMap[sid].sessions.push({
          class_id: cls.class_id,
          date: formattedDate,
          raw_date: cls.date,
          day: cls.day,
          time: formattedTime,
          full_time_slot: cls.time_slot,
          coach: cls.coach_name,
          session: 'Chess',
          student_level: cls.student_level,
          batch_type: cls.batch_type
        });
      });
    });

    studentSchedules = Object.values(studentMap).map(s => ({
      ...s,
      total_sessions: s.sessions.length
    }));
    studentSchedules.sort((a, b) => a.student_name.localeCompare(b.student_name));
  }

  if (!studentSchedules || studentSchedules.length === 0) {
    return (
      <div className="glass-panel" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
        <p>No student schedules generated yet. Please select a date range and click "Run Engine".</p>
      </div>
    );
  }

  // Filter students by search query
  const filteredStudents = studentSchedules.filter(s =>
    (s.student_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (s.student_id || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (s.student_level || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getCanvasBg = () => {
    if (selectedTheme === 'royal') return '#0f172a';
    if (selectedTheme === 'timeline') return '#090d16';
    return '#0b0f19';
  };

  const handleDownloadSingleImage = async (studentId, studentName) => {
    const element = document.getElementById(`student-card-export-${studentId}`);
    if (!element) return;
    setDownloadingId(studentId);
    try {
      const canvas = await html2canvas(element, {
        scale: 2,
        useCORS: true,
        backgroundColor: getCanvasBg(),
        logging: false,
      });
      const dataUrl = canvas.toDataURL('image/png');
      const link = document.createElement('a');
      const safeName = studentName.replace(/\s+/g, '_');
      link.download = `Mighty_Knight_Schedule_${safeName}_${selectedTheme}.png`;
      link.href = dataUrl;
      link.click();
    } catch (err) {
      console.error('Failed to capture schedule image:', err);
      alert('Error generating image for ' + studentName + ': ' + err.message);
    } finally {
      setDownloadingId(null);
    }
  };

  const handleDownloadAllImagesZip = async () => {
    if (filteredStudents.length === 0) return;
    setIsBulkDownloading(true);
    setZipProgress('Starting...');
    try {
      const zip = new JSZip();
      const folder = zip.folder("Student_Schedules");

      let completedCount = 0;
      for (const student of filteredStudents) {
        completedCount++;
        setZipProgress(`Rendering ${completedCount}/${filteredStudents.length}: ${student.student_name}`);

        const element = document.getElementById(`student-card-export-${student.student_id}`);
        if (element) {
          const canvas = await html2canvas(element, {
            scale: 2,
            useCORS: true,
            backgroundColor: getCanvasBg(),
            logging: false,
          });
          const base64Data = canvas.toDataURL('image/png').replace(/^data:image\/png;base64,/, '');
          const safeName = student.student_name.replace(/\s+/g, '_');
          folder.file(`Mighty_Knight_Schedule_${safeName}_${student.student_id}.png`, base64Data, { base64: true });
        }
      }

      setZipProgress('Zipping files...');
      const blob = await zip.generateAsync({ type: 'blob' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `Mighty_Knight_Student_Schedules_${selectedTheme}_${new Date().toISOString().slice(0, 10)}.zip`;
      link.click();
      URL.revokeObjectURL(link.href);
    } catch (err) {
      console.error('Failed to generate ZIP archive:', err);
      alert('Error generating ZIP file: ' + err.message);
    } finally {
      setIsBulkDownloading(false);
      setZipProgress('');
    }
  };

  const totalStudents = studentSchedules.length;
  const totalAssignedSessions = studentSchedules.reduce((acc, s) => acc + s.total_sessions, 0);

  return (
    <div className="glass-panel" style={{ padding: '24px' }}>
      {/* Header bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px', marginBottom: '24px', borderBottom: '1px solid var(--border-color)', paddingBottom: '16px' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '10px' }}>
            🎓 Output 5 — Student Schedules
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Individual student schedule images automatically generated from engine final assignments. Select UI themes below & export PNGs/ZIP.
          </p>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <div style={{ background: 'var(--bg-secondary)', padding: '8px 14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', fontSize: '0.8rem' }}>
            <span style={{ color: 'var(--text-muted)' }}>Total Students: </span>
            <strong style={{ color: 'var(--accent-gold)' }}>{totalStudents}</strong>
          </div>
          <div style={{ background: 'var(--bg-secondary)', padding: '8px 14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', fontSize: '0.8rem' }}>
            <span style={{ color: 'var(--text-muted)' }}>Assigned Sessions: </span>
            <strong style={{ color: 'var(--accent-blue)' }}>{totalAssignedSessions}</strong>
          </div>

          <button
            onClick={handleDownloadAllImagesZip}
            disabled={isBulkDownloading}
            className="btn btn-primary"
            style={{ padding: '10px 18px', background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)', color: '#fff', fontWeight: 700, fontSize: '0.875rem', display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            <FolderArchive size={18} />
            {isBulkDownloading ? (zipProgress || 'Packaging ZIP Archive...') : 'Download All Student Images (.zip)'}
          </button>
        </div>
      </div>

      {/* UI Theme Switcher Panel & Search */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '24px', background: 'rgba(0,0,0,0.25)', padding: '14px 18px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
        {/* Left: UI Theme Chooser */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--accent-gold)', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Palette size={16} /> CHOOSE TIMETABLE UI STYLE:
          </span>

          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => setSelectedTheme('executive')}
              style={{
                padding: '6px 14px',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.8rem',
                fontWeight: 700,
                cursor: 'pointer',
                border: selectedTheme === 'executive' ? '1px solid #fbbf24' : '1px solid var(--border-color)',
                background: selectedTheme === 'executive' ? 'linear-gradient(135deg, rgba(251,191,36,0.2) 0%, rgba(217,119,6,0.2) 100%)' : 'var(--bg-secondary)',
                color: selectedTheme === 'executive' ? '#fbbf24' : 'var(--text-secondary)',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              {selectedTheme === 'executive' && <Check size={14} />}
              👑 Executive Dark Gold
            </button>

            <button
              onClick={() => setSelectedTheme('royal')}
              style={{
                padding: '6px 14px',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.8rem',
                fontWeight: 700,
                cursor: 'pointer',
                border: selectedTheme === 'royal' ? '1px solid #38bdf8' : '1px solid var(--border-color)',
                background: selectedTheme === 'royal' ? 'linear-gradient(135deg, rgba(56,189,248,0.2) 0%, rgba(2,132,199,0.2) 100%)' : 'var(--bg-secondary)',
                color: selectedTheme === 'royal' ? '#38bdf8' : 'var(--text-secondary)',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              {selectedTheme === 'royal' && <Check size={14} />}
              🏆 Royal Navy Badge
            </button>

            <button
              onClick={() => setSelectedTheme('timeline')}
              style={{
                padding: '6px 14px',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.8rem',
                fontWeight: 700,
                cursor: 'pointer',
                border: selectedTheme === 'timeline' ? '1px solid #10b981' : '1px solid var(--border-color)',
                background: selectedTheme === 'timeline' ? 'linear-gradient(135deg, rgba(16,185,129,0.2) 0%, rgba(4,120,87,0.2) 100%)' : 'var(--bg-secondary)',
                color: selectedTheme === 'timeline' ? '#10b981' : 'var(--text-secondary)',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              {selectedTheme === 'timeline' && <Check size={14} />}
              ⏱ Modern Timeline Cards
            </button>
          </div>
        </div>

        {/* Right: Search Filter */}
        <div style={{ position: 'relative', width: '280px' }}>
          <Search size={16} style={{ position: 'absolute', left: '12px', top: '10px', color: 'var(--text-muted)' }} />
          <input
            type="text"
            placeholder="Search student..."
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
      </div>

      {/* STUDENT SCHEDULE CARDS LIST */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
        {filteredStudents.map((student) => {
          const isDownloading = downloadingId === student.student_id;

          return (
            <div
              key={student.student_id}
              style={{
                background: 'var(--bg-secondary)',
                borderRadius: 'var(--radius-lg)',
                border: '1px solid var(--border-color)',
                overflow: 'hidden',
                boxShadow: '0 10px 30px rgba(0,0,0,0.4)'
              }}
            >
              {/* Outer Control Header */}
              <div
                style={{
                  padding: '16px 24px',
                  background: 'rgba(0,0,0,0.3)',
                  borderBottom: '1px solid var(--border-color)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: '12px'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div
                    style={{
                      width: '40px',
                      height: '40px',
                      borderRadius: '50%',
                      background: 'linear-gradient(135deg, #fbbf24 0%, #d97706 100%)',
                      color: '#000',
                      fontWeight: 800,
                      fontSize: '1.1rem',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      boxShadow: '0 0 12px rgba(251, 191, 36, 0.4)'
                    }}
                  >
                    {student.student_name.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      Student: {student.student_name}
                      <span className="badge badge-gold" style={{ fontSize: '0.75rem', padding: '2px 8px' }}>
                        ID: {student.student_id}
                      </span>
                    </h3>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                      Level: <strong style={{ color: '#fff' }}>{student.student_level}</strong> · Sessions: <strong style={{ color: 'var(--accent-gold)' }}>{student.total_sessions}</strong>
                    </div>
                  </div>
                </div>

                {/* Individual Export Actions */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                  <a
                    href={getStudentIcsUrl(scheduleId, student.student_id)}
                    download={`mighty_knight_student_${student.student_id}_calendar.ics`}
                    className="btn btn-secondary"
                    style={{
                      padding: '8px 14px',
                      color: '#fff',
                      fontSize: '0.825rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      textDecoration: 'none',
                      borderColor: 'var(--border-color)'
                    }}
                    title="Download .ics Calendar Sync file to automatically add all classes to Google, Apple, or Outlook Calendar"
                  >
                    <Calendar size={15} style={{ color: 'var(--accent-blue)' }} /> .ics Calendar Sync
                  </a>

                  <button
                    onClick={() => handleDownloadSingleImage(student.student_id, student.student_name)}
                    disabled={isDownloading}
                    className="btn btn-secondary"
                    style={{
                      padding: '8px 16px',
                      borderColor: 'var(--accent-gold)',
                      color: 'var(--accent-gold)',
                      fontWeight: 700,
                      fontSize: '0.825rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}
                  >
                    <Image size={15} />
                    {isDownloading ? 'Capturing Image...' : `Download Image (.png)`}
                  </button>
                </div>
              </div>

              {/* DYNAMIC STYLED CANVAS DOM FOR PNG EXPORT */}
              <div id={`student-card-export-${student.student_id}`}>
                {/* THEME 1: EXECUTIVE DARK GOLD */}
                {selectedTheme === 'executive' && (
                  <div
                    style={{
                      padding: '32px',
                      background: '#0b101d',
                      color: '#f8fafc',
                      fontFamily: "'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
                      position: 'relative'
                    }}
                  >
                    {/* Top Gold Gradient Accent Line */}
                    <div style={{ height: '3px', background: 'linear-gradient(90deg, #d97706 0%, #fbbf24 50%, #d97706 100%)', borderRadius: '2px', marginBottom: '24px' }} />

                    {/* Header Banner */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                        <div
                          style={{
                            width: '54px',
                            height: '54px',
                            borderRadius: '16px',
                            background: 'linear-gradient(135deg, #fbbf24 0%, #d97706 100%)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            boxShadow: '0 4px 14px rgba(251, 191, 36, 0.45)',
                            padding: '4px'
                          }}
                        >
                          <img src="/CHESS.png" alt="Mighty Knight Logo" style={{ width: '42px', height: '42px', objectFit: 'contain' }} />
                        </div>
                        <div>
                          <div style={{ fontSize: '1.4rem', fontWeight: 900, color: '#fbbf24', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                            Mighty Knight Chess Academy
                          </div>
                          <div style={{ fontSize: '0.85rem', color: '#94a3b8', fontWeight: 600, marginTop: '2px' }}>
                            Official Student Master Schedule
                          </div>
                        </div>
                      </div>

                      {/* Student Info Pill */}
                      <div style={{ background: '#161f33', border: '1px solid #232f48', borderRadius: '14px', padding: '12px 20px', textAlign: 'right' }}>
                        <div style={{ fontSize: '1.25rem', fontWeight: 900, color: '#ffffff' }}>
                          {student.student_name}
                        </div>
                        <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '3px' }}>
                          ID: <span style={{ color: '#fbbf24', fontWeight: 800 }}>{student.student_id}</span> · Level: <span style={{ color: '#fbbf24', fontWeight: 800 }}>{student.student_level}</span>
                        </div>
                      </div>
                    </div>

                    {/* Schedule Table */}
                    {student.sessions.length === 0 ? (
                      <div style={{ padding: '24px', textAlign: 'center', color: '#94a3b8', fontStyle: 'italic', background: '#121a2b', borderRadius: '12px' }}>
                        No sessions scheduled for this period.
                      </div>
                    ) : (
                      <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: '0', background: '#0e1626', borderRadius: '14px', overflow: 'hidden', border: '1px solid #1c273e' }}>
                        <thead>
                          <tr style={{ background: '#121a2b', color: '#fbbf24', textAlign: 'left' }}>
                            <th style={{ padding: '14px 14px', fontWeight: 800, fontSize: '0.85rem', letterSpacing: '0.06em', width: '45px', textAlign: 'center' }}>#</th>
                            <th style={{ padding: '14px 18px', fontWeight: 800, fontSize: '0.85rem', letterSpacing: '0.06em' }}>DATE</th>
                            <th style={{ padding: '14px 18px', fontWeight: 800, fontSize: '0.85rem', letterSpacing: '0.06em' }}>DAY</th>
                            <th style={{ padding: '14px 18px', fontWeight: 800, fontSize: '0.85rem', letterSpacing: '0.06em' }}>TIME</th>
                            <th style={{ padding: '14px 18px', fontWeight: 800, fontSize: '0.85rem', letterSpacing: '0.06em' }}>COACH</th>
                            <th style={{ padding: '14px 18px', fontWeight: 800, fontSize: '0.85rem', letterSpacing: '0.06em' }}>SESSION</th>
                          </tr>
                        </thead>
                        <tbody>
                          {student.sessions.map((sess, idx) => (
                            <tr key={idx} style={{ borderBottom: '1px solid #1a2438', background: idx % 2 === 0 ? '#0e1626' : '#0b101d' }}>
                              <td style={{ padding: '14px 14px', fontWeight: 800, color: '#fbbf24', fontSize: '0.9rem', textAlign: 'center' }}>
                                {idx + 1}
                              </td>
                              <td style={{ padding: '14px 18px', fontWeight: 800, color: '#ffffff', fontSize: '0.925rem' }}>
                                {sess.date}
                              </td>
                              <td style={{ padding: '14px 18px', color: '#e2e8f0', fontWeight: 600, fontSize: '0.9rem' }}>
                                {sess.day}
                              </td>
                              <td style={{ padding: '14px 18px' }}>
                                <span style={{ background: '#132845', color: '#38bdf8', border: '1px solid #1e4a7a', padding: '6px 14px', borderRadius: '8px', fontWeight: 800, fontSize: '0.85rem', display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                                  ⏰ {sess.full_time_slot || sess.time}
                                </span>
                              </td>
                              <td style={{ padding: '14px 18px' }}>
                                <span style={{ background: '#2a2012', color: '#fbbf24', border: '1px solid #543f1b', padding: '6px 14px', borderRadius: '8px', fontWeight: 800, fontSize: '0.85rem', display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                                  👤 {sess.coach}
                                </span>
                              </td>
                              <td style={{ padding: '14px 18px' }}>
                                <span style={{ background: '#112b23', color: '#34d399', border: '1px solid #1b5443', padding: '6px 14px', borderRadius: '8px', fontWeight: 800, fontSize: '0.85rem', display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                                  ♟ Chess ({sess.student_level})
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}

                    <div style={{ marginTop: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.775rem', color: '#64748b', borderTop: '1px solid #1a2438', paddingTop: '14px' }}>
                      <span>Mighty Knight Scheduling Engine • Official Schedule</span>
                      <span>Verified for Student {student.student_name}</span>
                    </div>
                  </div>
                )}

                {/* THEME 2: ROYAL NAVY BADGE */}
                {selectedTheme === 'royal' && (
                  <div
                    style={{
                      padding: '32px',
                      background: '#0f172a',
                      color: '#ffffff',
                      fontFamily: "'Segoe UI', Roboto, sans-serif"
                    }}
                  >
                    <div style={{ background: 'linear-gradient(135deg, #1e3a8a 0%, #1e1b4b 100%)', borderRadius: '14px', border: '2px solid #3b82f6', padding: '20px 24px', marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <div style={{ fontSize: '0.75rem', fontWeight: 800, color: '#60a5fa', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
                          Official Academy Dispatch
                        </div>
                        <div style={{ fontSize: '1.4rem', fontWeight: 900, color: '#ffffff', marginTop: '2px' }}>
                          MIGHTY KNIGHT CHESS
                        </div>
                      </div>

                      <div style={{ background: '#3b82f6', color: '#ffffff', padding: '10px 20px', borderRadius: '10px', fontWeight: 900, fontSize: '1.1rem', boxShadow: '0 4px 12px rgba(59,130,246,0.4)' }}>
                        {student.student_name}
                      </div>
                    </div>

                    <table style={{ width: '100%', borderCollapse: 'collapse', background: '#1e293b', borderRadius: '10px', overflow: 'hidden' }}>
                      <thead>
                        <tr style={{ background: '#2563eb', color: '#ffffff' }}>
                          <th style={{ padding: '12px 14px', textAlign: 'center', fontSize: '0.85rem', fontWeight: 800, width: '40px' }}>#</th>
                          <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '0.85rem', fontWeight: 800 }}>Date</th>
                          <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '0.85rem', fontWeight: 800 }}>Day</th>
                          <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '0.85rem', fontWeight: 800 }}>Time</th>
                          <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '0.85rem', fontWeight: 800 }}>Coach</th>
                          <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '0.85rem', fontWeight: 800 }}>Session</th>
                        </tr>
                      </thead>
                      <tbody>
                        {student.sessions.map((sess, idx) => (
                          <tr key={idx} style={{ borderBottom: '1px solid #334155', background: idx % 2 === 0 ? '#1e293b' : '#0f172a' }}>
                            <td style={{ padding: '12px 14px', fontWeight: 800, color: '#fbbf24', textAlign: 'center' }}>{idx + 1}</td>
                            <td style={{ padding: '12px 16px', fontWeight: 800, color: '#60a5fa' }}>{sess.date}</td>
                            <td style={{ padding: '12px 16px', fontWeight: 600, color: '#f8fafc' }}>{sess.day}</td>
                            <td style={{ padding: '12px 16px', fontWeight: 700, color: '#fbbf24' }}>{sess.time}</td>
                            <td style={{ padding: '12px 16px', fontWeight: 700, color: '#ffffff' }}>{sess.coach}</td>
                            <td style={{ padding: '12px 16px', fontWeight: 600, color: '#34d399' }}>{sess.session}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* THEME 3: MODERN TIMELINE CARDS */}
                {selectedTheme === 'timeline' && (
                  <div
                    style={{
                      padding: '32px',
                      background: '#090d16',
                      color: '#ffffff',
                      fontFamily: "'Segoe UI', Roboto, sans-serif"
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', borderBottom: '1px solid #1e293b', paddingBottom: '16px' }}>
                      <div>
                        <span style={{ fontSize: '0.75rem', fontWeight: 800, color: '#10b981', letterSpacing: '0.08em' }}>ACADEMY TIMELINE</span>
                        <h3 style={{ fontSize: '1.3rem', fontWeight: 900, color: '#ffffff' }}>Schedule for {student.student_name}</h3>
                      </div>
                      <div style={{ background: '#10b981', color: '#000', padding: '6px 14px', borderRadius: '20px', fontWeight: 800, fontSize: '0.8rem' }}>
                        {student.student_level}
                      </div>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {student.sessions.map((sess, idx) => (
                        <div
                          key={idx}
                          style={{
                            background: '#131c2e',
                            borderRadius: '10px',
                            border: '1px solid #1e293b',
                            padding: '14px 20px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            flexWrap: 'wrap',
                            gap: '12px'
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                            <div style={{ background: '#1e293b', padding: '8px 14px', borderRadius: '8px', textAlign: 'center', border: '1px solid #334155' }}>
                              <div style={{ fontSize: '0.75rem', fontWeight: 800, color: '#fbbf24', marginBottom: '2px' }}>Class #{idx + 1}</div>
                              <div style={{ fontSize: '0.9rem', fontWeight: 900, color: '#10b981' }}>{sess.date}</div>
                              <div style={{ fontSize: '0.7rem', color: '#94a3b8', fontWeight: 700 }}>{sess.day}</div>
                            </div>
                            <div>
                              <div style={{ fontSize: '1rem', fontWeight: 800, color: '#ffffff' }}>⏰ {sess.time}</div>
                              <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '2px' }}>Chess Class · Batch {sess.batch_type}</div>
                            </div>
                          </div>

                          <div style={{ background: 'rgba(251,191,36,0.15)', border: '1px solid rgba(251,191,36,0.3)', padding: '8px 16px', borderRadius: '8px', color: '#fbbf24', fontWeight: 800, fontSize: '0.85rem' }}>
                            Coach: {sess.coach}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
