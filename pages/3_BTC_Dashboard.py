import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import openai
import os
from datetime import datetime, timezone, timedelta

# Config
DATA_DIR = Path("/home/ec2-user/My_Multi_App/data/App3_Data") #readline -f
DATA_FILE = DATA_DIR / "volatility_data.csv"

st.set_page_config(
    page_title="BTC Volatility Smile Dashboard",
    page_icon="₿",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/your-repo/issues',
        'Report a bug': "https://github.com/your-repo/issues",
        'About': """
        ## ₿ BTC Options Volatility Dashboard
        **Track Deribit's BTC option volatility smiles across expiries**

        *Data updates every 10 minutes*
        """
    }
)

# Add this function to get the file modification time
def get_last_modified_time(filepath):
    try:
        mod_time = os.path.getmtime(filepath)
        
        # 1. Get timestamp with UTC timezone awareness
        utc_time = datetime.fromtimestamp(mod_time, tz=timezone.utc)
        
        # 2. Convert to Singapore Time (UTC+8)
        sg_offset = timedelta(hours=8)
        sg_time = utc_time.astimezone(timezone(sg_offset))
        
        return sg_time.strftime('%Y-%m-%d %H:%M:%S (UTC+8)')
    except Exception as e:
        return f"Error: {e}"


# Load data
@st.cache_data
def load_data(filepath):
    df = pd.read_csv(filepath)
    df['expiry_date'] = pd.to_datetime(df['expiry_date'])
    return df

try:
    data = load_data(DATA_FILE)
except FileNotFoundError:
    st.error("Data file not found. Please ensure the file is in the correct directory.")
    st.stop()

# Sidebar filters
st.sidebar.header("Filters")
selected_expiries = st.sidebar.multiselect(
    "Select Expiry Dates",
    options=sorted(data['expiry_date'].dt.date.unique()),
    default=sorted(data['expiry_date'].dt.date.unique())[:3]
)
selected_option_type = st.sidebar.multiselect(
    "Select Option Type",
    options=data['option_type'].unique(),
    default=data['option_type'].unique()
)

# Filter data
filtered_data = data[
    (data['expiry_date'].dt.date.isin(selected_expiries)) &
    (data['option_type'].isin(selected_option_type))
]

# Main content
st.title("₿ BTC Volatility Smile Dashboard")
st.markdown("""
    **Visualize implied volatility for BTC options across strike prices and expiries.**
""")

# Add this line here
last_updated = get_last_modified_time(DATA_FILE)
st.caption(f"🔄 Last data fetched: {last_updated}")

# Plot
fig = px.line(
    filtered_data,
    x='strike',
    y='implied_volatility',
    color='expiry_date',
    symbol='option_type',
    title='BTC Volatility Smile by Expiry Date',
    labels={'strike': 'Strike Price', 'implied_volatility': 'Implied Volatility (%)'},
    hover_data=['option_type']
)
fig.update_layout(
    xaxis_title='Strike Price',
    yaxis_title='Implied Volatility (%)',
    legend_title_text='Expiry Date',
    hovermode='x unified'
)
# Plot the smile
st.plotly_chart(fig, use_container_width=True)

# AI Analysis Section
st.subheader("AI Market Analysis")

if st.button("Generate Analysis"):
    with st.spinner("Analysing volatility data..."):
        try:
            client = openai.OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key="<YOU_OPENROUTER_API_KEY>"
            )
            
            response = client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "http://localhost:8501",
                    "X-Title": "BTC Volatility Dashboard"
                },
                model="deepseek/deepseek-r1-0528-qwen3-8b:free",
                model= "mistralai/mistral-small-3.2-24b-instruct:free", #"deepseek/deepseek-r1-0528-qwen3-8b:free",
                messages=[
                    {
                        "role": "system",
                        "content": """
                        You are a professional Bitcoin market analyst.
                        Your task is to analyze BTC options data to interpret the volatility smile/skew for each expiry date.
                        For each expiry, plot the implied volatility against the strike price, identify the skew type (smile, downward skew, upward skew, or reverse skew), and infer market sentiment (bullish, bearish, or neutral).
                        Based on the skew, recommend whether to go long BTC ETF or long BTC inverse ETF.
                        Summarize your findings in a table with the following columns: Expiry Date, Skew Type, Market Sentiment, and Suggested Position.
                        Highlight any unusual patterns or strong signals.
                        """
                    },
                    {
                        "role": "user",
                        "content": f"""
                        Analyze this BTC options data:
                        {filtered_data.to_string()}

                        Provide the following:
                        1. Interpretation of the skew type and market sentiment for each expiry.
                        2. A recommendation for long BTC ETF or long BTC inverse ETF for each expiry.
                        3. A summary table of the results.
                        """
                    }
                ]
                #,max_tokens=100000  # Reduced from 100000 to a reasonable value
            )
            
            # Display the raw analysis in a clean box
            analysis_text = response.choices[0].message.content
            st.markdown(
                f"""
                <div style='
                    <!--background-color: #f8f9fa;-->
                    padding: 15px;
                    border-radius: 8px;
                    border-left: 4px solid #4e73df;
                    margin: 10px 0;
                '>
                    {analysis_text}
                </div>
                """,
                unsafe_allow_html=True
            )
            
        except Exception as e:
            st.error(f"Analysis failed: {str(e)}")

# Data preview
st.subheader("Data Preview")
st.dataframe(filtered_data.sort_values(['expiry_date', 'strike']), use_container_width=True)

# LinkedIN
st.markdown("---")
st.markdown("### Connect with Me!")

st.markdown("""
<a href="https://www.linkedin.com/in/saqif-juhaimee-17322a119/">
    <img src="https://upload.wikimedia.org/wikipedia/commons/c/ca/LinkedIn_logo_initials.png" width="20">
    Saqif Juhaimee
</a>
""", unsafe_allow_html=True)
