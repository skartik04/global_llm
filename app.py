import streamlit as st
import json
import pandas as pd
import ast
import re
import os

st.set_page_config(layout="wide")

# ---------- Load the JSON data ----------
@st.cache_data
def load_data():
    with open("all_features_combined.json") as f:
        return json.load(f)

data = load_data()
request_ids = list(data.keys())

# ---------- User Login ----------
st.sidebar.title("User Identification")
user_id = st.sidebar.text_input("Enter your name or initials", value="user1")

if not user_id:
    st.warning("Please enter your name or initials to proceed.")
    st.stop()

user_filename = f"evaluations_{user_id}.csv"

if st.sidebar.button("Start Fresh CSV"):
    # Clear in-memory evaluations and reset navigation
    st.session_state.evals = []
    st.session_state.req_index = 0
    st.session_state.selected_section = None

    # Delete old CSV if exists
    if os.path.exists(user_filename):
        os.remove(user_filename)

    # Create empty CSV with headers
    pd.DataFrame(columns=["request_id", "section", "rating", "comment"]).to_csv(user_filename, index=False)

    st.success("Started a fresh evaluation CSV. Beginning from the first request.")



def load_user_evals(user_id):
    filename = f"evaluations_{user_id}.csv"
    if os.path.exists(filename):
        return pd.read_csv(filename).to_dict("records")
    return []

if "user_id" not in st.session_state or st.session_state.get("user_id") != user_id:
    st.session_state.user_id = user_id
    st.session_state.evals = load_user_evals(user_id)

    # Set req_index to last evaluated request if possible
    if st.session_state.evals:
        last_eval = st.session_state.evals[-1]
        last_req_id = last_eval.get("request_id")
        last_section = last_eval.get("section")

        if last_req_id in request_ids:
            st.session_state.req_index = request_ids.index(last_req_id)
        else:
            st.session_state.req_index = 0

        st.session_state.selected_section = last_section
    else:
        st.session_state.req_index = 0
        st.session_state.selected_section = None


# ---------- Session State ----------
if "req_index" not in st.session_state:
    st.session_state.req_index = 0
if "selected_section" not in st.session_state:
    st.session_state.selected_section = None

# ---------- UI Header ----------
st.title("LLM Structured Output Evaluation")

# ---------- Navigation ----------
col1, col2, col3 = st.columns([1, 2, 1])
with col1:
    if st.button("Previous") and st.session_state.req_index > 0:
        st.session_state.req_index -= 1
        st.session_state.selected_section = None
with col3:
    if st.button("Next") and st.session_state.req_index < len(request_ids) - 1:
        st.session_state.req_index += 1
        st.session_state.selected_section = None

# ---------- Current Request ----------
req_id = request_ids[st.session_state.req_index]
st.markdown(f"### Request: `{req_id}`")

sections = list(data[req_id].keys())

# ---------- Select Structured Output ----------
selected_section = st.radio(
    "Choose output to evaluate:",
    sections,
    index=0 if st.session_state.selected_section is None else sections.index(st.session_state.selected_section)
)
st.session_state.selected_section = selected_section

entry = data[req_id][selected_section]
raw_input = entry.get("raw_input", "")
reasoning = entry.get("reasoning", "")
structured_output = {k: v for k, v in entry.items() if k not in ["raw_input", "reasoning"]}

# ---------- Display Raw Input ----------
st.markdown("#### Raw Input")

def render_raw_input(raw_input):
    try:
        if isinstance(raw_input, dict):
            st.json(raw_input)
            return
        if isinstance(raw_input, str):
            match = re.search(r"\{.*\}", raw_input, re.DOTALL)
            if match:
                dict_str = match.group(0)
                parsed = ast.literal_eval(dict_str)
                if isinstance(parsed, dict):
                    st.json(parsed)
                    return
    except Exception as e:
        st.warning(f"Could not parse raw_input as a dictionary: {e}")
    
    # Fallback: render as plain text
    st.markdown(
        f"""<div style="background-color:#262730;padding:15px;border-radius:6px;color:white;white-space:pre-wrap;">{raw_input}</div>""",
        unsafe_allow_html=True
    )

render_raw_input(raw_input)

# ---------- Display Reasoning ----------
st.markdown("#### Reasoning")
st.markdown(
    f"""<div style="background-color:#1e1e1e;padding:15px;border-radius:6px;color:white;white-space:pre-wrap;">{reasoning}</div>""",
    unsafe_allow_html=True
)

# ---------- Display Structured Output ----------
st.markdown("#### Structured Output")
st.json(structured_output)

# ---------- Evaluation Form ----------
st.markdown("#### Your Evaluation")
rating = st.radio("How would you rate this output?", ["Correct", "Incorrect", "Ambiguous"], horizontal=True)
comment = st.text_area("Comment (optional):")

if st.button("Save Evaluation"):
    eval_entry = {
        "request_id": req_id,
        "section": selected_section,
        "rating": rating,
        "comment": comment
    }

    # Overwrite if it already exists
    existing_idx = next(
        (i for i, entry in enumerate(st.session_state.evals)
         if entry["request_id"] == req_id and entry["section"] == selected_section),
        None
    )

    if existing_idx is not None:
        st.session_state.evals[existing_idx] = eval_entry
    else:
        st.session_state.evals.append(eval_entry)

    # Save to user-specific CSVs
    pd.DataFrame(st.session_state.evals).to_csv(user_filename, index=False)

    st.success(f"Saved evaluation for `{req_id}` → `{selected_section}`")


# ---------- Download CSV ----------
if st.session_state.evals:
    eval_df = pd.DataFrame(st.session_state.evals)
    csv = eval_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="📥 Download Your Evaluation",
        data=csv,
        file_name=user_filename,
        mime="text/csv"
    )