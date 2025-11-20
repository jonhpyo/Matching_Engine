# services/marketdata_service.py
import requests


class MarketDataService:
    """
    FastAPI 서버에서 Binance Depth만 가져오는 경량 버전.
    HTS 클라이언트용 대규모 MarketDataService와는 별도.

    사용 예:
        md = MarketDataService(symbol="SOLUSDT", limit=20)
        depth = md.fetch_depth()
    """

    def __init__(self, symbol="SOLUSDT", limit=20):
        self._symbol = symbol.upper()
        self.limit = limit

    # ----------------------------------------------------
    # 심볼 변경
    # ----------------------------------------------------
    def set_symbol(self, symbol: str):
        self._symbol = symbol.upper()

    # ----------------------------------------------------
    # Binance Depth 가져오기
    # ----------------------------------------------------
    def fetch_depth(self):
        """
        반환값 예:
            {
                "bids": [ [price, qty], ... ],
                "asks": [ [price, qty], ... ],
                "mid": float
            }
        """
        url = f"https://api.binance.com/api/v3/depth"
        params = {"symbol": self._symbol, "limit": self.limit}

        try:
            r = requests.get(url, params=params, timeout=2)
            r.raise_for_status()
            data = r.json()

            bids_raw = data.get("bids", [])
            asks_raw = data.get("asks", [])

            bids = [(float(p), float(q), i) for i, (p, q) in enumerate(bids_raw)]
            asks = [(float(p), float(q), i) for i, (p, q) in enumerate(asks_raw)]

            mid = self._calc_mid(bids, asks)

            return {
                "symbol": self._symbol,
                "bids": bids,
                "asks": asks,
                "mid": mid
            }

        except Exception as e:
            print("[MarketDataService] Binance depth fetch error:", e)
            return None

    # ----------------------------------------------------
    # MID PRICE 계산
    # ----------------------------------------------------
    def _calc_mid(self, bids, asks):
        if not bids or not asks:
            return 0.0
        return (bids[0][0] + asks[0][0]) / 2
