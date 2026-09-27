from datetime import datetime, timedelta

def fixed_schedule(start, end, times):
    slots = []

    current = start.date()

    while current <= end.date():
        for t in times:
            slots.append(
                datetime.combine(current, t)
            )

        current += timedelta(days=1)

    return slots

def interval_schedule(start, end, hours):
    slots = []
    current = start

    while current <= end:
        slots.append(current)
        current += timedelta(hours=hours)

    return slots