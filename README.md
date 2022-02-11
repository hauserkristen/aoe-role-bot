Assumptions
- There is only one data tab/sheet per Google Sheet (In example sheet, ignore Responses and Settings are ignored and Broadcasts is the only sheet read.)
- Data is on first sheet with A1 filled out with proper format.
- First row of data is row 6.
- There will be no blank lines in between filled out line in form.
- Errors get logged in the column to the right of the table.

Set Up
- When adding bot to discord, bot needs member intent to read through all members in the guild. Additionally needs 'Manage Roles' functionality
- Bot needs to have higher role than any it will assign. So if it will assign (Players, Broadcaster) it will need to be below Admins but above Players and Broadcaster roles.
- Need to share the Spreadsheet with service account.