""" Climate risk analyzer module: Era5.

 @file analyzer-model/data_service/era5/era5.py
"""

from __future__ import annotations

import logging
import os
import time
from datetime import date
from typing import Iterable, List, Sequence, Tuple

import pandas as pd
from psycopg2 import pool as psycopg2_pool

from data_service.db_pool import borrow_psycopg2_connection, get_psycopg2_pool

logger = logging.getLogger(__name__)

_DEFAULT_HISTORY_YEARS = int(os.getenv("WEATHER_HISTORY_YEARS", "30"))
_YEAR_CHUNK_SIZE = int(os.getenv("WEATHER_YEAR_CHUNK_SIZE", "5"))
_COORD_BATCH_SIZE = int(os.getenv("WEATHER_COORD_BATCH_SIZE", "8"))

_QUERY_PINCODE_COORDS = """
SELECT DISTINCT pm.pincode::text, pm.coord_25x25
FROM pincodes_master pm
WHERE pm.pincode = ANY(%s)
  AND pm.coord_25x25 IS NOT NULL;
"""

_QUERY_ERA5_CHUNK = """
SELECT DISTINCT ON (e.date, e.coord_25x25)
    e.coord_25x25,
    e.max_temperature,
    e.min_temperature,
    e.date
FROM era5_heat_processed e
WHERE e.coord_25x25 = ANY(%s)
  AND e.date >= %s
  AND e.date < %s
ORDER BY e.date, e.coord_25x25 DESC;
"""


def _rows_to_era5_dataframe(rows, pincode_coord_pairs: Sequence[Tuple[str, str]]):
    if not rows:
        return pd.DataFrame(columns=["pincode", "date", "Max_Temp", "Min_Temp", "coord_25x25"])

    weather = pd.DataFrame(
        rows, columns=["coord_25x25", "Max_Temp", "Min_Temp", "date"]
    )
    mapping = pd.DataFrame(pincode_coord_pairs, columns=["pincode", "coord_25x25"])
    data = weather.merge(mapping, on="coord_25x25", how="inner")
    data = data[["pincode", "date", "Max_Temp", "Min_Temp", "coord_25x25"]]
    data["date"] = pd.to_datetime(data["date"])
    data["Max_Temp"] = data["Max_Temp"].round(2)
    data["Min_Temp"] = data["Min_Temp"].round(2)
    data["pincode"] = data["pincode"].astype(int)
    return data


def _history_bounds(history_years: int) -> Tuple[date, date]:
    end = date(date.today().year + 1, 1, 1)
    start = date(date.today().year - history_years, 1, 1)
    return start, end


def _iter_year_windows(start: date, end: date, chunk_years: int) -> Iterable[Tuple[date, date]]:
    year = start.year
    while date(year, 1, 1) < end:
        window_start = date(year, 1, 1)
        window_end = date(min(year + chunk_years, end.year), 1, 1)
        if window_end > end:
            window_end = end
        if window_start >= window_end:
            break
        yield window_start, window_end
        year += chunk_years


def _chunked(items: Sequence, size: int) -> Iterable[List]:
    for index in range(0, len(items), size):
        yield list(items[index : index + size])


def fetch_era5_data(pincodes, config, history_years=None):
    """
    Fetch ERA5 temperature history by unique grid coordinates, in year + coordinate batches.
    All chunks are concatenated before returning to the risk models.
    """
    years = _DEFAULT_HISTORY_YEARS if history_years is None else history_years
    logger.info(
        "Starting chunked ERA5 fetch (history=%sy, year_chunk=%s, coord_batch=%s)",
        years,
        _YEAR_CHUNK_SIZE,
        _COORD_BATCH_SIZE,
    )

    pincodes_str = [str(pincode) for pincode in pincodes]
    logger.debug("pincodes: %s", pincodes_str)

    db_pool: psycopg2_pool.ThreadedConnectionPool = get_psycopg2_pool(config)
    try:
        start_time = time.time()
        with borrow_psycopg2_connection(db_pool, config=config) as conn:
            cur = conn.cursor()

            cur.execute(_QUERY_PINCODE_COORDS, (pincodes_str,))
            pincode_coord_pairs = [(str(row[0]), row[1]) for row in cur.fetchall()]
            if not pincode_coord_pairs:
                logger.warning("No pincode/coord mappings found for %s", pincodes_str)
                empty = pd.DataFrame(
                    columns=["pincode", "date", "Max_Temp", "Min_Temp", "coord_25x25"]
                )
                return empty, "ERA5 Gridded Temperature Data (0.25° x 0.25°)", pincodes

            unique_coords = sorted({coord for _, coord in pincode_coord_pairs})
            history_start, history_end = _history_bounds(years)
            logger.info(
                "ERA5 fetch plan: %s pincodes → %s unique coords, date range %s .. %s",
                len(pincode_coord_pairs),
                len(unique_coords),
                history_start,
                history_end,
            )

            chunk_frames: List[pd.DataFrame] = []
            total_rows = 0
            chunk_index = 0

            for window_start, window_end in _iter_year_windows(
                history_start, history_end, _YEAR_CHUNK_SIZE
            ):
                for coord_batch in _chunked(unique_coords, _COORD_BATCH_SIZE):
                    chunk_index += 1
                    query_start = time.time()
                    cur.execute(
                        _QUERY_ERA5_CHUNK,
                        (coord_batch, window_start, window_end),
                    )
                    rows = cur.fetchall()
                    elapsed = time.time() - query_start
                    total_rows += len(rows)
                    logger.info(
                        "ERA5 chunk %s: coords=%s date=[%s,%s) rows=%s in %.2fs",
                        chunk_index,
                        len(coord_batch),
                        window_start,
                        window_end,
                        len(rows),
                        elapsed,
                    )
                    if rows:
                        chunk_frames.append(_rows_to_era5_dataframe(rows, pincode_coord_pairs))

            if chunk_frames:
                data = pd.concat(chunk_frames, ignore_index=True)
                data = data.drop_duplicates(
                    subset=["pincode", "date", "coord_25x25"], keep="last"
                )
                data = data.sort_values("date").reset_index(drop=True)
            else:
                data = pd.DataFrame(
                    columns=["pincode", "date", "Max_Temp", "Min_Temp", "coord_25x25"]
                )

            logger.info(
                "Total ERA5 processing completed in %.2fs (weather_rows=%s, expanded_rows=%s)",
                time.time() - start_time,
                total_rows,
                len(data),
            )

            data_source = "ERA5 Gridded Temperature Data (0.25° x 0.25°)"
            return data, data_source, pincodes
    except Exception as exc:
        logger.error("Error in fetching ERA5 heat data: %s", exc, exc_info=True)
        raise
