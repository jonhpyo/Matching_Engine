# services/binance_depth.py
import requests

class BinanceDepthService:
    def __init__(self):
        self.base = "https://api.binance.com/api/v3/depth"

    def get_depth(self, symbol: str, limit=15):
        symbol = symbol.upper()

        try:
            url = f"{self.base}?symbol={symbol}&limit={limit}"
            r = requests.get(url, timeout=0.8)
            r.raise_for_status()

            data = r.json()

            bids = [(float(p), float(q)) for p, q in data["bids"]]
            asks = [(float(p), float(q)) for p, q in data["asks"]]

            mid = 0
            if bids and asks:
                mid = (bids[0][0] + asks[0][0]) / 2

            return {
                "bids": bids,
                "asks": asks,
                "mid": mid
            }

        except Exception as e:
            print("[BinanceDepthService] error:", e)
            return {"bids": [], "asks": [], "mid": 0}
