/**
 * Official 9 Academy Levels (Source of Truth)
 * No generic 'Beginner', no 'Beginner 3', no generic 'Intermediate'.
 */
export const OFFICIAL_LEVELS = [
  'Basic 1',
  'Basic 2',
  'Beginner 1',
  'Beginner 2',
  'Early Intermediate 1',
  'Early Intermediate 2',
  'Intermediate 1',
  'Intermediate 2',
  'Advanced'
];

/**
 * Filter dropdown options including 'All Levels' wildcard.
 * Note: 'All Levels' is strictly a UI filter, never a database level.
 */
export const FILTER_LEVEL_OPTIONS = [
  'All Levels',
  ...OFFICIAL_LEVELS
];
