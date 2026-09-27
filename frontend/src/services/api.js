import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

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

export const deleteMasterStudent = async (studentId) => {
  const res = await api.delete(`/master/students/${studentId}`);
  return res.data;
};

export const saveMasterCoach = async (coachData) => {
  const res = await api.post('/master/coaches', coachData);
  return res.data;
};

export const deleteMasterCoach = async (coachName) => {
  const res = await api.delete(`/master/coaches/${encodeURIComponent(coachName)}`);
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

export const deleteMasterBatch = async (batchId) => {
  const res = await api.delete(`/master/batches/${encodeURIComponent(batchId)}`);
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

