import logging
import datetime
from typing import Dict, Any
from src.tools.base import BaseTool
from src.memory import memory_manager

logger = logging.getLogger("blaine.tools.reminders")

class ScheduleReminderTool(BaseTool):
    @property
    def name(self) -> str:
        return "schedule_reminder"

    @property
    def description(self) -> str:
        return "Schedules a reminder for a user that will trigger a Telegram notification after a specified duration in minutes."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "integer",
                    "description": "Telegram user ID."
                },
                "reminder_text": {
                    "type": "string",
                    "description": "The text of the reminder (e.g. 'Check the oven', 'Call Mom')."
                },
                "target_time_iso": {
                    "type": "string",
                    "description": "Target trigger UTC date & time formatted as 'YYYY-MM-DD HH:MM:SS' (e.g. '2026-08-05 09:00:00'). Convert any local user time to UTC before setting."
                },
                "duration_minutes": {
                    "type": "number",
                    "description": "Relative duration in minutes from now (e.g. 15 for 'in 15 minutes')."
                }
            },
            "required": ["user_id", "reminder_text"]
        }

    async def execute(self, **kwargs) -> Dict[str, Any]:
        user_id = kwargs.get("user_id", 0)
        chat_id = kwargs.get("chat_id", user_id)
        reminder_text = kwargs.get("reminder_text", "")
        target_time_iso = kwargs.get("target_time_iso")
        duration = kwargs.get("duration_minutes")

        now_utc = datetime.datetime.now(datetime.timezone.utc)
        trigger_utc = None

        if target_time_iso:
            try:
                clean_str = str(target_time_iso).strip().replace("T", " ").replace("Z", "")
                if "+" in clean_str:
                    clean_str = clean_str.split("+")[0].strip()
                dt_naive = datetime.datetime.fromisoformat(clean_str)
                trigger_utc = dt_naive.replace(tzinfo=datetime.timezone.utc)
            except Exception as e:
                logger.warning(f"Failed to parse target_time_iso '{target_time_iso}': {e}")

        if not trigger_utc and duration is not None:
            try:
                dur = float(duration)
                trigger_utc = now_utc + datetime.timedelta(minutes=dur)
            except ValueError:
                pass

        if not trigger_utc:
            # Fallback default to 5 minutes if unparsable
            trigger_utc = now_utc + datetime.timedelta(minutes=5)

        # If computed target time is in the past, adjust to next day
        if trigger_utc <= now_utc:
            trigger_utc += datetime.timedelta(days=1)

        trigger_iso = trigger_utc.strftime("%Y-%m-%d %H:%M:%S")
        duration_mins = max(1, int((trigger_utc - now_utc).total_seconds() / 60.0))

        reminder_id = memory_manager.add_reminder(user_id, chat_id, reminder_text, trigger_iso)
        if not reminder_id:
            logger.info(f"Reminder '{reminder_text}' is already active. Skipping duplicate creation.")
            return {
                "status": "SUCCESS",
                "message": f"Reminder for '{reminder_text}' is already active.",
                "is_duplicate": True
            }

        logger.info(f"Scheduled reminder [{reminder_id}] for user {user_id} at UTC {trigger_iso}: '{reminder_text}'")

        user_tz_res = memory_manager.get_user_timezone(user_id)
        display_time = trigger_utc.strftime('%Y-%m-%d %H:%M UTC')
        if user_tz_res and isinstance(user_tz_res, tuple) and len(user_tz_res) == 2:
            try:
                dt_local = trigger_utc.astimezone(user_tz_res[0])
                display_time += f" ({dt_local.strftime('%H:%M')} {user_tz_res[1]})"
            except Exception:
                pass

        return {
            "status": "SUCCESS",
            "message": f"Reminder scheduled for {display_time} (in {duration_mins} min): '{reminder_text}'",
            "reminder_id": reminder_id,
            "is_duplicate": False
        }


class CancelReminderTool(BaseTool):
    @property
    def name(self) -> str:
        return "cancel_reminder"

    @property
    def description(self) -> str:
        return "Cancels an active pending reminder for a user by reminder ID or matching text."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "integer",
                    "description": "Telegram user ID."
                },
                "reminder_id": {
                    "type": "integer",
                    "description": "Optional specific ID of the reminder to cancel."
                },
                "reminder_text": {
                    "type": "string",
                    "description": "Optional text or snippet of the reminder to cancel if ID is unknown."
                }
            },
            "required": ["user_id"]
        }

    async def execute(self, **kwargs) -> Dict[str, Any]:
        user_id = kwargs.get("user_id", 0)
        reminder_id = kwargs.get("reminder_id")
        reminder_text = kwargs.get("reminder_text")

        if reminder_id is not None:
            try:
                reminder_id = int(reminder_id)
            except ValueError:
                reminder_id = None

        cancelled = memory_manager.cancel_reminder(user_id, reminder_id, reminder_text)
        if not cancelled:
            target_str = f"ID {reminder_id}" if reminder_id else f"'{reminder_text}'" if reminder_text else "specified filter"
            return {
                "status": "SUCCESS",
                "message": f"No active pending reminder found matching {target_str}."
            }

        if len(cancelled) == 1:
            msg = f"Cancelled reminder [{cancelled[0]['id']}]: '{cancelled[0]['reminder_text']}'."
        else:
            items_str = ", ".join([f"[{r['id']}] '{r['reminder_text']}'" for r in cancelled])
            msg = f"Cancelled {len(cancelled)} reminders: {items_str}."

        logger.info(f"Cancelled reminder(s) for user {user_id}: {msg}")
        return {
            "status": "SUCCESS",
            "message": msg,
            "cancelled": cancelled
        }


class ListRemindersTool(BaseTool):
    @property
    def name(self) -> str:
        return "list_reminders"

    @property
    def description(self) -> str:
        return "Lists all active pending reminders for the user."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "integer",
                    "description": "Telegram user ID."
                }
            },
            "required": ["user_id"]
        }

    async def execute(self, **kwargs) -> Dict[str, Any]:
        user_id = kwargs.get("user_id", 0)
        reminders = memory_manager.get_active_reminders(user_id)
        if not reminders:
            return {
                "status": "SUCCESS",
                "message": "You have no active pending reminders.",
                "reminders": []
            }

        lines = ["<b>Your active reminders:</b>"]
        user_tz_res = memory_manager.get_user_timezone(user_id)
        for r in reminders:
            due_str = f"{r['trigger_at']} UTC"
            if user_tz_res and isinstance(user_tz_res, tuple) and len(user_tz_res) == 2:
                try:
                    dt_naive = datetime.datetime.fromisoformat(r['trigger_at'])
                    dt_utc = dt_naive.replace(tzinfo=datetime.timezone.utc)
                    dt_local = dt_utc.astimezone(user_tz_res[0])
                    due_str += f" ({dt_local.strftime('%H:%M')} {user_tz_res[1]})"
                except Exception:
                    pass
            lines.append(f"• <b>[{r['id']}]</b> {r['reminder_text']} (due at {due_str})")

        return {
            "status": "SUCCESS",
            "message": "\n".join(lines),
            "reminders": reminders
        }


class AmendReminderTool(BaseTool):
    @property
    def name(self) -> str:
        return "amend_reminder"

    @property
    def description(self) -> str:
        return "Amends/modifies an existing active pending reminder's text, trigger duration/time, or both."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "integer",
                    "description": "Telegram user ID."
                },
                "reminder_id": {
                    "type": "integer",
                    "description": "Optional specific ID of the reminder to amend."
                },
                "reminder_text": {
                    "type": "string",
                    "description": "Optional current text of the reminder to locate if ID is not provided."
                },
                "new_reminder_text": {
                    "type": "string",
                    "description": "Optional new text for the reminder."
                },
                "new_target_time_iso": {
                    "type": "string",
                    "description": "Optional new target trigger UTC date & time formatted as 'YYYY-MM-DD HH:MM:SS'. Convert any local user time to UTC before setting."
                },
                "new_duration_minutes": {
                    "type": "number",
                    "description": "Optional new duration in minutes from now when the reminder should trigger."
                }
            },
            "required": ["user_id"]
        }

    async def execute(self, **kwargs) -> Dict[str, Any]:
        user_id = kwargs.get("user_id", 0)
        reminder_id = kwargs.get("reminder_id")
        reminder_text = kwargs.get("reminder_text")
        new_reminder_text = kwargs.get("new_reminder_text")
        new_target_time_iso = kwargs.get("new_target_time_iso")
        new_duration_minutes = kwargs.get("new_duration_minutes")

        if reminder_id is not None:
            try:
                reminder_id = int(reminder_id)
            except ValueError:
                reminder_id = None

        new_trigger_iso = None
        display_time = ""
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        trigger_utc = None

        if new_target_time_iso:
            try:
                clean_str = str(new_target_time_iso).strip().replace("T", " ").replace("Z", "")
                if "+" in clean_str:
                    clean_str = clean_str.split("+")[0].strip()
                dt_naive = datetime.datetime.fromisoformat(clean_str)
                trigger_utc = dt_naive.replace(tzinfo=datetime.timezone.utc)
                new_trigger_iso = trigger_utc.strftime("%Y-%m-%d %H:%M:%S")
                display_time = trigger_utc.strftime('%Y-%m-%d %H:%M UTC')
            except Exception as e:
                logger.warning(f"Failed to parse new_target_time_iso '{new_target_time_iso}': {e}")

        if not new_trigger_iso and new_duration_minutes is not None:
            duration = float(new_duration_minutes)
            trigger_utc = now_utc + datetime.timedelta(minutes=duration)
            new_trigger_iso = trigger_utc.strftime("%Y-%m-%d %H:%M:%S")
            display_time = trigger_utc.strftime('%Y-%m-%d %H:%M UTC')

        user_tz_res = memory_manager.get_user_timezone(user_id)
        if user_tz_res and isinstance(user_tz_res, tuple) and len(user_tz_res) == 2 and trigger_utc:
            try:
                dt_local = trigger_utc.astimezone(user_tz_res[0])
                display_time += f" ({dt_local.strftime('%H:%M')} {user_tz_res[1]})"
            except Exception:
                pass

        updated = memory_manager.amend_reminder(
            user_id=user_id,
            reminder_id=reminder_id,
            reminder_text=reminder_text,
            new_reminder_text=new_reminder_text,
            new_trigger_at_iso=new_trigger_iso
        )

        if not updated:
            target_str = f"ID {reminder_id}" if reminder_id else f"'{reminder_text}'" if reminder_text else "specified filter"
            return {
                "status": "SUCCESS",
                "message": f"No active pending reminder found matching {target_str} to amend."
            }

        if new_duration_minutes is not None:
            msg = f"Amended reminder [{updated['id']}]: '{updated['reminder_text']}' set for {display_time} ({int(float(new_duration_minutes))} min from now)."
        else:
            msg = f"Amended reminder [{updated['id']}]: text updated to '{updated['reminder_text']}'."

        logger.info(f"Amended reminder for user {user_id}: {msg}")
        return {
            "status": "SUCCESS",
            "message": msg,
            "reminder": updated
        }