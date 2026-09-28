""" Climate risk analyzer module: Radius.

 @file analyzer-model/data_service/near_by_pincodes/radius.py
"""

import logging

import duckdb
import numpy as np
import pandas as pd

from data_service.db_pool import borrow_asyncpg_connection

logger = logging.getLogger(__name__)


async def _fetch_pincode_candidates(location, radius_in_degrees, config):
    """Load only pincodes inside the search bounding box instead of the full master table."""
    min_lat = float(location["latitude"].min() - radius_in_degrees)
    max_lat = float(location["latitude"].max() + radius_in_degrees)
    min_lon = float(location["longitude"].min() - radius_in_degrees)
    max_lon = float(location["longitude"].max() + radius_in_degrees)

    async with borrow_asyncpg_connection(config) as conn:
        rows = await conn.fetch(
            """
            SELECT pincode, latitude, longitude, coord_25x25
            FROM public.pincodes_master
            WHERE latitude BETWEEN $1 AND $2
              AND longitude BETWEEN $3 AND $4
            """,
            min_lat,
            max_lat,
            min_lon,
            max_lon,
        )

    return pd.DataFrame(rows, columns=["pincode", "latitude", "longitude", "coord_25x25"])


async def find_nearby_pincodes(pincode, radius, config, to_pincode=None):
    try:
        logger.info(
            "Received pincode(s): %s, radius: %s, to_pincode: %s",
            pincode,
            radius,
            to_pincode,
        )

        pincode = np.array(pincode, dtype="U6")

        if radius == 0 or radius is None:
            logger.info("Radius is 0 or None, returning the primary pincode(s) as result.")
            result_set = set(pincode.tolist())
            if to_pincode:
                result_set.add(str(to_pincode))
            return list(result_set)

        async with borrow_asyncpg_connection(config) as conn:
            rows = await conn.fetch(
                """
                SELECT pincode, latitude, longitude, coord_25x25
                FROM public.pincodes_master
                WHERE pincode = ANY($1::text[])
                """,
                pincode.tolist(),
            )

        location = pd.DataFrame(rows, columns=["pincode", "latitude", "longitude", "coord_25x25"])
        if location.empty:
            raise ValueError(f"Pincode {pincode.tolist()} not found in the database.")

        radius_in_degrees = radius / 111
        pincode_table = await _fetch_pincode_candidates(location, radius_in_degrees, config)
        if pincode_table.empty:
            logger.info("No pincodes found in bounding box. Returning the primary pincode.")
            return pincode.tolist()

        con = duckdb.connect()
        try:
            con.register("pincode_table", pincode_table)
            nearby_pincodes_list = []

            for _, row in location.iterrows():
                ref_lat, ref_lon = row["latitude"], row["longitude"]
                query = f"""
                    SELECT pincode, coord_25x25,
                        SQRT(POW(latitude - {ref_lat}, 2) + POW(longitude - {ref_lon}, 2)) AS distance
                    FROM pincode_table
                    WHERE SQRT(POW(latitude - {ref_lat}, 2) + POW(longitude - {ref_lon}, 2)) < {radius_in_degrees}
                """
                result = con.execute(query).fetchdf()
                if not result.empty:
                    nearby_pincodes_list.append(result)
        finally:
            con.close()

        final_pincodes = set(pincode.tolist())
        if nearby_pincodes_list:
            nearby_pincodes = pd.concat(nearby_pincodes_list).drop_duplicates()
            final_pincodes.update(nearby_pincodes["pincode"].astype(str).tolist())

        if to_pincode:
            to_pincode = str(to_pincode)
            if to_pincode in pincode_table["pincode"].astype(str).values:
                final_pincodes.add(to_pincode)
            else:
                async with borrow_asyncpg_connection(config) as conn:
                    exists = await conn.fetchval(
                        "SELECT 1 FROM public.pincodes_master WHERE pincode = $1",
                        to_pincode,
                    )
                if exists:
                    final_pincodes.add(to_pincode)
                else:
                    logger.warning("to_pincode %s not found in database, skipping.", to_pincode)

        final_pincode_list = sorted(final_pincodes)
        logger.info("Final nearby pincodes count: %s", len(final_pincode_list))
        return final_pincode_list

    except Exception as exc:
        logger.error("Error in find_nearby_pincodes: %s", exc, exc_info=True)
        return None
