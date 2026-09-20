import { Download } from '@mui/icons-material';
import { Box, Button, Card, CardContent, Chip, Container, MenuItem, Pagination, Paper, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api, apiDownload } from '../../api/client';
import { ScreenHeader } from '../../components/ScreenHeader';
import { displayCaseNumber } from '../cases/details/caseDisplay';

type Option={id:string;label:string;environment_id?:string};
type Options={environments:Option[];request_types:Option[];priorities:Option[];assignees:Option[];policies:Option[]};
type Row={case_id:string;case_number:string;subject:string;environment:string;policy:string;response_target_minutes:number;response_result:string;resolution_target_minutes:number;resolution_result:string;paused_seconds:number};
type Metrics={compliance_percent:number;response_compliance_percent:number;resolution_compliance_percent:number;breached:number;at_risk:number;average_first_response_seconds:number;average_resolution_seconds:number;average_paused_seconds:number};
type Filters={created_from:string;created_to:string;environment_id:string;request_type_id:string;priority_option_id:string;assignee_id:string;state:string;policy_id:string};
const empty:Filters={created_from:'',created_to:'',environment_id:'',request_type_id:'',priority_option_id:'',assignee_id:'',state:'',policy_id:''};
const resultLabel:Record<string,string>={running:'פעיל',warning:'בסיכון',breached:'בחריגה',met:'עמד ביעד',paused:'מושהה',cancelled:'בוטל'};
const queryString=(filters:Filters,page?:number)=>{const params=new URLSearchParams();Object.entries(filters).forEach(([key,value])=>{if(value)params.set(key,value)});if(page){params.set('page',String(page));params.set('page_size','25')}return params.toString()};
const minutes=(seconds:number)=>`${Math.round(seconds/60)} דק׳`;

export function SlaReportPage(){
  const[search,setSearch]=useSearchParams();const restored={...empty,...Object.fromEntries(Object.keys(empty).map(key=>[key,search.get(key)||'']))} as Filters;const[filters,setFilters]=useState(restored);const[page,setPageState]=useState(Number(search.get('page')||1));const persist=(values:Filters,nextPage:number)=>{const next=new URLSearchParams(queryString(values,nextPage));next.set('run','1');setSearch(next)};const setPage=(value:number)=>{setPageState(value);persist(filters,value)};const params=queryString(filters,page);const metricParams=queryString(filters);
  const options=useQuery({queryKey:['sla-report-options'],queryFn:()=>api<Options>('/reports/sla/options')});
  const report=useQuery({queryKey:['sla-report',params],queryFn:()=>api<{items:Row[];total:number}>(`/reports/sla?${params}`)});
  const metrics=useQuery({queryKey:['sla-metrics',metricParams],queryFn:()=>api<Metrics>(`/reports/sla/metrics?${metricParams}`)});
  const set=(key:keyof Filters,value:string)=>{const next={...filters,[key]:value,...(key==='environment_id'?{request_type_id:'',policy_id:''}:{})};setFilters(next);setPageState(1);persist(next,1)};
  const download=async()=>{const blob=await apiDownload(`/reports/sla/export?${metricParams}`);const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download='sla-report.xlsx';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
  const scoped=(values:Option[])=>values.filter(item=>!filters.environment_id||!item.environment_id||item.environment_id===filters.environment_id);
  return <Container maxWidth="xl"><Stack spacing={2.5}>
    <ScreenHeader title="דוח SLA" subtitle="עמידה ביעדי תגובה ופתרון, סיכונים וחריגות" action={<Button variant="contained" startIcon={<Download/>} onClick={download}>ייצוא ל־Excel</Button>}/>
    <Box sx={{display:'grid',gridTemplateColumns:{xs:'1fr 1fr',lg:'repeat(8,1fr)'},gap:2}}>{[['עמידה כוללת',`${metrics.data?.compliance_percent||0}%`],['עמידה בתגובה',`${metrics.data?.response_compliance_percent||0}%`],['עמידה בפתרון',`${metrics.data?.resolution_compliance_percent||0}%`],['בחריגה',metrics.data?.breached||0],['בסיכון',metrics.data?.at_risk||0],['תגובה ממוצעת',minutes(metrics.data?.average_first_response_seconds||0)],['פתרון ממוצע',minutes(metrics.data?.average_resolution_seconds||0)],['השהיה ממוצעת',minutes(metrics.data?.average_paused_seconds||0)]].map(([label,value])=><Card key={label}><CardContent><Typography color="text.secondary" variant="body2">{label}</Typography><Typography variant="h5">{value}</Typography></CardContent></Card>)}</Box>
    <Paper variant="outlined" sx={{p:2}}><Box sx={{display:'grid',gridTemplateColumns:{xs:'1fr',sm:'repeat(2,1fr)',lg:'repeat(4,1fr)'},gap:2}}>
      <TextField type="date" label="תאריך פתיחה מ־" value={filters.created_from} onChange={event=>set('created_from',event.target.value)} slotProps={{inputLabel:{shrink:true}}}/><TextField type="date" label="תאריך פתיחה עד־" value={filters.created_to} onChange={event=>set('created_to',event.target.value)} slotProps={{inputLabel:{shrink:true}}}/>
      <TextField select label="סביבה" value={filters.environment_id} onChange={event=>set('environment_id',event.target.value)}><MenuItem value="">כל הסביבות</MenuItem>{options.data?.environments.map(item=><MenuItem key={item.id} value={item.id}>{item.label}</MenuItem>)}</TextField>
      <TextField select label="סוג קריאה" value={filters.request_type_id} onChange={event=>set('request_type_id',event.target.value)}><MenuItem value="">כל הסוגים</MenuItem>{scoped(options.data?.request_types||[]).map(item=><MenuItem key={item.id} value={item.id}>{item.label}</MenuItem>)}</TextField>
      <TextField select label="עדיפות" value={filters.priority_option_id} onChange={event=>set('priority_option_id',event.target.value)}><MenuItem value="">כל העדיפויות</MenuItem>{options.data?.priorities.map(item=><MenuItem key={item.id} value={item.id}>{item.label}</MenuItem>)}</TextField>
      <TextField select label="מטפל" value={filters.assignee_id} onChange={event=>set('assignee_id',event.target.value)}><MenuItem value="">כל המטפלים</MenuItem>{options.data?.assignees.map(item=><MenuItem key={item.id} value={item.id}>{item.label}</MenuItem>)}</TextField>
      <TextField select label="מצב SLA" value={filters.state} onChange={event=>set('state',event.target.value)}><MenuItem value="">כל המצבים</MenuItem>{Object.entries(resultLabel).map(([value,label])=><MenuItem key={value} value={value}>{label}</MenuItem>)}</TextField>
      <TextField select label="מדיניות" value={filters.policy_id} onChange={event=>set('policy_id',event.target.value)}><MenuItem value="">כל המדיניות</MenuItem>{scoped(options.data?.policies||[]).map(item=><MenuItem key={item.id} value={item.id}>{item.label}</MenuItem>)}</TextField>
    </Box><Button sx={{mt:2}} onClick={()=>{setFilters(empty);setPage(1)}}>איפוס מסננים</Button></Paper>
    <Paper variant="outlined" sx={{display:{xs:'none',md:'block'},overflowX:'auto'}}><Table><TableHead><TableRow>{['מספר','נושא','סביבה','מדיניות','יעד תגובה','תוצאת תגובה','יעד פתרון','תוצאת פתרון','זמן השהיה'].map(label=><TableCell key={label}>{label}</TableCell>)}</TableRow></TableHead><TableBody>{report.data?.items.map(item=><TableRow key={item.case_id}><TableCell>{displayCaseNumber(item.case_number)}</TableCell><TableCell>{item.subject}</TableCell><TableCell>{item.environment}</TableCell><TableCell>{item.policy}</TableCell><TableCell>{item.response_target_minutes} דק׳</TableCell><TableCell><Chip label={resultLabel[item.response_result]||item.response_result}/></TableCell><TableCell>{item.resolution_target_minutes} דק׳</TableCell><TableCell><Chip label={resultLabel[item.resolution_result]||item.resolution_result}/></TableCell><TableCell>{minutes(item.paused_seconds)}</TableCell></TableRow>)}</TableBody></Table></Paper>
    <Stack spacing={1} sx={{display:{md:'none'}}}>{report.data?.items.map(item=><Card key={item.case_id}><CardContent><Typography color="primary" fontWeight={650}>{displayCaseNumber(item.case_number)}</Typography><Typography variant="h6">{item.subject}</Typography><Typography>{item.environment} · {item.policy}</Typography><Stack direction="row" gap={1} mt={1} flexWrap="wrap"><Chip label={`תגובה: ${resultLabel[item.response_result]||item.response_result}`}/><Chip label={`פתרון: ${resultLabel[item.resolution_result]||item.resolution_result}`}/></Stack></CardContent></Card>)}</Stack>
    <Pagination page={page} count={Math.max(1,Math.ceil((report.data?.total||0)/25))} onChange={(_,value)=>setPage(value)}/>
  </Stack></Container>;
}
