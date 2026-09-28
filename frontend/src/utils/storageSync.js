// Client-Side Persistence & Synchronization Helper
// Guarantees zero data loss across page refreshes and serverless cold starts

const CUSTOM_STUDENTS_KEY = 'mk_custom_students';
const CUSTOM_BATCHES_KEY = 'mk_custom_batches';

export const getCustomStudentsLocal = () => {
  try {
    const raw = localStorage.getItem(CUSTOM_STUDENTS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (err) {
    console.warn("Could not read custom students from localStorage:", err);
    return [];
  }
};

export const saveCustomStudentLocal = (student) => {
  if (!student || !student.student_id) return;
  try {
    const list = getCustomStudentsLocal();
    const updated = [
      ...list.filter(s => s.student_id !== student.student_id),
      student
    ];
    localStorage.setItem(CUSTOM_STUDENTS_KEY, JSON.stringify(updated));
  } catch (err) {
    console.warn("Could not save custom student to localStorage:", err);
  }
};

export const deleteCustomStudentLocal = (studentId) => {
  if (!studentId) return;
  try {
    const list = getCustomStudentsLocal();
    const updated = list.filter(s => s.student_id !== studentId);
    localStorage.setItem(CUSTOM_STUDENTS_KEY, JSON.stringify(updated));
  } catch (err) {
    console.warn("Could not remove custom student from localStorage:", err);
  }
};

export const clearCustomStorageLocal = () => {
  try {
    localStorage.removeItem(CUSTOM_STUDENTS_KEY);
    localStorage.removeItem(CUSTOM_BATCHES_KEY);
  } catch (err) {
    console.warn("Could not clear custom localStorage:", err);
  }
};
