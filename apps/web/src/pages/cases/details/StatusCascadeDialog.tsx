import {useState} from 'react';
import {Alert,Button,Dialog,DialogActions,DialogContent,DialogTitle,Stack,Typography} from '@mui/material';
import {useTranslation} from 'react-i18next';
import {api} from '../../../api/client';

type Preview={preview_id:string;eligible:string[];unauthorized:string[];locked:string[];total_descendants:number};
export function StatusCascadeDialog({caseId,statusId,open,onClose,onApplied}:{caseId:string;statusId?:string;open:boolean;onClose:()=>void;onApplied:(summary:string)=>void}){
  const{t}=useTranslation();const[preview,setPreview]=useState<Preview>();const[error,setError]=useState('');const[busy,setBusy]=useState(false);
  async function choose(include_descendants:boolean){if(!statusId)return;setBusy(true);setError('');try{setPreview(await api<Preview>(`/cases/${caseId}/status-change-preview`,{method:'POST',body:JSON.stringify({target_status_id:statusId,include_descendants})}))}catch(caught){setError((caught as Error).message)}finally{setBusy(false)}}
  async function apply(){if(!preview)return;setBusy(true);try{const result=await api<{updated_count:number}>(`/cases/${caseId}/status-change`,{method:'POST',body:JSON.stringify({preview_id:preview.preview_id})});onApplied(t('relations.statusSummary',{count:result.updated_count}));setPreview(undefined);onClose()}catch(caught){setError((caught as Error).message)}finally{setBusy(false)}}
  return <Dialog open={open} onClose={onClose} fullWidth><DialogTitle>{t('relations.statusQuestion')}</DialogTitle><DialogContent><Stack spacing={2}>{error&&<Alert severity="error">{error}</Alert>}{preview?<><Typography>{t('relations.canUpdate',{count:preview.eligible.length})}</Typography><Typography>{t('relations.noPermission',{count:preview.unauthorized.length})}</Typography><Typography>{t('relations.locked',{count:preview.locked.length})}</Typography></>:<Typography>{t('relations.statusHelp')}</Typography>}</Stack></DialogContent><DialogActions>{preview?<><Button onClick={()=>setPreview(undefined)}>{t('common.cancel')}</Button><Button variant="contained" disabled={busy} onClick={apply}>{t('common.confirm')}</Button></>:<><Button disabled={busy} onClick={()=>choose(false)}>{t('relations.onlyThis')}</Button><Button variant="contained" disabled={busy} onClick={()=>choose(true)}>{t('relations.withChildren')}</Button></>}</DialogActions></Dialog>
}
