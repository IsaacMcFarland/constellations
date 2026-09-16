"""
Fetch the 20 brightest stars in the constellation Libra from SIMBAD
and store the results locally as a CSV.

"""

import astropy.units as u
import pandas as pd
from astropy.coordinates import SkyCoord, get_constellation
from astroquery.simbad import Simbad

CSV_PATH = "libra_stars.csv"

# Generous RA/Dec bounding box that comfortably contains all of Libra.
# We over-fetch here and then filter precisely with get_constellation().
RA_MIN, RA_MAX = 213.0, 240.0    # degrees
DEC_MIN, DEC_MAX = -30.0, -5.0   # degrees

# How many candidate stars to pull before filtering/sorting. Increase if
# you get fewer than 20 results back after the constellation filter.
CANDIDATE_LIMIT = 500


def fetch_candidates() -> pd.DataFrame:
    """Query SIMBAD's TAP service directly with ADQL for point sources in
    the Libra bounding box, pulling coordinates, parallax, proper motion,
    radial velocity, B/V magnitudes, and spectral type. Only stars with a
    measured parallax are included."""
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
    WHERE basic.otype = 'Star'
      AND basic.plx_value IS NOT NULL
      AND basic.ra BETWEEN {RA_MIN} AND {RA_MAX}
      AND basic.dec BETWEEN {DEC_MIN} AND {DEC_MAX}
    ORDER BY vmag ASC
    """
    result = Simbad.query_tap(query)
    return result.to_pandas()


def filter_to_libra(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only rows whose coordinates actually fall inside the Libra
    constellation boundary (the bounding box above is a superset)."""
    coords = SkyCoord(ra=df["ra"].values * u.deg, dec=df["dec"].values * u.deg)
    df = df.copy()
    df["constellation"] = get_constellation(coords, short_name=True)
    return df[df["constellation"] == "Lib"].copy()


def main():
    print("Querying SIMBAD for candidate stars near Libra...")
    df = fetch_candidates()
    print(f"  {len(df)} candidates returned")

    print("Filtering to confirmed Libra members...")
    df = filter_to_libra(df)
    print(f"  {len(df)} confirmed Libra stars")

    if len(df) < 20:
        print("Warning: fewer than 20 stars found. Try raising CANDIDATE_LIMIT.")

    top20 = df.sort_values("vmag").head(20).reset_index(drop=True)
    top20.index = top20.index + 1
    top20.index.name = "rank"

    top20.to_csv(CSV_PATH)
    print(f"Saved CSV -> {CSV_PATH}")

    print("\nTop 20 brightest stars in Libra:")
    cols = ["main_id", "ra", "dec", "plx_value", "pmra", "pmdec",
            "rvz_radvel", "bmag", "vmag", "sp_type"]
    print(top20[cols].to_string())


if __name__ == "__main__":
    main()