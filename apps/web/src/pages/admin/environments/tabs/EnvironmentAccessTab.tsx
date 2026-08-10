import { useState } from 'react';
import { useQuery,useQueryClient } from '@tanstack/react-query';
import { Button, Chip, FormControlLabel, MenuItem, Paper, Stack, Switch, Tab, Tabs, TextField, Typography } from '@mui/material';
import { api } from '../../../../api/client';
import type { Environment, Group, User } from '../../../../types';

type Membership={id:string;user_id?:string;user_name?:string;group_id?:string;group_name?:string;source:string};
export function EnvironmentAccessTab({environment}:{environment:Environment}) {
  const client=useQueryClient(); const [mode,setMode]=useState(0); const [value,setValue]=useState(''); const [activeOnly,setActiveOnly]=useState(true);
  const {data:members=[]}=useQuery({queryKey:['environment-members',environment.id],queryFn:()=>api<Membership[]>(`/environments/${environment.id}/memberships`)});
  const {data:users=[]}=useQuery({queryKey:['users',activeOnly],queryFn:()=>api<User[]>(`/users?active_only=${activeOnly}`)});
  const {data:groups=[]}=useQuery({queryKey:['groups'],queryFn:()=>api<Group[]>('/groups')});
  const refresh=()=>client.invalidateQueries({queryKey:['environment-members',environment.id]});
  async function add(){await api(`/environments/${environment.id}/memberships`,{method:'POST',body:JSON.stringify(mode===0?{user_id:value,group_id:null}:{user_id:null,group_id:value})});setValue('');await refresh()}
  async function remove(id:string){await api(`/environments/${environment.id}/memberships/${id}`,{method:'DELETE'});await refresh()}
  const options=mode===0?users:groups.filter(group=>group.is_active);
  return <Stack spacing={2}><Typography variant="h6">שיוך משתמשים לסביבה</Typography><Tabs value={mode} onChange={(_,next)=>{setMode(next);setValue('')}}><Tab label="משתמש"/><Tab label="קבוצת משתמשים"/></Tabs>{mode===0&&<FormControlLabel control={<Switch checked={activeOnly} onChange={e=>setActiveOnly(e.target.checked)}/>} label="משתמשים פעילים בלבד"/>}{members.map(m=><Paper key={m.id} variant="outlined" sx={{p:2}}><Stack direction="row" gap={1} alignItems="center"><Typography fontWeight={800} sx={{flex:1}}>{m.user_name||m.group_name}</Typography><Chip size="small" label={m.group_id?'קבוצה':m.source==='rule'?'כלל אוטומטי':'משתמש ישיר'}/><Button color="error" disabled={m.source==='rule'} onClick={()=>remove(m.id)}>הסרה</Button></Stack></Paper>)}<Paper variant="outlined" sx={{p:2}}><Stack direction={{xs:'column',sm:'row'}} gap={1}><TextField select fullWidth label={mode===0?'משתמש':'קבוצה'} value={value} onChange={e=>setValue(e.target.value)}>{options.map(item=><MenuItem key={item.id} value={item.id}>{'display_name' in item?item.display_name:item.name}</MenuItem>)}</TextField><Button variant="contained" disabled={!value} onClick={add}>הוספה</Button></Stack></Paper></Stack>;
}
