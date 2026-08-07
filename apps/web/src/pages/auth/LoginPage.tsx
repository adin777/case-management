import { FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { ApiError, getCurrentUser, login, token } from '../../api/client';

export function LoginPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [email, setEmail] = useState('admin@example.com');
  const [password, setPassword] = useState('Admin123!');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [apiStatus, setApiStatus] = useState('');

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setApiStatus('מתחבר לשרת...');
    setIsSubmitting(true);
    try {
      const result = await login(email, password);
      token.set(result.access_token, result.refresh_token);
      setApiStatus('מאמת משתמש...');
      const user = await getCurrentUser();
      queryClient.setQueryData(['me'], user);
      navigate('/', { replace: true });
    } catch (caught) {
      token.clear();
      console.error('Login failed', caught);
      if (caught instanceof ApiError) {
        if (caught.kind === 'credentials') setError('המייל או הסיסמה אינם נכונים');
        else if (caught.kind === 'network')
          setError('לא ניתן להתחבר לשרת המערכת. יש לבדוק שהשירות המקומי פועל.');
        else if (caught.kind === 'timeout')
          setError('אירעה שגיאת תקשורת. בדוק שהמערכת פועלת ב-http://localhost:8000');
        else setError(caught.message);
      } else setError('הכניסה נכשלה. פרטי השגיאה נרשמו בקונסול.');
      setApiStatus('');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Box className="login-art">
      <Card sx={{ width: { xs: '92%', sm: 460 }, p: 2 }}>
        <CardContent>
          <Box component="form" onSubmit={handleSubmit}>
            <Stack spacing={3}>
              <Typography variant="h4">מרכז השירות</Typography>
              <Typography color="text.secondary">ניהול פניות ותהליכי עבודה במקום אחד</Typography>
              {error && <Alert severity="error">{error}</Alert>}
              {apiStatus && <Alert severity="info">{apiStatus}</Alert>}
              <TextField
                label="דוא״ל"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                disabled={isSubmitting}
              />
              <TextField
                label="סיסמה"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    event.preventDefault();
                    event.currentTarget.closest('form')?.requestSubmit();
                  }
                }}
                disabled={isSubmitting}
              />
              <Button type="submit" size="large" variant="contained" disabled={isSubmitting}>
                {isSubmitting ? (
                  <>
                    <CircularProgress size={20} color="inherit" sx={{ ml: 1 }} />
                    מתחבר...
                  </>
                ) : (
                  'כניסה למערכת'
                )}
              </Button>
              <Typography textAlign="center">
                עדיין אין לך חשבון? <Link to="/register">הרשמה</Link>
              </Typography>
            </Stack>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
