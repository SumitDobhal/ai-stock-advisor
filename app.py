import streamlit as st
import yfinance as yf
import os
import requests
from dotenv import load_dotenv
from textblob import TextBlob
import pandas as pd
import ta
import difflib

# Secret loading function
def get_secret(key):
    if "STREAMLIT_ENV" in os.environ:  # Check if we're on Streamlit Cloud
        return st.secrets[key]
    else:
        load_dotenv()  # Load .env variables for local development
        return os.getenv(key)

# Load API keys
api_key = get_secret("TOGETHER_API_KEY")
news_api_key = get_secret("NEWSDATA_API_KEY")
fmp_api_key = get_secret("FMP_API_KEY")

st.title("💼 AI Stock Advisor (News + Technicals)")

ticker = st.text_input("Enter Stock Ticker (e.g. AAPL, TSLA):")

# Fetch the list of all tickers from the FMP API
@st.cache_data(ttl=86400)  # Cache for 24 hours
def get_all_tickers_from_fmp():
    url = f"https://financialmodelingprep.com/api/v3/stock/list?apikey={fmp_api_key}"
    response = requests.get(url)
    data = response.json()
    tickers = [item["symbol"] for item in data if "symbol" in item]
    return tickers

# Suggest closest ticker using fuzzy matching
def suggest_closest_ticker(user_ticker, all_tickers):
    matches = difflib.get_close_matches(user_ticker, all_tickers, n=1)
    return matches[0] if matches else None

# Function to fetch stock-related news
def fetch_news(ticker):
    company_name = yf.Ticker(ticker).info.get("shortName", ticker)
    url = f"https://newsdata.io/api/1/news?apikey={news_api_key}&q={company_name}&language=en"
    res = requests.get(url)
    articles = res.json().get("results", [])[:5]
    headlines = [article["title"] for article in articles]
    return headlines

# Analyze sentiment of news headlines
def analyze_sentiment(news):
    if not news:
        return 0
    scores = [TextBlob(headline).sentiment.polarity for headline in news]
    return sum(scores) / len(scores)

# Run when the user clicks the "Analyze Stock" button
if st.button("🔍 Analyze Stock"):
    if not ticker:
        st.warning("Please enter a stock ticker.")
    else:
        try:
            # Fetch the list of all valid tickers from FMP API
            all_tickers = get_all_tickers_from_fmp()

            # Check if the entered ticker is valid, suggest closest ticker if invalid
            if ticker.upper() not in all_tickers:
                suggestion = suggest_closest_ticker(ticker.upper(), all_tickers)
                if suggestion:
                    st.warning(f"❗ Couldn't find `{ticker.upper()}`. Did you mean `{suggestion}`?")
                else:
                    st.error(f"❌ Ticker `{ticker.upper()}` not found. Please try again.")
                st.stop()  # Stop further execution if ticker is invalid

            # Proceed with the analysis if ticker is valid
            stock = yf.Ticker(ticker)
            info = stock.info
            hist = stock.history(period="6mo")

            # Technical Indicators
            df = ta.add_all_ta_features(hist, open="Open", high="High", low="Low", close="Close", volume="Volume")
            sma_50 = df["trend_sma_fast"].dropna().iloc[-1] if not df["trend_sma_fast"].dropna().empty else "N/A"
            rsi = df["momentum_rsi"].dropna().iloc[-1] if not df["momentum_rsi"].dropna().empty else "N/A"

            # Volatility
            returns = hist["Close"].pct_change().dropna()
            volatility = returns.std()

            # News + Sentiment
            news = fetch_news(ticker)
            sentiment_score = analyze_sentiment(news)
            sentiment_label = "positive" if sentiment_score > 0.1 else "negative" if sentiment_score < -0.1 else "neutral"
            news_summary = "\n".join(f"- {headline}" for headline in news)

            # Build prompt for AI model
            prompt = f"""
You are a smart financial analyst.

Analyze the stock {ticker.upper()} using:
- Fundamentals: P/E Ratio: {info.get("trailingPE", 'N/A')}, Market Cap: {info.get("marketCap", 'N/A')}
- Technical Indicators: 50-day SMA: {sma_50}, RSI: {rsi}
- Volatility (6-month): {round(volatility, 4)}
- News Headlines:
{news_summary}
- News Sentiment: {sentiment_label} (score: {round(sentiment_score, 2)})

Give a final recommendation: Buy, Hold, or Sell — and explain your reasoning clearly.
            """
            st.write(prompt)

            # Call AI API for recommendation
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
                "max_tokens": 600,
                "temperature": 0.7
            }

            response = requests.post(url, headers=headers, json=data)
            suggestion = response.json()["choices"][0]["message"]["content"]

            # Display AI recommendation
            st.subheader(f"💡 Recommendation for {ticker.upper()}")
            st.write(suggestion)

        except Exception as e:
            st.error(f"❌ Error: {e}")
