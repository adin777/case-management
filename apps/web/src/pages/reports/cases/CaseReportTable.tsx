import { Card, CardContent, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from '@mui/material';
import type { CaseReportRow } from '../../../types';
import { reportColumns } from './reportColumns';

export function CaseReportTable({ rows, visible }: { rows: CaseReportRow[]; visible: (keyof CaseReportRow)[] }) {
  const columns = reportColumns.filter(([key]) => visible.includes(key));
  return <><TableContainer component={Paper} variant="outlined" sx={{ display: { xs: 'none', md: 'block' } }}><Table><TableHead><TableRow>{columns.map(([, label]) => <TableCell key={label}>{label}</TableCell>)}</TableRow></TableHead><TableBody>{rows.map((row) => <TableRow key={row.case_number}>{columns.map(([key]) => <TableCell key={key}>{row[key]}</TableCell>)}</TableRow>)}</TableBody></Table></TableContainer><div className="mobile-report-cards">{rows.map((row) => <Card key={row.case_number} variant="outlined"><CardContent><Typography fontWeight={700}>{row.case_number} · {row.title}</Typography><Typography variant="body2">{row.environment} · {row.request_type}</Typography><Typography variant="body2">{row.status} · {row.priority}</Typography></CardContent></Card>)}</div></>;
}
