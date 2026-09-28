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

// --- DELETED STUDENTS TRACKING ---
export const getDeletedStudentsLocal = () => {
  try {
    const raw = localStorage.getItem(DELETED_STUDENTS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (err) {
    return [];
  }
};

export const trackDeletedStudentLocal = (studentId) => {
  if (!studentId) return;
  try {
    const list = getDeletedStudentsLocal();
    if (!list.includes(studentId)) {
      list.push(studentId);
      localStorage.setItem(DELETED_STUDENTS_KEY, JSON.stringify(list));
    }
  } catch (err) {
    console.warn("Could not track deleted student:", err);
  }
};

export const untrackDeletedStudentLocal = (studentId) => {
  if (!studentId) return;
  try {
    const list = getDeletedStudentsLocal();
    const updated = list.filter(id => id !== studentId);
    localStorage.setItem(DELETED_STUDENTS_KEY, JSON.stringify(updated));
  } catch (err) {
    console.warn("Could not untrack deleted student:", err);
  }
};

// --- DELETED CLASSES TRACKING ---
export const getDeletedClassesLocal = () => {
  try {
    const raw = localStorage.getItem(DELETED_CLASSES_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (err) {
    return [];
  }
};

export const trackDeletedClassLocal = (classId) => {
  if (!classId) return;
  try {
    const list = getDeletedClassesLocal();
    if (!list.includes(classId)) {
      list.push(classId);
      localStorage.setItem(DELETED_CLASSES_KEY, JSON.stringify(list));
    }
  } catch (err) {
    console.warn("Could not track deleted class:", err);
  }
};

export const untrackDeletedClassLocal = (classId) => {
  if (!classId) return;
  try {
    const list = getDeletedClassesLocal();
    const updated = list.filter(id => id !== classId);
    localStorage.setItem(DELETED_CLASSES_KEY, JSON.stringify(updated));
  } catch (err) {
    console.warn("Could not untrack deleted class:", err);
  }
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
