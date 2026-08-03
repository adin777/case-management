import type { UserFieldOption } from '../../../../types';

export function parseCaseFieldOptions(text: string): UserFieldOption[] {
  return [...new Set(text.split(',').map((value) => value.trim()).filter(Boolean))]
    .map((label_he, index) => ({ value: label_he.toLowerCase().replace(/\s+/g, '_'), label_he, label_en: '', is_active: true, sort_order: index + 1 }));
}
