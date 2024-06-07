from lumibot.brokers import Alpaca
from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies.strategy import Strategy
from lumibot.traders import Trader
from datetime import datetime
from alpaca_trade_api import REST
from timedelta import Timedelta
from finbert_utils import estimate_sentiment

API_KEY= "PKWUEAI7FGYYNAK8YVYI"
API_SECRET="YAthUC6aXdEtKkchAde9GUGtfY0YSbS1gZgHTA1o"
BASE_URL="https://paper-api.alpaca.markets/v2"

ALPACA_CREDS={
    "API_KEY" : API_KEY,
    "API_SECRET" : API_SECRET,
    "PAPER" : True
}

class MLTrader(Strategy):
    def initialize(self, symbols:list=["SPY","AAPL","MSFT"], cash_at_risk:float=.5):
        self.symbols=symbols
        self.sleeptime="24H"
        self.last_trade={symbol: None for symbol in symbols}
        self.cash_at_risk=cash_at_risk
        self.api=REST(base_url=BASE_URL, key_id=API_KEY, secret_key=API_SECRET)

    def position_sizing(self, symbol):
        cash=self.get_cash()
        last_price=self.get_last_price(symbol)
        quantity=round(cash*self.cash_at_risk/last_price, 0)
        return cash, last_price, quantity

    def get_dates(self):
        today=self.get_datetime()
        three_days_prior=today-Timedelta(days=3)
        return today.strftime('%Y-%m-%d'), three_days_prior.strftime('%Y-%m-%d')

    def get_sentiment(self, symbol):
        today, three_days_prior = self.get_dates()
        news = self.api.get_news(symbol=symbol,
                                 start=three_days_prior,
                                 end=today)
        news = [ev.__dict__["_raw"]["headline"] for ev in news]
        probability, sentiment = estimate_sentiment(news)
        return probability, sentiment

    def on_trading_iteration(self):
        for symbol in self.symbols:
            cash, last_price, quantity = self.position_sizing(symbol)
            probability, sentiment = self.get_sentiment(symbol)

            if cash > last_price:
                if sentiment == "positive" and probability > .999:
                    if self.last_trade[symbol] == "sell":
                        self.sell_all()
                    order = self.create_order(
                        symbol,
                        quantity,
                        "buy",
                        type="bracket",
                        take_profit_price=last_price * 1.20,
                        stop_loss_price=last_price * .95
                    )
                    self.submit_order(order)
                    self.last_trade[symbol] = "buy"
                elif sentiment == "negative" and probability > .999:
                    if self.last_trade[symbol] == "buy":
                        self.sell_all()
                    order = self.create_order(
                        symbol,
                        quantity,
                        "sell",
                        type="bracket",
                        take_profit_price=last_price * .8,
                        stop_loss_price=last_price * 1.05
                    )
                    self.submit_order(order)
                    self.last_trade[symbol] = "sell"

start_date = datetime(2023, 12, 1)
end_date = datetime(2024, 5, 31)

broker = Alpaca(ALPACA_CREDS)
strategy = MLTrader(name='mlstrat', broker=broker,
                    parameters={"symbols": ["SPY", "AAPL", "MSFT"], "cash_at_risk": .5})

strategy.backtest(
    YahooDataBacktesting,
    start_date,
    end_date,
    parameters={"symbols": ["SPY", "AAPL", "MSFT"], "cash_at_risk": .5}
)
