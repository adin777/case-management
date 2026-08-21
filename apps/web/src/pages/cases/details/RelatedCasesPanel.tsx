import {useState} from 'react';
import {Delete,OpenInNew} from '@mui/icons-material';
import {Alert,Button,Card,CardContent,Divider,IconButton,Stack,Typography} from '@mui/material';
import {Link} from 'react-router-dom';
import {useQuery,useQueryClient} from '@tanstack/react-query';
import {useTranslation} from 'react-i18next';
import {api} from '../../../api/client';
import {AppSelect} from '../../../components/AppSelect';
import type {Case} from '../../../types';

type Related={id:string;relation_id?:string;case_number:string;title:string;environment:string;status:string;assignee?:string};
type Relations={parent?:Related|null;children:Related[]};

export function RelatedCasesPanel({caseId,canEdit}:{caseId:string;canEdit:boolean}){
  const{t}=useTranslation();const qc=useQueryClient();const[selected,setSelected]=useState('');const[error,setError]=useState('');
  const query=useQuery({queryKey:['case-relations',caseId],queryFn:()=>api<Relations>(`/cases/${caseId}/relations`)});
  const candidates=useQuery({queryKey:['relation-candidates',caseId],queryFn:()=>api<Case[]>('/cases')});
  const available=(candidates.data||[]).filter(row=>row.id!==caseId&&!query.data?.children.some(child=>child.id===row.id));
  async function link(){try{await api(`/cases/${caseId}/relations`,{method:'POST',body:JSON.stringify({child_case_id:selected})});setSelected('');await qc.invalidateQueries({queryKey:['case-relations',caseId]});}catch(caught){setError((caught as Error).message)}}
  async function remove(relationId:string){try{await api(`/cases/${caseId}/relations/${relationId}`,{method:'DELETE'});await qc.invalidateQueries({queryKey:['case-relations',caseId]});}catch(caught){setError((caught as Error).message)}}
  return <Card><CardContent><Typography variant="h6">{t('relations.title')}</Typography><Divider sx={{my:2}}/>{error&&<Alert severity="error" sx={{mb:2}}>{error}</Alert>}
    {query.data?.parent&&<Stack direction="row" alignItems="center" gap={1} mb={2}><Typography><strong>{t('relations.parent')}:</strong> {query.data.parent.case_number} · {query.data.parent.title}</Typography><IconButton component={Link} to={`/cases/${query.data.parent.id}`} aria-label={t('relations.open')}><OpenInNew/></IconButton></Stack>}
    <Typography fontWeight={800} mb={1}>{t('relations.children')}</Typography>
    <Stack spacing={1}>{query.data?.children.length?query.data.children.map(child=><Stack key={child.id} direction={{xs:'column',sm:'row'}} alignItems={{sm:'center'}} gap={1} sx={{p:1.5,border:'1px solid',borderColor:'divider',borderRadius:2}}><Typography flex={1}><strong>{child.case_number}</strong> · {child.title} · {child.environment} · {child.status}{child.assignee?` · ${child.assignee}`:''}</Typography><IconButton component={Link} to={`/cases/${child.id}`} aria-label={t('relations.open')}><OpenInNew/></IconButton>{canEdit&&child.relation_id&&<IconButton color="error" onClick={()=>remove(child.relation_id!)} aria-label={t('relations.remove')}><Delete/></IconButton>}</Stack>):<Typography color="text.secondary">{t('relations.empty')}</Typography>}</Stack>
    {canEdit&&<Stack direction={{xs:'column',sm:'row'}} gap={1} mt={2}><Button component={Link} to={`/cases/new?parentCaseId=${caseId}`} variant="contained">{t('relations.createChild')}</Button><AppSelect label={t('relations.linkExisting')} value={selected} onChange={setSelected} options={available.map(row=>({value:row.id,label:`${row.case_number} · ${row.title}`}))}/><Button disabled={!selected} onClick={link}>{t('relations.link')}</Button></Stack>}
  </CardContent></Card>;
}
