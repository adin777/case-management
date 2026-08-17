# AGENTS.md

## API CONTRACT RULE

`docs/api/API_SPEC.md` is the source of truth for the public/internal API contract.
Every feature or behavioral change that affects an endpoint, request, response, permission,
validation, filtering, domain value source, delete behavior, or workflow behavior must update:

1. `API_SPEC.md`.
2. Automated API contract tests.
3. Regression tests.
4. Implementation.

A feature is not Done when the implementation changed but the API contract/tests did not.
Every feature, bug fix, or behavioral change must add or update at least one regression test.
Bug fixes require a regression test that fails before the fix and passes after it.

Configurable fields are identified by stable IDs, never by labels. Business behavior attached
to a configurable field must use an explicit `semantic_binding`; no code may infer business
meaning from Hebrew or English labels. A Global Field may have environment-specific visibility,
requiredness, and create/edit presentation rules, consumed from the same configuration by the
backend and frontend. When a Preview flow exists, Apply must operate on exactly the previewed
snapshot and must have a permanent regression test.

A feature is broken when a displayed button has no observable effect, a mutation does not refresh
the UI, Preview works but Apply does not, the backend exposes `can_decide` without a frontend
action, or a semantic configurable field is ignored by its business consumer. Every reported
regression becomes permanent automated coverage.

After implementation, do not use an ad-hoc subset as final validation. Always run:
`powershell -ExecutionPolicy Bypass -File .\scripts\run-regression.ps1`.

## SIMPLE FIRST

כאשר פעולה יכולה להתבצע באופן ישיר וברור במסך, אין להוסיף שלב, Dialog, מצב עריכה או כפתור נוסף ללא צורך ממשי. שדה פשוט שניתן לעריכה יוצג כ־inline editable; אין להסתיר ערכים רלוונטיים או להוסיף ניווט כאשר הפעולה יכולה להתבצע במקום. לפני השלמת UI יש לשאול האם אפשר לבצע את אותה פעולה בפחות צעדים ולבחור בפתרון הפשוט יותר.

## NO HARDCODED CONFIGURATION

- אין להגדיר בקוד שדה עסקי גלובלי או סביבתי, אפשרות/ערך שדה, Status, Priority, SubPriority, Request Type, Department, Job Title, ערך אישור או תצורה עסקית אחרת.
- הקוד רשאי להגדיר רק סוגי שדות, metadata סמנטי ויכולות טכניות. כל Definition וכל Value עסקי מגיעים מה־Database ומנוהלים דרך UI/API.
- Database חדש וריק עולה עם אפס הגדרות שדות עסקיים וללא Seed עסקי.
- ישויות configurable חדשות נוצרות כתצורה שמורה ב־Database; Global Fields הם Definitions דינמיים ואינם constants בקוד.
- קובץ שהמערכת מייצאת ומיועד לעריכת משתמש חייב לתמוך ב־Round-trip Import דרך אותו חוזה מנורמל.
- מנהלי מערכת וחברי קבוצת Admin מסומנת מקבלים `edit` אוטומטי בכל Permission Domain קיים ועתידי, בלי Assignment rows לכל Domain.
- פעולת שמירה אינה נחשבת הצלחה עד ש־GET חדש מחזיר את הערך שנשמר.

## מקורות אמת ותלויות UI

An option displayed to a user must be valid for submission. UI option sources and backend validation must use the same domain service/source of truth.

Permission to perform a business action includes read access to the configuration values required to complete that action.

לכל Select יש מקור אמת מפורש: סביבה מתוך Environments; סוג קריאה מתוך RequestTypes של הסביבה שנבחרה; סטטוס מתוך ה־Workflow של הסביבה; עדיפות ותת־עדיפות מתוך ערכי הסביבה; משתמשים מתוך משתמשים פעילים ומורשים. אין לעשות reuse למערך אחר רק משום שהמבנה דומה.

לפני השלמת UI שתלוי בבחירה אחרת יש לבדוק בפועל את ה־IDs ואת התוויות שה־API מחזיר. שינוי בתחום configurable חייב להיבדק בכל הצרכנים שלו: הגדרות, יצירה, פרטי קריאה, Workflow, Automation, דוחות, Dashboard ומסננים.

## שער איכות חזותי

משימת UI אינה גמורה כאשר הפריסה שטוחה או מבלבלת, הפעולה הראשית אינה ברורה, ההתנהגות הרספונסיבית שבורה, הריווח או הטיפוגרפיה אינם עקביים, השדות נראים כברירות מחדל גולמיות של framework, או שהמשתמש צריך לנחש מה לעשות.

## מטרת הפרויקט

זהו מוצר Case Management גנרי לניהול קריאות שירות ותהליכים עסקיים בתחומים שונים.

מטרת המוצר היא לשלב:

- חוויית משתמש פשוטה ומהירה.
- סביבת עבודה יעילה למטפלים.
- גמישות גבוהה למיישמי המערכת ללא פיתוח שוטף.
- הרשאות, Audit, SLA ו-Workflow ברמה ארגונית.
- אפשרות להתאים את המערכת לכל תחום בלי להפוך אותה למסורבלת.

אין לבנות עוד מערכת Ticketing קשיחה, אך גם אין להפוך כל רכיב במערכת ל-Metadata חופשי. המודל הנדרש הוא ליבה יציבה עם שכבת קונפיגורציה מבוקרת.

## עקרונות עליונים

1. פשטות למשתמש קודמת להצגת כל היכולות במסך אחד.
2. גמישות שייכת בעיקר למסכי היישום והניהול, לא למסכי המשתמש הרגיל.
3. שדות ליבה, הרשאות, Audit ו-SLA הם תשתיות מערכת יציבות.
4. טפסים, ערכי רשימות, תצוגות, חוקים, Workflows והתראות ניתנים לקונפיגורציה.
5. כל שינוי קונפיגורציה משמעותי חייב להיות ניתן לבדיקה, לתיעוד ולשחזור.
6. הרשאות נאכפות תמיד בשרת. הסתרת רכיב ב-UI אינה הרשאה.
7. אין להוסיף מורכבות, ספרייה, שכבת הפשטה או טכנולוגיה חדשה ללא צורך ממשי.
8. יש לשמור על תאימות לאחור ועל המידע שכבר נשמר בבסיס הנתונים.
9. אין להציג פעולה כהצלחה לפני שנבדקה בפועל.
10. אין להניח הנחות מהותיות לגבי התנהגות עסקית. כשחסר מידע שמשנה את המודל, יש לעצור ולשאול.

## סביבת עבודה ותשתית נוכחית

- סביבת העבודה הפעילה היחידה כרגע היא `http://localhost:3000/`.
- בסיס הנתונים הנוכחי הוא SQLite מקומי ומתמשך.
- יש לתכנן את שכבת הנתונים כך שמעבר עתידי ל-PostgreSQL יהיה אפשרי ללא כתיבה מחדש של הלוגיקה העסקית.
- אין להחליף טכנולוגיה, ORM, Framework או מבנה פרויקט רק מפני שקיימת חלופה מועדפת.
- יש להשתמש במנגנון ה-Migrations הקיים. אם אין מנגנון כזה, יש להוסיף מנגנון ברור לפני שינויי Schema נוספים.
- אין ליצור נתוני Demo או Seed בסביבת העבודה הפעילה, אלא אם המשתמש ביקש זאת במפורש.
- אין למחוק, לאפס, לדרוס או ליצור מחדש את בסיס הנתונים ללא הוראה מפורשת.
- קובצי Database, גיבויים, Journals, קובצי Environment וסודות חייבים להיות מחוץ ל-Git.
- יש לוודא ש-`.gitignore` כולל לפחות קובצי `*.db`, `*.sqlite`, `*.sqlite3`, קובצי Journal/Backup וקובצי Secrets רלוונטיים.

## מודל הדומיין

### Environment

`Environment` הוא גבול קונפיגורציה והרשאה אמיתי, ולא Tag או שדה תיאורי בלבד.

לכל Environment יכולים להיות הגדרות עצמאיות של:

- משתמשים, קבוצות ותפקידים.
- סוגי קריאה.
- טפסים ופריסות.
- ערכי Status, Priority ו-Sub-priority.
- Workflow ומעברי סטטוס.
- SLA, שעות פעילות וחגים.
- Queues ותצוגות שמורות.
- כללים אוטומטיים.
- תבניות והתראות.
- הרשאות צפייה, עריכה, טיפול וניהול.

כל רשומת Case חייבת להשתייך ל-Environment אחד. מעבר Case בין Environments אינו עדכון רגיל, אלא פעולה עסקית שמחייבת בדיקת הרשאות, התאמת שדות, Workflow ו-SLA.

### שדות ליבה קבועים

השדות הבאים הם שדות מערכת. אין לאפשר למחוק אותם או להחליף אותם ב-Custom Fields:

- Case ID.
- Environment.
- Case Type.
- Subject.
- Description.
- Status.
- Priority.
- Sub-priority.
- Requester.
- Assigned group.
- Assignee.
- Created at.
- Updated at.
- Resolved at.
- Closed at.
- SLA state.

כללי עריכה:

- Environment, Subject ו-Description ניתנים לעריכה לאחר יצירת Case בהתאם להרשאה ולשלב בתהליך.
- Status, Priority ו-Sub-priority הם שדות קבועים, אך הערכים שלהם ניתנים להגדרה על ידי מיישם המערכת.
- Status חייב להופיע בכל Environment, אך רשימת הערכים שלו מוגדרת ברמת Environment.
- Priority ו-Sub-priority חייבים להופיע בכל Environment, עם ערכים ניתנים לעריכה ברמת Environment.
- Case Type הוא שדה עם ערכים הניתנים לעריכה בהגדרות Environment.
- אין להשתמש בשם המוצג של ערך כמפתח טכני. לכל ערך חייב להיות ID יציב.
- שינוי שם של ערך לא ישנה את ההיסטוריה או ישבור דוחות וחוקים.
- ערך שכבר נמצא בשימוש עובר למצב Inactive או Archived ולא נמחק פיזית.

ל-Status צריך להיות גם Semantic Category פנימי יציב, למשל `open`, `in_progress`, `waiting`, `resolved`, `closed`. הכותרת המוצגת למשתמש ניתנת להתאמה בכל Environment, אך הקטגוריה הפנימית נדרשת ל-SLA, דוחות והתנהגות מערכתית עקבית.

### תפקידים והרשאות

- בממשק העברי יש להציג את המונח `תפקיד` ולא `ROLE`.
- מנהל מערכת יכול להגדיר תפקידים ולבחור את שמותיהם.
- תפקיד אינו טקסט חופשי בלבד. הוא ישות עם ID יציב ומיפוי מפורש ל-Permissions.
- יש לתמוך בתפקידים שונים לאותו משתמש ב-Environments שונים.
- יש לתמוך בהרשאות לפי משתמש, קבוצה, תפקיד, Environment והקשר של ה-Case.
- יש לתמוך בשיתוף Case עם משתמשים מורשים נוספים כ-Participants או Viewers.
- יש להפריד בין הרשאות צפייה, יצירה, עריכה, שינוי סטטוס, שיוך, תגובה, כתיבת הערה פרטית וניהול Environment.
- יש לתמוך בהרשאות ברמת שדה: Hidden, Read-only, Editable ו-Required.
- הרשאות נבדקות בכל API ובכל פעולה עסקית, ולא רק בעת טעינת המסך.
- אין לחשוף מידע חסוי דרך API, Export, Search, Notification או Audit preview למשתמש שאינו מורשה.

## Custom Fields וטפסים

- מנהל מורשה יכול ליצור שדות מסוג Text, Long text, Number, Decimal, Date, Date-time, Checkbox, Single select, Multi-select, User, Group, Attachment, URL ו-Email לפי הצורך.
- לכל שדה יש ID יציב, Key טכני יציב, Label ניתן לעריכה, Type, Scope, Validation וסטטוס Active/Inactive.
- אין לשנות Type של שדה שכבר מכיל נתונים ללא Migration מפורש ובדיקת השפעה.
- Required אינו מאפיין גלובלי בלבד. ניתן להגדיר אותו לפי Environment, Case Type, Form, Role ו-Workflow state.
- אותו שדה יכול להיות חובה ביצירה, רשות בזמן טיפול וחובה לפני סגירה.
- יש להפריד בין Intake form, Agent form, Read-only view ו-Portal view.
- ערכי Select נשמרים באמצעות IDs ולא באמצעות Labels.
- יש לתמוך בסדר שדות, Sections, Help text, Default values ו-Conditional visibility.
- שינוי טופס אינו מוחק ערכים שנשמרו בעבר.
- אין להשתמש ב-JSON לא מבוקר או ב-EAV חופשי כתחליף למודל שדות מטיפוסים.
- אם SQLite מחייב שימוש ב-JSON בשלב ה-MVP, כל גישה אליו חייבת לעבור דרך שכבת Typed validation ברורה, ושדות ליבה ושדות חיפוש מרכזיים נשארים עמודות רגילות.

## Workflow וסטטוסים

- שינוי Status מתבצע דרך Transition מוגדר, לא באמצעות עדכון חופשי של השדה.
- לכל Transition יכולים להיות Source statuses, Target status, הרשאות, Conditions, Required fields ו-Actions.
- יש לתמוך בכניסה, יציאה, המתנה, פתיחה מחדש, פתרון וסגירה.
- אין לאפשר מעבר שאינו תקין לפי ה-Workflow הפעיל.
- יש לשמור Audit מלא לכל מעבר, כולל משתמש, זמן, ערך קודם, ערך חדש וסיבה אם נדרשה.
- שינוי Workflow שפורסם יוצר גרסה חדשה. אין לשנות בשקט את משמעות התהליך של Cases קיימים.
- יש להגדיר במפורש אם Cases פתוחים נשארים בגרסה הישנה או עוברים Migration לגרסה החדשה.
- Tasks, Approvals, Child cases ו-Relations הם הרחבות של Case ולא תחליף לליבה.

## כללים אוטומטיים

כל Rule חייב להיות ניתן ליצירה, עריכה, השבתה, שכפול, בדיקה ותיעוד.

מבנה מינימלי של Rule:

- שם ותיאור.
- Environment.
- Event trigger.
- Trigger field.
- Trigger value.
- Conditions אופציונליים.
- Field to change או Action.
- New value.
- Execution order או Priority.
- Active/Inactive.
- Version.
- Created by, updated by ו-timestamps.

כללי התנהגות:

- Trigger field מציג את השדות התקפים של ה-Environment.
- Trigger value מציג ערכים התואמים ל-Type ולערכים של השדה שנבחר.
- Field to change מציג רק שדות שניתן לעדכן באמצעות Rule.
- New value מציג ערכים התואמים לשדה היעד.
- שינוי Trigger field מנקה Trigger value שאינו תקף.
- שינוי Field to change מנקה New value שאינו תקף.
- יש לבצע Server-side validation מלאה גם אם ה-UI מגביל את הבחירה.
- יש למנוע לולאות Rules, הרצה כפולה ואפקטים לא דטרמיניסטיים.
- לכל הרצה נשמר Execution log שמסביר איזה Rule הופעל, אילו תנאים התאימו ומה השתנה.
- לפני פרסום Rule יש לספק Preview או Dry run מול Case לדוגמה כאשר הדבר אפשרי.
- פעולות אפשריות יורחבו בהדרגה: עדכון שדה, שינוי שיוך, שליחת התראה, יצירת Task, יצירת Child case והפעלת Webhook.
- אין להפעיל קוד חופשי שהוזן על ידי משתמש כחלק מ-Rule.

## SLA ו-OLA

- SLA הוא תשתית מערכת יציבה, אך הצגתו במסך Case היא Configurable. בשלב המוצר הנוכחי אין להציג Panel SLA בתוך Case Details; יש להשתמש בו בדוחות, התראות ולוגיקה פנימית.
- SLA אינו שדה Due date יחיד.
- יש לתמוך לפחות ב-First response, Next response ו-Resolution timers.
- כל Policy יכול לכלול תנאים, Priority, Calendar, Working hours, Holidays, Pause statuses, Warning threshold ו-Breach actions.
- יש להגדיר במפורש אילו Status categories עוצרות או מסיימות כל שעון.
- שינוי Priority או Policy מחשב מחדש SLA רק לפי מדיניות עסקית מוגדרת ומתועדת.
- יש לשמור היסטוריית SLA ולא רק את המועד הסופי הנוכחי.
- יש להציג למטפל זמן נותר, מצב Warning/Breached והסיבה להפסקת השעון.
- OLA פנימי בין קבוצות הוא הרחבה עתידית ואינו צריך לסבך את ה-MVP.

## תגובות, קבצים ושיתוף פעולה

יש להפריד בין סוגי האירועים הבאים:

- Public reply למגיש הבקשה ולמשתתפים מורשים.
- Internal note למטפלים מורשים.
- Private environment note למנהלי Environment ולבעלי הרשאה מפורשת.
- System event שנוצר אוטומטית ואינו תגובת משתמש.

כללים:

- יש לתמוך בתגובות וב-Replies תוך שמירה על Timeline ברור.
- כל תגובה שומרת מחבר, זמן, סוג Visibility והקשר.
- שינוי Visibility לאחר פרסום מחייב הרשאה ו-Audit.
- קבצים מצורפים עוברים בדיקת הרשאה, Type, Size ושם קובץ בטוח.
- אין לבנות נתיבי קבצים ישירות מקלט משתמש.
- מחיקה של Attachment או Comment, אם מותרת, חייבת להיות Soft delete עם Audit.
- Notifications חייבות לכבד את Visibility של האירוע.

## UX

- אין להוסיף שדה עסקי, ערך רשימה, Case Type, Status, Priority, Custom Field או Section למסך משתמש אלא אם נוצר במפורש על ידי Admin/Implementer או הוגדר כשדה Core במסמך זה.

### משתמש מגיש בקשה

- Portal נקי עם קטגוריות ברורות, חיפוש, יצירת Case ו-My Cases.
- הטופס הראשוני מציג רק מידע שנדרש בשלב זה.
- שדות מותנים נפתחים בהדרגה לפי הבחירות.
- לאחר שליחה יש להציג מספר Case, Status ברור, Timeline, קבצים ופעולות מותרות.
- הודעת שגיאה חייבת להסביר מה קרה ומה המשתמש יכול לעשות.
- אין להשאיר Submit שלא מגיב או כישלון שקט.

### מטפל

- סביבת העבודה צריכה לרכז Queue, פרטי Case, Timeline, SLA ופעולות מרכזיות.
- יש לספק Filters, Saved views, Sorting, Search ו-Bulk actions כאשר נפח העבודה מצדיק זאת.
- פעולות נפוצות צריכות להיות זמינות ללא מעבר בין מסכים רבים.
- אין להציג JSON פנימי, IDs טכניים או Debug information למשתמש.
- אין להעמיס את כל שדות ה-Case במסך אחד. יש להשתמש ב-Sections וב-Progressive disclosure.

### מיישם ומנהל

- הגדרות צריכות להיבנות באמצעות Wizards וטפסים ברורים, לא באמצעות עריכת JSON.
- יש לספק Preview לפי Role ו-Case state.
- יש להציג Dependencies לפני השבתת Field, Value, Status, Role או Rule.
- שינוי קונפיגורציה משמעותי עובר Draft, Validation, Publish ו-Rollback.
- אין לאפשר פרסום קונפיגורציה לא תקפה.

## Authentication

- יש לספק Login ברור עם הודעות שגיאה שימושיות.
- אין להשתמש במשתמש או סיסמת ברירת מחדל לא מתועדים.
- יש להוסיף Sign-up באמצעות Email וסיסמה כאשר הדבר נדרש במוצר.
- אם שליחת Email עדיין אינה זמינה, ניתן לאפשר רישום ישיר באופן זמני, אך יש לתעד זאת ולא להציג כאימות Email.
- Passwords נשמרים רק באמצעות מנגנון Hashing מקובל של הספרייה הקיימת.
- אין לרשום Passwords, Tokens או Secrets בלוגים.
- Session ו-Authorization נבדקים בצד השרת בכל בקשה מוגנת.

## ארכיטקטורת קוד

- לוגיקה עסקית אינה נכתבת בתוך Components, Routes או Controllers.
- יש להפריד בין Domain logic, Data access, API, UI ו-Infrastructure.
- יש להשתמש ב-Service layer לפעולות Case, Workflow, Permissions, Automation, SLA ו-Notifications.
- יש להעדיף מודולים קטנים עם אחריות ברורה על פני קבצים גדולים שמרכזים תחומים לא קשורים.
- אין לפצל קבצים באופן מלאכותי אם הפיצול אינו משפר אחריות, בדיקות או תחזוקה.
- יש להימנע מכפילויות. לוגיקה משותפת של Validation והרשאות נכתבת פעם אחת ומופעלת בכל נקודות הכניסה.
- IDs הם יציבים ואינם תלויים בשם המוצג.
- Timestamps נשמרים בפורמט ובאזור זמן עקביים.
- Audit הוא Append-only. אין לעדכן אירועי Audit קיימים.
- Notifications ואינטגרציות חיצוניות צריכות להשתמש ב-Outbox או מנגנון אמין דומה כדי למנוע אובדן אירועים.
- API ו-Webhooks צריכים להיות Versioned לפני חשיפה לצרכנים חיצוניים.
- אין להכניס AI ללוגיקת הליבה. AI יכול להציע סיווג, סיכום, כפילות או פתרון, אך החלטות משמעותיות דורשות אישור אדם ונרשמות ב-Audit.

## סדר ערכים

- אין להציג למשתמש `sort_order`; הוא נשמר פנימית בלבד.
- סדר ערכים מנוהל באמצעות Drag & Drop ונשמר מיד או באמצעות פעולת שמירה ברורה.
- שינוי סדר חייב להתעדכן בכל מקום שמשתמש בערכים.

## שינוי לוגיקה הוא End-to-End

- שינוי במודל עסקי חייב להיבדק ולעבור באופן עקבי דרך Database, Models, Services, API, Permissions, Automations, Reports, UI ו-Tests.
- אין לבצע שינוי לוגי נקודתי במסך אחד בלבד.

## חוזי קבצים, Payloads ומסננים

- כאשר המערכת מייצרת קובץ או תבנית שהיא צורכת לאחר מכן, בדיקת Round-trip אוטומטית חייבת להשתמש בתוצר של Endpoint היצירה עצמו.
- כאשר ה-Frontend שולח Payload מטיפוס מוגדר, Contract test חייב לאמת אותו מול Schema ה-Backend.
- אין להחזיק הגדרות Schema כפולות ונפרדות עבור Template, Parser, Validation או Export; יש להשתמש במקור אמת משותף.
- אזור מסננים משתמש רק באחד משני דפוסים ברורים: סינון חי עם משוב חזותי מפורש, או מסננים שמוחלים רק בלחיצה על `חיפוש`/`הרצה`. במסכים עסקיים מורכבים ברירת המחדל היא כפתור מפורש, בצירוף `איפוס` ומספר תוצאות.

## אין Hardcoded business configuration

- אין לשמור בקוד או ב-Seed Environment עסקי, Case Type, ערך Status, Priority, Sub-priority, Role עסקי, Custom Field, Select option, Approval configuration או Automation rule.
- הגדרות עסקיות נוצרות דרך UI ונשמרות ב-Database. Permission Domains של יכולות המוצר הם System Configuration ולכן הם חריג מותר.
- ערכי Demo/Seed עסקיים קיימים מוסרים רק באמצעות Migration בטוחה ששומרת מידע קיים.

## הרשאה לפיצ'ר חדש

כאשר נוסף Feature שמצריך הרשאה יש ליצור Permission Domain עם שם ותיאור בעברית ו-Scope, להציגו ב-UI של משתמשים וקבוצות, לאכוף אותו ב-Backend, להוסיף Tests ולהציגו בהסבר ההרשאה האפקטיבית. הסתרת UI בלבד אינה השלמת הרשאה.

- Admin Group הוא מושג מערכת המזוהה רק באמצעות flag יציב, לעולם לא לפי שם, ומקבל `edit` אוטומטי לכל Permission Domain קיים או עתידי.
- הרשאות Environment Manager הן מפורשות ומוגבלות לסביבה אחת.
- הערות מנהל ועקיפת נעילת קריאה אינן ניתנות למשתמש רגיל באמצעות Permission כללית.
- נראות קריאות משתמשת בשירות Backend משותף אחד עבור Dashboard, דוחות, יצוא וגישה ישירה.
- Export→Import נבדק אוטומטית באמצעות קובץ ה־Export המדויק; XLSX נקרא בספרייה תקנית ולא באמצעות parsing ידני של XML.
- החלפת זהות מחייבת ניקוי מלא של כל cache תלוי־זהות ב־Frontend וטעינה מחדש של זהות המשתמש.
- כל נראות Case נפתרת בשירות Backend יחיד שהוא מקור האמת; Dashboard, דוחות, יצוא, חיפוש וגישה ישירה אינם רשאים לממש חוקי נראות עצמאיים. רגרסיית נראות היא תקלה אבטחתית ומוצרית.
- System Admin רואה את כל הרשומות העסקיות, אלא אם כלל חריג מתועד במפורש. נראות Reporter, Requester, Assignee ו־Participant מכוסה תמיד בבדיקות רגרסיה.
- כל Filter חייב לכלול Label עברי גלוי, Control מתאים, מקור אפשרויות תקף, מצב ברירת מחדל ברור והתנהגות Apply/Reset. Dropdown ריק הוא Feature שבור.
- פעולות עסקיות שמוצגות בדוחות, לרבות אישור ודחייה, נשארות מכוסות בבדיקות רגרסיה.
- Environment Manager הוא שיוך עסקי מפורש לסביבה אחת ואינו מוסק מ־Permission כללית. עקיפת נעילה והערות מנהל מוגבלות ל־Environment Manager או System Admin.
- הרשאות בזמן Impersonation נבדקות לפי המשתמש האפקטיבי בלבד; המשתמש המקורי נשמר לצורכי Audit ולא מעניק הרשאות עסקיות.
- כל רגרסיה שדווחה בידי המשתמש הופכת לבדיקת רגרסיה אוטומטית קבועה.

## UX וקבצים

- UI/UX הוא חלק מדרישת Done: hierarchy חזותית, פעולות ברורות, Empty/Loading/Error states, אישור לפעולות רגישות, רספונסיביות וללא codes טכניים למשתמש.
- יעד גודל לקובץ הוא פחות מ-250 שורות כאשר הפיצול משפר אחריות ותחזוקה; Business Logic אינו נשמר בתוך Components או Routes.

## Migrations ושמירת מידע

- כל שינוי Schema מבוצע באמצעות Migration שניתן להריץ בסביבה קיימת.
- לפני Migration יש להבין את הנתונים הקיימים ואת השפעת השינוי.
- Migration חייב להיות Idempotent או מוגן מפני הרצה כפולה בהתאם לכלי הקיים.
- אין לשנות או למחוק מידע קיים כדי לגרום לטסט לעבור.
- אין לבצע Drop table, Truncate, Reset או מחיקת Database ללא אישור מפורש.
- שינוי שמות או מבנים צריך לכלול Backfill או Compatibility layer לפי הצורך.
- יש לבדוק שהאפליקציה עולה מחדש ושהמידע נשמר לאחר Restart.

## בדיקות חובה

כל שינוי התנהגותי מחייב בדיקה מתאימה. יש להשתמש בכלי הבדיקות הקיימים בפרויקט ולא להמציא פקודות שאינן קיימות.

תחומי בדיקה מרכזיים:

- יצירה, עריכה, צפייה וסגירת Case.
- עריכת Environment, Subject ו-Description לאחר יצירה.
- ערכי Case Type, Status, Priority ו-Sub-priority לפי Environment.
- הרשאות לפי Role, Group, Environment, Participant ו-Field.
- Public, Internal ו-Private comments.
- Custom field types, Required rules ו-Conditional visibility.
- Workflow transitions ו-Required fields לפני Transition.
- Automation rule mapping, execution order, loop prevention ו-Execution log.
- SLA start, pause, resume, warning, breach ו-recalculation.
- Attachments ו-Visibility.
- Login, Sign-up והודעות שגיאה.
- Persistence לאחר Restart.
- Migration על Database קיים ולא רק על Database ריק.

כאשר שינוי משפיע על UI:

- יש לבדוק את המסלול המלא בדפדפן ולא להסתפק בכך שה-Build עבר.
- יש לבדוק Success, Validation error, Permission denied, Empty state ו-Loading state.
- יש לבדוק Console errors ו-Network failures רלוונטיים.

## תהליך עבודה של Codex

לפני שינוי:

1. קרא את `AGENTS.md` ואת התיעוד הרלוונטי.
2. בדוק את מצב Git ושמור שינויים קיימים שאינם קשורים למשימה.
3. אתר את הזרימה המלאה מה-UI דרך ה-API ועד ה-Database.
4. בדוק Migrations, Models, Validation, Permissions ו-Tests קיימים לפני יצירת פתרון חדש.
5. הגדר בקצרה מה ישתנה ואיך תיבדק ההצלחה.

בזמן שינוי:

- בצע שינוי ממוקד ושלם, לא תיקון חלקי במסך בלבד.
- תקן את מקור הבעיה ולא רק את הסימפטום.
- שמור על תאימות לקוד ולנתונים הקיימים.
- אל תשנה קבצים שאינם קשורים למשימה.
- אל תבצע Refactor רחב תוך כדי תיקון נקודתי ללא צורך ברור.
- אם מתגלה בעיה נוספת שחוסמת את המשימה, תקן אותה רק כאשר היא בתוך אותו Scope. אחרת דווח עליה בנפרד.

לאחר שינוי:

1. הרץ Formatter, Lint, Type checks, Tests ו-Build הרלוונטיים שקיימים בפרויקט.
2. בדוק את התרחיש בפועל ב-`http://localhost:3000/` כאשר ניתן.
3. בדוק Persistence לאחר Restart כאשר השינוי נוגע לנתונים.
4. בדוק את ה-Diff וחפש Regression, קוד מת, Debug output וסודות.
5. עדכן תיעוד, Migrations ו-Tests לפי הצורך.
6. בצע Commit ממוקד עם הודעה ברורה.
7. בצע Push ל-Remote ול-Branch המחוברים כאשר קיימת הרשאה וגישה.
8. ודא שה-Commit קיים ב-Remote לפני דיווח שהעבודה הושלמה.

אם Push נכשל, אין לטעון שהשינוי נמצא ב-GitHub. יש לדווח במפורש מה הצליח, מה נכשל ומה נדרש כדי להשלים.

## Git ו-GitHub

- קוד המקור, Migrations, Tests ותיעוד נשמרים ב-GitHub.
- Database מקומי, נתוני משתמשים, קבצים מצורפים, Secrets ו-Environment files אינם נשמרים ב-GitHub.
- אין להשתמש ב-`git reset --hard`, מחיקה רחבה או פעולה הרסנית כדי לפתור קונפליקט.
- אין לדרוס שינויים של המשתמש או שינויים שאינם קשורים למשימה.
- כל Commit צריך לייצג יחידת עבודה הגיונית שעברה בדיקות רלוונטיות.
- אין לבצע Commit של קוד שבור או Build שנכשל, אלא אם המשתמש ביקש במפורש Checkpoint ומצבו תועד.
- לאחר כל שינוי שהושלם, יש לבצע Push. אם אין Remote, אין הרשאה או אין חיבור, יש לעצור ולדווח במקום להעמיד פנים שה-Push בוצע.

## הגדרת Done

A feature is not complete when:

- control exists but action does nothing.
- backend exists but UI cannot use it.
- UI changes only after browser refresh.
- list values differ from persisted values.
- button is missing from the actual workflow.
- placeholder text replaces functional UI.
- tests cover endpoint but not the user flow.

Done requires complete E2E behavior.

משימה נחשבת גמורה רק כאשר:

- ההתנהגות המבוקשת פועלת בפועל.
- הרשאות נאכפות בשרת.
- המידע נשמר לאחר Restart כאשר רלוונטי.
- אין כישלון שקט או Submit שלא מגיב.
- Migration מתאימה קיימת ונבדקה כאשר Schema השתנה.
- Tests, Lint, Type checks ו-Build הרלוונטיים עברו, או שקיים דיווח מדויק על חסימה.
- אין Debug output, Secrets או Database files ב-Diff.
- השינוי אינו שובר תהליכים קיימים ללא החלטה מפורשת.
- התיעוד עודכן כאשר התנהגות המוצר השתנתה.
- בוצעו Commit ו-Push כאשר הגישה ל-Remote זמינה.
- דיווח הסיום מציין בקצרה מה השתנה, מה נבדק, מה נדחף ומה עדיין פתוח.

## כללי תקשורת

- כתוב למשתמש בעברית ברורה וקצרה.
- הובל עם התוצאה ולא עם תיאור ארוך של הפעולות שבוצעו.
- אל תטען שפעולה הצליחה ללא אימות.
- ציין אי ודאות או מגבלה באופן מפורש.
- שאל שאלה רק כאשר החלטה חסרה תשנה מהותית את המודל, הנתונים, ההרשאות או התוצאה.
- בהחלטות טכניות קטנות והפיכות, פעל לפי שיקול דעת מקצועי והמשך ללא עצירה מיותרת.
