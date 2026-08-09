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
| קיים | GET | `/api/impersonation/status` |
| קיים | POST | `/api/impersonation/start` |
| קיים | POST | `/api/impersonation/stop` |
| יעד | POST | `/api/auth/refresh` |
| יעד | POST | `/api/auth/logout` |

## משתמשים, קבוצות והרשאות

קיימים/להרחבה: `GET/POST /api/users`, `PATCH /api/users/{id}`, `GET /api/groups`.
יעד: מחיקה בטוחה, חברות במספר קבוצות, העתקת קבוצות והרשאות ו־effective access מוסבר.
סדר ההכרעה: חריגת משתמש בסביבה, קבוצות בסביבה, חריגה כללית, קבוצות כלליות, none.
מנהל מערכת מקבל edit בכל domain אך אינו עוקף כלל עסקי כגון זהות מאשר.
התחזות דורשת `system.impersonate_users`, מנפיקה access token קצר־חיים לזהות היעד ואינה
מבצעת Login או שינוי סיסמה. ה־token שומר `real_actor_id`, וכל Audit בזמן התחזות שומר
`real_actor_user_id` ו־`impersonated_user_id` ב־metadata.

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

`PUT /api/environments/{id}/system-fields/{field_code}/reorder` מסדר באופן אטומי ערכי
Request Type, Status, Priority או Sub-priority באמצעות מערך IDs מלא של אותה סביבה.

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
- `POST /api/workflow-statuses/{id}/set-initial`: הגדרה אטומית של סטטוס פעיל כהתחלתי.

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
`request_type_id` ניתן לעדכון רק לסוג פעיל באותה סביבה. שינוי נשמר ללא אובדן ערכים רק
כאשר ה־Form וה־Workflow תואמים; אחרת מוחזר `409` ונדרש תהליך המרה מפורש.

## משתתפים, תגובות ואישורים

- `GET/POST /api/cases/{id}/participants`; `DELETE /api/cases/{id}/participants/{user_id}`.
- `include_participating=false` כברירת מחדל; `true` אינו עוקף הרשאת צפייה.
- `GET/POST /api/cases/{id}/public-comments` מיועד לשיחה הציבורית של בעלי גישה לקריאה.
- `GET /api/cases/{id}/manager-comments` דורש `comment.manager.read`; `POST` דורש
  `comment.manager.create`. הערוץ אינו נחשף כלל ב־UI ללא הרשאת הקריאה.
- תגובות ציבוריות והודעות מנהלים נשמרות ומוחזרות בנפרד; הרשאת visibility נאכפת בשרת
  ואינה תלויה בהסתרת רכיבים ב־UI.
- החלטת אישור: `POST /api/approval-tasks/{task_id}/decision`. רק המאשר של task פעיל רשאי
  להחליט; מנהל מערכת אינו מאשר במקום אדם אחר.
- `GET /api/approvals/pending-for-me` מחזיר רק משימות פעילות בשלב הפעיל של המשתמש המחובר.
- נעילה ושחרור נעילה מותרים רק למנהל מערכת או לבעל `environment.manage` באותה סביבה.
  בקריאה נעולה משתמש אחר מקבל `403` בעדכון שדות, סטטוס או משתתפים; תגובה ציבורית נשארת
  מותרת לפי הרשאת התגובה.

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

## מחזור חיי משתמשים וספר ארגוני

`GET /api/users` מחזיר משתמשים פעילים כברירת מחדל. הפרמטר `active_only=false` מאפשר לכלול משתמשים לא פעילים ובארכיון; ניתן לסנן גם באמצעות `status_filter`, `source`, `department`, `job_title` ו־`search`. `POST /api/users` יוצר משתמש ידני ו־`PATCH /api/users/{user_id}` מעדכן פרטים ארגוניים או מצב `active`, `inactive`, `archived`. השבתה או העברה לארכיון אינה מוחקת היסטוריה, ומשתמש שאינו פעיל אינו יכול להתחבר או לקבל משימת אישור חדשה.

שיוך משתמש לסביבה אינו כולל Role: `PUT /api/users/{user_id}/environment-memberships` מקבל מערך של `{environment_id}`, ו־`POST /api/environments/{environment_id}/memberships` מקבל משתמש או קבוצה ללא `role_id`. נתיבי `/api/roles` ו־`/api/groups/{group_id}/roles` הם מורשת מושבתת ומחזירים `410`; הרשאות נפתרות מקבוצות, רמות גישה וחריגות משתמש בלבד.

Excel: `GET /api/users/import/template` מוריד תבנית; `POST /api/users/import/preview` מקבל קובץ ומחזיר חדשים, לעדכון, ללא שינוי ושגיאות ללא כתיבה; `POST /api/users/import/apply` מחיל רק נתונים שאושרו; `GET /api/users-export` מייצא XLSX לפי מסנני מצב ומקור.

Directory: `GET /api/directory/status` מחזיר מצב וריצה אחרונה. `POST /api/directory/{name}/test` בודק ספק, ו־`POST /api/directory/{name}/preview` מבצע קריאה ללא שינוי נתונים. `POST /api/directory/apply` מחיל snapshot שאושר ושומר `DirectorySyncRun`; `GET /api/directory/runs` מחזיר יומן ריצות. הספקים הם `fake`, `entra`, `active_directory`. Entra משתמש ב־Graph `/users/delta` ושומר deltaLink לריצה הבאה. `directory_enabled` נפרד ממצב מקומי, ולכן Sync אינו מפעיל מחדש משתמש שהושבת או הועבר לארכיון ידנית.

## כללי שיוך ואישור לפי תפקיד ארגוני

`GET /api/environments/{environment_id}/assignment-rules` מחזיר כללים; `POST /api/environments/{environment_id}/assignment-rules/preview` מחזיר התאמות ללא כתיבה; `POST /api/environments/{environment_id}/assignment-rules` יוצר ומחיל כלל; `PUT /api/environment-assignment-rules/{rule_id}` מעדכן ומחיל אותו. תנאים בתוך כלל הם AND וכללים שונים הם OR. כלל מסיר רק membership שמקורו `rule` ובאותו `source_rule_id`, ולעולם אינו מסיר שיוך ידני.

שלב Approval מסוג `job_title` שומר את ערך התפקיד הארגוני ומייצר snapshot של כל המשתמשים הפעילים, החברים בסביבת הקריאה ובעלי אותו `job_title`. החלטת המשתמש הראשון משלימה את השלב ומבטלת את יתר המשימות. אם אין התאמה, יצירת המשימות נכשלת ב־`409` עם שגיאת קונפיגורציה ברורה.

## דוחות, שיוך ואישור תפעולי

דוח הקריאות משתמש ב־`workflow_status_id` וב־`WorkflowStatus.label_he` כמקור האמת היחיד לתצוגה, סינון, מיון וייצוא. `sort` תומך ב־`case_number`, `title`, `environment`, `request_type`, `status`, `priority`, `requester`, `assignee`, `created_at`, `updated_at`; `direction` הוא `asc` או `desc`, והמיון מתבצע בשרת לפני pagination.

`GET /api/environments/{environment_id}/eligible-assignees` מחזיר רק משתמשים פעילים בעלי שיוך פעיל לסביבה ודורש `case.assign`. `POST /api/cases/{case_id}/assign` מקבל `assignee_id` או `null` ו־`version`. בקריאה נעולה רק מנהל מערכת או בעל `environment.manage` רשאי לשנות מטפל.

`GET /api/cases/{case_id}/approvals` מחזיר לכל משימה מספר ושם שלב, סוג מאשר, snapshot של שם המאשר, מצב, מועד בקשה, החלטה, מועד החלטה והערה. שם המאשר נשמר בעת יצירת המשימה ואינו משתנה בעקבות שינוי עתידי בפרופיל.

## ניסיונות אישור, העברת משתמשים וסידור ערכים

`GET /api/cases/{case_id}/approvals` מחזיר אובייקט עם `current_approval`, ‏`approval_history`
ו־`can_resubmit`. לכל ApprovalInstance נשמר `attempt_number` מפורש. הרשימה הראשית מציגה רק את
הניסיון האחרון; ניסיונות קודמים נשארים כהיסטוריה עם Snapshot המאשר, החלטה, מועד וסיבת דחייה.
`POST /api/cases/{case_id}/approvals/resubmit` דורש `case.update`, זמין רק לאחר `rejected` או
`returned`, דוחה ניסיון כשכבר קיים אישור פעיל, ויוצר משימות חדשות מתצורת האישור הפעילה בלי למחוק היסטוריה.

`GET /api/users-export` מחזיר XLSX אמיתי ומכבד `status_filter`, ‏`source`, ‏`department`,
`job_title` ו־`search`. הקובץ כולל את כל שדות הפרופיל, תאריכי המערכת, קבוצות וסביבות.
`POST /api/users/import/preview` אינו כותב נתונים ומסווג יצירה, עדכון, ללא שינוי ושגיאה;
`POST /api/users/import/apply` מחיל רק את ה־snapshot שאושר. התאמה נעשית לפי
`directory_object_id`, לאחר מכן UPN ולבסוף Email, ללא יצירת משתמש כפול.

`PUT /api/environments/{environment_id}/system-fields/{field_code}/reorder` מקבל מערך IDs מלא
עבור Status, Request Type, Priority או SubPriority. ‏
`PUT /api/environments/{environment_id}/case-fields/{field_id}/options/reorder` מסדר אפשרויות של
שדה בחירה לפי הערכים היציבים שלהן. שני הנתיבים דוחים כפילויות, ערכים חסרים וערכים מהורה אחר.

מנהל מערכת מקבל `edit` באופן דינמי בכל PermissionDomain פעיל, כולל Domain שנוסף בעתיד, בלי ליצור
Assignment rows. התחזות דורשת `system.impersonate_users`; עצירה מחזירה token של המשתמש המקורי.
