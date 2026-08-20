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
`GET /api/access/subjects/{subject_type}/{subject_id}/matrix` מחזיר לכל תחום
`domain_code`, `domain_name`, `default_level`, `direct_level`, `effective_level`, `source`
ו־`can_override`. קבוצת Admin מזוהה רק באמצעות `is_system_admin_group`; ללא Override היא
מקבלת `default_level=edit`, `direct_level=inherit`, `effective_level=edit` ו־
`source=admin_group_default`. Override מפורש (`none`, `view`, `edit`) גובר על ברירת המחדל,
ושמירת `inherit` מוחקת אותו ומחזירה את ברירת המחדל.
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

`GET /api/case-creation/environments/{environment_id}/configuration` דורש `case.create`
ומחזיר מקור קריאה מצומצם לקריאה בלבד: סוגי קריאה פעילים, שדות גלובליים פעילים ומוצגים,
טופס דינמי ומשתתפים זכאים רק כאשר קיימת הרשאת ניהול
משתתפים. הנתיב אינו מעניק הרשאת יצירה, עריכה או מחיקה של Configuration. מסך פתיחת
קריאה צורך רק נתיב זה, והשרת מאמת שוב את אותם IDs בעת `POST /api/cases`.

הרשאה לפעולה עסקית כוללת קריאה מצומצמת של ערכי הקונפיגורציה הנדרשים להשלמתה;
`case.create` אינו מחייב ואינו מעניק `request_type.manage` או `environment.manage`.

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
  "participant_ids": [],
  "values": [{"field_definition_id":"uuid","value":"..."}]
}
```

Request Type ושדות דינמיים חייבים להשתייך לסביבה
ולטופס הרלוונטיים. הפרה מחזירה `422` עם הודעה עסקית. מותר ליצור מספר בלתי מוגבל של
קריאות בעלות אותם ערכים עסקיים; הזהויות הייחודיות היחידות הן `Case.id` ו־`case_number`.
עדכון inline משתמש ב־`PATCH` וב־`version`; conflict מחזיר `409`.
`request_type_id` ניתן לעדכון רק לסוג פעיל באותה סביבה. שינוי נשמר ללא אובדן ערכים רק
כאשר ה־Form וה־Workflow תואמים; אחרת מוחזר `409` ונדרש תהליך המרה מפורש.

## משתתפים, תגובות ואישורים

- `GET/POST /api/cases/{id}/participants`; `DELETE /api/cases/{id}/participants/{user_id}`.
- `include_participating=false` כברירת מחדל; `true` אינו עוקף הרשאת צפייה.
- `GET/POST /api/cases/{id}/public-comments` מיועד לשיחה הציבורית של בעלי גישה לקריאה.
- `GET/POST /api/cases/{id}/manager-comments` מותרים רק ל־System Admin או למשתמש בעל
  `EnvironmentMembership.is_environment_manager=true` בסביבת הקריאה. Permission כללית אינה מספיקה.
- תגובות ציבוריות והודעות מנהלים נשמרות ומוחזרות בנפרד; הרשאת visibility נאכפת בשרת
  ואינה תלויה בהסתרת רכיבים ב־UI.
- החלטת אישור: `POST /api/approval-tasks/{task_id}/decision`. רק המאשר של task פעיל רשאי
  להחליט; מנהל מערכת אינו מאשר במקום אדם אחר.
- `GET /api/approvals/pending-for-me` מחזיר רק משימות פעילות בשלב הפעיל של המשתמש המחובר.
- נעילה ושחרור נעילה מותרים רק למנהל מערכת או למנהל סביבה מפורש באותה סביבה.
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

כל `HTTPException` עסקי מוחזר במעטפה יציבה הכוללת `code`, ‏`message` ו־`details`.
שגיאת validation של סכימת בקשה מחזירה `code=FIELD_REQUIRED` ומערך `errors`. ה־Frontend
מתרגם לפי `code` לשפה הפעילה ואינו מציג הודעות FastAPI/Pydantic גולמיות.

## Health ותהליך שינוי

`GET /health` מחזיר `{"status":"healthy"}`. כל Endpoint או שינוי חוזה מחייב עדכון מסמך,
מימוש, API contract test ו־regression test באותו commit. יש לבדוק success, validation,
forbidden ו־not found, ולוודא שה־UI צורך אותו מקור אמת.

## מחזור חיי משתמשים וספר ארגוני

`GET /api/users` מחזיר משתמשים פעילים כברירת מחדל. הפרמטר `active_only=false` מאפשר לכלול משתמשים לא פעילים ובארכיון; ניתן לסנן גם באמצעות `status_filter`, `source`, `department`, `job_title` ו־`search`. `POST /api/users` יוצר משתמש ידני ו־`PATCH /api/users/{user_id}` מעדכן פרטים ארגוניים או מצב `active`, `inactive`, `archived`. השבתה או העברה לארכיון אינה מוחקת היסטוריה, ומשתמש שאינו פעיל אינו יכול להתחבר או לקבל משימת אישור חדשה.

שיוך משתמש לסביבה אינו כולל Role: `PUT /api/users/{user_id}/environment-memberships` מקבל מערך של `{environment_id}`, ו־`POST /api/environments/{environment_id}/memberships` מקבל משתמש או קבוצה ללא `role_id`. שיוך משתמש מפורש כולל `is_environment_manager`; ניתן לעדכנו ב־`PATCH /api/environments/{environment_id}/memberships/{membership_id}`. נתיבי `/api/roles` ו־`/api/groups/{group_id}/roles` הם מורשת מושבתת ומחזירים `410`; הרשאות נפתרות מקבוצות, רמות גישה וחריגות משתמש בלבד.

Excel: `GET /api/users/import/template` מוריד תבנית; `POST /api/users/import/preview` מקבל הן
את כותרות התבנית הידידותיות והן את סכימת ה־snake_case המלאה של `GET /api/users-export`.
ה־Preview מחזיר לכל שורה פעולה, `changed_fields`, ‏warnings ו־errors ללא כתיבה.
עמודות התאריכים ו־`source` הן לקריאה בלבד; `Groups` ו־`Environments` מוחלים רק כאשר
הערכים כבר קיימים, ואחרת מוחזרת שגיאת Preview ברורה. `POST /api/users/import/apply`
מחיל snapshot מאושר. כל קובץ Export ניתן לייבוא חוזר ללא שינוי (round-trip). קריאה וכתיבה
של XLSX מבוצעות באמצעות `openpyxl`, ללא parsing ישיר של worksheet XML.

ביצירת משתמש ידני `email` הוא מזהה הכניסה. `user_principal_name` אופציונלי; כאשר הוא ריק השרת שומר בו את כתובת ה-email המנורמלת. `display_name` ו-email תקין הם חובה, וסיסמה ידנית חייבת לכלול לפחות 8 תווים.

Directory: `GET /api/directory/status` מחזיר מצב וריצה אחרונה. `POST /api/directory/{name}/test` בודק ספק ומחזיר `ok`, הודעה ומערך `steps` של `{code,label,ok,message}` ללא Secrets; Entra בודק Configuration, Tenant, Client, קיום Secret, Token, Graph ו־Users endpoint, ו־AD מקומי בודק Server, Base DN, Bind, חיבור LDAP/LDAPS ושאילתת משתמש. `POST /api/directory/{name}/preview` מבצע קריאה ללא שינוי נתונים. `POST /api/directory/apply` מחיל snapshot שאושר ושומר `DirectorySyncRun`; `GET /api/directory/runs` מחזיר יומן ריצות. הספקים הם `fake`, `entra`, `active_directory`. Entra משתמש ב־Graph `/users/delta` ושומר deltaLink לריצה הבאה. `directory_enabled` נפרד ממצב מקומי, ולכן Sync אינו מפעיל מחדש משתמש שהושבת או הועבר לארכיון ידנית.

## כללי שיוך ואישור לפי תפקיד ארגוני

`GET /api/environments/{environment_id}/assignment-rules` מחזיר כללים; `POST /api/environments/{environment_id}/assignment-rules/preview` מחזיר התאמות ללא כתיבה; `POST /api/environments/{environment_id}/assignment-rules` יוצר ומחיל כלל; `PUT /api/environment-assignment-rules/{rule_id}` מעדכן ומחיל אותו. תנאים בתוך כלל הם AND וכללים שונים הם OR. כלל מסיר רק membership שמקורו `rule` ובאותו `source_rule_id`, ולעולם אינו מסיר שיוך ידני.

`GET /api/environment-assignment-options` מחזיר Selectors בלבד מתוך משתמשים וקבוצות
פעילים ומערכי Department/Job Title הייחודיים הקיימים. ערכים מרובים באותו ממד הם OR;
ממדים שונים הם AND. Preview מחזיר את המשתמשים המדויקים לפני Apply.

שלב Approval מסוג `job_title` שומר את ערך התפקיד הארגוני ומייצר snapshot של כל המשתמשים הפעילים, החברים בסביבת הקריאה ובעלי אותו `job_title`. החלטת המשתמש הראשון משלימה את השלב ומבטלת את יתר המשימות. אם אין התאמה, יצירת המשימות נכשלת ב־`409` עם שגיאת קונפיגורציה ברורה.

## דוחות, שיוך ואישור תפעולי

`GET /api/reports/available` מחזיר רק דוחות שהמשתמש מורשה לראות. מרכז הדוחות כולל דוח קריאות (`report.cases`), אישורים (`report.approvals`), משתמשים והרשאות (`report.users`) ו־Audit (`report.audit`). `GET /api/reports/approvals`, ‏`/reports/users` ו־`/reports/audit` מחזירים נתוני אמת מה־Database ואוכפים את Permission Domain המתאים בשרת.

דוח הקריאות משתמש ב־`workflow_status_id` וב־`WorkflowStatus.label_he` כמקור האמת היחיד לתצוגה, סינון, מיון וייצוא. `sort` תומך ב־`case_number`, `title`, `environment`, `request_type`, `status`, `priority`, `requester`, `assignee`, `created_at`, `updated_at`; `direction` הוא `asc` או `desc`, והמיון מתבצע בשרת לפני pagination.

`GET /api/environments/{environment_id}/eligible-assignees` מחזיר רק משתמשים פעילים בעלי שיוך פעיל לסביבה ודורש `case.assign`. `POST /api/cases/{case_id}/assign` מקבל `assignee_id` או `null` ו־`version`. בקריאה נעולה רק System Admin או Environment Manager מפורש של אותה סביבה רשאי לשנות מטפל. בהתאם לכך, `GET /api/cases/{case_id}` מחזיר `permissions.can_assign=false` למשתמש רגיל גם אם הוקצתה לו הרשאת `case.assign`.

`GET /api/cases/{case_id}/approvals` מחזיר לכל משימה מספר ושם שלב, סוג מאשר, snapshot של שם המאשר, מצב, מועד בקשה, החלטה, מועד החלטה והערה. שם המאשר נשמר בעת יצירת המשימה ואינו משתנה בעקבות שינוי עתידי בפרופיל.

## ניסיונות אישור, העברת משתמשים וסידור ערכים

## העברת קריאה בין סביבות

- `GET /api/cases/{case_id}/transfer-preview?target_environment_id={id}` דורש `case.transfer_environment` הן במקור והן ביעד ומחזיר סוגי קריאה פעילים, משתתפים ומטפל שיוסרו ושדות המקור.
- `GET /api/cases/{case_id}/transfer-requirements?request_type_id={id}` מחזיר סטטוס התחלתי, מיפויי שדות לפי `key` יציב וסוג תואם, שדות שיוסרו ושדות יעד נדרשים.
- `POST /api/cases/{case_id}/transfer` מקבל `target_environment_id`, `target_request_type_id`, `priority_id`, `sub_priority_id`, `assignee_id`, `new_field_values` ו־`reason`.
- השרת מאמת מחדש את כל מזהי היעד ואינו סומך על ה־Preview. הפעולה אטומית: כשל מבטל את כל השינויים.
- מספר הקריאה, Reporter, Requester, תגובות וקבצים נשמרים. שיוכי שדות, משתתפים ומטפל שאינם תקפים ביעד מוסרים מן הקריאה הפעילה ונשמרים ב־`CaseTransferHistory` וב־Audit.
- Approval פעיל מבוטל עם `environment_transfer`; תצורת אישור ו־SLA של היעד מאותחלות מחדש. נעילה נעקפת רק בידי מנהל מורשה.

## מאגר ידע סביבתי

- `GET/POST /api/environments/{environment_id}/knowledge/documents` דורשים בהתאמה `knowledge.read` או `knowledge.manage`. העלאה תומכת ב־PDF, DOCX, XLSX, TXT ו־MD, שומרת את הקובץ מחוץ ל־Git ומאנדקסת chunks מבודדים לסביבה.
- `GET /api/environments/{environment_id}/knowledge/documents/{document_id}/download` דורש `knowledge.read`.
- `POST /api/environments/{environment_id}/knowledge/documents/{document_id}/reindex` מפעיל מחדש חילוץ ואינדוקס ודורש `knowledge.manage`.
- `PATCH /api/environments/{environment_id}/knowledge/documents/{document_id}/active?enabled={boolean}` משבית או מפעיל גרסה בלי למחוק היסטוריה ודורש `knowledge.manage`.
- `POST /api/environments/{environment_id}/knowledge/documents/{document_id}/reindex` ו־`PATCH .../active?enabled=` דורשים `knowledge.manage`.
- `POST /api/environments/{environment_id}/knowledge/query` דורש `knowledge.query`, מקבל `{question}` ומחזיר `{answer, sources, provider}`. מקורות כוללים מסמך, section אם קיים ו־chunk index.
- גרסה חדשה בעלת אותו שם משביתה את הגרסה הקודמת; רק מסמכים פעילים במצב `ready` משתתפים בשליפה.
- `GET /api/system/ai-settings` זמין למנהל מערכת ומחזיר רק provider/model ומצב `api_key_configured`; הוא לעולם אינו מחזיר Secret. בהיעדר Secret Store המפתח מוגדר רק באמצעות `OPENAI_API_KEY` בצד השרת.
- `LLMProvider` ו־`EmbeddingProvider` הם ממשקים נפרדים. ברירת המחדל המקומית אינה מבצעת קריאת API ואינה גוררת חיוב.
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

## סביבות, עובדים וסטטוסים פשוטים

- `POST /api/environments` מקבל `name_he`, ‏`name_en` ו־`description` בלבד. `code` שנשלח בידי לקוח נזנח; השרת מקצה `system_number` רציף בפורמט `ENV-######` ומשתמש בו גם כמפתח הטכני התואם־לאחור.
- `POST /api/environments/{environment_id}/clone` דורש מנהל מערכת ומקבל שמות, תיאור ושני דגלים אופציונליים: `copy_memberships` ו־`copy_knowledge` (ברירת מחדל `false`). התגובה כוללת `environment` חדש ו־`summary`. תצורת סוגי הקריאה, טפסים, סטטוסים, עדיפויות, שדות, אוטומציות, אישורים ו־SLA מועתקת עם IDs ומספרים חדשים; Cases, תגובות, קבצים, היסטוריית אישורים, Audit ומספור אינם מועתקים.
- `Employee` הוא רשומת האדם הארגונית ו־`User.employee_record_id` הוא קישור יחיד אופציונלי לחשבון כניסה. יצירה ידנית, רישום, Import וסנכרון Directory יוצרים או מעדכנים את שתי הרשומות יחד. סדר ההתאמה הוא Directory Object ID, מספר עובד, UPN ולבסוף Email.
- `GET/POST/PATCH /api/user-fields` מנהלים הגדרות גלובליות (`scope=global`). `POST /api/environments/{environment_id}/user-field-definitions` יוצר הגדרה סביבתית (`scope=environment`) שאינה מוצגת בסביבה אחרת. השבתה אינה מוחקת `UserFieldValue` קיים.
- יצירת Request Type אינה דורשת `workflow_definition_id`. לכל סביבה נשמרת פנימית תצורת סטטוסים עם סטטוס התחלתי פעיל יחיד; Case חדש מקבל אותו אוטומטית. היעדר Workflow מפורש אינו מחזיר שגיאת "Workflow not configured".
- `GET /api/cases/{case_id}/allowed-transitions` ו־`status-options`: אם קיימים כללי מעבר פעילים הם נאכפים; אם אין כלל יוצא, כל סטטוס פעיל אחר מותר בכפוף ל־`case.change_status`.
- `POST /api/environments/{environment_id}/memberships` מקבל בדיוק אחד מבין `user_id` או `group_id`. כללי Department/Job Title מנוהלים דרך `/assignment-rules`; Preview מחזיר גם `matched` וגם רשימת `users`. חישוב מחדש מסיר רק Memberships שמקורם באותו כלל ולעולם לא Membership ידני.

### Transfer, reports and files

`GET /api/cases/{case_id}/transfer-requirements?request_type_id=...` הוא מקור האמת המשותף
ל־UI ולוולידציית ההעברה ומחזיר סטטוס התחלתי, שדות יעד, עדיפויות, תתי־עדיפויות ומטפלים
פעילים השייכים לסביבת היעד. שינוי סביבת היעד ב־UI מנקה את כל הבחירות התלויות.
`GET /api/cases/{case_id}` מחזיר גם `environment_name`; הסביבה אינה נערכת ישירות.

מסנן הסטטוס בדוח הקריאות שולח `workflow_status_id` יציב מתוך
`GET /api/reports/cases/value-sources`; ללא סביבה מוחזר איחוד הסטטוסים הפעילים מהסביבות
המורשות, ועם סביבה מוחזרים ערכיה בלבד. נתיבי `/api/reports/approvals`, `/users` ו־`/audit`
תומכים במסננים וב־pagination בצד השרת. דוח האישורים מחזיר `task_id` ו־`can_decide`
ומשתמש בנתיב ההחלטה המשותף `POST /api/approval-tasks/{task_id}/decision`.
מסנן הסביבה בדוח הקריאות אופציונלי. ללא סביבה הדוח והייצוא מחזירים את איחוד השורות
הנראות למשתמש לפי `CaseVisibilityService`; אותו שירות נאכף גם ב־`GET /api/cases` ובגישה ישירה.
נראות מתקבלת ליוצר, למבקש, למטפל, למשתתף או לבעל `case.read`/`case.read_environment` בסביבה.
`GET /api/cases/workspace/query` משתמש אף הוא ב־`CaseVisibilityService`. System Admin מקבל את
כל הקריאות; Reporter, Requester ו־Assignee מוצגים תמיד, בעוד `include_participating` קובע רק
אם להוסיף קריאות שבהן המשתמש הוא Participant בלבד. קריאה פעילה ללא `workflow_status_id`
אינה נעלמת בגלל ערך `NULL`.

`GET /api/reports/filter-options` מחזיר מקורות אמת משותפים למסנני הדוחות: סביבות, סוגי
קריאה עם סביבת האב, משתמשים פעילים, קבוצות פעילות, מחלקות, תפקידים ארגוניים, סטטוסי אישור
ושלבי אישור. דוח האישורים מציג `can_decide` ומשתמש ב־`POST /api/approval-tasks/{id}/decision`;
דחייה מחייבת `comment`, ואישור מאפשר הערה אופציונלית.

קבצים מצורפים מאומתים לפי שם, סיומת חסומה, MIME וגודל configurable. הרשימה המותרת
כוללת מסמכים, קובצי נתונים, תמונות, ארכיונים ודואר נתמכים; קובצי הרצה נדחים תמיד.
האחסון מחוץ ל־web root והורדה מתבצעת רק דרך API מורשה. תמיכה כ־Attachment אינה
מבטיחה תמיכה ב־Knowledge ingestion, שממשיך להחזיק רשימת extractors מצומצמת ובטוחה.
מחזור חיי סביבה מנוהל בנתיבים מפורשים: `POST /api/environments/{id}/archive` משבית
סביבה ושומר את הקריאות וההיסטוריה, ו־`POST /api/environments/{id}/restore` משחזר אותה.
`GET /api/environments/{id}/delete-impact` ו־`DELETE /api/environments/{id}?confirmation=<name>`
דורשים `environment.delete`. מחיקה פיזית מותרת רק כאשר אין קריאות או תלויות ודורשת
הקלדת שם מדויקת; אחרת מוחזר `409` עם ספירת התלויות ואין Cascade שקט.

### Environment assignment options

`GET /api/environment-assignment-options` מחזיר למנהל מערכת `users`, `groups`,
`departments` ו־`job_titles`. משתמשים וקבוצות מוחזרים כפריטי `id`/`label`; מחלקות
ותפקידים ארגוניים הם ערכים ייחודיים ולא ריקים מרשומות `Employee` פעילות בלבד.
כללי שיוך מקבלים ערך יחיד או מערך ערכים עבור `user_id`, `group_id`, `department`
או `job_title`. תצוגה מקדימה מחזירה לכל משתמש שם, דוא״ל, מחלקה ותפקיד, והחלה
מתבצעת רק לאחר בקשת יצירה מפורשת.

### UI failure handling

כשל בטעינת `transfer-preview` או `transfer-requirements`, לרבות payload חסר או
מערכים שאינם תקינים, מוצג כהודעת שגיאה ואינו מפיל את מסך React. הלקוח מנרמל את
מערכי הדרישות לערכים ריקים בטוחים ומציג מצב טעינה בכל מעבר. חריגת render בלתי
צפויה נתפסת ב־Error Boundary ברמת האפליקציה ומציעה ניסיון חוזר.

### Dynamic global case fields

Database חדש מתחיל ללא הגדרות שדות גלובליים. `GET/POST /api/global-case-fields`,
`PATCH/DELETE /api/global-case-fields/{id}` ו־`PUT /api/global-case-fields/order` מנהלים
Definitions דינמיים. סוגי השדות הם `text`, `textarea`, `number`, `date`, `datetime`,
`boolean`, `single_select`, `multi_select`, `user`, `email`, `url`; ה־key וה־IDs נוצרים
בשרת. מחיקה של שדה בשימוש מחזירה `409`, והשבתה שומרת ערכים היסטוריים.

לשדות בחירה קיימים `POST/PATCH/DELETE /api/global-case-fields/{field_id}/options[/{option_id}]`
ו־`PUT /api/global-case-fields/{field_id}/options/order`. ערך בשימוש אינו נמחק פיזית.
`PUT /api/environments/{environment_id}/global-case-fields/{field_id}/visibility?is_visible=`
שומר חריגת נראות; בהיעדר row ברירת המחדל היא מוצג. שדה לא פעיל לעולם אינו מוחזר כגלוי.

`GET /api/environments/{environment_id}/case-fields?request_type_id=` הוא מקור האמת המאוחד
ומחזיר `{global_fields, environment_fields}` לפי פעילות, נראות, סדר והרשאה. הוא משמש
לפתיחה, פרטי קריאה, העברה ודוחות. `GET/PUT /api/cases/{case_id}/global-field-values`
קורא ושומר ערכים; עדכון דורש `case.update`, מכבד נעילה ומאמת שהשדה פעיל וגלוי בסביבה.

### Subject access matrix

`GET /api/access/subjects/{user|group}/{id}/matrix?environment_id=` מחזיר View Model
אחיד לכל Permission Domain: `domain_code`, `domain_name`, `direct_level`,
`effective_level`, `source`, `scope`, `description`, `can_override`. עבור System Admin כל תחום מוחזר
כ־`edit`, המקור הוא „מנהל מערכת” ו־`can_override=false`; אין צורך ליצור Assignment rows.
חבר בקבוצה המסומנת `is_system_admin_group=true` מקבל באותו אופן `edit` לכל Domain קיים
או עתידי, עם מקור „קבוצת Admin”, ללא Assignment rows וללא אפשרות Override בקבוצה זו.

### Operational reports

`GET /api/reports/approvals`, `/users` ו־`/audit` מבצעים סינון, מיון ו־pagination
בשרת. הפרמטרים המשותפים הם `page`, `page_size`, `sort`, `direction`. דוח אישורים
תומך במספר קריאה, נושא, סביבה, סוג קריאה, מאשר, סטטוס, שלב וטווחי תאריכי בקשה/החלטה;
החלטה מתבצעת דרך `POST /api/approval-tasks/{id}/decision` ודחייה מחייבת הערה. דוח
משתמשים תומך במסננים נפרדים `name`, `email`, `username`, וב־`search` התואם לאחור,
וכן במצב, מקור, מחלקה, תפקיד, `group_ids` וסביבה. דוח Audit
תומך במשתמש, משתמש אפקטיבי בהתחזות, פעולה, ישות, Entity ID, סביבה, תאריכים וחיפוש.

### Semantic global fields and import snapshots

ל־Global Field קיים `semantic_binding` אופציונלי. `case.assignee` מותר רק לשדה `user`,
ורק שדה פעיל אחד יכול להחזיק אותו. ערכו ו־`Case.assignee_id` מסונכרנים דו־כיוונית,
והמשתמש נבדק מול רשימת המטפלים הפעילים והמשויכים לסביבה. תצורת שדה גלובלי בסביבה
כוללת `is_visible`, `is_required`, `show_on_create`, `show_on_edit`; שדה edit-only אינו
חוסם יצירה. `GET /api/environments/{id}/case-fields` תומך `presentation=create|edit`,
ו־`GET/PUT /api/environments/{id}/global-case-fields/configuration[/{field_id}]` מנהלים
את התצורה.

`POST /api/users/import/preview` מחזיר `import_session_id` ושומר snapshot מאושר.
`POST /api/users/import/apply` מקבל את המזהה ומחיל פעם אחת בלבד את אותו snapshot,
ללא parsing חוזר של תוכן שהלקוח יכול לשנות.
