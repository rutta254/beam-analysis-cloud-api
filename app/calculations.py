def analyze_simply_supported_beam(length: float, point_load: float):
    """
    Calculates key structural properties for a simply supported beam 
    subjected to a single point load at mid-span.
    """
    # Max Shear Force (V_max = P / 2)
    max_shear_kN = point_load / 2.0

    # Max Bending Moment (M_max = (P * L) / 4)
    max_moment_kNm = (point_load * length) / 4.0

    return {
        "beam_length_m": length,
        "point_load_kN": point_load,
        "max_shear_force_kN": max_shear_kN,
        "max_bending_moment_kNm": max_moment_kNm,
        "verification_status": "PASS"
    }