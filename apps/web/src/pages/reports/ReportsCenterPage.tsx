import type { ReactNode } from 'react';
import { ArrowBack, Assessment, FactCheck, Groups, History, Timer } from '@mui/icons-material';
import { Box, Card, CardActionArea, CardContent, CircularProgress, Container, Grid, Stack, Typography } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api } from '../../api/client';
import { ScreenHeader } from '../../components/ScreenHeader';

const meta: Record<string, { description: string; icon: ReactNode; color: string }> = {
  cases: { description: 'קריאות שירות לפי סביבה, סטטוס, מטפל וטווחי זמן', icon: <Assessment/>, color: '#1d4ed8' },
  approvals: { description: 'משימות אישור, החלטות והערות', icon: <FactCheck/>, color: '#0f766e' },
  users: { description: 'משתמשים, שיוכים והרשאות אפקטיביות', icon: <Groups/>, color: '#7c3aed' },
  audit: { description: 'אירועי פעילות וביקורת מערכת', icon: <History/>, color: '#c2410c' },
  sla: { description: 'עמידה ביעדי תגובה ופתרון, סיכונים וחריגות', icon: <Timer/>, color: '#be123c' },
};

export function ReportsCenterPage() {
  const navigate = useNavigate(); const { data = [], isLoading } = useQuery({ queryKey: ['available-reports'], queryFn: () => api<{ code: string; name: string }[]>('/reports/available') });
  return <Box className="reports-page"><Container maxWidth="xl"><Stack spacing={3}>
    <ScreenHeader title="דוחות" subtitle="הדוחות המרכזיים המוצגים בהתאם להרשאות שלך"/>
    {isLoading ? <Stack alignItems="center" py={8}><CircularProgress/></Stack> : <Grid container spacing={2.5}>{data.map((report) => { const item = meta[report.code]; return <Grid key={report.code} size={{ xs: 12, sm: 6, lg: 3 }}><Card className="report-card"><CardActionArea onClick={() => navigate(report.code === 'cases' ? '/reports/cases' : `/reports/${report.code}`)} sx={{ height: '100%' }}><CardContent sx={{ p: 3 }}><Box sx={{ width: 52, height: 52, display: 'grid', placeItems: 'center', borderRadius: 3, bgcolor: `${item?.color}14`, color: item?.color, mb: 2 }}>{item?.icon}</Box><Typography variant="h6">{report.name}</Typography><Typography color="text.secondary" mt={1} minHeight={48}>{item?.description}</Typography><Stack direction="row" alignItems="center" gap={.5} mt={2} color="primary.main"><Typography fontWeight={750}>פתיחת הדוח</Typography><ArrowBack fontSize="small"/></Stack></CardContent></CardActionArea></Card></Grid>; })}</Grid>}
  </Stack></Container></Box>;
}
