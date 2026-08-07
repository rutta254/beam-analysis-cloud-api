from enum import Enum

class DesignCode(str, Enum):
    EUROCODE2 = "EN1992"
    BS8110 = "BS8110"
    ACI318 = "ACI318"

def design_rc_beam_flexure(
    M_u: float,      # Ultimate Bending Moment in kN·m
    b: float,        # Section width in mm
    d: float,        # Effective depth in mm
    f_ck: float,     # Concrete strength (f_ck / f_c') in MPa
    f_yk: float,     # Steel yield strength (f_yk / f_y) in MPa
    code: DesignCode
) -> dict:
    """
    Computes required main tensile steel area (A_st) for rectangular sections
    under flexure based on the chosen design standard.
    """
    if M_u <= 0:
        return {"A_st_mm2": 0.0, "status": "No bending moment applied"}

    if code == DesignCode.EUROCODE2:
        # Eurocode 2 (EN 1992-1-1)
        gamma_s = 1.15
        f_yd = f_yk / gamma_s
        K = (M_u * 1e6) / (b * (d ** 2) * f_ck)
        K_limit = 0.167  # Single reinforcement limit

        if K <= K_limit:
            z = d * (0.5 + (0.25 - (K / 1.134)) ** 0.5)
            z = min(z, 0.95 * d)
            A_st = (M_u * 1e6) / (f_yd * z)
            return {"A_st_mm2": round(A_st, 2), "lever_arm_z_mm": round(z, 2), "status": "Singly Reinforced (PASS)"}
        else:
            return {"A_st_mm2": None, "status": "RESECTION REQUIRED: Compression steel needed (K > 0.167)"}

    elif code == DesignCode.BS8110:
        # BS 8110-1:1997
        K = (M_u * 1e6) / (b * (d ** 2) * f_ck)
        if K <= 0.156:
            z = d * (0.5 + (0.25 - (K / 0.9)) ** 0.5)
            z = min(z, 0.95 * d)
            A_st = (M_u * 1e6) / (0.95 * f_yk * z)
            return {"A_st_mm2": round(A_st, 2), "lever_arm_z_mm": round(z, 2), "status": "Singly Reinforced (PASS)"}
        else:
            return {"A_st_mm2": None, "status": "RESECTION REQUIRED: Compression steel needed (K > 0.156)"}

    elif code == DesignCode.ACI318:
        # ACI 318-19
        phi = 0.90
        R_n = (M_u * 1e6) / (phi * b * (d ** 2))
        term = 1 - (2 * R_n) / (0.85 * f_ck)
        if term >= 0:
            rho = (0.85 * f_ck / f_yk) * (1 - (term ** 0.5))
            A_st = rho * b * d
            return {"A_st_mm2": round(A_st, 2), "reinforcement_ratio_rho": round(rho, 5), "status": "Singly Reinforced (PASS)"}
        else:
            return {"A_st_mm2": None, "status": "RESECTION REQUIRED: Over-reinforced section"}

    raise ValueError("Unsupported Design Standard")