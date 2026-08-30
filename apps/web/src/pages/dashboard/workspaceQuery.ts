import type { WorkspaceFilters } from './types';

export function buildWorkspaceQuery(filters: WorkspaceFilters, view: string, page: number, pageSize: number, sort: string) {
  const value = new URLSearchParams({ view, activity_state: filters.activity_state, page: String(page), page_size: String(pageSize), sort, include_participating: String(filters.include_participating) });
  for (const key of ['search', 'created_from', 'created_to', 'title', 'updated_from', 'updated_to', 'environment_id'] as const) if (filters[key]) value.set(key, filters[key]);
  const dynamic = Object.fromEntries(Object.entries(filters.dynamic).filter(([, item]) => item));
  if (Object.keys(dynamic).length) value.set('dynamic_filters', JSON.stringify(dynamic));
  return value.toString();
}

export function nextWorkspaceSort(current: string, key: string) {
  return current.startsWith(`${key}:`) && current.endsWith(':asc') ? `${key}:desc` : `${key}:asc`;
}
