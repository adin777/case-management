import { Container, Pagination, Stack, Typography } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { api } from '../../../api/client';
import type { CaseReportRow, Environment, RequestType } from '../../../types';
import { CaseReportFilters, type ReportFilters } from './CaseReportFilters';
import { CaseReportTable } from './CaseReportTable';
import { ColumnSelector } from './ColumnSelector';
import { ExportExcelButton } from './ExportExcelButton';
import { reportColumns } from './reportColumns';

const initialColumns = (): (keyof CaseReportRow)[] => {
  try { return JSON.parse(localStorage.getItem('case-report-columns') || 'null') || reportColumns.map(([key]) => key); }
  catch { return reportColumns.map(([key]) => key); }
};

export function CaseReportPage() {
  const [filters, setFilters] = useState<ReportFilters>({ environment_id: '', request_type_id: '', status: '', search: '', sort: 'created_at', direction: 'desc' });
  const [page, setPage] = useState(1);
  const [columns, setColumns] = useState(initialColumns);
  const { data: environments = [] } = useQuery({ queryKey: ['environments'], queryFn: () => api<Environment[]>('/environments') });
  const { data: types = [] } = useQuery({ queryKey: ['request-types-report', filters.environment_id], queryFn: () => api<RequestType[]>(`/request-types?environment_id=${filters.environment_id}`), enabled: Boolean(filters.environment_id) });
  const query = new URLSearchParams([
    ...Object.entries(filters).filter(([, value]) => value),
    ['page', String(page)],
  ]);
  const { data } = useQuery({ queryKey: ['case-report', filters, page], queryFn: () => api<{ items: CaseReportRow[]; total: number; page_size: number }>(`/reports/cases?${query}`) });
  const changeColumns = (value: (keyof CaseReportRow)[]) => { setColumns(value); localStorage.setItem('case-report-columns', JSON.stringify(value)); };
  return <Container maxWidth="xl"><Stack spacing={2}><Typography variant="h4" fontWeight={800}>דוח קריאות שירות</Typography><CaseReportFilters value={filters} onChange={(value) => { setFilters(value); setPage(1); }} environments={environments} types={types}/><Stack direction="row" gap={1}><ExportExcelButton filters={filters}/><ColumnSelector value={columns} onChange={changeColumns}/></Stack><CaseReportTable rows={data?.items || []} visible={columns}/><Pagination count={Math.max(1, Math.ceil((data?.total || 0) / (data?.page_size || 25)))} page={page} onChange={(_, value) => setPage(value)}/></Stack></Container>;
}
