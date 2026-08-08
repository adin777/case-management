export type WorkspaceCase = {
  id: string; case_number: string; title: string; environment: string; request_type: string;
  status: string; priority: string; created_at: string; updated_at: string;
};

export type WorkspaceResponse = {
  items: WorkspaceCase[]; total: number; page: number; page_size: number; can_view_assigned_cases: boolean;
};

export type WorkspaceFilters = {
  activity_state: 'active' | 'inactive' | 'all'; created_from: string; created_to: string;
  title: string; updated_from: string; updated_to: string; environment_id: string;
  dynamic: Record<string, string>;
};
