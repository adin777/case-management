import { alpha, createTheme } from '@mui/material/styles';

export const appTheme = createTheme({
  direction: 'rtl',
  palette: {
    primary: { main: '#1d4ed8', dark: '#173b8f', light: '#dbeafe' },
    secondary: { main: '#0f766e' },
    background: { default: '#f3f6fb', paper: '#ffffff' },
    text: { primary: '#172033', secondary: '#61708a' },
  },
  typography: {
    fontFamily: 'Arial, "Noto Sans Hebrew", sans-serif',
    h4: { fontWeight: 850, letterSpacing: '-0.02em' },
    h5: { fontWeight: 800, letterSpacing: '-0.015em' },
    h6: { fontWeight: 750 },
    button: { fontWeight: 700, textTransform: 'none' },
  },
  shape: { borderRadius: 14 },
  components: {
    MuiCard: { styleOverrides: { root: { border: '1px solid #e1e7f0', boxShadow: '0 8px 28px rgba(24,45,82,.06)' } } },
    MuiButton: { defaultProps: { disableElevation: true }, styleOverrides: { root: { minHeight: 40, borderRadius: 10 } } },
    MuiTextField: { defaultProps: { variant: 'outlined' } },
    MuiOutlinedInput: { styleOverrides: { root: { backgroundColor: '#fff', '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: '#93a4bd' } } } },
    MuiChip: { styleOverrides: { root: { fontWeight: 700 } } },
    MuiTableHead: { styleOverrides: { root: { backgroundColor: alpha('#1d4ed8', .045) } } },
  },
});
