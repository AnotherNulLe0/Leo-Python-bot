from calendar import monthrange

from datepicker_base import *

STEPS = {YEAR: MONTH, MONTH: DAY, DAY: HOUR, HOUR: MINUTE}  # Added day:hour and hour:minute

PREV_STEPS = {MINUTE: HOUR, HOUR: DAY, DAY: MONTH, MONTH: YEAR, YEAR: YEAR}  # Added minute:hour and hour:day
PREV_ACTIONS = {MINUTE: GOTO, HOUR: GOTO, DAY: GOTO, MONTH: GOTO, YEAR: NOTHING}  # Added minue:goto and hour:goto


class DetailedTelegramCalendar(TelegramCalendar):
    first_step = YEAR

    def __init__(self, calendar_id=0, current_date=None, additional_buttons=None, locale='en',
                 min_date=None,
                 max_date=None, telethon=False, **kwargs):
        super(DetailedTelegramCalendar, self).__init__(calendar_id, current_date=current_date,
                                                       additional_buttons=additional_buttons, locale=locale,
                                                       min_date=min_date, max_date=max_date, is_random=False,
                                                       telethon=telethon, **kwargs)

    def _build(self, step=None, **kwargs):
        if not step:
            step = self.first_step

        self.step = step
        if step == YEAR:
            self._build_years()
        elif step == MONTH:
            self._build_months()
        elif step == DAY:
            self._build_days()
        elif step == HOUR:  # added elif for hour menu
            self._build_hours()
        elif step == MINUTE:  # added elif for minute menu
            self._build_minutes()

    def _process(self, call_data, *args, **kwargs):
        params = call_data.split("_")
        params = dict(
            zip(["start", "calendar_id", "action", "step", "year", "month", "day", "hour", "minute"][:len(params)],
                params))  # Added hour and minute

        if params['action'] == NOTHING:
            return None, None, None
        step = params['step']

        year = int(params['year'])
        month = int(params['month'])
        day = int(params['day'])
        hour = int(params['hour'])  # Added hour
        minute = int(params['minute'])  # Added minute
        self.current_date = datetime(year, month, day, hour, minute)  # Added hour and minute

        if params['action'] == GOTO:
            self._build(step=step)
            return None, self._keyboard, step

        if params['action'] == SELECT:
            if step in STEPS:
                self._build(step=STEPS[step])
                return None, self._keyboard, STEPS[step]
            else:
                return self.current_date, None, step

    def _build_years(self, *args, **kwargs):
        years_num = self.size_year * self.size_year_column

        start = self.current_date - relativedelta(years=(years_num - 1) // 2)
        years = self._get_period(YEAR, start, years_num)
        years_buttons = rows(
            [
                self._build_button(d.year if d else self.empty_year_button, SELECT if d else NOTHING, YEAR, d,
                                   is_random=self.is_random)
                for d in years
            ],
            self.size_year
        )

        nav_buttons = self._build_nav_buttons(YEAR, diff=relativedelta(years=years_num),
                                              mind=max_date(start, YEAR),
                                              maxd=min_date(start + relativedelta(years=years_num - 1), YEAR))

        self._keyboard = self._build_keyboard(years_buttons + nav_buttons)

    def _build_months(self, *args, **kwargs):
        start = self.current_date.replace(month=1)
        months = self._get_period(MONTH, self.current_date.replace(month=1), 12)
        months_buttons = rows(
            [
                self._build_button(
                    self.months[self.locale][d.month - 1] if d else self.empty_month_button,  # button text
                    SELECT if d else NOTHING,  # action
                    MONTH, d, is_random=self.is_random  # other parameters
                )
                for d in months
            ],
            self.size_month)

        nav_buttons = self._build_nav_buttons(MONTH, diff=relativedelta(months=12),
                                              mind=max_date(start, MONTH),
                                              maxd=min_date(start.replace(month=12), MONTH))

        self._keyboard = self._build_keyboard(months_buttons + nav_buttons)

    def _build_days(self, *args, **kwargs):
        days_num = monthrange(self.current_date.year, self.current_date.month)[1]

        start = self.current_date.replace(day=1)
        days = self._get_period(DAY, start, days_num)

        days_buttons = rows(
            [
                self._build_button(d.day if d else self.empty_day_button, SELECT if d else NOTHING, DAY, d,
                                   is_random=self.is_random)
                for d in days
            ],
            self.size_day
        )

        days_of_week_buttons = [[
            self._build_button(self.days_of_week[self.locale][i], NOTHING) for i in range(7)
        ]]

        # mind and maxd are swapped since we need maximum and minimum days in the month
        # without swapping next page can generated incorrectly
        nav_buttons = self._build_nav_buttons(DAY, diff=relativedelta(months=1),
                                              maxd=max_date(start, MONTH),
                                              mind=min_date(start + relativedelta(days=days_num - 1), MONTH))

        self._keyboard = self._build_keyboard(days_of_week_buttons + days_buttons + nav_buttons)

    def _build_hours(self, *args, **kwargs):
        start = self.current_date.replace(hour=0)
        hours = self._get_period(HOUR, start, 24)
        hours_buttons = rows(
            [
                self._build_button(
                    d.hour if d else self.empty_hour_button,  # button text
                    SELECT if d else NOTHING,  # action
                    HOUR, d, is_random=self.is_random  # other parameters
                )
                for d in hours
            ],
            self.size_hour)

        nav_buttons = self._build_nav_buttons(HOUR, diff=relativedelta(hours=24),
                                              mind=max_date(start, HOUR),
                                              maxd=min_date(start.replace(hour=0), HOUR))

        self._keyboard = self._build_keyboard(hours_buttons + nav_buttons)

    def _build_minutes(self, *args, **kwargs):
        start = self.current_date.replace(minute=0)
        minutes = self._get_period(MINUTE, start, 60)

        minutes_buttons = rows(
            [
                self._build_button(
                    d.minute if d else self.empty_minute_button,
                    SELECT if d else NOTHING,
                    MINUTE, d, is_random=self.is_random)
                for d in minutes
            ],
            self.size_minute
        )
        # minutes_of_hour_buttons = [[
        #     self._build_button(self.minutes_of_hour[self.locale][i], NOTHING) for i in range(59)
        # ]]

        nav_buttons = self._build_nav_buttons(MINUTE, diff=relativedelta(minutes=60),
                                              mind=max_date(start, MINUTE),
                                              maxd=min_date(start.replace(minute=59), MINUTE))

        self._keyboard = self._build_keyboard(minutes_buttons + nav_buttons)

    def _build_nav_buttons(self, step, diff, mind, maxd, *args, **kwargs):

        text = self.nav_buttons[step]

        sld = list(map(str, self.current_date.timetuple()[:5]))
        data = [sld[0], self.months[self.locale][int(sld[1]) - 1], sld[2], sld[3], sld[4]]
        data = dict(zip(["year", "month", "day", "hour", "minute"], data))
        prev_page = self.current_date - diff
        next_page = self.current_date + diff

        prev_exists = mind - relativedelta(**{LSTEP[step] + "s": 1}) >= self.min_date
        next_exists = maxd + relativedelta(**{LSTEP[step] + "s": 1}) <= self.max_date
        return [[
            self._build_button(text[0].format(**data) if prev_exists else self.empty_nav_button,
                               GOTO if prev_exists else NOTHING, step, prev_page, is_random=self.is_random),
            self._build_button(text[1].format(**data),
                               PREV_ACTIONS[step], PREV_STEPS[step], self.current_date, is_random=self.is_random),
            self._build_button(text[2].format(**data) if next_exists else self.empty_nav_button,
                               GOTO if next_exists else NOTHING, step, next_page, is_random=self.is_random),
        ]]

    def _get_period(self, step, start, diff, *args, **kwargs):
        if step != DAY:
            return super(DetailedTelegramCalendar, self)._get_period(step, start, diff, *args, **kwargs)

        dates = []
        cl = calendar.monthcalendar(start.year, start.month)
        for week in cl:
            for day in week:
                if day != 0 and self._valid_date(datetime(start.year, start.month, day)):
                    dates.append(datetime(start.year, start.month, day))  # date->datetime
                else:
                    dates.append(None)

        return dates
