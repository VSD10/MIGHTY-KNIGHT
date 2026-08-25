import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import CalendarPicker from './components/CalendarPicker';
import ExcelUploader from './components/ExcelUploader';
import CoachScheduleView from './components/CoachScheduleView';
import AdminScheduleView from './components/AdminScheduleView';
import AttentionReportView from './components/AttentionReportView';
import CoachWorkloadView from './components/CoachWorkloadView';
import MasterDataView from './components/MasterDataView';
import ManualEditModal from './components/ManualEditModal';
import { runSchedule, getOutput1, getOutput2, getOutput3, updateScheduleStatus, getActiveSchedule, getDataSummary } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('output2'); // Default to Detailed Admin Matrix
  const [startDate, setStartDate] = useState('2026-08-24');
  const [endDate, setEndDate] = useState('2026-08-30');
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

  // Manual edit modal state
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [targetEditClass, setTargetEditClass] = useState(null);

  // Load existing active schedule from SQLite on initial page load / server restart
  useEffect(() => {
    loadInitialActiveSchedule();
  }, []);

  const fetchActiveFileInfo = async () => {
    try {
      const summary = await getDataSummary();
      if (summary) setActiveFileInfo(summary);
    } catch (err) {
      console.error("Failed to fetch active file summary:", err);
    }
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

        setOutput1Data(o1);
        setOutput2Data(o2);
        setOutput3Data(o3);
      } else {
        handleRunScheduler();
      }
    } catch (err) {
      console.error('Failed to load active schedule:', err);
      handleRunScheduler();
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

      setOutput1Data(o1);
      setOutput2Data(o2);
      setOutput3Data(o3);
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

      setOutput1Data(o1);
      setOutput2Data(o2);
      setOutput3Data(o3);
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

          {activeTab === 'masterData' && (
            <MasterDataView onReRunScheduler={handleRunScheduler} />
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
