import type { ReactNode } from 'react';
import { Box, Button, Drawer, Stack } from '@mui/material';

export function ResponsivePage({children}:{children:ReactNode}){return <Box sx={{width:'100%',maxWidth:'100%',overflowX:'clip'}}>{children}</Box>}
export function MobileCardList({children}:{children:ReactNode}){return <Stack spacing={1.5} sx={{display:{xs:'flex',md:'none'}}}>{children}</Stack>}
export function ResponsiveTable({table,cards}:{table:ReactNode;cards:ReactNode}){return <><Box sx={{display:{xs:'none',md:'block'}}}>{table}</Box><MobileCardList>{cards}</MobileCardList></>}
export function ResponsiveFormGrid({children}:{children:ReactNode}){return <Box sx={{display:'grid',gridTemplateColumns:{xs:'1fr',sm:'repeat(2,minmax(0,1fr))',lg:'repeat(4,minmax(0,1fr))'},gap:1.5,'& .MuiInputBase-root':{minHeight:44}}}>{children}</Box>}
export function FilterDrawer({open,onClose,onReset,children}:{open:boolean;onClose:()=>void;onReset:()=>void;children:ReactNode}){return <Drawer anchor="bottom" open={open} onClose={onClose} PaperProps={{sx:{borderRadius:'20px 20px 0 0',maxHeight:'88vh',p:2}}}><Box sx={{overflowY:'auto'}}>{children}</Box><Stack direction="row" gap={1} pt={2}><Button fullWidth onClick={onReset}>איפוס</Button><Button fullWidth variant="contained" onClick={onClose}>הצגת תוצאות</Button></Stack></Drawer>}
export function MobileActionBar({children}:{children:ReactNode}){return <Stack direction="row" gap={1} sx={{display:{md:'none'},position:'sticky',bottom:8,zIndex:8,p:1,borderRadius:3,bgcolor:'rgba(255,255,255,.96)',boxShadow:'0 10px 30px #172f5b24','& .MuiButton-root':{minHeight:44,flex:1}}}>{children}</Stack>}
