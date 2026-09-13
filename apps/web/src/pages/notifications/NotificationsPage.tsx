import { Card,CardActionArea,CardContent,Container,MenuItem,Pagination,Stack,TextField,Typography } from '@mui/material';
import { useQuery,useQueryClient } from '@tanstack/react-query';
import { useNavigate,useSearchParams } from 'react-router-dom';
import { api } from '../../api/client';
import { ScreenHeader } from '../../components/ScreenHeader';

type Item={id:string;type:string;title:string;body:string;route?:string;is_read:boolean;created_at:string};
export function NotificationsPage(){
  const[search,setSearch]=useSearchParams();const navigate=useNavigate();const client=useQueryClient();const page=Number(search.get('page')||1),unread=search.get('unread')==='1',type=search.get('type')||'';
  const params=new URLSearchParams({page:String(page),page_size:'25',...(unread&&{unread_only:'true'}),...(type&&{notification_type:type})});
  const query=useQuery({queryKey:['notifications',params.toString()],queryFn:()=>api<{items:Item[];total:number}>(`/notifications?${params}`)});
  const set=(key:string,value:string)=>{const next=new URLSearchParams(search);if(value)next.set(key,value);else next.delete(key);next.set('page','1');setSearch(next)};
  return <Container maxWidth="md"><Stack spacing={2}><ScreenHeader title="התראות" subtitle="כל העדכונים החשובים במקום אחד"/><Stack direction={{xs:'column',sm:'row'}} gap={2}><TextField select label="מצב" value={unread?'1':''} onChange={e=>set('unread',e.target.value)}><MenuItem value="">הכול</MenuItem><MenuItem value="1">לא נקראו</MenuItem></TextField><TextField label="סוג התראה" value={type} onChange={e=>set('type',e.target.value)}/></Stack>{query.data?.items.map(item=><Card key={item.id} variant="outlined" sx={{borderColor:item.is_read?'divider':'primary.light'}}><CardActionArea onClick={async()=>{await api(`/notifications/${item.id}/read?is_read=true`,{method:'PUT'});await client.invalidateQueries({queryKey:['notifications']});navigate(item.route||'/notifications',{state:{returnTo:`/notifications?${search}`,returnLabel:'חזרה להתראות'}})}}><CardContent><Typography fontWeight={900}>{item.title}</Typography><Typography>{item.body}</Typography><Typography variant="caption" color="text.secondary">{new Date(item.created_at).toLocaleString('he-IL')}</Typography></CardContent></CardActionArea></Card>)}<Pagination page={page} count={Math.max(1,Math.ceil((query.data?.total||0)/25))} onChange={(_,value)=>{const next=new URLSearchParams(search);next.set('page',String(value));setSearch(next)}}/></Stack></Container>
}
