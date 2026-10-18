import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import CalendarPicker from './components/CalendarPicker';
import ExcelUploader from './components/ExcelUploader';
import CoachScheduleView from './components/CoachScheduleView';
import AdminScheduleView from './components/AdminScheduleView';
import AttentionReportView from './components/AttentionReportView';
import CoachWorkloadView from './components/CoachWorkloadView';
import StudentScheduleView from './components/StudentScheduleView';
import MasterDataView from './components/MasterDataView';
import SettingsView from './components/SettingsView';
import ManualEditModal from './components/ManualEditModal';
import DailySchedulePlanner from './components/DailySchedulePlanner';
import AbsoluteScheduleView from './components/AbsoluteScheduleView';
import { runSchedule, getOutput1, getOutput2, getOutput3, getOutput5, updateScheduleStatus, getActiveSchedule, getDataSummary, getConfig, getMasterStudents, getMasterBatches, saveMasterStudent, syncMasterStudentsBulk } from './services/api';
import { getCustomStudentsLocal, getDeletedStudentsLocal, getDeletedClassesLocal, trackDeletedClassLocal, clearCustomStorageLocal } from './utils/storageSync';

const getCurrentMonthBounds = () => {
  return {
    start: '2026-10-01',
    end: '2026-10-31'
  };
};

export default function App() {
  const defaultBounds = getCurrentMonthBounds();
  const [activeTab, setActiveTab] = useState('dayPlanner'); // Default to Daily Schedule Planner for high operations focus
  const [startDate, setStartDate] = useState(defaultBounds.start);
  const [endDate, setEndDate] = useState(defaultBounds.end);
  const [loading, setLoading] = useState(false);
  const [isUploaderOpen, setIsUploaderOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  // Active Schedule State
  const [currentScheduleId, setCurrentScheduleId] = useState(null);
  const [scheduleStatus, setScheduleStatus] = useState('Draft');
  const [activeScheduleInfo, setActiveScheduleInfo] = useState(null);
  const [activeFileInfo, setActiveFileInfo] = useState(null);
  
  // Output states
  const [output1Data, setOutput1Data] = useState(null);
  const [output2Data, setOutput2Data] = useState(null);
  const [output3Data, setOutput3Data] = useState(null);
  const [output5Data, setOutput5Data] = useState(null);
  const [systemConfig, setSystemConfig] = useState(null);
  const [masterStudentsList, setMasterStudentsList] = useState([]);
  const [masterBatchesList, setMasterBatchesList] = useState([]);

  // Manual edit modal state
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [targetEditClass, setTargetEditClass] = useState(null);

  // Load existing active schedule and config from SQLite on initial page load / server restart
  useEffect(() => {
    try {
      localStorage.removeItem('mk_deleted_classes');
      localStorage.removeItem('mk_deleted_student_ids');
    } catch (e) {}
    loadInitialActiveSchedule();
    fetchSystemConfig();
    fetchMasterStudentsList();
    fetchMasterBatchesList();
  }, []);


  const refreshScheduleRef = React.useRef();

  useEffect(() => {
    if (startDate) {
      const mStr = startDate.substring(0, 7);
      if (refreshScheduleRef.current) {
        refreshScheduleRef.current(currentScheduleId, null, mStr);
      }
    }
  }, [startDate]);

  const [isEngineBackgroundActive, setIsEngineBackgroundActive] = useState(false);
  const [backgroundJobMessage, setBackgroundJobMessage] = useState('');

  // Real-time SSE listener for fire-speed automatic updates (Part A4)
  useEffect(() => {
    let eventSource;
    try {
      eventSource = new EventSource('/api/events/stream');
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'ScheduleChanged') {
            console.log('[SSE] ScheduleChanged event received, updating view...', data);
            setIsEngineBackgroundActive(false);
            setBackgroundJobMessage('');
            if (refreshScheduleRef.current) {
              refreshScheduleRef.current(null, null, data.month);
            }
          }
        } catch (err) {
          console.warn('[SSE] Parse error:', err);
        }
      };
      eventSource.onerror = () => {
        // SSE may drop temporarily on server restart, browser auto-reconnects
      };
    } catch (e) {
      console.warn('[SSE] Failed to establish EventSource:', e);
    }
    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, []);

  // Pass-through filters: backend Layer 1 + Layer 3 Effective Schedule is the single authoritative source of truth
  const filterDeletedFromOutput3 = (o3, extraStudent = null) => {
    if (!o3) return o3;
    const deletedIds = new Set(getDeletedStudentsLocal());

    // 1. Filter out deleted students from attention_records
    let attentionRecords = (o3.attention_records || []).filter(
      r => !deletedIds.has(r.student_id)
    );

    // 2. Discover all known active students
    const allStudentsMap = new Map();
    (masterStudentsList || []).forEach(s => {
      if (s?.student_id && !deletedIds.has(s.student_id)) {
        allStudentsMap.set(s.student_id, s);
      }
    });
    getCustomStudentsLocal().forEach(s => {
      if (s?.student_id && !deletedIds.has(s.student_id)) {
        allStudentsMap.set(s.student_id, s);
      }
    });
    if (extraStudent && extraStudent.student_id && !deletedIds.has(extraStudent.student_id)) {
      allStudentsMap.set(extraStudent.student_id, extraStudent);
    }

    // 3. Count scheduled classes from output2Data
    const scheduledCounts = {};
    if (output2Data?.detailed_classes) {
      output2Data.detailed_classes.forEach(cls => {
        (cls.student_ids || []).forEach(sid => {
          scheduledCounts[sid] = (scheduledCounts[sid] || 0) + 1;
        });
      });
    }

    // 4. Ensure every active student with shortfall is present in attentionRecords
    const existingSids = new Set(attentionRecords.map(r => r.student_id));

    allStudentsMap.forEach((student, sid) => {
      if (student.is_active === false || student.is_active === 'false' || student.is_active === 0 || student.is_active === '0') return;
      const rawReq = Number(student.required_classes ?? 8);
      const sch = scheduledCounts[sid] || 0;
      const rem = Math.max(0, rawReq - sch);

      if (rawReq > 0 && rem > 0 && !existingSids.has(sid)) {
        const lvl = student.student_level || 'Beginner 1';
        const btype = student.batch_type || 'G';
        const bcode = student.batch || student.assigned_batch_id || `${btype} ${lvl}`;
        const isSundayEligible = (btype !== 'I' && lvl !== 'Basic 1' && lvl !== 'Intermediate 2');
        const tournReq = isSundayEligible
          ? 'Sunday Tournament Eligible: Basic 2 to Intermediate 1 (Group & Limited). Operating hours: 09:00 AM – 02:30 PM (cap 20).'
          : (btype === 'I' ? 'Individual Batch (Private 1-on-1): Ineligible for Sunday tournaments.' : 'Regular class scheduling.');

        const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
        const prefDays = days.filter(d => {
          const val = String(student[`${d.toLowerCase()}_pref`] || 'No Preference').toLowerCase();
          return !['not available', 'na', 'no', 'off'].includes(val);
        });

        attentionRecords.unshift({
          student_id: sid,
          student_name: student.student_name || sid,
          student_level: lvl,
          joining_date: student.joining_date || student.start_date || '',
          date_of_joining: student.date_of_joining || student.start_date || '',
          monthly_quota: rawReq,
          quota: rawReq,
          batch_eligibility: btype,
          batch_type: btype,
          batch_name: bcode,
          batch_code: bcode,
          required_classes: rawReq,
          scheduled_classes: sch,
          remaining_classes: rem,
          had_deleted_class: false,
          deleted_class_details: [],
          is_mid_month: false,
          shortfall: 0,
          shortfall_info: '',
          failure_reason: sch === 0
            ? `Unscheduled. Needs ${rem} class assignments to meet monthly requirement.`
            : `Partially scheduled (${sch}/${rawReq} classes). Shortfall of ${rem} class session(s).`,
          sunday_tournament_eligible: isSundayEligible,
          tournament_requirement: tournReq,
          preferred_days: prefDays.length > 0 ? prefDays.join(', ') : 'Mon, Tue, Wed, Thu, Fri, Sat, Sun',
          preferred_time: student.preferred_timings || 'Flexible',
          preferred_timings: student.preferred_timings || 'Flexible',
          preferred_times: student.preferred_times || [],
          preferred_coach: student.preferred_coach || '',
          availability: student.availability || {},
          is_morning_available: student.is_morning_available || false,
          details: `Needs ${rem} more class(es) in Batch ${bcode}`
        });
        existingSids.add(sid);
      }
    });

    return {
      ...o3,
      attention_records: attentionRecords,
      unscheduled_records: attentionRecords,
      unscheduled_count: attentionRecords.length,
      accountability_passed: attentionRecords.length === 0,
      total_students_considered: Math.max(o3.total_students_considered || 0, allStudentsMap.size)
    };
  };

  const handleDeleteClassOptimistic = (classId) => {
    trackDeletedClassLocal(classId);
    setOutput2Data(prev => {
      if (!prev || !prev.detailed_classes) return prev;
      return {
        ...prev,
        detailed_classes: prev.detailed_classes.filter(c => c.class_id !== classId)
      };
    });
  };

  const fetchMasterBatchesList = async () => {
    try {
      const res = await getMasterBatches();
      if (res && res.batches) setMasterBatchesList(res.batches);
    } catch (err) {
      console.error("Failed to fetch master batches:", err);
    }
  };

  const fetchMasterStudentsList = async () => {
    try {
      let res = await getMasterStudents();
      const serverStudents = res?.students || [];
      const deletedIds = new Set(getDeletedStudentsLocal());

      // Check if localStorage has custom students missing from the backend (e.g. serverless cold-start)
      const localCustom = getCustomStudentsLocal().filter(s => !deletedIds.has(s.student_id));
      if (localCustom && localCustom.length > 0) {
        const serverIds = new Set(serverStudents.map(s => s.student_id));
        let syncedAny = false;
        for (const s of localCustom) {
          if (!serverIds.has(s.student_id) && !deletedIds.has(s.student_id)) {
            try {
              console.log(`[STATE SYNC] Syncing custom student ${s.student_id} to backend...`);
              await saveMasterStudent(s);
              syncedAny = true;
            } catch (syncErr) {
              console.warn(`Failed to sync student ${s.student_id}:`, syncErr);
            }
          }
        }
        if (syncedAny) {
          res = await getMasterStudents();
        }
      }

      if (res && res.students) {
        setMasterStudentsList(res.students.filter(s => !deletedIds.has(s.student_id)));
        setOutput3Data(prev => prev ? filterDeletedFromOutput3(prev) : prev);
      }
    } catch (err) {
      console.error("Failed to fetch master students:", err);
    }
  };

  const fetchSystemConfig = async () => {
    try {
      const cfg = await getConfig();
      if (cfg) setSystemConfig(cfg);
    } catch (err) {
      console.error("Failed to fetch system config:", err);
    }
  };

  const fetchActiveFileInfo = async () => {
    try {
      const summary = await getDataSummary();
      if (summary) setActiveFileInfo(summary);
    } catch (err) {
      console.error("Failed to fetch active file summary:", err);
    }
  };

  const handleClearOutputs = () => {
    setCurrentScheduleId(null);
    setScheduleStatus('Draft');
    setActiveScheduleInfo(null);
    setOutput1Data(null);
    setOutput2Data(null);
    setOutput3Data(null);
    setOutput5Data(null);
    fetchActiveFileInfo();
  };

  const loadInitialActiveSchedule = async () => {
    setLoading(true);
    try {
      await fetchActiveFileInfo();
      const mStr = (startDate || '2026-10-01').substring(0, 7);
      const active = await getActiveSchedule(mStr).catch(() => null);
      if (active && active.schedule_id) {
        const sId = active.schedule_id;
        setCurrentScheduleId(sId);
        setActiveScheduleInfo(active);
        setScheduleStatus(active.status || 'Active');
        if (active.start_date) setStartDate(active.start_date);
        if (active.end_date) setEndDate(active.end_date);

        if (active.coach_slots) {
          setOutput1Data({
            schedule_id: sId,
            month: mStr,
            version: active.version,
            total_classes: active.total_classes,
            quotas_completed: active.quotas_completed,
            student_seats: active.student_seats,
            need_attention: active.unscheduled_students_count,
            coach_slots: active.coach_slots,
            whatsapp_plain_text: active.whatsapp_plain_text
          });
        }
        if (active.scheduled_classes) {
          setOutput2Data({
            schedule_id: sId,
            detailed_classes: active.scheduled_classes,
            coach_summaries: active.coach_summaries || [],
            total_classes: active.total_classes,
            student_seats: active.student_seats,
            compensation_count: active.compensation_count || 0
          });
        }
        if (active.attention_records) {
          setOutput3Data(filterDeletedFromOutput3({
            schedule_id: sId,
            month: mStr,
            total_students_considered: active.total_students_considered,
            total_input_students: active.total_students_considered,
            unscheduled_count: active.unscheduled_students_count,
            attention_records: active.attention_records,
            unscheduled_records: active.attention_records
          }));
        }
        if (active.student_schedules) {
          setOutput5Data({
            schedule_id: sId,
            total_students: active.student_schedules.length,
            student_schedules: active.student_schedules
          });
        }

        const [o1, o2, o3, o5] = await Promise.all([
          getOutput1(sId, mStr).catch(() => null),
          getOutput2(sId, mStr).catch(() => null),
          getOutput3(sId, mStr).catch(() => null),
          getOutput5(sId, mStr).catch(() => null),
        ]);

        if (o1) setOutput1Data(o1);
        if (o2) setOutput2Data(filterDeletedClasses(o2));
        if (o3) setOutput3Data(filterDeletedFromOutput3(o3));
        if (o5) setOutput5Data(o5);
      } else {
        clearCustomStorageLocal();
        handleClearOutputs();
      }
    } catch (err) {
      console.error('Failed to load active schedule:', err);
      handleClearOutputs();
    } finally {
      setLoading(false);
    }
  };

  const handleRunScheduler = async (forceAsync = true) => {
    setIsEngineBackgroundActive(true);
    setBackgroundJobMessage('Engine processing in background. All pages remain viewable and responsive...');
    try {
      const result = await runSchedule(startDate, endDate, forceAsync);
      if (result && result.status === 'processing') {
        setBackgroundJobMessage(result.message || 'Engine is executing in background. You can navigate and inspect schedules freely.');
        return;
      }
      const sId = result?.schedule_id;
      if (sId) {
        setCurrentScheduleId(sId);
        setActiveScheduleInfo(result);
        setScheduleStatus(result.status || 'Draft');

        const mStr = (startDate || '2026-10-01').substring(0, 7);
        const [o1, o2, o3, o5] = await Promise.all([
          getOutput1(sId, mStr).catch(() => null),
          getOutput2(sId, mStr).catch(() => null),
          getOutput3(sId, mStr).catch(() => null),
          getOutput5(sId, mStr).catch(() => null),
        ]);

        if (o1) setOutput1Data(o1);
        if (o2) setOutput2Data(filterDeletedClasses(o2));
        if (o3) setOutput3Data(filterDeletedFromOutput3(o3));
        if (o5) setOutput5Data(o5);
        await fetchActiveFileInfo();
      }
    } catch (err) {
      console.error('Failed to run scheduler:', err);
    } finally {
      setTimeout(() => {
        setIsEngineBackgroundActive(false);
        setBackgroundJobMessage('');
      }, 1500);
    }
  };

  const handleStatusToggle = async () => {
    if (!currentScheduleId) return;
    const nextStatus = scheduleStatus === 'Draft' ? 'Finalized' : 'Draft';
    try {
      await updateScheduleStatus(currentScheduleId, nextStatus);
      setScheduleStatus(nextStatus);
    } catch (err) {
      console.error('Failed to update schedule status:', err);
    }
  };

  const handleRefreshCurrentSchedule = async (sId = null, newStudent = null, targetMonth = null) => {
    const mStr = targetMonth || (startDate || '2026-10-01').substring(0, 7);

    if (newStudent) {
      const deletedIds = new Set(getDeletedStudentsLocal());
      if (!deletedIds.has(newStudent.student_id)) {
        setMasterStudentsList(prev => [
          newStudent,
          ...prev.filter(s => s.student_id !== newStudent.student_id)
        ]);
        // Optimistically inject into output3Data immediately with zero delay
        setOutput3Data(prev => {
          const base = prev || {
            schedule_id: sId || `SCHED_${mStr.replace('-', '')}`,
            month: mStr,
            attention_records: [],
            unscheduled_records: [],
            total_students_considered: 1,
            unscheduled_count: 1,
            accountability_passed: false
          };
          return filterDeletedFromOutput3(base, newStudent);
        });
      }
    }

    try {
      setLoading(true);

      // Prime the serverless backend instance with all custom students from localStorage before querying outputs
      const deletedIds = new Set(getDeletedStudentsLocal());
      const localCustom = getCustomStudentsLocal().filter(s => !deletedIds.has(s.student_id));
      if (localCustom && localCustom.length > 0) {
        try {
          await syncMasterStudentsBulk(localCustom);
        } catch (syncErr) {
          console.warn("[SYNC] Bulk custom students sync non-blocking:", syncErr);
        }
      }

      const active = await getActiveSchedule(mStr).catch(() => null);
      const targetId = sId || active?.schedule_id || currentScheduleId || `SCHED_${mStr.replace('-', '')}`;
      setCurrentScheduleId(targetId);

      if (active) {
        setActiveScheduleInfo(active);
        setScheduleStatus(active.status || 'Active');
        if (active.start_date) setStartDate(active.start_date);
        if (active.end_date) setEndDate(active.end_date);

        // Immediate reactive populate from active single source of truth
        if (active.coach_slots) {
          setOutput1Data({
            schedule_id: targetId,
            month: mStr,
            version: active.version,
            total_classes: active.total_classes,
            quotas_completed: active.quotas_completed,
            student_seats: active.student_seats,
            need_attention: active.unscheduled_students_count,
            coach_slots: active.coach_slots,
            whatsapp_plain_text: active.whatsapp_plain_text
          });
        }
        if (active.scheduled_classes) {
          setOutput2Data({
            schedule_id: targetId,
            detailed_classes: active.scheduled_classes,
            coach_summaries: active.coach_summaries || [],
            total_classes: active.total_classes,
            student_seats: active.student_seats,
            compensation_count: active.compensation_count || 0
          });
        }
        if (active.attention_records) {
          setOutput3Data(prev => filterDeletedFromOutput3({
            ...(prev || {}),
            schedule_id: targetId,
            month: mStr,
            total_students_considered: active.total_students_considered,
            total_input_students: active.total_students_considered,
            unscheduled_count: active.unscheduled_students_count,
            attention_records: active.attention_records,
            unscheduled_records: active.attention_records
          }, newStudent));
        }
        if (active.student_schedules) {
          setOutput5Data({
            schedule_id: targetId,
            total_students: active.student_schedules.length,
            student_schedules: active.student_schedules
          });
        }
      }

      const [o1, o2, o3, o5] = await Promise.all([
        getOutput1(targetId, mStr).catch(() => null),
        getOutput2(targetId, mStr).catch(() => null),
        getOutput3(targetId, mStr).catch(() => null),
        getOutput5(targetId, mStr).catch(() => null),
      ]);

      if (o1) setOutput1Data(o1);
      if (o2) setOutput2Data(filterDeletedClasses(o2));
      if (o3) setOutput3Data(filterDeletedFromOutput3(o3, newStudent));
      if (o5) setOutput5Data(o5);

      await fetchActiveFileInfo();
      await fetchMasterStudentsList();
      await fetchMasterBatchesList();
    } catch (err) {
      console.error('Failed to refresh schedule outputs:', err);
    } finally {
      setLoading(false);
    }
  };

  refreshScheduleRef.current = handleRefreshCurrentSchedule;

  const handleOpenManualEdit = (cls) => {
    setTargetEditClass(cls);
    setIsEditModalOpen(true);
  };

  const attentionCount = output3Data?.attention_records?.length ?? output3Data?.unscheduled_records?.length ?? output3Data?.unscheduled_count ?? 0;

  const scheduleStats = {
    totalClasses: output2Data?.detailed_classes?.length || 0,
    totalCoaches: output2Data?.coach_summaries?.length || (output2Data?.detailed_classes ? new Set(output2Data.detailed_classes.map(c => c.coach_name)).size : 0),
    totalStudents: output3Data?.total_students_considered || output3Data?.total_input_students || masterStudentsList?.length || 0,
    completedQuota: output3Data?.scheduled_students_count ?? output3Data?.successfully_scheduled_students ?? (output3Data?.total_students_considered ? Math.max(0, output3Data.total_students_considered - (output3Data.unscheduled_count || 0)) : (activeScheduleInfo?.successfully_scheduled_students || 0)),
    attentionCount: attentionCount,
    totalSessions: (output2Data?.detailed_classes || []).reduce((acc, c) => acc + (c.student_ids?.length || 0), 0),
    hasSchedule: !!currentScheduleId && !!output2Data
  };

  return (
    <div style={{ display: 'flex', gap: '24px', minHeight: '100vh', padding: '24px', maxWidth: '1800px', margin: '0 auto' }}>
      {/* 1. Left Command & Operations Retractable Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        activeFileInfo={activeFileInfo}
        scheduleStatus={scheduleStatus}
        onStatusToggle={handleStatusToggle}
        onUploadClick={() => setIsUploaderOpen(true)}
        onScheduleClick={handleRunScheduler}
        loading={loading}
        attentionCount={attentionCount}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
      />

      {/* 2. Main Executive Operations Canvas */}
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: '24px' }}>
        {/* Top Header & Date Range Selector with Executive Metrics */}
        <CalendarPicker
          startDate={startDate}
          endDate={endDate}
          setStartDate={setStartDate}
          setEndDate={setEndDate}
          onRunScheduler={handleRunScheduler}
          loading={loading}
          stats={scheduleStats}
        />

        {/* Rule 6: Non-Blocking Background Engine Execution Banner */}
        {isEngineBackgroundActive && (
          <div style={{
            background: 'linear-gradient(135deg, rgba(37, 99, 235, 0.12), rgba(79, 70, 229, 0.12))',
            border: '1px solid rgba(59, 130, 246, 0.35)',
            borderRadius: '12px',
            padding: '12px 20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '16px',
            boxShadow: '0 4px 16px rgba(0, 0, 0, 0.25)',
            backdropFilter: 'blur(8px)',
            animation: 'fadeIn 0.3s ease-in-out'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span style={{
                display: 'inline-block',
                width: '10px',
                height: '10px',
                borderRadius: '50%',
                backgroundColor: '#3b82f6',
                boxShadow: '0 0 10px #3b82f6',
                animation: 'pulse 1.5s infinite'
              }} />
              <div>
                <div style={{ fontWeight: 600, color: '#93c5fd', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span>⚡ Background Engine Execution Active (Rule 6)</span>
                </div>
                <div style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>
                  {backgroundJobMessage || 'All pages remain responsive. Operations and changes are safely queued without blocking.'}
                </div>
              </div>
            </div>
            <div style={{ fontSize: '0.75rem', padding: '4px 10px', borderRadius: '6px', background: 'rgba(59, 130, 246, 0.2)', color: '#93c5fd', fontWeight: 600 }}>
              Non-Blocking Mode
            </div>
          </div>
        )}

        {/* Dynamic Canvas Views */}
        <main>
          {activeTab === 'output1' && (
            <CoachScheduleView
              coachScheduleData={output1Data}
              onRunScheduler={handleRunScheduler}
              loading={loading}
            />
          )}

          {activeTab === 'dayPlanner' && (
            <DailySchedulePlanner
              detailedClasses={output2Data?.detailed_classes || []}
              scheduleId={currentScheduleId}
              startDate={startDate}
              endDate={endDate}
              onRefreshSchedule={handleRefreshCurrentSchedule}
              onOpenManualEdit={handleOpenManualEdit}
              onDeleteClassOptimistic={handleDeleteClassOptimistic}
              coaches={output2Data?.coach_summaries || []}
              masterStudents={masterStudentsList}
              unscheduledStudents={output3Data?.attention_records || output3Data?.unscheduled_records || []}
              masterBatches={masterBatchesList}
            />
          )}

          {activeTab === 'output2' && (
            <AdminScheduleView
              adminScheduleData={output2Data}
              onOpenManualEdit={handleOpenManualEdit}
              scheduleId={currentScheduleId}
              onRefreshSchedule={handleRefreshCurrentSchedule}
            />
          )}

          {activeTab === 'output3' && (
            <AttentionReportView
              attentionData={output3Data}
              onOpenManualEditForStudent={handleOpenManualEdit}
              scheduleId={currentScheduleId}
              onRefreshSchedule={handleRefreshCurrentSchedule}
              coachList={output2Data?.coach_summaries?.map(c => c.coach_name) || []}
              activeMonth={(startDate || '2026-10-01').substring(0, 7)}
            />
          )}

          {activeTab === 'coachWorkload' && (
            <CoachWorkloadView
              coachSummaries={output2Data?.coach_summaries || []}
              detailedClasses={output2Data?.detailed_classes || []}
              scheduleId={currentScheduleId}
              onOpenManualEdit={handleOpenManualEdit}
              onRefreshSchedule={handleRefreshCurrentSchedule}
              systemConfig={systemConfig}
              onRefreshConfig={fetchSystemConfig}
            />
          )}

          {activeTab === 'studentSchedules' && (
            <StudentScheduleView
              studentScheduleData={output5Data}
              activeMonth={(startDate || '2026-10-01').substring(0, 7)}
              onRefreshSchedule={handleRefreshCurrentSchedule}
              detailedClasses={output2Data?.detailed_classes || []}
              scheduleId={currentScheduleId}
            />
          )}

          {activeTab === 'masterData' && (
            <MasterDataView
              onReRunScheduler={handleRunScheduler}
              onClearSchedule={handleClearOutputs}
              onRefreshSchedule={(newStu) => handleRefreshCurrentSchedule(currentScheduleId, newStu)}
            />
          )}

          {activeTab === 'absoluteSchedule' && (
            <AbsoluteScheduleView
              activeMonth={(startDate || '2026-10-01').substring(0, 7)}
              onBaselineActivated={(activatedMonth) => handleRefreshCurrentSchedule(null, null, activatedMonth)}
            />
          )}

          {activeTab === 'settings' && (
            <SettingsView
              config={systemConfig}
              onSaveConfigSuccess={(updatedCfg) => {
                setSystemConfig(updatedCfg);
                handleRunScheduler();
              }}
            />
          )}
        </main>
      </div>

      {/* Excel Upload Modal */}
      <ExcelUploader
        isOpen={isUploaderOpen}
        onClose={() => setIsUploaderOpen(false)}
        onUploadSuccess={() => {
          setIsUploaderOpen(false);
          handleRunScheduler();
        }}
      />

      {/* Manual Admin Override Modal */}
      <ManualEditModal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        targetClass={targetEditClass}
        scheduleId={currentScheduleId}
        onSaveSuccess={handleRefreshCurrentSchedule}
        onRefreshSchedule={handleRefreshCurrentSchedule}
        masterStudents={masterStudentsList}
        masterBatches={masterBatchesList}
      />
    </div>
  );
}
