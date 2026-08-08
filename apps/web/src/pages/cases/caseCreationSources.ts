import type { Priority, RequestType, SubPriority } from '../../types';

export const requestTypesUrl = (environmentId: string) =>
  `/request-types?environment_id=${environmentId}&active_only=true`;

export const activeRequestTypes = (rows: RequestType[], environmentId: string) =>
  rows.filter((row) => row.environment_id === environmentId && row.is_active);

export const activePriorities = (rows: Priority[]) => rows.filter((row) => row.is_active);
export const activeSubPriorities = (rows: SubPriority[]) => rows.filter((row) => row.is_active);
