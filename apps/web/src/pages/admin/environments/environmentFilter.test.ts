import { describe, expect, it } from 'vitest';
import { filterEnvironments } from './environmentFilter';
import type { Environment } from '../../../types';

const rows = [
  { id: 'a', code: 'A', name_he: 'פעילה', name_en: 'Active', is_active: true },
  { id: 'b', code: 'B', name_he: 'לא פעילה', name_en: 'Inactive', is_active: false },
] as Environment[];

describe('environment active-only filter', () => {
  it('defaults to active-only behavior', () => expect(filterEnvironments(rows, true)).toEqual([rows[0]]));
  it('shows active and inactive when unchecked', () => expect(filterEnvironments(rows, false)).toEqual(rows));
});
