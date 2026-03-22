# WWM Guild Bot MVP

A minimal Discord bot for one Discord server and one **Where Winds Meet** guild.
It replaces the core guild-war coordination use cases that usually force a guild to pay for Raid-Helper and Guild Manager:

- one-character registration per Discord user
- one primary build per user
- one-time event creation
- recurring event templates backed by SQLite
- signup embeds with buttons for tank / healer / DPS / bench / tentative / absence
- role caps and bench caps
- officer roster overrides
- lock / close / unlock controls
- automatic embed refreshes after every change

The goal is to ship a reliable internal tool fast, not to build a generic SaaS platform.

## Project tree

```text
.
├── .env.example
├── README.md
├── requirements.txt
└── wwm_guild_bot
    ├── __init__.py
    ├── bot.py
    ├── config.py
    ├── db.py
    ├── embeds.py
    ├── models.py
    ├── scheduler.py
    ├── utils.py
    ├── views.py
    └── cogs
        ├── admin.py
        ├── events.py
        └── register.py
```

## What the bot does

### Character and build registration

Each Discord user can store exactly one WWM character and one primary build with these fields:

- Discord user ID
- character_name
- mastery
- role
- primary_weapon from a fixed list
- secondary_weapon from a fixed list
- Martial Arts Path from a fixed list
- sect_boost
- 4 inner ways chosen by autocomplete, each with tier 1-6
- notes

`/register_character` is a single slash command form.
It keeps registration on one Discord command page with role, weapon, and Martial Arts Path selectors, plus inner-way autocomplete and tier selectors.

### Events and signups

Users can sign up to one event once, and can change their signup by pressing buttons.

Buttons:

- Tank
- Healer
- DPS
- Bench
- Tentative
- Absence
- Withdraw
- Refresh (officers only)

Database rules:

- SQLite is the source of truth
- every signup change updates SQLite first
- then the signup embed is re-rendered
- then the original message is edited or reposted if missing

### Recurring events

Recurring templates are stored in SQLite, and APScheduler runs every minute to:

1. scan active templates
2. calculate due occurrences
3. create real event rows when their signup-open time arrives
4. auto-post the event embed
5. store the Discord message ID

Supported recurrence patterns in v1:

- `once`
- `weekly` on one weekday
- `weekly` on multiple weekdays
- `every_n_weeks`

Stopping recurrence is supported by:

- end date
- max occurrences
- manual deactivate with `/template_toggle`

## Assumptions

- This bot is intentionally **single-server**. `DISCORD_GUILD_ID` is required and commands sync only to that guild.
- This bot is intentionally **single-game** and **single-build-per-user**.
- Event creation commands assume datetimes are entered in the configured `DEFAULT_TIMEZONE`.
- Recurring templates store an explicit timezone per template using an IANA name such as `UTC` or `America/New_York`.
- For recurring events, `signup_open_lead_hours` controls when the actual event row is created.
- `close_offset_hours` means the event closes that many hours before start.
- The scheduler runs every minute, which is accurate enough for guild war coordination and much simpler than per-template job orchestration.
- If a signup message was deleted, the next refresh or signup change reposts it automatically.

## Known limitations

- No web dashboard.
- No multiple characters or multiple builds per user.
- No advanced waitlist prioritization.
- No export or analytics.
- No per-event permission editor.
- Registration uses one slash command form instead of multiple modals.
- This MVP uses slash-command text inputs for event creation rather than large admin modals, to keep officer workflows simple and maintainable.

## Discord application setup

1. Go to <https://discord.com/developers/applications>.
2. Create a new application.
3. Open **Bot** and create a bot user.
4. Under **Privileged Gateway Intents**, enable **Server Members Intent**.
5. Copy the bot token into `.env`.
6. Under **OAuth2 > URL Generator**:
   - Scopes:
     - `bot`
     - `applications.commands`
   - Bot permissions:
     - View Channels
     - Send Messages
     - Embed Links
     - Use Slash Commands
     - Read Message History
     - Manage Messages
       - optional but helpful if you want the bot to edit/repost without permission issues
7. Invite the bot to the single Discord server you want to use.

## Environment variables

Copy `.env.example` to `.env` and fill in:

```env
DISCORD_BOT_TOKEN=your_bot_token_here
DISCORD_GUILD_ID=123456789012345678
SQLITE_PATH=wwm_guild_bot.sqlite3
DEFAULT_TIMEZONE=UTC
OFFICER_ROLE_NAMES=Officer,Raid Lead
ADMIN_ROLE_NAMES=Admin,Guild Master
```

## Local setup

### 1. Create a virtual environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and set your real token, guild ID, and preferred role names.

### 4. Run the bot

```bash
python -m wwm_guild_bot.bot
```

On startup the bot will:

- initialize the SQLite schema
- load all cogs
- sync slash commands to the configured guild
- restore persistent button views for posted events
- start the scheduler
- reload recurring behavior from the database by scanning active templates every minute

## Slash commands

### User commands

- `/help`
- `/register_character`
- `/my_build`
- `/signup_status`
- `/withdraw event_id`

### Officer commands

- `/event_create`
- `/event_post event_id`
- `/event_create_recurring`
- `/event_list`
- `/event_close event_id`
- `/event_lock event_id`
- `/event_unlock event_id`
- `/roster_move event_id user role_or_state`
- `/roster_remove event_id user`
- `/event_refresh event_id`
- `/template_toggle template_id active`

## Recurring event behavior details

### Template model

A recurring template is **not** an active event.
It only stores the rule for future event generation.

When the scheduler sees that an occurrence is due:

1. it creates a real `events` row
2. it computes `closes_at = starts_at - close_offset`
3. it posts the signup embed to the configured channel
4. it stores `signup_message_id`
5. it increments the generated occurrence counter

### Recurrence examples

#### Once

- `recurrence_type=once`
- `start_date=2026-03-25`
- `time_of_day=20:00`

#### Weekly on multiple weekdays

- `recurrence_type=weekly`
- `weekdays=wed,sat`

#### Every 2 weeks

- `recurrence_type=every_n_weeks`
- `interval_weeks=2`
- optional `weekdays=wed`
  - if omitted, it uses the weekday of `start_date`

## Officer permission model

The bot uses simple role-name checks:

- any administrator is allowed
- any member with a role listed in `OFFICER_ROLE_NAMES`
- any member with a role listed in `ADMIN_ROLE_NAMES`

This keeps v1 easy to run without a database-backed permission system.

## Quick usage flow

1. Run `/help` if you need a full walkthrough of commands and signup behavior.
2. Run `/register_character` and fill the single command form.
3. Officer runs `/event_create`.
4. Officer runs `/event_post event_id:<id>`.
5. Members click Tank / Healer / DPS / Bench / Tentative / Absence.
6. Officers use `/roster_move`, `/event_lock`, `/event_close`, or `/event_refresh` when needed.
7. Officers create recurring templates with `/event_create_recurring`.
8. Scheduler automatically creates and posts future events when they become due.

## Next improvements

If you want a v2 later, the highest-value next changes are:

1. autocomplete for event IDs and templates
2. per-event officer notes and raid plans
3. waitlist priority / attendance history
4. one-click event duplication
5. optional export to CSV or JSON backups
6. better recurring rule UX with admin modals or command groups

## Exact end-to-end run steps

1. **Install Python 3.12**.
2. **Create the virtual environment**:
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   ```
3. **Install packages**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Create env file**:
   ```bash
   cp .env.example .env
   ```
5. **Fill `.env`** with:
   - `DISCORD_BOT_TOKEN`
   - `DISCORD_GUILD_ID`
   - `SQLITE_PATH`
   - `DEFAULT_TIMEZONE`
   - `OFFICER_ROLE_NAMES`
   - `ADMIN_ROLE_NAMES`
6. **Create the Discord app and bot**, enable **Server Members Intent**, and invite it with `bot` + `applications.commands` scopes.
7. **Run the bot**:
   ```bash
   python -m wwm_guild_bot.bot
   ```
8. **Wait for startup sync**. Commands are guild-scoped, so they should appear quickly in the configured server.
9. **Register a character** with `/register_character`.
10. **Create and post an event** with `/event_create` then `/event_post`.
11. **Create a recurring template** with `/event_create_recurring`.
12. **Leave the bot running** so APScheduler can keep generating due events.
