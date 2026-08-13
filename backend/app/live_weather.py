from __future__ import annotations

from datetime import (
    date as Date,
    datetime,
    timedelta,
)

import requests

from .weather import (
    WeatherSnapshot,
)


OPEN_METEO_GEOCODING_URL = (
    "https://geocoding-api.open-meteo.com/v1/search"
)

OPEN_METEO_FORECAST_URL = (
    "https://api.open-meteo.com/v1/forecast"
)


class WeatherProviderError(
    RuntimeError
):
    """
    Raised when the live weather provider cannot produce a forecast.
    """


WEATHER_CODE_LABELS = {
    0: "clear",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    56: "light freezing drizzle",
    57: "dense freezing drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    66: "light freezing rain",
    67: "heavy freezing rain",
    71: "slight snow",
    73: "moderate snow",
    75: "heavy snow",
    77: "snow grains",
    80: "slight rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    85: "slight snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with slight hail",
    99: "thunderstorm with heavy hail",
}


SEVERE_WEATHER_CODES = {
    65,
    67,
    75,
    82,
    86,
    95,
    96,
    99,
}


def normalize_city(
    city: str,
) -> str:
    """
    Remove a state suffix before Open-Meteo geocoding.

    Example:
        Boston, MA -> Boston
    """

    cleaned = (
        city
        .strip()
    )

    if "," in cleaned:
        cleaned = (
            cleaned
            .split(
                ",",
                1,
            )[0]
            .strip()
        )

    return cleaned


def resolve_forecast_date(
    date_text: str,
    *,
    today: (
        Date
        | None
    ) = None,
) -> Date:
    """
    Convert common PlanPilot date text into a concrete forecast date.

    Supported:
    - YYYY-MM-DD
    - today
    - tomorrow
    - weekday names such as Friday

    Unknown date text falls back to today.
    """

    base_date = (
        today
        or Date.today()
    )

    cleaned = (
        date_text
        .strip()
        .lower()
    )

    if not cleaned:
        return base_date

    try:
        return (
            datetime.strptime(
                cleaned,
                "%Y-%m-%d",
            )
            .date()
        )

    except ValueError:
        pass

    if cleaned == "today":
        return base_date

    if cleaned == "tomorrow":
        return (
            base_date
            + timedelta(
                days=1
            )
        )

    weekdays = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    requested_weekday = (
        weekdays.get(
            cleaned
        )
    )

    if requested_weekday is None:
        return base_date

    days_ahead = (
        requested_weekday
        - base_date.weekday()
    ) % 7

    return (
        base_date
        + timedelta(
            days=days_ahead
        )
    )


def normalize_start_time(
    start_time: str,
) -> str:
    """
    Convert planner time text into HH:MM.

    Invalid values fall back to 18:00.
    """

    cleaned = (
        start_time
        .strip()
    )

    for format_string in (
        "%H:%M",
        "%H:%M:%S",
    ):
        try:
            parsed = (
                datetime.strptime(
                    cleaned,
                    format_string,
                )
            )

            return (
                parsed.strftime(
                    "%H:%M"
                )
            )

        except ValueError:
            continue

    return "18:00"


def weather_code_label(
    code: int,
) -> str:
    """
    Convert a WMO/Open-Meteo weather code into readable text.
    """

    return (
        WEATHER_CODE_LABELS.get(
            int(
                code
            ),
            f"weather code {code}",
        )
    )


class OpenMeteoWeatherProvider:
    """
    Live Open-Meteo forecast provider.

    The provider:
    1. geocodes the PlanPilot city
    2. requests hourly weather
    3. selects the hour closest to the itinerary start time
    4. converts the result into WeatherSnapshot
    """

    def __init__(
        self,
        *,
        timeout_seconds: int = 15,
    ) -> None:
        self.timeout_seconds = (
            timeout_seconds
        )

    def geocode_city(
        self,
        city: str,
    ) -> tuple[
        float,
        float,
    ]:
        """
        Resolve a city into coordinates using Open-Meteo geocoding.
        """

        query = normalize_city(
            city
        )

        response: (
            requests.Response
            | None
        ) = None

        try:
            response = requests.get(
                OPEN_METEO_GEOCODING_URL,
                params={
                    "name": query,
                    "count": 1,
                    "language": "en",
                    "format": "json",
                },
                timeout=(
                    self.timeout_seconds
                ),
            )

            response.raise_for_status()

        except requests.RequestException as exc:
            detail = (
                response.text
                if response is not None
                else str(
                    exc
                )
            )

            raise WeatherProviderError(
                (
                    "Weather geocoding "
                    f"failed: {detail}"
                )
            ) from exc

        try:
            payload = (
                response.json()
            )

        except ValueError as exc:
            raise WeatherProviderError(
                (
                    "Weather geocoding "
                    "returned invalid JSON."
                )
            ) from exc

        results = payload.get(
            "results",
            [],
        )

        if not results:
            raise WeatherProviderError(
                (
                    "Weather provider "
                    f"could not locate {city}."
                )
            )

        first = results[0]

        try:
            return (
                float(
                    first[
                        "latitude"
                    ]
                ),
                float(
                    first[
                        "longitude"
                    ]
                ),
            )

        except (
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise WeatherProviderError(
                (
                    "Weather geocoding "
                    "returned invalid coordinates."
                )
            ) from exc

    def get_weather(
        self,
        *,
        city: str,
        date: str,
        start_time: str = "18:00",
    ) -> WeatherSnapshot:
        """
        Retrieve weather closest to the requested itinerary start time.
        """

        latitude, longitude = (
            self.geocode_city(
                city
            )
        )

        forecast_date = (
            resolve_forecast_date(
                date
            )
        )

        normalized_time = (
            normalize_start_time(
                start_time
            )
        )

        target_timestamp = (
            f"{forecast_date.isoformat()}"
            f"T{normalized_time}"
        )

        response: (
            requests.Response
            | None
        ) = None

        try:
            response = requests.get(
                OPEN_METEO_FORECAST_URL,
                params={
                    "latitude": latitude,
                    "longitude": longitude,
                    "hourly": (
                        "temperature_2m,"
                        "precipitation_probability,"
                        "weather_code,"
                        "wind_speed_10m"
                    ),
                    "temperature_unit": (
                        "celsius"
                    ),
                    "wind_speed_unit": (
                        "kmh"
                    ),
                    "timezone": "auto",
                    "forecast_days": 16,
                },
                timeout=(
                    self.timeout_seconds
                ),
            )

            response.raise_for_status()

        except requests.RequestException as exc:
            detail = (
                response.text
                if response is not None
                else str(
                    exc
                )
            )

            raise WeatherProviderError(
                (
                    "Weather forecast "
                    f"request failed: {detail}"
                )
            ) from exc

        try:
            payload = (
                response.json()
            )

        except ValueError as exc:
            raise WeatherProviderError(
                (
                    "Weather forecast "
                    "returned invalid JSON."
                )
            ) from exc

        hourly = payload.get(
            "hourly",
            {},
        )

        if not isinstance(
            hourly,
            dict,
        ):
            raise WeatherProviderError(
                "Weather forecast did not include hourly data."
            )

        times = hourly.get(
            "time",
            [],
        )

        temperatures = hourly.get(
            "temperature_2m",
            [],
        )

        precipitation = hourly.get(
            "precipitation_probability",
            [],
        )

        weather_codes = hourly.get(
            "weather_code",
            [],
        )

        winds = hourly.get(
            "wind_speed_10m",
            [],
        )

        series_lengths = {
            len(
                times
            ),
            len(
                temperatures
            ),
            len(
                precipitation
            ),
            len(
                weather_codes
            ),
            len(
                winds
            ),
        }

        if (
            not times
            or len(
                series_lengths
            ) != 1
        ):
            raise WeatherProviderError(
                (
                    "Weather forecast returned "
                    "incomplete hourly data."
                )
            )

        try:
            target = datetime.fromisoformat(
                target_timestamp
            )

        except ValueError as exc:
            raise WeatherProviderError(
                "Invalid forecast target time."
            ) from exc

        parsed_times: list[
            datetime
        ] = []

        for item in times:
            try:
                parsed_times.append(
                    datetime.fromisoformat(
                        str(
                            item
                        )
                    )
                )

            except ValueError:
                parsed_times.append(
                    datetime.min
                )

        valid_indices = [
            index
            for index, item
            in enumerate(
                parsed_times
            )
            if (
                item
                != datetime.min
                and item.date()
                == forecast_date
            )
        ]

        if not valid_indices:
            raise WeatherProviderError(
                (
                    "Requested date is outside "
                    "the available forecast horizon."
                )
            )

        closest_index = min(
            valid_indices,
            key=lambda index: abs(
                (
                    parsed_times[
                        index
                    ]
                    - target
                )
                .total_seconds()
            ),
        )

        try:
            temperature_c = float(
                temperatures[
                    closest_index
                ]
            )

            precipitation_probability = (
                float(
                    precipitation[
                        closest_index
                    ]
                )
                / 100.0
            )

            weather_code = int(
                weather_codes[
                    closest_index
                ]
            )

            wind_speed_kph = float(
                winds[
                    closest_index
                ]
            )

        except (
            TypeError,
            ValueError,
            IndexError,
        ) as exc:
            raise WeatherProviderError(
                (
                    "Weather forecast contained "
                    "invalid hourly values."
                )
            ) from exc

        return WeatherSnapshot(
            condition=(
                weather_code_label(
                    weather_code
                )
            ),
            temperature_c=(
                temperature_c
            ),
            precipitation_probability=(
                precipitation_probability
            ),
            wind_speed_kph=(
                wind_speed_kph
            ),
            severe_weather=(
                weather_code
                in SEVERE_WEATHER_CODES
            ),
            source="open-meteo",
        )
