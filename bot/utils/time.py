import datetime
import re
from enum import Enum
from typing import Optional, Union

import arrow
import dateutil.parser
from dateutil.relativedelta import relativedelta

EPOCH_AWARE = datetime.datetime.fromtimestamp(0, datetime.timezone.utc)

_DURATION_REGEX = re.compile(
    r"((?P<years>\d+?) ?(years|year|Y|y) ?)?"
    r"((?P<months>\d+?) ?(months|month|m) ?)?"
    r"((?P<weeks>\d+?) ?(weeks|week|W|w) ?)?"
    r"((?P<days>\d+?) ?(days|day|D|d) ?)?"
    r"((?P<hours>\d+?) ?(hours|hour|H|h) ?)?"
    r"((?P<minutes>\d+?) ?(minutes|minute|M) ?)?"
    r"((?P<seconds>\d+?) ?(seconds|second|S|s))?"
)


ValidTimestamp = Union[int, float, str, datetime.datetime, datetime.date]


class TimestampFormats(Enum):
    """
    Represents the different formats possible for Discord timestamps.

    Examples are given in epoch time.
    """

    DATE_TIME = "f"  # January 1, 1970 1:00 AM
    DAY_TIME = "F"  # Thursday, January 1, 1970 1:00 AM
    DATE_SHORT = "d"  # 01/01/1970
    DATE = "D"  # January 1, 1970
    TIME = "t"  # 1:00 AM
    TIME_SECONDS = "T"  # 1:00:00 AM
    RELATIVE = "R"  # 52 years ago


def _stringify_time_unit(value: int, unit: str) -> str:
    """
    Returns a string to represent a value and time unit, ensuring that it uses the right plural form of the unit.

    >>> _stringify_time_unit(1, "seconds")
    "1 second"
    >>> _stringify_time_unit(24, "hours")
    "24 hours"
    >>> _stringify_time_unit(0, "minutes")
    "less than a minute"
    """
    if unit == "seconds" and value == 0:
        return "0 seconds"
    elif value == 1:
        return f"{value} {unit[:-1]}"
    elif value == 0:
        return f"less than a {unit[:-1]}"
    else:
        return f"{value} {unit}"


def discord_timestamp(timestamp: ValidTimestamp, format: TimestampFormats = TimestampFormats.DATE_TIME) -> str:
    """
    Format a timestamp as a Discord-flavored Markdown timestamp.

    `timestamp` can be one of the following:

    * POSIX timestamp in seconds
    * ISO 8601 string with or without a timezone
    * datetime object that is either aware or naïve; assume UTC if it is naïve
    * date object
    """
    if format not in TimestampFormats:
        raise ValueError(f"Format can only be one of {', '.join(TimestampFormats.args)}, not {format}.")

    # Convert each possible timestamp class to an integer.
    if isinstance(timestamp, (str, datetime.datetime)):
        timestamp = (_normalise(timestamp) - EPOCH_AWARE).total_seconds()
    elif isinstance(timestamp, datetime.date):
        timestamp = (timestamp - EPOCH_AWARE.date()).total_seconds()

    return f"<t:{int(timestamp)}:{format.value}>"


def humanize_delta(delta: relativedelta, precision: str = "seconds", max_units: int = 6) -> str:
    """
    Returns a human-readable version of the relativedelta.

    precision specifies the smallest unit of time to include (e.g. "seconds", "minutes").
    max_units specifies the maximum number of units of time to include (e.g. 1 may include days but not hours).
    """
    if max_units <= 0:
        raise ValueError("max_units must be positive")

    units = (
        ("years", delta.years),
        ("months", delta.months),
        ("days", delta.days),
        ("hours", delta.hours),
        ("minutes", delta.minutes),
        ("seconds", delta.seconds),
    )

    # Add the time units that are >0, but stop at accuracy or max_units.
    time_strings = []
    unit_count = 0
    for unit, value in units:
        if value:
            time_strings.append(_stringify_time_unit(value, unit))
            unit_count += 1

        if unit == precision or unit_count >= max_units:
            break

    # Add the 'and' between the last two units, if necessary
    if len(time_strings) > 1:
        time_strings[-1] = f"{time_strings[-2]} and {time_strings[-1]}"
        del time_strings[-2]

    # If nothing has been found, just make the value 0 precision, e.g. `0 days`.
    if not time_strings:
        humanized = _stringify_time_unit(0, precision)
    else:
        humanized = ", ".join(time_strings)

    return humanized


def parse_duration_string(duration: str) -> Optional[relativedelta]:
    """
    Converts a `duration` string to a relativedelta object.

    The function supports the following symbols for each unit of time:

    - years: `Y`, `y`, `year`, `years`
    - months: `m`, `month`, `months`
    - weeks: `w`, `W`, `week`, `weeks`
    - days: `d`, `D`, `day`, `days`
    - hours: `H`, `h`, `hour`, `hours`
    - minutes: `M`, `minute`, `minutes`
    - seconds: `S`, `s`, `second`, `seconds`

    The units need to be provided in descending order of magnitude.
    If the string does represent a durationdelta object, it will return None.
    """
    match = _DURATION_REGEX.fullmatch(duration)
    if not match:
        return None

    duration_dict = {unit: int(amount) for unit, amount in match.groupdict(default=0).items()}
    delta = relativedelta(**duration_dict)

    return delta


def relativedelta_to_timedelta(delta: relativedelta) -> datetime.timedelta:
    """Converts a relativedelta object to a timedelta object."""
    utcnow = datetime.datetime.utcnow()
    return utcnow + delta - utcnow


def format_relative(timestamp: ValidTimestamp) -> str:
    """
    Format `timestamp` as a relative Discord timestamp.

    A relative timestamp describes how much time has elapsed since `timestamp` or how much time
    remains until `timestamp` is reached. See `time.discord_timestamp`'s documentation for details.
    """
    return discord_timestamp(timestamp, TimestampFormats.RELATIVE)


def format_with_duration(
    timestamp: Union[str, datetime.datetime, None],
    other_timestamp: Union[str, datetime.datetime, None] = None,
    precision: str = "seconds",
    max_units: int = 2,
) -> Optional[str]:
    """
    Format `timestamp` as a Discord timestamp with the duration between it and `other_timestamp`.

    Use the current time if `other_timestamp` is unspecified.

    The timestamps can be ISO 8601 strings with or without a timezone.
    They may also be datetime objects that are either aware or naïve.
    They do not have to be of the same type (e.g. one can be a string and the other a datetime).
    Assume datetimes are in UTC if they're naïve.

    Forward `precision` and `max_units` to `time.humanize_delta`.

    Return None if `timestamp` is falsy.
    """
    if not timestamp:
        return None

    formatted_timestamp = discord_timestamp(timestamp)
    delta = abs(get_delta(timestamp, other_timestamp))
    duration = humanize_delta(delta, precision, max_units)

    return f"{formatted_timestamp} ({duration})"


def until_expiration(expiry: Union[str, datetime.datetime, None]) -> Optional[str]:
    """
    Get the remaining time until an infraction's expiration as a Discord timestamp.

    `expiry` can be an ISO 8601 string with or without a timezone.
    It may also be a datetime object that is either aware or naïve.
    Assume the datetime is in UTC if it is naïve.

    Return "Permanent" if `expiry` is None. Return "Expired" if `expiry` is in the past.
    """
    if not expiry:
        return "Permanent"

    expiry = _normalise(expiry)

    if expiry < arrow.utcnow():
        return "Expired"

    return format_relative(expiry)


def get_delta(
    start_time: Union[str, datetime.datetime],
    end_time: Union[str, datetime.datetime, None] = None,
) -> relativedelta:
    """
    Return a relativedelta representing the difference between two times.

    Use the current time if `end_time` is unspecified.

    The timestamps can be ISO 8601 strings with or without a timezone.
    They may also be datetime objects that are either aware or naïve.
    They do not have to be of the same type (e.g. one can be a string and the other a datetime).
    Assume datetimes are in UTC if they're naïve.
    """
    start_time = _normalise(start_time)
    end_time = _normalise(end_time or datetime.datetime.utcnow())

    return relativedelta(start_time, end_time)


def _normalise(timestamp: Union[str, datetime.datetime]) -> datetime.datetime:
    """
    Return a timezone-aware datetime object in UTC.

    `timestamp` can be an ISO 8601 string with or without a timezone.
    It may also be a datetime object that is either aware or naïve.
    Assume the datetime is in UTC if it is naïve.
    """
    if isinstance(timestamp, str):
        timestamp = dateutil.parser.isoparse(timestamp)

    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=datetime.timezone.utc)
    else:
        return timestamp.astimezone(datetime.timezone.utc)
