import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from app.schemas import (
    BeamAnalysisRequest,
    BeamAnalysisResponse,
    ReactionForces,
    CriticalValues,
    VaryingLoad,
)


def calculate_beam(req: BeamAnalysisRequest) -> BeamAnalysisResponse:
    L = req.length
    
    # -------------------------------------------------------------
    # 0. SAFELY EXTRACT SUPPORTS & LOADS
    # -------------------------------------------------------------
    supports = getattr(req, 'supports', None)
    if supports:
        sup_a = getattr(supports, 'support_a', 0.0)
        sup_b = getattr(supports, 'support_b', L)
    else:
        sup_a = 0.0
        sup_b = L

    span_ab = sup_b - sup_a

    if span_ab <= 0:
        raise ValueError("Support B position must be strictly greater than Support A position.")
    if sup_b > L:
        raise ValueError(f"Support B position ({sup_b}m) cannot exceed total beam length ({L}m).")

    point_loads = getattr(req, 'point_loads', []) or []
    point_moments = getattr(req, 'point_moments', []) or []
    varying_loads = list(getattr(req, 'varying_loads', []) or [])
    udls = getattr(req, 'udls', []) or []

    # Clean Pydantic instantiation for simple UDLs from frontend
    for u in udls:
        varying_loads.append(
            VaryingLoad(
                w1=u.magnitude,
                w2=u.magnitude,
                start=u.start,
                end=u.end
            )
        )

    # -------------------------------------------------------------
    # 1. EQUILIBRIUM: Sum of Moments about Support A = 0
    # -------------------------------------------------------------
    total_moment_A = 0.0
    total_vertical_load = 0.0

    # Point loads
    for p in point_loads:
        total_moment_A += p.magnitude * (p.position - sup_a)
        total_vertical_load += p.magnitude

    # Point moments (Clockwise positive)
    for m in point_moments:
        total_moment_A += m.magnitude

    # Varying & Uniform loads
    for v in varying_loads:
        w_len = v.end - v.start
        if w_len <= 0:
            continue
        w_total = 0.5 * (v.w1 + v.w2) * w_len
        
        # Centroid distance from start of load
        if (v.w1 + v.w2) > 0:
            centroid_offset = (w_len / 3.0) * ((v.w1 + 2 * v.w2) / (v.w1 + v.w2))
        else:
            centroid_offset = w_len / 2.0
            
        x_centroid = v.start + centroid_offset
        total_moment_A += w_total * (x_centroid - sup_a)
        total_vertical_load += w_total

    # Reactions
    R_B = total_moment_A / span_ab
    R_A = total_vertical_load - R_B

    # -------------------------------------------------------------
    # 2. INTERNAL FORCES (SFD & BMD)
    # -------------------------------------------------------------
    num_points = getattr(req, 'num_points', 200)
    x_coords = np.linspace(0, L, num_points)
    shear_force = []
    bending_moment = []

    for x in x_coords:
        V = 0.0
        M = 0.0

        # Reactions
        if x >= sup_a:
            V += R_A
            M += R_A * (x - sup_a)
        if x >= sup_b:
            V += R_B
            M += R_B * (x - sup_b)

        # Point loads
        for p in point_loads:
            if x > p.position:
                V -= p.magnitude
                M -= p.magnitude * (x - p.position)

        # Point moments
        for m in point_moments:
            if x >= m.position:
                M -= m.magnitude

        # Varying & Uniform loads
        for v in varying_loads:
            if x > v.start:
                eff_end = min(x, v.end)
                covered_len = eff_end - v.start
                tot_len = v.end - v.start
                
                if tot_len > 0:
                    w_x = v.w1 + (v.w2 - v.w1) * (covered_len / tot_len)
                    w_seg = 0.5 * (v.w1 + w_x) * covered_len
                    
                    if (v.w1 + w_x) > 0:
                        c_seg = (covered_len / 3.0) * ((v.w1 + 2 * w_x) / (v.w1 + w_x))
                    else:
                        c_seg = covered_len / 2.0

                    V -= w_seg
                    M -= w_seg * (x - (v.start + c_seg))

        shear_force.append(V)
        bending_moment.append(M)

    # -------------------------------------------------------------
    # 3. DEFLECTION (Double Trapezoidal Integration of -M / EI)
    # -------------------------------------------------------------
    E = getattr(req, 'E', 210e6)
    I = getattr(req, 'I', 0.0001)
    EI = E * I  # Flexural rigidity in kN*m^2
    M_arr = np.array(bending_moment)

    curv = -M_arr / EI

    theta_raw = np.zeros_like(x_coords)
    v_raw = np.zeros_like(x_coords)
    
    for idx in range(1, len(x_coords)):
        dx = x_coords[idx] - x_coords[idx-1]
        theta_raw[idx] = theta_raw[idx-1] + 0.5 * (curv[idx-1] + curv[idx]) * dx
        v_raw[idx] = v_raw[idx-1] + 0.5 * (theta_raw[idx-1] + theta_raw[idx]) * dx

    # Enforce boundary conditions: v(sup_a) = 0 and v(sup_b) = 0
    idx_a = (np.abs(x_coords - sup_a)).argmin()
    idx_b = (np.abs(x_coords - sup_b)).argmin()

    x_a, v_a = x_coords[idx_a], v_raw[idx_a]
    x_b, v_b = x_coords[idx_b], v_raw[idx_b]

    slope_C1 = -(v_b - v_a) / (x_b - x_a) if x_b != x_a else 0.0
    intercept_C2 = -v_a - slope_C1 * x_a

    deflection_m = v_raw + (slope_C1 * x_coords + intercept_C2)
    deflection_mm = deflection_m * 1000.0

    # -------------------------------------------------------------
    # 4. CRITICAL VALUES
    # -------------------------------------------------------------
    abs_M = np.abs(bending_moment)
    max_M_idx = np.argmax(abs_M)
    max_M = bending_moment[max_M_idx]

    abs_v = np.abs(deflection_mm)
    max_def_idx = np.argmax(abs_v)

    return BeamAnalysisResponse(
        span=L,
        reactions=ReactionForces(R_A=round(R_A, 3), R_B=round(R_B, 3)),
        critical_values=CriticalValues(
            max_bending_moment=round(float(max_M), 3),
            max_shear_force=round(float(np.max(np.abs(shear_force))), 3),
            max_deflection_mm=round(float(deflection_mm[max_def_idx]), 3),
            x_max_moment=round(float(x_coords[max_M_idx]), 3),
            x_max_deflection=round(float(x_coords[max_def_idx]), 3)
        ),
        x_coords=[round(x, 3) for x in x_coords],
        shear_force=[round(v, 3) for v in shear_force],
        bending_moment=[round(m, 3) for m in bending_moment],
        deflection_mm=[round(d, 3) for d in deflection_mm]
    )


def generate_sfd_bmd_plot(res: BeamAnalysisResponse) -> bytes:
    """Generates 3-panel SFD, BMD, and Deflection plots."""
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    fig.suptitle(f"Advanced Beam Analysis (Span = {res.span}m)", fontsize=13, fontweight='bold')

    # --- SFD ---
    ax1.plot(res.x_coords, res.shear_force, color='#1f77b4', linewidth=2)
    ax1.fill_between(res.x_coords, res.shear_force, color='#1f77b4', alpha=0.2)
    ax1.axhline(0, color='black', linewidth=0.8, linestyle='--')
    ax1.set_ylabel("Shear (kN)", fontweight='bold')
    ax1.set_title(f"Max Shear: {res.critical_values.max_shear_force} kN", fontsize=9)
    ax1.grid(True, linestyle=':', alpha=0.6)

    # --- BMD ---
    ax2.plot(res.x_coords, res.bending_moment, color='#d62728', linewidth=2)
    ax2.fill_between(res.x_coords, res.bending_moment, color='#d62728', alpha=0.2)
    ax2.axhline(0, color='black', linewidth=0.8, linestyle='--')
    ax2.set_ylabel("Moment (kNm)", fontweight='bold')
    ax2.set_title(
        f"Max Moment: {res.critical_values.max_bending_moment} kNm at x = {res.critical_values.x_max_moment}m", 
        fontsize=9
    )
    ax2.grid(True, linestyle=':', alpha=0.6)

    # --- Deflection Curve ---
    ax3.plot(res.x_coords, res.deflection_mm, color='#2ca02c', linewidth=2)
    ax3.fill_between(res.x_coords, res.deflection_mm, color='#2ca02c', alpha=0.2)
    ax3.axhline(0, color='black', linewidth=0.8, linestyle='--')
    ax3.set_xlabel("Span Position x (m)", fontweight='bold')
    ax3.set_ylabel("Deflection (mm)", fontweight='bold')
    ax3.set_title(
        f"Max Deflection: {res.critical_values.max_deflection_mm} mm at x = {res.critical_values.x_max_deflection}m", 
        fontsize=9
    )
    ax3.grid(True, linestyle=':', alpha=0.6)

    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150)
    plt.close(fig)
    buffer.seek(0)
    
    return buffer.getvalue()