import io
import matplotlib
# Use non-interactive 'Agg' backend suitable for server environments
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from app.schemas import (
    BeamAnalysisRequest,
    BeamAnalysisResponse,
    ReactionForces,
    CriticalValues,
)


def calculate_beam(req: BeamAnalysisRequest) -> BeamAnalysisResponse:
    L = req.length
    
    # Static Equilibrium calculations: Sum of Moments about A = 0
    total_moment_A = 0.0
    total_load = 0.0

    for p in req.point_loads:
        total_moment_A += p.magnitude * p.position
        total_load += p.magnitude

    for u in req.udls:
        w_len = u.end - u.start
        w_total = u.magnitude * w_len
        centroid = u.start + (w_len / 2.0)
        total_moment_A += w_total * centroid
        total_load += w_total

    R_B = total_moment_A / L
    R_A = total_load - R_B

    # Discretize span for SFD and BMD diagram generation
    step = L / (req.num_points - 1)
    x_coords = [round(i * step, 3) for i in range(req.num_points)]
    
    shear_force = []
    bending_moment = []

    for x in x_coords:
        V = R_A
        M = R_A * x

        # Subtract point load effects
        for p in req.point_loads:
            if x > p.position:
                V -= p.magnitude
                M -= p.magnitude * (x - p.position)

        # Subtract UDL effects
        for u in req.udls:
            if x > u.start:
                eff_end = min(x, u.end)
                covered = eff_end - u.start
                w_segment = u.magnitude * covered
                V -= w_segment
                M -= w_segment * (x - (u.start + covered / 2.0))

        shear_force.append(round(V, 3))
        bending_moment.append(round(M, 3))

    # Find critical values
    abs_moments = [abs(m) for m in bending_moment]
    max_M = max(abs_moments)
    max_M_pos = x_coords[abs_moments.index(max_M)]
    max_V = max(abs(v) for v in shear_force)

    return BeamAnalysisResponse(
        span=L,
        reactions=ReactionForces(R_A=round(R_A, 3), R_B=round(R_B, 3)),
        critical_values=CriticalValues(
            max_bending_moment=round(max_M, 3),
            max_shear_force=round(max_V, 3),
            x_max_moment=max_M_pos
        ),
        x_coords=x_coords,
        shear_force=shear_force,
        bending_moment=bending_moment
    )


def generate_sfd_bmd_plot(res: BeamAnalysisResponse) -> bytes:
    """Generates SFD and BMD plots and returns PNG image bytes."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    fig.suptitle(f"Beam Analysis Diagrams (Span = {res.span}m)", fontsize=14, fontweight='bold')

    # --- Plot Shear Force Diagram (SFD) ---
    ax1.plot(res.x_coords, res.shear_force, color='#1f77b4', linewidth=2)
    ax1.fill_between(res.x_coords, res.shear_force, color='#1f77b4', alpha=0.25)
    ax1.axhline(0, color='black', linewidth=0.8, linestyle='--')
    ax1.set_ylabel("Shear Force (kN)", fontweight='bold')
    ax1.set_title(f"Max Shear Force: {res.critical_values.max_shear_force} kN", fontsize=10)
    ax1.grid(True, linestyle=':', alpha=0.6)

    # --- Plot Bending Moment Diagram (BMD) ---
    ax2.plot(res.x_coords, res.bending_moment, color='#d62728', linewidth=2)
    ax2.fill_between(res.x_coords, res.bending_moment, color='#d62728', alpha=0.25)
    ax2.axhline(0, color='black', linewidth=0.8, linestyle='--')
    ax2.set_xlabel("Span Position x (m)", fontweight='bold')
    ax2.set_ylabel("Bending Moment (kNm)", fontweight='bold')
    ax2.set_title(
        f"Max Bending Moment: {res.critical_values.max_bending_moment} kNm at x = {res.critical_values.x_max_moment}m", 
        fontsize=10
    )
    ax2.grid(True, linestyle=':', alpha=0.6)

    plt.tight_layout()

    # Save plot to buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150)
    plt.close(fig)
    buffer.seek(0)
    
    return buffer.getvalue()