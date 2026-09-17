import React, { useState, useMemo } from 'react';
import {
  Calendar as CalendarIcon,
  Clock,
  User,
  Users,
  Plus,
  Trash2,
  Edit3,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  CheckCircle,
  Sparkles,
  ShieldAlert,
  UserPlus,
  X,
  Layers,
  Search,
  Filter
} from 'lucide-react';
import { deleteClass, applyManualEdit, createScheduleClass, assignStudentToClass } from '../services/api';

const TIME_SLOT_PRESETS = [
  '06:00 AM - 07:00 AM',
  '07:00 AM - 08:00 AM',
  '08:00 AM - 03:00 PM',
  '04:00 PM - 05:00 PM',
  '05:00 PM - 06:00 PM',
  '06:00 PM - 07:00 PM',
  '07:00 PM - 08:00 PM',
  '08:00 PM - 09:00 PM',
  '09:00 PM - 10:00 PM'
];

const LEVEL_OPTIONS = [
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

export default function DailySchedulePlanner({
  detailedClasses = [],
  scheduleId,
  startDate,
  endDate,
  onRefreshSchedule,
  onOpenManualEdit,
  coaches = [],
  masterStudents = [],
  unscheduledStudents = []
}) {
  // Determine all calendar dates in the active month
  const monthDays = useMemo(() => {
    if (!startDate || !endDate) return [];
    const days = [];
    const curr = new Date(startDate);
    const end = new Date(endDate);
    
    // Safety guard against invalid dates
    if (isNaN(curr.getTime()) || isNaN(end.getTime())) return [];

    while (curr <= end) {
      const y = curr.getFullYear();
      const m = String(curr.getMonth() + 1).padStart(2, '0');
      const d = String(curr.getDate()).padStart(2, '0');
      const dateStr = `${y}-${m}-${d}`;
      const dayName = curr.toLocaleString('default', { weekday: 'short' });
      const fullDayName = curr.toLocaleString('default', { weekday: 'long' });
      
      days.push({
        dateStr,
        dayNum: d,
        dayName,
        fullDayName,
        isSunday: dayName === 'Sun',
        dateObj: new Date(curr)
      });
      curr.setDate(curr.getDate() + 1);
    }
    return days;
  }, [startDate, endDate]);

  // Selected date state (default to today if in range, otherwise first day of month)
  const [selectedDate, setSelectedDate] = useState(() => {
    const todayStr = new Date().toISOString().split('T')[0];
    if (startDate && endDate && todayStr >= startDate && todayStr <= endDate) {
      return todayStr;
    }
    return startDate || '2026-09-01';
  });

  // Search & Filter state for classes on selected day
  const [searchFilter, setSearchFilter] = useState('');
  const [coachFilter, setCoachFilter] = useState('All');

  // Modal states for Create Class & Add Student
  const [isAddClassModalOpen, setIsAddClassModalOpen] = useState(false);
  const [isAddStudentModalOpen, setIsAddStudentModalOpen] = useState(false);
  const [targetClassForAddStudent, setTargetClassForAddStudent] = useState(null);

  // New Class Form State
  const [newClassCoach, setNewClassCoach] = useState('');
  const [newClassTimeSlot, setNewClassTimeSlot] = useState(TIME_SLOT_PRESETS[4]); // 05:00 PM - 06:00 PM
  const [newClassLevel, setNewClassLevel] = useState('Basic 1');
  const [newClassBatchType, setNewClassBatchType] = useState('G');
  const [newClassBatchName, setNewClassBatchName] = useState('');
  const [newClassSelectedStudents, setNewClassSelectedStudents] = useState([]);
  const [studentSearchTerm, setStudentSearchTerm] = useState('');
  const [creatingClass, setCreatingClass] = useState(false);
  const [actionMessage, setActionMessage] = useState(null);

  // Map of classes count per date for the ribbon badges
  const classesPerDate = useMemo(() => {
    const map = {};
    (detailedClasses || []).forEach(cls => {
      if (cls.date) {
        map[cls.date] = (map[cls.date] || 0) + 1;
      }
    });
    return map;
  }, [detailedClasses]);

  // Filter classes for the currently selected date
  const classesForSelectedDay = useMemo(() => {
    let list = (detailedClasses || []).filter(cls => cls.date === selectedDate);
    
    if (coachFilter !== 'All') {
      list = list.filter(cls => cls.coach_name?.toLowerCase() === coachFilter.toLowerCase());
    }

    if (searchFilter.trim()) {
      const q = searchFilter.toLowerCase();
      list = list.filter(cls => 
        cls.coach_name?.toLowerCase().includes(q) ||
        cls.time_slot?.toLowerCase().includes(q) ||
        cls.student_level?.toLowerCase().includes(q) ||
        cls.students_formatted?.toLowerCase().includes(q) ||
        cls.student_names?.some(n => n.toLowerCase().includes(q)) ||
        cls.student_ids?.some(id => id.toLowerCase().includes(q))
      );
    }

    // Sort chronologically by time slot
    return list.sort((a, b) => {
      const aSlot = a.time_slot || '';
      const bSlot = b.time_slot || '';
      return aSlot.localeCompare(bSlot);
    });
  }, [detailedClasses, selectedDate, coachFilter, searchFilter]);

  // Selected date info
  const selectedDayInfo = useMemo(() => {
    const d = monthDays.find(item => item.dateStr === selectedDate);
    if (d) return d;
    const dateObj = new Date(selectedDate);
    return {
      dateStr: selectedDate,
      dayNum: String(dateObj.getDate()).padStart(2, '0'),
      dayName: dateObj.toLocaleString('default', { weekday: 'short' }),
      fullDayName: dateObj.toLocaleString('default', { weekday: 'long' }),
      isSunday: dateObj.getDay() === 0
    };
  }, [monthDays, selectedDate]);

  // Unique coaches list for filter dropdown and create class modal
  const availableCoaches = useMemo(() => {
    if (coaches && coaches.length > 0) return coaches;
    const set = new Set();
    (detailedClasses || []).forEach(cls => {
      if (cls.coach_name) set.add(cls.coach_name);
    });
    return Array.from(set).map(name => ({ coach_name: name }));
  }, [coaches, detailedClasses]);

  // Handle Quick Day Navigation
  const handlePrevDay = () => {
    const idx = monthDays.findIndex(d => d.dateStr === selectedDate);
    if (idx > 0) {
      setSelectedDate(monthDays[idx - 1].dateStr);
    }
  };

  const handleNextDay = () => {
    const idx = monthDays.findIndex(d => d.dateStr === selectedDate);
    if (idx >= 0 && idx < monthDays.length - 1) {
      setSelectedDate(monthDays[idx + 1].dateStr);
    }
  };

  const handleToday = () => {
    const todayStr = new Date().toISOString().split('T')[0];
    const match = monthDays.find(d => d.dateStr === todayStr);
    if (match) setSelectedDate(match.dateStr);
    else if (monthDays.length > 0) setSelectedDate(monthDays[0].dateStr);
  };

  // Toast notification helper
  const showToast = (msg, type = 'success') => {
    setActionMessage({ text: msg, type });
    setTimeout(() => setActionMessage(null), 4000);
  };

  // Delete a class directly from this day
  const handleDeleteClass = async (cls) => {
    if (!scheduleId) return;
    const confirmMsg = `Cancel and delete class on ${cls.date} at ${cls.time_slot} (${cls.coach_name})?\nAll assigned students will safely return to the Unscheduled Pool.`;
    if (!window.confirm(confirmMsg)) return;

    try {
      await deleteClass(scheduleId, cls.class_id);
      showToast(`Class at ${cls.time_slot} deleted successfully.`);
      if (onRefreshSchedule) onRefreshSchedule();
    } catch (err) {
      console.error('Failed to delete class:', err);
      showToast('Error deleting class. Please try again.', 'danger');
    }
  };

  // Remove a single student chip from a class
  const handleRemoveStudentFromClass = async (cls, studentId, studentName) => {
    if (!scheduleId) return;
    if (!window.confirm(`Remove ${studentName} (${studentId}) from this class?`)) return;

    try {
      const remainingIds = (cls.student_ids || []).filter(id => id !== studentId);
      await applyManualEdit(scheduleId, {
        class_id: cls.class_id,
        coach_name: cls.coach_name,
        date: cls.date,
        time_slot: cls.time_slot,
        student_level: cls.student_level,
        batch_type: cls.batch_type,
        student_ids: remainingIds
      });

      showToast(`Removed ${studentName} from class.`);
      if (onRefreshSchedule) onRefreshSchedule();
    } catch (err) {
      console.error('Failed to remove student:', err);
      showToast('Error removing student from class.', 'danger');
    }
  };

  // Open Add Student Modal for a class
  const handleOpenAddStudent = (cls) => {
    setTargetClassForAddStudent(cls);
    setIsAddStudentModalOpen(true);
  };

  // Assign Student to target class
  const handleAssignStudent = async (studentId, studentName) => {
    if (!scheduleId || !targetClassForAddStudent) return;
    try {
      await assignStudentToClass(scheduleId, studentId, targetClassForAddStudent.class_id);
      showToast(`Added ${studentName} to ${targetClassForAddStudent.time_slot} class.`);
      setIsAddStudentModalOpen(false);
      setTargetClassForAddStudent(null);
      if (onRefreshSchedule) onRefreshSchedule();
    } catch (err) {
      console.error('Failed to assign student:', err);
      showToast('Failed to assign student to class.', 'danger');
    }
  };

  // Open Create Class Modal
  const handleOpenCreateClassModal = () => {
    setNewClassCoach(availableCoaches[0]?.coach_name || 'Saravanan');
    setNewClassTimeSlot(TIME_SLOT_PRESETS[4]);
    setNewClassLevel('Basic 1');
    setNewClassBatchType('G');
    setNewClassBatchName('');
    setNewClassSelectedStudents([]);
    setStudentSearchTerm('');
    setIsAddClassModalOpen(true);
  };

  // Submit Create Class
  const handleCreateClassSubmit = async (e) => {
    e.preventDefault();
    if (!scheduleId) {
      alert('No active schedule loaded. Please run the monthly engine first.');
      return;
    }
    if (!newClassCoach) {
      alert('Please select a coach for this class.');
      return;
    }

    setCreatingClass(true);
    try {
      await createScheduleClass(scheduleId, {
        coach_name: newClassCoach,
        date: selectedDate,
        time_slot: newClassTimeSlot,
        student_level: newClassLevel,
        batch_type: newClassBatchType,
        batch_name: newClassBatchName || `${newClassLevel} - ${newClassCoach}`,
        student_ids: newClassSelectedStudents.map(s => s.student_id)
      });

      showToast(`Created new class for ${selectedDate} at ${newClassTimeSlot}!`);
      setIsAddClassModalOpen(false);
      if (onRefreshSchedule) onRefreshSchedule();
    } catch (err) {
      console.error('Failed to create class:', err);
      showToast(err.response?.data?.detail || 'Failed to create class.', 'danger');
    } finally {
      setCreatingClass(false);
    }
  };

  // Helper to toggle student selection in create modal
  const handleToggleSelectStudent = (student) => {
    const exists = newClassSelectedStudents.some(s => s.student_id === student.student_id);
    if (exists) {
      setNewClassSelectedStudents(newClassSelectedStudents.filter(s => s.student_id !== student.student_id));
    } else {
      // Check batch capacity limit
      const maxCap = newClassBatchType === 'I' ? 1 : (newClassBatchType === 'L' ? 4 : 10);
      if (newClassSelectedStudents.length >= maxCap) {
        alert(`Maximum capacity for Batch Type [${newClassBatchType}] is ${maxCap} students.`);
        return;
      }
      setNewClassSelectedStudents([...newClassSelectedStudents, student]);
    }
  };

  // Filtered student candidates for create modal
  const studentCandidates = useMemo(() => {
    const list = unscheduledStudents && unscheduledStudents.length > 0 
      ? unscheduledStudents 
      : masterStudents;

    if (!studentSearchTerm.trim()) return list.slice(0, 30);
    const q = studentSearchTerm.toLowerCase();
    return list.filter(s => 
      s.student_name?.toLowerCase().includes(q) ||
      s.student_id?.toLowerCase().includes(q) ||
      s.student_level?.toLowerCase().includes(q)
    ).slice(0, 30);
  }, [unscheduledStudents, masterStudents, studentSearchTerm]);

  // Statistics for selected day
  const totalClassesToday = classesForSelectedDay.length;
  const uniqueCoachesToday = new Set(classesForSelectedDay.map(c => c.coach_name)).size;
  const totalStudentsToday = classesForSelectedDay.reduce((acc, c) => acc + (c.student_ids?.length || 0), 0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* Toast Alert Banner */}
      {actionMessage && (
        <div
          className="glass-panel"
          style={{
            padding: '12px 20px',
            borderLeft: `4px solid ${actionMessage.type === 'danger' ? 'var(--status-danger)' : 'var(--accent-gold)'}`,
            background: actionMessage.type === 'danger' ? 'rgba(244, 63, 94, 0.15)' : 'rgba(251, 191, 36, 0.15)',
            color: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderRadius: 'var(--radius-md)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.85rem', fontWeight: 700 }}>
            {actionMessage.type === 'danger' ? <AlertCircle size={18} color="var(--status-danger)" /> : <CheckCircle size={18} color="var(--accent-gold)" />}
            <span>{actionMessage.text}</span>
          </div>
          <button onClick={() => setActionMessage(null)} style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer' }}>
            <X size={16} />
          </button>
        </div>
      )}

      {/* 1. Header Banner & Operations Title */}
      <div className="glass-panel" style={{ padding: '20px 24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h2 style={{ fontSize: '1.4rem', fontWeight: 900, color: '#fff', letterSpacing: '-0.02em' }}>
                Daily Schedule Planner & Operations
              </h2>
              <span className="badge badge-gold" style={{ fontSize: '0.7rem', padding: '3px 8px' }}>
                <Sparkles size={10} style={{ marginRight: '4px' }} /> Live Day Plan
              </span>
            </div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Select any day in the month to inspect scheduled slots, customize class rosters, add emergency classes, or reassign trainers.
            </p>
          </div>

          {/* Quick Date Control Actions */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button
              onClick={handlePrevDay}
              className="btn btn-secondary"
              style={{ padding: '8px 12px', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <ChevronLeft size={16} /> Prev Day
            </button>
            <button
              onClick={handleToday}
              className="btn btn-secondary"
              style={{ padding: '8px 14px', fontSize: '0.8rem', fontWeight: 700, color: 'var(--accent-gold)' }}
            >
              Today
            </button>
            <button
              onClick={handleNextDay}
              className="btn btn-secondary"
              style={{ padding: '8px 12px', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              Next Day <ChevronRight size={16} />
            </button>
            <button
              onClick={handleOpenCreateClassModal}
              className="btn btn-primary"
              style={{ padding: '8px 18px', fontSize: '0.85rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '8px', boxShadow: '0 0 15px rgba(251, 191, 36, 0.4)' }}
            >
              <Plus size={16} /> Add Class on This Day
            </button>
          </div>
        </div>

        {/* 2. Horizontal Month Day Ribbon */}
        <div style={{ marginTop: '20px', borderTop: '1px solid var(--border-color)', paddingTop: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.7rem', fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              CALENDAR DAYS OF MONTH ({monthDays.length} DAYS)
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--accent-gold)', fontWeight: 700 }}>
              Active Day: {selectedDayInfo.fullDayName}, {selectedDate}
            </span>
          </div>

          <div
            style={{
              display: 'flex',
              gap: '8px',
              overflowX: 'auto',
              paddingBottom: '10px',
              scrollbarWidth: 'thin'
            }}
          >
            {monthDays.map((d) => {
              const isSelected = d.dateStr === selectedDate;
              const classCount = classesPerDate[d.dateStr] || 0;

              return (
                <button
                  key={d.dateStr}
                  onClick={() => setSelectedDate(d.dateStr)}
                  style={{
                    minWidth: '68px',
                    padding: '8px 6px',
                    borderRadius: 'var(--radius-md)',
                    border: isSelected ? '2px solid var(--accent-gold)' : '1px solid var(--border-color)',
                    background: isSelected
                      ? 'linear-gradient(135deg, rgba(251, 191, 36, 0.25) 0%, rgba(217, 119, 6, 0.25) 100%)'
                      : (d.isSunday ? 'rgba(239, 68, 68, 0.05)' : 'var(--bg-secondary)'),
                    color: isSelected ? '#fff' : 'var(--text-secondary)',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '2px',
                    transition: 'all 0.2s ease',
                    boxShadow: isSelected ? '0 0 12px rgba(251, 191, 36, 0.3)' : 'none',
                    flexShrink: 0
                  }}
                >
                  <span style={{ fontSize: '0.65rem', fontWeight: 800, textTransform: 'uppercase', color: d.isSunday ? 'var(--status-danger)' : (isSelected ? 'var(--accent-gold)' : 'var(--text-muted)') }}>
                    {d.dayName}
                  </span>
                  <span style={{ fontSize: '1.15rem', fontWeight: 900, color: isSelected ? 'var(--accent-gold)' : '#fff' }}>
                    {d.dayNum}
                  </span>
                  <span
                    style={{
                      fontSize: '0.6rem',
                      fontWeight: 700,
                      padding: '1px 5px',
                      borderRadius: '10px',
                      background: classCount > 0 ? (isSelected ? 'var(--accent-gold)' : 'rgba(251, 191, 36, 0.2)') : 'rgba(255, 255, 255, 0.05)',
                      color: classCount > 0 ? (isSelected ? '#000' : 'var(--accent-gold)') : 'var(--text-muted)'
                    }}
                  >
                    {classCount} {classCount === 1 ? 'cls' : 'cls'}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* 3. Selected Day Banner & Stats Bar */}
      <div
        className="glass-panel"
        style={{
          padding: '16px 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '16px',
          background: selectedDayInfo.isSunday ? 'rgba(239, 68, 68, 0.08)' : 'var(--bg-card)',
          borderLeft: selectedDayInfo.isSunday ? '4px solid var(--status-danger)' : '4px solid var(--accent-gold)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 900, color: '#fff' }}>
                {selectedDayInfo.fullDayName}, {selectedDate}
              </h3>
              {selectedDayInfo.isSunday && (
                <span className="badge badge-danger" style={{ fontSize: '0.65rem' }}>
                  Sunday Schedule (Ends ≤ 3:00 PM)
                </span>
              )}
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Manage, edit, or customize all classes scheduled for this date.
            </p>
          </div>
        </div>

        {/* Quick Day Metrics */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
          <div style={{ background: 'var(--bg-secondary)', padding: '6px 14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', textAlign: 'center' }}>
            <span style={{ fontSize: '0.625rem', color: 'var(--text-muted)', fontWeight: 800, textTransform: 'uppercase' }}>CLASSES</span>
            <div style={{ fontSize: '1.1rem', fontWeight: 900, color: 'var(--accent-gold)' }}>{totalClassesToday}</div>
          </div>

          <div style={{ background: 'var(--bg-secondary)', padding: '6px 14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', textAlign: 'center' }}>
            <span style={{ fontSize: '0.625rem', color: 'var(--text-muted)', fontWeight: 800, textTransform: 'uppercase' }}>COACHES</span>
            <div style={{ fontSize: '1.1rem', fontWeight: 900, color: '#38bdf8' }}>{uniqueCoachesToday}</div>
          </div>

          <div style={{ background: 'var(--bg-secondary)', padding: '6px 14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', textAlign: 'center' }}>
            <span style={{ fontSize: '0.625rem', color: 'var(--text-muted)', fontWeight: 800, textTransform: 'uppercase' }}>STUDENTS</span>
            <div style={{ fontSize: '1.1rem', fontWeight: 900, color: '#a855f7' }}>{totalStudentsToday}</div>
          </div>
        </div>
      </div>

      {/* 4. Filter & Search Toolbar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1, minWidth: '240px' }}>
          <div style={{ position: 'relative', width: '100%', maxWidth: '360px' }}>
            <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Search time slot, coach, or student name..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              className="input-field"
              style={{ width: '100%', paddingLeft: '36px', fontSize: '0.825rem' }}
            />
          </div>

          {/* Coach Filter Dropdown */}
          <select
            value={coachFilter}
            onChange={(e) => setCoachFilter(e.target.value)}
            className="input-field"
            style={{ width: '180px', fontSize: '0.825rem' }}
          >
            <option value="All">All Coaches</option>
            {availableCoaches.map((c) => (
              <option key={c.coach_name} value={c.coach_name}>
                {c.coach_name}
              </option>
            ))}
          </select>
        </div>

        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>
          Showing {classesForSelectedDay.length} of {detailedClasses.filter(c => c.date === selectedDate).length} classes
        </span>
      </div>

      {/* 5. Main Day Class Roster Timeline */}
      {classesForSelectedDay.length === 0 ? (
        <div
          className="glass-panel"
          style={{
            padding: '60px 20px',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '16px'
          }}
        >
          <div
            style={{
              width: '64px',
              height: '64px',
              borderRadius: '50%',
              background: 'rgba(251, 191, 36, 0.1)',
              border: '1px solid rgba(251, 191, 36, 0.25)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--accent-gold)'
            }}
          >
            <CalendarIcon size={32} />
          </div>
          <div>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 800, color: '#fff' }}>
              No Classes Scheduled on {selectedDayInfo.fullDayName}, {selectedDate}
            </h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '4px', maxWidth: '500px' }}>
              There are currently no classes planned for this day. You can add a new class right now or run the monthly engine.
            </p>
          </div>
          <button
            onClick={handleOpenCreateClassModal}
            className="btn btn-primary"
            style={{ padding: '10px 22px', fontSize: '0.85rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            <Plus size={16} /> Add First Class for {selectedDayInfo.dayName}
          </button>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(420px, 1fr))', gap: '16px' }}>
          {classesForSelectedDay.map((cls) => {
            const studentCount = cls.student_ids?.length || 0;
            const maxCap = cls.batch_type === 'I' ? 1 : (cls.batch_type === 'L' ? 4 : 10);
            const isFull = studentCount >= maxCap;

            return (
              <div
                key={cls.class_id}
                className="glass-panel"
                style={{
                  padding: '18px 20px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  gap: '14px',
                  border: cls.is_manual_override ? '1px solid rgba(251, 191, 36, 0.45)' : '1px solid var(--border-color)',
                  background: 'linear-gradient(180deg, rgba(15, 23, 42, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%)',
                  borderRadius: 'var(--radius-lg)',
                  boxShadow: 'var(--shadow-subtle)',
                  transition: 'transform 0.2s ease, border-color 0.2s ease'
                }}
              >
                {/* Top: Slot Badge & Class Status */}
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        background: 'rgba(251, 191, 36, 0.15)',
                        border: '1px solid rgba(251, 191, 36, 0.35)',
                        padding: '4px 10px',
                        borderRadius: 'var(--radius-md)',
                        color: 'var(--accent-gold)',
                        fontWeight: 800,
                        fontSize: '0.8rem'
                      }}
                    >
                      <Clock size={14} />
                      <span>{cls.time_slot}</span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span className={`badge ${cls.batch_type === 'I' ? 'badge-info' : (cls.batch_type === 'L' ? 'badge-gold' : 'badge-primary')}`} style={{ fontSize: '0.65rem' }}>
                        Batch [{cls.batch_type}]
                      </span>
                      <span className="badge badge-secondary" style={{ fontSize: '0.65rem' }}>
                        {cls.student_level}
                      </span>
                    </div>
                  </div>

                  {/* Coach & Capacity Row */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px', paddingBottom: '10px', borderBottom: '1px solid var(--border-color)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div
                        style={{
                          width: '32px',
                          height: '32px',
                          borderRadius: '50%',
                          background: 'rgba(56, 189, 248, 0.15)',
                          border: '1px solid rgba(56, 189, 248, 0.3)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          color: '#38bdf8'
                        }}
                      >
                        <User size={16} />
                      </div>
                      <div>
                        <div style={{ fontSize: '0.9rem', fontWeight: 800, color: '#fff' }}>
                          Coach {cls.coach_name}
                        </div>
                        <div style={{ fontSize: '0.675rem', color: 'var(--text-muted)' }}>
                          Assigned Trainer
                        </div>
                      </div>
                    </div>

                    {/* Capacity Indicator */}
                    <div style={{ textAlign: 'right' }}>
                      <span
                        style={{
                          fontSize: '0.75rem',
                          fontWeight: 800,
                          color: isFull ? 'var(--status-danger)' : 'var(--accent-gold)'
                        }}
                      >
                        {studentCount} / {maxCap} Students
                      </span>
                      <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                        {isFull ? 'Batch Full' : `${maxCap - studentCount} seats open`}
                      </div>
                    </div>
                  </div>

                  {/* Students Roster (Chips with remove 'x') */}
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <span style={{ fontSize: '0.65rem', fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                        STUDENTS ENROLLED ({studentCount})
                      </span>
                      {!isFull && (
                        <button
                          onClick={() => handleOpenAddStudent(cls)}
                          style={{
                            background: 'none',
                            border: 'none',
                            color: 'var(--accent-gold)',
                            fontSize: '0.7rem',
                            fontWeight: 800,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px'
                          }}
                        >
                          <Plus size={12} /> Add Student
                        </button>
                      )}
                    </div>

                    {studentCount === 0 ? (
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic', padding: '6px 0' }}>
                        No students enrolled in this batch yet.
                      </div>
                    ) : (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                        {(cls.student_ids || []).map((sid, sIdx) => {
                          const sName = cls.student_names?.[sIdx] || sid;
                          return (
                            <div
                              key={sid}
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '6px',
                                background: 'rgba(255, 255, 255, 0.06)',
                                border: '1px solid var(--border-color)',
                                borderRadius: '16px',
                                padding: '3px 8px',
                                fontSize: '0.75rem',
                                color: '#fff'
                              }}
                            >
                              <span style={{ fontWeight: 700 }}>{sName}</span>
                              <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>({sid})</span>
                              <button
                                onClick={() => handleRemoveStudentFromClass(cls, sid, sName)}
                                title={`Remove ${sName}`}
                                style={{
                                  background: 'none',
                                  border: 'none',
                                  padding: '1px',
                                  color: 'var(--text-muted)',
                                  cursor: 'pointer',
                                  display: 'flex',
                                  alignItems: 'center'
                                }}
                                onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--status-danger)')}
                                onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
                              >
                                <X size={12} />
                              </button>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>

                {/* Bottom Action Footer */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-color)', paddingTop: '10px', marginTop: '6px' }}>
                  <div style={{ display: 'flex', gap: '6px' }}>
                    <button
                      onClick={() => onOpenManualEdit(cls)}
                      className="btn btn-secondary"
                      style={{ padding: '6px 10px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                      title="Edit Trainer, Time Slot, or Level"
                    >
                      <Edit3 size={13} /> Edit Class
                    </button>
                    <button
                      onClick={() => handleOpenAddStudent(cls)}
                      disabled={isFull}
                      className="btn btn-secondary"
                      style={{ padding: '6px 10px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                      title="Assign another student to this batch"
                    >
                      <UserPlus size={13} /> + Student
                    </button>
                  </div>

                  <button
                    onClick={() => handleDeleteClass(cls)}
                    className="btn btn-secondary"
                    style={{ padding: '6px 10px', fontSize: '0.75rem', color: 'var(--status-danger)', borderColor: 'rgba(244, 63, 94, 0.3)', display: 'flex', alignItems: 'center', gap: '4px' }}
                    title="Cancel & Delete Class"
                  >
                    <Trash2 size={13} /> Cancel
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 6. Modal: Create New Class for Selected Date */}
      {isAddClassModalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.8)',
            backdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '20px'
          }}
        >
          <div
            className="glass-panel"
            style={{
              width: '100%',
              maxWidth: '620px',
              maxHeight: '90vh',
              overflowY: 'auto',
              padding: '26px',
              border: '1px solid var(--border-gold)',
              borderRadius: 'var(--radius-lg)'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px', borderBottom: '1px solid var(--border-color)', paddingBottom: '14px' }}>
              <div>
                <h3 style={{ fontSize: '1.25rem', fontWeight: 900, color: '#fff' }}>
                  Create Class for {selectedDayInfo.fullDayName}
                </h3>
                <span style={{ fontSize: '0.8rem', color: 'var(--accent-gold)', fontWeight: 700 }}>
                  Date: {selectedDate}
                </span>
              </div>
              <button
                onClick={() => setIsAddClassModalOpen(false)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleCreateClassSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {/* Coach Selection */}
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 800, color: 'var(--text-muted)', marginBottom: '6px' }}>
                  SELECT TRAINER / COACH
                </label>
                <select
                  value={newClassCoach}
                  onChange={(e) => setNewClassCoach(e.target.value)}
                  className="input-field"
                  style={{ width: '100%', fontSize: '0.85rem' }}
                  required
                >
                  {availableCoaches.map((c) => (
                    <option key={c.coach_name} value={c.coach_name}>
                      Coach {c.coach_name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Time Slot Selection (Pills + Dropdown) */}
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 800, color: 'var(--text-muted)', marginBottom: '6px' }}>
                  SELECT TIME SLOT
                </label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '8px' }}>
                  {TIME_SLOT_PRESETS.map((slot) => (
                    <button
                      key={slot}
                      type="button"
                      onClick={() => setNewClassTimeSlot(slot)}
                      style={{
                        padding: '5px 9px',
                        borderRadius: 'var(--radius-sm)',
                        fontSize: '0.725rem',
                        fontWeight: 700,
                        border: newClassTimeSlot === slot ? '1px solid var(--accent-gold)' : '1px solid var(--border-color)',
                        background: newClassTimeSlot === slot ? 'rgba(251, 191, 36, 0.25)' : 'var(--bg-secondary)',
                        color: newClassTimeSlot === slot ? 'var(--accent-gold)' : 'var(--text-secondary)',
                        cursor: 'pointer'
                      }}
                    >
                      {slot}
                    </button>
                  ))}
                </div>
                <input
                  type="text"
                  placeholder="Or enter custom slot (e.g. 03:30 PM - 04:30 PM)"
                  value={newClassTimeSlot}
                  onChange={(e) => setNewClassTimeSlot(e.target.value)}
                  className="input-field"
                  style={{ width: '100%', fontSize: '0.85rem' }}
                  required
                />
              </div>

              {/* Level & Batch Type in 2 Columns */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 800, color: 'var(--text-muted)', marginBottom: '6px' }}>
                    STUDENT LEVEL
                  </label>
                  <select
                    value={newClassLevel}
                    onChange={(e) => setNewClassLevel(e.target.value)}
                    className="input-field"
                    style={{ width: '100%', fontSize: '0.85rem' }}
                  >
                    {LEVEL_OPTIONS.map((lvl) => (
                      <option key={lvl} value={lvl}>
                        {lvl}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 800, color: 'var(--text-muted)', marginBottom: '6px' }}>
                    BATCH TYPE
                  </label>
                  <select
                    value={newClassBatchType}
                    onChange={(e) => setNewClassBatchType(e.target.value)}
                    className="input-field"
                    style={{ width: '100%', fontSize: '0.85rem' }}
                  >
                    <option value="G">Group [G] (Max 10)</option>
                    <option value="L">Limited [L] (Max 4)</option>
                    <option value="I">Individual [I] (Max 1)</option>
                  </select>
                </div>
              </div>

              {/* Custom Batch Name (Optional) */}
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 800, color: 'var(--text-muted)', marginBottom: '6px' }}>
                  BATCH NAME (OPTIONAL)
                </label>
                <input
                  type="text"
                  placeholder={`e.g. ${newClassLevel} - ${newClassCoach}`}
                  value={newClassBatchName}
                  onChange={(e) => setNewClassBatchName(e.target.value)}
                  className="input-field"
                  style={{ width: '100%', fontSize: '0.85rem' }}
                />
              </div>

              {/* Student Assignment Multi-Select */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <label style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--text-muted)' }}>
                    ASSIGN INITIAL STUDENTS ({newClassSelectedStudents.length} SELECTED)
                  </label>
                  <span style={{ fontSize: '0.7rem', color: 'var(--accent-gold)' }}>
                    Batch limit: {newClassBatchType === 'I' ? 1 : (newClassBatchType === 'L' ? 4 : 10)}
                  </span>
                </div>

                {/* Selected Students Badges */}
                {newClassSelectedStudents.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '10px' }}>
                    {newClassSelectedStudents.map((stu) => (
                      <span
                        key={stu.student_id}
                        style={{
                          background: 'rgba(251, 191, 36, 0.2)',
                          border: '1px solid var(--accent-gold)',
                          padding: '3px 8px',
                          borderRadius: '12px',
                          fontSize: '0.75rem',
                          color: '#fff',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px'
                        }}
                      >
                        {stu.student_name} ({stu.student_id})
                        <X
                          size={12}
                          style={{ cursor: 'pointer' }}
                          onClick={() => handleToggleSelectStudent(stu)}
                        />
                      </span>
                    ))}
                  </div>
                )}

                <input
                  type="text"
                  placeholder="Filter student list..."
                  value={studentSearchTerm}
                  onChange={(e) => setStudentSearchTerm(e.target.value)}
                  className="input-field"
                  style={{ width: '100%', fontSize: '0.8rem', marginBottom: '8px' }}
                />

                <div
                  style={{
                    maxHeight: '140px',
                    overflowY: 'auto',
                    background: 'var(--bg-secondary)',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-color)',
                    padding: '6px'
                  }}
                >
                  {studentCandidates.map((stu) => {
                    const isSelected = newClassSelectedStudents.some(s => s.student_id === stu.student_id);
                    return (
                      <div
                        key={stu.student_id}
                        onClick={() => handleToggleSelectStudent(stu)}
                        style={{
                          padding: '6px 10px',
                          borderRadius: 'var(--radius-sm)',
                          fontSize: '0.75rem',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          cursor: 'pointer',
                          background: isSelected ? 'rgba(251, 191, 36, 0.2)' : 'transparent',
                          color: isSelected ? 'var(--accent-gold)' : '#fff'
                        }}
                      >
                        <span>
                          <strong>{stu.student_name}</strong> ({stu.student_id}) · <span style={{ color: 'var(--text-muted)' }}>{stu.student_level}</span>
                        </span>
                        <span>{isSelected ? '✓ Selected' : '+ Add'}</span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Action Buttons */}
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <button
                  type="button"
                  onClick={() => setIsAddClassModalOpen(false)}
                  className="btn btn-secondary"
                  style={{ padding: '8px 16px', fontSize: '0.85rem' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingClass}
                  className="btn btn-primary"
                  style={{ padding: '8px 22px', fontSize: '0.85rem', fontWeight: 800 }}
                >
                  {creatingClass ? 'Creating Class...' : 'Save & Plan Class'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 7. Modal: Quick Add Student to Existing Class */}
      {isAddStudentModalOpen && targetClassForAddStudent && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.8)',
            backdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '20px'
          }}
        >
          <div
            className="glass-panel"
            style={{
              width: '100%',
              maxWidth: '520px',
              padding: '24px',
              border: '1px solid var(--border-gold)',
              borderRadius: 'var(--radius-lg)'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', borderBottom: '1px solid var(--border-color)', paddingBottom: '10px' }}>
              <div>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#fff' }}>
                  Enroll Student in Class
                </h3>
                <span style={{ fontSize: '0.75rem', color: 'var(--accent-gold)' }}>
                  {targetClassForAddStudent.time_slot} · Coach {targetClassForAddStudent.coach_name}
                </span>
              </div>
              <button
                onClick={() => setIsAddStudentModalOpen(false)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={18} />
              </button>
            </div>

            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
              Select a student to assign directly to this batch. They will be added immediately and sync across all outputs.
            </p>

            <input
              type="text"
              placeholder="Search student name or ID..."
              value={studentSearchTerm}
              onChange={(e) => setStudentSearchTerm(e.target.value)}
              className="input-field"
              style={{ width: '100%', fontSize: '0.825rem', marginBottom: '10px' }}
            />

            <div
              style={{
                maxHeight: '260px',
                overflowY: 'auto',
                background: 'var(--bg-secondary)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-color)',
                padding: '6px'
              }}
            >
              {studentCandidates
                .filter(s => !(targetClassForAddStudent.student_ids || []).includes(s.student_id))
                .map((s) => (
                  <div
                    key={s.student_id}
                    onClick={() => handleAssignStudent(s.student_id, s.student_name)}
                    style={{
                      padding: '8px 12px',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '0.8rem',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      cursor: 'pointer',
                      borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                      transition: 'background 0.2s ease'
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(251, 191, 36, 0.15)')}
                    onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                  >
                    <div>
                      <div style={{ fontWeight: 800, color: '#fff' }}>{s.student_name}</div>
                      <div style={{ fontSize: '0.675rem', color: 'var(--text-muted)' }}>
                        {s.student_id} · {s.student_level || 'Basic'} · {s.batch_type || 'Group'}
                      </div>
                    </div>
                    <button
                      className="btn btn-secondary"
                      style={{ padding: '4px 10px', fontSize: '0.725rem', fontWeight: 800, color: 'var(--accent-gold)' }}
                    >
                      + Assign
                    </button>
                  </div>
                ))}
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '16px' }}>
              <button
                onClick={() => setIsAddStudentModalOpen(false)}
                className="btn btn-secondary"
                style={{ padding: '8px 16px', fontSize: '0.8rem' }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
