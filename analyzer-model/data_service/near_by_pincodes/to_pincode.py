""" Climate risk analyzer module: To Pincode.

 @file analyzer-model/data_service/near_by_pincodes/to_pincode.py
"""

import logging
import math

from data_service.db_pool import borrow_asyncpg_connection

logger = logging.getLogger(__name__)


def haversine(lat1, lon1, lat2, lon2):
    earth_radius_km = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_radius_km * c


async def calculate_distance(pincode1, pincode2, config):
    async with borrow_asyncpg_connection(config) as conn:
        rows = await conn.fetch(
            """
            SELECT pincode, latitude, longitude
            FROM public.pincodes_master
            WHERE pincode = ANY($1::text[])
            """,
            [str(pincode1), str(pincode2)],
        )

    locations = {row["pincode"]: row for row in rows}
    location1 = locations.get(str(pincode1))
    location2 = locations.get(str(pincode2))

    if not location1 or not location2:
        logger.warning("Could not fetch coordinates for one or both pincodes.")
        return None

    distance = haversine(
        location1["latitude"],
        location1["longitude"],
        location2["latitude"],
        location2["longitude"],
    )
    logger.debug("Distance between %s and %s: %.2f km", pincode1, pincode2, distance)
    return distance
