import { Add, AssignmentLateOutlined, ConfirmationNumberOutlined, History } from '@mui/icons-material';
import { Alert, Box, Button, CardActionArea, Container, Skeleton, Stack, Typography } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { api } from '../../api/client';
import { BusinessPill } from '../../components/BusinessPill';
import { ScreenHeader } from '../../components/ScreenHeader';
import { displayCaseNumber } from '../cases/details/caseDisplay';
import type { WorkspaceResponse } from '../dashboard/types';
import { openCase } from '../../navigation/caseNavigation';

export function PortalHomePage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const query = useQuery({ queryKey: ['portal-my-cases'], queryFn: () => api<WorkspaceResponse>('/cases/workspace/query?view=my&page=1&page_size=6&sort=updated_at%3Adesc&include_participating=true'), retry: false });
  const cases = query.data?.items || [];
  const pending = cases.filter((item) => /ממתין|waiting/i.test(item.status));
  const summary = [
    { label: t('dashboard.my'), value: query.data?.total || 0, icon: <ConfirmationNumberOutlined color="primary" /> },
    { label: t('portal.waiting'), value: pending.length, icon: <AssignmentLateOutlined color="warning" /> },
    { label: t('portal.updated'), value: cases.length, icon: <History color="action" /> },
  ];
  return <Container maxWidth="xl"><Stack spacing={3}>
    <ScreenHeader title={t('nav.portal')} subtitle={t('portal.subtitle')} action={<Button component={Link} to="/cases/new" variant="contained" size="large" startIcon={<Add />}>{t('cases.createTitle')}</Button>} />
    <Box className="portal-summary">{summary.map(item => <Box className="portal-summary-item" key={item.label}>{item.icon}<Box><Typography className="portal-summary-number">{query.isLoading ? <Skeleton width={44} /> : item.value}</Typography><Typography variant="body2" color="text.secondary">{item.label}</Typography></Box></Box>)}</Box>
    {query.isLoading ? <Stack spacing={1.5} aria-label={t('common.loading')}>{[0, 1, 2].map(row => <Skeleton key={row} variant="rounded" height={96} />)}</Stack> : query.error ? <Alert severity="error">{t('portal.loadFailed')}</Alert> : <Stack spacing={2}>
      <Typography component="h2" variant="h5">{t('portal.recent')}</Typography>
      {!!cases.length && <Box className="portal-case-list">{cases.map(item => <CardActionArea className="portal-case-row" key={item.id} onClick={() => openCase(navigate, location, item.id, t('portal.back'))}>
        <Typography className="portal-case-number" variant="body2" color="primary" fontWeight={650}>{displayCaseNumber(item.case_number)}</Typography>
        <Box className="portal-case-copy"><Typography component="h3" variant="h6">{item.title}</Typography><Typography variant="body2" color="text.secondary" mt={.5}>{item.environment} · {new Date(item.updated_at).toLocaleString(i18n.language === 'en' ? 'en-US' : 'he-IL')}</Typography></Box>
        <Stack className="portal-case-pills" direction="row" gap={1} alignItems="center" flexWrap="wrap"><BusinessPill label={item.status} /><BusinessPill label={item.priority} kind="priority" /></Stack>
      </CardActionArea>)}</Box>}
      {!cases.length && <Alert severity="info">{t('portal.empty')}</Alert>}
    </Stack>}
  </Stack></Container>;
}
