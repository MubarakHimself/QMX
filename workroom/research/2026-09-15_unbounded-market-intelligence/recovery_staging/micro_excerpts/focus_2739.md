# 2739: An Example of Developing a Spread Strategy for Moscow Exchange Futures

## Key paras

The MetaTrader 5 platform allows developing and testing trading robots that simultaneously trade multiple financial instruments. The built-in Strategy Tester automatically downloads required tick history from the broker's server taking into account contract specifications, so the developer does not need to do that manually. This makes it possible to easily and reliably reproduce trading environment conditions, including even millisecond intervals between the arrival of ticks on different symbols. In this article we will demonstrate the development and testing of a spread strategy on two [Moscow Exchange futures](http://www.moex.com/en/derivatives/select.aspx "http://moex.com/en/derivatives/s

Si-M.Y and RTS-M.Y futures are traded on Moscow Exchange. These futures types are tightly correlated. Here M.Y means contract expiration date:

Si is a futures contract on US dollar/Russian ruble exchange rate, RTS is a futures contract on the RTS index expressed in US dollars. The RTS index includes stocks of Russian companies, the prices of which are expressed in rubles, USD/RUR fluctuations also affect index fluctuations expressed in US dollars. Price charts show that when one asset grows, the second asset usually falls.

We have received linear regression coefficients and can draw a synthetic chart of type Y(RTS) = A\*RTS+B. Let us call the difference between the source asset and the synthetic sequence "a spread". This difference will vary at each bar from negative to positive values.

In order to visualize the spread, let us create the *TwoSymbolsSpread\_Ind.mql5* indicator that displays the histogram of spread on the last 500 bars. Positive values are drawn in blue, negative values are yellow.

### Creating a linear regression channel on the spread channel over the last 100 bars

The spread indicator shows that the difference between the Si futures and the synthetic symbol changes from time to time. In order to evaluate the current spread, let us create the *SpreadRegression\_Ind.mq5* indicator (spread with a linear regression on it) that draws a trend line on a spread chart. The line parameters are calculated using linear regression. Let us launch the two indicators on a chart for debugging.

The slope of the red trend line changes depending on the spread value on the last 100 bars. Now we have a minimum of required data and we can try to build a trading system.

Spread values in the *TwoSymbolsSpread\_Ind.mql5* indicator are calculated as the difference between Si and Y(RTS)=A\*RTS + B. You can easily check it by running the indicator in the [debugging](https://www.metatrader5.com/en/metaeditor/help/development/debug "https://www.metatrader5.com/en/metaeditor/help/development/debug") mode (F5 key).

Let us create a simple Expert Advisor that would monitor change of slope of the linear regression attached to a spread chart. Line slope is the A coefficient in the equation: Y=A\*X+B. If trend is positive on the spread chart, A>0. If trend is negative, A<0. The linear regression is calculated using the last 100 values of the spread chart. Here is a part of the Expert Advisor code *Strategy1\_AngleChange\_EA.mq5.*

#include <Trade\Trade.mqh>    //+------------------------------------------------------------------+    //| Spread strategy type                                             |    //+------------------------------------------------------------------+    enum SPREAD\_STRATEGY      {       BUY\_AND\_SELL\_ON\_UP,  // Buy 1-st, Sell 2-nd       SELL\_AND\_BUY\_ON\_UP,  // Sell 1-st, Buy 2-nd      };    //---    input int       LR\_length=100;                     // Number of bars for a regression on spread    input int       Spread\_length=500;                 // number of bars for spread calculation    input ENUM\_TIMEFRAMES  period=PERIOD\_M5;           // Time-frame    input string    symbol1="

input SPREAD\_STRATEGY strategy=SELL\_AND\_BUY\_ON\_UP; // Type of a spread strategy

---

