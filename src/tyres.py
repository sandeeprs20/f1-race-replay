# src/tyres.py


def build_tyre_map(session) -> dict:
    """
    Returns:
      tyre_map[driver_code][lap_number] = compound_str
      e.g. tyre_map["VER"][12] = "SOFT"
    """
    tyre_map = {}

    for driver_number in session.drivers:
        info = session.get_driver(driver_number)
        code = info["Abbreviation"]

        laps_df = session.laps.pick_drivers(driver_number)
        if laps_df.empty:
            continue

        lap_to_comp = {}
        for _, row in laps_df.iterrows():
            lap_no = row.get("LapNumber", None)
            comp = row.get("Compound", None)

            if lap_no is None:
                continue

            # Compound can be None for out/in laps; keep as None
            lap_to_comp[int(lap_no)] = None if comp is None else str(comp).upper()

        tyre_map[code] = lap_to_comp

    return tyre_map
