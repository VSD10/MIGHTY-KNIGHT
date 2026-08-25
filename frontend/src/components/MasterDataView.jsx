import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Users, Award, Search, Plus, Edit2, Trash2, Save, X, RefreshCw, Check, AlertCircle } from 'lucide-react';
import { getMasterData, saveMasterStudent, deleteMasterStudent, saveMasterCoach, deleteMasterCoach } from '../services/api';

export default function MasterDataView({ onReRunScheduler }) {
  const [activeSubTab, setActiveSubTab] = useState('students');
  const [students, setStudents] = useState([]);
  const [coaches, setCoaches] = useState([]);
  const [filename, setFilename] = useState('');
  const [uploadTimestamp, setUploadTimestamp] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');

  // Editing state
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
        setFilename(data.filename || '');
        setUploadTimestamp(data.upload_timestamp || '');
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

  // Student CRUD
  const handleSaveStudent = async (studentData) => {
    try {
      await saveMasterStudent(studentData);
      showNotification(`Saved student ${studentData.student_name} (${studentData.student_id}) & updated active schedule!`);
      setEditingStudent(null);
      await fetchMasterData();
      if (onReRunScheduler) await onReRunScheduler();
    } catch (err) {
      alert('Failed to save student: ' + err.message);
    }
  };

  const handleDeleteStudent = async (studentId, studentName) => {
    if (!window.confirm(`Are you sure you want to delete student "${studentName}" (${studentId})?`)) return;
    try {
      await deleteMasterStudent(studentId);
      showNotification(`Deleted student ${studentName} & updated active schedule!`);
      await fetchMasterData();
      if (onReRunScheduler) await onReRunScheduler();
    } catch (err) {
      alert('Failed to delete student: ' + err.message);
    }
  };

  // Coach CRUD
  const handleSaveCoach = async (coachData) => {
    try {
      await saveMasterCoach(coachData);
      showNotification(`Saved coach ${coachData.coach_name} & updated active schedule!`);
      setEditingCoach(null);
      await fetchMasterData();
      if (onReRunScheduler) await onReRunScheduler();
    } catch (err) {
      alert('Failed to save coach: ' + err.message);
    }
  };

  const handleDeleteCoach = async (coachName) => {
    if (!window.confirm(`Are you sure you want to delete coach "${coachName}"?`)) return;
    try {
      await deleteMasterCoach(coachName);
      showNotification(`Deleted coach ${coachName} & updated active schedule!`);
      await fetchMasterData();
      if (onReRunScheduler) await onReRunScheduler();
    } catch (err) {
      alert('Failed to delete coach: ' + err.message);
    }
  };

  const filteredStudents = students.filter(s =>
    (s.student_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (s.student_id || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (s.student_level || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredCoaches = coaches.filter(c =>
    (c.coach_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (Array.isArray(c.levels_handled) ? c.levels_handled.join(', ') : '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="glass-panel" style={{ padding: '24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '10px' }}>
            👥 Master Data Management Hub (Excel & Dynamic Store)
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Live table of all parsed Excel records stored in SQLite. Edit, add, or delete students & coaches with 0 data loss.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <button
            onClick={() => onReRunScheduler && onReRunScheduler()}
            className="btn btn-primary"
            style={{ padding: '10px 16px', background: 'var(--accent-gold)', borderColor: 'var(--accent-gold)', color: '#000', fontWeight: 800, fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <RefreshCw size={16} /> Re-Run Engine on Updated Data
          </button>
        </div>
      </div>

      {/* Success Notification Banner */}
      {successMsg && (
        <div style={{ padding: '12px 16px', background: 'rgba(16, 185, 129, 0.2)', border: '1px solid #10b981', color: '#10b981', borderRadius: 'var(--radius-md)', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem' }}>
          <Check size={18} /> {successMsg}
        </div>
      )}

      {/* Navigation Sub-Tabs & Search */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '20px', borderBottom: '1px solid var(--border-color)', paddingBottom: '16px' }}>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            onClick={() => { setActiveSubTab('students'); setSearchQuery(''); }}
            style={{
              padding: '10px 20px',
              borderRadius: 'var(--radius-md)',
              border: activeSubTab === 'students' ? '1px solid var(--accent-gold)' : '1px solid var(--border-color)',
              background: activeSubTab === 'students' ? 'rgba(234, 179, 8, 0.15)' : 'var(--bg-secondary)',
              color: activeSubTab === 'students' ? 'var(--accent-gold)' : 'var(--text-secondary)',
              fontWeight: 700,
              fontSize: '0.9rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}
          >
            <Users size={18} /> Master Students ({students.length})
          </button>

          <button
            onClick={() => { setActiveSubTab('coaches'); setSearchQuery(''); }}
            style={{
              padding: '10px 20px',
              borderRadius: 'var(--radius-md)',
              border: activeSubTab === 'coaches' ? '1px solid var(--accent-blue)' : '1px solid var(--border-color)',
              background: activeSubTab === 'coaches' ? 'rgba(59, 130, 246, 0.15)' : 'var(--bg-secondary)',
              color: activeSubTab === 'coaches' ? 'var(--accent-blue)' : 'var(--text-secondary)',
              fontWeight: 700,
              fontSize: '0.9rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}
          >
            <Award size={18} /> Master Coaches ({coaches.length})
          </button>
        </div>

        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <div style={{ position: 'relative', minWidth: '260px' }}>
            <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder={`Search ${activeSubTab}...`}
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

          {activeSubTab === 'students' ? (
            <button
              onClick={() => setEditingStudent({ student_id: `STU_${Date.now().toString().slice(-4)}`, student_name: '', student_level: 'Basic 1', batch_type: 'G', preferred_days: 'All', preferred_time: '05:00 PM', region_timezone: 'IST', required_classes: 8 })}
              className="btn btn-secondary"
              style={{ padding: '8px 14px', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <Plus size={16} /> Add Student
            </button>
          ) : (
            <button
              onClick={() => setEditingCoach({ coach_name: '', levels_handled: ['Basic 1', 'Basic 2'], monthly_capacity_min: 0, monthly_capacity_max: 100, mon_max: 4, tue_max: 4, wed_max: 4, thu_max: 4, fri_max: 4, sat_max: 5, sun_max: 2 })}
              className="btn btn-secondary"
              style={{ padding: '8px 14px', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <Plus size={16} /> Add Coach
            </button>
          )}
        </div>
      </div>

      {/* MASTER STUDENTS DYNAMIC TABLE */}
      {activeSubTab === 'students' && (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                <th style={{ padding: '12px' }}>Student ID</th>
                <th style={{ padding: '12px' }}>Student Name</th>
                <th style={{ padding: '12px' }}>Level</th>
                <th style={{ padding: '12px' }}>Batch</th>
                <th style={{ padding: '12px' }}>Preferred Days</th>
                <th style={{ padding: '12px' }}>Preferred Time</th>
                <th style={{ padding: '12px' }}>Region/TZ</th>
                <th style={{ padding: '12px' }}>Req Classes</th>
                <th style={{ padding: '12px', textAlign: 'center' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredStudents.map((s) => (
                <tr key={s.student_id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                  <td style={{ padding: '12px', fontWeight: 700, color: 'var(--accent-gold)' }}>{s.student_id}</td>
                  <td style={{ padding: '12px', fontWeight: 600, color: '#fff' }}>{s.student_name}</td>
                  <td style={{ padding: '12px' }}>
                    <span style={{ padding: '2px 8px', borderRadius: '12px', background: 'rgba(255,255,255,0.08)', fontSize: '0.75rem' }}>{s.student_level}</span>
                  </td>
                  <td style={{ padding: '12px' }}>
                    <span style={{ padding: '2px 8px', borderRadius: '4px', background: s.batch_type === 'G' ? 'rgba(59,130,246,0.2)' : 'rgba(234,179,8,0.2)', color: s.batch_type === 'G' ? '#60a5fa' : '#facc15', fontWeight: 700, fontSize: '0.75rem' }}>{s.batch_type}</span>
                  </td>
                  <td style={{ padding: '12px', color: 'var(--text-secondary)' }}>{s.preferred_days || 'All'}</td>
                  <td style={{ padding: '12px', color: 'var(--text-secondary)' }}>{s.preferred_time || '05:00 PM'}</td>
                  <td style={{ padding: '12px', color: 'var(--text-muted)' }}>{s.region_timezone || 'IST'}</td>
                  <td style={{ padding: '12px', fontWeight: 700 }}>{s.required_classes || 8}</td>
                  <td style={{ padding: '12px', textAlign: 'center' }}>
                    <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
                      <button
                        onClick={() => setEditingStudent(s)}
                        style={{ background: 'none', border: 'none', color: '#60a5fa', cursor: 'pointer' }}
                        title="Edit Student"
                      >
                        <Edit2 size={16} />
                      </button>
                      <button
                        onClick={() => handleDeleteStudent(s.student_id, s.student_name)}
                        style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer' }}
                        title="Delete Student"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* MASTER COACHES DYNAMIC TABLE */}
      {activeSubTab === 'coaches' && (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                <th style={{ padding: '12px' }}>Coach Name</th>
                <th style={{ padding: '12px' }}>Levels Handled</th>
                <th style={{ padding: '12px' }}>Monthly Min</th>
                <th style={{ padding: '12px' }}>Monthly Max</th>
                <th style={{ padding: '12px' }}>Mon-Sun Daily Caps</th>
                <th style={{ padding: '12px', textAlign: 'center' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredCoaches.map((c) => (
                <tr key={c.coach_name} style={{ borderBottom: '1px solid var(--border-color)' }}>
                  <td style={{ padding: '12px', fontWeight: 800, color: '#fff' }}>{c.coach_name}</td>
                  <td style={{ padding: '12px' }}>
                    <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                      {(Array.isArray(c.levels_handled) ? c.levels_handled : []).map((lvl, idx) => (
                        <span key={idx} style={{ padding: '2px 6px', borderRadius: '4px', background: 'rgba(234, 179, 8, 0.15)', color: 'var(--accent-gold)', fontSize: '0.725rem' }}>
                          {lvl}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td style={{ padding: '12px', color: 'var(--text-secondary)' }}>{c.monthly_capacity_min || 0}</td>
                  <td style={{ padding: '12px', fontWeight: 700, color: 'var(--accent-gold)' }}>{c.monthly_capacity_max || 100}</td>
                  <td style={{ padding: '12px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    M:{c.mon_max ?? 4} | T:{c.tue_max ?? 4} | W:{c.wed_max ?? 4} | Th:{c.thu_max ?? 4} | F:{c.fri_max ?? 4} | Sa:{c.sat_max ?? 5} | Su:{c.sun_max ?? 2}
                  </td>
                  <td style={{ padding: '12px', textAlign: 'center' }}>
                    <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
                      <button
                        onClick={() => setEditingCoach(c)}
                        style={{ background: 'none', border: 'none', color: '#60a5fa', cursor: 'pointer' }}
                        title="Edit Coach"
                      >
                        <Edit2 size={16} />
                      </button>
                      <button
                        onClick={() => handleDeleteCoach(c.coach_name)}
                        style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer' }}
                        title="Delete Coach"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* STUDENT EDIT / ADD MODAL */}
      {editingStudent && (
        <StudentEditModal
          student={editingStudent}
          onSave={handleSaveStudent}
          onClose={() => setEditingStudent(null)}
        />
      )}

      {/* COACH EDIT / ADD MODAL */}
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

function StudentEditModal({ student, onSave, onClose }) {
  const [formData, setFormData] = useState({ ...student });

  useEffect(() => {
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = originalOverflow;
    };
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!formData.student_id || !formData.student_name) {
      alert('Student ID and Name are required');
      return;
    }
    onSave(formData);
  };

  const modalContent = (
    <div
      onClick={onClose}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        width: '100vw',
        height: '100vh',
        background: 'rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(8px)',
        WebkitBackdropFilter: 'blur(8px)',
        zIndex: 99999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
        boxSizing: 'border-box'
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="glass-panel"
        style={{
          width: '100%',
          maxWidth: '520px',
          maxHeight: '90vh',
          overflowY: 'auto',
          background: 'var(--bg-secondary)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--accent-gold)',
          padding: '24px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.8), 0 0 30px rgba(251, 191, 36, 0.25)',
          margin: 'auto'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 style={{ fontSize: '1.2rem', fontWeight: 800, color: '#fff' }}>
            {student.student_id ? 'Edit Master Student' : 'Add New Master Student'}
          </h3>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div>
            <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>Student ID</label>
            <input
              type="text"
              value={formData.student_id}
              onChange={e => setFormData({ ...formData, student_id: e.target.value })}
              style={{ width: '100%', padding: '8px 12px', background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', color: '#fff' }}
              required
            />
          </div>

          <div>
            <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>Student Name</label>
            <input
              type="text"
              value={formData.student_name}
              onChange={e => setFormData({ ...formData, student_name: e.target.value })}
              style={{ width: '100%', padding: '8px 12px', background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', color: '#fff' }}
              required
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>Level</label>
              <select
                value={formData.student_level}
                onChange={e => setFormData({ ...formData, student_level: e.target.value })}
                style={{ width: '100%', padding: '8px 12px', background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', color: '#fff' }}
              >
                <option value="Basic 1">Basic 1</option>
                <option value="Basic 2">Basic 2</option>
                <option value="Beginner 1">Beginner 1</option>
                <option value="Beginner 2">Beginner 2</option>
                <option value="Beginner 3">Beginner 3</option>
                <option value="Early Intermediate 1">Early Intermediate 1</option>
                <option value="Early Intermediate 2">Early Intermediate 2</option>
                <option value="Intermediate 1">Intermediate 1</option>
                <option value="Intermediate">Intermediate</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>Batch Type</label>
              <select
                value={formData.batch_type}
                onChange={e => setFormData({ ...formData, batch_type: e.target.value })}
                style={{ width: '100%', padding: '8px 12px', background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', color: '#fff' }}
              >
                <option value="G">G (Group - max 10)</option>
                <option value="L">L (Limited - max 3)</option>
                <option value="I">I (Individual 1-on-1)</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>Preferred Days</label>
              <input
                type="text"
                value={formData.preferred_days || ''}
                onChange={e => setFormData({ ...formData, preferred_days: e.target.value })}
                placeholder="e.g. Monday, Wednesday"
                style={{ width: '100%', padding: '8px 12px', background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', color: '#fff' }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>Preferred Time</label>
              <input
                type="text"
                value={formData.preferred_time || ''}
                onChange={e => setFormData({ ...formData, preferred_time: e.target.value })}
                placeholder="e.g. 05:00 PM"
                style={{ width: '100%', padding: '8px 12px', background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', color: '#fff' }}
              />
            </div>
          </div>

          <button type="submit" className="btn btn-primary" style={{ marginTop: '12px', padding: '10px' }}>
            <Save size={16} /> Save Student Record
          </button>
        </form>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}

function CoachEditModal({ coach, onSave, onClose }) {
  const [formData, setFormData] = useState({ ...coach });
  const [levelsStr, setLevelsStr] = useState(Array.isArray(coach.levels_handled) ? coach.levels_handled.join(', ') : '');

  useEffect(() => {
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = originalOverflow;
    };
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!formData.coach_name) {
      alert('Coach Name is required');
      return;
    }
    const lvls = levelsStr.split(',').map(s => s.trim()).filter(Boolean);
    onSave({ ...formData, levels_handled: lvls });
  };

  const modalContent = (
    <div
      onClick={onClose}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        width: '100vw',
        height: '100vh',
        background: 'rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(8px)',
        WebkitBackdropFilter: 'blur(8px)',
        zIndex: 99999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
        boxSizing: 'border-box'
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="glass-panel"
        style={{
          width: '100%',
          maxWidth: '540px',
          maxHeight: '90vh',
          overflowY: 'auto',
          background: 'var(--bg-secondary)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--accent-blue)',
          padding: '24px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.8), 0 0 30px rgba(96, 165, 250, 0.25)',
          margin: 'auto'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 style={{ fontSize: '1.2rem', fontWeight: 800, color: '#fff' }}>
            {coach.coach_name ? 'Edit Master Coach' : 'Add New Master Coach'}
          </h3>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div>
            <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>Coach Name</label>
            <input
              type="text"
              value={formData.coach_name}
              onChange={e => setFormData({ ...formData, coach_name: e.target.value })}
              style={{ width: '100%', padding: '8px 12px', background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', color: '#fff' }}
              required
            />
          </div>

          <div>
            <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>Levels Handled (comma-separated)</label>
            <input
              type="text"
              value={levelsStr}
              onChange={e => setLevelsStr(e.target.value)}
              placeholder="e.g. Basic 1, Basic 2, Intermediate 1"
              style={{ width: '100%', padding: '8px 12px', background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', color: '#fff' }}
              required
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>Monthly Min Capacity</label>
              <input
                type="number"
                value={formData.monthly_capacity_min ?? 0}
                onChange={e => setFormData({ ...formData, monthly_capacity_min: parseInt(e.target.value, 10) })}
                style={{ width: '100%', padding: '8px 12px', background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', color: '#fff' }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>Monthly Max Capacity</label>
              <input
                type="number"
                value={formData.monthly_capacity_max ?? 100}
                onChange={e => setFormData({ ...formData, monthly_capacity_max: parseInt(e.target.value, 10) })}
                style={{ width: '100%', padding: '8px 12px', background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', color: '#fff' }}
              />
            </div>
          </div>

          <button type="submit" className="btn btn-primary" style={{ marginTop: '12px', padding: '10px' }}>
            <Save size={16} /> Save Coach Record
          </button>
        </form>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}
