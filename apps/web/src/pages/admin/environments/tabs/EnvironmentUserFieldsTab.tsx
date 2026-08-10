import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Alert, Button, Paper, Stack, TextField, Typography } from '@mui/material';
import { api } from '../../../../api/client';
import type { Environment, UserField } from '../../../../types';

type EnvironmentFieldRow={definition:UserField};
export function EnvironmentUserFieldsTab({environment}:{environment:Environment}){
  const client=useQueryClient(); const[label,setLabel]=useState(''); const[key,setKey]=useState(''); const[error,setError]=useState('');
  const{data:rows=[]}=useQuery({queryKey:['environment-user-fields',environment.id],queryFn:()=>api<EnvironmentFieldRow[]>(`/environments/${environment.id}/user-fields`)});
  async function create(){setError('');try{await api(`/environments/${environment.id}/user-field-definitions`,{method:'POST',body:JSON.stringify({key,label_he:label,label_en:label,field_type:'short_text',is_active:true,environment_ids:[]})});setLabel('');setKey('');await client.invalidateQueries({queryKey:['environment-user-fields',environment.id]})}catch(e){setError((e as Error).message)}}
  const scoped=rows.filter(row=>row.definition.scope==='environment');
  return <Stack spacing={2}><Typography variant="h6">שדות משתמש בסביבה</Typography><Typography color="text.secondary">שדות אלה מוצגים רק למשתמשים בהקשר של {environment.name_he}.</Typography>{error&&<Alert severity="error">{error}</Alert>}<Stack direction={{xs:'column',sm:'row'}} spacing={1}><TextField label="שם השדה" value={label} onChange={e=>setLabel(e.target.value)}/><TextField label="מפתח טכני" value={key} onChange={e=>setKey(e.target.value)}/><Button variant="contained" disabled={!label.trim()||!key.trim()} onClick={create}>הוספה</Button></Stack>{scoped.map(row=><Paper key={row.definition.id} variant="outlined" sx={{p:2}}><Typography fontWeight={800}>{row.definition.label_he}</Typography><Typography variant="body2">{row.definition.key} · {row.definition.is_active?'פעיל':'לא פעיל'}</Typography></Paper>)}</Stack>;
}
