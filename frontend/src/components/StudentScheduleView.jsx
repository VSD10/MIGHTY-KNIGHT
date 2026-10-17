import { MIGHTY_KNIGHT_LOGO } from '../constants/logo';
import React, { useState, useEffect, useMemo } from 'react';
import {
  Search, Download, Calendar, ShieldCheck, Sparkles, FolderArchive,
  Clock, BookOpen, Copy, Check, Filter, Eye, CheckCircle2, AlertTriangle
} from 'lucide-react';
import JSZip from 'jszip';
import { getStudentIcsUrl } from '../services/api';
import { STUDENT_DATABASE, normalizeBatchLevel } from '../constants/studentDatabase';

// On-Demand High-Resolution HTML5 Canvas PNG Renderer for both:
// 1. Actual Planned Schedule ("planned")
// 2. Actual Attended Classes ("attended")
async function renderStudentCardToPngBlob(student, mode = 'planned', targetMonth = '2026-10') {
  const classes = mode === 'attended'
    ? (student.actual_attended_classes || [])
    : (student.actual_schedule_classes || student.classes || []);
  const diffSummary = student.attendance_summary || {};
  const diffs = diffSummary.differences || [];

  const width = 1536;
  const rowHeight = 52;
  const diffBoxHeight = (mode === 'attended' && diffs.length > 0) ? (90 + diffs.length * 32) : (mode === 'attended' ? 80 : 0);
  const numRows = Math.max(classes.length, 1);
  const height = Math.max(740, 520 + numRows * rowHeight + diffBoxHeight);

  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');

  // 1. Royal Crimson & Obsidian Gradient Background
  const bgGrad = ctx.createRadialGradient(width / 2, height * 0.18, 40, width / 2, height / 2, width * 0.85);
  bgGrad.addColorStop(0, '#380408');
  bgGrad.addColorStop(0.45, '#170204');
  bgGrad.addColorStop(1, '#050102');
  ctx.fillStyle = bgGrad;
  ctx.fillRect(0, 0, width, height);

  // Top Golden Bokeh Glow
  const glowGrad = ctx.createRadialGradient(width / 2, 60, 10, width / 2, 60, 460);
  glowGrad.addColorStop(0, 'rgba(245, 158, 11, 0.24)');
  glowGrad.addColorStop(0.5, 'rgba(220, 38, 38, 0.12)');
  glowGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');
  ctx.fillStyle = glowGrad;
  ctx.fillRect(0, 0, width, 360);

  // Helper for rounded rectangles
  const roundRect = (x, y, w, h, r, fill, stroke, strokeWidth = 1.5) => {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
    if (fill) {
      ctx.fillStyle = fill;
      ctx.fill();
    }
    if (stroke) {
      ctx.strokeStyle = stroke;
      ctx.lineWidth = strokeWidth;
      ctx.stroke();
    }
  };

  // 2. Load Mighty Knight Logo
  roundRect(42, 32, 112, 112, 20, '#450a0a', 'rgba(245, 158, 11, 0.75)', 2);
  try {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    await new Promise((resolve) => {
      img.onload = resolve;
      img.onerror = resolve;
      img.src = MIGHTY_KNIGHT_LOGO;
    });
    if (img.width > 0) {
      ctx.save();
      ctx.beginPath();
      ctx.roundRect(44, 34, 108, 108, 18);
      ctx.clip();
      ctx.drawImage(img, 44, 34, 108, 108);
      ctx.restore();
    }
  } catch (e) {}

  // Brand Titles
  ctx.fillStyle = '#fbbf24';
  ctx.font = '900 38px Cinzel, Georgia, serif';
  ctx.fillText('MIGHTY KNIGHT', 174, 72);
  ctx.fillStyle = '#ffffff';
  ctx.font = '700 22px Cinzel, Georgia, serif';
  ctx.fillText('CHESS ACADEMY', 174, 104);
  ctx.fillStyle = '#f59e0b';
  ctx.fillRect(174, 114, 320, 1.5);
  ctx.fillStyle = '#cbd5e1';
  ctx.font = '600 13px Outfit, sans-serif';
  ctx.fillText('DISCIPLINE  •  STRATEGY  •  BRIGHTER MINDS', 174, 134);

  // 3. Right Student Profile Card
  const cardX = width - 520;
  roundRect(cardX, 28, 478, 126, 18, 'rgba(22, 10, 16, 0.88)', 'rgba(245, 158, 11, 0.55)', 1.5);
  ctx.fillStyle = '#ffffff';
  ctx.font = '800 22px Outfit, sans-serif';
  ctx.fillText(student.student_name || 'Student', cardX + 22, 62);

  ctx.fillStyle = '#fbbf24';
  ctx.font = '800 14px Outfit, sans-serif';
  const bCode = student.batch_code || student.batch_name || student.batch_type || 'GBN1-01';
  ctx.fillText(`ID: ${student.student_id}   •   BATCH CODE: ${bCode}`, cardX + 22, 86);

  // Level & Rating Pills inside Profile Card
  roundRect(cardX + 22, 100, 220, 38, 10, 'rgba(15, 23, 42, 0.85)', 'rgba(52, 211, 153, 0.45)', 1);
  ctx.fillStyle = '#94a3b8';
  ctx.font = '700 10px Outfit, sans-serif';
  ctx.fillText('BATCH LEVEL', cardX + 34, 114);
  ctx.fillStyle = '#34d399';
  ctx.font = '800 14px Outfit, sans-serif';
  ctx.fillText(student.student_level || 'Beginner 1', cardX + 34, 131);

  roundRect(cardX + 254, 100, 202, 38, 10, 'rgba(15, 23, 42, 0.85)', 'rgba(251, 191, 36, 0.45)', 1);
  ctx.fillStyle = '#94a3b8';
  ctx.font = '700 10px Outfit, sans-serif';
  ctx.fillText('MKCA RATING', cardX + 266, 114);
  ctx.fillStyle = '#fbbf24';
  ctx.font = '800 14px Outfit, sans-serif';
  ctx.fillText(`★ ${student.mkca_rating ?? '-'}`, cardX + 266, 131);

  // 4. Schedule Banner
  const bannerY = 174;
  roundRect(
    42,
    bannerY,
    width - 84,
    62,
    14,
    mode === 'attended' ? 'rgba(6, 78, 59, 0.85)' : 'rgba(153, 27, 27, 0.85)',
    mode === 'attended' ? 'rgba(52, 211, 153, 0.6)' : 'rgba(239, 68, 68, 0.5)',
    1.5
  );
  ctx.fillStyle = '#ffffff';
  ctx.font = '800 20px Outfit, sans-serif';
  ctx.fillText(
    mode === 'attended'
      ? `ACTUAL ATTENDED CLASSES LOG (${targetMonth}) — REAL-TIME VERIFIED`
      : `OFFICIAL STUDENT CLASS SCHEDULE (${targetMonth} ACADEMIC CYCLE)`,
    66,
    bannerY + 28
  );
  ctx.fillStyle = mode === 'attended' ? '#a7f3d0' : '#fca5a5';
  ctx.font = '600 13px Outfit, sans-serif';
  ctx.fillText(
    mode === 'attended'
      ? `Attended So Far: ${classes.length} Class(es)  •  Regular: ${diffSummary.attended_as_planned_count ?? classes.length}  •  ⓒ Compensation/Extra: ${diffSummary.compensation_or_alt_count ?? 0}`
      : `Planned Monthly Quota: ${student.required_classes ?? 12} Classes  •  Assigned Batch: ${bCode}`,
    66,
    bannerY + 48
  );

  // 5. Attendance Difference Summary Box (when mode === 'attended')
  let tableStartY = bannerY + 80;
  if (mode === 'attended') {
    roundRect(42, tableStartY, width - 84, diffBoxHeight - 14, 12, 'rgba(15, 23, 42, 0.92)', 'rgba(251, 191, 36, 0.5)', 1.5);
    ctx.fillStyle = '#fbbf24';
    ctx.font = '800 15px Outfit, sans-serif';
    ctx.fillText(
      `ATTENDANCE vs. ACTUAL SCHEDULE DIFFERENCE SUMMARY — ${diffSummary.attended_as_planned_count ?? 0} Regular + ${diffSummary.compensation_or_alt_count ?? 0} ⓒ Alternative/Compensation`,
      62,
      tableStartY + 28
    );
    if (diffs.length === 0) {
      ctx.fillStyle = '#34d399';
      ctx.font = '700 14px Outfit, sans-serif';
      ctx.fillText('✓ 100% of attended classes followed the original Actual Schedule with zero deviations.', 62, tableStartY + 54);
    } else {
      diffs.forEach((d, idx) => {
        const dy = tableStartY + 54 + idx * 28;
        ctx.fillStyle = d.type === 'compensation_or_extra' ? '#fbbf24' : '#f87171';
        ctx.font = '700 13px Outfit, sans-serif';
        ctx.fillText(
          `• [${d.badge}] ${d.date} (${d.day || ''}) at ${d.time_slot} with Coach ${d.coach_name} (${d.batch_name || bCode}) — ${d.note}`,
          62,
          dy
        );
      });
    }
    tableStartY += diffBoxHeight;
  }

  // 6. Table Header & Rows
  const tableH = 50 + numRows * rowHeight;
  roundRect(42, tableStartY, width - 84, tableH, 16, 'rgba(12, 16, 28, 0.92)', 'rgba(220, 38, 38, 0.48)', 1.5);
  roundRect(42, tableStartY, width - 84, 48, 14, 'rgba(32, 10, 16, 0.98)', null);

  const cols = [
    { label: '#', x: 68 },
    { label: 'DATE', x: 135 },
    { label: 'DAY', x: 290 },
    { label: 'TIME SLOT', x: 450 },
    { label: 'COACH', x: 650 },
    { label: 'BATCH CODE', x: 850 },
    { label: 'BATCH LEVEL', x: 1060 },
    { label: 'STATUS / TYPE', x: 1310 }
  ];
  ctx.fillStyle = '#fbbf24';
  ctx.font = '800 13px Outfit, sans-serif';
  cols.forEach(c => ctx.fillText(c.label, c.x, tableStartY + 30));

  if (classes.length === 0) {
    ctx.fillStyle = '#94a3b8';
    ctx.font = '700 16px Outfit, sans-serif';
    ctx.fillText(`No classes recorded for ${student.student_name} in ${targetMonth}.`, 520, tableStartY + 82);
  } else {
    classes.forEach((cls, idx) => {
      const ry = tableStartY + 48 + idx * rowHeight;
      ctx.fillStyle = idx % 2 === 0 ? 'rgba(15, 23, 42, 0.55)' : 'rgba(10, 15, 30, 0.75)';
      ctx.fillRect(44, ry, width - 88, rowHeight - 1);

      const isComp = Boolean(cls.is_compensation || cls.has_compensation);
      roundRect(60, ry + 11, 40, 28, 7, isComp ? '#d97706' : '#dc2626', null);
      ctx.fillStyle = '#ffffff';
      ctx.font = '800 14px Outfit, sans-serif';
      ctx.fillText(String(idx + 1), 74, ry + 30);

      ctx.fillStyle = '#ffffff';
      ctx.font = '700 15px Outfit, sans-serif';
      ctx.fillText(cls.date || '', 135, ry + 31);

      ctx.fillStyle = '#cbd5e1';
      ctx.font = '600 15px Outfit, sans-serif';
      ctx.fillText(cls.day || '', 290, ry + 31);

      roundRect(445, ry + 10, 165, 32, 8, 'rgba(30, 58, 138, 0.85)', 'rgba(96, 165, 250, 0.45)', 1);
      ctx.fillStyle = '#93c5fd';
      ctx.font = '800 14px Outfit, sans-serif';
      ctx.fillText(`⏰ ${cls.time_slot || ''}`, 458, ry + 31);

      ctx.fillStyle = '#f8fafc';
      ctx.font = '700 15px Outfit, sans-serif';
      ctx.fillText(`Coach ${cls.coach_name || ''}`, 650, ry + 31);

      roundRect(845, ry + 10, 165, 32, 8, 'rgba(6, 78, 59, 0.65)', 'rgba(52, 211, 153, 0.45)', 1);
      ctx.fillStyle = '#34d399';
      ctx.font = '800 14px Outfit, sans-serif';
      ctx.fillText(cls.batch_name || cls.batch_code || bCode, 860, ry + 31);

      ctx.fillStyle = '#e2e8f0';
      ctx.font = '700 14px Outfit, sans-serif';
      ctx.fillText(student.student_level || cls.student_level || '', 1060, ry + 31);

      ctx.fillStyle = isComp ? '#fbbf24' : (cls.is_tournament ? '#f59e0b' : '#34d399');
      ctx.font = '800 13px Outfit, sans-serif';
      ctx.fillText(
        isComp ? 'ⓒ Compensation / Alt' : (cls.is_tournament ? '🏆 Tournament' : '✓ Regular Planned'),
        1310,
        ry + 31
      );
    });
  }

  // 7. Verified Audit Footer
  const footerY = tableStartY + tableH + 34;
  ctx.fillStyle = '#fbbf24';
  ctx.font = '700 18px Cinzel, Georgia, serif';
  ctx.fillText('Mighty Knight Chess Academy  —  "Train your Brain"', 52, footerY);

  ctx.fillStyle = '#34d399';
  ctx.font = '700 14px Outfit, sans-serif';
  ctx.fillText(
    `✓ Audit & Data Integrity Verified for ${student.student_name} (ID: ${student.student_id} · Batch ${bCode})`,
    width - 680,
    footerY
  );

  return new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
}

export default function StudentScheduleView({
  studentScheduleData,
  detailedClasses = [],
  scheduleId,
  activeMonth = '2026-10'
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedLevelFilter, setSelectedLevelFilter] = useState('ALL');
  const [downloadingId, setDownloadingId] = useState(null);
  const [isBulkDownloading, setIsBulkDownloading] = useState(false);
  const [zipProgress, setZipProgress] = useState('');
  const [showAuditModal, setShowAuditModal] = useState(false);

  // Per-student card mode: 'planned' (Actual Schedule) vs 'attended' (Actual Attended Classes)
  const [globalCardMode, setGlobalCardMode] = useState('planned');
  const [studentCardModeMap, setStudentCardModeMap] = useState({});
  const [attendanceMonthMap, setAttendanceMonthMap] = useState({});

  const liveStudents = useMemo(() => {
    const rawList = studentScheduleData?.student_schedules || [];
    if (rawList.length > 0) {
      return [...rawList].sort((a, b) => (a.student_name || '').localeCompare(b.student_name || ''));
    }
    return [];
  }, [studentScheduleData]);

  const filteredStudents = useMemo(() => {
    return liveStudents.filter(s => {
      const q = searchQuery.toLowerCase().trim();
      const matchesSearch = !q ||
        (s.student_name || '').toLowerCase().includes(q) ||
        (s.student_id || '').toLowerCase().includes(q) ||
        (s.batch_code || s.batch_name || '').toLowerCase().includes(q) ||
        (s.student_level || '').toLowerCase().includes(q);
      const matchesLevel = selectedLevelFilter === 'ALL' || s.student_level === selectedLevelFilter;
      return matchesSearch && matchesLevel;
    });
  }, [liveStudents, searchQuery, selectedLevelFilter]);

  const getCardMode = (sid) => studentCardModeMap[sid] || globalCardMode;
  const setCardMode = (sid, mode) => setStudentCardModeMap(prev => ({ ...prev, [sid]: mode }));

  const getAttMonth = (sid) => attendanceMonthMap[sid] || '2026-10';
  const handleChangeAttMonth = (sid, val) => {
    if (val < '2026-10') {
      alert('Historical records prior to October 2026 are not enabled in this academic cycle.');
      return;
    }
    setAttendanceMonthMap(prev => ({ ...prev, [sid]: val }));
  };

  const handleDownloadPng = async (student, mode = 'planned') => {
    const key = `${student.student_id}_${mode}`;
    setDownloadingId(key);
    try {
      const monthUsed = mode === 'attended' ? getAttMonth(student.student_id) : activeMonth;
      const blob = await renderStudentCardToPngBlob(student, mode, monthUsed);
      const safeName = (student.student_name || student.student_id).replace(/[^a-zA-Z0-9_-]/g, '_');
      const suffix = mode === 'attended' ? `Actual_Attendance_${monthUsed}` : `Actual_Schedule_${monthUsed}`;
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `Mighty_Knight_${safeName}_${student.student_id}_${suffix}.png`;
      link.click();
      URL.revokeObjectURL(link.href);
    } catch (err) {
      alert('Failed to generate PNG: ' + err.message);
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
      const folder = zip.folder(`Mighty_Knight_${globalCardMode === 'attended' ? 'Attendance' : 'Schedules'}_${activeMonth}`);
      let count = 0;
      for (const stu of filteredStudents) {
        count++;
        setZipProgress(`Rendering ${count}/${filteredStudents.length}: ${stu.student_name}`);
        const blob = await renderStudentCardToPngBlob(stu, globalCardMode, activeMonth);
        const safeName = (stu.student_name || stu.student_id).replace(/[^a-zA-Z0-9_-]/g, '_');
        folder.file(`Mighty_Knight_${safeName}_${stu.student_id}.png`, blob);
      }
      setZipProgress('Packaging ZIP archive...');
      const zipBlob = await zip.generateAsync({ type: 'blob' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(zipBlob);
      link.download = `Mighty_Knight_${globalCardMode === 'attended' ? 'Actual_Attendance' : 'Actual_Schedules'}_${activeMonth}.zip`;
      link.click();
      URL.revokeObjectURL(link.href);
    } catch (err) {
      alert('Error creating ZIP: ' + err.message);
    } finally {
      setIsBulkDownloading(false);
      setZipProgress('');
    }
  };

  const levelsList = [
    'ALL', 'Basic 1', 'Basic 2', 'Beginner 1', 'Beginner 2',
    'Early Intermediate 1', 'Early Intermediate 2', 'Intermediate 1', 'Intermediate 2'
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '22px', paddingBottom: '60px' }}>
      {/* Top Header & Global Mode Switcher */}
      <div
        className="glass-panel"
        style={{
          padding: '20px 24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '16px',
          border: '1px solid rgba(245, 158, 11, 0.35)',
          background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.96) 0%, rgba(30, 15, 20, 0.92) 100%)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <img
            src={MIGHTY_KNIGHT_LOGO}
            alt="Mighty Knight Logo"
            style={{ width: '54px', height: '54px', borderRadius: '12px', border: '1.5px solid var(--accent-gold)', objectFit: 'contain', background: '#450a0a' }}
          />
          <div>
            <h2 style={{ fontSize: '1.4rem', fontWeight: 900, color: '#fff', margin: 0 }}>
              Output 5 — Student Schedules & Real-Time Attendance Hub ({activeMonth})
            </h2>
            <p style={{ fontSize: '0.82rem', color: '#cbd5e1', marginTop: '3px' }}>
              Switch between each student's <strong>Actual Planned Schedule</strong> and <strong>Actual Attended Classes (So Far + ⓒ Compensation Differences)</strong>. On-demand PNG generation with full Audit & Validation.
            </p>
          </div>
        </div>

        {/* Global Mode Toggle + Audit + Bulk ZIP */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', background: 'rgba(0,0,0,0.45)', padding: '4px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.12)' }}>
            <button
              onClick={() => {
                setGlobalCardMode('planned');
                setStudentCardModeMap({});
              }}
              style={{
                padding: '7px 14px',
                borderRadius: '8px',
                border: 'none',
                fontWeight: 800,
                fontSize: '0.78rem',
                cursor: 'pointer',
                background: globalCardMode === 'planned' ? 'var(--accent-gold)' : 'transparent',
                color: globalCardMode === 'planned' ? '#000' : '#cbd5e1'
              }}
            >
              📅 1. Actual Planned Schedules
            </button>
            <button
              onClick={() => {
                setGlobalCardMode('attended');
                setStudentCardModeMap({});
              }}
              style={{
                padding: '7px 14px',
                borderRadius: '8px',
                border: 'none',
                fontWeight: 800,
                fontSize: '0.78rem',
                cursor: 'pointer',
                background: globalCardMode === 'attended' ? '#10b981' : 'transparent',
                color: globalCardMode === 'attended' ? '#000' : '#cbd5e1'
              }}
            >
              ✅ 2. Actual Attended Classes (Live)
            </button>
          </div>

          <button
            onClick={() => setShowAuditModal(true)}
            className="btn btn-secondary"
            style={{
              padding: '8px 14px',
              border: '1px solid rgba(52, 211, 153, 0.45)',
              color: '#34d399',
              background: 'rgba(6, 78, 59, 0.3)',
              fontWeight: 800,
              fontSize: '0.8rem',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <ShieldCheck size={16} /> Audit & Validation ({liveStudents.length})
          </button>

          <button
            onClick={handleDownloadAllImagesZip}
            disabled={isBulkDownloading}
            className="btn btn-primary"
            style={{
              padding: '9px 16px',
              fontWeight: 800,
              fontSize: '0.82rem',
              display: 'flex',
              alignItems: 'center',
              gap: '7px'
            }}
          >
            <FolderArchive size={16} />
            {isBulkDownloading ? (zipProgress || 'Rendering PNGs...') : `Download All PNGs (.zip)`}
          </button>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div
        className="glass-panel"
        style={{
          padding: '14px 20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '14px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.78rem', fontWeight: 800, color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Filter size={14} /> LEVEL:
          </span>
          {levelsList.map(lvl => (
            <button
              key={lvl}
              onClick={() => setSelectedLevelFilter(lvl)}
              style={{
                padding: '5px 11px',
                borderRadius: '8px',
                fontSize: '0.75rem',
                fontWeight: 700,
                cursor: 'pointer',
                border: selectedLevelFilter === lvl ? '1px solid #f59e0b' : '1px solid rgba(255,255,255,0.1)',
                background: selectedLevelFilter === lvl ? 'rgba(245,158,11,0.25)' : 'rgba(15,23,42,0.6)',
                color: selectedLevelFilter === lvl ? '#fbbf24' : '#94a3b8'
              }}
            >
              {lvl}
            </button>
          ))}
        </div>

        <div style={{ position: 'relative', width: '300px' }}>
          <Search size={16} style={{ position: 'absolute', left: '12px', top: '10px', color: '#64748b' }} />
          <input
            type="text"
            placeholder="Search student name, ID, or batch code..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="input-field"
            style={{ width: '100%', paddingLeft: '36px', fontSize: '0.82rem' }}
          />
        </div>
      </div>

      {/* STUDENT CARDS LIST */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
        {filteredStudents.length === 0 && (
          <div className="glass-panel" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <p>No student schedule records found. Upload and activate an Absolute Schedule to populate.</p>
          </div>
        )}
        {filteredStudents.map((student) => {
          const sid = student.student_id;
          const mode = getCardMode(sid);
          const attMonth = getAttMonth(sid);
          const isFutureAttMonth = attMonth > '2026-10';
          const bCode = student.batch_code || student.batch_name || student.batch_type || 'GBN1-01';
          const plannedClasses = student.actual_schedule_classes || student.classes || [];
          const attendedClasses = isFutureAttMonth ? [] : (student.actual_attended_classes || []);
          const displayClasses = mode === 'attended' ? attendedClasses : plannedClasses;
          const summary = student.attendance_summary || {};
          const diffs = summary.differences || [];

          return (
            <div
              key={sid}
              className="glass-panel"
              style={{
                border: mode === 'attended' ? '1.5px solid rgba(16, 185, 129, 0.5)' : '1.5px solid rgba(245, 158, 11, 0.4)',
                borderRadius: '16px',
                overflow: 'hidden',
                background: 'radial-gradient(circle at 50% 10%, #2a060a 0%, #110408 55%, #070b14 100%)',
                boxShadow: '0 18px 40px rgba(0, 0, 0, 0.65)'
              }}
            >
              {/* Top Control Bar: Student Tabs (1. Actual Schedule vs 2. Actual Attended Classes) */}
              <div
                style={{
                  padding: '12px 20px',
                  background: 'rgba(15, 23, 42, 0.95)',
                  borderBottom: '1px solid rgba(255,255,255,0.1)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: '12px'
                }}
              >
                {/* Mode Selector Tabs for this Student */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                  <button
                    onClick={() => setCardMode(sid, 'planned')}
                    style={{
                      padding: '6px 14px',
                      borderRadius: '8px',
                      border: mode === 'planned' ? '1px solid #fbbf24' : '1px solid rgba(255,255,255,0.12)',
                      background: mode === 'planned' ? 'rgba(245, 158, 11, 0.25)' : 'rgba(15, 23, 42, 0.7)',
                      color: mode === 'planned' ? '#fbbf24' : '#94a3b8',
                      fontWeight: 800,
                      fontSize: '0.78rem',
                      cursor: 'pointer'
                    }}
                  >
                    📅 1. Actual Schedule ({plannedClasses.length} Classes)
                  </button>

                  <button
                    onClick={() => setCardMode(sid, 'attended')}
                    style={{
                      padding: '6px 14px',
                      borderRadius: '8px',
                      border: mode === 'attended' ? '1px solid #10b981' : '1px solid rgba(255,255,255,0.12)',
                      background: mode === 'attended' ? 'rgba(16, 185, 129, 0.25)' : 'rgba(15, 23, 42, 0.7)',
                      color: mode === 'attended' ? '#34d399' : '#94a3b8',
                      fontWeight: 800,
                      fontSize: '0.78rem',
                      cursor: 'pointer'
                    }}
                  >
                    ✅ 2. Actual Attended Classes ({(student.actual_attended_classes || []).length} So Far)
                    {diffs.length > 0 && (
                      <span style={{ marginLeft: '6px', background: '#f59e0b', color: '#000', padding: '1px 6px', borderRadius: '10px', fontSize: '0.68rem', fontWeight: 900 }}>
                        {diffs.length} ⓒ Diff
                      </span>
                    )}
                  </button>

                  {/* Month Selector inside Attendance Mode (Point 5 & 10) */}
                  {mode === 'attended' && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginLeft: '6px' }}>
                      <span style={{ fontSize: '0.72rem', fontWeight: 800, color: '#fde68a' }}>ATTENDANCE MONTH:</span>
                      <input
                        type="month"
                        min="2026-10"
                        max="2027-02"
                        value={attMonth}
                        onChange={(e) => handleChangeAttMonth(sid, e.target.value)}
                        className="input-field"
                        style={{ padding: '4px 8px', fontSize: '0.76rem', fontWeight: 800 }}
                      />
                    </div>
                  )}
                </div>

                {/* Right Action Buttons: .ics Calendar (ONLY on Actual Schedule & ONLY when 0 Attention Issues!) + On-Demand PNG Download */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                  {mode === 'planned' && (
                    student.has_attention_issue ? (
                      <button
                        type="button"
                        onClick={() => alert(`Calendar (.ics) is locked for ${student.student_name}: Please resolve all missing/deleted class issues in Output 3 (Attention Page) first.`)}
                        className="btn btn-secondary"
                        style={{
                          padding: '6px 12px',
                          fontSize: '0.75rem',
                          color: '#f87171',
                          borderColor: 'rgba(239, 68, 68, 0.45)',
                          cursor: 'not-allowed',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '5px'
                        }}
                        title="Locked until student's shortfall/deleted class is resolved in Output 3"
                      >
                        <AlertTriangle size={14} /> .ics Locked (Fix in Output 3)
                      </button>
                    ) : (
                      <a
                        href={getStudentIcsUrl(scheduleId, sid)}
                        download={`mighty_knight_${sid}_calendar.ics`}
                        className="btn btn-secondary"
                        style={{
                          padding: '6px 12px',
                          color: '#60a5fa',
                          fontSize: '0.78rem',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '5px',
                          textDecoration: 'none',
                          background: 'rgba(30, 58, 138, 0.35)',
                          borderColor: 'rgba(59, 130, 246, 0.45)',
                          fontWeight: 800
                        }}
                        title="Download .ics Calendar for Actual Planned Schedule"
                      >
                        <Calendar size={14} /> .ics Calendar
                      </a>
                    )
                  )}

                  <button
                    onClick={() => handleDownloadPng(student, mode)}
                    disabled={downloadingId === `${sid}_${mode}` || (mode === 'attended' && isFutureAttMonth)}
                    style={{
                      padding: '7px 16px',
                      background: mode === 'attended'
                        ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
                        : 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
                      border: '1px solid rgba(255,255,255,0.25)',
                      color: '#000',
                      fontWeight: 900,
                      fontSize: '0.8rem',
                      borderRadius: '8px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      cursor: 'pointer'
                    }}
                  >
                    <Download size={15} />
                    {downloadingId === `${sid}_${mode}`
                      ? 'Rendering PNG...'
                      : (mode === 'attended' ? 'Download Attended Classes PNG' : 'Download Actual Schedule PNG')}
                  </button>
                </div>
              </div>

              {/* CARD BODY: Branded Mighty Knight Header + Profile Box + Difference Highlight + Schedule Table */}
              <div style={{ padding: '22px 26px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {/* Branded Header Row */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <img
                      src={MIGHTY_KNIGHT_LOGO}
                      alt="Mighty Knight Crest"
                      style={{
                        width: '72px',
                        height: '72px',
                        borderRadius: '16px',
                        border: '2px solid rgba(245, 158, 11, 0.65)',
                        boxShadow: '0 0 20px rgba(220, 38, 38, 0.45)',
                        objectFit: 'contain', background: '#450a0a'
                      }}
                    />
                    <div>
                      <div style={{ fontFamily: 'Cinzel, serif', fontSize: '1.55rem', fontWeight: 900, color: '#fbbf24', letterSpacing: '1.5px' }}>
                        MIGHTY KNIGHT CHESS ACADEMY
                      </div>
                      <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#cbd5e1', letterSpacing: '2.5px', textTransform: 'uppercase', marginTop: '2px' }}>
                        Discipline • Strategy • Brighter Minds
                      </div>
                    </div>
                  </div>

                  {/* Student Profile Box */}
                  <div
                    style={{
                      background: 'rgba(22, 10, 16, 0.85)',
                      border: '1.5px solid rgba(220, 38, 38, 0.5)',
                      borderRadius: '14px',
                      padding: '12px 18px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '18px',
                      flexWrap: 'wrap'
                    }}
                  >
                    <div>
                      <div style={{ fontSize: '1.15rem', fontWeight: 900, color: '#fff' }}>{student.student_name}</div>
                      <div style={{ fontSize: '0.78rem', color: '#fbbf24', fontWeight: 800 }}>
                        ID: {sid} · Batch Code: <span style={{ color: '#34d399' }}>{bCode}</span> [{student.batch_type || 'G'}]
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: '10px' }}>
                      <div style={{ background: 'rgba(15, 23, 42, 0.8)', padding: '6px 12px', borderRadius: '8px', border: '1px solid rgba(52, 211, 153, 0.35)' }}>
                        <span style={{ fontSize: '0.65rem', color: '#94a3b8', display: 'block', fontWeight: 700 }}>LEVEL</span>
                        <strong style={{ fontSize: '0.85rem', color: '#34d399' }}>{student.student_level}</strong>
                      </div>
                      <div style={{ background: 'rgba(15, 23, 42, 0.8)', padding: '6px 12px', borderRadius: '8px', border: '1px solid rgba(251, 191, 36, 0.35)' }}>
                        <span style={{ fontSize: '0.65rem', color: '#94a3b8', display: 'block', fontWeight: 700 }}>MKCA RATING</span>
                        <strong style={{ fontSize: '0.85rem', color: '#fbbf24' }}>★ {student.mkca_rating ?? '-'}</strong>
                      </div>
                    </div>
                  </div>
                </div>

                {/* If mode === 'attended' and Future Month selected -> show clear Future Month block notice */}
                {mode === 'attended' && isFutureAttMonth ? (
                  <div
                    style={{
                      padding: '24px',
                      borderRadius: '12px',
                      background: 'rgba(244, 63, 94, 0.15)',
                      border: '1.5px solid #f43f5e',
                      color: '#fecdd3',
                      textAlign: 'center',
                      fontWeight: 800
                    }}
                  >
                    ⚠️ {attMonth} is a Future Month — Actual Attended Classes can only be viewed for completed or current dates (up to 2026-10-15).
                  </div>
                ) : (
                  <>
                    {/* Attendance Difference Highlight Box (Point 5 & 10) */}
                    {mode === 'attended' && (
                      <div
                        style={{
                          padding: '14px 18px',
                          borderRadius: '12px',
                          background: 'rgba(15, 23, 42, 0.9)',
                          border: '1.5px solid rgba(251, 191, 36, 0.5)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '10px'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
                          <strong style={{ fontSize: '0.88rem', color: '#fbbf24' }}>
                            📊 Real-Time Attendance vs. Planned Schedule Difference Summary (Up to {summary.reference_today || '2026-10-15'})
                          </strong>
                          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                            <span className="badge" style={{ background: 'rgba(16, 185, 129, 0.2)', color: '#34d399', border: '1px solid #10b981', fontSize: '0.72rem', fontWeight: 800 }}>
                              ✓ Attended as Planned: {summary.attended_as_planned_count ?? attendedClasses.length}
                            </span>
                            <span className="badge" style={{ background: 'rgba(245, 158, 11, 0.2)', color: '#fbbf24', border: '1px solid #f59e0b', fontSize: '0.72rem', fontWeight: 800 }}>
                              ⓒ Alternative / Compensation / Extra: {summary.compensation_or_alt_count ?? 0}
                            </span>
                            <span className="badge" style={{ background: 'rgba(59, 130, 246, 0.2)', color: '#93c5fd', border: '1px solid #3b82f6', fontSize: '0.72rem', fontWeight: 800 }}>
                              Total Attended So Far: {attendedClasses.length} / {student.required_classes ?? 12} Monthly Quota
                            </span>
                          </div>
                        </div>

                        {diffs.length === 0 ? (
                          <div style={{ fontSize: '0.78rem', color: '#6ee7b7', fontWeight: 700 }}>
                            ✓ Every attended class so far matches the student's original Actual Schedule with zero deviations.
                          </div>
                        ) : (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            {diffs.map((d, dIdx) => (
                              <div
                                key={dIdx}
                                style={{
                                  padding: '6px 12px',
                                  borderRadius: '8px',
                                  background: d.type === 'compensation_or_extra' ? 'rgba(245, 158, 11, 0.15)' : 'rgba(244, 63, 94, 0.15)',
                                  border: d.type === 'compensation_or_extra' ? '1px solid rgba(251, 191, 36, 0.45)' : '1px solid rgba(244, 63, 94, 0.45)',
                                  color: d.type === 'compensation_or_extra' ? '#fde68a' : '#fecdd3',
                                  fontSize: '0.76rem',
                                  display: 'flex',
                                  justifyContent: 'space-between',
                                  flexWrap: 'wrap',
                                  gap: '8px'
                                }}
                              >
                                <span>
                                  <strong>{d.badge}:</strong> {d.date} ({d.day}) at <strong>{d.time_slot}</strong> · Coach <strong>{d.coach_name}</strong> · Batch <strong>{d.batch_name || bCode}</strong>
                                </span>
                                <span style={{ opacity: 0.9 }}>{d.note}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Schedule / Attendance Table */}
                    <div style={{ overflowX: 'auto', border: '1px solid rgba(220, 38, 38, 0.4)', borderRadius: '12px', background: 'rgba(12, 16, 28, 0.9)' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', textAlign: 'left' }}>
                        <thead>
                          <tr style={{ background: 'rgba(32, 10, 16, 0.95)', color: '#fbbf24', borderBottom: '1px solid rgba(220, 38, 38, 0.4)' }}>
                            <th style={{ padding: '10px 14px', width: '55px' }}>#</th>
                            <th style={{ padding: '10px 14px' }}>DATE</th>
                            <th style={{ padding: '10px 14px' }}>DAY</th>
                            <th style={{ padding: '10px 14px' }}>TIME SLOT</th>
                            <th style={{ padding: '10px 14px' }}>TRAINER / COACH</th>
                            <th style={{ padding: '10px 14px' }}>BATCH CODE</th>
                            <th style={{ padding: '10px 14px' }}>BATCH LEVEL</th>
                            <th style={{ padding: '10px 14px' }}>STATUS / TYPE</th>
                          </tr>
                        </thead>
                        <tbody>
                          {displayClasses.length === 0 ? (
                            <tr>
                              <td colSpan={8} style={{ padding: '24px', textAlign: 'center', color: '#94a3b8', fontWeight: 700 }}>
                                No classes recorded in this view for {student.student_name}.
                              </td>
                            </tr>
                          ) : (
                            displayClasses.map((cls, cIdx) => {
                              const isComp = Boolean(cls.is_compensation || cls.has_compensation);
                              return (
                                <tr
                                  key={`${cls.class_id}_${cIdx}`}
                                  style={{
                                    borderBottom: '1px solid rgba(255,255,255,0.05)',
                                    background: isComp
                                      ? 'rgba(245, 158, 11, 0.12)'
                                      : (cIdx % 2 === 0 ? 'rgba(15, 23, 42, 0.5)' : 'rgba(10, 15, 30, 0.7)')
                                  }}
                                >
                                  <td style={{ padding: '9px 14px', fontWeight: 800, color: '#fff' }}>{cIdx + 1}</td>
                                  <td style={{ padding: '9px 14px', fontWeight: 700, color: '#fff' }}>{cls.date}</td>
                                  <td style={{ padding: '9px 14px', color: '#cbd5e1' }}>{cls.day}</td>
                                  <td style={{ padding: '9px 14px', color: '#93c5fd', fontWeight: 800 }}>⏰ {cls.time_slot}</td>
                                  <td style={{ padding: '9px 14px', color: '#fff', fontWeight: 700 }}>Coach {cls.coach_name}</td>
                                  <td style={{ padding: '9px 14px' }}>
                                    <span style={{ background: 'rgba(6, 78, 59, 0.6)', border: '1px solid rgba(52, 211, 153, 0.45)', color: '#34d399', padding: '2px 9px', borderRadius: '6px', fontWeight: 800, fontSize: '0.75rem' }}>
                                      {cls.batch_name || cls.batch_code || bCode}
                                    </span>
                                  </td>
                                  <td style={{ padding: '9px 14px', color: '#e2e8f0' }}>{student.student_level}</td>
                                  <td style={{ padding: '9px 14px' }}>
                                    {isComp ? (
                                      <span style={{ color: '#fbbf24', fontWeight: 900 }}>ⓒ Compensation / Alt</span>
                                    ) : cls.is_tournament ? (
                                      <span style={{ color: '#f59e0b', fontWeight: 800 }}>🏆 Tournament</span>
                                    ) : (
                                      <span style={{ color: '#34d399', fontWeight: 700 }}>✓ Planned Regular</span>
                                    )}
                                  </td>
                                </tr>
                              );
                            })
                          )}
                        </tbody>
                      </table>
                    </div>
                  </>
                )}

                {/* Card Footer: Inspiration Tagline + Verification */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px', paddingTop: '4px', fontSize: '0.78rem', color: '#cbd5e1' }}>
                  <div>
                    <strong style={{ color: '#fbbf24', fontFamily: 'Cinzel, serif' }}>Mighty Knight Chess Academy</strong> · <em style={{ color: '#fde68a' }}>"Train your Brain"</em>
                  </div>
                  <div style={{ color: '#34d399', fontWeight: 700 }}>
                    ✓ Verified for {student.student_name} (ID: {sid} · Batch {bCode})
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* AUDIT & VALIDATION MODAL */}
      {showAuditModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.85)',
            backdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: '24px'
          }}
        >
          <div
            className="glass-panel"
            style={{
              width: '100%',
              maxWidth: '960px',
              maxHeight: '88vh',
              overflowY: 'auto',
              padding: '26px',
              border: '1.5px solid rgba(245, 158, 11, 0.45)',
              background: '#0b101d',
              borderRadius: '16px'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '14px', marginBottom: '18px' }}>
              <div>
                <h3 style={{ fontSize: '1.35rem', fontWeight: 900, color: '#fbbf24', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <ShieldCheck size={22} color="#34d399" /> Student Schedules & Attendance Integrity Audit ({activeMonth})
                </h3>
                <p style={{ fontSize: '0.82rem', color: '#94a3b8', margin: '4px 0 0 0' }}>
                  Live verification of official Mighty Knight branding, Batch Codes (GB1-01..IIM2-01), MKCA Ratings, and .ics Calendar locks.
                </p>
              </div>
              <button onClick={() => setShowAuditModal(false)} className="btn btn-secondary" style={{ padding: '6px 14px', fontSize: '0.82rem' }}>
                Close Audit
              </button>
            </div>

            <div style={{ maxHeight: '420px', overflowY: 'auto', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '10px' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', textAlign: 'left' }}>
                <thead>
                  <tr style={{ background: 'rgba(255,255,255,0.05)', color: '#fbbf24', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                    <th style={{ padding: '8px 12px' }}>#</th>
                    <th style={{ padding: '8px 12px' }}>Student Name</th>
                    <th style={{ padding: '8px 12px' }}>ID</th>
                    <th style={{ padding: '8px 12px' }}>Batch Code</th>
                    <th style={{ padding: '8px 12px' }}>Level</th>
                    <th style={{ padding: '8px 12px' }}>MKCA Rating</th>
                    <th style={{ padding: '8px 12px' }}>Planned / Scheduled</th>
                    <th style={{ padding: '8px 12px' }}>Attended So Far</th>
                    <th style={{ padding: '8px 12px' }}>.ics Status</th>
                  </tr>
                </thead>
                <tbody>
                  {liveStudents.map((s, idx) => (
                    <tr key={s.student_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', color: '#cbd5e1' }}>
                      <td style={{ padding: '8px 12px' }}>{idx + 1}</td>
                      <td style={{ padding: '8px 12px', fontWeight: 700, color: '#fff' }}>{s.student_name}</td>
                      <td style={{ padding: '8px 12px', color: '#fbbf24' }}>{s.student_id}</td>
                      <td style={{ padding: '8px 12px', color: '#34d399', fontWeight: 800 }}>{s.batch_code || s.batch_name}</td>
                      <td style={{ padding: '8px 12px' }}>{s.student_level}</td>
                      <td style={{ padding: '8px 12px' }}>★ {s.mkca_rating ?? '-'}</td>
                      <td style={{ padding: '8px 12px' }}>{s.scheduled_classes_count} / {s.required_classes}</td>
                      <td style={{ padding: '8px 12px', color: '#60a5fa' }}>{(s.actual_attended_classes || []).length} classes</td>
                      <td style={{ padding: '8px 12px', color: s.has_attention_issue ? '#f87171' : '#34d399', fontWeight: 800 }}>
                        {s.has_attention_issue ? 'Locked (Attention)' : '✓ Unlocked'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
