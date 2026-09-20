import { GroupsOutlined, HubOutlined, Public, SchemaOutlined } from '@mui/icons-material';
import { Alert, Box, Chip, Container, LinearProgress, Stack } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { api } from '../../api/client';
import { ScreenHeader } from '../../components/ScreenHeader';
import { ModuleDirectory } from '../../components/ModuleDirectory';
import type { Environment, Group, User } from '../../types';
import type { GlobalField } from '../admin/global-fields/types';
import { FieldHistorySettings } from './FieldHistorySettings';

export function ImplementerStudioPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const environments = useQuery({ queryKey: ['environments'], queryFn: () => api<Environment[]>('/environments') });
  const fields = useQuery({ queryKey: ['global-case-fields'], queryFn: () => api<GlobalField[]>('/global-case-fields?include_inactive=true') });
  const users = useQuery({ queryKey: ['users'], queryFn: () => api<User[]>('/users?active_only=false') });
  const groups = useQuery({ queryKey: ['groups'], queryFn: () => api<Group[]>('/groups') });
  const loading = environments.isLoading || fields.isLoading || users.isLoading || groups.isLoading;
  const selectWarnings = (fields.data || []).filter(field => field.is_active && ['single_select', 'multi_select'].includes(field.field_type) && !field.options.some(option => option.is_active)).length;
  const modules = [
    { id: 'environments', title: t('studio.environments'), description: t('studio.environmentsDescription'), url: '/admin/environments', icon: <Public />, count: environments.data?.length || 0 },
    { id: 'fields', title: t('nav.globalFields'), description: t('studio.fieldsDescription'), url: '/admin/case-values', icon: <SchemaOutlined />, count: fields.data?.length || 0 },
    { id: 'users', title: t('permissions.users'), description: t('studio.usersDescription'), url: '/admin/users', icon: <GroupsOutlined />, count: (users.data?.length || 0) + (groups.data?.length || 0) },
    { id: 'permissions', title: t('permissions.title'), description: t('studio.permissionsDescription'), url: '/admin/permissions', icon: <HubOutlined />, count: undefined },
  ];
  return <Box className="admin-page"><Container maxWidth="xl"><Stack spacing={3}>
    <ScreenHeader title={t('studio.title')} subtitle={t('studio.subtitle')} />
    {loading && <LinearProgress />}
    {selectWarnings > 0 && <Alert severity="warning">{t('studio.optionWarnings', { count: selectWarnings })}</Alert>}
    <ModuleDirectory items={modules.map(module => ({ ...module, detail: module.count === undefined ? undefined : <Chip label={module.count} size="small" />, onOpen: () => navigate(module.url) }))} />
    <FieldHistorySettings />
  </Stack></Container></Box>;
}
