import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import CalendarPicker from './components/CalendarPicker';
import ExcelUploader from './components/ExcelUploader';
import CoachScheduleView from './components/CoachScheduleView';
import AdminScheduleView from './components/AdminScheduleView';
import AttentionReportView from './components/AttentionReportView';
import ManualEditModal from './components/ManualEditModal';
import { runSchedule, getOutput1, getOutput2, getOutput3, updateScheduleStatus } from './services/api';

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

  // Auto-run scheduler on initial load with default data
  useEffect(() => {
    handleRunScheduler();
  }, []);

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
          />
        )}

        {activeTab === 'output3' && (
          <AttentionReportView
            attentionData={output3Data}
            onOpenManualEditForStudent={handleOpenManualEdit}
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
        onSaveSuccess={handleRunScheduler}
      />
    </div>
  );
}
