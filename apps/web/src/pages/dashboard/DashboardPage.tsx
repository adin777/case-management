import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Add } from '@mui/icons-material';
import { Alert, Box, Button, Chip, CircularProgress, Container, MenuItem, Pagination, Paper, Stack, Tab, Tabs, TextField, Typography } from '@mui/material';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../../api/client';
import type { CaseField, Environment } from '../../types';
import { ScreenHeader } from '../../components/ScreenHeader';
import { CaseFilters } from './CaseFilters';
import { DashboardCaseList } from './DashboardCaseList';
import type { WorkspaceFilters, WorkspaceResponse } from './types';
import { buildWorkspaceQuery, nextWorkspaceSort } from './workspaceQuery';
import { SavedViewsBar, workspaceColumns, type SavedView } from './SavedViewsBar';
import { CaseQuickPreview } from './CaseQuickPreview';
import { BulkActionBar } from './BulkActionBar';
import { readWorkspaceState, writeWorkspaceState } from './workspaceUrlState';

const initial: WorkspaceFilters = { activity_state: 'active', search: '', created_from: '', created_to: '', title: '', updated_from: '', updated_to: '', environment_id: '', include_participating: false, dynamic: {} };

export function DashboardPage() {
  const [searchParams, setSearchParams] = useSearchParams(); const view = searchParams.get('tab') === 'assigned' ? 'assigned' : 'my'; const queue=searchParams.get('queue')||'';const restored=readWorkspaceState(searchParams,initial);
  const [filters, setFilters] = useState(restored.filters); const [page, setPageState] = useState(restored.page); const [pageSize, setPageSizeState] = useState(restored.pageSize); const [sort, setSortState] = useState(restored.sort); const [visibleColumns,setVisibleColumns]=useState<string[]>([...workspaceColumns]); const[selectedIds,setSelectedIds]=useState<string[]>([]);const[previewId,setPreviewId]=useState<string>();
  const persist=(nextFilters=filters,nextPage=page,nextSize=pageSize,nextSort=sort)=>setSearchParams(writeWorkspaceState(searchParams,nextFilters,nextPage,nextSize,nextSort));const setPage=(value:number)=>{setPageState(value);persist(filters,value)};const setPageSize=(value:number)=>{setPageSizeState(value);setPageState(1);persist(filters,1,value)};const setSort=(value:string)=>{setSortState(value);setPageState(1);persist(filters,1,pageSize,value)};
  const { data: environments = [] } = useQuery({ queryKey: ['case-creation-environments'], queryFn: () => api<Environment[]>('/case-creation/environments') });
  const { data: fieldData = { global_fields: [], environment_fields: [] } } = useQuery({ queryKey: ['dashboard-fields', filters.environment_id], queryFn: () => api<{ global_fields: CaseField[]; environment_fields: CaseField[] }>(`/environments/${filters.environment_id}/case-fields`), enabled: Boolean(filters.environment_id) });
  const filterable = [...fieldData.global_fields, ...fieldData.environment_fields].filter((field) => field.is_active && field.validation_json?.is_filterable === true);
  const params = useMemo(() => buildWorkspaceQuery(filters, view, page, pageSize, sort,queue), [filters, page, pageSize, sort, view,queue]);
  const query = useQuery({ queryKey: ['workspace-cases', params], queryFn: () => api<WorkspaceResponse>(`/cases/workspace/query?${params}`), retry: false });
  const changeFilters = (next: WorkspaceFilters) => { setFilters(next); setPageState(1);persist(next,1); };
  const changeSort = (key: string) => { const next=nextWorkspaceSort(sort,key);setSort(next); };
  return <Box className="workspace-page"><Container maxWidth="xl"><Stack spacing={2.5}>
    <ScreenHeader title="מרכז העבודה" subtitle="הקריאות, המסננים והפעולות החשובות במקום אחד" action={<Button component={Link} to="/cases/new" variant="contained" size="large" startIcon={<Add/>}>פתיחת קריאה חדשה</Button>}/>
    <Paper className="workspace-tabs" variant="outlined"><Tabs value={view} onChange={(_, value) => { setSearchParams({ tab: value }); setPage(1); }}><Tab value="my" label="הקריאות שלי"/>{(view === 'assigned' || query.data?.can_view_assigned_cases) && <Tab value="assigned" label="קריאות בטיפולי" disabled={query.data?.can_view_assigned_cases === false}/>}</Tabs></Paper>
    <Stack direction="row" gap={1} flexWrap="wrap">{[['','הכול'],['unassigned','לא משויכות'],['waiting_agent','ממתינות לטיפול'],['waiting_requester','ממתינות למשתמש'],['recent','עודכנו לאחרונה'],['sla_warning','בסיכון SLA'],['sla_breached','בחריגה מ־SLA']].map(([value,label])=><Chip key={value} clickable color={queue===value?'primary':'default'} label={label} onClick={()=>{const next=new URLSearchParams(searchParams);if(value)next.set('queue',value);else next.delete('queue');setSearchParams(next);setPage(1)}}/>)}</Stack>
    <SavedViewsBar filters={filters} sort={sort} pageSize={pageSize} visibleColumns={visibleColumns} onColumnsChange={setVisibleColumns} onApply={(saved:SavedView)=>{setFilters({...initial,...saved.filters});setSort(saved.sort);setPageSize(saved.page_size);setVisibleColumns(saved.visible_columns);setPage(1)}}/>
    <CaseFilters value={filters} environments={environments} fields={filterable} onChange={changeFilters} onReset={() => changeFilters({ ...initial })}/>
    {query.error && <Alert severity="error">{(query.error as Error).message}</Alert>}
    {query.isLoading ? <Box textAlign="center" py={7}><CircularProgress/></Box> : <DashboardCaseList items={query.data?.items || []} sort={sort} onSort={changeSort} visibleColumns={visibleColumns} selectedIds={selectedIds} onToggle={id=>setSelectedIds(current=>current.includes(id)?current.filter(value=>value!==id):[...current,id])} onPreview={setPreviewId}/>}<BulkActionBar selectedIds={selectedIds} onClear={()=>setSelectedIds([])}/><CaseQuickPreview caseId={previewId} onClose={()=>setPreviewId(undefined)}/>
    <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems="center" gap={2}>
      <Typography color="text.secondary">{query.data?.total || 0} קריאות</Typography>
      <Pagination page={page} count={Math.max(1, Math.ceil((query.data?.total || 0) / pageSize))} onChange={(_, value) => setPage(value)} color="primary"/>
      <TextField select size="small" label="שורות בעמוד" value={pageSize} onChange={(event) => { setPageSize(Number(event.target.value)); setPage(1); }} sx={{ minWidth: 130 }}>{[10, 25, 50, 100].map((size) => <MenuItem key={size} value={size}>{size}</MenuItem>)}</TextField>
    </Stack>
  </Stack></Container></Box>;
}
