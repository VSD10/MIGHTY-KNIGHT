import React, { useState, useEffect } from 'react';
import {
  FileSpreadsheet, Upload, Download, CheckCircle, AlertTriangle,
  ShieldAlert, RefreshCw, Calendar, ArrowRight, ArrowLeft, Eye,
  Trash2, Play, Sparkles, Database, History, Info, ChevronRight,
  Filter, Search
} from 'lucide-react';
import {
  getBaselineStatus, getBaselineTemplateUrl, uploadBaselineExcel,
  activateBaseline, discardBaseline, getExportActiveBaselineUrl,
  generateNextMonthDraft, promoteEffectiveToBaseline
} from '../services/api';

export default function AbsoluteScheduleView({ onBaselineActivated }) {
  const [selectedMonth, setSelectedMonth] = useState('2026-10');
  const [statusData, setStatusData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [actionMsg, setActionMsg] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedLevel, setSelectedLevel] = useState('ALL');
  const [activeViewMode, setActiveViewMode] = useState('preview'); // 'preview' | 'validation' | 'history'

  useEffect(() => {
    fetchBaselineStatus(selectedMonth);
  }, [selectedMonth]);

  const fetchBaselineStatus = async (month) => {
    setLoading(true);
    try {
      const data = await getBaselineStatus(month);
      setStatusData(data);
    } catch (err) {
      console.error('Failed to fetch baseline status:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setActionMsg(null);
    try {
      const res = await uploadBaselineExcel(file, selectedMonth);
      setActionMsg({
        type: 'success',
        text: `Excel parsed successfully! Found ${res.draft_baseline.student_count} students and ${res.draft_baseline.class_count} classes. Ready for review.`
      });
      await fetchBaselineStatus(selectedMonth);
      setActiveViewMode('preview');
    } catch (err) {
      setActionMsg({
        type: 'error',
        text: err?.response?.data?.detail || err?.message || 'Failed to upload baseline file.'
      });
    } finally {
      setUploading(false);
    }
  };

  const handleActivate = async () => {
    const draft = statusData?.draft_baseline;
    if (!draft) return;

    if (!window.confirm(`Activate Baseline v${draft.version} as the authoritative immutable baseline for ${selectedMonth}? This will flow into Effective Schedule across the academy.`)) {
      return;
    }

    setLoading(true);
    try {
      await activateBaseline(selectedMonth, draft.version, 'Admin');
      setActionMsg({
        type: 'success',
        text: `Baseline v${draft.version} for ${selectedMonth} is now ACTIVE and immutable.`
      });
      await fetchBaselineStatus(selectedMonth);
      if (onBaselineActivated) onBaselineActivated();
    } catch (err) {
      setActionMsg({
        type: 'error',
        text: err?.response?.data?.detail || err?.message || 'Activation failed.'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDiscard = async () => {
    if (!window.confirm(`Discard pending draft baseline for ${selectedMonth}?`)) return;
    setLoading(true);
    try {
      await discardBaseline(selectedMonth);
      setActionMsg({ type: 'info', text: 'Draft baseline discarded.' });
      await fetchBaselineStatus(selectedMonth);
    } catch (err) {
      setActionMsg({ type: 'error', text: 'Could not discard draft.' });
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateNextMonth = async () => {
    const [y, m] = selectedMonth.split('-').map(Number);
    let nextY = y;
    let nextM = m + 1;
    if (nextM > 12) {
      nextM = 1;
      nextY += 1;
    }
    const nextMonthStr = `${nextY}-${String(nextM).padStart(2, '0')}`;

    if (!window.confirm(`Generate draft Absolute Schedule for ${nextMonthStr} by mapping recurring patterns from ${selectedMonth}?`)) {
      return;
    }

    setLoading(true);
    try {
      await generateNextMonthDraft(selectedMonth, nextY, nextM, 'Admin');
      setSelectedMonth(nextMonthStr);
      setActionMsg({
        type: 'success',
        text: `Generated draft baseline for ${nextMonthStr} based on ${selectedMonth} recurring patterns!`
      });
    } catch (err) {
      setActionMsg({
        type: 'error',
        text: err?.response?.data?.detail || err?.message || 'Failed to generate next month draft.'
      });
    } finally {
      setLoading(false);
    }
  };

  const handlePromoteEffective = async () => {
    if (!window.confirm(`Promote the current Effective Schedule for ${selectedMonth} (excluding single-occurrence ⓒ exceptions) into a draft Absolute Schedule?`)) {
      return;
    }
    setLoading(true);
    try {
      await promoteEffectiveToBaseline(selectedMonth, 'Admin');
      setActionMsg({
        type: 'success',
        text: `Current Effective Schedule promoted to Draft Baseline for ${selectedMonth}.`
      });
      await fetchBaselineStatus(selectedMonth);
    } catch (err) {
      setActionMsg({
        type: 'error',
        text: err?.response?.data?.detail || err?.message || 'Promotion failed.'
      });
    } finally {
      setLoading(false);
    }
  };

  // Month metadata
  const [yearNum, monthNum] = selectedMonth.split('-').map(Number);
  const firstDayObj = new Date(yearNum, monthNum - 1, 1);
  const daysInMonth = new Date(yearNum, monthNum, 0).getDate();
  const firstWeekdayName = firstDayObj.toLocaleDateString('en-US', { weekday: 'long' });

  const activeBaseline = statusData?.active_baseline;
  const draftBaseline = statusData?.draft_baseline;
  const currentDisplayBaseline = draftBaseline || activeBaseline;

  // Filter students
  const studentsList = currentDisplayBaseline?.students_data || [];
  const filteredStudents = studentsList.filter(s => {
    const matchesSearch = !searchQuery ||
      s.student_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.student_id.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesLevel = selectedLevel === 'ALL' || s.student_level === selectedLevel;
    return matchesSearch && matchesLevel;
  });

  const validationReport = currentDisplayBaseline?.validation_report || { blocking: [], baseline_exceptions: [], info: [] };
  const blockingCount = validationReport.blocking?.length || 0;
  const exceptionsCount = validationReport.baseline_exceptions?.length || 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* 1. Header & Month Selector Toolbar */}
      <div
        className="glass-panel"
        style={{
          padding: '20px 24px',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
          border: '1px solid var(--border-gold)',
          background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%)'
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '8px',
                background: 'rgba(250, 204, 21, 0.15)',
                border: '1px solid var(--accent-gold)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--accent-gold)'
              }}
            >
              <Database size={20} />
            </div>
            <div>
              <h2 style={{ fontSize: '1.3rem', fontWeight: 900, color: '#fff', margin: 0, letterSpacing: '-0.02em' }}>
                Absolute Schedule Space
              </h2>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                Immutable Month-Aware Excel Baseline (Layer 1) · {daysInMonth} Days in Month · Starts on {firstWeekdayName}
              </div>
            </div>
          </div>
        </div>

        {/* Month Selector Pills */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(15, 23, 42, 0.6)', padding: '6px', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
          <button
            onClick={() => setSelectedMonth('2026-09')}
            className={`btn ${selectedMonth === '2026-09' ? 'btn-primary' : ''}`}
            style={{ padding: '6px 12px', fontSize: '0.75rem' }}
          >
            Sep '26
          </button>
          <button
            onClick={() => setSelectedMonth('2026-10')}
            className={`btn ${selectedMonth === '2026-10' ? 'btn-primary' : ''}`}
            style={{ padding: '6px 12px', fontSize: '0.75rem', fontWeight: 800 }}
          >
            Oct '26 (Reference)
          </button>
          <button
            onClick={() => setSelectedMonth('2026-11')}
            className={`btn ${selectedMonth === '2026-11' ? 'btn-primary' : ''}`}
            style={{ padding: '6px 12px', fontSize: '0.75rem' }}
          >
            Nov '26
          </button>
          <button
            onClick={() => setSelectedMonth('2026-12')}
            className={`btn ${selectedMonth === '2026-12' ? 'btn-primary' : ''}`}
            style={{ padding: '6px 12px', fontSize: '0.75rem' }}
          >
            Dec '26
          </button>
        </div>
      </div>

      {/* Action Notification */}
      {actionMsg && (
        <div
          style={{
            padding: '12px 18px',
            borderRadius: '10px',
            background: actionMsg.type === 'error' ? 'rgba(239, 68, 68, 0.15)' : (actionMsg.type === 'success' ? 'rgba(34, 197, 94, 0.15)' : 'rgba(56, 189, 248, 0.15)'),
            border: actionMsg.type === 'error' ? '1px solid #ef4444' : (actionMsg.type === 'success' ? '1px solid #22c55e' : '1px solid #38bdf8'),
            color: actionMsg.type === 'error' ? '#fca5a5' : (actionMsg.type === 'success' ? '#86efac' : '#bae6fd'),
            fontSize: '0.85rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}
        >
          <span>{actionMsg.text}</span>
          <button onClick={() => setActionMsg(null)} style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer' }}>×</button>
        </div>
      )}

      {/* 2. Status Panel & Primary Actions */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
        
        {/* Status Card */}
        <div className="glass-panel" style={{ padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              MONTH STATUS
            </span>
            <span
              className={`badge ${statusData?.status === 'Active' ? 'badge-gold' : (statusData?.status === 'Draft' ? 'badge-blue' : 'badge-danger')}`}
              style={{ fontSize: '0.75rem', padding: '4px 10px', fontWeight: 800 }}
            >
              {statusData?.status || 'Loading...'} {statusData?.version ? `(v${statusData.version})` : ''}
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginTop: '4px' }}>
            <div style={{ background: 'rgba(15, 23, 42, 0.5)', padding: '10px', borderRadius: '8px' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Students</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#fff' }}>
                {currentDisplayBaseline?.student_count || 0}
              </div>
            </div>
            <div style={{ background: 'rgba(15, 23, 42, 0.5)', padding: '10px', borderRadius: '8px' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Classes</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--accent-gold)' }}>
                {currentDisplayBaseline?.class_count || 0}
              </div>
            </div>
            <div style={{ background: 'rgba(15, 23, 42, 0.5)', padding: '10px', borderRadius: '8px' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Student Seats</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--accent-blue)' }}>
                {currentDisplayBaseline?.student_class_count || 0}
              </div>
            </div>
          </div>

          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            <strong>File:</strong> {currentDisplayBaseline?.file_name || 'None'} · <strong>Uploaded by:</strong> {currentDisplayBaseline?.uploaded_by || 'System'}
          </div>
        </div>

        {/* Action Toolbar Card */}
        <div className="glass-panel" style={{ padding: '18px 20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '14px' }}>
          <div>
            <span style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              BASELINE OPERATIONS
            </span>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginTop: '10px' }}>
              
              {/* Download month-aware blank template */}
              <a
                href={getBaselineTemplateUrl(selectedMonth)}
                download={`Mighty_Knight_Baseline_Template_${selectedMonth}.xlsx`}
                className="btn btn-secondary"
                style={{ fontSize: '0.8rem', padding: '8px 12px', display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                <Download size={14} /> Download {selectedMonth} Template
              </a>

              {/* Upload Excel */}
              <label
                className="btn btn-primary"
                style={{ fontSize: '0.8rem', padding: '8px 12px', display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}
              >
                <Upload size={14} /> {uploading ? 'Parsing...' : 'Upload Absolute Excel'}
                <input
                  type="file"
                  accept=".xlsx, .xls"
                  onChange={handleFileUpload}
                  disabled={uploading}
                  style={{ display: 'none' }}
                />
              </label>

              {/* Download Active Excel */}
              {activeBaseline && (
                <a
                  href={getExportActiveBaselineUrl(selectedMonth)}
                  download={`Mighty_Knight_Active_Baseline_${selectedMonth}.xlsx`}
                  className="btn btn-secondary"
                  style={{ fontSize: '0.8rem', padding: '8px 12px', display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <FileSpreadsheet size={14} /> Export Active Excel
                </a>
              )}
            </div>
          </div>

          {/* Action Row */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', borderTop: '1px solid var(--border-color)', paddingTop: '10px' }}>
            {draftBaseline && (
              <>
                <button
                  onClick={handleActivate}
                  disabled={loading || blockingCount > 0}
                  className="btn btn-primary"
                  style={{ fontSize: '0.8rem', padding: '8px 14px', background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)', color: '#fff', fontWeight: 800 }}
                >
                  <CheckCircle size={14} /> Activate as Absolute Schedule
                </button>
                <button
                  onClick={handleDiscard}
                  disabled={loading}
                  className="btn btn-secondary"
                  style={{ fontSize: '0.8rem', padding: '8px 12px', color: '#f87171' }}
                >
                  <Trash2 size={14} /> Discard Draft
                </button>
              </>
            )}

            <button
              onClick={handleGenerateNextMonth}
              disabled={loading || !activeBaseline}
              className="btn btn-secondary"
              style={{ fontSize: '0.8rem', padding: '8px 12px', display: 'flex', alignItems: 'center', gap: '6px' }}
              title="Maps current student recurring attendance patterns onto the next month calendar"
            >
              <Sparkles size={14} style={{ color: 'var(--accent-gold)' }} /> Generate Next-Month Draft
            </button>

            <button
              onClick={handlePromoteEffective}
              disabled={loading}
              className="btn btn-secondary"
              style={{ fontSize: '0.8rem', padding: '8px 12px', display: 'flex', alignItems: 'center', gap: '6px' }}
              title="Promotes current Effective Schedule (excluding single-occurrence ⓒ exceptions) to draft baseline for review"
            >
              <ArrowRight size={14} /> Promote to Baseline
            </button>
          </div>
        </div>
      </div>

      {/* 3. Navigation View Modes (Preview vs Validation vs History) */}
      <div style={{ display: 'flex', gap: '10px', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
        <button
          onClick={() => setActiveViewMode('preview')}
          style={{
            background: activeViewMode === 'preview' ? 'rgba(250, 204, 21, 0.15)' : 'transparent',
            border: activeViewMode === 'preview' ? '1px solid var(--accent-gold)' : '1px solid transparent',
            color: activeViewMode === 'preview' ? '#fff' : 'var(--text-secondary)',
            borderRadius: '8px',
            padding: '8px 16px',
            fontSize: '0.825rem',
            fontWeight: 700,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <Eye size={15} /> Baseline Preview Grid ({filteredStudents.length} Students)
        </button>

        <button
          onClick={() => setActiveViewMode('validation')}
          style={{
            background: activeViewMode === 'validation' ? 'rgba(239, 68, 68, 0.15)' : 'transparent',
            border: activeViewMode === 'validation' ? '1px solid #ef4444' : '1px solid transparent',
            color: activeViewMode === 'validation' ? '#fff' : 'var(--text-secondary)',
            borderRadius: '8px',
            padding: '8px 16px',
            fontSize: '0.825rem',
            fontWeight: 700,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <ShieldAlert size={15} style={{ color: blockingCount > 0 ? '#ef4444' : '#f59e0b' }} />
          Validation Report
          {(blockingCount > 0 || exceptionsCount > 0) && (
            <span className="badge badge-danger" style={{ fontSize: '0.65rem', padding: '1px 6px' }}>
              {blockingCount + exceptionsCount}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveViewMode('history')}
          style={{
            background: activeViewMode === 'history' ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
            border: activeViewMode === 'history' ? '1px solid var(--accent-blue)' : '1px solid transparent',
            color: activeViewMode === 'history' ? '#fff' : 'var(--text-secondary)',
            borderRadius: '8px',
            padding: '8px 16px',
            fontSize: '0.825rem',
            fontWeight: 700,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <History size={15} /> Version History ({statusData?.history?.length || 0})
        </button>
      </div>

      {/* 4. Main View Content */}

      {/* VIEW: Preview Grid */}
      {activeViewMode === 'preview' && (
        <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          
          {/* Filter Bar */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ position: 'relative' }}>
                <Search size={15} style={{ position: 'absolute', left: '10px', top: '10px', color: 'var(--text-muted)' }} />
                <input
                  type="text"
                  placeholder="Search student or ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{
                    background: 'rgba(15, 23, 42, 0.6)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    padding: '8px 12px 8px 32px',
                    color: '#fff',
                    fontSize: '0.8rem',
                    width: '220px'
                  }}
                />
              </div>

              <select
                value={selectedLevel}
                onChange={(e) => setSelectedLevel(e.target.value)}
                style={{
                  background: 'rgba(15, 23, 42, 0.6)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  padding: '8px 12px',
                  color: '#fff',
                  fontSize: '0.8rem'
                }}
              >
                <option value="ALL">All Levels</option>
                <option value="Basic 1">Basic 1</option>
                <option value="Basic 2">Basic 2</option>
                <option value="Beginner 1">Beginner 1</option>
                <option value="Beginner 2">Beginner 2</option>
                <option value="Early Intermediate 1">Early Intermediate 1</option>
                <option value="Early Intermediate 2">Early Intermediate 2</option>
                <option value="Intermediate 1">Intermediate 1</option>
                <option value="Intermediate 2">Intermediate 2</option>
              </select>
            </div>

            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              Showing {filteredStudents.length} of {studentsList.length} students
            </div>
          </div>

          {/* Table Container */}
          <div style={{ overflowX: 'auto', maxHeight: '550px', border: '1px solid var(--border-color)', borderRadius: '10px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.8rem' }}>
              <thead>
                <tr style={{ background: 'rgba(30, 41, 59, 0.9)', position: 'sticky', top: 0, zIndex: 10 }}>
                  <th style={{ padding: '10px 12px', borderBottom: '1px solid var(--border-color)', width: '60px' }}>#</th>
                  <th style={{ padding: '10px 12px', borderBottom: '1px solid var(--border-color)', minWidth: '180px' }}>Student Name</th>
                  <th style={{ padding: '10px 12px', borderBottom: '1px solid var(--border-color)', width: '110px' }}>Student ID</th>
                  <th style={{ padding: '10px 12px', borderBottom: '1px solid var(--border-color)', width: '140px' }}>Level</th>
                  <th style={{ padding: '10px 12px', borderBottom: '1px solid var(--border-color)', width: '90px' }}>Batch</th>
                  <th style={{ padding: '10px 12px', borderBottom: '1px solid var(--border-color)', width: '90px' }}>Planned</th>
                  <th style={{ padding: '10px 12px', borderBottom: '1px solid var(--border-color)', width: '90px' }}>Scheduled</th>
                  <th style={{ padding: '10px 12px', borderBottom: '1px solid var(--border-color)', minWidth: '150px' }}>Notes</th>
                </tr>
              </thead>
              <tbody>
                {filteredStudents.length === 0 ? (
                  <tr>
                    <td colSpan={8} style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
                      No students found in baseline for {selectedMonth}.
                    </td>
                  </tr>
                ) : (
                  filteredStudents.map((s, idx) => (
                    <tr
                      key={s.student_id}
                      style={{
                        borderBottom: '1px solid rgba(51, 65, 85, 0.4)',
                        background: idx % 2 === 0 ? 'rgba(15, 23, 42, 0.3)' : 'transparent'
                      }}
                    >
                      <td style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>{idx + 1}</td>
                      <td style={{ padding: '10px 12px', fontWeight: 700, color: '#fff' }}>{s.student_name}</td>
                      <td style={{ padding: '10px 12px', color: 'var(--accent-blue)', fontFamily: 'monospace' }}>{s.student_id}</td>
                      <td style={{ padding: '10px 12px' }}>
                        <span className="badge badge-gold" style={{ fontSize: '0.7rem', padding: '2px 8px' }}>
                          {s.student_level}
                        </span>
                      </td>
                      <td style={{ padding: '10px 12px' }}>
                        <span className={`badge ${s.batch_type === 'I' ? 'badge-danger' : (s.batch_type === 'L' ? 'badge-blue' : 'badge-gold')}`} style={{ fontSize: '0.7rem' }}>
                          {s.batch_type}
                        </span>
                      </td>
                      <td style={{ padding: '10px 12px', fontWeight: 700, color: '#fff' }}>{s.required_classes || 12}</td>
                      <td style={{ padding: '10px 12px', fontWeight: 800, color: (s.classes_scheduled_count >= (s.required_classes || 12)) ? '#22c55e' : '#f59e0b' }}>
                        {s.classes_scheduled_count || 0}
                      </td>
                      <td style={{ padding: '10px 12px', color: 'var(--text-muted)', fontSize: '0.75rem' }}>{s.note || s.batch_name || '-'}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* VIEW: Validation Report */}
      {activeViewMode === 'validation' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          
          {/* Blocking Errors Card */}
          <div
            className="glass-panel"
            style={{
              padding: '20px',
              border: blockingCount > 0 ? '1px solid #ef4444' : '1px solid var(--border-color)',
              background: blockingCount > 0 ? 'rgba(239, 68, 68, 0.05)' : 'rgba(30, 41, 59, 0.4)'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
              <ShieldAlert size={20} style={{ color: blockingCount > 0 ? '#ef4444' : '#22c55e' }} />
              <h3 style={{ fontSize: '1rem', fontWeight: 800, color: '#fff', margin: 0 }}>
                Blocking Validation Errors ({blockingCount})
              </h3>
            </div>
            {blockingCount === 0 ? (
              <div style={{ fontSize: '0.85rem', color: '#86efac' }}>
                ✓ Zero blocking errors. Baseline structure is 100% valid for activation.
              </div>
            ) : (
              <ul style={{ margin: 0, paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {validationReport.blocking.map((err, idx) => (
                  <li key={idx} style={{ fontSize: '0.85rem', color: '#fca5a5' }}>
                    {err}
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Baseline Exceptions Card (Part E4) */}
          <div
            className="glass-panel"
            style={{
              padding: '20px',
              border: exceptionsCount > 0 ? '1px solid rgba(245, 158, 11, 0.4)' : '1px solid var(--border-color)'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
              <AlertTriangle size={20} style={{ color: '#f59e0b' }} />
              <h3 style={{ fontSize: '1rem', fontWeight: 800, color: '#fff', margin: 0 }}>
                Baseline Exceptions ({exceptionsCount})
              </h3>
            </div>
            <div style={{ fontSize: '0.775rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
              Per Part E4: Baseline exceptions represent historical arrangements in the baseline. They are imported as-is, flagged, never auto-fixed, and are <em>not</em> marked as ⓒ.
            </div>

            {exceptionsCount === 0 ? (
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                No baseline exceptions detected.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '350px', overflowY: 'auto' }}>
                {validationReport.baseline_exceptions.map((exc, idx) => (
                  <div
                    key={idx}
                    style={{
                      background: 'rgba(15, 23, 42, 0.6)',
                      border: '1px solid rgba(245, 158, 11, 0.25)',
                      borderRadius: '8px',
                      padding: '10px 14px'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontWeight: 700, fontSize: '0.85rem', color: '#fff' }}>
                        {exc.rule}
                      </span>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                        {exc.date} · {exc.time_slot} · Coach {exc.coach}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.8rem', color: '#fde68a', marginTop: '2px' }}>
                      {exc.reason}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Info Notes Card */}
          {validationReport.info?.length > 0 && (
            <div className="glass-panel" style={{ padding: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                <Info size={18} style={{ color: 'var(--accent-blue)' }} />
                <h3 style={{ fontSize: '0.95rem', fontWeight: 800, color: '#fff', margin: 0 }}>
                  Information & Synchronization Notes
                </h3>
              </div>
              <ul style={{ margin: 0, paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {validationReport.info.map((note, idx) => (
                  <li key={idx} style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    {note}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* VIEW: Version History */}
      {activeViewMode === 'history' && (
        <div className="glass-panel" style={{ padding: '20px' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 800, color: '#fff', marginBottom: '14px' }}>
            Version History for {selectedMonth}
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {(statusData?.history || []).map((h) => (
              <div
                key={h.id}
                style={{
                  background: 'rgba(15, 23, 42, 0.6)',
                  border: h.status === 'Active' ? '1px solid var(--accent-gold)' : '1px solid var(--border-color)',
                  borderRadius: '10px',
                  padding: '14px 18px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between'
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '1rem', fontWeight: 800, color: '#fff' }}>
                      Version {h.version}
                    </span>
                    <span
                      className={`badge ${h.status === 'Active' ? 'badge-gold' : (h.status === 'Draft' ? 'badge-blue' : 'badge-danger')}`}
                      style={{ fontSize: '0.7rem' }}
                    >
                      {h.status}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                    File: {h.file_name} · Uploaded by: {h.uploaded_by} on {h.uploaded_at}
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: 800, color: '#fff' }}>
                      {h.student_count} Students · {h.class_count} Classes
                    </div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                      {h.student_class_count} Seats
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
}
