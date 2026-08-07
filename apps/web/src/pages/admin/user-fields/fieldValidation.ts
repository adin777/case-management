import { z } from 'zod';
import type { UserFieldOption, UserFieldType } from '../../../types';

export const FIELD_TYPES: UserFieldType[] = ['short_text','long_text','number','date','boolean','single_select','multi_select','user','email','phone'];
export function normalizeOptionLabels(input: string) { return [...new Set(input.split(',').map((value) => value.trim()).filter(Boolean))]; }
export function buildOptions(input: string): UserFieldOption[] { return normalizeOptionLabels(input).map((label_he, index) => ({ value: crypto.randomUUID(), label_he, label_en: '', is_active: true, sort_order: index + 1 })); }
export function suggestKey(label: string) { const ascii = label.toLowerCase().trim().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, ''); return /^[a-z]/.test(ascii) ? ascii : `field_${crypto.randomUUID().slice(0, 8)}`; }
export const fieldSchema = z.object({
  key: z.string().regex(/^[a-z][a-z0-9_]*$/, 'מפתח השדה חייב להתחיל באות אנגלית קטנה ויכול להכיל אותיות, מספרים וקו תחתון בלבד'),
  label_he: z.string().trim().min(1, 'יש להזין תווית בעברית'), label_en: z.string(),
  field_type: z.enum(FIELD_TYPES as [UserFieldType, ...UserFieldType[]]), is_required: z.boolean(), is_active: z.boolean(), options_text: z.string(), environment_ids: z.array(z.string()),
  min_length: z.string(), max_length: z.string(), placeholder: z.string(), rows: z.string(), minimum: z.string(), maximum: z.string(), decimals: z.string(), pattern: z.string(), default_value: z.string(), sort_order: z.number(),
}).superRefine((value, context) => { const count = normalizeOptionLabels(value.options_text).length; if (value.field_type === 'single_select' && count < 1) context.addIssue({ code: 'custom', path: ['options_text'], message: 'יש להזין לפחות ערך אחד עבור שדה בחירה' }); if (value.field_type === 'multi_select' && count < 2) context.addIssue({ code: 'custom', path: ['options_text'], message: 'יש להזין לפחות שני ערכים עבור שדה בחירה מרובה' }); });
export type UserFieldFormValues = z.infer<typeof fieldSchema>;
