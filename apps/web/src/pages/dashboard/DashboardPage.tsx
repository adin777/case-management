import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Add } from '@mui/icons-material';
import { Alert, Box, Button, CircularProgress, Container, MenuItem, Pagination, Paper, Stack, Tab, Tabs, TextField, Typography } from '@mui/material';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../../api/client';
import type { CaseField, Environment } from '../../types';
import { ScreenHeader } from '../../components/ScreenHeader';
import { CaseFilters } from './CaseFilters';
import { DashboardCaseList } from './DashboardCaseList';
import type { WorkspaceFilters, WorkspaceResponse } from './types';
import { buildWorkspaceQuery, nextWorkspaceSort } from './workspaceQuery';

const initial: WorkspaceFilters = { activity_state: 'active', search: '', created_from: '', created_to: '', title: '', updated_from: '', updated_to: '', environment_id: '', include_participating: false, dynamic: {} };

export function DashboardPage() {
  const [searchParams, setSearchParams] = useSearchParams(); const view = searchParams.get('tab') === 'assigned' ? 'assigned' : 'my';
  const [filters, setFilters] = useState(initial); const [page, setPage] = useState(1); const [pageSize, setPageSize] = useState(25); const [sort, setSort] = useState('updated_at:desc');
  const { data: environments = [] } = useQuery({ queryKey: ['case-creation-environments'], queryFn: () => api<Environment[]>('/case-creation/environments') });
  const { data: fieldData = { global_fields: [], environment_fields: [] } } = useQuery({ queryKey: ['dashboard-fields', filters.environment_id], queryFn: () => api<{ global_fields: CaseField[]; environment_fields: CaseField[] }>(`/environments/${filters.environment_id}/case-fields`), enabled: Boolean(filters.environment_id) });
  const filterable = [...fieldData.global_fields, ...fieldData.environment_fields].filter((field) => field.is_active && field.validation_json?.is_filterable === true);
  const params = useMemo(() => buildWorkspaceQuery(filters, view, page, pageSize, sort), [filters, page, pageSize, sort, view]);
  const query = useQuery({ queryKey: ['workspace-cases', params], queryFn: () => api<WorkspaceResponse>(`/cases/workspace/query?${params}`), retry: false });
  const changeFilters = (next: WorkspaceFilters) => { setFilters(next); setPage(1); };
  const changeSort = (key: string) => { setSort((current) => nextWorkspaceSort(current, key)); setPage(1); };
  return <Box className="workspace-page"><Container maxWidth="xl"><Stack spacing={2.5}>
    <ScreenHeader title="מרכז העבודה" subtitle="הקריאות, המסננים והפעולות החשובות במקום אחד" action={<Button component={Link} to="/cases/new" variant="contained" size="large" startIcon={<Add/>}>פתיחת קריאה חדשה</Button>}/>
    <Paper className="workspace-tabs" variant="outlined"><Tabs value={view} onChange={(_, value) => { setSearchParams({ tab: value }); setPage(1); }}><Tab value="my" label="הקריאות שלי"/>{(view === 'assigned' || query.data?.can_view_assigned_cases) && <Tab value="assigned" label="קריאות בטיפולי" disabled={query.data?.can_view_assigned_cases === false}/>}</Tabs></Paper>
    <CaseFilters value={filters} environments={environments} fields={filterable} onChange={changeFilters} onReset={() => changeFilters({ ...initial })}/>
    {query.error && <Alert severity="error">{(query.error as Error).message}</Alert>}
    {query.isLoading ? <Box textAlign="center" py={7}><CircularProgress/></Box> : <DashboardCaseList items={query.data?.items || []} sort={sort} onSort={changeSort}/>}
    <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems="center" gap={2}>
      <Typography color="text.secondary">{query.data?.total || 0} קריאות</Typography>
      <Pagination page={page} count={Math.max(1, Math.ceil((query.data?.total || 0) / pageSize))} onChange={(_, value) => setPage(value)} color="primary"/>
      <TextField select size="small" label="שורות בעמוד" value={pageSize} onChange={(event) => { setPageSize(Number(event.target.value)); setPage(1); }} sx={{ minWidth: 130 }}>{[10, 25, 50, 100].map((size) => <MenuItem key={size} value={size}>{size}</MenuItem>)}</TextField>
    </Stack>
  </Stack></Container></Box>;
}
