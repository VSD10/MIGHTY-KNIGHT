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
import { runSchedule, getOutput1, getOutput2, getOutput3, getOutput5, updateScheduleStatus, getActiveSchedule, getDataSummary, getConfig, getMasterStudents } from './services/api';

const getCurrentMonthBounds = () => {
  const today = new Date();
  const y = today.getFullYear();
  const m = today.getMonth();
  const pad = (n) => String(n).padStart(2, '0');
  const lastDay = new Date(y, m + 1, 0).getDate();
  return {
    start: `${y}-${pad(m + 1)}-01`,
    end: `${y}-${pad(m + 1)}-${pad(lastDay)}`
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

  // Manual edit modal state
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [targetEditClass, setTargetEditClass] = useState(null);

  // Load existing active schedule and config from SQLite on initial page load / server restart
  useEffect(() => {
    loadInitialActiveSchedule();
    fetchSystemConfig();
    fetchMasterStudentsList();
  }, []);

  const fetchMasterStudentsList = async () => {
    try {
      const res = await getMasterStudents();
      if (res && res.students) setMasterStudentsList(res.students);
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
        setOutput2Data(o2);
        setOutput3Data(o3);
        if (o5) setOutput5Data(o5);
      } else {
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
      setOutput2Data(o2);
      setOutput3Data(o3);
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

  const handleRefreshCurrentSchedule = async (sId = currentScheduleId) => {
    if (!sId) return;
    try {
      setLoading(true);
      const o1 = await getOutput1(sId);
      const o2 = await getOutput2(sId);
      const o3 = await getOutput3(sId);
      const o5 = await getOutput5(sId).catch(() => null);

      setOutput1Data(o1);
      setOutput2Data(o2);
      setOutput3Data(o3);
      if (o5) setOutput5Data(o5);
      await fetchActiveFileInfo();
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

  const attentionCount = output3Data?.unscheduled_records?.length || 0;

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
        {/* Top Header & Date Range Selector with Top-Right Upload Action */}
        <CalendarPicker
          startDate={startDate}
          endDate={endDate}
          setStartDate={setStartDate}
          setEndDate={setEndDate}
          onRunScheduler={handleRunScheduler}
          loading={loading}
          onUploadClick={() => setIsUploaderOpen(true)}
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
              coaches={output2Data?.coach_summaries || []}
              masterStudents={masterStudentsList}
              unscheduledStudents={output3Data?.unscheduled_records || []}
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
      />
    </div>
  );
}
