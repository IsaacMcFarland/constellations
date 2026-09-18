"""
Fetch the 20 brightest stars (with measured parallax) for each of the 12
zodiac constellations from SIMBAD, and store them all in one CSV tagged by
constellation.

Install dependencies first:
    pip install astroquery astropy pandas

Usage:
    python fetch_zodiac_data.py
"""

import pandas as pd
import astropy.units as u
from astropy.coordinates import SkyCoord, get_constellation
from astroquery.simbad import Simbad

CSV_PATH = "zodiac_top20_stars.csv"
CANDIDATE_LIMIT = 500  # candidates pulled per constellation before filtering/ranking

# Generous RA/Dec bounding boxes per zodiac constellation (a superset of the
# true boundary; get_constellation() below does the precise filtering).
# (name, iau_short_code, ra_min, ra_max, dec_min, dec_max) in degrees.
ZODIAC_BOXES = [
    ("Aries",       "Ari", 24.0,  54.0,   9.0,  32.0),
    ("Taurus",      "Tau", 48.0,  91.0,  -1.0,  32.0),
    ("Gemini",      "Gem", 87.0, 123.0,   9.0,  36.0),
    ("Cancer",      "Cnc", 117.0,141.0,   6.0,  34.0),
    ("Leo",         "Leo", 139.0,178.0,  -1.0,  34.0),
    ("Virgo",       "Vir", 169.0,226.0, -23.0,  15.0),
    ("Libra",       "Lib", 213.0,240.0, -30.0,  -5.0),
    ("Scorpius",    "Sco", 231.0,271.0, -47.0,  -7.0),
    ("Sagittarius", "Sgr", 264.0,307.0, -47.0, -10.0),
    ("Capricornus", "Cap", 299.0,330.0, -29.0,  -7.0),
    ("Aquarius",    "Aqr", 308.0,360.0, -27.0,   4.0),
    ("Pisces",      "Psc", 340.0,360.0,  -7.0,  34.0),  # note: Pisces also wraps past 0h RA; see caveat below
]


def fetch_candidates(ra_min, ra_max, dec_min, dec_max):
    query = f"""
    SELECT TOP {CANDIDATE_LIMIT}
           basic.main_id, basic.ra, basic.dec, basic.otype,
           basic.plx_value,
           basic.pmra, basic.pmdec,
           basic.rvz_radvel, basic.rvz_type,
           basic.sp_type,
           fluxb.flux AS bmag,
           fluxv.flux AS vmag
    FROM basic
    JOIN flux AS fluxv ON fluxv.oidref = basic.oid AND fluxv.filter = 'V'
    LEFT JOIN flux AS fluxb ON fluxb.oidref = basic.oid AND fluxb.filter = 'B'
    WHERE basic.plx_value IS NOT NULL
      AND basic.ra BETWEEN {ra_min} AND {ra_max}
      AND basic.dec BETWEEN {dec_min} AND {dec_max}
    ORDER BY vmag ASC
    """
    result = Simbad.query_tap(query)
    return result.to_pandas()


def filter_to_constellation(df, short_code):
    coords = SkyCoord(ra=df["ra"].values * u.deg, dec=df["dec"].values * u.deg)
    df = df.copy()
    df["constellation_code"] = get_constellation(coords, short_name=True)
    return df[df["constellation_code"] == short_code].copy()


def main():
    all_top20 = []

    for name, code, ra_min, ra_max, dec_min, dec_max in ZODIAC_BOXES:
        print(f"Querying {name}...")
        df = fetch_candidates(ra_min, ra_max, dec_min, dec_max)
        df = filter_to_constellation(df, code)
        print(f"  {len(df)} confirmed {name} stars with parallax")

        if len(df) < 20:
            print(f"  Warning: fewer than 20 stars found for {name}. "
                  f"Try raising CANDIDATE_LIMIT or widening its box.")

        top20 = df.sort_values("vmag").head(20).reset_index(drop=True)
        top20.insert(0, "constellation", name)
        top20.index = top20.index + 1
        top20.index.name = "rank"
        all_top20.append(top20)

    combined = pd.concat(all_top20)
    combined.to_csv(CSV_PATH)
    print(f"\nSaved {len(combined)} rows ({len(ZODIAC_BOXES)} constellations x ~20) -> {CSV_PATH}")


if __name__ == "__main__":
    main()