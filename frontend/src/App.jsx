import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import CalendarPicker from './components/CalendarPicker';
import ExcelUploader from './components/ExcelUploader';
import CoachScheduleView from './components/CoachScheduleView';
import AdminScheduleView from './components/AdminScheduleView';
import AttentionReportView from './components/AttentionReportView';
import CoachWorkloadView from './components/CoachWorkloadView';
import ManualEditModal from './components/ManualEditModal';
import { runSchedule, getOutput1, getOutput2, getOutput3, updateScheduleStatus, getActiveSchedule } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('output1');
  const [startDate, setStartDate] = useState('2026-08-24');
  const [endDate, setEndDate] = useState('2026-08-30');
  const [loading, setLoading] = useState(false);
  const [isUploaderOpen, setIsUploaderOpen] = useState(false);

  // Active Schedule State
  const [currentScheduleId, setCurrentScheduleId] = useState(null);
  const [scheduleStatus, setScheduleStatus] = useState('Draft');
  
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

  const loadInitialActiveSchedule = async () => {
    setLoading(true);
    try {
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

      // Fetch all 3 outputs independently
      const o1 = await getOutput1(sId);
      const o2 = await getOutput2(sId);
      const o3 = await getOutput3(sId);

      setOutput1Data(o1);
      setOutput2Data(o2);
      setOutput3Data(o3);
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

  return (
    <div style={{ minHeight: '100vh', padding: '24px 32px', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Top Navigation & App Bar */}
      <Header
        scheduleStatus={scheduleStatus}
        onStatusToggle={handleStatusToggle}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onUploadClick={() => setIsUploaderOpen(true)}
        onScheduleClick={handleRunScheduler}
        loading={loading}
      />

      {/* Date / Calendar Picker Controls */}
      <CalendarPicker
        startDate={startDate}
        endDate={endDate}
        setStartDate={setStartDate}
        setEndDate={setEndDate}
        onRunScheduler={handleRunScheduler}
        loading={loading}
      />

      {/* Active Output View */}
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
      </main>

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
        onSaveSuccess={() => handleRefreshCurrentSchedule(currentScheduleId)}
      />
    </div>
  );
}
