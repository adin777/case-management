export type ReportFilters = Record<string, string> & {
  environment_id: string; request_type_id: string; status: string; search: string;
  created_by_id: string; assignee_id: string; created_from: string; created_to: string;
  updated_from: string; updated_to: string; case_number: string; title: string;
  description: string; priority: string; sort: string; direction: string;
  workflow_status_id: string; priority_id: string;
};

export const emptyFilters: ReportFilters = {
  environment_id: '', request_type_id: '', status: '', search: '', created_by_id: '', assignee_id: '',
  created_from: '', created_to: '', updated_from: '', updated_to: '', case_number: '', title: '',
  description: '', priority: '', sort: 'created_at', direction: 'desc',
  workflow_status_id: '', priority_id: '',
};
