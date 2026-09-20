import { ExpandMore, Tune } from '@mui/icons-material';
import { Badge, Button, Collapse, Paper, Stack, Typography, useMediaQuery, useTheme } from '@mui/material';
import { type ReactNode, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FilterDrawer, ResponsiveFormGrid } from '../responsive/ResponsivePrimitives';

type Props = { primary: ReactNode; advanced?: ReactNode; actions?: ReactNode; activeCount: number; onReset: () => void };
export function CompactFilterPanel({ primary, advanced, actions, activeCount, onReset }: Props) {
  const { t } = useTranslation();
  const mobile = useMediaQuery(useTheme().breakpoints.down('md'));
  const [open, setOpen] = useState(false); const [more, setMore] = useState(false);
  const content = <Stack spacing={2}>
    <Stack direction="row" gap={1} alignItems="center"><Tune color="primary" /><Typography component="h2" variant="h6">{t('filters.title')}</Typography></Stack>
    <ResponsiveFormGrid>{primary}</ResponsiveFormGrid>
    {advanced && <><Button size="small" aria-expanded={more} endIcon={<ExpandMore sx={{ transform: more ? 'rotate(180deg)' : 'none' }} />} onClick={() => setMore(value => !value)} sx={{ alignSelf: 'flex-start' }}>{t('filters.more')}</Button><Collapse in={more}><ResponsiveFormGrid>{advanced}</ResponsiveFormGrid></Collapse></>}
    <Stack direction="row" gap={1} flexWrap="wrap">{actions}<Button size="small" onClick={onReset}>{t('reports.reset')}</Button></Stack>
  </Stack>;
  if (mobile) return <><Badge badgeContent={activeCount} color="primary" sx={{ alignSelf: 'flex-start' }}><Button variant="outlined" startIcon={<Tune />} onClick={() => setOpen(true)}>{t('filters.open')}</Button></Badge><FilterDrawer open={open} onClose={() => setOpen(false)} onReset={onReset}>{content}</FilterDrawer></>;
  return <Paper variant="outlined" className="filter-panel">{content}</Paper>;
}
