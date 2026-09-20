import type { ReactNode } from 'react';
import { AssessmentOutlined, FactCheckOutlined, GroupsOutlined, History, TimerOutlined } from '@mui/icons-material';
import { Alert, Box, Container, Skeleton, Stack } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { api } from '../../api/client';
import { ScreenHeader } from '../../components/ScreenHeader';
import { ModuleDirectory } from '../../components/ModuleDirectory';

const icons: Record<string, ReactNode> = { cases: <AssessmentOutlined />, approvals: <FactCheckOutlined />, users: <GroupsOutlined />, audit: <History />, sla: <TimerOutlined /> };
export function ReportsCenterPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data = [], isLoading, error } = useQuery({ queryKey: ['available-reports'], queryFn: () => api<{ code: string; name: string }[]>('/reports/available') });
  return <Box className="reports-page"><Container maxWidth="xl"><Stack spacing={3}>
    <ScreenHeader title={t('reports.title')} subtitle={t('reports.subtitle')} />
    {isLoading ? <Stack spacing={2} aria-label={t('common.loading')}>{[0, 1, 2].map(row => <Skeleton key={row} variant="rounded" height={96} />)}</Stack> : error ? <Alert severity="error">{t('reports.failed')}</Alert> : data.length ? <ModuleDirectory items={data.map(report => ({ id: report.code, title: report.name, description: t(`reportDirectory.${report.code}`, { defaultValue: '' }), icon: icons[report.code] || <AssessmentOutlined />, onOpen: () => navigate(report.code === 'cases' ? '/reports/cases' : `/reports/${report.code}`) }))} /> : <Alert severity="info">{t('reportDirectory.empty')}</Alert>}
  </Stack></Container></Box>;
}
