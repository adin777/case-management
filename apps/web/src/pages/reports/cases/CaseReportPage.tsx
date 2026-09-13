import { ArrowForward, PlayArrow } from '@mui/icons-material';
import { Alert, Box, Button, Chip, CircularProgress, Container, MenuItem, Pagination, Paper, Stack, TextField, Typography } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../../../api/client';
import { ScreenHeader } from '../../../components/ScreenHeader';
import type { CaseReportRow, Environment, RequestType, User } from '../../../types';
import { emptyFilters, type ReportFilters } from './reportFilters';
import { CaseReportTable } from './CaseReportTable';
import { CaseReportFilters } from './CaseReportFilters';
import { ExportExcelButton } from './ExportExcelButton';
import { readReportState, writeReportState } from '../reportUrlState';

const visible: (keyof CaseReportRow)[] = ['case_number', 'title', 'environment', 'request_type', 'status', 'priority', 'requester', 'assignee', 'created_at', 'updated_at'];
export function CaseReportPage() {
  const [search,setSearch]=useSearchParams();const restored=readReportState(search);const restoredFilters={...emptyFilters,...restored.filters} as ReportFilters;
  const [filters, setFilters] = useState<ReportFilters>(restoredFilters); const [applied, setApplied] = useState<ReportFilters | null>(restored.run?restoredFilters:null); const [page, setPageState] = useState(restored.page); const [pageSize, setPageSizeState] = useState(restored.pageSize);
  const sizeRef=useRef(pageSize);const persist=(value:ReportFilters,nextPage=page,nextSize=sizeRef.current)=>setSearch(writeReportState(value,nextPage,nextSize,value.sort,value.direction,visible));const setPage=(value:number)=>{setPageState(value);if(applied)persist(applied,value)};const setPageSize=(value:number)=>{sizeRef.current=value;setPageSizeState(value);setPageState(1);if(applied)persist(applied,1,value)};
  const { data: environments = [] } = useQuery({ queryKey: ['environments'], queryFn: () => api<Environment[]>('/environments') });
  const { data: types = [] } = useQuery({ queryKey: ['request-types', filters.environment_id], queryFn: () => api<RequestType[]>(`/request-types${filters.environment_id ? `?environment_id=${filters.environment_id}` : ''}`) });
  const { data: users = [] } = useQuery({ queryKey: ['users'], queryFn: () => api<User[]>('/users'), retry: false });
  const { data: sources = { statuses: [], priorities: [] } } = useQuery({ queryKey: ['report-value-sources', filters.environment_id], queryFn: () => api<{ statuses: { id: string; label_he: string; environment: string }[]; priorities: { id: string; label_he: string }[] }>(`/reports/cases/value-sources${filters.environment_id ? `?environment_id=${filters.environment_id}` : ''}`) });
  const query = new URLSearchParams([...(applied ? Object.entries(applied).filter(([, value]) => value) : []), ['page', String(page)], ['page_size', String(pageSize)]]);
  const report = useQuery({ queryKey: ['case-report', applied, page, pageSize], queryFn: () => api<{ items: CaseReportRow[]; total: number; page_size: number }>(`/reports/cases?${query}`), enabled: applied !== null });
  const run = () => { const next={...filters};setPageState(1);setApplied(next);persist(next,1); }; const clear = () => { setFilters({ ...emptyFilters }); setApplied(null); setPageState(1);setSearch({}); };
  return <Box className="reports-page"><Container maxWidth="xl"><Stack spacing={2.5}>
    <Button component={Link} to="/reports" startIcon={<ArrowForward/>} sx={{ alignSelf: 'flex-start' }}>חזרה לכל הדוחות</Button>
    <ScreenHeader title="דוח קריאות שירות" subtitle="חיפוש, ניתוח וייצוא קריאות בהתאם להרשאות שלך" action={applied ? <ExportExcelButton filters={applied}/> : undefined}/>
    <CaseReportFilters value={filters} onChange={setFilters} environments={environments} types={types} users={users} statuses={sources.statuses}/>
    <Stack direction="row" gap={1}><Button variant="contained" size="large" startIcon={<PlayArrow/>} onClick={run}>הרץ דוח</Button><Button onClick={clear}>ניקוי מסננים</Button></Stack>
    {!applied ? <Paper className="empty-state" variant="outlined"><Typography variant="h6">הדוח מוכן להרצה</Typography><Typography color="text.secondary">בחרו מסננים ולחצו על “הרץ דוח”</Typography></Paper>
      : report.isLoading ? <Stack alignItems="center" py={7}><CircularProgress/><Typography mt={2}>טוען נתונים…</Typography></Stack>
      : report.isError ? <Alert severity="error">טעינת הדוח נכשלה: {(report.error as Error).message}</Alert>
      : !report.data?.items.length ? <Paper className="empty-state" variant="outlined"><Typography variant="h6">לא נמצאו תוצאות</Typography><Typography color="text.secondary">נסו לשנות או לנקות את המסננים</Typography></Paper>
      : <><Chip color="primary" variant="outlined" label={`${report.data.total} תוצאות`} sx={{ alignSelf: 'flex-start' }}/><CaseReportTable rows={report.data.items} visible={visible} filters={applied} onFilters={(next) => { setFilters(next); setApplied(next); setPage(1); }} sources={sources}/><Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems="center" gap={2}><Typography color="text.secondary">עמוד {page}</Typography><Pagination count={Math.max(1, Math.ceil(report.data.total / report.data.page_size))} page={page} onChange={(_, value) => setPage(value)} color="primary"/><TextField select size="small" label="שורות בעמוד" value={pageSize} onChange={(event) => { setPageSize(Number(event.target.value)); setPage(1); }} sx={{ minWidth: 130 }}>{[10,25,50,100].map((size) => <MenuItem key={size} value={size}>{size}</MenuItem>)}</TextField></Stack></>}
  </Stack></Container></Box>;
}
