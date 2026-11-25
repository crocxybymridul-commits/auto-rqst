# LETTER — Telegram Join Request Manager

This starter project automatically approves **new** join requests for one private channel.

## Important limitation

Telegram Bot API can receive new join-request updates and approve individual users. It does **not** provide a method to enumerate all existing pending join requests or bulk-approve the existing backlog.

The existing 7K+ backlog therefore is **not handled by this Bot-API-only project**. Telegram TDLib documents separate methods for reading pending requests and processing requests in bulk. That requires a separately authorized Telegram client session and appropriate channel permissions. Do not send account passwords, login codes, or session files to anyone.

## 1. Bot permissions

Add the bot to the private channel as an administrator and enable **Invite Users** / **Manage Invite Links** permission. The bot must be able to manage join requests.

## 2. Railway variables

Set these in Railway:

- `BOT_TOKEN`: token from BotFather
- `CHANNEL_ID`: private channel numeric ID, usually starts with `-100`
- `ADMIN_ID`: your own Telegram numeric user ID
- `DATABASE_PATH`: `/data/letter.db`

Attach a Railway Volume and mount it at `/data` so approval statistics persist across restarts.

## 3. Deploy

Upload this project to a Git repository connected to Railway, or deploy it using a supported Railway project workflow. Railway must run it as a worker/service using the included `Procfile` or start command:

`python main.py`

Do not run multiple replicas: polling should have only one active instance.

## 4. Commands

- `/start`
- `/help`
- `/status`
- `/pause`
- `/resume`

Only the configured `ADMIN_ID` can use management commands.

## 5. Test safely

First submit a test join request from a separate account. Confirm the bot approves it, then check `/status`.

## Security

- Never commit `.env`.
- Never share your bot token, Telegram login code, password, or TDLib session.
- If the bot token is exposed, regenerate it through BotFather.
- Automatic approval allows anyone with a valid join request to enter. Use only on a channel you administer and intend to open to all applicants.
