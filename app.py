import streamlit as st
import yfinance as yf
import os
import requests
from dotenv import load_dotenv

# Load .env vars
load_dotenv()
api_key = os.getenv("TOGETHER_API_KEY")

# Streamlit UI
st.title("📈 AI Stock Advisor (Free with Mixtral)")

# Ticker input
ticker = st.text_input("Enter Stock Ticker Symbol (e.g. AAPL, TSLA, GOOGL):")

if st.button("🔍 Analyze Stock"):
    if not ticker:
        st.warning("Please enter a valid stock ticker.")
    else:
        try:
            st.write(f"📥 Fetching data for {ticker.upper()}...")

            stock = yf.Ticker(ticker)
            info = stock.info

            prompt = f"""
            Analyze this stock and say if it's a good buy:
            Ticker: {ticker}
            P/E Ratio: {info.get('trailingPE')}
            Market Cap: {info.get('marketCap')}
            Recent News: {ticker} recently made headlines.

            Return your recommendation and explain why.
            """

            url = "https://api.together.xyz/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
                "messages": [
                    {"role": "system", "content": "You are a helpful financial analyst."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 500,
                "temperature": 0.7
            }

            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            suggestion = response.json()["choices"][0]["message"]["content"]

            st.subheader(f"💡 Suggestion for {ticker.upper()}")
            st.write(suggestion)

        except Exception as e:
            st.error(f"❌ Error: {e}")
