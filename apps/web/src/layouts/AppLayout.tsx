import { type ReactNode, useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Add, ApprovalOutlined, AssessmentOutlined, FolderOpenOutlined, HomeOutlined, Logout, Menu, PhoneIphone, SwitchAccount, Tune, WorkOutline } from '@mui/icons-material';
import { NotificationBell } from '../components/notifications/NotificationBell';
import { Alert, AppBar, Avatar, Badge, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, Divider, Drawer, IconButton, List, ListItemButton, ListItemIcon, ListItemText, MenuItem, Stack, TextField, Toolbar, Tooltip, Typography } from '@mui/material';
import { api, token } from '../api/client';
import type { User } from '../types';
import { applyIdentityToken } from './identitySwitch';
import { useTranslation } from 'react-i18next';
import { applyLanguage, type AppLanguage } from '../i18n';
import { ImpersonationBanner, type ImpersonationStatus } from './ImpersonationBanner';
import { MobilePreviewDialog } from './MobilePreviewDialog';
import { isNavigationActive } from './navigationState';

type LinkItem = { url: string; label: string; icon: ReactNode; implementer?: boolean; agent?: boolean };
export function AppLayout() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate(); const client = useQueryClient(); const routeLocation = useLocation();
  const [open, setOpen] = useState(false);
  const [impersonationOpen, setImpersonationOpen] = useState(false);
  const [mobilePreviewOpen, setMobilePreviewOpen] = useState(false);
  const [targetId, setTargetId] = useState('');
  async function adoptIdentity(accessToken: string) {
    applyIdentityToken(accessToken, client); setImpersonationOpen(false); setTargetId('');
    await Promise.all([client.fetchQuery({ queryKey: ['me'], queryFn: () => api<User>('/auth/me') }), client.fetchQuery({ queryKey: ['impersonation-status'], queryFn: () => api<ImpersonationStatus>('/impersonation/status') })]);
    navigate('/');
  }
  const { data: user } = useQuery({ queryKey: ['me'], queryFn: () => api<User>('/auth/me') });
  const { data: impersonation } = useQuery({ queryKey: ['impersonation-status'], queryFn: () => api<ImpersonationStatus>('/impersonation/status') });
  const { data: users = [] } = useQuery({ queryKey: ['users-for-impersonation'], queryFn: () => api<User[]>('/users'), enabled: !!impersonation?.can_start });
  const { data: approvals = [] } = useQuery({ queryKey: ['pending-approvals'], queryFn: () => api<unknown[]>('/approvals/pending-for-me') });
  const baseLinks: LinkItem[] = [
    { url: '/', label: t('nav.portal'), icon: <HomeOutlined /> },
    { url: '/workspace', label: t('dashboard.title'), icon: <WorkOutline />, agent: true },
    { url: '/reports', label: t('nav.reports'), icon: <AssessmentOutlined /> },
    { url: '/implementer', label: t('nav.implementer'), icon: <Tune />, implementer: true },
  ];
  const links: LinkItem[] = approvals.length ? [...baseLinks.slice(0, 2), { url: '/approvals/pending', label: t('nav.pendingApprovals'), icon: <Badge badgeContent={approvals.length} color="warning"><ApprovalOutlined /></Badge> }, ...baseLinks.slice(2)] : baseLinks;
  const canImplement = user?.is_system_admin || Boolean(user?.can_implement);
  const embeddedPreview = new URLSearchParams(routeLocation.search).get('mobilePreview') === '1';
  const visibleLinks = links.filter((link) => (!link.implementer || canImplement) && (!link.agent || user?.can_use_agent_workspace));
  const direction = i18n.language === 'en' ? 'ltr' : 'rtl';
  const drawerAnchor = direction === 'rtl' ? 'right' : 'left';
  const currentLink = visibleLinks.find(link => isNavigationActive(routeLocation.pathname, link.url));
  const drawer = <Box className="app-navigation">
    <Box className="drawer-brand"><Box className="brand-mark"><FolderOpenOutlined fontSize="small" /></Box><Typography fontWeight={700}>{t('app.name')}</Typography></Box>
    <Divider />
    <List component="nav" aria-label={t('nav.mainNavigation')} className="app-navigation-list">{visibleLinks.map(link => <ListItemButton selected={isNavigationActive(routeLocation.pathname, link.url)} aria-current={isNavigationActive(routeLocation.pathname, link.url) ? 'page' : undefined} key={link.url} onClick={() => { navigate(link.url); setOpen(false); }}><ListItemIcon>{link.icon}</ListItemIcon><ListItemText primary={link.label} /></ListItemButton>)}</List>
    <Stack className="app-navigation-footer" direction="row" alignItems="center" gap={1.5}><Avatar>{user?.display_name?.[0]}</Avatar><Box minWidth={0}><Typography variant="body2" fontWeight={650} noWrap>{user?.display_name}</Typography><Typography variant="caption" color="text.secondary">{t('app.name')}</Typography></Box></Stack>
  </Box>;
  return <Box className="app-shell" sx={{ display: 'flex' }}>
    <AppBar position="fixed" color="inherit" elevation={0} sx={{ borderBottom: '1px solid', borderColor: 'divider', width: { md: 'calc(100% - 248px)' }, ...(direction === 'rtl' ? { left: 0, right: 'auto' } : { right: 0, left: 'auto' }), bgcolor: 'background.paper' }}>
      <Toolbar className="app-toolbar">
        <IconButton aria-label={t('header.openMenu')} sx={{ display: { md: 'none' } }} onClick={() => setOpen(true)}><Menu /></IconButton>
        <Typography className="app-toolbar-title" variant="body2" color="text.secondary" noWrap>{currentLink?.label || t('app.name')}</Typography>
        {user?.is_system_admin&&!embeddedPreview && <Tooltip title={t('header.mobilePreview')}><IconButton aria-label={t('header.mobilePreview')} onClick={() => setMobilePreviewOpen(true)}><PhoneIphone /></IconButton></Tooltip>}
        <TextField className="app-language" select size="small" value={i18n.language === 'en' ? 'en' : 'he'} slotProps={{ select: { inputProps: { 'aria-label': t('language.label') } } }} onChange={event => void applyLanguage(event.target.value as AppLanguage)} sx={{ minWidth: 88 }}><MenuItem value="he">{t('language.he')}</MenuItem><MenuItem value="en">{t('language.en')}</MenuItem></TextField>
        {impersonation?.can_start && <Tooltip title={t('header.impersonate')}><IconButton aria-label={t('header.impersonate')} onClick={() => setImpersonationOpen(true)}><SwitchAccount /></IconButton></Tooltip>}
        <NotificationBell />
        <Avatar sx={{ display: { xs: 'none', sm: 'flex' }, marginInlineStart: 1 }}>{user?.display_name?.[0]}</Avatar>
        <Typography className="app-user-name" variant="body2">{user?.display_name}</Typography>
        <Tooltip title={t('header.logout')}><IconButton aria-label={t('header.logout')} onClick={() => { token.clear(); location.href = '/login'; }}><Logout /></IconButton></Tooltip>
      </Toolbar>
    </AppBar>
    <Drawer variant="permanent" anchor={drawerAnchor} sx={{ display: { xs: 'none', md: 'block' }, '& .MuiDrawer-paper': { width: 248, borderColor: 'divider' } }}>{drawer}</Drawer>
    <Drawer open={open} anchor={drawerAnchor} onClose={() => setOpen(false)} sx={{ display: { md: 'none' }, '& .MuiDrawer-paper': { width: 248 } }}>{drawer}</Drawer>
    <Box component="main" className="app-main" sx={{ flex: 1, p: { xs: 2, md: 4 }, pb: { xs: 12, md: 4 }, mt: { xs: 10, md: 8 }, ...(direction === 'rtl' ? { mr: { md: '248px' } } : { ml: { md: '248px' } }), minWidth: 0 }}>
      <ImpersonationBanner status={impersonation || { active: false, can_start: false }} onEnd={async () => { const result = await api<{ access_token: string }>('/impersonation/stop', { method: 'POST' }); await adoptIdentity(result.access_token); }} />
      <Outlet />
    </Box>
    {!routeLocation.pathname.startsWith('/cases/') && <Button aria-label={t('cases.createTitle')} variant="contained" startIcon={<Add />} onClick={() => navigate('/cases/new')} sx={{ display: { md: 'none' }, position: 'fixed', bottom: 'max(18px, env(safe-area-inset-bottom))', insetInlineEnd: 18, zIndex: 20, minHeight: 48, borderRadius: '8px', boxShadow: 3 }}>{t('dashboard.newCase')}</Button>}
    <Dialog open={impersonationOpen} onClose={() => setImpersonationOpen(false)} fullWidth maxWidth="sm">
      <DialogTitle>{t('header.impersonate')}</DialogTitle><DialogContent><Alert severity="info" sx={{ mb: 2 }}>{t('header.impersonationNotice')}</Alert><TextField select fullWidth label={t('header.chooseUser')} value={targetId} onChange={event => setTargetId(event.target.value)}>{users.filter(row => row.is_active !== false && row.id !== user?.id).map(row => <MenuItem key={row.id} value={row.id}>{row.display_name} · {row.email}</MenuItem>)}</TextField></DialogContent>
      <DialogActions><Button onClick={() => setImpersonationOpen(false)}>{t('common.cancel')}</Button><Button variant="contained" disabled={!targetId} onClick={async () => { const result = await api<{ access_token: string }>('/impersonation/start', { method: 'POST', body: JSON.stringify({ user_id: targetId }) }); await adoptIdentity(result.access_token); }}>{t('header.startImpersonation')}</Button></DialogActions>
    </Dialog>
    {!embeddedPreview && <MobilePreviewDialog open={mobilePreviewOpen} onClose={() => setMobilePreviewOpen(false)} path={`${routeLocation.pathname}${routeLocation.search}`} />}
  </Box>;
}
