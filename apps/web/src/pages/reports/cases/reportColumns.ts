import type { CaseReportRow } from '../../../types';

export const reportColumns: [keyof CaseReportRow, string][] = [
  ['case_number', 'מספר קריאה'], ['environment', 'סביבה'], ['request_type', 'סוג קריאה'],
  ['title', 'נושא'], ['description', 'תיאור'], ['status', 'סטטוס'], ['priority', 'עדיפות'],
  ['requester', 'פותח'], ['assignee', 'מטפל'], ['created_at', 'נוצר'], ['updated_at', 'עודכן'],
];
