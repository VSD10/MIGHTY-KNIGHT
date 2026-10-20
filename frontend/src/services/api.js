import axios from 'axios';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
});

export const getHealth = async () => {
  const res = await api.get('/health');
  return res.data;
};

export const getConfig = async () => {
  const res = await api.get('/config');
  return res.data;
};

export const updateConfig = async (configData) => {
  const res = await api.post('/config', configData);
  return res.data;
};

export const uploadExcel = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const res = await api.post('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return res.data;
};

export const runSchedule = async (startDate, endDate) => {
  const res = await api.post('/schedule/run', {
    start_date: startDate,
    end_date: endDate,
  });
  return res.data;
};

export const getOutput1 = async (scheduleId) => {
  const res = await api.get(`/schedule/${scheduleId}/output1`);
  return res.data;
};

export const getOutput2 = async (scheduleId) => {
  const res = await api.get(`/schedule/${scheduleId}/output2`);
  return res.data;
};

export const getOutput3 = async (scheduleId) => {
  const res = await api.get(`/schedule/${scheduleId}/output3`);
  return res.data;
};

export const getOutput5 = async (scheduleId) => {
  const res = await api.get(`/schedule/${scheduleId}/output5`);
  return res.data;
};

export const updateScheduleStatus = async (scheduleId, status) => {
  const res = await api.post(`/schedule/${scheduleId}/status`, { status });
  return res.data;
};

export const validateManualOverride = async (scheduleId, overrideData) => {
  const res = await api.post(`/schedule/${scheduleId}/validate-override`, overrideData);
  return res.data;
};

export const applyManualEdit = async (scheduleId, editData) => {
  const res = await api.post(`/schedule/${scheduleId}/manual-edit`, editData);
  return res.data;
};

export const assignStudentToClass = async (scheduleId, studentId, classId) => {
  const res = await api.post(`/schedule/${scheduleId}/assign-student`, {
    student_id: studentId,
    class_id: classId
  });
  return res.data;
};

export const createClassForStudent = async (scheduleId, classData) => {
  const res = await api.post(`/schedule/${scheduleId}/create-class-for-student`, classData);
  return res.data;
};

export const deleteClass = async (scheduleId, classId) => {
  const res = await api.delete(`/schedule/${scheduleId}/class/${classId}`);
  return res.data;
};

export const createScheduleClass = async (scheduleId, classData) => {
  const res = await api.post(`/schedule/${scheduleId}/classes`, classData);
  return res.data;
};

export const getDownloadTemplateUrl = () => {
  return `${API_BASE_URL}/download-template`;
};

export const getMonthlyMatrixExcelUrl = (scheduleId) => {
  return `${API_BASE_URL}/schedule/${scheduleId}/export-monthly-excel`;
};

export const validateSchedule = async (scheduleId) => {
  const res = await api.get(`/schedule/${scheduleId}/validate`);
  return res.data;
};

export const getCoachExcelUrl = (scheduleId, coachName) => {
  return `${API_BASE_URL}/schedule/${scheduleId}/coach/${encodeURIComponent(coachName)}/export-excel`;
};

export const getCoachIcsUrl = (scheduleId, coachName) => {
  return `${API_BASE_URL}/schedule/${scheduleId}/coach/${encodeURIComponent(coachName)}/export-ics`;
};

export const getStudentIcsUrl = (scheduleId, studentId) => {
  return `${API_BASE_URL}/schedule/${scheduleId}/student/${encodeURIComponent(studentId)}/export-ics`;
};

export const getCoachWhatsAppMsg = async (scheduleId, coachName) => {
  const res = await api.get(`/schedule/${scheduleId}/coach/${encodeURIComponent(coachName)}/whatsapp`);
  return res.data;
};

export const getMasterData = async () => {
  const res = await api.get('/master/data');
  return res.data;
};

export const getMasterStudents = async () => {
  const res = await api.get('/master/students');
  return res.data;
};

export const getMasterStats = async () => {
  const res = await api.get('/master/stats');
  return res.data;
};

export const saveMasterStudent = async (studentData) => {
  const res = await api.post('/master/students', studentData);
  return res.data;
};

export const deleteMasterStudent = async (studentId, scope = 'remove_from_schedule') => {
  const res = await api.delete(`/master/students/${studentId}?scope=${encodeURIComponent(scope)}`);
  return res.data;
};

export const saveMasterCoach = async (coachData) => {
  const res = await api.post('/master/coaches', coachData);
  return res.data;
};

export const deleteMasterCoach = async (coachName, scope = 'remove_from_schedule') => {
  const res = await api.delete(`/master/coaches/${encodeURIComponent(coachName)}?scope=${encodeURIComponent(scope)}`);
  return res.data;
};

export const getDataSummary = async () => {
  const res = await api.get('/data/summary');
  return res.data;
};

export const getActiveSchedule = async () => {
  const res = await api.get('/schedule/latest/active');
  return res.data;
};

export const getMasterBatches = async () => {
  const res = await api.get('/master/batches');
  return res.data;
};

export const saveMasterBatch = async (batchData) => {
  const res = await api.post('/master/batches', batchData);
  return res.data;
};

export const deleteMasterBatch = async (batchId, scope = 'remove_from_schedule') => {
  const res = await api.delete(`/master/batches/${encodeURIComponent(batchId)}?scope=${encodeURIComponent(scope)}`);
  return res.data;
};

export const importBatchDataset = async () => {
  const res = await api.post('/master/batches/import-dataset');
  return res.data;
};

export const clearAllMasterData = async () => {
  const res = await api.post('/master/clear-all');
  return res.data;
};

// ==============================================================================
// BASELINE MANAGEMENT APIS (PART E)
// ==============================================================================

export const getBaselineStatus = async (month = '2026-10') => {
  const res = await api.get(`/baseline/status?month=${month}`);
  return res.data;
};

export const getBaselineTemplateUrl = (month = '2026-10') => {
  return `${API_BASE_URL}/baseline/template?month=${month}`;
};

export const uploadBaselineExcel = async (file, month = '2026-10') => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('month', month);
  const res = await api.post('/baseline/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};

export const activateBaseline = async (month, version, user = 'Admin') => {
  const res = await api.post('/baseline/activate', { month, version, user });
  return res.data;
};

export const discardBaseline = async (month) => {
  const res = await api.post('/baseline/discard', { month });
  return res.data;
};

export const getExportActiveBaselineUrl = (month = '2026-10') => {
  return `${API_BASE_URL}/baseline/export-active?month=${month}`;
};

export const generateNextMonthDraft = async (sourceMonth, targetYear, targetMonth, user = 'Admin') => {
  const res = await api.post('/baseline/generate-next-month', {
    source_month: sourceMonth,
    target_year: targetYear,
    target_month: targetMonth,
    user
  });
  return res.data;
};

export const promoteEffectiveToBaseline = async (month, user = 'Admin') => {
  const res = await api.post('/baseline/promote-effective', { month, user });
  return res.data;
};

// ==============================================================================
// EXCEPTION OVERLAY APIS (PART D)
// ==============================================================================

export const validateException = async (exceptionData) => {
  const res = await api.post('/schedule/exception/validate', exceptionData);
  return res.data;
};

export const applyException = async (exceptionData) => {
  const res = await api.post('/schedule/exception/apply', exceptionData);
  return res.data;
};

export const revertException = async (exceptionId, month = '2026-10') => {
  const res = await api.post(`/schedule/exception/${exceptionId}/revert?month=${month}`);
  return res.data;
};

export const getExceptionsList = async (month = '2026-10', status = 'active') => {
  const res = await api.get(`/schedule/exceptions?month=${month}&status=${status}`);
  return res.data;
};

// ==============================================================================
// AUDIT LOGS & EFFECTIVE SCHEDULE APIS (PART A)
// ==============================================================================

export const getAuditLogs = async (month = null, limit = 100) => {
  const url = month ? `/audit-logs?month=${month}&limit=${limit}` : `/audit-logs?limit=${limit}`;
  const res = await api.get(url);
  return res.data;
};

export const getEffectiveSchedule = async (month = '2026-10') => {
  const res = await api.get(`/effective-schedule?month=${month}`);
  return res.data;
};

// ==============================================================================
// F1 MASTER DATA & F2 ENGINE APIS
// ==============================================================================

export const convertBatchType = async (studentId, newBatchType, month = '2026-10') => {
  const res = await api.post('/master/student/convert-batch', {
    student_id: studentId,
    new_batch_type: newBatchType,
    month
  });
  return res.data;
};

export const changeStudentLevel = async (studentId, newLevel, reason = '', month = '2026-10') => {
  const res = await api.post('/master/student/change-level', {
    student_id: studentId,
    new_level: newLevel,
    reason,
    month
  });
  return res.data;
};

export const getCoachPriorityMatrix = async () => {
  const res = await api.get('/master/coaches/priority-matrix');
  return res.data;
};

export const moveCoachPriority = async (level, coachName, direction) => {
  const res = await api.post('/master/coaches/priority/move', {
    level,
    coach_name: coachName,
    direction
  });
  return res.data;
};

export const updateCoachPriority = async (level, coachName, newPriority) => {
  const res = await api.post('/master/coaches/priority', {
    level,
    coach_name: coachName,
    new_priority: newPriority
  });
  return res.data;
};

export const deleteCoachPriority = async (level, coachName) => {
  const res = await api.delete(`/master/coaches/priority?level=${encodeURIComponent(level)}&coach_name=${encodeURIComponent(coachName)}`);
  return res.data;
};

export const addCoachToPriority = async (level, coachName, newPriority = null) => {
  const res = await api.post('/master/coaches/priority/add', {
    level,
    coach_name: coachName,
    new_priority: newPriority
  });
  return res.data;
};

export const getEngineSettings = async () => {
  const res = await api.get('/engine/settings');
  return res.data;
};

export const updateEngineSettings = async (settingsData) => {
  const res = await api.post('/engine/settings', settingsData);
  return res.data;
};

export const getEngineSuggestions = async (studentId, neededClasses = 1, month = '2026-10') => {
  const res = await api.get(`/engine/suggestions?student_id=${encodeURIComponent(studentId)}&needed_classes=${neededClasses}&month=${month}`);
  return res.data;
};

export const acceptEngineSuggestion = async (payload) => {
  const res = await api.post('/engine/suggestions/accept', payload);
  return res.data;
};

export const getSmartBatches = async (month = '2026-10') => {
  const res = await api.get(`/engine/smart-batches?month=${month}`);
  return res.data;
};

export const getConsolidationAdvisor = async (month = '2026-10') => {
  const res = await api.get(`/engine/consolidation-advisor?month=${month}`);
  return res.data;
};

// --- RULE 2: ACTUAL COMPLETED SCHEDULE ---
export const getActualCompletedSchedule = async (month = '2026-10', currentDate = null) => {
  const query = currentDate ? `?month=${month}&current_date=${encodeURIComponent(currentDate)}` : `?month=${month}`;
  const res = await api.get(`/baseline/actual-completed${query}`);
  return res.data;
};

// --- RULE 4: BATCH REASSIGNMENT ---
export const reassignBatchCoach = async (data) => {
  const res = await api.post('/schedule/reassign-batch-coach', data);
  return res.data;
};

// --- RULE 6: ENGINE QUEUE & ASYNC EXECUTION ---
export const enqueueEngineTask = async (taskType, payload = {}) => {
  const res = await api.post('/engine/tasks/enqueue', { task_type: taskType, payload });
  return res.data;
};

export const getEngineTaskStatus = async () => {
  const res = await api.get('/engine/tasks/status');
  return res.data;
};

// --- COACH AVAILABILITY & REMAINING SLOTS ---
export const getCoachAvailability = async (params = {}) => {
  const query = new URLSearchParams();
  if (params.month) query.append('month', params.month);
  if (params.date) query.append('date', params.date);
  if (params.coach_name) query.append('coach_name', params.coach_name);
  if (params.level) query.append('level', params.level);
  if (params.day) query.append('day', params.day);
  if (params.status) query.append('status', params.status);
  if (params.start_date) query.append('start_date', params.start_date);
  if (params.end_date) query.append('end_date', params.end_date);
  const qStr = query.toString();
  const res = await api.get(`/coach-availability${qStr ? '?' + qStr : ''}`);
  return res.data;
};

// --- DELETED RECORDS & ACADEMY INSTRUCTIONS ---
export const getDeletedRecords = async () => {
  const res = await api.get('/deleted-records');
  return res.data;
};

export const saveDeletedRecord = async (data) => {
  const res = await api.post('/deleted-records', data);
  return res.data;
};

export const updateDeletedRecordScope = async (recordId, newScope) => {
  const res = await api.post(`/deleted-records/${recordId}/scope`, { new_scope: newScope });
  return res.data;
};

export const restoreDeletedRecord = async (recordId) => {
  const res = await api.post(`/deleted-records/${recordId}/restore`);
  return res.data;
};

export const permanentlyDeleteRecord = async (recordId) => {
  const res = await api.delete(`/deleted-records/${recordId}/permanent`);
  return res.data;
};

