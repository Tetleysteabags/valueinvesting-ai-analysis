import time
import openai
from openai import (
    OpenAIError,
    RateLimitError,
    APIConnectionError,
    InternalServerError,
    BadRequestError
)
from utils.cache import load_cache, save_cache, get_cache_key
from config import OPENAI_API_KEY, CACHE_FILE

openai.api_key = OPENAI_API_KEY

def ask_openai(messages, temperature=0.2, max_tokens=250, max_retries=3):
    cache = load_cache()
    cache_key = get_cache_key(messages)

    if cache_key in cache:
        print("Cache hit 🔥")
        return cache[cache_key]

    print("Cache miss ❄️. Calling OpenAI API...")
    for attempt in range(max_retries):
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            content = response.choices[0].message.content.strip()
            cache[cache_key] = content
            save_cache(cache, CACHE_FILE)
            return content
        except (OpenAIError, RateLimitError, APIConnectionError, InternalServerError, BadRequestError) as e:
            wait = 2 ** (attempt + 1)
            print(f"OpenAI API error: {e}. Retrying in {wait} seconds...")
            time.sleep(wait)
        except Exception as e:
            print(f"Unexpected error: {e}")
            break

    return None

# === OpenAI Analyses ===
def sentiment_analysis(ticker):
    prompt = f"Provide a sentiment analysis for stock {ticker} based on recent news and social media posts. Is the sentiment positive, negative, or neutral? Focus on key drivers (e.g., earnings reports, news events, market sentiment) Be concise and to the point, maximum 2 sentences."
    result = ask_openai([
        {"role": "system", "content": "You are a market sentiment analyst who is looking for stocks that are undervalued and have a good chance of growth. Focus on key factors like news, earnings, and market sentiment."},
        {"role": "user", "content": prompt}
    ])
    if result is None:
        return "No sentiment analysis available"
    return result


# Analyse earnings calls for the stock using OpenAI
def earnings_call(ticker):
    prompt = f"Summarize the latest earnings call for stock {ticker}. Highlight key points such as management outlook, risks, opportunities, and financial performance. Be concise and to the point, maximum 2 sentences."
    result = ask_openai([
        {"role": "system", "content": "You are a financial analyst who is looking for stocks that are undervalued and have a good chance of growth. Provide key insights from the earnings call."},
        {"role": "user", "content": prompt}
    ])
    if result is None:
        return "No earnings call analysis available"
    return result


# Stock analysis using OpenAI
def stock_insights(ticker):
    prompt = f"Analyze stock {ticker}. Include its business model, growth prospects, financial performance, and risks. Provide key investment takeaways. Be concise and to the point, maximum 2 sentences."
    result = ask_openai([
        {"role": "system", "content": "You are a financial analyst who is looking for stocks that are undervalued and have a good chance of growth. Provide a summary of key investment insights."},
        {"role": "user", "content": prompt}
    ])
    if result is None:
        return "No stock insights available"
    return result


# Value investing analysis using OpenAI
def value_investing(ticker):
    prompt = f"Evaluate stock {ticker} from a value investor's perspective. Compare key metrics (PE ratio, PB ratio, ROE) to the industry average and provide investment recommendations. Be concise and to the point, maximum 2 sentences."
    result = ask_openai([
        {"role": "system", "content": "You are a value investor who is looking for stocks that are undervalued and have a good chance of growth. Compare key financial metrics with the industry and provide an investment recommendation."},
        {"role": "user", "content": prompt}
    ])
    if result is None:
        return "No value investing analysis available"
    return result