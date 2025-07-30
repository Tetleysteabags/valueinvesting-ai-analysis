import os, json, time
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

CSV_PATH = "/Users/thomasgeorgiou/Documents/Coding/value-investing-ai/ValueInvesting-AI-Analysis/strict_analysis_results.csv"   

SYSTEM_MSG = (
    "You are an equity analyst. "
    "Given fundamentals & qualitative notes, rate the stock's expected "
    "risk‑adjusted performance over the next 24 months on a 1‑10 scale. "
    "Be rigorous: low PE, high ROE, good FCF yield, reasonable debt and "
    "positive qualitative signals deserve higher scores. Penalise extreme "
    "leverage, negative earnings or deteriorating sentiment."
)

def build_prompt(row: pd.Series) -> str:
    """Compose a compact prompt for one company."""
    numeric_fields = [
        "market_cap", "current_price", "pe_ratio", "price_to_book", "debt_to_equity",
        "roe", "fcf_yield", "beta"
    ]
    nums = {f: row[f] for f in numeric_fields if pd.notna(row[f])}
    blob = "\n".join(f"{k}: {v}" for k, v in nums.items())
    text_fields = ["sentiment_insight", "earnings_insight", "value_insight"]
    commentary = "\n".join(str(row[f]) for f in text_fields if row[f])
    return (
        f"Ticker: {row.symbol}  Company: {row.company}\n"
        f"{blob}\n"
        f"{commentary}\n\n"
        "Respond JSON only in the format: "
        '{"score": <1‑10 integer>, "reason": "<one concise sentence>"}'
    )

def ask_gpt(prompt: str, model="gpt-4o-mini") -> dict:
    """Call ChatGPT once, retrying on rate limits."""
    for _ in range(3):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": SYSTEM_MSG},
                          {"role": "user", "content": prompt}],
                temperature=0.3,
            )
            return json.loads(resp.choices[0].message.content)
        except Exception as e:
            print("Retrying after error:", e)
            time.sleep(2)
    return {"score": 0, "reason": "API error"}

def main():
    df = pd.read_csv(CSV_PATH)
    results = []

    for _, row in df.iterrows():
        prompt = build_prompt(row)
        res = ask_gpt(prompt)
        results.append({
            "ticker": row.symbol,
            "score": res.get("score", 0),
            "reason": res.get("reason", "–")
        })

    ranked = pd.DataFrame(results).sort_values("score", ascending=False)
    ranked.to_csv("gpt_ranking.csv", index=False)
    print(ranked)

if __name__ == "__main__":
    main()
