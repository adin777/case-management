import { Button, Container, Pagination, Stack, Typography } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { api } from '../../../api/client';
import type { CaseReportRow } from '../../../types';
import { emptyFilters, type ReportFilters } from './reportFilters';
import { CaseReportTable } from './CaseReportTable';
import { ColumnSelector } from './ColumnSelector';
import { ExportExcelButton } from './ExportExcelButton';
import { reportColumns } from './reportColumns';

const initialColumns = (): (keyof CaseReportRow)[] => {
  try { return JSON.parse(localStorage.getItem('case-report-columns') || 'null') || reportColumns.map(([key]) => key); }
  catch { return reportColumns.map(([key]) => key); }
};

export function CaseReportPage() {
  const [filters, setFilters] = useState<ReportFilters>(() => { try { return { ...emptyFilters, ...JSON.parse(localStorage.getItem('case-report-filters') || '{}') }; } catch { return emptyFilters; } });
  const [page, setPage] = useState(1);
  const [columns, setColumns] = useState(initialColumns);
  const { data: sources = { statuses: [], priorities: [] } } = useQuery({ queryKey: ['report-value-sources', filters.environment_id], queryFn: () => api<{ statuses: { id: string; label_he: string; environment: string }[]; priorities: { id: string; label_he: string }[] }>(`/reports/cases/value-sources${filters.environment_id ? `?environment_id=${filters.environment_id}` : ''}`) });
  const query = new URLSearchParams([
    ...Object.entries(filters).filter(([, value]) => value),
    ['page', String(page)],
  ]);
  const { data } = useQuery({ queryKey: ['case-report', filters, page], queryFn: () => api<{ items: CaseReportRow[]; total: number; page_size: number }>(`/reports/cases?${query}`) });
  const changeColumns = (value: (keyof CaseReportRow)[]) => { setColumns(value); localStorage.setItem('case-report-columns', JSON.stringify(value)); };
  const changeFilters = (value: ReportFilters) => { setFilters(value); setPage(1); localStorage.setItem('case-report-filters', JSON.stringify(value)); };
  return <Container maxWidth="xl"><Stack spacing={2}><Typography variant="h4" fontWeight={800}>דוח קריאות שירות</Typography><Stack direction="row" gap={1} alignItems="center" flexWrap="wrap"><ExportExcelButton filters={filters}/><ColumnSelector value={columns} onChange={changeColumns}/><Button onClick={() => changeFilters(emptyFilters)}>ניקוי כל המסננים</Button><Typography>{data?.total || 0} תוצאות</Typography></Stack><CaseReportTable rows={data?.items || []} visible={columns} filters={filters} onFilters={changeFilters} sources={sources}/><Pagination count={Math.max(1, Math.ceil((data?.total || 0) / (data?.page_size || 25)))} page={page} onChange={(_, value) => setPage(value)}/></Stack></Container>;
}
