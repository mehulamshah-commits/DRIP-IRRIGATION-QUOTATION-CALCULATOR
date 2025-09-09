
# app.py
import streamlit as st
import pandas as pd
import math
from io import StringIO

st.set_page_config(page_title="Drip Qty & Quotation (Prototype)", layout="wide")

st.title("Drip Irrigation — Quantity & Quotation Prototype")
st.write("Enter field/layout, emitter & hydraulic rules. App adds lateral max-length checks and filter selection based on water source.")

#
# -------- DEFAULT PRICES (editable) --------
#
DEFAULT_PRICES = {
    "drip_16mm_per_m": {"label": "Drip Lateral 16mm (per m)", "unit": "m", "price": 17.0},
    "drip_20mm_per_m": {"label": "Drip Lateral 20mm (per m)", "unit": "m", "price": 19.5},
    "pvc_submain_50mm_per_m": {"label": "PVC Submain 50mm (per m)", "unit": "m", "price": 120.0},
    "control_valve_50mm": {"label": "Control Valve 50mm", "unit": "pcs", "price": 950.0},
    "flush_valve_50mm": {"label": "Flush Valve 50mm", "unit": "pcs", "price": 450.0},
    "air_release_valve": {"label": "Air Release Valve", "unit": "pcs", "price": 650.0},
    "take_off_16mm": {"label": "Take-off 16mm", "unit": "pcs", "price": 4.0},
    "grommet_16mm": {"label": "Grommet 16mm", "unit": "pcs", "price": 3.0},
    "end_cap_16mm": {"label": "End Cap 16mm", "unit": "pcs", "price": 5.0},
    "joiner_16mm": {"label": "Joiner 16mm", "unit": "pcs", "price": 4.0},
    "filter_screen_2in": {"label": "Screen/Disc Filter 2\" (50mm)", "unit": "pcs", "price": 2400.0},
    "hydrocyclone": {"label": "Hydrocyclone (sand separator)", "unit": "pcs", "price": 6000.0},
    "media_filter": {"label": "Media / Sand Filter (set)", "unit": "set", "price": 15000.0},
    "fertigation_venturi": {"label": "Fertigation Venturi", "unit": "set", "price": 3500.0},
    "misc_pct": {"label": "Wastage / Misc (%)", "unit": "%", "price": 3.0}
}

#
# -------- LAYOUT INPUTS --------
#
st.sidebar.header("Layout & Inputs")
length_m = st.sidebar.number_input("Field length (m)", min_value=1.0, value=200.0, step=1.0)
width_m  = st.sidebar.number_input("Field width (m)",  min_value=1.0, value=100.0, step=1.0)
bed_spacing = st.sidebar.number_input("Bed / row spacing (m)", min_value=0.1, value=1.5, step=0.1)
laterals_along_length = st.sidebar.checkbox("Laterals run along LENGTH (otherwise along WIDTH)", value=True)

st.sidebar.header("Emitters & Hydraulics")
emitter_spacing_m = st.sidebar.number_input("Emitter spacing on lateral (m)", min_value=0.05, value=0.30, step=0.05)
emitter_lph = st.sidebar.number_input("Emitter discharge (LPH)", value=4.0, step=0.5)
laterals_per_valve = st.sidebar.number_input("Laterals per control valve (design zoning)", min_value=1, value=20, step=1)
submain_runs = st.sidebar.number_input("Submain runs (qty)", min_value=1, value=1, step=1)
submain_length = st.sidebar.number_input("Submain length per run (m)", min_value=0.0, value=100.0, step=1.0)

st.sidebar.header("Lateral Options")
lateral_dia = st.sidebar.selectbox("Select lateral diameter", options=["16mm","20mm"], index=0)

st.sidebar.header("Water & Filtration")
water_source = st.sidebar.selectbox("Water source", options=["Borewell (clean groundwater)","Open well / Canal (moderate solids)","Recycled / Dirty water (high solids)"], index=0)
include_fertigation = st.sidebar.checkbox("Include fertigation (venturi)", value=False)

st.sidebar.header("Prices (editable)")
prices = {}
for k,v in DEFAULT_PRICES.items():
    prices[k] = st.sidebar.number_input(f"{v['label']} ({v['unit']})", value=float(v['price']), min_value=0.0, step=1.0, key=k)

#
# -------- RULES: MAX LATERAL LENGTHS --------
#
MAX_RUN_16MM = 100.0
MAX_RUN_20MM = 150.0

max_allowed = MAX_RUN_16MM if lateral_dia=="16mm" else MAX_RUN_20MM

#
# -------- CALCULATIONS --------
#
rows = int((width_m // bed_spacing) if laterals_along_length else (length_m // bed_spacing))
lateral_length = length_m if laterals_along_length else width_m
total_lateral_length = rows * lateral_length

emitters_per_lateral = math.ceil(lateral_length / emitter_spacing_m) + 1
total_emitters = emitters_per_lateral * rows

if lateral_length <= max_allowed:
    laterals_per_bed = 1
    zones_multiplier = 1
    note_split = None
else:
    parts_needed = math.ceil(lateral_length / max_allowed)
    laterals_per_bed = parts_needed
    zones_multiplier = parts_needed
    note_split = f"Lateral length {lateral_length:.1f} m exceeds recommended {max_allowed:.0f} m for {lateral_dia}. Suggest splitting each lateral into {parts_needed} runs (or use larger dia if hydraulically ok)."

effective_rows = rows * laterals_per_bed
effective_total_lateral_len = effective_rows * (lateral_length / laterals_per_bed)
emitters_per_split_lateral = math.ceil((lateral_length / laterals_per_bed) / emitter_spacing_m) + 1
total_emitters_after_split = emitters_per_split_lateral * effective_rows

valves = math.ceil(effective_rows / laterals_per_valve)
control_valves = max(1, valves)
flush_valves = int(submain_runs)
air_release_valves = max(1, math.ceil(submain_runs / 2))

takeoffs = effective_rows
grommets = effective_rows
endcaps = effective_rows
joiners = max(0, math.ceil(0.02 * effective_total_lateral_len))

misc_pct = prices["misc_pct"] / 100.0

bom = []

lateral_price_per_m = prices["drip_16mm_per_m"] if lateral_dia=="16mm" else prices["drip_20mm_per_m"]
bom.append({"item": f"Drip lateral {lateral_dia} (m)", "unit": "m", "qty": math.ceil(effective_total_lateral_len*(1+misc_pct)), "rate": lateral_price_per_m})
bom.append({"item": "PVC submain 50mm (m)", "unit":"m","qty": math.ceil(submain_runs * submain_length * (1+misc_pct)), "rate": prices["pvc_submain_50mm_per_m"]})
bom.append({"item": "Control valve 50mm", "unit":"pcs","qty": control_valves, "rate": prices["control_valve_50mm"]})
bom.append({"item":"Flush valve 50mm","unit":"pcs","qty":flush_valves,"rate":prices["flush_valve_50mm"]})
bom.append({"item":"Air release valve","unit":"pcs","qty":air_release_valves,"rate":prices["air_release_valve"]})
bom.append({"item":"Take-off 16mm","unit":"pcs","qty": math.ceil(takeoffs*(1+misc_pct)), "rate": prices["take_off_16mm"]})
bom.append({"item":"Grommet 16mm","unit":"pcs","qty": math.ceil(grommets*(1+misc_pct)), "rate": prices["grommet_16mm"]})
bom.append({"item":"End cap 16mm","unit":"pcs","qty": math.ceil(endcaps*(1+misc_pct)), "rate": prices["end_cap_16mm"]})
bom.append({"item":"Joiner 16mm (est)","unit":"pcs","qty": joiners, "rate": prices["joiner_16mm"]})

if water_source.startswith("Borewell"):
    bom.append({"item":"Screen/Disc filter 2\" (50mm)", "unit":"pcs", "qty":1, "rate":prices["filter_screen_2in"]})
elif water_source.startswith("Open well") :
    bom.append({"item":"Hydrocyclone / Sand Separator", "unit":"pcs", "qty":1, "rate":prices["hydrocyclone"]})
    bom.append({"item":"Screen/Disc filter 2\" (50mm)", "unit":"pcs", "qty":1, "rate":prices["filter_screen_2in"]})
else:
    bom.append({"item":"Media / Sand Filter (set)", "unit":"set","qty":1,"rate":prices["media_filter"]})
    bom.append({"item":"Hydrocyclone / Sand Separator", "unit":"pcs", "qty":1, "rate":prices["hydrocyclone"]})
    bom.append({"item":"Screen/Disc filter 2\" (50mm)", "unit":"pcs", "qty":1, "rate":prices["filter_screen_2in"]})

if include_fertigation:
    bom.append({"item":"Fertigation venturi", "unit":"set", "qty":1, "rate": prices["fertigation_venturi"]})

for l in bom:
    l["amount"] = l["qty"] * l["rate"]

subtotal = sum([l["amount"] for l in bom])
gst_rate = 0.05
gst_amount = subtotal * gst_rate
grand_total = subtotal + gst_amount

col1, col2 = st.columns([2,1])

with col1:
    st.header("Design Summary")
    st.write(f"Rows / laterals (original): **{rows}**")
    st.write(f"Lateral length (each): **{lateral_length:.1f} m**")
    st.write(f"Total lateral length (original): **{total_lateral_length:.1f} m**")
    st.write("---")
    st.write("**After applying lateral max-length checks**:")
    st.write(f"Selected lateral dia: **{lateral_dia}** (max recommended run: {max_allowed:.0f} m)")
    if note_split:
        st.warning(note_split)
    st.write(f"Effective laterals (rows × splits): **{effective_rows}**")
    st.write(f"Total effective lateral length: **{effective_total_lateral_len:.1f} m**")
    st.write(f"Emitters per lateral (after split): **{emitters_per_split_lateral}**")
    st.write(f"Total emitters (after split): **{total_emitters_after_split}**")
    st.write(f"Control valves needed (est): **{control_valves}**")
    st.write(f"Submain runs: **{submain_runs}** (each {submain_length:.1f} m)")
    st.write("---")
    st.info("Note: hydraulic design (pressure, flow) should still be validated for long runs or heavy emitter counts. This tool uses conservative max-length heuristics.")

with col2:
    st.header("Quick Cost")
    st.metric("Subtotal (excl. GST)", f"₹ {subtotal:,.0f}")
    st.metric("GST assumed", f"{int(gst_rate*100)}%")
    st.metric("Grand total (incl. GST)", f"₹ {grand_total:,.0f}")
    st.write("")
    if st.button("Export BOM as CSV"):
        df = pd.DataFrame(bom)[["item","unit","qty","rate","amount"]]
        csv = df.to_csv(index=False)
        st.download_button("Download CSV", data=csv, file_name="drip_bom.csv", mime="text/csv")

st.header("Bill of Materials (editable prices from sidebar)")
df_bom = pd.DataFrame(bom)[["item","unit","qty","rate","amount"]]
st.dataframe(df_bom.style.format({"rate":"{:.2f}","amount":"{:.2f}"}), height=340)

st.markdown("---")
st.subheader("Assumptions & notes")
st.markdown("""
- Lateral max-run values are conservative defaults (16mm: 100m, 20mm: 150m). Adjust based on emitter type and pressure.
- Filter recommendations:
  - Borewell: Screen/disc filter usually sufficient.
  - Open well / canal: Hydrocyclone + Screen recommended.
  - Recycled / dirty: Media/sand + Hydrocyclone + Screen recommended.
- Prices seeded from retail listings (Jain/Finolex) — edit the sidebar numbers to reflect your supplier prices before issuing a quotation.
- This prototype does not perform full hydraulic calculations (pressure loss, head-loss curves). Use as fast quoting + quantity tool; add hydraulic checks later for design sign-off.
""")

st.markdown("----")
st.caption("Prototype — change default unit prices in the sidebar before exporting quotations.")
