# Product roadmap

## Completed in the current milestone

- Hebrew business permission domains with none/view/edit, bulk user/group assignment, active-state filtering, and audited copy modes.
- Safe local development-user cleanup with a verified SQLite backup and preserved audit identity snapshots.
- Header-level case-report filtering and sorting, including last update, creator, assignee, configured workflow status, and configured priority.
- Editable unlimited approval flows with user/group approvers, ordering, any/all/minimum-count rules, decision comments, notifications, and a durable approved state on the case.

## הושלם

- תשתית מקומית ב־SQLite עם Alembic, אימות משתמשים ו־RBAC רב־סביבתי.
- ניהול משתמשים, קבוצות, תפקידים, הרשאות ישירות והרשאות גורפות.
- סוגי קריאות, טפסים בגרסאות, שדות דינמיים, עדיפויות ותת־עדיפויות.
- יצירה, צפייה ועריכה של קריאות, משתתפים, תגובות ציבוריות/פנימיות ונעילה.
- אוטומציות בסיסיות, סבבי אישור, דוח קריאות וייצוא XLSX.
- מודל Workflow ניתן להגדרה, סטטוסים, מעברים והיסטוריית סטטוסים.
- מנוע מעבר חוקי עם בדיקת הרשאה, דרישת תגובה/פתרון, Audit והתראה.
- מדיניות SLA לפי סביבה, סוג קריאה ועדיפות, כולל סדר specificity ו־due dates.
- קבצים מצורפים באחסון מקומי עם allow-list, מגבלת גודל, checksum, הגנת נתיב ומחיקה לוגית.
- התראות בתוך המערכת ו־outbox לתשתית ערוצי הפצה עתידיים.
- migrations `0007` ו־`0008`; מסד הנתונים הקיים נשמר ללא reset.

## חלקי בשלב הנוכחי

- מסכי Workflow ו־SLA מציגים, יוצרים ומפעילים/משביתים הגדרות. עריכת סטטוסים ומעברים קיימת ב־API אך טרם הושלם עבורה עורך מלא בממשק.
- SLA מוצג בקריאה, אך מנגנון רקע לעדכון warning/breached טרם נוסף; החישוב מתעדכן בעת פעולות תפעוליות.
- קבצים ניתנים להעלאה ולהורדה מתוך הקריאה. Drag & Drop, progress מדויק וצירוף כחלק אטומי משליחת תגובה עדיין חסרים.
- התראות נוצרות במעבר סטטוס וניתנות לקריאה/סימון דרך API. עמוד/Drawer ופעמון עם badge טרם חוברו.
- Audit שומר before/after לפעולות החדשות, אך מסך `/admin/audit` המלא והרחבת כל אירועי ההתחברות טרם הושלמו.
- דוח הקריאות כולל pagination, פילטרים בסיסיים ו־XLSX; פילטרי SLA, אישורים ושדות דינמיים עדיין חלקיים.
- מסך הרשאות גורפות כולל בחירה מרובה, סינון פעילות ו־Dialog; pagination, tri-state מלא וסיכום הרשאות אפקטיביות לכל scope עדיין חלקיים.

## השלב הבא — עדיפות גבוהה

1. להשלים Workflow Builder מלא: עריכת סטטוסים/מעברים, סדר, צבע, שכפול ושיוך לסוג קריאה.
2. לחבר את מסך הקריאה למעברי Workflow החדשים ולהציג Timeline מלא עם שמות משתמשים וסטטוסים.
3. להשלים מרכז התראות, badge ואירועים עבור הקצאה, משתתף, תגובות ואישורים.
4. להשלים `/admin/audit` עם פילטרים, פירוט לפני/אחרי והרשאות system/environment.
5. להרחיב את דוח הקריאות לכל פילטרי SLA/אישור/נעילה/משתתף ושדות דינמיים.
6. להשלים עריכת סוג קריאה, קבוצה מטפלת ומשתתפים עם אזהרת שינוי טופס ללא אובדן נתונים.

## מגבלות ידועות

- חישובי SLA משתמשים בזמן קלנדרי; `business_calendar_id` נשמר כתשתית עתידית בלבד.
- ערוץ Email אינו שולח דואר אמיתי; ה־outbox נועד לחיבור ספק עתידי ללא סודות בקוד.
- האחסון המקומי מתאים לסביבת הפיתוח היחידה בלבד ואינו תחליף לאחסון אובייקטים בפריסה מבוזרת.
- חבילת ה־Frontend עדיין גדולה ומצריכה code splitting לפני production.
- קיימות אזהרות בדיקות לגבי מפתח JWT קצר בסביבת test ולגבי תאימות עתידית של TestClient; אין כשל בדיקות.

## איכות ואימות

- Backend: Ruff, mypy, Alembic check ו־31 בדיקות עוברות.
- Frontend: ESLint, TypeScript, 17 בדיקות ו־production build עוברים.
- Browser E2E: כניסה, שמירת session לאחר restart, Workflow ו־SLA אומתו ב־`http://localhost:3000/`.
