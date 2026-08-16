# הגדרת Microsoft Entra לסנכרון משתמשים

1. ב־Microsoft Entra Admin Center צרו App Registration ייעודי למערכת.
2. העתיקו את Tenant ID ואת Client ID.
3. צרו Client Secret ושמרו אותו במנהל סודות; אין לשמור אותו ב־Git או בלוגים.
4. תחת API permissions הוסיפו Microsoft Graph Application permission בשם `User.Read.All`.
5. הפעילו Admin Consent עבור הארגון.
6. הגדירו בסביבת השרת בלבד:
   - `AZURE_TENANT_ID`
   - `AZURE_CLIENT_ID`
   - `AZURE_CLIENT_SECRET`
7. הפעילו מחדש את ה־Backend.
8. עברו אל משתמשים והרשאות → Directory, בחרו Microsoft Entra ולחצו „בדיקת חיבור”.
9. לאחר שכל שלבי האבחון ירוקים, לחצו „תצוגה מקדימה” ובדקו משתמשים חדשים, לעדכון, להשבתה וללא שינוי.
10. רק לאחר אישור התצוגה המקדימה לחצו „סנכרון עכשיו”.

בדיקת החיבור מבקשת OAuth token וקוראת `Microsoft Graph /users?$top=1`. התוצאה אינה
מחזירה או מציגה את ה־Secret. בסביבת development אפשר לבחור Fake Directory כדי לבדוק
את אותו תהליך ללא חיבור חיצוני.
