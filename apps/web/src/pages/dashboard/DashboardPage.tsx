import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Add } from '@mui/icons-material';
import { Alert, Box, Button, CircularProgress, Container, Pagination, Paper, Stack, Tab, Tabs, Typography } from '@mui/material';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../../api/client';
import type { CaseField, Environment } from '../../types';
import { CaseFilters } from './CaseFilters';
import { DashboardCaseList } from './DashboardCaseList';
import type { WorkspaceFilters, WorkspaceResponse } from './types';

const initial: WorkspaceFilters = { activity_state: 'active', created_from: '', created_to: '', title: '', updated_from: '', updated_to: '', environment_id: '', include_participating: false, dynamic: {} };

export function DashboardPage() {
  const [search, setSearch] = useSearchParams(); const view = search.get('tab') === 'assigned' ? 'assigned' : 'my';
  const [filters, setFilters] = useState(initial); const [page, setPage] = useState(1);
  const { data: environments = [] } = useQuery({ queryKey: ['case-creation-environments'], queryFn: () => api<Environment[]>('/case-creation/environments') });
  const { data: fieldData = {global_fields:[],environment_fields:[]} } = useQuery({ queryKey: ['dashboard-fields', filters.environment_id], queryFn: () => api<{global_fields:CaseField[];environment_fields:CaseField[]}>(`/environments/${filters.environment_id}/case-fields`), enabled: !!filters.environment_id });
  const fields=[...fieldData.global_fields,...fieldData.environment_fields];
  const filterable = fields.filter((field) => field.is_active && field.validation_json?.is_filterable === true);
  const params = useMemo(() => { const value = new URLSearchParams({ view, activity_state: filters.activity_state, page: String(page), page_size: '25', sort: 'updated_at:desc', include_participating: String(filters.include_participating) }); for (const key of ['created_from','created_to','title','updated_from','updated_to','environment_id'] as const) if (filters[key]) value.set(key, filters[key]); const dynamic = Object.fromEntries(Object.entries(filters.dynamic).filter(([, item]) => item)); if (Object.keys(dynamic).length) value.set('dynamic_filters', JSON.stringify(dynamic)); return value.toString(); }, [filters, page, view]);
  const query = useQuery({ queryKey: ['workspace-cases', params], queryFn: () => api<WorkspaceResponse>(`/cases/workspace/query?${params}`), retry: false });
  const changeFilters = (next: WorkspaceFilters) => { setFilters(next); setPage(1); };
  return <Container maxWidth="xl"><Stack spacing={2.5}><Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" gap={2}><Box><Typography variant="h4" fontWeight={800}>מרכז העבודה</Typography><Typography color="text.secondary">הקריאות, המסננים והפעולות החשובות במקום אחד</Typography></Box><Button component={Link} to="/cases/new" variant="contained" startIcon={<Add/>}>פתיחת קריאה חדשה</Button></Stack>
    <Paper variant="outlined"><Tabs value={view} onChange={(_, value) => setSearch({ tab: value })}><Tab value="my" label="הקריאות שלי"/>{(view === 'assigned' || query.data?.can_view_assigned_cases) && <Tab value="assigned" label="קריאות בטיפולי" disabled={query.data?.can_view_assigned_cases === false}/>}</Tabs></Paper>
    <CaseFilters value={filters} environments={environments} fields={filterable} onChange={changeFilters}/>
    {query.error && <Alert severity="error">{(query.error as Error).message}</Alert>}{query.isLoading ? <Box textAlign="center" py={6}><CircularProgress/></Box> : <DashboardCaseList items={query.data?.items || []}/>}
    {(query.data?.total || 0) > 25 && <Pagination page={page} count={Math.ceil((query.data?.total || 0) / 25)} onChange={(_, value) => setPage(value)} sx={{ alignSelf: 'center' }}/>}
  </Stack></Container>;
}
