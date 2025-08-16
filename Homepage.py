import streamlit as st

# Set page config
st.set_page_config(
    page_title="App Launcher",
    layout="wide",
    page_icon="🚀"
)

# Custom CSS for buttons (unchanged)
st.markdown("""
<style>
    .app-button {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 20px;
        border-radius: 10px;
        background-color: #f0f2f6;
        border: 1px solid #ddd;
        transition: all 0.3s;
        height: 200px;
        text-align: center;
    }
    .app-button:hover {
        background-color: #e6e9ef;
        transform: translateY(-5px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .app-icon {
        font-size: 48px;
        margin-bottom: 15px;
    }
    .app-title {
        font-size: 20px;
        font-weight: bold;
        margin-bottom: 5px;
    }
    .app-description {
        font-size: 14px;
        color: #666;
    }
</style>
""", unsafe_allow_html=True)

# App header
st.title("🚀 Application Launcher")
st.markdown("Select an application to launch:")

# Create columns for the app buttons
col1, col2 = st.columns(2)

with col1:
    st.markdown(
        """
        <a href="/COT_MM_Dashboard" target="_self" style="text-decoration: none;">
            <div class="app-button">
                <div class="app-icon">📊</div>
                <div class="app-title">COT Dashboard</div>
                <div class="app-description">Commodity Managed Money positioning alerts and analysis</div>
            </div>
        </a>
        """,
        unsafe_allow_html=True
    )

with col2:
    st.markdown(
        """
        <a href="/JPEG_Table_Extractor" target="_self" style="text-decoration: none;">
            <div class="app-button">
                <div class="app-icon">🖼️</div>
                <div class="app-title">Table Extractor</div>
                <div class="app-description">Extract tables from images using AI</div>
            </div>
        </a>
        """,
        unsafe_allow_html=True
    )

# Instructions (unchanged)
st.markdown("---")
st.markdown("### How to use:")
st.markdown("1. Click on the application you want to use")
st.markdown("2. Use the navigation menu on the left to return to this launcher")