import streamlit as st
import json
import os
import pandas as pd
import ast
st.set_page_config(layout="wide")
# ---------- Load the JSON data ----------
@st.cache_data
def load_data():
    with open("all_features_combined.json") as f:
        return json.load(f)

data = load_data()
request_ids = list(data.keys())

# ---------- Session State ----------
if "req_index" not in st.session_state:
    st.session_state.req_index = 0
if "selected_section" not in st.session_state:
    st.session_state.selected_section = None

# ---------- UI Header ----------
st.title("🧠 LLM Structured Output Evaluation")

# ---------- Navigation ----------
col1, col2, col3 = st.columns([1, 2, 1])
with col1:
    if st.button("⬅️ Previous") and st.session_state.req_index > 0:
        st.session_state.req_index -= 1
        st.session_state.selected_section = None
with col3:
    if st.button("Next ➡️") and st.session_state.req_index < len(request_ids) - 1:
        st.session_state.req_index += 1
        st.session_state.selected_section = None

# ---------- Current Request ----------
req_id = request_ids[st.session_state.req_index]
st.markdown(f"### 📝 Request: `{req_id}`")

sections = list(data[req_id].keys())

# ---------- Select Structured Output ----------
selected_section = st.radio("Choose output to evaluate:", sections, index=0 if st.session_state.selected_section is None else sections.index(st.session_state.selected_section))
st.session_state.selected_section = selected_section

entry = data[req_id][selected_section]
raw_input = entry.get("raw_input", "")
reasoning = entry.get("reasoning", "")
structured_output = {k: v for k, v in entry.items() if k not in ["raw_input", "reasoning"]}

# ---------- Display Raw Input ----------
st.markdown("#### 📄 Raw Input")

def render_raw_input(raw_input):
    import re
    try:
        # Case 1: it's already a dictionary
        if isinstance(raw_input, dict):
            st.json(raw_input)
            return

        # Case 2: string that contains a dictionary (e.g., starts with "Prescription: {")
        if isinstance(raw_input, str):
            match = re.search(r"\{.*\}", raw_input, re.DOTALL)
            if match:
                dict_str = match.group(0)
                parsed = ast.literal_eval(dict_str)
                if isinstance(parsed, dict):
                    st.json(parsed)
                    return
    except Exception as e:
        st.warning(f"⚠️ Could not parse raw_input as a dictionary: {e}")

    # Fallback: render as plain text in a dark box
    st.markdown(
        f"""<div style="background-color:#262730;padding:15px;border-radius:6px;color:white;white-space:pre-wrap;">{raw_input}</div>""",
        unsafe_allow_html=True
    )

render_raw_input(raw_input)

# ---------- Display Reasoning ----------
st.markdown("#### 🧠 Reasoning")
st.markdown(
    f"""<div style="background-color:#1e1e1e;padding:15px;border-radius:6px;color:white;white-space:pre-wrap;">{reasoning}</div>""",
    unsafe_allow_html=True
)

# ---------- Display Structured Output ----------
st.markdown("#### 📦 Structured Output")
st.json(structured_output)

# ---------- Evaluation Form ----------
st.markdown("#### 📝 Your Evaluation")
rating = st.radio("How would you rate this output?", ["Correct", "Incorrect", "Ambiguous"], horizontal=True)
comment = st.text_area("Comment (optional):")

if st.button("💾 Save Evaluation"):
    eval_entry = {
        "request_id": req_id,
        "section": selected_section,
        "rating": rating,
        "comment": comment
    }

    eval_df = pd.DataFrame([eval_entry])
    if os.path.exists("evaluations.csv"):
        eval_df.to_csv("evaluations.csv", mode="a", index=False, header=False)
    else:
        eval_df.to_csv("evaluations.csv", index=False)

        st.success(f"Saved evaluation for `{req_id}` → `{selected_section}`")

    # --- Add CSV download button ---
    if os.path.exists("evaluations.csv"):
        with open("evaluations.csv", "rb") as f:
            st.download_button(
                label="📥 Download Your Evaluation",
                data=f,
                file_name="evaluations.csv",
                mime="text/csv"
            )