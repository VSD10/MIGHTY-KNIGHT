/**
 * Formats an individual date's complete schedule into clean, WhatsApp-ready text.
 * Strictly adheres to BRD specifications: Date, Day, Time, Coaches, Batches, and Assigned Students.
 */

const getTimeSlotSortMinutes = (timeSlotStr) => {
  if (!timeSlotStr || typeof timeSlotStr !== 'string') return 9999;
  try {
    const match = timeSlotStr.match(/(\d{1,2})(?::(\d{2}))?\s*(AM|PM)/i);
    if (!match) return 9999;
    let hours = parseInt(match[1], 10);
    const minutes = match[2] ? parseInt(match[2], 10) : 0;
    const ampm = match[3].toUpperCase();
    if (ampm === 'PM' && hours < 12) hours += 12;
    if (ampm === 'AM' && hours === 12) hours = 0;
    return hours * 60 + minutes;
  } catch (e) {
    return 9999;
  }
};

/**
 * Format an array of class objects for a single day into clean WhatsApp text.
 * @param {string} dateStr - e.g. "2026-10-01"
 * @param {string} dayStr - e.g. "Thursday"
 * @param {Array} classes - List of class objects for that date
 * @returns {string} WhatsApp-formatted text
 */
export const formatSingleDayWhatsAppSchedule = (dateStr, dayStr, classes = []) => {
  if (!classes || classes.length === 0) {
    return `📅 *${dayStr || 'Date'}, ${dateStr}*\n───────────────────────\nNo classes scheduled for this date.`;
  }

  // Derive day name if not provided
  let effectiveDay = dayStr;
  if (!effectiveDay && classes[0]?.day) {
    effectiveDay = classes[0].day;
  }
  if (!effectiveDay && dateStr) {
    try {
      const d = new Date(dateStr);
      if (!isNaN(d.getTime())) {
        effectiveDay = d.toLocaleDateString('en-US', { weekday: 'long' });
      }
    } catch (e) {}
  }
  if (!effectiveDay) effectiveDay = 'Schedule';

  // Sort classes chronologically by time_slot
  const sortedClasses = [...classes].sort(
    (a, b) => getTimeSlotSortMinutes(a.time_slot) - getTimeSlotSortMinutes(b.time_slot)
  );

  // Group classes by time slot
  const timeSlotMap = new Map();
  sortedClasses.forEach((cls) => {
    const slot = cls.time_slot || 'Flexible Slot';
    if (!timeSlotMap.has(slot)) {
      timeSlotMap.set(slot, []);
    }
    timeSlotMap.get(slot).push(cls);
  });

  const lines = [
    `📅 *${effectiveDay}, ${dateStr}*`,
    `───────────────────────`
  ];

  timeSlotMap.forEach((classesInSlot, slotTime) => {
    const isTournament = classesInSlot.some(c => c.is_tournament);
    const hasCompensation = classesInSlot.some(c => c.is_compensation || c.has_compensation);
    
    // Extract unique coaches for this time slot
    const coachNames = Array.from(new Set(classesInSlot.map(c => c.coach_name).filter(Boolean)));
    const coachStr = coachNames.length > 0 ? coachNames.join(', ') : 'Unassigned';
    
    const tournBadge = isTournament ? ' 🏆 (Tournament)' : '';
    const compBadge = hasCompensation ? ' ⓒ' : '';

    lines.push(`⏰ *${slotTime}* — ${coachStr}${tournBadge}${compBadge}`);

    // Details for each class/batch in this time slot
    classesInSlot.forEach((c) => {
      const coach = c.coach_name || 'Coach';
      const batchCode = c.batch_code || c.batch_name || `Batch ${c.batch_type || 'G'}`;
      const level = c.student_level ? ` (${c.student_level})` : '';
      
      let studentText = c.students_formatted;
      if (!studentText && Array.isArray(c.student_names) && c.student_names.length > 0) {
        studentText = c.student_names.join(', ');
      }
      if (!studentText && Array.isArray(c.student_ids) && c.student_ids.length > 0) {
        studentText = c.student_ids.join(', ');
      }
      if (!studentText) {
        studentText = 'No students assigned';
      }

      const cTag = (c.is_compensation || c.has_compensation) ? ' [ⓒ]' : '';
      const tTag = c.is_tournament ? ' [Tournament]' : '';
      lines.push(`   • ${coach} [${batchCode}${level}${cTag}${tTag}]: ${studentText}`);
    });

    lines.push(''); // Blank line separator between time slots
  });

  return lines.join('\n').trim();
};

/**
 * Format coach_slots object (Output 1 format) for a single day.
 * @param {string} dateStr - "2026-10-01"
 * @param {string} dayStr - "Thursday"
 * @param {Array} coachSlotsForDay - list of coach slot objects
 * @returns {string} WhatsApp-formatted text
 */
export const formatCoachSlotsForDayWhatsApp = (dateStr, dayStr, coachSlotsForDay = []) => {
  if (!coachSlotsForDay || coachSlotsForDay.length === 0) {
    return `📅 *${dayStr || 'Date'}, ${dateStr}*\n───────────────────────\nNo classes scheduled for this date.`;
  }

  const lines = [
    `📅 *${dayStr || 'Day'}, ${dateStr}*`,
    `───────────────────────`
  ];

  const sortedSlots = [...coachSlotsForDay].sort(
    (a, b) => getTimeSlotSortMinutes(a.time_slot) - getTimeSlotSortMinutes(b.time_slot)
  );

  sortedSlots.forEach((slot) => {
    const isTourn = slot.is_tournament;
    const hasComp = slot.has_compensation;
    const tournTag = isTourn ? ' 🏆 (Tournament)' : '';
    const compTag = hasComp ? ' ⓒ' : '';
    const coachesStr = Array.isArray(slot.coaches) ? slot.coaches.join(', ') : (slot.coach_name || '');

    lines.push(`⏰ *${slot.time_slot}* — ${coachesStr}${tournTag}${compTag}`);

    if (slot.batches_summary && typeof slot.batches_summary === 'object') {
      Object.entries(slot.batches_summary).forEach(([cName, batchList]) => {
        if (Array.isArray(batchList)) {
          batchList.forEach((bDetail) => {
            lines.push(`   • ${cName} [${bDetail}]`);
          });
        }
      });
    }
    lines.push('');
  });

  return lines.join('\n').trim();
};

/**
 * Copy text to clipboard with modern API and reliable document.execCommand fallback.
 * @param {string} text - The text to copy
 * @returns {Promise<boolean>} Resolves true on success, false on failure
 */
export const copyTextToClipboard = async (text) => {
  if (!text) return false;

  // 1. Try modern navigator.clipboard API
  if (typeof navigator !== 'undefined' && navigator.clipboard && navigator.clipboard.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (err) {
      console.warn('[Clipboard] navigator.clipboard.writeText failed, trying fallback...', err);
    }
  }

  // 2. Fallback using temporary textarea
  try {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    textArea.setAttribute('readonly', '');
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    const successful = document.execCommand('copy');
    document.body.removeChild(textArea);
    return successful;
  } catch (err) {
    console.error('[Clipboard] document.execCommand fallback failed:', err);
    return false;
  }
};
