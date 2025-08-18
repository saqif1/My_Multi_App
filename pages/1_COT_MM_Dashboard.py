import cot_reports as cot
import pandas as pd
import numpy as np
import datetime
from scipy import stats # Import scipy.stats for percentile calculation
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# --- Data Loading ---
# Create an empty DataFrame to store all the data.
df = pd.DataFrame()

# Define the time period for which to fetch the data (last 1 year for current data, 3+ years for historical percentiles)
# Adjust years_back_history for percentile calculation history
years_back_current = 1 # For displaying recent data in future
years_back_history = 3 # For percentile calculations (as per spec: 1-3Y history)

end = datetime.datetime.now()
# Ensure start dates are at the beginning of the year for consistent historical lookbacks
start_current = datetime.date(end.year - years_back_current, 1, 1)
start_history = datetime.date(end.year - years_back_history, 1, 1)


# Loop through each year from the start year to the current year and fetch the COT data.
# The 'disaggregated_futopt' report type provides detailed trader categories.
print("Fetching COT data...")
# Fetch data for the history period
for i in range(start_history.year, end.year + 1):
    try:
        # cot_year() fetches all available reports for the given year.
        # It automatically handles fetching only up to the latest available report for the current year.
        single_year = pd.DataFrame(cot.cot_year(i, cot_report_type='disaggregated_futopt'))
        df = pd.concat([df, single_year], ignore_index=True)
    except Exception as e:
        print(f"Could not fetch data for year {i}. Error: {e}")
print("Data fetching complete.")

# Define common commodities (your original list, no changes needed here)
common_commodities = [
    "WHEAT-SRW - CHICAGO BOARD OF TRADE",
    "WHEAT-HRW - CHICAGO BOARD OF TRADE",
    "CORN - CHICAGO BOARD OF TRADE",
    "SOYBEANS - CHICAGO BOARD OF TRADE",
    "SOYBEAN OIL - CHICAGO BOARD OF TRADE",
    "SOYBEAN MEAL - CHICAGO BOARD OF TRADE",
    "OATS - CHICAGO BOARD OF TRADE",
    "ROUGH RICE - CHICAGO BOARD OF TRADE",
    "NAT GAS NYME - NEW YORK MERCANTILE EXCHANGE",
    "NY HARBOR ULSD - NEW YORK MERCANTILE EXCHANGE",
    "GASOLINE RBOB - NEW YORK MERCANTILE EXCHANGE",
    "CRUDE OIL, LIGHT SWEET-WTI - ICE FUTURES EUROPE",
    "WTI FINANCIAL CRUDE OIL - NEW YORK MERCANTILE EXCHANGE", # Added this to cover WTI explicitly on NYMEX
    "BRENT LAST DAY - NEW YORK MERCANTILE EXCHANGE", # Though primary is ICE, it appears on your list as NYMEX
    "GOLD - COMMODITY EXCHANGE INC.",
    "SILVER - COMMODITY EXCHANGE INC.",
    "PLATINUM - NEW YORK MERCANTILE EXCHANGE",
    "PALLADIUM - NEW YORK MERCANTILE EXCHANGE",
    "SUGAR NO. 11 - ICE FUTURES U.S.",
    "COFFEE C - ICE FUTURES U.S.",
    "COCOA - ICE FUTURES U.U.S.",
    "COTTON NO. 2 - ICE FUTURES U.S.",
    "FRZN CONCENTRATED ORANGE JUICE - ICE FUTURES U.S.",
    "LEAN HOGS - CHICAGO MERCANTILE EXCHANGE",
    "LIVE CATTLE - CHICAGO MERCANTILE EXCHANGE",
    "FEEDER CATTLE - CHICAGO MERCANTILE EXCHANGE",
    "MILK, Class III - CHICAGO MERCANTILE EXCHANGE",
    "LUMBER - CHICAGO MERCANTILE EXCHANGE",
    "CANOLA - ICE FUTURES U.S.",
    "ALUMINUM - COMMODITY EXCHANGE INC.",
    "COPPER- #1 - COMMODITY EXCHANGE INC."
]

df = df.loc[df.Market_and_Exchange_Names.isin(common_commodities), :].copy() # Use .copy() to avoid SettingWithCopyWarning

# Convert 'Report_Date_as_YYYY-MM-DD' to datetime objects
df['Report_Date'] = pd.to_datetime(df['Report_Date_as_YYYY-MM-DD'])

# Sort by Market and Date
df = df.sort_values(by=['Market_and_Exchange_Names', 'Report_Date']).reset_index(drop=True)

# --- Data Processing: Step 2 & 3 ---

def calculate_cot_metrics(df_commodity):
    """
    Calculates Net_Position_%_OI and Percentile_Rank for a given commodity's DataFrame.
    """
    # Ensure numeric types
    for col in ['M_Money_Positions_Long_All', 'M_Money_Positions_Short_All', 'Open_Interest_All']:
        df_commodity[col] = pd.to_numeric(df_commodity[col], errors='coerce')

    # Calculate Net_Position
    df_commodity['Net_Position'] = df_commodity['M_Money_Positions_Long_All'] - df_commodity['M_Money_Positions_Short_All']

    # Calculate Net_Position_%_OI
    df_commodity['Net_Position_%_OI'] = (df_commodity['Net_Position'] / df_commodity['Open_Interest_All']) * 100
    df_commodity.replace([np.inf, -np.inf], np.nan, inplace=True) # Handle division by zero if OI is 0

    # Calculate Percentile_Rank vs. 1-3Y history
    df_commodity['Percentile_Rank'] = np.nan # Initialize with NaN

    # Sort again to ensure proper rolling calculation
    df_commodity = df_commodity.sort_values(by='Report_Date').reset_index(drop=True)

    for i in range(len(df_commodity)):
        current_date = df_commodity.loc[i, 'Report_Date']
        
        # Define the historical window (e.g., 3 years prior to current_date)
        # Using 365.25 for a slightly more accurate year approximation
        history_start_date = current_date - pd.Timedelta(days=years_back_history * 365.25) 
        
        # Filter historical data up to (but not including) the current report date
        # And ensure it's within the history_start_date
        historical_values = df_commodity[
            (df_commodity['Report_Date'] >= history_start_date) & 
            (df_commodity['Report_Date'] < current_date)
        ]['Net_Position_%_OI'].dropna().values
        
        if len(historical_values) > 0:
            current_value = df_commodity.loc[i, 'Net_Position_%_OI']
            if not pd.isna(current_value):
                df_commodity.loc[i, 'Percentile_Rank'] = stats.percentileofscore(historical_values, current_value, kind='weak')
        # Else, Percentile_Rank remains NaN (already initialized)

    # Flag extremes
    df_commodity['Alert'] = 'Gray: Neutral'
    df_commodity.loc[df_commodity['Percentile_Rank'] >= 90, 'Alert'] = '🔴 Overbought'
    df_commodity.loc[df_commodity['Percentile_Rank'] <= 10, 'Alert'] = '🟢 Oversold'

    # Calculate Trend (▲/▼ vs. prior week)
    df_commodity['Prior_Week_Net_Position_%_OI'] = df_commodity.groupby('Market_and_Exchange_Names')['Net_Position_%_OI'].shift(1)
    df_commodity['Trend'] = ''
    df_commodity.loc[df_commodity['Net_Position_%_OI'] > df_commodity['Prior_Week_Net_Position_%_OI'], 'Trend'] = '▲'
    df_commodity.loc[df_commodity['Net_Position_%_OI'] < df_commodity['Prior_Week_Net_Position_%_OI'], 'Trend'] = '▼'
    
    return df_commodity

# Apply the function to each commodity group
processed_df = df.groupby('Market_and_Exchange_Names', group_keys=False).apply(calculate_cot_metrics)

# Filter for current data based on start_current (last 'years_back_current' year)
current_data_df = processed_df[processed_df['Report_Date'] >= pd.to_datetime(start_current)]

# Get the latest report date for each commodity for the alert panel
latest_alerts = current_data_df.groupby('Market_and_Exchange_Names').last().reset_index()


# --- Streamlit Dashboard Components ---
st.set_page_config(
    page_title="COT Managed Money Extreme Positioning Dashboard",  # More descriptive name
    page_icon="📊",
    layout="wide"
)

st.title("COT Extreme Positioning Alert Dashboard")
st.markdown("Real-time monitor for overbought/oversold markets using CFTC’s Managed Money positioning.")

# --- Styling Functions ---
# Function to apply background color to the entire row and text color to the 'Alert' column
def highlight_alert_row(row):
    styles = [''] * len(row) # Initialize with empty strings for all columns
    
    if '🔴 Overbought' in row['Alert']:
        row_bg_color = 'background-color: #ffe6e6;' # Light red
        text_color = 'color: #000000;' # Black text
    elif '🟢 Oversold' in row['Alert']:
        row_bg_color = 'background-color: #e6ffe6;' # Light green
        text_color = 'color: #000000;' # Black text
    else:
        # Default for 'Gray: Neutral' or no alert
        return styles # Return empty styles if no alert to avoid unwanted default colors

    # Apply row background color to all cells in the row
    styles = [row_bg_color + 'color: #000000;'] * len(row) # Force black text for all cells

    return styles

# Function to apply color to trend arrows
def color_trend(val):
    if '▲' in val:
        return 'color: #006400;' # Dark green
    elif '▼' in val:
        return 'color: #8B0000;' # Dark red
    return 'color: #000000;' # Default black


# A. Core Visualizations: Traffic Light Alert Panel
st.header(f"1. Traffic Light Alert Panel ({years_back_history}-Year Percentile)")

# Filter for only commodities with an actual alert (Red or Green)
alerted_commodities = latest_alerts[latest_alerts['Alert'] != 'Gray: Neutral'].copy()

# Rename columns for display in this specific dataframe
alerted_display_df = alerted_commodities[[
    'Market_and_Exchange_Names',
    'Net_Position_%_OI',
    'Percentile_Rank',
    'Alert',
    'Trend'
]].rename(columns={
    'Market_and_Exchange_Names': 'Commodity',
    'Net_Position_%_OI': 'Net Pos %OI',
    'Percentile_Rank': 'Percentile'
})

if not alerted_display_df.empty:
    st.dataframe(
        alerted_display_df.style.apply(highlight_alert_row, axis=1) # Apply full row highlight + text color
        .applymap(color_trend, subset=['Trend']) # Apply color to trend arrows only
        .format({
            'Net Pos %OI': "{:.1f}%",
            'Percentile': "{:.0f}%"
        }),
        hide_index=True,
        use_container_width=True
    )
else:
    st.info("No extreme alerts at the moment. All markets are currently neutral.")

st.markdown("---")

# Historical Percentile Chart and Top Alerts Table
st.header(f"2. Detailed Analysis ({years_back_history}-Year Percentile)")

selected_commodity = st.selectbox(
    "Select a Commodity for Detailed Chart:",
    options=latest_alerts['Market_and_Exchange_Names'].unique()
)

if selected_commodity:
    st.subheader(f"Historical Percentile Chart: {selected_commodity}")
    commodity_data = processed_df[processed_df['Market_and_Exchange_Names'] == selected_commodity].copy()
    
    # Filter for the relevant history for charting (e.g., last 3 years)
    chart_data = commodity_data[commodity_data['Report_Date'] >= pd.to_datetime(end - pd.Timedelta(days=years_back_history * 365.25))]

    if not chart_data.empty:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                            row_heights=[0.7, 0.3],
                            subplot_titles=[f'{selected_commodity} - Managed Money Net Position % Open Interest',
                                            f'{selected_commodity} - Managed Money Percentile Rank'])

        # Chart 1: Net_Position_%_OI with shaded bands
        fig.add_trace(
            go.Scatter(
                x=chart_data['Report_Date'],
                y=chart_data['Net_Position_%_OI'],
                mode='lines',
                name='Net Pos %OI',
                line=dict(color='blue')
            ),
            row=1, col=1
        )
        
        # Calculate 10th and 90th percentile values over the *entire historical range* for the commodity
        # This will be static lines on the chart for the full period.
        
        full_historical_net_pos_oi = processed_df[
            (processed_df['Market_and_Exchange_Names'] == selected_commodity) & 
            (processed_df['Report_Date'] >= pd.to_datetime(end - pd.Timedelta(days=years_back_history * 365.25)))
        ]['Net_Position_%_OI'].dropna()

        if not full_historical_net_pos_oi.empty:
            p10 = np.percentile(full_historical_net_pos_oi, 10)
            p90 = np.percentile(full_historical_net_pos_oi, 90)

            # Add shaded bands (using shapes)
            # Oversold band
            fig.add_shape(
                type="rect",
                xref="x domain", yref="y",
                x0=0, x1=1,
                y0=min(chart_data['Net_Position_%_OI'].min(), p10 - (abs(p10)*0.1 if p10 !=0 else 5)), # Extend range slightly intelligently
                y1=p10,
                fillcolor="rgba(0,255,0,0.2)", # Green for oversold
                line_width=0,
                layer="below", # Ensure it's behind the line
                row=1, col=1
            )
            fig.add_annotation(
                x=chart_data['Report_Date'].iloc[0], y=p10 + (abs(p10)*0.05 if p10 !=0 else 1), # Adjust y position as needed
                text="10th Percentile (Oversold)",
                showarrow=False,
                xanchor='left', # Anchor to left of x coordinate
                font=dict(color="darkgreen", size=10),
                row=1, col=1
            )
            
            # Overbought band
            fig.add_shape(
                type="rect",
                xref="x domain", yref="y",
                x0=0, x1=1,
                y0=p90,
                y1=max(chart_data['Net_Position_%_OI'].max(), p90 + (abs(p90)*0.1 if p90 !=0 else 5)), # Extend range slightly intelligently
                fillcolor="rgba(255,0,0,0.2)", # Red for overbought
                line_width=0,
                layer="below", # Ensure it's behind the line
                row=1, col=1
            )
            fig.add_annotation(
                x=chart_data['Report_Date'].iloc[0], y=p90 - (abs(p90)*0.05 if p90 !=0 else 1), # Adjust y position as needed
                text="90th Percentile (Overbought)",
                showarrow=False,
                xanchor='left', # Anchor to left of x coordinate
                font=dict(color="darkred", size=10),
                row=1, col=1
            )
        
        # Chart 2: Percentile Rank
        fig.add_trace(
            go.Scatter(
                x=chart_data['Report_Date'],
                y=chart_data['Percentile_Rank'],
                mode='lines',
                name='Percentile Rank',
                line=dict(color='purple')
            ),
            row=2, col=1
        )
        
        # Add 10th and 90th percentile lines on the percentile rank chart
        fig.add_hline(y=10, line_dash="dot", line_color="green", row=2, col=1, annotation_text="10th %ile", annotation_position="top left")
        fig.add_hline(y=90, line_dash="dot", line_color="red", row=2, col=1, annotation_text="90th %ile", annotation_position="bottom left")

        fig.update_layout(
            height=600,
            title_text=f"Managed Money Positioning for {selected_commodity}",
            xaxis_rangeslider_visible=False,
            hovermode="x unified"
        )
        
        fig.update_yaxes(title_text="Net Pos %OI", row=1, col=1)
        fig.update_yaxes(title_text="Percentile Rank", row=2, col=1, range=[0,100]) # Ensure percentile always 0-100
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(f"No sufficient historical data to plot for {selected_commodity} within the last {years_back_history} years.")

st.markdown("---")

st.subheader("Top Alerts Table (All Commodities)")

# Display the full latest_alerts table, sorted by 'Alert' to show red/green first
display_alerts_table = latest_alerts[[
    'Market_and_Exchange_Names',
    'Net_Position_%_OI',
    'Percentile_Rank',
    'Alert',
    'Trend'
]].rename(columns={
    'Market_and_Exchange_Names': 'Commodity',
    'Net_Position_%_OI': 'Net Pos %OI',
    'Percentile_Rank': 'Percentile'
}).sort_values(by=['Alert'], ascending=False).reset_index(drop=True) # Sort to show alerts first


st.dataframe(
    display_alerts_table.style.apply(highlight_alert_row, axis=1)
    .applymap(color_trend, subset=['Trend'])
    .format({
        'Net Pos %OI': "{:.1f}%",
        'Percentile': "{:.0f}%"
    }),
    hide_index=True,
    use_container_width=True
)

# LinkedIN
st.markdown("---")
st.markdown("### Connect with Me!")

st.markdown("""
<a href="https://www.linkedin.com/in/saqif-juhaimee-17322a119/">
    <img src="https://upload.wikimedia.org/wikipedia/commons/c/ca/LinkedIn_logo_initials.png" width="20">
    Saqif Juhaimee
</a>
""", unsafe_allow_html=True)
# st.subheader("Next Steps & Enhancements")
# st.markdown("""
# - **Price Overlay:** Integrate live futures prices from external APIs (e.g., Alpha Vantage, Polygon.io, or specialized data providers like Databento for futures) to correlate COT extremes with price action. This would likely involve fetching daily or weekly price data and aligning it with the COT report dates.
# - **Email Alerts:** Set up a scheduled job (e.g., using AWS Lambda and EventBridge, or a simple Python script with `smtplib` and a scheduler like `APScheduler`) to send weekly email summaries of new extreme alerts.
# - **Backtesting Signals:** Develop a module to backtest the historical performance of "Overbought" and "Oversold" signals. This would involve analyzing subsequent price movements after a signal is triggered.
# - **Database Integration:** For persistent storage of historical COT data and faster retrieval, consider using SQLite (for simpler local use) or PostgreSQL (for a more robust, scalable solution) as mentioned in the project spec. Streamlit has built-in `st.connection` for databases.
# - **Deployment:** For a shareable web app, deploying on platforms like Streamlit Community Cloud (simplest for Streamlit apps), AWS EC2, or a containerized service like AWS Fargate/ECS with a CI/CD pipeline (more complex but robust) would be the next step. AWS Lambda is suitable for the data processing backend for weekly updates, less so for the entire interactive Streamlit dashboard directly.
# """)

# To run this Streamlit app:
# 1. Save the code as a Python file (e.g., `cot_dashboard.py`).
# 2. Open your terminal or command prompt.
# 3. Navigate to the directory where you saved the file.
# 4. Run the command: `streamlit run cot_dashboard.py`