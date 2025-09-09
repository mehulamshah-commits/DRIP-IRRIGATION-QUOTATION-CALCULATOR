# app.py - Drip Irrigation Quantity & Quotation Tool (v3 fully working)
import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="🌱 Drip Irrigation Designer", layout="wide")

st.title("🌱 Drip Irrigation Quantity & Quotation Tool (v3)")

# ---------------- DEFAULT PRICES ----------------
DEFAULT_PRICES = {
    "drip_16mm_per_m": 17.0,
    "drip_20mm_per_m": 19.5,
    "pvc_submain_50mm_per_m": 120.0,
    "pvc_submain_63mm_per_m": 160.0,
    "pvc_submain_75mm_per_m": 220.0,
    "pvc_main_90mm_per_m": 400.0,
    "control_valve_50mm": 950.0,
    "flush_valve_50mm": 450.0,
    "air_release_valve": 650.0,
    "take_off_16mm": 4.0,
    "grommet_16mm": 3.0,
    "end_cap_16mm": 5.0,
    "joiner_16mm": 4.0,
    "filter_2in": 2400.0,
    "filter_2_5in": 3800.0,
    "filter_3in": 5200.0,
    "hydrocyclone": 6000.0,
    "media_filter": 15000.0,
    "fertigation_venturi": 3500.0,
    "misc_pct": 5.0
}

# ---------------- INPUTS ----------------
with st.sidebar:
    st.header("🌱 Field Inputs")
    length_m = st.number_input("Field length (m)", min_value=1.0, value=200.0, step=1.0)
    width_m  = st.number_input("Field width (m)",  min_value=1.0, value=100.0, step=1.0)
    bed_spacing = st.number_input("Bed / row spacing (m)", min_value=0.1, value=1.5, step=0.1)
    laterals_along_length = st.checkbox("Laterals run along LENGTH", value=True)

    st.header("💧 Emitters")
    emitter_spacing_m = st.number_input("Emitter spacing on lateral (m)", min_value=0.05, value=0.30, step=0.05)
    emitter_lph = st.number_input("Emitter discharge (LPH)", value=4.0, step=0.5)

    st.header("⚙️ System (optional)")
    mainline_length = st.number_input("Mainline length (m)", min_value=0.0, value=50.0, step=1.0)
    pump_capacity_m3hr = st.number_input("Pump capacity (m3/hr)", min_value=0.0, value=0.0, step=0.1)

    st.header("🚰 Water & Filtration")
    water_source = st.selectbox("Water source", ["Borewell (clean)", "Open well / Canal", "Recycled / Dirty water"])
    include_fertigation = st.checkbox("Include fertigation (venturi)", value=False)

    st.header("💰 Prices (editable)")
    prices = {}
    for k,v in DEFAULT_PRICES.items():
        prices[k] = st.number_input(f"{k}", value=float(v), min_value=0.0, step=1.0, key=k)

# ---------------- CALCULATIONS ----------------
MAX_RUN_16MM = 100.0
MAX_RUN_20MM = 150.0
LATERAL_FLOW_THRESH_16MM_LPH = 200.0
SAFE_VALVE_FLOW_M3HR = 5.0
misc_pct = prices["misc_pct"] / 100.0

rows = int((width_m // bed_spacing) if laterals_along_length else (length_m // bed_spacing))
lateral_length = length_m if laterals_along_length else width_m
emitters_per_lateral = math.ceil(lateral_length / emitter_spacing_m) + 1
flow_per_lateral_lph = emitters_per_lateral * emitter_lph
flow_per_lateral_m3hr = flow_per_lateral_lph * 0.001

auto_lateral = "16mm"
if lateral_length > MAX_RUN_16MM or flow_per_lateral_lph > LATERAL_FLOW_THRESH_16MM_LPH:
    auto_lateral = "20mm"

laterals_per_bed = 1
if lateral_length > (MAX_RUN_16MM if auto_lateral=="16mm" else MAX_RUN_20MM):
    laterals_per_bed = math.ceil(lateral_length / (MAX_RUN_16MM if auto_lateral=="16mm" else MAX_RUN_20MM))
effective_rows = rows * laterals_per_bed
effective_total_lateral_len = effective_rows * (lateral_length / laterals_per_bed)
emitters_per_split_lateral = math.ceil((lateral_length / laterals_per_bed) / emitter_spacing_m) + 1
flow_per_split_lateral_m3hr = emitters_per_split_lateral * emitter_lph * 0.001

laterals_per_valve = max(1,int(SAFE_VALVE_FLOW_M3HR / flow_per_split_lateral_m3hr)) if flow_per_split_lateral_m3hr>0 else 1
valves_needed = math.ceil(effective_rows / laterals_per_valve)
control_valves = max(1,valves_needed)

# Submain sizing
def choose_submain_dia(flow_m3hr):
    if flow_m3hr <= 3.0:
        return "50mm", prices["pvc_submain_50mm_per_m"]
    elif flow_m3hr <= 6.0:
        return "63mm", prices["pvc_submain_63mm_per_m"]
    elif flow_m3hr <= 12.0:
        return "75mm", prices["pvc_submain_75mm_per_m"]
    else:
        return "90mm", prices["pvc_main_90mm_per_m"]

flow_per_valve_m3hr = flow_per_split_lateral_m3hr * laterals_per_valve
submain_dia, submain_rate = choose_submain_dia(flow_per_valve_m3hr)

# Filter sizing
def choose_filter_size(flow_m3hr):
    if flow_m3hr <= 6.0:
        return "2\"", prices["filter_2in"]
    elif flow_m3hr <= 12.0:
        return "2.5\"", prices["filter_2_5in"]
    else:
        return "3\"", prices["filter_3in"]

total_flow_m3hr = flow_per_split_lateral_m3hr * effective_rows
filter_dia, filter_rate = choose_filter_size(total_flow_m3hr)

# Mainline sizing
def choose_mainline_dia(flow_m3hr):
    if flow_m3hr <= 6.0:
        return "63mm", prices["pvc_submain_63mm_per_m"]
    elif flow_m3hr <= 12.0:
        return "75mm", prices["pvc_submain_75mm_per_m"]
    else:
        return "90mm", prices["pvc_main_90mm_per_m"]

mainline_dia, mainline_rate = choose_mainline_dia(total_flow_m3hr)

# BOM
takeoffs = effective_rows
grommets = effective_rows
endcaps = effective_rows
joiners = max(1,int(0.02*effective_total_lateral_len))

bom = []
lateral_price = prices["drip_16mm_per_m"] if auto_lateral=="16mm" else prices["drip_20mm_per_m"]
bom.append({"item": f"Drip lateral {auto_lateral} (m)", "unit":"m","qty":effective_total_lateral_len*(1+misc_pct),"rate":lateral_price})
bom.append({"item": f"PVC submain {submain_dia} (m)", "unit":"m","qty":effective_rows*(lateral_length/2)*(1+misc_pct),"rate":submain_rate})
bom.append({"item":"Control valve 50mm","unit":"pcs","qty":control_valves,"rate":prices["control_valve_50mm"]})
bom.append({"item":"Take-off 16mm","unit":"pcs","qty":takeoffs*(1+misc_pct),"rate":prices["take_off_16mm"]})
bom.append({"item":"Grommet 16mm","unit":"pcs","qty":grommets*(1+misc_pct),"rate":prices["grommet_16mm"]})
bom.append({"item":"End cap 16mm","unit":"pcs","qty":endcaps*(1+misc_pct),"rate":prices["end_cap_16mm"]})
bom.append({"item":"Joiner 16mm","unit":"pcs","qty":joiners,"rate":prices["joiner_16mm"]})
bom.append({"item":f"Mainline {mainline_dia} (m)","unit":"m","qty":mainline_length*(1+misc_pct),"rate":mainline_rate})

if water_source.startswith("Borewell"):
    bom.append({"item":f"Screen/Disc filter {filter_dia}","unit":"pcs","qty":1,"rate":filter_rate})
elif water_source.startswith("Open well"):
    bom.append({"item":"Hydrocyclone","unit":"pcs","qty":1,"rate":prices["hydrocyclone"]})
    bom.append({"item":f"Screen/Disc filter {filter_dia}","unit":"pcs","qty":1,"rate":filter_rate})
else:
    bom.append({"item":"Media Filter","unit":"set","qty":1,"rate":prices["media_filter"]})
    bom.append({"item":"Hydrocyclone","unit":"pcs","qty":1,"rate":prices["hydrocyclone"]})
    bom.append({"item":f"Screen/Disc filter {filter_dia}","unit":"pcs","qty":1,"rate":filter_rate})

if include_fertigation:
    bom.append({"item":"Fertigation Venturi","unit":"set","qty":1,"rate":prices["fertigation_venturi"]})

for l in bom:
    l["amount"] = l["qty"] * l["rate"]

bom_df = pd.DataFrame(bom)
subtotal = bom_df["amount"].sum()
gst_rate = 0.05
gst_amount = subtotal*gst_rate
grand_total = subtotal + gst_amount

# ---------------- UI: TABS ----------------
tab1, tab2, tab3 = st.tabs(["🌱 Inputs Summary", "📊 Design Summary", "🧾 Quotation / BOM"])

with tab1:
    st.subheader("✅ Inputs Overview")
    st.write(f"- Field: {length_m} m × {width_m} m")
    st.write(f"- Bed spacing: {bed_spacing} m")
    st.write(f"- Laterals along: {'Length' if laterals_along_length else 'Width'}")
    st.write(f"- Emitters: {emitter_lph} LPH @ {emitter_spacing_m} m spacing")
    st.write(f"- Water source: {water_source}")
    if pump_capacity_m3hr>0:
        st.write(f"- Pump capacity: {pump_capacity_m3hr} m³/hr")
    st.write(f"- Fertigation: {'Included' if include_fertigation else 'Not included'}")

with tab2:
    st.subheader("📊 Design Summary")
    st.success(f"Lateral chosen: {auto_lateral}")
    st.info(f"Effective laterals: {effective_rows}")
    st.info(f"Emitters per lateral: {emitters_per_split_lateral}")
    st.info(f"Flow per lateral: {flow_per_split_lateral_m3hr:.3f} m³/hr")
    st.info(f"Control valves needed: {control_valves}")
    st.info(f"Submain dia: {submain_dia}")
    st.info(f"Mainline dia: {mainline_dia}")
    st.info(f"Filter: {filter_dia}")
   
