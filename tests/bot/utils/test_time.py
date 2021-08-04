import unittest
from datetime import date, datetime, timedelta, timezone

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from bot.utils import time
from tests._autospec import autospec


class TimeTests(unittest.TestCase):
    """Test helper functions in bot.utils.time."""

    def test_discord_timestamp_posix(self):
        """discord_timestamp should support UTC POSIX timestamps in seconds as floats or ints."""
        test_cases = (
            (10000, '<t:10000:f>'),
            (-500, '<t:-500:f>'),
            (1628132028.188289, '<t:1628132028:f>'),
            (-9823.237182, '<t:-9823:f>'),
        )

        for timestamp, expected in test_cases:
            with self.subTest(timestamp=timestamp, expected=expected):
                self.assertEqual(time.discord_timestamp(timestamp), expected)

    def test_discord_timestamp_iso_8601(self):
        """discord_timestamp should support an ISO 8601 timestamp with or without a timezone and assume UTC."""
        test_cases = (
            ('2016-12-10T23:55:19', '<t:1481414119:f>'),
            ('2004-05-23T04:10:43+00:00', '<t:1085285443:f>'),
            ('1983-08-02 13:14:02-02:30', '<t:428687042:f>'),
            ('1942-04-03 21:25:11Z', '<t:-875586889:f>'),
        )

        for timestamp, expected in test_cases:
            with self.subTest(timestamp=timestamp, expected=expected):
                self.assertEqual(time.discord_timestamp(timestamp), expected)

    def test_discord_timestamp_datetime_naive(self):
        """discord_timestamp should support a naïve datetime and assume UTC."""
        test_cases = (
            (datetime(2016, 12, 10, 23, 55, 19), '<t:1481414119:f>'),
            (datetime(2004, 5, 23, 4, 10, 43), '<t:1085285443:f>'),
            (datetime(1942, 4, 3, 21, 25, 11), '<t:-875586889:f>'),
        )

        for timestamp, expected in test_cases:
            with self.subTest(timestamp=timestamp, expected=expected):
                self.assertEqual(time.discord_timestamp(timestamp), expected)

    def test_discord_timestamp_datetime_aware(self):
        """discord_timestamp should support an aware datetime."""
        tz_minus_2_30 = timezone(timedelta(hours=-2, minutes=-30))
        test_cases = (
            (datetime(2016, 12, 10, 23, 55, 19, tzinfo=timezone.utc), '<t:1481414119:f>'),
            (datetime(2004, 5, 23, 4, 10, 43, tzinfo=timezone.utc), '<t:1085285443:f>'),
            (datetime(1983, 8, 2, 13, 14, 2, tzinfo=tz_minus_2_30), '<t:428687042:f>'),
            (datetime(1942, 4, 3, 21, 25, 11, tzinfo=timezone.utc), '<t:-875586889:f>'),
        )

        for timestamp, expected in test_cases:
            with self.subTest(timestamp=timestamp, expected=expected):
                self.assertEqual(time.discord_timestamp(timestamp), expected)

    def test_discord_timestamp_date(self):
        """discord_timestamp should support a date in UTC."""
        test_cases = (
            (date(2016, 12, 10), '<t:1481328000:f>'),
            (date(2004, 5, 23), '<t:1085270400:f>'),
            (date(1942, 4, 3), '<t:-875664000:f>'),
        )

        for timestamp, expected in test_cases:
            with self.subTest(timestamp=timestamp, expected=expected):
                self.assertEqual(time.discord_timestamp(timestamp), expected)

    def test_discord_timestamp_formats(self):
        """"discord_timestamp should format the timestamp in the given format."""
        test_cases = (
            (100, time.TimestampFormats.DATE_TIME, '<t:100:f>'),
            (100, time.TimestampFormats.DAY_TIME, '<t:100:F>'),
            (100, time.TimestampFormats.DATE_SHORT, '<t:100:d>'),
            (100, time.TimestampFormats.DATE, '<t:100:D>'),
            (100, time.TimestampFormats.TIME, '<t:100:t>'),
            (100, time.TimestampFormats.TIME_SECONDS, '<t:100:T>'),
            (100, time.TimestampFormats.RELATIVE, '<t:100:R>'),
        )

        for timestamp, format_, expected in test_cases:
            with self.subTest(timestamp=timestamp, format=format_, expected=expected):
                self.assertEqual(time.discord_timestamp(timestamp, format_), expected)

    def test_humanize_delta_handle_unknown_units(self):
        """humanize_delta should be able to handle unknown units, and will not abort."""
        # Does not abort for unknown units, as the unit name is checked
        # against the attribute of the relativedelta instance.
        self.assertEqual(time.humanize_delta(relativedelta(days=2, hours=2), 'elephants', 2), '2 days and 2 hours')

    def test_humanize_delta_handle_high_units(self):
        """humanize_delta should be able to handle very high units."""
        # Very high maximum units, but it only ever iterates over
        # each value the relativedelta might have.
        self.assertEqual(time.humanize_delta(relativedelta(days=2, hours=2), 'hours', 20), '2 days and 2 hours')

    def test_humanize_delta_mixed(self):
        """humanize_delta should limit units to the given precision and the amount to max_units."""
        test_cases = (
            (relativedelta(months=7, hours=12, seconds=13), 'hours', 2, '7 months and 12 hours'),
            (relativedelta(years=2, months=11, days=4, seconds=19), 'hours', 2, '2 years and 11 months'),
            (relativedelta(months=1, days=25, minutes=32, seconds=54), 'hours', 3, '1 month and 25 days'),
            (relativedelta(years=9, hours=2, minutes=43), 'months', 4, '9 years'),
            (relativedelta(days=5, minutes=22, seconds=49), 'minutes', 3, '5 days and 22 minutes'),
            (relativedelta(days=21, hours=3, minutes=36, seconds=31), 'minutes', 2, '21 days and 3 hours'),
            (relativedelta(minutes=27, seconds=6), 'days', 5, 'less than a day'),
            (relativedelta(days=2), 'seconds', 1, '2 days'),
            (relativedelta(days=2, hours=2), 'minutes', 2, '2 days and 2 hours'),
            (relativedelta(days=2, hours=2), 'seconds', 1, '2 days'),
            (relativedelta(days=2, hours=2), 'days', 2, '2 days'),
        )

        for delta, precision, max_units, expected in test_cases:
            with self.subTest(delta=delta, precision=precision, max_units=max_units, expected=expected):
                self.assertEqual(time.humanize_delta(delta, precision, max_units), expected)

    def test_humanize_delta_max_units(self):
        """humanize_delta should clamp the unit count to max_units, preferring to omit the smallest units."""
        test_cases = (
            (
                relativedelta(years=2, months=3, days=4, hours=14, minutes=55, seconds=31, microseconds=11),
                (6, '2 years, 3 months, 4 days, 14 hours, 55 minutes and 31 seconds'),
                (5, '2 years, 3 months, 4 days, 14 hours and 55 minutes'),
                (4, '2 years, 3 months, 4 days and 14 hours'),
                (3, '2 years, 3 months and 4 days'),
                (2, '2 years and 3 months'),
                (1, '2 years'),
            ),
            (
                relativedelta(months=5, days=15, hours=22, minutes=19, microseconds=45),
                (6, '5 months, 15 days, 22 hours and 19 minutes'),
                (5, '5 months, 15 days, 22 hours and 19 minutes'),
                (4, '5 months, 15 days, 22 hours and 19 minutes'),
                (3, '5 months, 15 days and 22 hours'),
                (2, '5 months and 15 days'),
                (1, '5 months'),
            ),
            (
                relativedelta(days=9, hours=6, seconds=47),
                (6, '9 days, 6 hours and 47 seconds'),
                (5, '9 days, 6 hours and 47 seconds'),
                (4, '9 days, 6 hours and 47 seconds'),
                (3, '9 days, 6 hours and 47 seconds'),
                (2, '9 days and 6 hours'),
                (1, '9 days'),
            ),
        )

        for delta, *cases in test_cases:
            for max_units, expected in cases:
                with self.subTest(delta=delta, precision="seconds", max_units=max_units, expected=expected):
                    self.assertEqual(time.humanize_delta(delta, "seconds", max_units), expected)

    def test_humanize_delta_precision(self):
        """humanize_delta should omit units past the given precision."""
        test_cases = (
            (
                relativedelta(years=8, months=11, days=8, hours=7, minutes=41, seconds=38, microseconds=33),
                ('seconds', '8 years, 11 months, 8 days, 7 hours, 41 minutes and 38 seconds'),
                ('minutes', '8 years, 11 months, 8 days, 7 hours and 41 minutes'),
                ('hours', '8 years, 11 months, 8 days and 7 hours'),
                ('days', '8 years, 11 months and 8 days'),
                ('months', '8 years and 11 months'),
                ('years', '8 years'),
            ),
            (
                relativedelta(months=11, days=8, hours=7, minutes=41, seconds=38, microseconds=33),
                ('seconds', '11 months, 8 days, 7 hours, 41 minutes and 38 seconds'),
                ('minutes', '11 months, 8 days, 7 hours and 41 minutes'),
                ('hours', '11 months, 8 days and 7 hours'),
                ('days', '11 months and 8 days'),
                ('months', '11 months'),
                ('years', 'less than a year'),
            ),
            (
                relativedelta(days=8, hours=7, minutes=41, seconds=38, microseconds=33),
                ('seconds', '8 days, 7 hours, 41 minutes and 38 seconds'),
                ('minutes', '8 days, 7 hours and 41 minutes'),
                ('hours', '8 days and 7 hours'),
                ('days', '8 days'),
                ('months', 'less than a month'),
                ('years', 'less than a year'),
            ),
            (
                relativedelta(hours=7, minutes=41, seconds=38, microseconds=33),
                ('seconds', '7 hours, 41 minutes and 38 seconds'),
                ('minutes', '7 hours and 41 minutes'),
                ('hours', '7 hours'),
                ('days', 'less than a day'),
                ('months', 'less than a month'),
                ('years', 'less than a year'),
            ),
            (
                relativedelta(minutes=41, seconds=38, microseconds=33),
                ('seconds', '41 minutes and 38 seconds'),
                ('minutes', '41 minutes'),
                ('hours', 'less than a hour'),
                ('days', 'less than a day'),
                ('months', 'less than a month'),
                ('years', 'less than a year'),
            ),
            (
                relativedelta(seconds=38, microseconds=33),
                ('seconds', '38 seconds'),
                ('minutes', 'less than a minute'),
                ('hours', 'less than a hour'),
                ('days', 'less than a day'),
                ('months', 'less than a month'),
                ('years', 'less than a year'),
            ),
        )

        for delta, *cases in test_cases:
            for precision, expected in cases:
                with self.subTest(delta=delta, precision=precision, max_units=6, expected=expected):
                    self.assertEqual(time.humanize_delta(delta, precision, 6), expected)

    def test_humanize_delta_zero(self):
        """humanize_delta should return "less than a ..." for a zeroed delta, except when precision is seconds."""
        delta = relativedelta()
        test_cases = (
            ('seconds', '0 seconds'),
            ('minutes', 'less than a minute'),
            ('hours', 'less than a hour'),
            ('days', 'less than a day'),
            ('months', 'less than a month'),
            ('years', 'less than a year'),
        )

        for precision, expected in test_cases:
            for max_units in range(1, 7):
                with self.subTest(delta=delta, precision=precision, max_units=max_units, expected=expected):
                    self.assertEqual(time.humanize_delta(delta, precision, max_units), expected)

    def test_humanize_delta_raises_for_invalid_max_units(self):
        """humanize_delta should raises ValueError('max_units must be positive') for invalid max_units."""
        test_cases = (-1, 0)

        for max_units in test_cases:
            with self.subTest(max_units=max_units), self.assertRaises(ValueError) as error:
                time.humanize_delta(relativedelta(days=2, hours=2), 'hours', max_units)
            self.assertEqual(str(error.exception), 'max_units must be positive')

    def test_relativedelta_to_timedelta(self):
        """relativedelta_to_timedelta should return a timedelta equivalent to the given relativedelta."""
        now = datetime.now()
        relative_delta = relativedelta(years=1, months=10, days=12, hours=2, minutes=4, seconds=10, microseconds=11)

        result = time.relativedelta_to_timedelta(relative_delta)

        # Transitively check the deltas for equality by comparing the result of adding each to the same datetime.
        self.assertEqual(now + relative_delta, now + result)
        self.assertIsInstance(result, timedelta)

    @autospec(time, "discord_timestamp", return_value="<t:10000:R>")
    def test_format_relative(self, mock_discord_timestamp):
        """format_relative should use discord_timestamp with TimestampFormats.RELATIVE."""
        actual = time.format_relative(10000)
        mock_discord_timestamp.assert_called_once_with(10000, time.TimestampFormats.RELATIVE)
        self.assertEqual(actual, mock_discord_timestamp.return_value)

    def test_format_with_duration_none_expiry(self):
        """format_with_duration should work for None expiry."""
        test_cases = (
            (None, None, None, None),

            # To make sure that date_from and max_units are not touched
            (None, 'Why hello there!', None, None),
            (None, None, float('inf'), None),
            (None, 'Why hello there!', float('inf'), None),
        )

        for timestamp, other, max_units, expected in test_cases:
            with self.subTest(timestamp=timestamp, other=other, max_units=max_units, expected=expected):
                self.assertEqual(time.format_with_duration(timestamp, other, max_units), expected)

    def test_format_with_duration_custom_units(self):
        """format_with_duration should work for custom max_units."""
        test_cases = (
            ('3000-12-12T00:01:00Z', datetime(3000, 12, 11, 12, 5, 5), 6,
             '<t:32533488060:f> (11 hours, 55 minutes and 55 seconds)'),
            ('3000-11-23T20:09:00Z', datetime(3000, 4, 25, 20, 15), 20,
             '<t:32531918940:f> (6 months, 28 days, 23 hours and 54 minutes)')
        )

        for timestamp, other, max_units, expected in test_cases:
            with self.subTest(timestamp=timestamp, other=other, max_units=max_units, expected=expected):
                self.assertEqual(time.format_with_duration(timestamp, other, max_units=max_units), expected)

    def test_format_with_duration_normal_usage(self):
        """format_with_duration should work for normal usage, across various durations."""
        test_cases = (
            ('2019-12-12T00:01:00Z', datetime(2019, 12, 11, 12, 0, 5), '<t:1576108860:f> (12 hours and 55 seconds)'),
            ('2019-12-12T00:00:00Z', datetime(2019, 12, 11, 23, 59), '<t:1576108800:f> (1 minute)'),
            ('2019-11-23T20:09:00Z', datetime(2019, 11, 15, 20, 15), '<t:1574539740:f> (7 days and 23 hours)'),
            ('2019-11-23T20:09:00Z', datetime(2019, 4, 25, 20, 15), '<t:1574539740:f> (6 months and 28 days)'),
            ('2019-11-23T20:58:00Z', datetime(2019, 11, 23, 20, 53), '<t:1574542680:f> (5 minutes)'),
            ('2019-11-24T00:00:00Z', datetime(2019, 11, 23, 23, 59, 0), '<t:1574553600:f> (1 minute)'),
            ('2019-11-23T23:59:00Z', datetime(2017, 7, 21, 23, 0), '<t:1574553540:f> (2 years and 4 months)'),
            ('2019-11-23T23:59:00Z', datetime(2019, 11, 23, 23, 49, 5), '<t:1574553540:f> (9 minutes and 55 seconds)'),
            (None, datetime(2019, 11, 23, 23, 49, 5), None),
        )

        for timestamp, other, expected in test_cases:
            with self.subTest(timestamp=timestamp, other=other, expected=expected):
                self.assertEqual(time.format_with_duration(timestamp, other), expected)

    def test_format_with_duration_different_types(self):
        """Both format_with_duration timestamp args should support ISO 8601 strings and aware/naïve datetimes."""
        test_cases = (
            (
                datetime(2019, 11, 23, 22, 9, tzinfo=timezone(timedelta(hours=2))),
                datetime(2019, 11, 15, 20, 15, tzinfo=timezone.utc),
                '<t:1574539740:f> (7 days and 23 hours)'
            ),
            (datetime(2019, 11, 23, 20, 58), '2019-11-23T20:53:00Z', '<t:1574542680:f> (5 minutes)'),
            ('2019-11-24T00:00:00+00:00', '2019-11-23T21:59:00-02:00', '<t:1574553600:f> (1 minute)'),
        )

        for timestamp, other, expected in test_cases:
            with self.subTest(timestamp=timestamp, other=other, expected=expected):
                self.assertEqual(time.format_with_duration(timestamp, other), expected)

    def test_until_expiration_with_duration_none_expiry(self):
        """until_expiration should work for None expiry."""
        self.assertEqual(time.until_expiration(None), "Permanent")

    def test_until_expiration_expired(self):
        """until_expiration should return "Expire" for expired timestamps."""
        test_cases = (
            ('1000-12-12T00:01:00Z', 'Expired'),
            ('0500-11-23T20:09:00Z', 'Expired'),
        )

        for expiry, expected in test_cases:
            with self.subTest(expiry=expiry, expected=expected):
                self.assertEqual(time.until_expiration(expiry), expected)

    @freeze_time(datetime(2000, 12, 29))
    @autospec(time, "discord_timestamp", return_value="test-value")
    def test_until_expiration_not_expired(self, mock_discord_timestamp):
        """If not permanent or expired, until_expiration should use discord_timestamp to return a relative timestamp."""
        test_cases = (
            datetime(3000, 12, 12, 0, 1, tzinfo=timezone.utc),
            datetime(2050, 11, 23, tzinfo=timezone.utc),
            datetime(2000, 12, 29, 20, 9, tzinfo=timezone.utc),
        )

        for expiry in test_cases:
            with self.subTest(expiry=expiry):
                actual = time.until_expiration(expiry)

                self.assertEqual(actual, mock_discord_timestamp.return_value)
                mock_discord_timestamp.assert_called_once_with(expiry, time.TimestampFormats.RELATIVE)

                mock_discord_timestamp.reset_mock()
