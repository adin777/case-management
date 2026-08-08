# Case Management API Specification

גרסה 0.1 — Living Specification. מסמך זה הוא מקור האמת לחוזה ה־API, ויש לעדכנו יחד עם
המימוש ובדיקות החוזה בכל שינוי מהותי.

## עקרונות

- Base URL מקומי: `http://localhost:8000/api`; הממשק: `http://localhost:3000`.
- ברירת המחדל היא JSON UTF-8. אימות והרשאה נאכפים בשרת.
- Environment הוא גבול הרשאה וקונפיגורציה. ערכים עסקיים מגיעים מה־DB ולא מקוד קשיח.
- IDs הם מפתחות טכניים יציבים; labels בעברית ניתנים לעריכה.
- מחיקה פיזית מותרת רק ללא תלויות; אחרת מוחזר `409` ומוצעת השבתה.
- שינויים עסקיים משמעותיים נרשמים ב־Audit.

הסימונים במסמך: **קיים**, **קיים/להרחבה**, **יעד**.

## Authentication

| סטטוס | Method | Endpoint |
|---|---|---|
| קיים | POST | `/api/auth/login` |
| קיים | GET | `/api/auth/me` |
| קיים | POST | `/api/auth/register` |
| יעד | POST | `/api/auth/refresh` |
| יעד | POST | `/api/auth/logout` |

## משתמשים, קבוצות והרשאות

קיימים/להרחבה: `GET/POST /api/users`, `PATCH /api/users/{id}`, `GET /api/groups`.
יעד: מחיקה בטוחה, חברות במספר קבוצות, העתקת קבוצות והרשאות ו־effective access מוסבר.
סדר ההכרעה: חריגת משתמש בסביבה, קבוצות בסביבה, חריגה כללית, קבוצות כלליות, none.
מנהל מערכת מקבל edit בכל domain אך אינו עוקף כלל עסקי כגון זהות מאשר.

## סביבות

| סטטוס | Method | Endpoint |
|---|---|---|
| קיים | GET/POST | `/api/environments` |
| קיים | PATCH | `/api/environments/{environment_id}` |
| יעד | DELETE | `/api/environments/{environment_id}` |
| קיים | GET | `/api/case-creation/environments` |

עדכון `is_active` משפיע רק על Path ID. סביבה לא פעילה אינה מוצעת ליצירה אך נשארת
קריאה בהיסטוריה.

## סוגי קריאה ומקורות יצירה

`GET /api/request-types?environment_id={id}&active_only=true` מחזיר רק RequestType פעילים
השייכים לסביבה. התצוגה היא `name_he` והערך הנשמר הוא `id`.

קיימים: `POST /api/request-types`, `PATCH /api/request-types/{id}` ו־
`GET /api/request-types/{id}/case-config`. יעד: מחיקה בטוחה ו־reorder.

`GET /api/environments/{id}/priorities` ו־`GET /api/environments/{id}/sub-priorities`
הם מקורות האמת לערכים בסביבה; ה־UI מציג רק פעילים ושומר UUID. סטטוסים לפתיחה מגיעים
מ־`case-config`. שינוי סביבה מאפס Request Type, Status, Priority, Sub-priority וערכי שדות.

## שדות וטפסים

שדות הליבה הם Environment, Subject, Description, Request Type, Status, Priority ו־Sub-priority.
טופס דינמי הוא אופציונלי: סוג קריאה ללא שדות נוספים רשאי ליצור Case עם `values: []`.
כאשר קיים טופס, רק שדות פעילים השייכים אליו מתקבלים והחובה נאכפת בשרת.

## Workflow

- `GET /api/cases/{id}/status-options`: כל הסטטוסים הפעילים עם `current`, `allowed`, `reason`.
- `GET /api/cases/{id}/allowed-transitions`: מעברים חוקיים.
- `POST /api/cases/{id}/transitions`: ביצוע מעבר חוקי בלבד.

## Cases

קיימים `GET/POST /api/cases`, `GET/PATCH /api/cases/{id}`, assign ו־lock.
יצירה מקבלת IDs מנוהלים בלבד:

```json
{
  "environment_id": "uuid",
  "request_type_id": "uuid",
  "title": "בעיה בהזמנה",
  "description": "תיאור מלא",
  "workflow_status_id": "uuid",
  "priority_id": "uuid",
  "sub_priority_id": "uuid-or-null",
  "participant_ids": [],
  "values": []
}
```

Request Type, Priority, Sub-priority, Workflow Status ושדות דינמיים חייבים להשתייך לסביבה
ולטופס הרלוונטיים. הפרה מחזירה `422` עם הודעה עסקית. מותר ליצור מספר בלתי מוגבל של
קריאות בעלות אותם ערכים עסקיים; הזהויות הייחודיות היחידות הן `Case.id` ו־`case_number`.
עדכון inline משתמש ב־`PATCH` וב־`version`; conflict מחזיר `409`.

## משתתפים, תגובות ואישורים

- `GET/POST /api/cases/{id}/participants`; `DELETE /api/cases/{id}/participants/{user_id}`.
- `include_participating=false` כברירת מחדל; `true` אינו עוקף הרשאת צפייה.
- תגובות ציבוריות והודעות מנהלים מופרדות והרשאת visibility נאכפת בשרת.
- החלטת אישור: `POST /api/approval-tasks/{task_id}/decision`. רק המאשר של task פעיל רשאי
  להחליט; מנהל מערכת אינו מאשר במקום אדם אחר.

## אוטומציות, דוחות וקבצים

Automation שומר IDs של שדות וערכים מנוהלים ומספק execution log. `GET /api/reports/cases`
ו־`GET /api/reports/cases/export`
משתמשים באותה שאילתה מורשית, עם pagination, filtering, sorting ו־include_participating.
Attachments עוברים בדיקות הרשאה, סוג, גודל ושם בטוח ונמחקים לוגית.

## Branding ו־Audit

יעד: `GET /api/system/branding`, העלאה והסרת logo. הקובץ נשמר באחסון מקומי ולא ב־DB או Git.
Audit הוא append-only ושומר actor, environment, before/after ו־timestamp.

## שגיאות

פורמט מועדף:

```json
{"code":"RESOURCE_IN_USE","message":"לא ניתן למחוק: הערך נמצא בשימוש.","details":{}}
```

`400` בקשה עסקית לא תקינה; `401` לא מחובר; `403` אסור; `404` לא נמצא; `409` conflict;
`422` validation; `500` תקלה בלתי צפויה. אין לחשוף SQL או stack trace. `IntegrityError`
בלתי צפוי אינו מתורגם אוטומטית ל־duplicate; unique עסקי צפוי נבדק בשירות ומוחזר כ־409.

## Health ותהליך שינוי

`GET /health` מחזיר `{"status":"healthy"}`. כל Endpoint או שינוי חוזה מחייב עדכון מסמך,
מימוש, API contract test ו־regression test באותו commit. יש לבדוק success, validation,
forbidden ו־not found, ולוודא שה־UI צורך אותו מקור אמת.
