# Case Management

מערכת Case Management מקומית, בעברית וב־RTL, המבוססת על React, FastAPI ו־SQLite. אין צורך ב־Docker, PostgreSQL, MinIO או Mailpit להפעלה המקומית.

## התקנה ראשונה ב־Windows

דרישות: Windows 10/11, Python 3.12 ומעלה, Node.js 22 ומעלה ו־npm.

```powershell
cd C:\projects\Case_Management
powershell -ExecutionPolicy Bypass -File .\scripts\setup-local.ps1
```

הסקריפט יוצר virtual environment, מתקין dependencies, מריץ Alembic ו־Seed ומתקין את ה־frontend.

## הפעלה

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-local.ps1
```

המערכת תיפתח ב־http://localhost:3000. ה־API זמין ב־http://localhost:8000 ו־Swagger ב־http://localhost:8000/docs.

**Do not open apps/web/index.html directly.** זוהי אפליקציית Vite ויש להפעיל אותה דרך הסקריפט.

עצירה:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\stop-local.ps1
```

## בסיס הנתונים וגיבוי

הנתונים נשמרים באופן קבוע בקובץ `data\case_management.db`. כאשר המערכת סגורה ניתן לגבות אותה באמצעות העתקת הקובץ למיקום בטוח. ההפעלה אינה מוחקת נתונים.

איפוס מפורש של נתוני Development, עם בקשת אישור:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\reset-development-data.ps1
```

Migration `0001` הוחלפה בשלב היסוד ב־migration מפורשת וניידת ל־SQLite; אין בסיס נתונים קודם שנדרש לשמר.

## משתמשי Development

- `admin@example.com` / `Admin123!`
- `requester@example.com` / `Requester123!`
- `agent@example.com` / `Agent123!`

סיסמאות אלה מיועדות לפיתוח מקומי בלבד.

## בדיקות

```powershell
cd apps\api
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\mypy.exe app
.\.venv\Scripts\pytest.exe
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\alembic.exe check

cd ..\web
npm run lint
npm run typecheck
npm test
npm run build
```

PostgreSQL נשאר יעד עתידי אופציונלי: `pip install -e ".[postgres]"`. Docker Compose נשמר עבור deployment מלא, אך אינו חלק מזרימת ההפעלה המקומית.

ראו `docs/architecture/overview.md` ו־`docs/adr/` להחלטות הארכיטקטורה.
