import type { ReactNode } from 'react';
import { Box, Button, Drawer, Stack } from '@mui/material';
import { useTranslation } from 'react-i18next';

export function ResponsivePage({ children }: { children: ReactNode }) { return <Box sx={{ width: '100%', maxWidth: '100%', minWidth: 0 }}>{children}</Box>; }
export function MobileCardList({ children }: { children: ReactNode }) { return <Stack spacing={1.5} sx={{ display: { xs: 'flex', md: 'none' } }}>{children}</Stack>; }
export function ResponsiveTable({ table, cards }: { table: ReactNode; cards: ReactNode }) { return <><Box sx={{ display: { xs: 'none', md: 'block' } }}>{table}</Box><MobileCardList>{cards}</MobileCardList></>; }
export function ResponsiveFormGrid({ children }: { children: ReactNode }) { return <Box sx={{ display: 'grid', gridTemplateColumns: { xs: 'minmax(0,1fr)', sm: 'repeat(2,minmax(0,1fr))', lg: 'repeat(4,minmax(0,1fr))' }, gap: 2, '& .MuiInputBase-root': { minHeight: 44 }, '& > *': { minWidth: 0 } }}>{children}</Box>; }
export function FilterDrawer({ open, onClose, onReset, children }: { open: boolean; onClose: () => void; onReset: () => void; children: ReactNode }) {
  const { t } = useTranslation();
  return <Drawer anchor="bottom" open={open} onClose={onClose} PaperProps={{ sx: { borderRadius: '16px 16px 0 0', maxHeight: '88dvh', p: 2 } }}><Box sx={{ overflowY: 'auto', minHeight: 0 }}>{children}</Box><Stack direction="row" gap={1} pt={2} sx={{ borderTop: '1px solid', borderColor: 'divider', mt: 2, pb: 'env(safe-area-inset-bottom)' }}><Button fullWidth onClick={onReset}>{t('reports.reset')}</Button><Button fullWidth variant="contained" onClick={onClose}>{t('filters.showResults')}</Button></Stack></Drawer>;
}
export function MobileActionBar({ children }: { children: ReactNode }) { return <Stack direction="row" gap={1} sx={{ display: { md: 'none' }, position: 'sticky', bottom: 8, zIndex: 8, p: 1, mt: 2, borderRadius: '8px', bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', flexWrap: 'wrap', '& .MuiButton-root': { minHeight: 44, flex: '1 1 auto' } }}>{children}</Stack>; }
