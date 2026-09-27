import React, { useState, useEffect, useMemo } from 'react';
import { createPortal } from 'react-dom';
import {
  Users, Award, Layers, Search, Plus, Edit2, Trash2,
  Save, X, RefreshCw, Check, AlertCircle, Shield, UserCheck, Calendar
} from 'lucide-react';
import {
  getMasterData, getMasterStats, saveMasterStudent, deleteMasterStudent,
  saveMasterCoach, deleteMasterCoach, saveMasterBatch, deleteMasterBatch,
  clearAllMasterData
} from '../services/api';
import BatchesTab from './BatchesTab';
import { OFFICIAL_LEVELS } from '../constants/levels';

const STANDARD_LEVELS = OFFICIAL_LEVELS;

export default function MasterDataView({ onReRunScheduler, onClearSchedule, onRefreshSchedule }) {
  const [activeSubTab, setActiveSubTab] = useState('batches'); // 'batches' | 'students' | 'coaches'
  const [students, setStudents] = useState([]);
  const [coaches, setCoaches] = useState([]);
  const [batches, setBatches] = useState([]);
  const [loading, setLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');

  // Search & Filter state for Students & Coaches
  const [studentSearch, setStudentSearch] = useState('');
  const [studentLevelFilter, setStudentLevelFilter] = useState('ALL');
  const [studentTypeFilter, setStudentTypeFilter] = useState('ALL');

  const [coachSearch, setCoachSearch] = useState('');
  const [coachLevelFilter, setCoachLevelFilter] = useState('ALL');

  // Editing Modals
  const [editingStudent, setEditingStudent] = useState(null);
  const [editingCoach, setEditingCoach] = useState(null);

  useEffect(() => {
    fetchMasterData();
  }, []);

  const fetchMasterData = async () => {
    setLoading(true);
    try {
      const data = await getMasterData();
      if (data) {
        setStudents(data.students || []);
        setCoaches(data.coaches || []);
        setBatches(data.batches || []);
      }
    } catch (err) {
      console.error('Failed to fetch master data:', err);
    } finally {
      setLoading(false);
    }
  };

  const showNotification = (msg) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(''), 3500);
  };

  // ----------------------------------------------------
  // DASHBOARD STATISTICS COMPUTATION
  // ----------------------------------------------------
  const stats = useMemo(() => {
    const totalBatches = batches.length;
    const totalStudents = students.length;
    const totalCoaches = coaches.length;
    const groupBatches = batches.filter(b => b.batch_type === 'G').length;
    const limitedBatches = batches.filter(b => b.batch_type === 'L').length;
    const individualBatches = batches.filter(b => b.batch_type === 'I').length;
    return { totalBatches, totalStudents, totalCoaches, groupBatches, limitedBatches, individualBatches };
  }, [batches, students, coaches]);

  // ----------------------------------------------------
  // STUDENT CRUD
  // ----------------------------------------------------
  const handleSaveStudent = async (studentData) => {
    try {
      await saveMasterStudent(studentData);
      showNotification(`Saved student ${studentData.student_name} (${studentData.student_id})`);
      setEditingStudent(null);
      await fetchMasterData();
      if (onRefreshSchedule) await onRefreshSchedule();
    } catch (err) {
      alert('Failed to save student: ' + err.message);
    }
  };

  const handleDeleteStudent = async (studentId) => {
    if (!window.confirm(`Delete student ${studentId}? This will also unlink them from any enrolled batches.`)) return;
    try {
      await deleteMasterStudent(studentId);
      // Optimistically remove from local state immediately so UI feels instant
      setStudents(prev => prev.filter(s => s.student_id !== studentId));
      showNotification(`Deleted student ${studentId}`);
      // Then sync full data from server
      await fetchMasterData();
      if (onRefreshSchedule) await onRefreshSchedule();
    } catch (err) {
      console.error('Delete failed:', err);
      alert('Failed to delete student: ' + (err?.response?.data?.detail || err.message));
      // Re-sync in case of partial failure
      await fetchMasterData();
    }
  };

  // ----------------------------------------------------
  // COACH / TRAINER CRUD
  // ----------------------------------------------------
  const handleSaveCoach = async (coachData) => {
    try {
      await saveMasterCoach(coachData);
      showNotification(`Saved trainer ${coachData.coach_name}`);
      setEditingCoach(null);
      await fetchMasterData();
    } catch (err) {
      alert('Failed to save coach: ' + err.message);
    }
  };

  const handleDeleteCoach = async (coachName) => {
    if (!window.confirm(`Are you sure you want to delete trainer ${coachName}? Batches assigned to this trainer will be set to Unassigned.`)) return;
    try {
      await deleteMasterCoach(coachName);
      showNotification(`Deleted trainer ${coachName}`);
      await fetchMasterData();
    } catch (err) {
      alert('Failed to delete coach: ' + err.message);
    }
  };

  // ----------------------------------------------------
  // BATCH CRUD
  // ----------------------------------------------------
  const handleSaveBatch = async (batchData) => {
    try {
      await saveMasterBatch(batchData);
      showNotification(`Saved batch ${batchData.batch_name}`);
      await fetchMasterData();
    } catch (err) {
      alert('Failed to save batch: ' + err.message);
    }
  };

  const handleDeleteBatch = async (batchId) => {
    try {
      await deleteMasterBatch(batchId);
      showNotification(`Deleted batch ${batchId}`);
      await fetchMasterData();
    } catch (err) {
      alert('Failed to delete batch: ' + err.message);
    }
  };

  // Clear All Master Data
  const handleClearAllMasterData = async () => {
    if (!window.confirm('⚠️ Are you sure you want to delete ALL batches, students, trainers, and active schedules to start fresh from scratch?\n\nThis action cannot be undone.')) {
      return;
    }
    setLoading(true);
    try {
      await clearAllMasterData();
      showNotification('All Master Data cleared! You are starting completely from scratch.');
      await fetchMasterData();
      if (onClearSchedule) {
        onClearSchedule();
      }
    } catch (err) {
      alert('Failed to clear master data: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // Filtered Students (Sorted alphabetically A-Z by student name)
  const filteredStudents = useMemo(() => {
    const list = students.filter(s => {
      if (studentTypeFilter !== 'ALL' && s.batch_type !== studentTypeFilter) return false;
      if (studentLevelFilter !== 'ALL' && s.student_level !== studentLevelFilter) return false;
      if (studentSearch.trim()) {
        const q = studentSearch.toLowerCase();
        const matchesName = (s.student_name || '').toLowerCase().includes(q);
        const matchesId = (s.student_id || '').toLowerCase().includes(q);
        const matchesLevel = (s.student_level || '').toLowerCase().includes(q);
        const matchesRegion = (s.region_timezone || '').toLowerCase().includes(q);
        return matchesName || matchesId || matchesLevel || matchesRegion;
      }
      return true;
    });

    // Sort alphabetically by student name
    return list.sort((a, b) => (a.student_name || '').localeCompare(b.student_name || ''));
  }, [students, studentSearch, studentLevelFilter, studentTypeFilter]);

  // Filtered Coaches
  const filteredCoaches = useMemo(() => {
    return coaches.filter(c => {
      if (coachLevelFilter !== 'ALL') {
        const levels = Array.isArray(c.levels_handled) ? c.levels_handled : [];
        if (!levels.some(l => l.toLowerCase() === coachLevelFilter.toLowerCase())) return false;
      }
      if (coachSearch.trim()) {
        const q = coachSearch.toLowerCase();
        const matchesName = (c.coach_name || '').toLowerCase().includes(q);
        const matchesLevels = (Array.isArray(c.levels_handled) ? c.levels_handled.join(', ') : '').toLowerCase().includes(q);
        return matchesName || matchesLevels;
      }
      return true;
    });
  }, [coaches, coachSearch, coachLevelFilter]);

  return (
    <div className="glass-panel" style={{ padding: '24px' }}>
      {/* ---------------------------------------------------- */}
      {/* 1. HEADER ROW */}
      {/* ---------------------------------------------------- */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '10px' }}>
            👥 Master Data Management Hub
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Central master-data source of truth for batches, students, and trainers. All changes persist to the database and drive the scheduling engine.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
          <button
            onClick={handleClearAllMasterData}
            disabled={loading}
            className="btn btn-secondary"
            style={{
              padding: '10px 16px',
              background: 'rgba(239, 68, 68, 0.15)',
              borderColor: 'rgba(239, 68, 68, 0.5)',
              color: '#ef4444',
              fontWeight: 700,
              fontSize: '0.85rem',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
            title="Wipe all master batches, students, trainers and restart from scratch"
          >
            <Trash2 size={16} /> Reset to Scratch / Clear All
          </button>

          <button
            onClick={() => onReRunScheduler && onReRunScheduler()}
            className="btn btn-primary"
            style={{
              padding: '10px 18px',
              background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
              border: 'none',
              color: '#000',
              fontWeight: 800,
              fontSize: '0.85rem',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <RefreshCw size={16} /> Re-Run Engine on Updated Data
          </button>
        </div>
      </div>

      {/* SUCCESS NOTIFICATION TOAST */}
      {successMsg && (
        <div style={{ padding: '12px 16px', background: 'rgba(16, 185, 129, 0.2)', border: '1px solid #10b981', color: '#10b981', borderRadius: 'var(--radius-md)', marginBottom: '18px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem' }}>
          <Check size={18} /> {successMsg}
        </div>
      )}

      {/* ---------------------------------------------------- */}
      {/* 2. DASHBOARD METRICS: 6 KEY STATS CARDS */}
      {/* ---------------------------------------------------- */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '14px', marginBottom: '22px' }}>
        {/* Total Batches */}
        <div className="glass-panel" style={{ padding: '14px 18px', display: 'flex', alignItems: 'center', gap: '14px', borderLeft: '4px solid var(--accent-gold)' }}>
          <div style={{ padding: '10px', borderRadius: '10px', background: 'rgba(234, 179, 8, 0.15)', color: 'var(--accent-gold)' }}>
            <Layers size={22} />
          </div>
          <div>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#fff' }}>{stats.totalBatches}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Total Batches</div>
          </div>
        </div>

        {/* Total Students */}
        <div className="glass-panel" style={{ padding: '14px 18px', display: 'flex', alignItems: 'center', gap: '14px', borderLeft: '4px solid #60a5fa' }}>
          <div style={{ padding: '10px', borderRadius: '10px', background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa' }}>
            <Users size={22} />
          </div>
          <div>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#60a5fa' }}>{stats.totalStudents}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Total Students</div>
          </div>
        </div>

        {/* Total Trainers */}
        <div className="glass-panel" style={{ padding: '14px 18px', display: 'flex', alignItems: 'center', gap: '14px', borderLeft: '4px solid #10b981' }}>
          <div style={{ padding: '10px', borderRadius: '10px', background: 'rgba(16, 185, 129, 0.15)', color: '#10b981' }}>
            <Award size={22} />
          </div>
          <div>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#10b981' }}>{stats.totalCoaches}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Total Trainers</div>
          </div>
        </div>

        {/* Group Batches (G) */}
        <div className="glass-panel" style={{ padding: '14px 18px', display: 'flex', alignItems: 'center', gap: '14px', borderLeft: '4px solid #38bdf8' }}>
          <div style={{ padding: '10px', borderRadius: '10px', background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8' }}>
            <Users size={22} />
          </div>
          <div>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#38bdf8' }}>{stats.groupBatches}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Group Batches (G)</div>
          </div>
        </div>

        {/* Limited Batches (L) */}
        <div className="glass-panel" style={{ padding: '14px 18px', display: 'flex', alignItems: 'center', gap: '14px', borderLeft: '4px solid #c084fc' }}>
          <div style={{ padding: '10px', borderRadius: '10px', background: 'rgba(168, 85, 247, 0.15)', color: '#c084fc' }}>
            <Shield size={22} />
          </div>
          <div>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#c084fc' }}>{stats.limitedBatches}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Limited Batches (L)</div>
          </div>
        </div>

        {/* Individual Batches (I) */}
        <div className="glass-panel" style={{ padding: '14px 18px', display: 'flex', alignItems: 'center', gap: '14px', borderLeft: '4px solid #facc15' }}>
          <div style={{ padding: '10px', borderRadius: '10px', background: 'rgba(250, 204, 21, 0.15)', color: '#facc15' }}>
            <UserCheck size={22} />
          </div>
          <div>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#facc15' }}>{stats.individualBatches}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Individual 1-on-1 (I)</div>
          </div>
        </div>
      </div>

      {/* ---------------------------------------------------- */}
      {/* 3. SIMPLIFIED 3-TAB NAVIGATION */}
      {/* ---------------------------------------------------- */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '22px', borderBottom: '1px solid var(--border-color)', paddingBottom: '14px' }}>
        <button
          onClick={() => setActiveSubTab('batches')}
          style={{
            padding: '10px 22px',
            borderRadius: 'var(--radius-md)',
            border: activeSubTab === 'batches' ? '1px solid var(--accent-gold)' : '1px solid var(--border-color)',
            background: activeSubTab === 'batches' ? 'rgba(234, 179, 8, 0.15)' : 'var(--bg-secondary)',
            color: activeSubTab === 'batches' ? 'var(--accent-gold)' : 'var(--text-secondary)',
            fontWeight: 800,
            fontSize: '0.9rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            transition: 'all 0.15s ease'
          }}
        >
          <Layers size={18} /> Groups / Batches ({batches.length})
        </button>

        <button
          onClick={() => setActiveSubTab('students')}
          style={{
            padding: '10px 22px',
            borderRadius: 'var(--radius-md)',
            border: activeSubTab === 'students' ? '1px solid #60a5fa' : '1px solid var(--border-color)',
            background: activeSubTab === 'students' ? 'rgba(59, 130, 246, 0.15)' : 'var(--bg-secondary)',
            color: activeSubTab === 'students' ? '#60a5fa' : 'var(--text-secondary)',
            fontWeight: 800,
            fontSize: '0.9rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            transition: 'all 0.15s ease'
          }}
        >
          <Users size={18} /> Students ({students.length})
        </button>

        <button
          onClick={() => setActiveSubTab('coaches')}
          style={{
            padding: '10px 22px',
            borderRadius: 'var(--radius-md)',
            border: activeSubTab === 'coaches' ? '1px solid #c084fc' : '1px solid var(--border-color)',
            background: activeSubTab === 'coaches' ? 'rgba(168, 85, 247, 0.15)' : 'var(--bg-secondary)',
            color: activeSubTab === 'coaches' ? '#c084fc' : 'var(--text-secondary)',
            fontWeight: 800,
            fontSize: '0.9rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            transition: 'all 0.15s ease'
          }}
        >
          <Award size={18} /> Trainers ({coaches.length})
        </button>
      </div>

      {/* ---------------------------------------------------- */}
      {/* 4. TAB CONTENT 1: BATCHES */}
      {/* ---------------------------------------------------- */}
      {activeSubTab === 'batches' && (
        <BatchesTab
          batches={batches}
          allStudents={students}
          allCoaches={coaches}
          onSaveBatch={handleSaveBatch}
          onDeleteBatch={handleDeleteBatch}
          loading={loading}
        />
      )}

      {/* ---------------------------------------------------- */}
      {/* 5. TAB CONTENT 2: STUDENTS */}
      {/* ---------------------------------------------------- */}
      {activeSubTab === 'students' && (
        <div>
          {/* SEARCH, FILTERS & ACTION ROW */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px', marginBottom: '18px', background: 'rgba(255,255,255,0.02)', padding: '14px', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
            {/* Search Bar */}
            <div style={{ position: 'relative', flex: 1, minWidth: '240px' }}>
              <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                type="text"
                placeholder="Search student name, ID, level, or region..."
                value={studentSearch}
                onChange={e => setStudentSearch(e.target.value)}
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

            <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
              {/* Type Filter */}
              <div style={{ display: 'flex', background: 'var(--bg-secondary)', padding: '3px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
                {['ALL', 'G', 'L', 'I'].map(t => (
                  <button
                    key={t}
                    onClick={() => setStudentTypeFilter(t)}
                    style={{
                      padding: '5px 12px',
                      borderRadius: '5px',
                      border: 'none',
                      background: studentTypeFilter === t ? '#3b82f6' : 'transparent',
                      color: studentTypeFilter === t ? '#fff' : 'var(--text-secondary)',
                      fontWeight: 700,
                      fontSize: '0.75rem',
                      cursor: 'pointer'
                    }}
                  >
                    {t === 'ALL' ? 'All Types' : (t === 'G' ? 'Group' : (t === 'L' ? 'Limited' : 'Individual'))}
                  </button>
                ))}
              </div>

              {/* Level Filter */}
              <select
                value={studentLevelFilter}
                onChange={e => setStudentLevelFilter(e.target.value)}
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
                {STANDARD_LEVELS.map(lvl => (
                  <option key={lvl} value={lvl}>{lvl}</option>
                ))}
              </select>

              {/* Student Count Badge (A-Z) */}
              <span className="badge badge-gold" style={{ fontSize: '0.75rem', padding: '6px 12px', fontWeight: 700 }}>
                {filteredStudents.length} Students (A–Z)
              </span>

              {/* Add New Student Button */}
              <button
                onClick={() => {
                  const newId = `STU_${Date.now().toString().slice(-4)}`;
                  setEditingStudent({
                    student_id: newId,
                    student_name: '',
                    student_level: 'Beginner 1',
                    batch_type: 'G',
                    required_classes: 8,
                    region_timezone: 'IST',
                    mon_pref: 'No Preference',
                    tue_pref: 'No Preference',
                    wed_pref: 'No Preference',
                    thu_pref: 'No Preference',
                    fri_pref: 'No Preference',
                    sat_pref: 'No Preference',
                    sun_pref: 'No Preference',
                    assigned_batch_id: '',
                    tournament_pref: 'No',
                    additional_comments: ''
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
                  background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
                  border: 'none',
                  color: '#fff'
                }}
              >
                <Plus size={16} /> Add New Student
              </button>
            </div>
          </div>

          {/* STUDENTS DATA TABLE */}
          {filteredStudents.length === 0 ? (
            <div className="glass-panel" style={{ padding: '60px 20px', textAlign: 'center', color: 'var(--text-secondary)' }}>
              <Users size={48} style={{ color: 'var(--border-color)', marginBottom: '16px' }} />
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff', marginBottom: '8px' }}>
                No students found
              </h3>
              <p style={{ fontSize: '0.85rem', maxWidth: '400px', margin: '0 auto 20px auto' }}>
                {studentSearch || studentLevelFilter !== 'ALL' || studentTypeFilter !== 'ALL'
                  ? 'No students match your filter criteria. Try clearing search or filters.'
                  : 'Start by creating master student records with skill levels, availability preferences, and required monthly classes.'}
              </p>
              <button
                onClick={() => {
                  const newId = `STU_${Date.now().toString().slice(-4)}`;
                  setEditingStudent({
                    student_id: newId,
                    student_name: '',
                    student_level: 'Beginner 1',
                    batch_type: 'G',
                    required_classes: 8,
                    region_timezone: 'IST',
                    assigned_batch_id: '',
                    tournament_pref: 'No'
                  });
                }}
                className="btn btn-primary"
                style={{ padding: '10px 20px', fontWeight: 700, fontSize: '0.85rem' }}
              >
                <Plus size={16} /> + Add First Student
              </button>
            </div>
          ) : (
            <div className="glass-panel" style={{ overflowX: 'auto', padding: '0', borderRadius: 'var(--radius-lg)' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                <thead>
                  <tr style={{ background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                    <th style={{ padding: '14px 12px', fontWeight: 700, color: 'var(--text-secondary)', width: '50px', textAlign: 'center', whiteSpace: 'nowrap' }}>#</th>
                    <th style={{ padding: '14px 16px', fontWeight: 700, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>Student Name & ID</th>
                    <th style={{ padding: '14px 16px', fontWeight: 700, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>Rating</th>
                    <th style={{ padding: '14px 16px', fontWeight: 700, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>Level</th>
                    <th style={{ padding: '14px 16px', fontWeight: 700, color: 'var(--text-secondary)', whiteSpace: 'nowrap', minWidth: '110px' }}>Batch Type</th>
                    <th style={{ padding: '14px 16px', fontWeight: 700, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>Req Classes</th>
                    <th style={{ padding: '14px 16px', fontWeight: 700, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>Region / TZ</th>
                    <th style={{ padding: '14px 16px', fontWeight: 700, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>Assigned Batch</th>
                    <th style={{ padding: '14px 16px', fontWeight: 700, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>Weekly Availability</th>
                    <th style={{ padding: '14px 16px', fontWeight: 700, color: 'var(--text-secondary)', textAlign: 'center', whiteSpace: 'nowrap' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredStudents.map((student, index) => {
                    // Check if student belongs to any batch
                    const assignedBatch = batches.find(b =>
                      (b.student_ids || []).includes(student.student_id) ||
                      (b.students || []).some(s => s.student_id === student.student_id)
                    );

                    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
                    const dayKeys = ['mon_pref', 'tue_pref', 'wed_pref', 'thu_pref', 'fri_pref', 'sat_pref', 'sun_pref'];

                    return (
                      <tr
                        key={student.student_id}
                        style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', transition: 'background 0.15s ease' }}
                        onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
                        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                      >
                        <td style={{ padding: '14px 12px', textAlign: 'center', width: '50px', whiteSpace: 'nowrap' }}>
                          <span style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            minWidth: '28px',
                            height: '24px',
                            padding: '0 6px',
                            borderRadius: '6px',
                            background: 'rgba(255,255,255,0.06)',
                            color: 'var(--text-muted)',
                            fontSize: '0.75rem',
                            fontWeight: 700,
                            fontFamily: 'monospace'
                          }}>
                            {index + 1}
                          </span>
                        </td>

                        <td style={{ padding: '14px 16px', whiteSpace: 'nowrap' }}>
                          <div style={{ fontWeight: 800, color: '#fff', fontSize: '0.9rem' }}>{student.student_name}</div>
                          <div style={{ fontSize: '0.725rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>{student.student_id}</div>
                        </td>

                        <td style={{ padding: '14px 16px', whiteSpace: 'nowrap' }}>
                          {student.mkca_rating != null && student.mkca_rating !== '' ? (
                            <span style={{
                              padding: '3px 9px',
                              borderRadius: '12px',
                              background: 'rgba(234, 179, 8, 0.15)',
                              color: 'var(--accent-gold)',
                              fontSize: '0.8rem',
                              fontWeight: 800,
                              fontFamily: 'monospace',
                              letterSpacing: '0.02em',
                              whiteSpace: 'nowrap'
                            }}>
                              ♟ {student.mkca_rating}
                            </span>
                          ) : (
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontStyle: 'italic' }}>—</span>
                          )}
                        </td>

                        <td style={{ padding: '14px 16px', whiteSpace: 'nowrap' }}>
                          <span style={{ padding: '3px 9px', borderRadius: '12px', background: 'rgba(255,255,255,0.06)', color: '#e2e8f0', fontSize: '0.75rem', fontWeight: 600, whiteSpace: 'nowrap' }}>
                            {student.student_level || 'Beginner'}
                          </span>
                        </td>

                        <td style={{ padding: '14px 16px', whiteSpace: 'nowrap' }}>
                          <span style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            whiteSpace: 'nowrap',
                            padding: '4px 10px',
                            borderRadius: '6px',
                            background: student.batch_type === 'G' ? 'rgba(59, 130, 246, 0.2)' : (student.batch_type === 'L' ? 'rgba(168, 85, 247, 0.2)' : 'rgba(234, 179, 8, 0.2)'),
                            color: student.batch_type === 'G' ? '#60a5fa' : (student.batch_type === 'L' ? '#c084fc' : '#facc15'),
                            border: `1px solid ${student.batch_type === 'G' ? 'rgba(59, 130, 246, 0.35)' : (student.batch_type === 'L' ? 'rgba(168, 85, 247, 0.35)' : 'rgba(234, 179, 8, 0.35)')}`,
                            fontWeight: 700,
                            fontSize: '0.75rem',
                            letterSpacing: '0.01em',
                            lineHeight: 1.2
                          }}>
                            {student.batch_type === 'G' ? 'Group (G)' : (student.batch_type === 'L' ? 'Limited (L)' : 'Individual (I)')}
                          </span>
                        </td>

                        <td style={{ padding: '14px 16px', fontWeight: 700, color: '#fff', whiteSpace: 'nowrap' }}>
                          {student.required_classes ?? 8} / mo
                        </td>

                        <td style={{ padding: '14px 16px', color: 'var(--text-secondary)', fontSize: '0.8rem', whiteSpace: 'nowrap' }}>
                          {student.region_timezone || 'IST'}
                        </td>

                        <td style={{ padding: '14px 16px', whiteSpace: 'nowrap' }}>
                          {assignedBatch ? (
                            <span style={{ padding: '3px 8px', borderRadius: '6px', background: 'rgba(234, 179, 8, 0.15)', color: 'var(--accent-gold)', fontWeight: 700, fontSize: '0.75rem', whiteSpace: 'nowrap' }}>
                              {assignedBatch.batch_name}
                            </span>
                          ) : (
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontStyle: 'italic', whiteSpace: 'nowrap' }}>
                              Unassigned
                            </span>
                          )}
                        </td>

                        <td style={{ padding: '14px 16px', whiteSpace: 'nowrap' }}>
                          <div style={{ display: 'flex', gap: '3px', flexWrap: 'nowrap' }}>
                            {days.map((d, dIdx) => {
                              const pref = String(student[dayKeys[dIdx]] || '').toLowerCase();
                              const isOff = ['not available', 'na', 'no', 'false', '0', 'off'].includes(pref);
                              return (
                                <span
                                  key={d}
                                  title={`${d}: ${student[dayKeys[dIdx]] || 'Available'}`}
                                  style={{
                                    width: '20px',
                                    height: '20px',
                                    borderRadius: '4px',
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    fontSize: '0.65rem',
                                    fontWeight: 700,
                                    background: isOff ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                                    color: isOff ? '#f87171' : '#34d399'
                                  }}
                                >
                                  {d[0]}
                                </span>
                              );
                            })}
                          </div>
                        </td>

                        <td style={{ padding: '14px 16px', textAlign: 'center' }}>
                          <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
                            <button
                              onClick={() => setEditingStudent({ ...student, assigned_batch_id: assignedBatch?.batch_id || '' })}
                              style={{
                                padding: '6px 10px',
                                borderRadius: '6px',
                                background: 'rgba(96, 165, 250, 0.15)',
                                border: '1px solid rgba(96, 165, 250, 0.3)',
                                color: '#60a5fa',
                                cursor: 'pointer'
                              }}
                              title="Edit Student"
                            >
                              <Edit2 size={14} />
                            </button>
                            <button
                              onClick={() => handleDeleteStudent(student.student_id)}
                              style={{
                                padding: '6px 10px',
                                borderRadius: '6px',
                                background: 'rgba(239, 68, 68, 0.15)',
                                border: '1px solid rgba(239, 68, 68, 0.3)',
                                color: '#ef4444',
                                cursor: 'pointer'
                              }}
                              title="Delete Student"
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ---------------------------------------------------- */}
      {/* 6. TAB CONTENT 3: TRAINERS */}
      {/* ---------------------------------------------------- */}
      {activeSubTab === 'coaches' && (
        <div>
          {/* SEARCH, FILTERS & ACTION ROW */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px', marginBottom: '18px', background: 'rgba(255,255,255,0.02)', padding: '14px', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
            {/* Search Bar */}
            <div style={{ position: 'relative', flex: 1, minWidth: '240px' }}>
              <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                type="text"
                placeholder="Search trainer name, handled levels..."
                value={coachSearch}
                onChange={e => setCoachSearch(e.target.value)}
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

            <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
              {/* Level Filter */}
              <select
                value={coachLevelFilter}
                onChange={e => setCoachLevelFilter(e.target.value)}
                style={{
                  padding: '7px 12px',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-color)',
                  color: '#fff',
                  fontSize: '0.8rem'
                }}
              >
                <option value="ALL">All Levels Handled</option>
                {STANDARD_LEVELS.map(lvl => (
                  <option key={lvl} value={lvl}>{lvl}</option>
                ))}
              </select>

              {/* Add New Trainer Button */}
              <button
                onClick={() => {
                  setEditingCoach({
                    coach_name: '',
                    levels_handled: ['Basic 1', 'Basic 2', 'Beginner 1'],
                    monthly_capacity_min: 20,
                    monthly_capacity_max: 60,
                    mon_max: 4,
                    tue_max: 4,
                    wed_max: 4,
                    thu_max: 4,
                    fri_max: 4,
                    sat_max: 5,
                    sun_max: 2,
                    sunday_pref: 'Available',
                    sunday_max_classes: 2,
                    preferred_timings: 'No Preference',
                    special_comments: ''
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
                  background: 'linear-gradient(135deg, #a855f7 0%, #7e22ce 100%)',
                  border: 'none',
                  color: '#fff'
                }}
              >
                <Plus size={16} /> Add New Trainer
              </button>
            </div>
          </div>

          {/* TRAINERS DATA TABLE */}
          {filteredCoaches.length === 0 ? (
            <div className="glass-panel" style={{ padding: '60px 20px', textAlign: 'center', color: 'var(--text-secondary)' }}>
              <Award size={48} style={{ color: 'var(--border-color)', marginBottom: '16px' }} />
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff', marginBottom: '8px' }}>
                No trainers found
              </h3>
              <p style={{ fontSize: '0.85rem', maxWidth: '400px', margin: '0 auto 20px auto' }}>
                {coachSearch || coachLevelFilter !== 'ALL'
                  ? 'No trainers match your filter criteria. Try clearing search or filters.'
                  : 'Start by creating master trainer profiles with skill capabilities, monthly target hours, and daily working limits.'}
              </p>
              <button
                onClick={() => {
                  setEditingCoach({
                    coach_name: '',
                    levels_handled: ['Basic 1', 'Beginner 1'],
                    monthly_capacity_min: 20,
                    monthly_capacity_max: 60,
                    mon_max: 4,
                    tue_max: 4,
                    wed_max: 4,
                    thu_max: 4,
                    fri_max: 4,
                    sat_max: 5,
                    sun_max: 2,
                    sunday_pref: 'Available'
                  });
                }}
                className="btn btn-primary"
                style={{ padding: '10px 20px', fontWeight: 700, fontSize: '0.85rem' }}
              >
                <Plus size={16} /> + Add First Trainer
              </button>
            </div>
          ) : (
            <div className="glass-panel" style={{ overflowX: 'auto', padding: '0', borderRadius: 'var(--radius-lg)' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                <thead>
                  <tr style={{ background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                    <th style={{ padding: '14px 16px', fontWeight: 700, color: 'var(--text-secondary)' }}>Trainer Name</th>
                    <th style={{ padding: '14px 16px', fontWeight: 700, color: 'var(--text-secondary)' }}>Levels Handled</th>
                    <th style={{ padding: '14px 16px', fontWeight: 700, color: 'var(--text-secondary)' }}>Monthly Target</th>
                    <th style={{ padding: '14px 16px', fontWeight: 700, color: 'var(--text-secondary)' }}>Daily Max Limits</th>
                    <th style={{ padding: '14px 16px', fontWeight: 700, color: 'var(--text-secondary)' }}>Sunday Max</th>
                    <th style={{ padding: '14px 16px', fontWeight: 700, color: 'var(--text-secondary)' }}>Assigned Batches</th>
                    <th style={{ padding: '14px 16px', fontWeight: 700, color: 'var(--text-secondary)', textAlign: 'center' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredCoaches.map(coach => {
                    const assignedBatches = batches.filter(b => (b.fixed_trainer || '').toLowerCase() === coach.coach_name.toLowerCase());
                    const levels = Array.isArray(coach.levels_handled) ? coach.levels_handled : [];

                    return (
                      <tr
                        key={coach.coach_name}
                        style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', transition: 'background 0.15s ease' }}
                        onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
                        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                      >
                        <td style={{ padding: '14px 16px' }}>
                          <div style={{ fontWeight: 800, color: '#fff', fontSize: '0.9rem' }}>{coach.coach_name}</div>
                        </td>

                        <td style={{ padding: '14px 16px' }}>
                          <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', maxWidth: '280px' }}>
                            {levels.map((l, lIdx) => (
                              <span key={lIdx} style={{ padding: '2px 7px', borderRadius: '4px', background: 'rgba(168, 85, 247, 0.15)', color: '#c084fc', fontSize: '0.725rem', fontWeight: 600 }}>
                                {l}
                              </span>
                            ))}
                          </div>
                        </td>

                        <td style={{ padding: '14px 16px' }}>
                          <span style={{ fontWeight: 800, color: '#10b981' }}>{coach.monthly_capacity_min ?? 0}</span>
                          <span style={{ color: 'var(--text-muted)' }}> - </span>
                          <span style={{ fontWeight: 800, color: '#38bdf8' }}>{coach.monthly_capacity_max ?? 100}</span>
                          <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}> / mo</span>
                        </td>

                        <td style={{ padding: '14px 16px', color: 'var(--text-secondary)', fontSize: '0.775rem' }}>
                          {(() => {
                            const sameWk = coach.mon_max === coach.tue_max && coach.mon_max === coach.wed_max && coach.mon_max === coach.thu_max && coach.mon_max === coach.fri_max;
                            return sameWk ? (
                              <span>M-F: {coach.mon_max ?? 4} | Sat: {coach.sat_max ?? 5} | Sun: {coach.sun_max ?? 2}</span>
                            ) : (
                              <span title={`Mon: ${coach.mon_max}, Tue: ${coach.tue_max}, Wed: ${coach.wed_max}, Thu: ${coach.thu_max}, Fri: ${coach.fri_max}, Sat: ${coach.sat_max}, Sun: ${coach.sun_max}`}>
                                M:{coach.mon_max} T:{coach.tue_max} W:{coach.wed_max} Th:{coach.thu_max} F:{coach.fri_max} | Sa:{coach.sat_max} Su:{coach.sun_max}
                              </span>
                            );
                          })()}
                        </td>

                        <td style={{ padding: '14px 16px' }}>
                          <span style={{
                            padding: '3px 8px',
                            borderRadius: '6px',
                            background: coach.sunday_pref === 'Off' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                            color: coach.sunday_pref === 'Off' ? '#f87171' : '#34d399',
                            fontSize: '0.75rem',
                            fontWeight: 700
                          }}>
                            {coach.sunday_pref === 'Off' ? 'Off' : `${coach.sunday_max_classes ?? coach.sun_max ?? 2} max`}
                          </span>
                        </td>

                        <td style={{ padding: '14px 16px' }}>
                          <span style={{
                            padding: '4px 10px',
                            borderRadius: '6px',
                            background: assignedBatches.length > 0 ? 'rgba(234, 179, 8, 0.15)' : 'rgba(255,255,255,0.05)',
                            color: assignedBatches.length > 0 ? 'var(--accent-gold)' : 'var(--text-muted)',
                            fontWeight: 700,
                            fontSize: '0.75rem'
                          }}>
                            {assignedBatches.length} Batches
                          </span>
                        </td>

                        <td style={{ padding: '14px 16px', textAlign: 'center' }}>
                          <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
                            <button
                              onClick={() => setEditingCoach({ ...coach })}
                              style={{
                                padding: '6px 10px',
                                borderRadius: '6px',
                                background: 'rgba(192, 132, 252, 0.15)',
                                border: '1px solid rgba(192, 132, 252, 0.3)',
                                color: '#c084fc',
                                cursor: 'pointer'
                              }}
                              title="Edit Trainer"
                            >
                              <Edit2 size={14} />
                            </button>
                            <button
                              onClick={() => handleDeleteCoach(coach.coach_name)}
                              style={{
                                padding: '6px 10px',
                                borderRadius: '6px',
                                background: 'rgba(239, 68, 68, 0.15)',
                                border: '1px solid rgba(239, 68, 68, 0.3)',
                                color: '#ef4444',
                                cursor: 'pointer'
                              }}
                              title="Delete Trainer"
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ---------------------------------------------------- */}
      {/* 7. STUDENT EDIT / ADD MODAL */}
      {/* ---------------------------------------------------- */}
      {editingStudent && (
        <StudentEditModal
          student={editingStudent}
          allBatches={batches}
          onSave={handleSaveStudent}
          onClose={() => setEditingStudent(null)}
        />
      )}

      {/* ---------------------------------------------------- */}
      {/* 8. COACH / TRAINER EDIT / ADD MODAL */}
      {/* ---------------------------------------------------- */}
      {editingCoach && (
        <CoachEditModal
          coach={editingCoach}
          onSave={handleSaveCoach}
          onClose={() => setEditingCoach(null)}
        />
      )}
    </div>
  );
}

// 1-hour time slots 05:00 AM → 11:00 PM (including intermediate slots like 08:30 PM)
const TIME_SLOTS = [
  '05:00 AM','06:00 AM','07:00 AM','08:00 AM','09:00 AM','10:00 AM','11:00 AM',
  '12:00 PM','01:00 PM','02:00 PM','03:00 PM','04:00 PM',
  '05:00 PM','06:00 PM','07:00 PM','08:00 PM','08:30 PM','09:00 PM','10:00 PM','11:00 PM'
];

// ----------------------------------------------------
// STUDENT EDIT / ADD MODAL COMPONENT
// ----------------------------------------------------
function StudentEditModal({ student, allBatches, onSave, onClose }) {
  const [formData, setFormData] = useState({
    student_id: student.student_id || `STU_${Date.now().toString().slice(-4)}`,
    student_name: student.student_name || '',
    mkca_rating: student.mkca_rating ?? '',
    student_level: student.student_level || 'Beginner 1',
    batch_type: student.batch_type || 'G',
    required_classes: student.required_classes ?? 8,
    region_timezone: student.region_timezone || 'IST',
    mon_pref: student.mon_pref || 'No Preference',
    tue_pref: student.tue_pref || 'No Preference',
    wed_pref: student.wed_pref || 'No Preference',
    thu_pref: student.thu_pref || 'No Preference',
    fri_pref: student.fri_pref || 'No Preference',
    sat_pref: student.sat_pref || 'No Preference',
    sun_pref: student.sun_pref || 'No Preference',
    assigned_batch_id: student.assigned_batch_id || '',
    tournament_pref: student.tournament_pref || 'No',
    additional_comments: student.additional_comments || ''
  });

  const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
  const dayKeys = ['mon_pref', 'tue_pref', 'wed_pref', 'thu_pref', 'fri_pref', 'sat_pref', 'sun_pref'];

  // Parse "HH:MM AM-HH:MM PM" range string into { isOff, from, to }
  const parseDayPref = (val) => {
    if (!val || val === 'No Preference' || val === 'Morning' || val === 'Evening') return { isOff: false, from: '06:00 PM', to: '09:00 PM' };
    if (val === 'Not Available') return { isOff: true, from: '06:00 PM', to: '09:00 PM' };
    if (val.includes('-')) {
      const [from, to] = val.split('-');
      return { isOff: false, from: from || '06:00 PM', to: to || '09:00 PM' };
    }
    return { isOff: false, from: val, to: '09:00 PM' };
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!formData.student_name.trim()) {
      alert('Student Name is required');
      return;
    }
    // Sanitize: convert empty-string fields to null so backend Optional[float/str] validation passes
    const sanitized = {
      ...formData,
      mkca_rating: formData.mkca_rating === '' || formData.mkca_rating === undefined ? null : Number(formData.mkca_rating),
      assigned_batch_id: formData.assigned_batch_id || null,
    };
    onSave(sanitized);
  };

  const modalContent = (
    <div
      onClick={onClose}
      style={{
        position: 'fixed',
        top: 0, left: 0, right: 0, bottom: 0,
        width: '100vw', height: '100vh',
        background: 'rgba(0, 0, 0, 0.8)',
        backdropFilter: 'blur(8px)',
        zIndex: 99999,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '20px', boxSizing: 'border-box'
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: '#0d131f',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-lg)',
          width: '100%', maxWidth: '640px', maxHeight: '90vh',
          display: 'flex', flexDirection: 'column',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)'
        }}
      >
        <div style={{ padding: '18px 20px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 800, color: '#fff' }}>
              {student.student_name ? `Edit Student: ${student.student_name}` : 'Add New Master Student'}
            </h3>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Configure student skill level, availability, required classes, and batch assignment
            </p>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} style={{ overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {/* ID, Name & Rating */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '4px' }}>Student ID *</label>
              <input
                type="text"
                value={formData.student_id}
                onChange={e => setFormData({ ...formData, student_id: e.target.value })}
                required
                style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.85rem' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '4px' }}>Student Name *</label>
              <input
                type="text"
                value={formData.student_name}
                onChange={e => setFormData({ ...formData, student_name: e.target.value })}
                placeholder="e.g. Magnus Carlsen"
                required
                style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.85rem' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '4px' }}>MKCA Rating</label>
              <input
                type="number"
                min="0"
                max="3000"
                step="0.1"
                value={formData.mkca_rating}
                onChange={e => setFormData({ ...formData, mkca_rating: e.target.value === '' ? '' : parseFloat(e.target.value) })}
                placeholder="e.g. 133.1"
                style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.85rem' }}
              />
            </div>
          </div>

          {/* Level, Batch Type, Required Classes */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '4px' }}>Level</label>
              <select
                value={formData.student_level}
                onChange={e => setFormData({ ...formData, student_level: e.target.value })}
                style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.85rem' }}
              >
                {STANDARD_LEVELS.map(lvl => (
                  <option key={lvl} value={lvl}>{lvl}</option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '4px' }}>Batch Type</label>
              <select
                value={formData.batch_type}
                onChange={e => setFormData({ ...formData, batch_type: e.target.value })}
                style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.85rem' }}
              >
                <option value="G">Group (G)</option>
                <option value="L">Limited (L)</option>
                <option value="I">Individual (I)</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '4px' }}>Classes / Month</label>
              <input
                type="number"
                min="1"
                max="30"
                value={formData.required_classes}
                onChange={e => setFormData({ ...formData, required_classes: parseInt(e.target.value) || 8 })}
                style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.85rem' }}
              />
            </div>
          </div>

          {/* Region / TZ & Assigned Batch */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '4px' }}>Region / Timezone</label>
              <input
                type="text"
                value={formData.region_timezone}
                onChange={e => setFormData({ ...formData, region_timezone: e.target.value })}
                placeholder="e.g. IST, EST, PST"
                style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.85rem' }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '4px' }}>Assigned Batch (Optional)</label>
              <select
                value={formData.assigned_batch_id}
                onChange={e => setFormData({ ...formData, assigned_batch_id: e.target.value })}
                style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.85rem' }}
              >
                <option value="">None (Unassigned)</option>
                {allBatches.map(b => (
                  <option key={b.batch_id} value={b.batch_id}>{b.batch_name} ({b.batch_type} - {b.level})</option>
                ))}
              </select>
            </div>
          </div>

          {/* Day-Wise Time Window Availability */}
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '8px' }}>
              🕐 Day-Wise Preferred Time Window <span style={{ fontWeight: 400, color: 'var(--text-muted)', fontStyle: 'italic' }}>— 1-hr session will be scheduled within this window</span>
            </label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {days.map((d, dIdx) => {
                const { isOff, from, to } = parseDayPref(formData[dayKeys[dIdx]]);
                const setDay = (newOff, newFrom, newTo) =>
                  setFormData(prev => ({
                    ...prev,
                    [dayKeys[dIdx]]: newOff ? 'Not Available' : `${newFrom}-${newTo}`
                  }));
                return (
                  <div
                    key={d}
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '68px 46px 1fr 18px 1fr',
                      gap: '8px',
                      alignItems: 'center',
                      background: 'var(--bg-secondary)',
                      padding: '8px 12px',
                      borderRadius: '8px',
                      border: isOff ? '1px solid rgba(239,68,68,0.35)' : '1px solid rgba(52,211,153,0.25)'
                    }}
                  >
                    {/* Day label */}
                    <span style={{ fontSize: '0.8rem', fontWeight: 700, color: isOff ? '#f87171' : 'var(--accent-gold)' }}>
                      {d.slice(0, 3)}
                    </span>

                    {/* ON / OFF toggle */}
                    <button
                      type="button"
                      onClick={() => setDay(!isOff, from, to)}
                      style={{
                        padding: '4px 6px',
                        borderRadius: '5px',
                        border: 'none',
                        background: isOff ? 'rgba(239,68,68,0.2)' : 'rgba(52,211,153,0.2)',
                        color: isOff ? '#f87171' : '#34d399',
                        fontSize: '0.65rem',
                        fontWeight: 800,
                        cursor: 'pointer',
                        letterSpacing: '0.05em'
                      }}
                    >
                      {isOff ? 'OFF' : 'ON'}
                    </button>

                    {/* From → To selectors, or Not Available label */}
                    {isOff ? (
                      <span style={{ gridColumn: '3 / -1', fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                        Not available this day
                      </span>
                    ) : (
                      <>
                        <select
                          value={from}
                          onChange={e => setDay(false, e.target.value, to)}
                          style={{ width: '100%', padding: '5px 4px', borderRadius: '5px', background: 'var(--bg-card)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.78rem' }}
                        >
                          {!TIME_SLOTS.includes(from) && <option value={from}>{from}</option>}
                          {TIME_SLOTS.map(t => <option key={t} value={t}>{t}</option>)}
                        </select>
                        <span style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>→</span>
                        <select
                          value={to}
                          onChange={e => setDay(false, from, e.target.value)}
                          style={{ width: '100%', padding: '5px 4px', borderRadius: '5px', background: 'var(--bg-card)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.78rem' }}
                        >
                          {!TIME_SLOTS.includes(to) && <option value={to}>{to}</option>}
                          {TIME_SLOTS.map(t => <option key={t} value={t}>{t}</option>)}
                        </select>
                      </>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Additional Comments */}
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '4px' }}>Notes / Comments</label>
            <input
              type="text"
              value={formData.additional_comments}
              onChange={e => setFormData({ ...formData, additional_comments: e.target.value })}
              placeholder="Any special notes or scheduling requests"
              style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.85rem' }}
            />
          </div>

          {/* Modal Actions */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
            <button type="button" onClick={onClose} className="btn btn-secondary" style={{ padding: '8px 16px', fontSize: '0.85rem' }}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" style={{ padding: '8px 20px', fontSize: '0.85rem', fontWeight: 800 }}>
              <Save size={16} /> Save Student Record
            </button>
          </div>
        </form>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}

// ----------------------------------------------------
// COACH / TRAINER EDIT / ADD MODAL COMPONENT
// ----------------------------------------------------
const COACH_DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

const COACH_PRESETS = [
  { label: '🌇 5–9 PM (Evening)', slots: ['5 pm – 9 pm'], desc: 'Popular evening slot' },
  { label: '🌙 6–9 PM (Peak)', slots: ['6 pm – 9 pm'], desc: 'Standard evening batch' },
  { label: '⏱️ 4–10 PM (Full)', slots: ['4 pm – 10 pm'], desc: 'Full evening window' },
  { label: '🌅 6–10 AM (Morning)', slots: ['6 am – 10 am'], desc: 'Early morning session' },
  { label: '☀️ 8 AM–3 PM (Day)', slots: ['8 am – 3 pm'], desc: 'Daytime batch shift' },
  { label: '🔄 Split (6–8 AM & 6–9 PM)', slots: ['6 am – 8 am', '6 pm – 9 pm'], desc: 'Morning + Evening' },
  { label: '🌐 No Preference', slots: ['No Preference'], desc: 'Open to any time' },
];

const COMMON_SLOT_BUTTONS = [
  '5 pm – 9 pm',
  '6 pm – 9 pm',
  '7 pm – 9 pm',
  '4 pm – 10 pm',
  '6 am – 8 am',
  '6 am – 10 am',
  '8 am – 3 pm',
  '9 am – 2 pm'
];

const SUNDAY_PREF_BUTTONS = ['8am-3pm', 'Available', 'Off', 'Morning Only', 'Evening Only'];

function parseCoachTimingsToDays(str) {
  const res = {};
  COACH_DAYS.forEach(d => {
    res[d] = { isOff: false, slots: [] };
  });

  if (!str || str.trim().toLowerCase() === 'no preference') {
    return res;
  }

  // If simple range without day name (e.g. "5 pm - 9 pm")
  if (!/monday|tuesday|wednesday|thursday|friday|saturday/i.test(str)) {
    COACH_DAYS.forEach(d => {
      res[d].slots = [str.trim()];
    });
    return res;
  }

  const blocks = str.split(/[;\n]/);
  blocks.forEach(b => {
    const trimmed = b.trim();
    if (!trimmed) return;
    const match = trimmed.match(/^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday)\s*:\s*(.*)/i);
    if (match) {
      const dayName = COACH_DAYS.find(d => d.toLowerCase() === match[1].toLowerCase()) || match[1];
      const details = match[2].trim();
      if (/not available/i.test(details) || /max\s*0/i.test(details)) {
        res[dayName] = { isOff: true, slots: [] };
      } else {
        const cleanSlots = details.replace(/\(max\s*\d+\)/gi, '').trim();
        const parts = cleanSlots.split(',').map(s => s.trim()).filter(Boolean);
        res[dayName] = { isOff: false, slots: parts };
      }
    }
  });

  return res;
}

function buildTimingsStringFromDays(dayMap, currentFormData) {
  const parts = [];
  COACH_DAYS.forEach(d => {
    const dayData = dayMap[d];
    const maxKey = `${d.slice(0, 3).toLowerCase()}_max`;
    const maxVal = currentFormData[maxKey] ?? 0;

    if (!dayData || dayData.isOff || maxVal === 0) {
      parts.push(`${d}: Not available (max 0)`);
    } else if (dayData.slots && dayData.slots.length > 0) {
      parts.push(`${d}: ${dayData.slots.join(', ')} (max ${maxVal})`);
    } else {
      parts.push(`${d}: No Preference (max ${maxVal})`);
    }
  });
  return parts.join('; ');
}

function CoachEditModal({ coach, onSave, onClose }) {
  const [formData, setFormData] = useState({
    coach_name: coach.coach_name || '',
    levels_handled: Array.isArray(coach.levels_handled) ? coach.levels_handled : ['Basic 1', 'Beginner 1'],
    monthly_capacity_min: coach.monthly_capacity_min ?? 20,
    monthly_capacity_max: coach.monthly_capacity_max ?? 60,
    mon_max: coach.mon_max ?? 4,
    tue_max: coach.tue_max ?? 4,
    wed_max: coach.wed_max ?? 4,
    thu_max: coach.thu_max ?? 4,
    fri_max: coach.fri_max ?? 4,
    sat_max: coach.sat_max ?? 5,
    sun_max: coach.sun_max ?? 2,
    sunday_pref: coach.sunday_pref || 'Available',
    sunday_max_classes: coach.sunday_max_classes ?? 2,
    preferred_timings: coach.preferred_timings || 'No Preference',
    special_comments: coach.special_comments || ''
  });

  const [activeDayTab, setActiveDayTab] = useState('Monday');
  const [dayMap, setDayMap] = useState(() => parseCoachTimingsToDays(coach.preferred_timings));
  const [showRawText, setShowRawText] = useState(false);
  const [customFrom, setCustomFrom] = useState('05:00 PM');
  const [customTo, setCustomTo] = useState('09:00 PM');

  const updateTimingsAndForm = (newDayMap, updatedFormBase = formData) => {
    setDayMap(newDayMap);
    const newStr = buildTimingsStringFromDays(newDayMap, updatedFormBase);
    setFormData({ ...updatedFormBase, preferred_timings: newStr });
  };

  const toggleSlotOnActiveDay = (slot) => {
    const current = dayMap[activeDayTab] || { isOff: false, slots: [] };
    let newSlots;
    if (current.slots.includes(slot)) {
      newSlots = current.slots.filter(s => s !== slot);
    } else {
      newSlots = [...current.slots.filter(s => s !== 'No Preference'), slot];
    }
    const newDayMap = {
      ...dayMap,
      [activeDayTab]: { isOff: false, slots: newSlots }
    };
    updateTimingsAndForm(newDayMap);
  };

  const toggleActiveDayAvailability = () => {
    const current = dayMap[activeDayTab] || { isOff: false, slots: [] };
    const newOff = !current.isOff;
    const newDayMap = {
      ...dayMap,
      [activeDayTab]: { ...current, isOff: newOff }
    };
    updateTimingsAndForm(newDayMap);
  };

  const applyPresetToWeekdays = (presetSlots) => {
    const newDayMap = { ...dayMap };
    ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'].forEach(d => {
      newDayMap[d] = { isOff: false, slots: [...presetSlots] };
    });
    updateTimingsAndForm(newDayMap);
  };

  const applyPresetToAllDays = (presetSlots) => {
    const newDayMap = { ...dayMap };
    COACH_DAYS.forEach(d => {
      newDayMap[d] = { isOff: false, slots: [...presetSlots] };
    });
    updateTimingsAndForm(newDayMap);
  };

  const copyActiveDayToWeekdays = () => {
    const current = dayMap[activeDayTab] || { isOff: false, slots: [] };
    const newDayMap = { ...dayMap };
    ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'].forEach(d => {
      newDayMap[d] = { isOff: current.isOff, slots: [...current.slots] };
    });
    updateTimingsAndForm(newDayMap);
  };

  const addCustomSlotToActiveDay = () => {
    const slotStr = `${customFrom} – ${customTo}`;
    toggleSlotOnActiveDay(slotStr);
  };

  const toggleLevel = (lvl) => {
    const current = formData.levels_handled || [];
    if (current.includes(lvl)) {
      setFormData({ ...formData, levels_handled: current.filter(l => l !== lvl) });
    } else {
      setFormData({ ...formData, levels_handled: [...current, lvl] });
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!formData.coach_name.trim()) {
      alert('Trainer Name is required');
      return;
    }
    onSave(formData);
  };

  const activeDayData = dayMap[activeDayTab] || { isOff: false, slots: [] };

  const modalContent = (
    <div
      onClick={onClose}
      style={{
        position: 'fixed',
        top: 0, left: 0, right: 0, bottom: 0,
        width: '100vw', height: '100vh',
        background: 'rgba(0, 0, 0, 0.82)',
        backdropFilter: 'blur(8px)',
        zIndex: 99999,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '20px', boxSizing: 'border-box'
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: '#0d131f',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-lg)',
          width: '100%', maxWidth: '720px', maxHeight: '92vh',
          display: 'flex', flexDirection: 'column',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.6)'
        }}
      >
        <div style={{ padding: '18px 20px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 800, color: '#fff' }}>
              {coach.coach_name ? `Edit Trainer: ${coach.coach_name}` : 'Add New Master Trainer'}
            </h3>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Configure trainer capabilities, daily class limits, and interactive timing slots
            </p>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} style={{ overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Trainer Name */}
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '4px' }}>Trainer Name *</label>
            <input
              type="text"
              value={formData.coach_name}
              onChange={e => setFormData({ ...formData, coach_name: e.target.value })}
              placeholder="e.g. Coach Dhaanush"
              required
              style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.85rem' }}
            />
          </div>

          {/* Handled Levels Tag Selector */}
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '6px' }}>
              Levels Handled (Click to toggle)
            </label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {STANDARD_LEVELS.map(lvl => {
                const isSelected = (formData.levels_handled || []).includes(lvl);
                return (
                  <button
                    key={lvl}
                    type="button"
                    onClick={() => toggleLevel(lvl)}
                    style={{
                      padding: '4px 10px',
                      borderRadius: '6px',
                      border: isSelected ? '1px solid #c084fc' : '1px solid var(--border-color)',
                      background: isSelected ? 'rgba(192, 132, 252, 0.2)' : 'rgba(255,255,255,0.04)',
                      color: isSelected ? '#c084fc' : '#94a3b8',
                      fontSize: '0.75rem',
                      fontWeight: isSelected ? 700 : 500,
                      cursor: 'pointer'
                    }}
                  >
                    {isSelected ? '✓ ' : ''}{lvl}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Monthly Capacity Target */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '4px' }}>Target Min Monthly Classes</label>
              <input
                type="number"
                min="0"
                max="200"
                value={formData.monthly_capacity_min}
                onChange={e => setFormData({ ...formData, monthly_capacity_min: parseInt(e.target.value) || 0 })}
                style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.85rem' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '4px' }}>Maximum Permitted Capacity</label>
              <input
                type="number"
                min="1"
                max="250"
                value={formData.monthly_capacity_max}
                onChange={e => setFormData({ ...formData, monthly_capacity_max: parseInt(e.target.value) || 100 })}
                style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.85rem' }}
              />
            </div>
          </div>

          {/* Daily Limits: Mon to Sun */}
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '6px' }}>
              Daily Maximum Class Limits (Mon - Sun)
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '6px' }}>
              {[
                { label: 'Mon', key: 'mon_max' },
                { label: 'Tue', key: 'tue_max' },
                { label: 'Wed', key: 'wed_max' },
                { label: 'Thu', key: 'thu_max' },
                { label: 'Fri', key: 'fri_max' },
                { label: 'Sat', key: 'sat_max' },
                { label: 'Sun', key: 'sun_max' }
              ].map(d => (
                <div key={d.key} style={{ textAlign: 'center' }}>
                  <span style={{ display: 'block', fontSize: '0.7rem', fontWeight: 700, color: d.key === 'sun_max' ? '#f87171' : (d.key === 'sat_max' ? '#38bdf8' : 'var(--accent-gold)'), marginBottom: '2px' }}>
                    {d.label}
                  </span>
                  <input
                    type="number"
                    min="0"
                    max="10"
                    value={formData[d.key] ?? 0}
                    onChange={e => {
                      const val = parseInt(e.target.value) || 0;
                      const update = { [d.key]: val };
                      if (d.key === 'sun_max') update.sunday_max_classes = val;
                      const updatedForm = { ...formData, ...update };
                      updateTimingsAndForm(dayMap, updatedForm);
                    }}
                    style={{ width: '100%', padding: '6px 2px', textAlign: 'center', borderRadius: '6px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.85rem' }}
                  />
                </div>
              ))}
            </div>
          </div>

          {/* ---------------------------------------------------- */}
          {/* INTERACTIVE BUTTON-BASED PREFERRED TIMING SELECTOR   */}
          {/* ---------------------------------------------------- */}
          <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(234, 179, 8, 0.25)', borderRadius: '10px', padding: '14px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <div>
                <span style={{ fontSize: '0.85rem', fontWeight: 800, color: 'var(--accent-gold)' }}>
                  🕐 Preferred Timing Windows (Button Selection)
                </span>
                <p style={{ margin: '2px 0 0 0', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                  Click presets or pick day-by-day availability buttons with one tap
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowRawText(!showRawText)}
                style={{
                  padding: '4px 8px',
                  borderRadius: '5px',
                  background: showRawText ? 'rgba(234, 179, 8, 0.2)' : 'rgba(255,255,255,0.05)',
                  border: '1px solid var(--border-color)',
                  color: showRawText ? 'var(--accent-gold)' : 'var(--text-secondary)',
                  fontSize: '0.7rem',
                  cursor: 'pointer',
                  fontWeight: 600
                }}
              >
                {showRawText ? 'Hide Raw Text' : '✏️ Edit Raw Text'}
              </button>
            </div>

            {/* QUICK PRESETS (ONE-CLICK) */}
            <div style={{ marginBottom: '14px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>
                  ⚡ 1-Click Quick Presets:
                </span>
                <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                  Click preset to apply
                </span>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {COACH_PRESETS.map(p => (
                  <div key={p.label} style={{ display: 'inline-flex', borderRadius: '6px', overflow: 'hidden', border: '1px solid var(--border-color)' }}>
                    <button
                      type="button"
                      onClick={() => applyPresetToWeekdays(p.slots)}
                      title={`Apply ${p.label} to Mon-Fri`}
                      style={{
                        padding: '5px 9px',
                        background: 'rgba(255,255,255,0.05)',
                        border: 'none',
                        color: '#e2e8f0',
                        fontSize: '0.72rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                        transition: 'background 0.15s'
                      }}
                      onMouseEnter={e => e.currentTarget.style.background = 'rgba(234, 179, 8, 0.2)'}
                      onMouseLeave={e => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
                    >
                      {p.label}
                    </button>
                    <button
                      type="button"
                      onClick={() => applyPresetToAllDays(p.slots)}
                      title="Apply to Mon-Sat"
                      style={{
                        padding: '5px 6px',
                        background: 'rgba(59, 130, 246, 0.15)',
                        border: 'none',
                        borderLeft: '1px solid var(--border-color)',
                        color: '#60a5fa',
                        fontSize: '0.65rem',
                        fontWeight: 700,
                        cursor: 'pointer'
                      }}
                    >
                      All
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* DAY TABS (Mon - Sat) */}
            <div style={{ marginBottom: '10px' }}>
              <div style={{ display: 'flex', gap: '5px', overflowX: 'auto', paddingBottom: '4px' }}>
                {COACH_DAYS.map(day => {
                  const dData = dayMap[day] || { isOff: false, slots: [] };
                  const isSelected = activeDayTab === day;
                  const isOff = dData.isOff;
                  const count = (dData.slots || []).length;
                  return (
                    <button
                      key={day}
                      type="button"
                      onClick={() => setActiveDayTab(day)}
                      style={{
                        flex: '1',
                        minWidth: '55px',
                        padding: '6px 4px',
                        borderRadius: '6px',
                        border: isSelected ? '1px solid var(--accent-gold)' : (isOff ? '1px solid rgba(239,68,68,0.3)' : '1px solid var(--border-color)'),
                        background: isSelected ? 'rgba(234, 179, 8, 0.18)' : (isOff ? 'rgba(239,68,68,0.1)' : 'rgba(255,255,255,0.03)'),
                        color: isSelected ? 'var(--accent-gold)' : (isOff ? '#f87171' : '#cbd5e1'),
                        fontSize: '0.75rem',
                        fontWeight: isSelected ? 800 : 600,
                        cursor: 'pointer',
                        textAlign: 'center'
                      }}
                    >
                      <div>{day.slice(0, 3)}</div>
                      <div style={{ fontSize: '0.62rem', marginTop: '2px', opacity: 0.85 }}>
                        {isOff ? 'Off' : (count > 0 ? `${count} slot` : 'Open')}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* ACTIVE DAY TIMING PANEL */}
            <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '0.85rem', fontWeight: 800, color: '#fff' }}>
                    {activeDayTab} Availability:
                  </span>
                  <button
                    type="button"
                    onClick={toggleActiveDayAvailability}
                    style={{
                      padding: '3px 8px',
                      borderRadius: '5px',
                      border: 'none',
                      background: activeDayData.isOff ? 'rgba(239, 68, 68, 0.2)' : 'rgba(52, 211, 153, 0.2)',
                      color: activeDayData.isOff ? '#f87171' : '#34d399',
                      fontSize: '0.7rem',
                      fontWeight: 800,
                      cursor: 'pointer'
                    }}
                  >
                    {activeDayData.isOff ? '❌ Mark as Off / Unavailable' : '✅ Active & Available'}
                  </button>
                </div>

                {!activeDayData.isOff && (
                  <button
                    type="button"
                    onClick={copyActiveDayToWeekdays}
                    style={{
                      padding: '3px 8px',
                      borderRadius: '5px',
                      background: 'rgba(168, 85, 247, 0.15)',
                      border: '1px solid rgba(168, 85, 247, 0.3)',
                      color: '#c084fc',
                      fontSize: '0.68rem',
                      fontWeight: 700,
                      cursor: 'pointer'
                    }}
                  >
                    📋 Copy to Mon-Fri
                  </button>
                )}
              </div>

              {!activeDayData.isOff ? (
                <div>
                  <span style={{ display: 'block', fontSize: '0.7rem', color: 'var(--text-secondary)', marginBottom: '6px', fontWeight: 700 }}>
                    Click time slots to toggle for {activeDayTab}:
                  </span>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '10px' }}>
                    {COMMON_SLOT_BUTTONS.map(slot => {
                      const isActive = activeDayData.slots && activeDayData.slots.includes(slot);
                      return (
                        <button
                          key={slot}
                          type="button"
                          onClick={() => toggleSlotOnActiveDay(slot)}
                          style={{
                            padding: '5px 10px',
                            borderRadius: '6px',
                            border: isActive ? '1px solid #38bdf8' : '1px solid var(--border-color)',
                            background: isActive ? 'rgba(56, 189, 248, 0.22)' : 'rgba(255,255,255,0.03)',
                            color: isActive ? '#38bdf8' : '#94a3b8',
                            fontSize: '0.75rem',
                            fontWeight: isActive ? 700 : 500,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px'
                          }}
                        >
                          {isActive ? '✓ ' : '+ '}{slot}
                        </button>
                      );
                    })}
                  </div>

                  {/* CUSTOM TIME ADDER */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(255,255,255,0.02)', padding: '6px 8px', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>Custom:</span>
                    <select
                      value={customFrom}
                      onChange={e => setCustomFrom(e.target.value)}
                      style={{ padding: '4px 6px', borderRadius: '4px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.72rem' }}
                    >
                      {TIME_SLOTS.map(t => <option key={t} value={t}>{t}</option>)}
                    </select>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>→</span>
                    <select
                      value={customTo}
                      onChange={e => setCustomTo(e.target.value)}
                      style={{ padding: '4px 6px', borderRadius: '4px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.72rem' }}
                    >
                      {TIME_SLOTS.map(t => <option key={t} value={t}>{t}</option>)}
                    </select>
                    <button
                      type="button"
                      onClick={addCustomSlotToActiveDay}
                      style={{
                        padding: '4px 10px',
                        borderRadius: '4px',
                        background: 'rgba(52, 211, 153, 0.18)',
                        border: '1px solid rgba(52, 211, 153, 0.35)',
                        color: '#34d399',
                        fontSize: '0.72rem',
                        fontWeight: 700,
                        cursor: 'pointer'
                      }}
                    >
                      + Add Custom Slot
                    </button>
                  </div>

                  {/* ACTIVE SELECTED SLOTS CHIPS */}
                  {activeDayData.slots && activeDayData.slots.length > 0 && (
                    <div style={{ marginTop: '8px', display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '5px' }}>
                      <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Selected for {activeDayTab}:</span>
                      {activeDayData.slots.map(s => (
                        <span
                          key={s}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            padding: '2px 7px',
                            borderRadius: '4px',
                            background: 'rgba(234, 179, 8, 0.15)',
                            border: '1px solid rgba(234, 179, 8, 0.3)',
                            color: 'var(--accent-gold)',
                            fontSize: '0.7rem',
                            fontWeight: 700
                          }}
                        >
                          {s}
                          <span
                            onClick={() => toggleSlotOnActiveDay(s)}
                            style={{ cursor: 'pointer', marginLeft: '2px', color: '#f87171', fontWeight: 800 }}
                            title="Remove slot"
                          >
                            ×
                          </span>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div style={{ padding: '12px 0', textAlign: 'center', color: '#f87171', fontSize: '0.8rem', fontStyle: 'italic' }}>
                  {activeDayTab} is marked as Off (Not available). The scheduler will not schedule classes for this trainer on {activeDayTab}.
                </div>
              )}
            </div>

            {/* SUNDAY PREFERENCE BUTTONS */}
            <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>
                  ☀️ Sunday Preference (Click button to set):
                </span>
                <span style={{ fontSize: '0.75rem', fontWeight: 800, color: '#f59e0b' }}>
                  Current: {formData.sunday_pref}
                </span>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {SUNDAY_PREF_BUTTONS.map(btn => {
                  const isSel = formData.sunday_pref === btn;
                  return (
                    <button
                      key={btn}
                      type="button"
                      onClick={() => setFormData({ ...formData, sunday_pref: btn })}
                      style={{
                        padding: '4px 10px',
                        borderRadius: '6px',
                        border: isSel ? '1px solid #f59e0b' : '1px solid var(--border-color)',
                        background: isSel ? 'rgba(245, 158, 11, 0.22)' : 'rgba(255,255,255,0.03)',
                        color: isSel ? '#fbbf24' : '#94a3b8',
                        fontSize: '0.72rem',
                        fontWeight: isSel ? 700 : 500,
                        cursor: 'pointer'
                      }}
                    >
                      {isSel ? '✓ ' : ''}{btn}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* LIVE PREVIEW / RAW TEXT */}
            <div style={{ marginTop: '12px', background: 'rgba(0,0,0,0.3)', padding: '8px 10px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.06)' }}>
              <div style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px' }}>
                Generated Schedule Engine Timing String:
              </div>
              {showRawText ? (
                <textarea
                  rows={3}
                  value={formData.preferred_timings}
                  onChange={e => {
                    setFormData({ ...formData, preferred_timings: e.target.value });
                    setDayMap(parseCoachTimingsToDays(e.target.value));
                  }}
                  style={{ width: '100%', padding: '6px', borderRadius: '4px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.75rem', fontFamily: 'monospace' }}
                />
              ) : (
                <div style={{ fontSize: '0.72rem', color: '#cbd5e1', fontFamily: 'monospace', wordBreak: 'break-word', lineHeight: 1.4 }}>
                  {formData.preferred_timings || 'No Preference'}
                </div>
              )}
            </div>
          </div>

          {/* Special Comments / Tournament Exceptions */}
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '4px' }}>Special Comments / Tournament Exceptions</label>
            <input
              type="text"
              value={formData.special_comments || ''}
              onChange={e => setFormData({ ...formData, special_comments: e.target.value, temporary_exceptions: e.target.value })}
              placeholder="e.g. Will go to tournament on 4,5,6th july..."
              style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.85rem' }}
            />
          </div>

          {/* Modal Actions */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
            <button type="button" onClick={onClose} className="btn btn-secondary" style={{ padding: '8px 16px', fontSize: '0.85rem' }}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" style={{ padding: '8px 20px', fontSize: '0.85rem', fontWeight: 800 }}>
              <Save size={16} /> Save Trainer Record
            </button>
          </div>
        </form>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}
