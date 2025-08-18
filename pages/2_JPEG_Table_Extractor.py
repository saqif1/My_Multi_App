import streamlit as st
import base64
import os
from openai import OpenAI
import pandas as pd
from io import StringIO

# Set page config
st.set_page_config(
    page_title="AI Table Extractor",  # Simplified name
    page_icon="🖼️",
    layout="wide"
)

# Initialize session state
if 'extracted_data' not in st.session_state:
    st.session_state.extracted_data = []

# App title and description
st.title("📄 Image Table Extractor")
st.markdown("""
Upload images containing tables, and this app will extract the table data using AI.
The extracted data will be displayed below and can be downloaded as CSV.
""")

api_key = "<YOUR_API_KEY>" #st.text_input("OpenRouter API Key", type="password")

# Sidebar for API settings
with st.sidebar:
    st.header("Configurations:")
    model_options = [
        "mistralai/mistral-small-3.2-24b-instruct:free",
        "moonshotai/kimi-vl-a3b-thinking:free",
        "meta-llama/llama-3.2-11b-vision-instruct:free",
        "qwen/qwen2.5-vl-32b-instruct:free",
        "mistralai/mistral-small-3.1-24b-instruct:free",
        "google/gemma-3-4b:free",
        "google/gemma-3-12b:free",
        "google/gemma-3-27b:free",
        "qwen/qwen2.5-vl-72b-instruct:free"
    ]
    selected_model = st.selectbox("Select Model", model_options, index=0)
    st.markdown("---")
    st.markdown("**Note:** This app uses OpenRouter to access various AI models.")

# File uploader
uploaded_files = st.file_uploader(
    "Upload image files (JPEG, PNG)",
    type=["jpeg", "jpg", "png"],
    accept_multiple_files=True
)

def encode_image(uploaded_file):
    return base64.b64encode(uploaded_file.read()).decode('utf-8')

def extract_table(image_base64, filename):
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )
    
    try:
        response = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "http://localhost",
                "X-Title": "Table Extraction App"
            },
            model=selected_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a data extraction expert. Extract table data from images and return it as clean, "
                        "column-aligned CSV. Infer headers if present, otherwise use 'Column1, Column2, ...'. "
                        "Return **only** the CSV data, no additional text."
                        "**DO NOT** include any extraneous text like 'Processing file' or '--- Extracted CSV ---'."
                    )
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract this table as CSV:"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                    ]
                }
            ],
            max_tokens=10000
        )
        
        extracted_csv = response.choices[0].message.content
        return extracted_csv.strip(), None
    except Exception as e:
        return None, str(e)

# Process files when button is clicked
if st.button("Extract Tables") and uploaded_files:
    if not api_key:
        st.error("Please enter your OpenRouter API key")
        st.stop()
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    results = []
    
    for i, uploaded_file in enumerate(uploaded_files):
        status_text.text(f"Processing {i+1}/{len(uploaded_files)}: {uploaded_file.name}")
        progress_bar.progress((i + 1) / len(uploaded_files))
        
        try:
            # Encode image
            image_base64 = encode_image(uploaded_file)
            
            # Extract table
            extracted_csv, error = extract_table(image_base64, uploaded_file.name)
            
            if error:
                results.append({
                    "filename": uploaded_file.name,
                    "status": "Error",
                    "message": error,
                    "data": None
                })
            else:
                # Try to parse CSV
                try:
                    df = pd.read_csv(StringIO(extracted_csv))
                    results.append({
                        "filename": uploaded_file.name,
                        "status": "Success",
                        "message": f"Extracted {len(df)} rows",
                        "data": df
                    })
                except Exception as e:
                    results.append({
                        "filename": uploaded_file.name,
                        "status": "Partial Success",
                        "message": f"Extracted but couldn't parse CSV: {str(e)}",
                        "data": extracted_csv  # Store raw CSV text
                    })
        except Exception as e:
            results.append({
                "filename": uploaded_file.name,
                "status": "Error",
                "message": str(e),
                "data": None
            })
    
    # Store results in session state
    st.session_state.extracted_data = results
    progress_bar.empty()
    status_text.empty()
    st.success("Processing complete!")

# Display results
if st.session_state.extracted_data:
    st.markdown("---")
    st.header("Extraction Results")
    
    for result in st.session_state.extracted_data:
        with st.expander(f"{result['filename']} - {result['status']}"):
            if result['status'] == "Success":
                st.dataframe(result['data'])
                
                # Convert DataFrame to CSV
                csv = result['data'].to_csv(index=False).encode('utf-8')
                
                st.download_button(
                    label=f"Download {result['filename']} as CSV",
                    data=csv,
                    file_name=f"{os.path.splitext(result['filename'])[0]}.csv",
                    mime="text/csv",
                    key=f"download_{result['filename']}"
                )
            elif result['status'] == "Partial Success":
                st.warning(result['message'])
                st.code(result['data'])
                
                # Download raw CSV text
                st.download_button(
                    label=f"Download {result['filename']} as CSV",
                    data=result['data'],
                    file_name=f"{os.path.splitext(result['filename'])[0]}.csv",
                    mime="text/csv",
                    key=f"download_{result['filename']}"
                )
            else:
                st.error(result['message'])
    
    # Combined download option
    if any(result['status'] in ["Success", "Partial Success"] for result in st.session_state.extracted_data):
        st.markdown("---")
        st.subheader("Download All Extracted Data")
        
        # Create a ZIP file with all successful extractions
        import zipfile
        from io import BytesIO
        
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for result in st.session_state.extracted_data:
                if result['status'] in ["Success", "Partial Success"]:
                    filename = f"{os.path.splitext(result['filename'])[0]}.csv"
                    if result['status'] == "Success":
                        content = result['data'].to_csv(index=False)
                    else:
                        content = result['data']
                    zip_file.writestr(filename, content)
        
        st.download_button(
            label="Download All as ZIP",
            data=zip_buffer.getvalue(),
            file_name="extracted_tables.zip",
            mime="application/zip"
        )