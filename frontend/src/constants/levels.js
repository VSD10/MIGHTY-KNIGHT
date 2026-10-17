/**
 * Official 8 Academy Levels (Source of Truth)
 * Strictly 8 levels from Basic 1 to Intermediate 2.
 */
export const OFFICIAL_LEVELS = [
  'Basic 1',
  'Basic 2',
  'Beginner 1',
  'Beginner 2',
  'Early Intermediate 1',
  'Early Intermediate 2',
  'Intermediate 1',
  'Intermediate 2'
];

/**
 * Filter dropdown options including 'All Levels' wildcard.
 * Note: 'All Levels' is strictly a UI filter, never a database level.
 */
export const FILTER_LEVEL_OPTIONS = [
  'All Levels',
  ...OFFICIAL_LEVELS
];
