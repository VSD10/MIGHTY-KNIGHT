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
import { runSchedule, getOutput1, getOutput2, getOutput3, getOutput5, updateScheduleStatus, getActiveSchedule, getDataSummary, getConfig, getMasterStudents, getMasterBatches, saveMasterStudent } from './services/api';
import { getCustomStudentsLocal, getDeletedStudentsLocal, getDeletedClassesLocal, trackDeletedClassLocal } from './utils/storageSync';

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
    loadInitialActiveSchedule();
    fetchSystemConfig();
    fetchMasterStudentsList();
    fetchMasterBatchesList();
  }, []);

  // Filters to guarantee deleted classes and deleted students stay deleted even across serverless cold starts
  const filterDeletedClasses = (o2) => {
    if (!o2 || !o2.detailed_classes) return o2;
    const deleted = new Set(getDeletedClassesLocal());
    if (deleted.size === 0) return o2;
    return {
      ...o2,
      detailed_classes: o2.detailed_classes.filter(c => !deleted.has(c.class_id))
    };
  };

  const filterDeletedFromOutput3 = (o3) => {
    if (!o3) return o3;
    const deleted = new Set(getDeletedStudentsLocal());
    if (deleted.size === 0) return o3;
    const filteredRecords = (o3.attention_records || []).filter(r => !deleted.has(r.student_id));
    const filteredUnscheduled = (o3.unscheduled_records || []).filter(r => !deleted.has(r.student_id));
    return {
      ...o3,
      attention_records: filteredRecords,
      unscheduled_records: filteredUnscheduled,
      unscheduled_count: filteredRecords.length
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
      const active = await getActiveSchedule();
      if (active && active.schedule_id) {
        const sId = active.schedule_id;
        setCurrentScheduleId(sId);
        setScheduleStatus(active.status || 'Draft');
        if (active.start_date) setStartDate(active.start_date);
        if (active.end_date) setEndDate(active.end_date);

        const o1 = await getOutput1(sId);
        const o2 = await getOutput2(sId);
        const o3 = await getOutput3(sId);
        const o5 = await getOutput5(sId).catch(() => null);

        setOutput1Data(o1);
        setOutput2Data(filterDeletedClasses(o2));
        setOutput3Data(filterDeletedFromOutput3(o3));
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

  const handleRunScheduler = async () => {
    setLoading(true);
    try {
      const result = await runSchedule(startDate, endDate);
      const sId = result.schedule_id;
      setCurrentScheduleId(sId);
      setScheduleStatus(result.status || 'Draft');

      const o1 = await getOutput1(sId);
      const o2 = await getOutput2(sId);
      const o3 = await getOutput3(sId);
      const o5 = await getOutput5(sId).catch(() => null);

      setOutput1Data(o1);
      setOutput2Data(filterDeletedClasses(o2));
      setOutput3Data(filterDeletedFromOutput3(o3));
      if (o5) setOutput5Data(o5);
      await fetchActiveFileInfo();
    } catch (err) {
      console.error('Failed to run scheduler:', err);
    } finally {
      setLoading(false);
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

  const handleRefreshCurrentSchedule = async (sId = currentScheduleId, newStudent = null) => {
    let targetId = sId;
    if (!targetId) {
      try {
        const active = await getActiveSchedule();
        if (active?.schedule_id) {
          targetId = active.schedule_id;
          setCurrentScheduleId(targetId);
        }
      } catch (e) {
        console.warn("Could not resolve active schedule:", e);
      }
    }

    if (newStudent) {
      const deletedIds = new Set(getDeletedStudentsLocal());
      if (!deletedIds.has(newStudent.student_id)) {
        setMasterStudentsList(prev => [
          newStudent,
          ...prev.filter(s => s.student_id !== newStudent.student_id)
        ]);
      }
    }

    if (!targetId) return;
    try {
      setLoading(true);
      const o1 = await getOutput1(targetId);
      const o2 = await getOutput2(targetId);
      const o3 = await getOutput3(targetId);
      const o5 = await getOutput5(targetId).catch(() => null);

      setOutput1Data(o1);
      setOutput2Data(filterDeletedClasses(o2));
      setOutput3Data(filterDeletedFromOutput3(o3));
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

        {/* Dynamic Canvas Views */}
        <main>
          {activeTab === 'output1' && (
            <CoachScheduleView coachScheduleData={output1Data} />
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
            />
          )}

          {activeTab === 'coachWorkload' && (
            <CoachWorkloadView
              coachSummaries={output2Data?.coach_summaries || []}
              detailedClasses={output2Data?.detailed_classes || []}
              scheduleId={currentScheduleId}
            />
          )}

          {activeTab === 'studentSchedules' && (
            <StudentScheduleView
              studentScheduleData={output5Data}
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
