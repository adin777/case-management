import type { UserFieldOption } from '../../../../types';

export function parseCaseFieldOptions(text: string): UserFieldOption[] {
  return [...new Set(text.split(',').map((value) => value.trim()).filter(Boolean))]
    .map((label_he, index) => { let hash=0; for(const char of label_he) hash=(hash*31+char.charCodeAt(0))>>>0; return { value:`option_${index+1}_${hash.toString(36)}`,label_he,label_en:'',is_active:true,sort_order:index+1 }; });
}
