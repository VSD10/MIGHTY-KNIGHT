/**
 * Official 9 Academy Levels (Source of Truth)
 * Strict Naming Pattern: [BatchType][LevelCode]-[SubdivisionNumber]
 * Examples: GBN1-01 (Max 8), LB1-01 (Max 3), IEM2-01 (Max 1)
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

export const FILTER_LEVEL_OPTIONS = [
  'All Levels',
  ...OFFICIAL_LEVELS
];

export const LEVEL_TO_CODE = {
  'Basic 1': 'B1',
  'Basic 2': 'B2',
  'Beginner 1': 'BN1',
  'Beginner 2': 'BN2',
  'Early Intermediate 1': 'EM1',
  'Early Intermediate 2': 'EM2',
  'Intermediate 1': 'IM1',
  'Intermediate 2': 'IM2',
  'Advanced': 'ADV'
};

export const CODE_TO_LEVEL = Object.fromEntries(
  Object.entries(LEVEL_TO_CODE).map(([k, v]) => [v, k])
);

export const BATCH_CAPACITIES = {
  G: { min: 1, max: 8, label: 'Group Batch (Max 8)' },
  L: { min: 1, max: 3, label: 'Limited Batch (Max 3)' },
  I: { min: 1, max: 1, label: 'Individual Batch (Exact 1)' }
};

export function formatBatchSubdivisionName(batchType = 'G', level = 'Beginner 1', subNum = 1) {
  const bType = (batchType || 'G').toUpperCase().charAt(0);
  const code = LEVEL_TO_CODE[level] || 'BN1';
  const num = String(subNum).padStart(2, '0');
  return `${bType}${code}-${num}`;
}

export function parseBatchSubdivision(batchName = '') {
  if (!batchName) return null;
  const match = String(batchName).trim().match(/^([GLI])([A-Z0-9]+)-(\d{2,})$/i);
  if (!match) return null;
  const bType = match[1].toUpperCase();
  const lvlCode = match[2].toUpperCase();
  const subNum = parseInt(match[3], 10);
  return {
    batchName,
    batchType: bType,
    levelCode: lvlCode,
    level: CODE_TO_LEVEL[lvlCode] || 'Beginner 1',
    subdivisionNumber: subNum,
    maxCapacity: BATCH_CAPACITIES[bType]?.max || 8
  };
}
