import { ArrowDownward, ArrowUpward, FilterAlt } from '@mui/icons-material';
import { Card, CardContent, IconButton, InputAdornment, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, Tooltip, Typography } from '@mui/material';
import type { CaseReportRow } from '../../../types';
import { statusLabel } from '../../../status';
import type { ReportFilters } from './reportFilters';
import { reportColumns } from './reportColumns';

const filterable = new Set<keyof CaseReportRow>(['case_number', 'title', 'description', 'priority']);
const sortable = new Set<keyof CaseReportRow>(['case_number', 'environment', 'request_type', 'title', 'status', 'priority', 'requester', 'created_at', 'updated_at']);
const display = (key: keyof CaseReportRow, value: string) => key === 'status' ? statusLabel(value) : key.endsWith('_at') ? new Date(value).toLocaleString('he-IL') : value;

export function CaseReportTable({ rows, visible, filters, onFilters }: { rows: CaseReportRow[]; visible: (keyof CaseReportRow)[]; filters: ReportFilters; onFilters: (value: ReportFilters) => void }) {
  const columns = reportColumns.filter(([key]) => visible.includes(key));
  const sort = (key: keyof CaseReportRow) => sortable.has(key) && onFilters({ ...filters, sort: key, direction: filters.sort === key && filters.direction === 'asc' ? 'desc' : 'asc' });
  return <><TableContainer component={Paper} variant="outlined" sx={{ display: { xs: 'none', md: 'block' } }}><Table size="small"><TableHead><TableRow>{columns.map(([key, label]) => <TableCell key={key} sx={{ verticalAlign: 'top', minWidth: 145 }}>
    <Typography fontWeight={800}>{label}{sortable.has(key) && <Tooltip title="מיון עולה או יורד"><IconButton size="small" onClick={() => sort(key)}>{filters.sort === key && filters.direction === 'asc' ? <ArrowUpward fontSize="inherit"/> : <ArrowDownward fontSize="inherit"/>}</IconButton></Tooltip>}</Typography>
    {filterable.has(key) &&
      <TextField size="small" placeholder={`סינון ${label}`} value={filters[key] || ''} onChange={(event) => onFilters({ ...filters, [key]: event.target.value })} slotProps={{ input: { startAdornment: <InputAdornment position="start"><FilterAlt fontSize="small"/></InputAdornment> } }}/>
    }
  </TableCell>)}</TableRow></TableHead><TableBody>{rows.map((row) => <TableRow hover key={row.case_number}>{columns.map(([key]) => <TableCell key={key}>{display(key, row[key])}</TableCell>)}</TableRow>)}</TableBody></Table></TableContainer>
  <div className="mobile-report-cards">{rows.map((row) => <Card key={row.case_number} variant="outlined"><CardContent><Typography fontWeight={700}>{row.case_number} · {row.title}</Typography><Typography variant="body2">{row.environment} · {row.request_type}</Typography><Typography variant="body2">{statusLabel(row.status)} · {row.priority}</Typography><Typography variant="body2">מטפל: {row.assignee}</Typography></CardContent></Card>)}</div></>;
}
