"""CLI entrypoint. Usage:

    python -m src.pipeline fetch       # pull all data
    python -m src.pipeline features    # build feature table
    python -m src.pipeline train       # train capacity model + cuisine recs
    python -m src.pipeline all         # run everything
"""
# ============================================================================
#                                                 _____
#                                       ___---'''     '''---___
#                              _,--'''                           '''--,_
#                           ,-'                                         '-,
#                        ,-'           /\      __       __      /\         '-,
#                      ,'             /  \    /  \     /  \    /  \           ',
#                     /    .---.     | /\ |  | /\ |   | /\ |  | /\ |           \
#                    |    ( o o )    |/  \|  |/  \|   |/  \|  |/  \|   ,,       |
#                    |     \ ~ /_____________________________________,,'',,     |
#                     \     '-' /    JAI  SHARMA     '~  DRAGON  ~'      ''--,,_|
#                      '-,___  /_____________________________________________,,-'
#                           \ |                                             |
#                            \|   RESTAURANT  SATURATION  MODEL  ·  BOSTON  |
#                             \_____________________________________________|
#                              )))                                       (((
#                              ~~~             ~ Jai Sharma ~            ~~~
# ============================================================================
from __future__ import annotations
import sys


def fetch():
    from src.scrapers.census_api import fetch_acs_blockgroups
    from src.scrapers.boston_data import fetch_inspections
    from src.scrapers.osm_restaurants import fetch_osm_restaurants
    from src.scrapers.lodes import fetch_lodes_wac
    fetch_acs_blockgroups()
    fetch_osm_restaurants()
    try:
        fetch_inspections()
    except Exception as e:
        print(f"[warn] inspections fetch failed: {e}")
    try:
        fetch_lodes_wac()
    except Exception as e:
        print(f"[warn] LODES fetch failed: {e}")


def features():
    from src.features.violations import build_violation_features
    from src.features.build import build_features
    try:
        build_violation_features()
    except Exception as e:
        print(f"[warn] violation features failed: {e}")
    build_features()


def train():
    from src.model.capacity_model import train as train_cap
    from src.model.cuisine_recommender import recommend
    from src.model.survival_model import train as train_surv
    train_cap()
    recommend()
    try:
        train_surv()
    except Exception as e:
        print(f"[warn] survival model skipped: {e}")


COMMANDS = {"fetch": fetch, "features": features, "train": train}


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] not in {*COMMANDS, "all"}:
        print(__doc__)
        return 1
    cmd = argv[1]
    if cmd == "all":
        for fn in COMMANDS.values():
            fn()
    else:
        COMMANDS[cmd]()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
