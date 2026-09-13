import { MoreHoriz } from '@mui/icons-material';
import { Card, CardActionArea, CardContent, IconButton, Menu, MenuItem, Paper, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TableSortLabel, Typography } from '@mui/material';
import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { BusinessPill } from '../../../components/BusinessPill';
import { displayCaseNumber } from '../../cases/details/caseDisplay';
import type { CaseReportRow } from '../../../types';
import type { ReportFilters } from './reportFilters';
import { reportColumns } from './reportColumns';
import { openCase } from '../../../navigation/caseNavigation';

const sortable = new Set<keyof CaseReportRow>(['case_number','environment','request_type','title','status','priority','requester','assignee','created_at','updated_at']);
export function CaseReportTable({ rows, visible, filters, onFilters }: { rows: CaseReportRow[]; visible: (keyof CaseReportRow)[]; filters: ReportFilters; onFilters: (value: ReportFilters) => void; sources: unknown }) {
  const {t,i18n}=useTranslation();const navigate=useNavigate();const location=useLocation();const[menu,setMenu]=useState<{anchor:HTMLElement;id:string}>();
  const columns=reportColumns.filter(([key])=>visible.includes(key)&&key!=='description');
  const label=(key:keyof CaseReportRow,fallback:string)=>t(`reports.columns.${key}`,{defaultValue:fallback});
  const display=(key:keyof CaseReportRow,value:string)=>key==='case_number'?displayCaseNumber(value):key.endsWith('_at')?new Date(value).toLocaleString(i18n.language==='en'?'en-US':'he-IL'):value;
  const sort=(key:keyof CaseReportRow)=>onFilters({...filters,sort:key,direction:filters.sort===key&&filters.direction==='asc'?'desc':'asc'});
  const open=(id:string)=>openCase(navigate,location,id,'חזרה לדוח');
  return <><TableContainer className="data-table" component={Paper} variant="outlined" sx={{display:{xs:'none',md:'block'}}}><Table><TableHead><TableRow>{columns.map(([key,fallback])=><TableCell key={key}>{sortable.has(key)?<TableSortLabel active={filters.sort===key} direction={filters.sort===key&&filters.direction==='asc'?'asc':'desc'} onClick={()=>sort(key)}>{label(key,fallback)}</TableSortLabel>:label(key,fallback)}</TableCell>)}<TableCell>פעולות</TableCell></TableRow></TableHead><TableBody>{rows.map(row=><TableRow hover key={row.case_number}>{columns.map(([key])=><TableCell key={key}>{key==='status'?<BusinessPill label={row[key]}/>:key==='priority'?<BusinessPill label={row[key]} kind="priority"/>:key==='case_number'?<Typography color="primary" fontWeight={850}>{display(key,row[key])}</Typography>:display(key,row[key])}</TableCell>)}<TableCell><IconButton aria-label="פעולות" onClick={event=>setMenu({anchor:event.currentTarget,id:row.id})}><MoreHoriz/></IconButton></TableCell></TableRow>)}</TableBody></Table></TableContainer><Menu anchorEl={menu?.anchor} open={Boolean(menu)} onClose={()=>setMenu(undefined)}><MenuItem onClick={()=>{if(menu)open(menu.id)}}>פתיחת הקריאה</MenuItem></Menu><div className="mobile-report-cards">{rows.map(row=><Card key={row.case_number} variant="outlined"><CardActionArea onClick={()=>open(row.id)} aria-label={`פתיחת קריאה ${displayCaseNumber(row.case_number)}`}><CardContent><Typography color="primary" fontWeight={850}>{displayCaseNumber(row.case_number)}</Typography><Typography variant="h6">{row.title}</Typography><Stack direction="row" gap={1} my={1}><BusinessPill label={row.status}/><BusinessPill label={row.priority} kind="priority"/></Stack><Typography variant="body2">{row.environment} · {row.request_type}</Typography><Typography variant="body2">{t('reports.assignee')}: {row.assignee}</Typography></CardContent></CardActionArea></Card>)}</div></>;
}
