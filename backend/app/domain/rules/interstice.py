"""Interstice value object: civil-month and day duration (PROC-02)."""

import calendar
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Interstice:
    start: date
    end: date

    def months(self) -> int:
        """Full civil months between start and end, with end-of-month adjustment.

        A month counts as complete when the end day reaches the start day, or when
        the end date is the last day of its month (29/02 -> 28/02 counts).
        """
        if self.end <= self.start:
            return 0
        months = (self.end.year - self.start.year) * 12 + (self.end.month - self.start.month)
        last_day = calendar.monthrange(self.end.year, self.end.month)[1]
        if self.end.day < self.start.day and self.end.day != last_day:
            months -= 1
        return months

    def days(self) -> int:
        return (self.end - self.start).days

    def crosses(self, moment: date) -> bool:
        """True when the interstice starts before `moment` and ends on or after it."""
        return self.start < moment <= self.end
