import { Add, AssignmentLate, ConfirmationNumber, History } from '@mui/icons-material';
import { Alert, Box, Button, Card, CardActionArea, CardContent, CircularProgress, Container, Stack, Typography } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { api } from '../../api/client';
import { BusinessPill } from '../../components/BusinessPill';
import { ScreenHeader } from '../../components/ScreenHeader';
import { displayCaseNumber } from '../cases/details/caseDisplay';
import type { WorkspaceResponse } from '../dashboard/types';
import { openCase } from '../../navigation/caseNavigation';

export function PortalHomePage() {
  const navigate = useNavigate();
  const location = useLocation();
  const query = useQuery({ queryKey: ['portal-my-cases'], queryFn: () => api<WorkspaceResponse>('/cases/workspace/query?view=my&page=1&page_size=6&sort=updated_at%3Adesc&include_participating=true'), retry: false });
  const cases = query.data?.items || [];
  const pending = cases.filter((item) => /ממתין|waiting/i.test(item.status));
  return <Container maxWidth="lg"><Stack spacing={3}><ScreenHeader title="הפורטל שלי" subtitle="פתיחת קריאה, מעקב ועדכונים במקום אחד" action={<Button component={Link} to="/cases/new" variant="contained" size="large" startIcon={<Add/>}>פתיחת קריאה חדשה</Button>}/><Box sx={{display:'grid',gridTemplateColumns:{xs:'1fr',sm:'repeat(3,1fr)'},gap:2}}><Card variant="outlined"><CardContent><ConfirmationNumber color="primary"/><Typography variant="h4">{query.data?.total||0}</Typography><Typography>הקריאות שלי</Typography></CardContent></Card><Card variant="outlined"><CardContent><AssignmentLate color="warning"/><Typography variant="h4">{pending.length}</Typography><Typography>ממתינות לתגובה</Typography></CardContent></Card><Card variant="outlined"><CardContent><History color="action"/><Typography variant="h4">{cases.length}</Typography><Typography>עודכנו לאחרונה</Typography></CardContent></Card></Box>{query.isLoading?<Box textAlign="center" py={6}><CircularProgress/></Box>:query.error?<Alert severity="error">לא ניתן לטעון את הקריאות כעת</Alert>:<Stack spacing={1.5}><Typography variant="h5">קריאות אחרונות</Typography>{cases.map(item=><Card key={item.id} variant="outlined"><CardActionArea onClick={()=>openCase(navigate,location,item.id,'חזרה לקריאות שלי')}><CardContent><Stack direction={{xs:'column',sm:'row'}} justifyContent="space-between" gap={1}><Box><Typography color="primary" fontWeight={850}>{displayCaseNumber(item.case_number)}</Typography><Typography variant="h6">{item.title}</Typography><Typography color="text.secondary">{item.environment} · {new Date(item.updated_at).toLocaleString('he-IL')}</Typography></Box><Stack direction="row" gap={1} alignItems="center"><BusinessPill label={item.status}/><BusinessPill label={item.priority} kind="priority"/></Stack></Stack></CardContent></CardActionArea></Card>)}{!cases.length&&<Alert severity="info">עדיין אין קריאות להצגה. אפשר לפתוח קריאה חדשה מהכפתור למעלה.</Alert>}</Stack>}</Stack></Container>;
}
