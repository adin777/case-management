import { type ReactNode, useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Add, Approval, Assessment, Dashboard, Logout, Menu, Notifications, PhoneIphone, SwitchAccount, Tune } from '@mui/icons-material';
import { Alert, AppBar, Avatar, Badge, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, Divider, Drawer, IconButton, List, ListItemButton, ListItemIcon, ListItemText, MenuItem, TextField, Toolbar, Tooltip, Typography } from '@mui/material';
import { api, token } from '../api/client';
import type { User } from '../types';
import { applyIdentityToken } from './identitySwitch';
import { useTranslation } from 'react-i18next';
import { applyLanguage, type AppLanguage } from '../i18n';
import { ImpersonationBanner, type ImpersonationStatus } from './ImpersonationBanner';
import { MobilePreviewDialog } from './MobilePreviewDialog';

type LinkItem = { url: string; label: string; icon: ReactNode; implementer?: boolean; agent?: boolean };
export function AppLayout() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate(); const client=useQueryClient(); const routeLocation = useLocation(); const [open, setOpen] = useState(false); const [impersonationOpen, setImpersonationOpen] = useState(false); const [mobilePreviewOpen, setMobilePreviewOpen] = useState(false); const [targetId, setTargetId] = useState('');
  async function adoptIdentity(accessToken:string){applyIdentityToken(accessToken,client);setImpersonationOpen(false);setTargetId('');await Promise.all([client.fetchQuery({queryKey:['me'],queryFn:()=>api<User>('/auth/me')}),client.fetchQuery({queryKey:['impersonation-status'],queryFn:()=>api<ImpersonationStatus>('/impersonation/status')})]);navigate('/')}
  const { data: user } = useQuery({ queryKey: ['me'], queryFn: () => api<User>('/auth/me') });
  const { data: impersonation } = useQuery({ queryKey: ['impersonation-status'], queryFn: () => api<ImpersonationStatus>('/impersonation/status') });
  const { data: users = [] } = useQuery({ queryKey: ['users-for-impersonation'], queryFn: () => api<User[]>('/users'), enabled: !!impersonation?.can_start });
  const { data: approvals = [] } = useQuery({ queryKey: ['pending-approvals'], queryFn: () => api<unknown[]>('/approvals/pending-for-me') });
  const baseLinks: LinkItem[] = [
    { url: '/', label: 'הפורטל שלי', icon: <Dashboard/> }, { url: '/workspace', label: 'מרכז העבודה', icon: <Dashboard/>, agent: true }, { url: '/reports', label: t('nav.reports'), icon: <Assessment/> },
    { url: '/implementer', label: 'סטודיו למיישם', icon: <Tune/>, implementer: true },
  ];
  const links: LinkItem[] = approvals.length ? [...baseLinks.slice(0, 2), { url: '/approvals/pending', label: t('nav.pendingApprovals'), icon: <Badge badgeContent={approvals.length} color="warning"><Approval/></Badge> }, ...baseLinks.slice(2)] : baseLinks;
  const canImplement=user?.is_system_admin||Boolean(user?.can_implement);
  const embeddedPreview=new URLSearchParams(routeLocation.search).get('mobilePreview')==='1';
  const visibleLinks = links.filter((link) => (!link.implementer||canImplement)&&(!link.agent||user?.can_use_agent_workspace));
  const direction=i18n.language==='en'?'ltr':'rtl'; const drawerAnchor=direction==='rtl'?'right':'left';
  const drawer = <Box sx={{ width: 260 }}><Box className="drawer-brand">◆ {t('app.name')}</Box><Divider/><List>{visibleLinks.map((link) => <ListItemButton selected={routeLocation.pathname === link.url} key={link.url} onClick={() => { navigate(link.url); setOpen(false); }}><ListItemIcon>{link.icon}</ListItemIcon><ListItemText primary={link.label}/></ListItemButton>)}</List></Box>;
  return <Box sx={{ display: 'flex' }}>
    <AppBar position="fixed" color="inherit" elevation={0} sx={{ borderBottom: '1px solid #e1e7f0', width: { md: 'calc(100% - 260px)' }, backdropFilter: 'blur(12px)', bgcolor: 'rgba(255,255,255,.92)' }}><Toolbar><IconButton aria-label={t('header.openMenu')} sx={{ display: { md: 'none' } }} onClick={() => setOpen(true)}><Menu/></IconButton><Box sx={{ flex: 1 }}/>{user?.is_system_admin&&!embeddedPreview&&<Tooltip title="תצוגה מקדימה למובייל"><IconButton aria-label="תצוגה מקדימה למובייל" onClick={()=>setMobilePreviewOpen(true)}><PhoneIphone/></IconButton></Tooltip>}<TextField select size="small" aria-label={t('language.label')} value={i18n.language==='en'?'en':'he'} onChange={event=>void applyLanguage(event.target.value as AppLanguage)} sx={{minWidth:110,mx:1}}><MenuItem value="he">{t('language.he')}</MenuItem><MenuItem value="en">{t('language.en')}</MenuItem></TextField>{impersonation?.can_start && <Tooltip title={t('header.impersonate')}><IconButton onClick={() => setImpersonationOpen(true)}><SwitchAccount/></IconButton></Tooltip>}<Tooltip title={t('header.notifications')}><IconButton aria-label={t('header.notifications')}><Notifications/></IconButton></Tooltip><Avatar>{user?.display_name?.[0]}</Avatar><Typography sx={{ mx: 1 }}>{user?.display_name}</Typography><Tooltip title={t('header.logout')}><IconButton aria-label={t('header.logout')} onClick={() => { token.clear(); location.href = '/login'; }}><Logout/></IconButton></Tooltip></Toolbar></AppBar>
    <Drawer variant="permanent" anchor={drawerAnchor} sx={{ display: { xs: 'none', md: 'block' }, '& .MuiDrawer-paper': { width: 260 } }}>{drawer}</Drawer>
    <Drawer open={open} anchor={drawerAnchor} onClose={() => setOpen(false)} sx={{ display: { md: 'none' } }}>{drawer}</Drawer>
    <Box component="main" sx={{ flex: 1, p: { xs: 1.5, md: 4 }, pb:{xs:10,md:4}, mt: 8, ...(direction==='rtl'?{mr:{md:'260px'}}:{ml:{md:'260px'}}), minWidth: 0 }}><ImpersonationBanner status={impersonation||{active:false,can_start:false}} onEnd={async()=>{const result=await api<{access_token:string}>('/impersonation/stop',{method:'POST'});await adoptIdentity(result.access_token)}}/><Outlet/></Box>
    <Button aria-label="פתיחת קריאה חדשה" variant="contained" startIcon={<Add/>} onClick={()=>navigate('/cases/new')} sx={{display:{md:'none'},position:'fixed',bottom:18,left:18,zIndex:20,minHeight:48,borderRadius:8,boxShadow:6}}>פתיחת קריאה</Button>
    <Dialog open={impersonationOpen} onClose={() => setImpersonationOpen(false)} fullWidth maxWidth="sm"><DialogTitle>התחזות למשתמש</DialogTitle><DialogContent><Alert severity="info" sx={{ mb: 2 }}>כל פעולה תירשם ב־Audit עם המשתמש המקורי והמשתמש המוצג.</Alert><TextField select fullWidth label="בחירת משתמש פעיל" value={targetId} onChange={(event) => setTargetId(event.target.value)}>{users.filter((row) => row.is_active !== false && row.id !== user?.id).map((row) => <MenuItem key={row.id} value={row.id}>{row.display_name} · {row.email}</MenuItem>)}</TextField></DialogContent><DialogActions><Button onClick={() => setImpersonationOpen(false)}>ביטול</Button><Button variant="contained" disabled={!targetId} onClick={async () => { const result = await api<{access_token:string}>('/impersonation/start', { method: 'POST', body: JSON.stringify({ user_id: targetId }) }); await adoptIdentity(result.access_token); }}>התחלת התחזות</Button></DialogActions></Dialog>
    {!embeddedPreview&&<MobilePreviewDialog open={mobilePreviewOpen} onClose={()=>setMobilePreviewOpen(false)} path={`${routeLocation.pathname}${routeLocation.search}`}/>}
  </Box>;
}
