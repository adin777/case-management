import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Alert, Button, MenuItem, Paper, Stack, TextField, Typography } from '@mui/material';
import { api } from '../../../../api/client';
import type { Environment } from '../../../../types';
type Rule={id:string;name:string;conditions:{field:string;value:string}[]};
type Preview={matched:number;users:{id:string;display_name:string;department?:string;job_title?:string}[]};
export function EnvironmentAssignmentRulesTab({environment}:{environment:Environment}){
  const client=useQueryClient(); const[name,setName]=useState(''); const[field,setField]=useState('department'); const[value,setValue]=useState(''); const[preview,setPreview]=useState<Preview>();
  const{data:rules=[]}=useQuery({queryKey:['assignment-rules',environment.id],queryFn:()=>api<Rule[]>(`/environments/${environment.id}/assignment-rules`)});
  const payload={name,conditions:[{field,value}],is_active:true};
  async function show(){setPreview(await api<Preview>(`/environments/${environment.id}/assignment-rules/preview`,{method:'POST',body:JSON.stringify(payload)}))}
  async function save(){await api(`/environments/${environment.id}/assignment-rules`,{method:'POST',body:JSON.stringify(payload)});setName('');setValue('');setPreview(undefined);await client.invalidateQueries({queryKey:['assignment-rules',environment.id]})}
  return <Stack spacing={2}><Typography variant="h6">שיוך לפי מאפיין ארגוני</Typography>{rules.map(r=><Paper key={r.id} variant="outlined" sx={{p:2}}><Typography fontWeight={800}>{r.name}</Typography><Typography>{r.conditions.map(c=>`${c.field} = ${c.value}`).join(' וגם ')}</Typography></Paper>)}<Paper variant="outlined" sx={{p:2}}><Stack spacing={2}><TextField label="שם הכלל" value={name} onChange={e=>setName(e.target.value)}/><TextField select label="מקור השיוך" value={field} onChange={e=>setField(e.target.value)}><MenuItem value="department">מחלקה</MenuItem><MenuItem value="job_title">תפקיד ארגוני</MenuItem></TextField><TextField label="ערך" value={value} onChange={e=>{setValue(e.target.value);setPreview(undefined)}}/><Button disabled={!name||!value} onClick={show}>תצוגה מקדימה</Button>{preview&&<Alert severity="info"><Typography fontWeight={800}>כלל זה ישייך {preview.matched} משתמשים</Typography>{preview.users.map(user=><Typography key={user.id} variant="body2">{user.display_name} · {user.department||user.job_title||'ללא שיוך ארגוני'}</Typography>)}</Alert>}<Button variant="contained" disabled={!preview} onClick={save}>אישור ושמירת כלל</Button></Stack></Paper></Stack>;
}
