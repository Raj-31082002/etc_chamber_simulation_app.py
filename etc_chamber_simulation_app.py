import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(
    page_title="ETC APS Voice Combat Simulation",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ Voice-Controlled APS + ETC Real-Time Simulation")
st.caption("ETC chamber working animation with combat voice alerts and projectile motion visualization.")

st.warning("Academic visualization model only. Not a validated weapon design solver.")

# ============================================================
# SIDEBAR INPUTS
# ============================================================

st.sidebar.header("ETC Launcher Inputs")

propellant_mass_g = st.sidebar.slider("Propellant Mass (g)", 20, 300, 120, 5)
electric_pulse_kj = st.sidebar.slider("Electric Pulse Energy (kJ)", 5, 120, 35, 5)
plasma_efficiency = st.sidebar.slider("Plasma Coupling Efficiency", 0.05, 0.60, 0.25, 0.01)

chamber_length_mm = st.sidebar.slider("Chamber Length (mm)", 40, 250, 120, 5)
chamber_diameter_mm = st.sidebar.slider("Chamber Diameter (mm)", 20, 80, 50, 2)
barrel_length_mm = st.sidebar.slider("Barrel Length (mm)", 150, 1500, 500, 25)

projectile_mass_g = st.sidebar.slider("Projectile / Interceptor Mass (g)", 20, 300, 80, 5)
projectile_diameter_mm = st.sidebar.slider("Projectile Diameter (mm)", 10, 50, 25, 1)

st.sidebar.header("Threat / APS Inputs")

threat_velocity = st.sidebar.slider("Threat Velocity (m/s)", 100, 900, 200, 10)
threat_distance = st.sidebar.slider("Threat Distance (m)", 20, 500, 180, 10)
interception_distance = st.sidebar.slider("Interception Distance (m)", 20, 200, 80, 5)

voice_mode = st.sidebar.checkbox("Enable Voice Combat Mode", True)
animation_speed = st.sidebar.slider("Animation Speed", 40, 180, 90, 10)

# ============================================================
# SIMPLE ETC MODEL
# ============================================================

def clip(v, lo, hi):
    return max(lo, min(v, hi))

def calculate_etc():
    mp = propellant_mass_g / 1000
    Ei = electric_pulse_kj * 1000
    mi = projectile_mass_g / 1000

    Lc = chamber_length_mm / 1000
    Dc = chamber_diameter_mm / 1000
    Lb = barrel_length_mm / 1000
    Dp = projectile_diameter_mm / 1000

    chamber_volume = np.pi * (Dc / 2) ** 2 * Lc
    bore_area = np.pi * (Dp / 2) ** 2

    propellant_energy_density = 3.0e6
    gas_fraction = 0.85
    gas_R = 300
    gamma = 1.22
    ballistic_efficiency = 0.18

    chemical_energy = mp * propellant_energy_density
    electric_energy = Ei * plasma_efficiency
    total_energy = chemical_energy + electric_energy

    gas_mass = max(mp * gas_fraction, 1e-6)
    cv = gas_R / (gamma - 1)

    temperature = 300 + total_energy / (gas_mass * cv)
    temperature = clip(temperature, 500, 6500)

    pressure_pa = gas_mass * gas_R * temperature / max(chamber_volume, 1e-9)
    pressure_mpa = clip(pressure_pa / 1e6, 5, 450)

    useful_work = min(
        total_energy * ballistic_efficiency,
        pressure_pa * bore_area * Lb * 0.55
    )

    muzzle_velocity = np.sqrt(max(2 * useful_work / max(mi, 1e-6), 0))
    muzzle_velocity = clip(muzzle_velocity, 50, 950)

    acceleration = muzzle_velocity ** 2 / (2 * max(Lb, 1e-6))
    launch_time = muzzle_velocity / max(acceleration, 1e-6)

    threat_tti = threat_distance / threat_velocity
    interceptor_flight_time = interception_distance / muzzle_velocity
    total_interception_time = launch_time + interceptor_flight_time
    time_margin = threat_tti - total_interception_time

    return pressure_mpa, temperature, muzzle_velocity, launch_time, total_interception_time, time_margin

pressure_mpa, temperature_k, muzzle_velocity, launch_time, interception_time, time_margin = calculate_etc()

# ============================================================
# OUTPUT CARDS
# ============================================================

c1, c2, c3, c4 = st.columns(4)

c1.metric("Peak Pressure", f"{pressure_mpa:.1f} MPa")
c2.metric("Peak Temperature", f"{temperature_k:.0f} K")
c3.metric("Muzzle Velocity", f"{muzzle_velocity:.1f} m/s")
c4.metric("Interception Time", f"{interception_time:.4f} s")

if time_margin > 0:
    st.success(f"Target Neutralization Feasible | Time Margin: {time_margin:.4f} s")
else:
    st.error(f"Interception Not Feasible | Time Deficit: {abs(time_margin):.4f} s")

# ============================================================
# VOICE COMBAT MODE
# ============================================================

if voice_mode:
    st.markdown(
        """
        <script>
        function speakCombatSequence() {
            const messages = [
                "Threat detected",
                "AI classification complete",
                "ETC launcher armed",
                "Interceptor launched",
                "Target neutralized"
            ];

            let delay = 0;
            messages.forEach((msg) => {
                setTimeout(() => {
                    let utterance = new SpeechSynthesisUtterance(msg);
                    utterance.rate = 0.9;
                    utterance.pitch = 0.9;
                    utterance.volume = 1.0;
                    window.speechSynthesis.speak(utterance);
                }, delay);
                delay += 1800;
            });
        }
        </script>

        <button onclick="speakCombatSequence()" style="
            background-color:#00cc66;
            color:black;
            padding:12px 22px;
            border:none;
            border-radius:10px;
            font-size:18px;
            font-weight:bold;
            cursor:pointer;">
            🔊 Play Voice Combat Sequence
        </button>
        """,
        unsafe_allow_html=True
    )

# ============================================================
# 3D CHAMBER ANIMATION HELPERS
# ============================================================

def cylinder_surface_x(x0, x1, radius, color, opacity=0.35):
    theta = np.linspace(0, 2 * np.pi, 50)
    x = np.linspace(x0, x1, 2)
    theta, x = np.meshgrid(theta, x)

    y = radius * np.cos(theta)
    z = radius * np.sin(theta)

    return go.Surface(
        x=x,
        y=y,
        z=z,
        opacity=opacity,
        colorscale=[[0, color], [1, color]],
        showscale=False,
        hoverinfo="skip"
    )

def plasma_sphere(xc, strength):
    u = np.linspace(0, 2*np.pi, 25)
    v = np.linspace(0, np.pi, 15)
    u, v = np.meshgrid(u, v)

    r = 0.18 + 0.35 * strength
    x = xc + r * np.cos(u) * np.sin(v)
    y = r * np.sin(u) * np.sin(v)
    z = r * np.cos(v)

    return go.Surface(
        x=x,
        y=y,
        z=z,
        opacity=0.35,
        colorscale=[[0, "yellow"], [0.5, "orange"], [1, "red"]],
        showscale=False,
        hoverinfo="skip"
    )

def pressure_wave(xc, radius):
    theta = np.linspace(0, 2*np.pi, 40)
    x = np.full_like(theta, xc)
    y = radius * np.cos(theta)
    z = radius * np.sin(theta)

    return go.Scatter3d(
        x=x,
        y=y,
        z=z,
        mode="lines",
        line=dict(color="orange", width=6),
        hoverinfo="skip"
    )

def projectile(xc, length, radius):
    body = cylinder_surface_x(xc - length/2, xc + length/2, radius, "lime", 1.0)

    nose = go.Cone(
        x=[xc + length/2],
        y=[0],
        z=[0],
        u=[0.8],
        v=[0],
        w=[0],
        sizemode="absolute",
        sizeref=0.35,
        colorscale=[[0, "lime"], [1, "lime"]],
        showscale=False,
        hoverinfo="skip"
    )

    return [body, nose]

def exhaust_trail(x0, x1):
    return go.Scatter3d(
        x=[x0, x1],
        y=[0, 0],
        z=[0, 0],
        mode="lines",
        line=dict(color="yellow", width=8),
        opacity=0.45,
        hoverinfo="skip"
    )

# ============================================================
# 3D REAL-TIME STYLE ETC ANIMATION
# ============================================================

st.markdown("## ⚡ Real-Time ETC Chamber Working Animation")

Lc = chamber_length_mm / 1000
Lb = barrel_length_mm / 1000
Dc = chamber_diameter_mm / 1000
Dp = projectile_diameter_mm / 1000

scale = 5.0 / max(Lc + Lb, 1e-6)

chamber_x0 = 0
chamber_x1 = Lc * scale
barrel_x0 = chamber_x1
barrel_x1 = (Lc + Lb) * scale

chamber_r = max((Dc / 2) * scale, 0.32)
barrel_r = max((Dp / 2) * scale, 0.13)

projectile_len = max(Dp * scale * 1.5, 0.35)
projectile_r = barrel_r * 0.85

n_frames = 60
x_positions = np.linspace(barrel_x0 + projectile_len, barrel_x1 - projectile_len/2, n_frames)

time_ms = np.linspace(0, 5, n_frames)
peak_time = 1.0 + 0.4 * (1 - plasma_efficiency)
width = 0.6

pressure_curve = pressure_mpa * np.exp(-((time_ms - peak_time) / width) ** 2)
temperature_curve = 300 + (temperature_k - 300) * np.exp(-((time_ms - peak_time) / (width * 1.15)) ** 2)
velocity_curve = np.minimum(muzzle_velocity * (1 - np.exp(-time_ms / 1.2)), muzzle_velocity)

base_chamber = cylinder_surface_x(chamber_x0, chamber_x1, chamber_r, "lightblue", 0.22)
base_barrel = cylinder_surface_x(barrel_x0, barrel_x1, barrel_r, "gray", 0.32)

axis = go.Scatter3d(
    x=[chamber_x0, barrel_x1],
    y=[0, 0],
    z=[0, 0],
    mode="lines",
    line=dict(color="white", width=3),
    hoverinfo="skip"
)

initial_plasma = plasma_sphere(chamber_x0 + 0.20, 0.25)
initial_wave = pressure_wave(chamber_x0 + 0.25, chamber_r * 0.35)
initial_projectile = projectile(x_positions[0], projectile_len, projectile_r)

state_text = go.Scatter3d(
    x=[chamber_x1 * 0.45],
    y=[-chamber_r * 1.55],
    z=[chamber_r * 1.2],
    mode="text",
    text=[f"t = 0.00 ms<br>P = {pressure_curve[0]:.1f} MPa<br>T = {temperature_curve[0]:.0f} K<br>V = {velocity_curve[0]:.1f} m/s"],
    hoverinfo="skip"
)

base_data = [
    base_chamber,
    base_barrel,
    axis,
    initial_plasma,
    initial_wave,
] + initial_projectile + [
    state_text
]

frames = []

for i in range(n_frames):
    frac = i / (n_frames - 1)

    plasma_strength = np.exp(-((frac - 0.18) / 0.22) ** 2)
    wave_x = chamber_x0 + 0.25 + frac * (barrel_x1 - chamber_x0)

    dynamic = [
        plasma_sphere(chamber_x0 + 0.20, plasma_strength),
        pressure_wave(wave_x, chamber_r * (0.35 + 0.45 * plasma_strength)),
    ]

    dynamic += projectile(x_positions[i], projectile_len, projectile_r)

    if i > 5:
        dynamic.append(exhaust_trail(max(chamber_x0, x_positions[i] - 0.9), x_positions[i] - 0.25))
    else:
        dynamic.append(exhaust_trail(chamber_x0, chamber_x0))

    dynamic.append(
        go.Scatter3d(
            x=[chamber_x1 * 0.45],
            y=[-chamber_r * 1.55],
            z=[chamber_r * 1.2],
            mode="text",
            text=[
                f"t = {time_ms[i]:.2f} ms<br>"
                f"P = {pressure_curve[i]:.1f} MPa<br>"
                f"T = {temperature_curve[i]:.0f} K<br>"
                f"V = {velocity_curve[i]:.1f} m/s"
            ],
            hoverinfo="skip"
        )
    )

    frames.append(go.Frame(data=dynamic, traces=[3,4,5,6,7,8], name=str(i)))

fig = go.Figure(data=base_data, frames=frames)

fig.update_layout(
    height=680,
    template="plotly_dark",
    title="ETC Internal Sequence: Electric Pulse → Plasma → Pressure Wave → Projectile Acceleration",
    scene=dict(
        xaxis=dict(title="Launcher Axis", showgrid=False),
        yaxis=dict(title="Radial Direction", showgrid=False),
        zaxis=dict(title="Radial Direction", showgrid=False),
        aspectmode="manual",
        aspectratio=dict(x=2.6, y=0.75, z=0.75),
        camera=dict(eye=dict(x=1.6, y=-1.7, z=0.85))
    ),
    margin=dict(l=0, r=0, t=50, b=0),
    showlegend=False,
    updatemenus=[
        dict(
            type="buttons",
            showactive=False,
            x=0.03,
            y=1.05,
            buttons=[
                dict(
                    label="▶ Play ETC Chamber Animation",
                    method="animate",
                    args=[
                        None,
                        dict(
                            frame=dict(duration=animation_speed, redraw=True),
                            transition=dict(duration=0),
                            fromcurrent=True,
                            mode="immediate"
                        )
                    ]
                ),
                dict(
                    label="⏸ Pause",
                    method="animate",
                    args=[
                        [None],
                        dict(frame=dict(duration=0, redraw=False), mode="immediate")
                    ]
                )
            ]
        )
    ]
)

st.plotly_chart(fig, use_container_width=True)

# ============================================================
# CURVES
# ============================================================

st.markdown("## 📊 Live Ballistic Curves")

tab1, tab2, tab3 = st.tabs(["Pressure Curve", "Temperature Curve", "Velocity Curve"])

with tab1:
    figp = go.Figure()
    figp.add_trace(go.Scatter(x=time_ms, y=pressure_curve, mode="lines", line=dict(width=4, color="orange")))
    figp.update_layout(template="plotly_dark", height=350, xaxis_title="Time (ms)", yaxis_title="Pressure (MPa)")
    st.plotly_chart(figp, use_container_width=True)

with tab2:
    figt = go.Figure()
    figt.add_trace(go.Scatter(x=time_ms, y=temperature_curve, mode="lines", line=dict(width=4, color="red")))
    figt.update_layout(template="plotly_dark", height=350, xaxis_title="Time (ms)", yaxis_title="Temperature (K)")
    st.plotly_chart(figt, use_container_width=True)

with tab3:
    figv = go.Figure()
    figv.add_trace(go.Scatter(x=time_ms, y=velocity_curve, mode="lines", line=dict(width=4, color="lime")))
    figv.update_layout(template="plotly_dark", height=350, xaxis_title="Time (ms)", yaxis_title="Velocity (m/s)")
    st.plotly_chart(figv, use_container_width=True)

# ============================================================
# DOWNLOAD HTML SIMULATION
# ============================================================

st.markdown("## 📥 Download Simulation")

html = fig.to_html(include_plotlyjs="cdn")

st.download_button(
    label="🌐 Download ETC Chamber 3D Simulation HTML",
    data=html.encode("utf-8"),
    file_name="etc_chamber_real_time_simulation.html",
    mime="text/html"
)

result_df = pd.DataFrame({
    "Parameter": [
        "Propellant Mass",
        "Electric Pulse Energy",
        "Plasma Coupling Efficiency",
        "Peak Pressure",
        "Peak Temperature",
        "Muzzle Velocity",
        "Launch Time",
        "Interception Time",
        "Time Margin"
    ],
    "Value": [
        f"{propellant_mass_g} g",
        f"{electric_pulse_kj} kJ",
        f"{plasma_efficiency:.2f}",
        f"{pressure_mpa:.2f} MPa",
        f"{temperature_k:.0f} K",
        f"{muzzle_velocity:.2f} m/s",
        f"{launch_time:.5f} s",
        f"{interception_time:.4f} s",
        f"{time_margin:.4f} s"
    ]
})

st.table(result_df)

st.download_button(
    label="📥 Download Result CSV",
    data=result_df.to_csv(index=False).encode("utf-8"),
    file_name="etc_chamber_simulation_results.csv",
    mime="text/csv"
)
