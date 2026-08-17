import { useState } from 'react';
import { useQuery,useQueryClient } from '@tanstack/react-query';
import { Button, Chip, FormControlLabel, MenuItem, Paper, Stack, Switch, TextField, Typography } from '@mui/material';
import { api } from '../../../../api/client';
import type { Environment, Group, User } from '../../../../types';
import { EnvironmentAssignmentRulesTab } from './EnvironmentAssignmentRulesTab';

type Membership={id:string;user_id?:string;user_name?:string;group_id?:string;group_name?:string;source:string;is_environment_manager:boolean};
export function EnvironmentAccessTab({environment}:{environment:Environment}) {
  const client=useQueryClient(); const [mode,setMode]=useState(0); const [value,setValue]=useState(''); const [activeOnly,setActiveOnly]=useState(true);
  const {data:members=[]}=useQuery({queryKey:['environment-members',environment.id],queryFn:()=>api<Membership[]>(`/environments/${environment.id}/memberships`)});
  const {data:users=[]}=useQuery({queryKey:['users',activeOnly],queryFn:()=>api<User[]>(`/users?active_only=${activeOnly}`)});
  const {data:groups=[]}=useQuery({queryKey:['groups'],queryFn:()=>api<Group[]>('/groups')});
  const refresh=()=>client.invalidateQueries({queryKey:['environment-members',environment.id]});
  async function add(){await api(`/environments/${environment.id}/memberships`,{method:'POST',body:JSON.stringify(mode===0?{user_id:value,group_id:null}:{user_id:null,group_id:value})});setValue('');await refresh()}
  async function remove(id:string){await api(`/environments/${environment.id}/memberships/${id}`,{method:'DELETE'});await refresh()}
  async function manager(member:Membership,enabled:boolean){await api(`/environments/${environment.id}/memberships/${member.id}`,{method:'PATCH',body:JSON.stringify({is_environment_manager:enabled})});await refresh()}
  const options=mode===0?users:groups.filter(group=>group.is_active);
  return <Stack spacing={3}><Typography variant="h6">משתמשים ושיוכים לסביבה</Typography><Paper variant="outlined" sx={{p:2}}><Stack spacing={2}><Typography fontWeight={800}>שיוך ישיר</Typography><TextField select fullWidth label="סוג שיוך" value={mode} onChange={e=>{setMode(Number(e.target.value));setValue('')}}><MenuItem value={0}>משתמש</MenuItem><MenuItem value={1}>קבוצת משתמשים</MenuItem></TextField>{mode===0&&<FormControlLabel control={<Switch checked={activeOnly} onChange={e=>setActiveOnly(e.target.checked)}/>} label="משתמשים פעילים בלבד"/>}<Stack direction={{xs:'column',sm:'row'}} gap={1}><TextField select fullWidth label={mode===0?'משתמש':'קבוצת משתמשים'} value={value} onChange={e=>setValue(e.target.value)}>{options.map(item=><MenuItem key={item.id} value={item.id}>{'display_name' in item?item.display_name:item.name}</MenuItem>)}</TextField><Button variant="contained" disabled={!value} onClick={add}>הוספה</Button></Stack></Stack></Paper>{members.map(m=><Paper key={m.id} variant="outlined" sx={{p:2}}><Stack direction={{xs:'column',sm:'row'}} gap={1} alignItems={{sm:'center'}}><Typography fontWeight={800} sx={{flex:1}}>{m.user_name||m.group_name}</Typography><Chip size="small" label={m.group_id?'קבוצה':m.source==='rule'?'כלל אוטומטי':'משתמש ישיר'}/>{m.user_id&&<FormControlLabel control={<Switch checked={m.is_environment_manager} onChange={e=>manager(m,e.target.checked)}/>} label="מנהל סביבה"/>}<Button color="error" disabled={m.source==='rule'} onClick={()=>remove(m.id)}>הסרה</Button></Stack></Paper>)}<EnvironmentAssignmentRulesTab environment={environment}/></Stack>;
}
