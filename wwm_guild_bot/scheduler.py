from __future__ import annotations

from datetime import timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .utils import (
    apply_close_offset,
    get_timezone,
    localize_event_time,
    parse_date_input,
    parse_time_input,
    utc_now,
)


class BotScheduler:
    def __init__(self, bot: "WWMGuildBot"):
        self.bot = bot
        self.scheduler = AsyncIOScheduler(timezone="UTC")

    def start(self) -> None:
        if self.scheduler.running:
            return
        self.scheduler.add_job(self.sync_recurring_templates, "interval", minutes=1, id="sync_templates")
        self.scheduler.add_job(self.close_expired_events, "interval", minutes=1, id="close_events")
        self.scheduler.start()

    async def sync_recurring_templates(self) -> None:
        now_utc = utc_now()
        templates = self.bot.db.list_templates(active_only=True)
        for template in templates:
            occurrences = self.iter_due_occurrences(template, now_utc)
            for starts_at in occurrences:
                if self.bot.db.template_has_event_at(template.id, starts_at):
                    continue
                closes_at = apply_close_offset(starts_at, template.close_offset_minutes)
                event_id = self.bot.db.create_event(
                    {
                        "title": template.title,
                        "description": template.description,
                        "starts_at": starts_at,
                        "closes_at": closes_at,
                        "tank_cap": template.tank_cap,
                        "healer_cap": template.healer_cap,
                        "dps_cap": template.dps_cap,
                        "bench_cap": template.bench_cap,
                        "allow_tentative": template.allow_tentative,
                        "status": "open",
                        "signup_channel_id": template.channel_id,
                        "recurring_template_id": template.id,
                    }
                )
                self.bot.db.increment_template_generated_count(template.id)
                await self.bot.post_event_message(event_id)

            refreshed = self.bot.db.get_template(template.id)
            if refreshed is None:
                continue
            if refreshed.end_after_occurrences and refreshed.generated_count >= refreshed.end_after_occurrences:
                self.bot.db.set_template_active(refreshed.id, False)
            if refreshed.end_date and parse_date_input(refreshed.end_date) < now_utc.date():
                self.bot.db.set_template_active(refreshed.id, False)

    async def close_expired_events(self) -> None:
        expired_ids = self.bot.db.get_expired_open_event_ids()
        for event_id in expired_ids:
            self.bot.db.update_event_status(event_id, "closed")
            await self.bot.refresh_event_message(event_id)

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def iter_due_occurrences(self, template, now_utc):
        timezone = get_timezone(template.timezone)
        now_local = now_utc.astimezone(timezone)
        start_date = parse_date_input(template.start_date)
        time_of_day = parse_time_input(template.time_of_day)
        end_date = parse_date_input(template.end_date) if template.end_date else None
        created: list = []
        weekdays = [int(part) for part in template.weekdays_csv.split(",") if part.strip()]
        max_occurrences = template.end_after_occurrences

        def can_emit(candidate_local):
            candidate_utc = candidate_local.astimezone(get_timezone("UTC"))
            open_at = candidate_utc - timedelta(minutes=template.signup_open_lead_minutes)
            if open_at > now_utc:
                return False
            if end_date and candidate_local.date() > end_date:
                return False
            if max_occurrences is not None and template.generated_count + len(created) >= max_occurrences:
                return False
            return True

        if template.recurrence_type == "once":
            candidate = localize_event_time(start_date, time_of_day, template.timezone)
            if can_emit(candidate):
                created.append(candidate.astimezone(get_timezone("UTC")))
            return created

        lookahead_days = 370
        for day_offset in range(lookahead_days):
            candidate_date = start_date + timedelta(days=day_offset)
            if candidate_date > now_local.date() + timedelta(days=30):
                break
            if candidate_date < start_date:
                continue
            if template.recurrence_type == "weekly":
                if weekdays and candidate_date.weekday() not in weekdays:
                    continue
            elif template.recurrence_type == "every_n_weeks":
                weeks_since_start = (candidate_date - start_date).days // 7
                if weeks_since_start % max(template.interval_weeks, 1) != 0:
                    continue
                if weekdays:
                    if candidate_date.weekday() != weekdays[0]:
                        continue
                elif candidate_date.weekday() != start_date.weekday():
                    continue
            candidate = localize_event_time(candidate_date, time_of_day, template.timezone)
            if can_emit(candidate):
                created.append(candidate.astimezone(get_timezone("UTC")))
        return created
