import { Component, type ErrorInfo, type ReactNode } from 'react';
import { Alert, Box, Button, Stack, Typography } from '@mui/material';

type Props = { children: ReactNode };
type State = { error: Error | null };

export class AppErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    if (import.meta.env.DEV) console.error('Unexpected render error', error, info.componentStack);
  }

  private retry = () => {
    this.setState({ error: null });
  };

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <Box component="main" sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center', p: 3 }}>
        <Stack spacing={2} sx={{ width: '100%', maxWidth: 520 }}>
          <Typography variant="h4">אירעה שגיאה בהצגת המסך</Typography>
          <Alert severity="error">לא ניתן היה להציג את התוכן. אפשר לנסות שוב ללא אובדן המידע שנשמר.</Alert>
          <Button variant="contained" onClick={this.retry}>ניסיון חוזר</Button>
        </Stack>
      </Box>
    );
  }
}
