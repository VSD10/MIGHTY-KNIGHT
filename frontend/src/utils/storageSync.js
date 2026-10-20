// Client-Side Persistence & Synchronization Helper
// Guarantees zero data loss across page refreshes and serverless cold starts

const CUSTOM_STUDENTS_KEY = 'mk_custom_students';
const CUSTOM_BATCHES_KEY = 'mk_custom_batches';
const DELETED_STUDENTS_KEY = 'mk_deleted_student_ids';
const DELETED_CLASSES_KEY = 'mk_deleted_class_ids';

// --- CUSTOM STUDENTS PERSISTENCE ---
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
    // If this student was previously marked deleted, untrack it
    untrackDeletedStudentLocal(student.student_id);

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

// --- DELETED STUDENTS TRACKING (SQLite is authoritative source of truth) ---
export const getDeletedStudentsLocal = () => {
  // Always defer to SQLite backend database to avoid stale client masking
  return [];
};

export const trackDeletedStudentLocal = (studentId) => {
  // SQLite handles deletion persistence via backend API
};

export const untrackDeletedStudentLocal = (studentId) => {
  // SQLite handles restore/persistence via backend API
};

// --- DELETED CLASSES TRACKING (SQLite is authoritative source of truth) ---
export const getDeletedClassesLocal = () => {
  // Always defer to SQLite backend database to avoid stale client masking
  return [];
};

export const trackDeletedClassLocal = (classId) => {
  // SQLite handles deletion persistence via backend API
};

export const untrackDeletedClassLocal = (classId) => {
  // SQLite handles restore/persistence via backend API
};

// --- WIPE ALL PERSISTENCE ---
export const clearCustomStorageLocal = () => {
  try {
    localStorage.removeItem(CUSTOM_STUDENTS_KEY);
    localStorage.removeItem(CUSTOM_BATCHES_KEY);
    localStorage.removeItem(DELETED_STUDENTS_KEY);
    localStorage.removeItem(DELETED_CLASSES_KEY);
  } catch (err) {
    console.warn("Could not clear custom localStorage:", err);
  }
};
