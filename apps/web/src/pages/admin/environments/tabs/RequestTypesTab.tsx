import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Add } from '@mui/icons-material';
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, Paper, Stack, TextField, Typography } from '@mui/material';
import { api } from '../../../../api/client'; import type { Environment, RequestType } from '../../../../types';

export function RequestTypesTab({ environment }: { environment: Environment }) {
  const qc=useQueryClient(); const [open,setOpen]=useState(false); const [name,setName]=useState(''); const [error,setError]=useState('');
  const {data:items=[]}=useQuery({queryKey:['request-types',environment.id],queryFn:()=>api<RequestType[]>(`/request-types?environment_id=${environment.id}`)});
  async function create(){setError('');try{await api('/request-types',{method:'POST',body:JSON.stringify({environment_id:environment.id,code:`rt_${Date.now()}`,name_he:name,name_en:name,description:''})});setOpen(false);setName('');qc.invalidateQueries({queryKey:['request-types',environment.id]});}catch(e){setError((e as Error).message)}}
  async function toggle(item:RequestType){await api(`/request-types/${item.id}`,{method:'PATCH',body:JSON.stringify({is_active:!item.is_active})});qc.invalidateQueries({queryKey:['request-types',environment.id]})}
  return <Stack spacing={2}><Button startIcon={<Add/>} variant="contained" onClick={()=>setOpen(true)} sx={{alignSelf:'flex-start'}}>סוג קריאה חדש</Button>{items.map(item=><Paper key={item.id} variant="outlined" sx={{p:2}}><Stack direction={{xs:'column',sm:'row'}} justifyContent="space-between"><div><Typography fontWeight={700}>{item.name_he}</Typography><Typography variant="body2" color="text.secondary">{item.system_number} · {item.is_active?'פעיל':'מושבת'}</Typography></div><Stack direction="row"><Button onClick={()=>toggle(item)}>{item.is_active?'השבתה':'הפעלה'}</Button><Button href={`/admin/request-types/${item.id}`}>פתיחת הגדרות</Button></Stack></Stack></Paper>)}<Dialog open={open} onClose={()=>setOpen(false)} fullWidth fullScreen={window.innerWidth<600}><DialogTitle>יצירת סוג קריאה</DialogTitle><DialogContent>{error&&<Alert severity="error">{error}</Alert>}<TextField autoFocus fullWidth label="שם בעברית" value={name} onChange={e=>setName(e.target.value)} sx={{mt:1}}/></DialogContent><DialogActions><Button onClick={()=>setOpen(false)}>ביטול</Button><Button variant="contained" disabled={!name.trim()} onClick={create}>יצירה</Button></DialogActions></Dialog></Stack>;
}
