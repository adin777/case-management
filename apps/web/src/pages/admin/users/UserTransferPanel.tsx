import { useRef, useState } from 'react';
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, Paper, Stack, Typography } from '@mui/material';
import { api, apiDownload, apiUpload } from '../../../api/client';

type ImportRow={email:string;display_name:string;action:string;errors:string[]};
type ImportPreview={created:number;updated:number;disabled:number;unchanged:number;errors:number;rows:ImportRow[];users:Record<string,unknown>[]};
type Filters={status:string;source:string;department:string;jobTitle:string;search:string};

function saveBlob(blob:Blob,name:string){const url=URL.createObjectURL(blob);const anchor=document.createElement('a');anchor.href=url;anchor.download=name;anchor.click();URL.revokeObjectURL(url)}

export function UserTransferPanel({filters,onApplied}:{filters:Filters;onApplied:()=>Promise<void>}){
  const input=useRef<HTMLInputElement>(null);const[preview,setPreview]=useState<ImportPreview>();const[open,setOpen]=useState(false);const[error,setError]=useState('');const[busy,setBusy]=useState(false);
  async function download(path:string,name:string){setError('');try{saveBlob(await apiDownload(path),name)}catch(caught){setError((caught as Error).message)}}
  async function choose(file?:File){if(!file)return;setBusy(true);setError('');try{const form=new FormData();form.append('file',file);setPreview(await apiUpload<ImportPreview>('/users/import/preview',form));setOpen(true)}catch(caught){setError((caught as Error).message)}finally{setBusy(false);if(input.current)input.current.value=''}}
  async function apply(){if(!preview)return;setBusy(true);setError('');try{await api('/users/import/apply',{method:'POST',body:JSON.stringify(preview.users)});await onApplied();setOpen(false);setPreview(undefined)}catch(caught){setError((caught as Error).message)}finally{setBusy(false)}}
  const params=new URLSearchParams();if(filters.status)params.set('status_filter',filters.status);if(filters.source)params.set('source',filters.source);if(filters.department)params.set('department',filters.department);if(filters.jobTitle)params.set('job_title',filters.jobTitle);if(filters.search)params.set('search',filters.search);
  return <Paper variant="outlined" sx={{p:2}}><Stack direction={{xs:'column',sm:'row'}} gap={1} alignItems={{sm:'center'}}><Typography fontWeight={800} sx={{flex:1}}>העברת משתמשים באמצעות Excel</Typography><Button onClick={()=>download('/users/import/template','user-import-template.xlsx')}>הורדת תבנית</Button><Button onClick={()=>input.current?.click()} disabled={busy}>ייבוא משתמשים</Button><Button variant="outlined" onClick={()=>download(`/users-export?${params}`,'users.xlsx')}>ייצוא משתמשים</Button><input ref={input} hidden type="file" accept=".xlsx" onChange={event=>choose(event.target.files?.[0])}/></Stack>{error&&<Alert severity="error" sx={{mt:1}}>{error}</Alert>}
    <Dialog open={open} onClose={()=>!busy&&setOpen(false)} fullWidth maxWidth="md"><DialogTitle>תצוגה מקדימה לייבוא משתמשים</DialogTitle><DialogContent><Alert severity={preview?.errors?'error':'info'}>חדשים: {preview?.created||0} · לעדכון: {preview?.updated||0} · ללא שינוי: {preview?.unchanged||0} · להשבתה: {preview?.disabled||0} · שגויים: {preview?.errors||0}</Alert><Stack spacing={1} sx={{mt:2,maxHeight:420,overflow:'auto'}}>{preview?.rows.map((row,index)=><Paper key={`${row.email}-${index}`} variant="outlined" sx={{p:1.5}}><Typography fontWeight={700}>{row.display_name} · {row.email}</Typography><Typography variant="body2">{row.action}{row.errors.length?` · ${row.errors.join(', ')}`:''}</Typography></Paper>)}</Stack></DialogContent><DialogActions><Button onClick={()=>setOpen(false)} disabled={busy}>ביטול</Button><Button variant="contained" onClick={apply} disabled={busy||!!preview?.errors}>אישור והחלה</Button></DialogActions></Dialog>
  </Paper>;
}
