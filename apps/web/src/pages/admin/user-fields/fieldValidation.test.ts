import { describe, expect, it } from 'vitest';
import { buildOptions, fieldSchema, normalizeOptionLabels } from './fieldValidation';

const base = { key: 'department', label_he: 'מחלקה', label_en: '', field_type: 'short_text',
  is_required: false, is_active: true, options_text: '', environment_ids: [], min_length: '',
  max_length: '', placeholder: '', rows: '3', minimum: '', maximum: '', decimals: '0',
  pattern: '', default_value: '', sort_order: 0 };

describe('dynamic user-field configuration', () => {
  it('splits, trims and removes empty and duplicate values', () => {
    expect(normalizeOptionLabels('כספים, , משאבי אנוש,כספים, תפעול')).toEqual(['כספים','משאבי אנוש','תפעול']);
  });
  it('builds stable structured options for chip previews and payloads', () => {
    const options = buildOptions('כספים, מערכות מידע');
    expect(options.map((option) => option.label_he)).toEqual(['כספים','מערכות מידע']);
    expect(options.every((option) => option.value && option.is_active)).toBe(true);
  });
  it('shows options only for select types through schema requirements', () => {
    expect(fieldSchema.safeParse(base).success).toBe(true);
    expect(fieldSchema.safeParse({ ...base, field_type: 'single_select' }).success).toBe(false);
    expect(fieldSchema.safeParse({ ...base, field_type: 'single_select', options_text: 'כספים' }).success).toBe(true);
    expect(fieldSchema.safeParse({ ...base, field_type: 'multi_select', options_text: 'מחשב' }).success).toBe(false);
    expect(fieldSchema.safeParse({ ...base, field_type: 'multi_select', options_text: 'מחשב, מסך' }).success).toBe(true);
  });
  it('validates technical keys and Hebrew labels before submit', () => {
    expect(fieldSchema.safeParse({ ...base, key: '1bad' }).success).toBe(false);
    expect(fieldSchema.safeParse({ ...base, key: 'מחלקה' }).success).toBe(false);
    expect(fieldSchema.safeParse({ ...base, label_he: '' }).success).toBe(false);
  });
  it('supports selecting multiple environments', () => {
    const result = fieldSchema.parse({ ...base, environment_ids: ['env-1','env-2'] });
    expect(result.environment_ids).toHaveLength(2);
  });
});
