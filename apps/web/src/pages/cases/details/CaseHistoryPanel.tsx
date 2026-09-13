import { History } from '@mui/icons-material';
import { Box, Button, Chip, Pagination, Stack, ToggleButton, ToggleButtonGroup, Typography } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { api } from '../../../api/client';
import { CaseSection } from './CaseSection';

type Row={id:string;changed_at:string;changed_by_name_snapshot?:string;field_label_snapshot:string;old_display_value?:string;new_display_value?:string;source:string;real_actor_id?:string;effective_user_id?:string};
type Result={items:Row[];total:number;page:number;page_size:number};
export function CaseHistoryPanel({caseId}:{caseId:string}){
  const[kind,setKind]=useState('all');const[page,setPage]=useState(1);const[open,setOpen]=useState(false);
  const query=useQuery({queryKey:['case-history',caseId,kind,page],queryFn:()=>api<Result>(`/cases/${caseId}/history?kind=${kind}&page=${page}&page_size=20`),enabled:open});
  return <CaseSection title="היסטוריה" icon={<History/>}><Stack spacing={2}>{!open?<Button onClick={()=>setOpen(true)}>הצגת היסטוריה</Button>:<><ToggleButtonGroup exclusive size="small" value={kind} onChange={(_,value)=>{if(value){setKind(value);setPage(1)}}}><ToggleButton value="all">כל השינויים</ToggleButton><ToggleButton value="fields">שדות בלבד</ToggleButton><ToggleButton value="system">מערכת</ToggleButton></ToggleButtonGroup>{query.data?.items.map(row=><Box key={row.id} sx={{borderInlineStart:'3px solid',borderColor:'primary.main',ps:2,py:1}}><Stack direction="row" gap={1} alignItems="center" flexWrap="wrap"><Typography fontWeight={800}>{new Date(row.changed_at).toLocaleString('he-IL')} · {row.changed_by_name_snapshot||'מערכת'}</Typography><Chip size="small" label={row.source}/></Stack><Typography>{row.field_label_snapshot}</Typography><Typography color="text.secondary">{row.old_display_value||'ללא'} ← {row.new_display_value||'ללא'}</Typography></Box>)}{query.data&&query.data.total>20&&<Pagination page={page} count={Math.ceil(query.data.total/20)} onChange={(_,value)=>setPage(value)}/>}</>}</Stack></CaseSection>;
}
