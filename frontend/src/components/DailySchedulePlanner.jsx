import React, { useState, useMemo, useEffect } from 'react';
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
  Filter,
  Copy,
  Check
} from 'lucide-react';
import { deleteClass, applyManualEdit, createScheduleClass, assignStudentToClass, validateException, applyException } from '../services/api';
import RuleViolationModal from './RuleViolationModal';
import CompensationBadge from './CompensationBadge';
import { OFFICIAL_LEVELS, FILTER_LEVEL_OPTIONS } from '../constants/levels';
import { trackDeletedClassLocal, getDeletedClassesLocal } from '../utils/storageSync';
import { formatSingleDayWhatsAppSchedule, copyTextToClipboard } from '../utils/dayScheduleFormatter';

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

const LEVEL_OPTIONS = OFFICIAL_LEVELS;

const getTimeSlotSortMinutes = (timeSlotStr) => {
  if (!timeSlotStr || typeof timeSlotStr !== 'string') return 9999;
  try {
    const match = timeSlotStr.match(/(\d{1,2})(?::(\d{2}))?\s*(AM|PM)/i);
    if (!match) return 9999;
    let hours = parseInt(match[1], 10);
    const minutes = match[2] ? parseInt(match[2], 10) : 0;
    const ampm = match[3].toUpperCase();
    if (ampm === 'PM' && hours < 12) hours += 12;
    if (ampm === 'AM' && hours === 12) hours = 0;
    return hours * 60 + minutes;
  } catch (e) {
    return 9999;
  }
};

export default function DailySchedulePlanner({
  detailedClasses = [],
  scheduleId,
  startDate,
  endDate,
  onRefreshSchedule,
  onOpenManualEdit,
  onDeleteClassOptimistic,
  coaches = [],
  masterStudents = [],
  unscheduledStudents = [],
  masterBatches = []
}) {
  // Local state for instant optimistic class removals (0ms latency UI updates)
  const [optimisticDeletedClassIds, setOptimisticDeletedClassIds] = useState(new Set());

  // Active classes excluding optimistic local deletions
  const activeDetailedClasses = useMemo(() => {
    return (detailedClasses || []).filter(cls => !optimisticDeletedClassIds.has(cls.class_id));
  }, [detailedClasses, optimisticDeletedClassIds]);

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

  // Selected date state (default to startDate if provided, otherwise 2026-10-01)
  const [selectedDate, setSelectedDate] = useState(() => {
    return startDate || '2026-10-01';
  });

  // Keep selectedDate synchronized whenever the active month changes
  useEffect(() => {
    if (startDate) {
      if (!selectedDate || selectedDate < startDate || (endDate && selectedDate > endDate)) {
        setSelectedDate(startDate);
      }
    }
  }, [startDate, endDate]);

  // Search & Filter state for classes on selected day
  const [searchFilter, setSearchFilter] = useState('');
  const [coachFilter, setCoachFilter] = useState('All');
  const [showOnlyCompensation, setShowOnlyCompensation] = useState(false);
  const [copiedDay, setCopiedDay] = useState(false);

  const handleCopySelectedDayWhatsApp = async (e) => {
    e?.stopPropagation?.();
    e?.preventDefault?.();
    const text = formatSingleDayWhatsAppSchedule(selectedDate, selectedDayInfo?.fullDayName, classesForSelectedDay);
    const ok = await copyTextToClipboard(text);
    if (ok) {
      setCopiedDay(true);
      setTimeout(() => setCopiedDay(false), 2500);
    } else {
      alert("Failed to copy schedule to clipboard. Please check clipboard permissions.");
    }
  };

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
  const [violationModalOpen, setViolationModalOpen] = useState(false);
  const [pendingViolations, setPendingViolations] = useState([]);
  const [pendingExceptionPayload, setPendingExceptionPayload] = useState(null);

  // Map student_id -> official Batch Code (e.g. IBN2-01, GB1-01)
  const studentBatchCodeMap = useMemo(() => {
    const m = {};
    (masterBatches || []).forEach(b => {
      const code = b.batch_id || b.batch_name;
      (b.student_ids || []).forEach(sid => { m[sid] = code; });
    });
    (masterStudents || []).forEach(s => {
      const code = s.batch_code || s.batch || s.batch_name || s.assigned_batch_id;
      if (code && !m[s.student_id]) m[s.student_id] = code;
    });
    return m;
  }, [masterBatches, masterStudents]);

  // All ⓒ classes across the entire active month (for Filter ⓒ Only month directory)
  const allMonthCompensationClasses = useMemo(() => {
    return activeDetailedClasses.filter(cls => cls.is_compensation || cls.has_compensation || cls.exception_metadata);
  }, [activeDetailedClasses]);

  // Map of classes count per date for the ribbon badges
  const classesPerDate = useMemo(() => {
    const map = {};
    activeDetailedClasses.forEach(cls => {
      if (cls.date) {
        map[cls.date] = (map[cls.date] || 0) + 1;
      }
    });
    return map;
  }, [activeDetailedClasses]);

  // Filter classes for the currently selected date
  const classesForSelectedDay = useMemo(() => {
    let list = activeDetailedClasses.filter(cls => cls.date === selectedDate);
    
    if (coachFilter !== 'All') {
      list = list.filter(cls => cls.coach_name?.toLowerCase() === coachFilter.toLowerCase());
    }

    if (showOnlyCompensation) {
      list = list.filter(cls => cls.is_compensation || cls.has_compensation);
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

    // Sort chronologically by time slot from AM to PM, then by coach name
    return list.sort((a, b) => {
      const aMin = getTimeSlotSortMinutes(a.time_slot);
      const bMin = getTimeSlotSortMinutes(b.time_slot);
      if (aMin !== bMin) return aMin - bMin;
      return (a.coach_name || '').localeCompare(b.coach_name || '');
    });
  }, [activeDetailedClasses, selectedDate, coachFilter, searchFilter, showOnlyCompensation]);

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
    activeDetailedClasses.forEach(cls => {
      if (cls.coach_name) set.add(cls.coach_name);
    });
    return Array.from(set).map(name => ({ coach_name: name }));
  }, [coaches, activeDetailedClasses]);

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
    if (!cls?.class_id) return;
    const confirmMsg = `Cancel and delete class on ${cls.date} at ${cls.time_slot} (${cls.coach_name})?\nAll assigned students will safely return to the Unscheduled Pool in Attention Required.`;
    if (!window.confirm(confirmMsg)) return;

    const classId = cls.class_id;
    const month = cls.date ? cls.date.substring(0, 7) : '2026-10';

    // 1. Instantly track optimistically in component state for 0ms latency UI removal
    setOptimisticDeletedClassIds(prev => new Set([...prev, classId]));
    showToast(`Class at ${cls.time_slot} cancelled successfully.`);

    // 2. Also notify parent if optimistic callback provided
    if (onDeleteClassOptimistic) {
      onDeleteClassOptimistic(classId);
    }

    // 3. Authoritative Layer 3 exception deletion
    try {
      await applyException({
        month,
        date: cls.date,
        time_slot: cls.time_slot,
        coach_name: cls.coach_name,
        class_id: classId,
        class_key: `${cls.date}||${cls.time_slot}||${cls.coach_name}`,
        action_type: 'delete',
        affected_student_ids: cls.student_ids || [],
        before: cls,
        after: null,
        subtype: 'manual',
        violated_rules: [],
        reason: 'Class removed by Administrator from Daily Planner',
        created_by: 'Admin'
      });
    } catch (excErr) {
      console.warn("Exception deletion note:", excErr);
    }

    // 4. API request to backend
    try {
      if (scheduleId) {
        await deleteClass(scheduleId, classId);
      }
    } catch (err) {
      console.warn('Backend legacy delete note:', err);
    }

    if (onRefreshSchedule) {
      await onRefreshSchedule();
    }
  };

  // Remove a single student chip from a class
  const handleRemoveStudentFromClass = async (cls, studentId, studentName) => {
    if (!window.confirm(`Remove ${studentName} (${studentId}) from this class?`)) return;

    const month = cls.date ? cls.date.substring(0, 7) : '2026-10';
    const remainingIds = (cls.student_ids || []).filter(id => id !== studentId);

    try {
      await applyException({
        month,
        date: cls.date,
        time_slot: cls.time_slot,
        coach_name: cls.coach_name,
        class_id: cls.class_id,
        class_key: `${cls.date}||${cls.time_slot}||${cls.coach_name}`,
        action_type: 'remove_student',
        affected_student_ids: [studentId],
        before: cls,
        after: {
          ...cls,
          student_ids: remainingIds
        },
        subtype: 'manual',
        violated_rules: [],
        reason: `Removed student ${studentName} (${studentId}) from class`,
        created_by: 'Admin'
      });

      showToast(`Removed ${studentName}. Shortfall immediately reflected in Attention Required.`);
      if (onRefreshSchedule) await onRefreshSchedule();
    } catch (err) {
      console.error('Failed to remove student via exception:', err);
      try {
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
        if (onRefreshSchedule) await onRefreshSchedule();
      } catch (fallbackErr) {
        showToast(fallbackErr.response?.data?.detail || 'Error removing student from class.', 'danger');
      }
    }
  };

  // Open Add Student Modal for a class
  const handleOpenAddStudent = (cls) => {
    setTargetClassForAddStudent(cls);
    setIsAddStudentModalOpen(true);
  };

  // Assign Student to target class (Validates rules & pops up RuleViolationModal if violation, then marks as ⓒ)
  const handleAssignStudent = async (studentId, studentName) => {
    if (!targetClassForAddStudent) return;
    const cls = targetClassForAddStudent;
    const month = (cls.date || selectedDate || '2026-10-01').substring(0, 7);
    const updatedSids = [...new Set([...(cls.student_ids || []), studentId])];
    const cleanTime = (cls.time_slot || '').split('-')[0].trim();

    try {
      const valRes = await validateException({
        month,
        date: cls.date,
        time_slot: cleanTime,
        coach_name: cls.coach_name,
        class_id: cls.class_id,
        student_level: cls.student_level,
        batch_type: cls.batch_type,
        student_ids: updatedSids,
        action_type: 'add_student'
      });

      const excPayload = {
        month,
        date: cls.date,
        time_slot: cleanTime,
        coach_name: cls.coach_name,
        class_id: cls.class_id,
        class_key: `${cls.date}||${cleanTime}||${cls.coach_name}`,
        action_type: 'add_student',
        affected_student_ids: [studentId],
        before: { student_ids: cls.student_ids || [] },
        after: { student_ids: updatedSids },
        subtype: 'compensation',
        violated_rules: valRes.violations || [],
        reason: `Added ${studentName} (${studentId}) to ${cls.batch_name || cls.batch_type} class (ⓒ Compensation / Manual Override)`,
        created_by: 'Admin'
      };

      if (valRes.has_violations && valRes.violations?.length > 0) {
        setIsAddStudentModalOpen(false);
        setPendingViolations(valRes.violations);
        setPendingExceptionPayload(excPayload);
        setViolationModalOpen(true);
        return;
      }

      await applyException(excPayload);
      showToast(`Added ${studentName} (${studentId}) to ${cls.batch_name || cls.time_slot} with ⓒ marker! Synced across all pages.`);
      setIsAddStudentModalOpen(false);
      setTargetClassForAddStudent(null);
      if (onRefreshSchedule) await onRefreshSchedule();
    } catch (err) {
      console.error('Failed to assign student:', err);
      showToast(err.response?.data?.detail || 'Failed to assign student to class.', 'danger');
    }
  };

  // Open Create Class Modal
  const handleOpenCreateClassModal = () => {
    setNewClassCoach(availableCoaches[0]?.coach_name || 'BATHRI');
    setNewClassTimeSlot(TIME_SLOT_PRESETS[4]);
    setNewClassLevel('Beginner 1');
    setNewClassBatchType('G');
    setNewClassBatchName('');
    setNewClassSelectedStudents([]);
    setStudentSearchTerm('');
    setIsAddClassModalOpen(true);
  };

  // Submit Create Class (Validates rules first; if violation like Group student in Individual class, pops up RuleViolationModal, then saves as ⓒ!)
  const handleCreateClassSubmit = async (e) => {
    e.preventDefault();
    if (!newClassCoach) {
      alert('Please select a coach for this class.');
      return;
    }

    const month = (selectedDate || '2026-10-01').substring(0, 7);
    const cleanTime = (newClassTimeSlot || '').split('-')[0].trim();
    const sIds = newClassSelectedStudents.map(s => s.student_id);
    const firstStuBatchCode = sIds.length > 0 ? studentBatchCodeMap[sIds[0]] : null;
    const resolvedBatchCode = newClassBatchName.trim() || firstStuBatchCode || `${newClassBatchType}${newClassLevel.split(' ')[0][0].toUpperCase()}1-01`;

    setCreatingClass(true);
    try {
      const valRes = await validateException({
        month,
        date: selectedDate,
        time_slot: cleanTime,
        coach_name: newClassCoach,
        student_level: newClassLevel,
        batch_type: newClassBatchType,
        student_ids: sIds,
        action_type: 'add'
      });

      // Also check if any selected student's registered batch_type differs from newClassBatchType (e.g. Group student given an Individual class)
      const extraViolations = [...(valRes.violations || [])];
      newClassSelectedStudents.forEach(stu => {
        const stuBType = (stu.batch_type || 'G').toUpperCase();
        if (stuBType !== newClassBatchType.toUpperCase()) {
          extraViolations.push({
            rule_id: 'B2_BATCH_TYPE_MISMATCH',
            rule_name: `Batch Type Exception (${stu.student_name}: Registered [${stuBType}] placed in [${newClassBatchType}] Class)`,
            severity: 'hard',
            reason: `${stu.student_name} (${stu.student_id} · ${studentBatchCodeMap[stu.student_id] || stuBType}) is a [${stuBType}] batch student being assigned a manual [${newClassBatchType}] class.`
          });
        }
      });

      const dayName = new Date(selectedDate).toLocaleString('en-US', { weekday: 'long' });
      const excPayload = {
        month,
        date: selectedDate,
        time_slot: cleanTime,
        coach_name: newClassCoach,
        class_key: `${selectedDate}||${cleanTime}||${newClassCoach}`,
        action_type: 'add',
        affected_student_ids: sIds,
        before: {},
        after: {
          day: dayName,
          student_level: newClassLevel,
          batch_type: newClassBatchType,
          batch_name: resolvedBatchCode,
          batch_code: resolvedBatchCode,
          student_ids: sIds
        },
        subtype: extraViolations.length > 0 ? 'rule_exception' : 'compensation',
        violated_rules: extraViolations,
        reason: extraViolations.length > 0
          ? `Admin Override (ⓒ): Created ${resolvedBatchCode} [${newClassBatchType}] class on ${selectedDate} at ${cleanTime}`
          : `Manual / Compensation class (ⓒ) created on ${selectedDate} at ${cleanTime}`,
        created_by: 'Admin'
      };

      if (extraViolations.length > 0) {
        setIsAddClassModalOpen(false);
        setPendingViolations(extraViolations);
        setPendingExceptionPayload(excPayload);
        setViolationModalOpen(true);
        return;
      }

      await applyException(excPayload);
      showToast(`Created class ${resolvedBatchCode} on ${selectedDate} at ${cleanTime} with ⓒ badge!`);
      setIsAddClassModalOpen(false);
      if (onRefreshSchedule) await onRefreshSchedule();
    } catch (err) {
      console.error('Failed to create class:', err);
      showToast(err.response?.data?.detail || 'Failed to create class.', 'danger');
    } finally {
      setCreatingClass(false);
    }
  };

  // Confirm & Acknowledge Rule Violations -> Save with ⓒ Marker
  const handleConfirmViolationException = async ({ subtype, reason }) => {
    if (!pendingExceptionPayload) return;
    try {
      await applyException({
        ...pendingExceptionPayload,
        subtype: subtype || 'rule_exception',
        reason: reason || pendingExceptionPayload.reason
      });
      setViolationModalOpen(false);
      setPendingExceptionPayload(null);
      setPendingViolations([]);
      setTargetClassForAddStudent(null);
      showToast('Rule exception acknowledged and saved with ⓒ marker! Updated across all pages.');
      if (onRefreshSchedule) await onRefreshSchedule();
    } catch (err) {
      console.error('Failed to apply acknowledged exception:', err);
      showToast(err.response?.data?.detail || 'Failed to apply exception.', 'danger');
    }
  };

  // Helper to toggle student selection in create modal
  const handleToggleSelectStudent = (student) => {
    const exists = newClassSelectedStudents.some(s => s.student_id === student.student_id);
    if (exists) {
      setNewClassSelectedStudents(newClassSelectedStudents.filter(s => s.student_id !== student.student_id));
    } else {
      // Check batch capacity limit
      const maxCap = newClassBatchType === 'I' ? 1 : (newClassBatchType === 'L' ? 3 : 8);
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

          <button
            type="button"
            onClick={handleCopySelectedDayWhatsApp}
            title="Copy this date's schedule formatted for WhatsApp"
            className="btn btn-secondary"
            style={{
              padding: '8px 14px',
              fontSize: '0.78rem',
              fontWeight: 800,
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: copiedDay ? 'rgba(16, 185, 129, 0.25)' : 'rgba(255, 255, 255, 0.06)',
              borderColor: copiedDay ? '#10b981' : 'var(--border-color)',
              color: copiedDay ? '#10b981' : '#fff',
              cursor: 'pointer',
              borderRadius: 'var(--radius-md)',
              boxShadow: '0 2px 6px rgba(0,0,0,0.2)'
            }}
          >
            {copiedDay ? <Check size={14} color="#10b981" /> : <Copy size={14} />}
            <span>{copiedDay ? 'Copied WhatsApp!' : 'Copy Day WhatsApp'}</span>
          </button>
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

          {/* Show only ⓒ classes filter toggle (Part D) */}
          <button
            type="button"
            onClick={() => setShowOnlyCompensation(!showOnlyCompensation)}
            className={`btn ${showOnlyCompensation ? 'btn-primary' : 'btn-secondary'}`}
            style={{
              padding: '7px 14px',
              fontSize: '0.8rem',
              fontWeight: 800,
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              borderColor: showOnlyCompensation ? 'var(--accent-gold)' : 'var(--border-color)',
              color: showOnlyCompensation ? '#000' : 'var(--accent-gold)'
            }}
            title="Filter to show temporary compensation or rule exception (ⓒ) classes on this day and across the month"
          >
            <span style={{ fontWeight: 900, fontSize: '0.95rem' }}>ⓒ</span>
            <span>{showOnlyCompensation ? `Showing ⓒ Only (${allMonthCompensationClasses.length} in Month)` : `Filter ⓒ Only (${allMonthCompensationClasses.length} in Month)`}</span>
          </button>
        </div>

        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>
          Showing {classesForSelectedDay.length} of {activeDetailedClasses.filter(c => c.date === selectedDate).length} classes
        </span>
      </div>

      {/* Month-Wide ⓒ Compensation & Exception Directory when Filter ⓒ Only is active */}
      {showOnlyCompensation && (
        <div
          className="glass-panel"
          style={{
            padding: '16px 20px',
            border: '1px solid rgba(251, 191, 36, 0.5)',
            background: 'rgba(120, 53, 15, 0.2)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px', marginBottom: '10px' }}>
            <div>
              <h4 style={{ fontSize: '0.95rem', fontWeight: 900, color: '#fbbf24', margin: 0 }}>
                ⓒ All Compensation & Exception Classes in Active Month ({allMonthCompensationClasses.length})
              </h4>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', margin: '2px 0 0 0' }}>
                {classesForSelectedDay.length === 0
                  ? `No ⓒ classes on ${selectedDate}. Click any date below to jump directly to a ⓒ class in this month:`
                  : `Showing ${classesForSelectedDay.length} ⓒ class(es) on ${selectedDate}. You can also jump to any other ⓒ class in this month below:`}
              </p>
            </div>
            <button
              onClick={() => setShowOnlyCompensation(false)}
              className="btn btn-secondary"
              style={{ padding: '5px 12px', fontSize: '0.75rem' }}
            >
              Show All Classes
            </button>
          </div>
          {allMonthCompensationClasses.length === 0 ? (
            <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
              No ⓒ compensation or exception classes exist in this month yet.
            </div>
          ) : (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {allMonthCompensationClasses.map((cItem) => (
                <button
                  key={cItem.class_id}
                  onClick={() => setSelectedDate(cItem.date)}
                  style={{
                    padding: '6px 12px',
                    borderRadius: '8px',
                    border: cItem.date === selectedDate ? '2px solid #fbbf24' : '1px solid rgba(251, 191, 36, 0.35)',
                    background: cItem.date === selectedDate ? 'rgba(251, 191, 36, 0.25)' : 'rgba(15, 23, 42, 0.85)',
                    color: '#fff',
                    cursor: 'pointer',
                    fontSize: '0.75rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
                >
                  <span style={{ color: '#fbbf24', fontWeight: 900 }}>ⓒ {cItem.date}</span>
                  <span>· {cItem.time_slot}</span>
                  <span style={{ color: '#38bdf8', fontWeight: 700 }}>· {cItem.coach_name}</span>
                  <span style={{ color: '#34d399', fontWeight: 800 }}>[{cItem.batch_code || cItem.batch_name}]</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

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
            const maxCap = cls.batch_type === 'I' ? 1 : (cls.batch_type === 'L' ? 3 : 8);
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

                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                      {/* Tournament visual badge (Part C) */}
                      {cls.is_tournament && (
                        <span
                          className="badge"
                          style={{
                            background: 'linear-gradient(135deg, #f59e0b 0%, #b45309 100%)',
                            color: '#000',
                            fontWeight: 900,
                            fontSize: '0.65rem',
                            border: '1px solid #fbbf24',
                            boxShadow: '0 0 8px rgba(245, 158, 11, 0.4)'
                          }}
                        >
                          🏆 {cls.tournament_name || 'Tournament'}
                        </span>
                      )}

                      {/* Circled ⓒ Badge with popover & Revert (Part D) */}
                      {(cls.is_compensation || cls.has_compensation || cls.exception_metadata) && (
                        <CompensationBadge
                          cls={cls}
                          month={selectedDate ? selectedDate.substring(0, 7) : '2026-10'}
                          onRevertSuccess={onRefreshSchedule}
                        />
                      )}

                      <span
                        className="badge"
                        style={{
                          fontSize: '0.7rem',
                          fontWeight: 900,
                          background: 'rgba(16, 185, 129, 0.18)',
                          border: '1px solid rgba(52, 211, 153, 0.5)',
                          color: '#34d399',
                          padding: '3px 8px'
                        }}
                        title="Official Academy Batch Code"
                      >
                        {cls.batch_code || cls.batch_name || studentBatchCodeMap[cls.student_ids?.[0]] || `Batch [${cls.batch_type}]`}
                      </span>
                      <span className={`badge ${cls.batch_type === 'I' ? 'badge-info' : (cls.batch_type === 'L' ? 'badge-gold' : 'badge-primary')}`} style={{ fontSize: '0.65rem' }}>
                        Type [{cls.batch_type}]
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
                              <span style={{ fontSize: '0.65rem', color: 'var(--accent-gold)', fontWeight: 700 }}>
                                ({sid} · {cls.student_batch_codes?.[sIdx] || studentBatchCodeMap[sid] || cls.batch_name || cls.batch_type})
                              </span>
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
                    <option value="G">Group [G] (Max 8)</option>
                    <option value="L">Limited [L] (Max 3)</option>
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
                    Batch limit: {newClassBatchType === 'I' ? 1 : (newClassBatchType === 'L' ? 3 : 8)}
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
    
      {/* 8. Rule Violation Confirmation Modal (Accept & Acknowledge -> Marks as ⓒ) */}
      <RuleViolationModal
        isOpen={violationModalOpen}
        onClose={() => {
          setViolationModalOpen(false);
          setPendingExceptionPayload(null);
          setPendingViolations([]);
        }}
        violations={pendingViolations}
        onConfirm={handleConfirmViolationException}
        targetSummary={
          pendingExceptionPayload
            ? `${pendingExceptionPayload.date} · ${pendingExceptionPayload.time_slot} · Coach ${pendingExceptionPayload.coach_name}`
            : ''
        }
      />
    </div>
  );
}