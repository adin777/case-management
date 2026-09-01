import { AccountTree, AutoFixHigh, FactCheck, Groups, Hub, Inventory2, Public, Rule, Schema } from '@mui/icons-material';
import { Alert, Box, Card, CardActionArea, CardContent, Chip, Container, LinearProgress, Stack, Typography } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api } from '../../api/client';
import { ScreenHeader } from '../../components/ScreenHeader';
import type { Environment, Group, User } from '../../types';
import type { GlobalField } from '../admin/global-fields/types';
import type { ReactNode } from 'react';

type Module={title:string;description:string;url:string;icon:ReactNode;count:number;warning?:string};
export function ImplementerStudioPage(){
  const navigate=useNavigate();
  const environments=useQuery({queryKey:['environments'],queryFn:()=>api<Environment[]>('/environments')});
  const fields=useQuery({queryKey:['global-case-fields'],queryFn:()=>api<GlobalField[]>('/global-case-fields?include_inactive=true')});
  const users=useQuery({queryKey:['users'],queryFn:()=>api<User[]>('/users?active_only=false')});
  const groups=useQuery({queryKey:['groups'],queryFn:()=>api<Group[]>('/groups')});
  const loading=environments.isLoading||fields.isLoading||users.isLoading||groups.isLoading;
  const selectWarnings=(fields.data||[]).filter(field=>field.is_active&&['single_select','multi_select'].includes(field.field_type)&&!field.options.some(option=>option.is_active)).length;
  const modules:Module[]=[
    {title:'סביבות עבודה',description:'הקמה, שכפול והגדרת תהליך עסקי',url:'/admin/environments',icon:<Public/>,count:environments.data?.length||0},
    {title:'שדות גלובליים',description:'שדות, אפשרויות, תרגומים וסדר תצוגה',url:'/admin/case-values',icon:<Schema/>,count:fields.data?.length||0,warning:selectWarnings?`${selectWarnings} שדות דורשים אפשרויות`:undefined},
    {title:'משתמשים וקבוצות',description:'זהויות, קבוצות ושיוכים ארגוניים',url:'/admin/users',icon:<Groups/>,count:(users.data?.length||0)+(groups.data?.length||0)},
    {title:'הרשאות',description:'הרשאות ישירות, ירושה ותחולה סביבתית',url:'/admin/permissions',icon:<Hub/>,count:0},
    {title:'סוגי קריאות ושדות סביבה',description:'מנוהלים מתוך סביבת העבודה הנבחרת',url:'/admin/environments',icon:<Inventory2/>,count:0},
    {title:'אוטומציות',description:'כללים חזותיים המבוססים על שדות יציבים',url:'/admin/environments',icon:<AutoFixHigh/>,count:0},
    {title:'אישורים',description:'שלבים, מאשרים ותצוגה מקדימה של השרשרת',url:'/admin/environments',icon:<AccountTree/>,count:0},
    {title:'בדיקת תקינות',description:'בדיקת תלויות ואזהרות לפני שינוי',url:'/admin/environments',icon:<FactCheck/>,count:selectWarnings},
    {title:'כללי שיוך',description:'שיוך לפי משתמש, קבוצה, מחלקה או תפקיד',url:'/admin/environments',icon:<Rule/>,count:0},
  ];
  return <Box className="admin-page"><Container maxWidth="xl"><Stack spacing={2.5}><ScreenHeader title="סטודיו להגדרת מערכת" subtitle="כל הגדרות התהליך העסקי, התקינות וההרשאות במקום אחד"/>{loading&&<LinearProgress/>}{selectWarnings>0&&<Alert severity="warning">נמצאו {selectWarnings} שדות בחירה פעילים ללא אפשרויות פעילות.</Alert>}<Box sx={{display:'grid',gridTemplateColumns:{xs:'1fr',sm:'repeat(2,minmax(0,1fr))',lg:'repeat(3,minmax(0,1fr))'},gap:2}}>{modules.map(module=><Card key={module.title} variant="outlined" className="report-card"><CardActionArea onClick={()=>navigate(module.url)} sx={{height:'100%'}}><CardContent><Stack direction="row" justifyContent="space-between" alignItems="flex-start"><Box className="permission-module-icon">{module.icon}</Box><Chip label={module.count} size="small"/></Stack><Typography variant="h6" mt={2}>{module.title}</Typography><Typography color="text.secondary">{module.description}</Typography>{module.warning&&<Chip color="warning" label={module.warning} sx={{mt:2}}/>}</CardContent></CardActionArea></Card>)}</Box></Stack></Container></Box>;
}
