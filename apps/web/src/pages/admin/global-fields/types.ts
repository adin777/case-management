export type GlobalOption = { id: string; label_he: string; label_en: string; is_active: boolean; sort_order: number };
export type GlobalField = { id: string; key: string; label_he: string; label_en: string; field_type: string; is_required: boolean; is_active: boolean; track_history: boolean; sort_order: number; semantic_binding?: string | null; options: GlobalOption[] };
export const fieldTypes = [
  ['text','טקסט קצר'],['textarea','טקסט ארוך'],['number','מספר'],['date','תאריך'],['datetime','תאריך ושעה'],['boolean','כן / לא'],['single_select','בחירה יחידה'],['multi_select','בחירה מרובה'],['user','משתמש'],['email','דוא״ל'],['url','קישור'],
] as const;
export const typeLabel = (value: string) => fieldTypes.find(([key]) => key === value)?.[1] || value;
export const semanticLabel = (value?: string | null) => ({ 'case.status':'סטטוס', 'case.priority':'עדיפות', 'case.sub_priority':'תת עדיפות', 'case.assignee':'מטפל' }[value || ''] || 'ללא');
