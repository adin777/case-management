import { Card, CardActionArea, CardContent, Chip, Paper, Stack, Table, TableBody, TableCell, TableHead, TableRow, Typography } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import type { WorkspaceCase } from './types';
import {useTranslation} from 'react-i18next';

export function DashboardCaseList({ items }: { items: WorkspaceCase[] }) {
  const {t,i18n}=useTranslation();const locale=i18n.language==='en'?'en-US':'he-IL';
  const navigate = useNavigate();
  if (!items.length) return <Paper variant="outlined" sx={{ p: 6, textAlign: 'center' }}><Typography fontWeight={700}>{t('dashboard.empty')}</Typography><Typography color="text.secondary">{t('dashboard.emptyHelp')}</Typography></Paper>;
  return <><Paper variant="outlined" sx={{ display: { xs: 'none', md: 'block' }, overflowX: 'auto' }}><Table><TableHead><TableRow>{[t('dashboard.caseNumber'),t('cases.subject'),t('cases.environment'),t('cases.requestType'),t('dashboard.status'),t('dashboard.priority'),t('dashboard.created'),t('dashboard.updated')].map((label) => <TableCell key={label}>{label}</TableCell>)}</TableRow></TableHead><TableBody>{items.map((item) => <TableRow hover key={item.id} onClick={() => navigate(`/cases/${item.id}`)} sx={{ cursor: 'pointer' }}><TableCell>{item.case_number}</TableCell><TableCell>{item.title}</TableCell><TableCell>{item.environment}</TableCell><TableCell>{item.request_type}</TableCell><TableCell><Chip size="small" label={item.status}/></TableCell><TableCell>{item.priority}</TableCell><TableCell>{new Date(item.created_at).toLocaleDateString(locale)}</TableCell><TableCell>{new Date(item.updated_at).toLocaleString(locale)}</TableCell></TableRow>)}</TableBody></Table></Paper>
  <Stack spacing={1.5} sx={{ display: { md: 'none' } }}>{items.map((item) => <Card variant="outlined" key={item.id}><CardActionArea onClick={() => navigate(`/cases/${item.id}`)}><CardContent><Typography color="primary" fontWeight={800}>{item.case_number}</Typography><Typography variant="h6">{item.title}</Typography><Stack direction="row" gap={1} mt={1} flexWrap="wrap"><Chip size="small" label={item.status}/><Chip size="small" variant="outlined" label={item.environment}/></Stack><Typography variant="caption" color="text.secondary">{t('dashboard.updated')}: {new Date(item.updated_at).toLocaleString(locale)}</Typography></CardContent></CardActionArea></Card>)}</Stack></>;
}
