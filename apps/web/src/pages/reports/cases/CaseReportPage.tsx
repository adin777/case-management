import { Alert, Button, CircularProgress, Container, Pagination, Paper, Stack, Typography } from '@mui/material';
import { PlayArrow } from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { api } from '../../../api/client';
import type { CaseReportRow, Environment, RequestType, User } from '../../../types';
import { emptyFilters, type ReportFilters } from './reportFilters';
import { CaseReportTable } from './CaseReportTable';
import { CaseReportFilters } from './CaseReportFilters';
import { ColumnSelector } from './ColumnSelector';
import { ExportExcelButton } from './ExportExcelButton';
import { reportColumns } from './reportColumns';

const initialColumns = (): (keyof CaseReportRow)[] => {
  try { return JSON.parse(localStorage.getItem('case-report-columns') || 'null') || reportColumns.map(([key]) => key); }
  catch { return reportColumns.map(([key]) => key); }
};

export function CaseReportPage() {
  const [filters, setFilters] = useState<ReportFilters>({ ...emptyFilters });
  const [applied, setApplied] = useState<ReportFilters | null>(null);
  const [page, setPage] = useState(1);
  const [columns, setColumns] = useState(initialColumns);
  const { data: environments = [] } = useQuery({ queryKey: ['environments'], queryFn: () => api<Environment[]>('/environments') });
  const { data: types = [] } = useQuery({ queryKey: ['request-types', filters.environment_id], queryFn: () => api<RequestType[]>(`/request-types${filters.environment_id ? `?environment_id=${filters.environment_id}` : ''}`) });
  const { data: users = [] } = useQuery({ queryKey: ['users'], queryFn: () => api<User[]>('/users'), retry: false });
  const { data: sources = { statuses: [], priorities: [] } } = useQuery({ queryKey: ['report-value-sources', filters.environment_id], queryFn: () => api<{ statuses: { id: string; label_he: string; environment: string }[]; priorities: { id: string; label_he: string }[] }>(`/reports/cases/value-sources${filters.environment_id ? `?environment_id=${filters.environment_id}` : ''}`) });
  const query = new URLSearchParams([...(applied ? Object.entries(applied).filter(([, value]) => value) : []), ['page', String(page)]]);
  const report = useQuery({ queryKey: ['case-report', applied, page], queryFn: () => api<{ items: CaseReportRow[]; total: number; page_size: number }>(`/reports/cases?${query}`), enabled: applied !== null });
  const changeColumns = (value: (keyof CaseReportRow)[]) => { setColumns(value); localStorage.setItem('case-report-columns', JSON.stringify(value)); };
  const run = () => { setPage(1); setApplied({ ...filters }); };
  const clear = () => { setFilters({ ...emptyFilters }); setApplied(null); setPage(1); };
  return <Container maxWidth="xl"><Stack spacing={2.5}>
    <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" gap={2}><div><Typography variant="h4">דוח קריאות שירות</Typography><Typography color="text.secondary">בחרו מסננים והריצו את הדוח לקבלת תמונת מצב עדכנית</Typography></div><Stack direction="row" gap={1} alignItems="center"><ColumnSelector value={columns} onChange={changeColumns}/>{applied && <ExportExcelButton filters={applied}/>}</Stack></Stack>
    <CaseReportFilters value={filters} onChange={setFilters} environments={environments} types={types} users={users} statuses={sources.statuses}/>
    <Stack direction="row" gap={1}><Button variant="contained" size="large" startIcon={<PlayArrow/>} onClick={run}>הרצת דוח</Button><Button onClick={clear}>ניקוי מסננים</Button></Stack>
    {!applied ? <Paper variant="outlined" sx={{ p: 7, textAlign: 'center' }}><Typography variant="h6">הדוח מוכן להרצה</Typography><Typography color="text.secondary">התוצאות ייטענו רק לאחר לחיצה על “הרצת דוח”</Typography></Paper>
      : report.isLoading ? <Stack alignItems="center" py={7}><CircularProgress/><Typography mt={2}>טוען תוצאות…</Typography></Stack>
      : report.isError ? <Alert severity="error">לא ניתן להריץ את הדוח: {(report.error as Error).message}</Alert>
      : !report.data?.items.length ? <Paper variant="outlined" sx={{ p: 7, textAlign: 'center' }}><Typography variant="h6">לא נמצאו תוצאות</Typography><Typography color="text.secondary">נסו לשנות את המסננים ולהריץ שוב</Typography></Paper>
      : <><Typography fontWeight={700}>{report.data.total} תוצאות</Typography><CaseReportTable rows={report.data.items} visible={columns} filters={applied} onFilters={(next) => { setFilters(next); setApplied(next); setPage(1); }} sources={sources}/><Pagination count={Math.max(1, Math.ceil(report.data.total / report.data.page_size))} page={page} onChange={(_, value) => setPage(value)}/></>}
  </Stack></Container>;
}
