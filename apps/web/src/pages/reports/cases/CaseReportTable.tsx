import { ArrowDownward, ArrowUpward, FilterAlt } from '@mui/icons-material';
import { Card, CardContent, IconButton, InputAdornment, MenuItem, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, Tooltip, Typography } from '@mui/material';
import { useTranslation } from 'react-i18next';
import type { CaseReportRow } from '../../../types';
import { statusLabel } from '../../../status';
import type { ReportFilters } from './reportFilters';
import { reportColumns } from './reportColumns';

const filterable = new Set<keyof CaseReportRow>(['case_number','title','description']);
const sortable = new Set<keyof CaseReportRow>(['case_number','environment','request_type','title','status','priority','requester','assignee','created_at','updated_at']);
type Sources={statuses:{id:string;label_he:string;environment?:string}[];priorities:{id:string;label_he:string}[]};

export function CaseReportTable({rows,visible,filters,onFilters,sources}:{rows:CaseReportRow[];visible:(keyof CaseReportRow)[];filters:ReportFilters;onFilters:(value:ReportFilters)=>void;sources:Sources}){
  const {t,i18n}=useTranslation();
  const columns=reportColumns.filter(([key])=>visible.includes(key));
  const label=(key:keyof CaseReportRow,fallback:string)=>t(`reports.columns.${key}`,{defaultValue:fallback});
  const display=(key:keyof CaseReportRow,value:string)=>key==='status'?statusLabel(value):key.endsWith('_at')?new Date(value).toLocaleString(i18n.language==='en'?'en-US':'he-IL'):value;
  const sort=(key:keyof CaseReportRow)=>sortable.has(key)&&onFilters({...filters,sort:key,direction:filters.sort===key&&filters.direction==='asc'?'desc':'asc'});
  return <><TableContainer component={Paper} variant="outlined" sx={{display:{xs:'none',md:'block'}}}><Table size="small"><TableHead><TableRow>{columns.map(([key,fallback])=><TableCell key={key} sx={{verticalAlign:'top',minWidth:145}}>
    <Typography fontWeight={800}>{label(key,fallback)}{sortable.has(key)&&<Tooltip title={t('reports.sort')}><IconButton size="small" onClick={()=>sort(key)}>{filters.sort===key&&filters.direction==='asc'?<ArrowUpward fontSize="inherit"/>:<ArrowDownward fontSize="inherit"/>}</IconButton></Tooltip>}</Typography>
    {filterable.has(key)&&<TextField size="small" placeholder={t('reports.filter',{label:label(key,fallback)})} value={filters[key]||''} onChange={event=>onFilters({...filters,[key]:event.target.value})} slotProps={{input:{startAdornment:<InputAdornment position="start"><FilterAlt fontSize="small"/></InputAdornment>}}}/>}
    {key==='status'&&<TextField select size="small" fullWidth label={t('reports.filterStatus')} value={filters.workflow_status_id} onChange={event=>onFilters({...filters,workflow_status_id:event.target.value})}><MenuItem value="">{t('reports.all')}</MenuItem>{sources.statuses.map(item=><MenuItem key={item.id} value={item.id}>{item.label_he}{item.environment?` · ${item.environment}`:''}</MenuItem>)}</TextField>}
    {key==='priority'&&<TextField select size="small" fullWidth label={t('reports.filterPriority')} value={filters.priority_id} onChange={event=>onFilters({...filters,priority_id:event.target.value})}><MenuItem value="">{t('reports.all')}</MenuItem>{sources.priorities.map(item=><MenuItem key={item.id} value={item.id}>{item.label_he}</MenuItem>)}</TextField>}
  </TableCell>)}</TableRow></TableHead><TableBody>{rows.map(row=><TableRow hover key={row.case_number}>{columns.map(([key])=><TableCell key={key}>{display(key,row[key])}</TableCell>)}</TableRow>)}</TableBody></Table></TableContainer>
  <div className="mobile-report-cards">{rows.map(row=><Card key={row.case_number} variant="outlined"><CardContent><Typography fontWeight={700}>{row.case_number} · {row.title}</Typography><Typography variant="body2">{row.environment} · {row.request_type}</Typography><Typography variant="body2">{statusLabel(row.status)} · {row.priority}</Typography><Typography variant="body2">{t('reports.assignee')}: {row.assignee}</Typography></CardContent></Card>)}</div></>;
}
