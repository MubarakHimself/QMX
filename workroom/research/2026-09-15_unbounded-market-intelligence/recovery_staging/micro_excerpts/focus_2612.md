# 2612: Testing trading strategies on real ticks

## Sections

### Comparing results of different test modes

Test results in different modes are displayed in the table. The first thing that catches the eye is the difference in the number of trading operations. Thus, all other test results are also different. Testing in "1 minute OHLC" took 1.57 seconds which is 23 times faster than in "Every tick" mode. Such a difference is important when optimizing the trading system inputs.

In its turn, the mode "Every tick based on real ticks" has turned out to be even more time-consuming – 74 seconds as compared to 36.7 seconds in "Every tick" mode. This can be easily explained by the fact that more than 34 million ticks have been modeled when using real ticks which is almost two times more than in "Every tick" mode. Thus, the more ticks are used in tests, the more time is required for one pass in the strategy tester.

| Parameter | 1 minute OHLC | Every tick | Every tick   based on real ticks |
| --- | --- | --- | --- |
| Ticks | 731 466 | 18 983 485 | 34 099 141 |
| Net profit | 169.46 | -466.81 | -97.24 |
| Trades | 96 | 158 | 156 |
| Deals | 192 | 316 | 312 |
| Equity drawdown % | 311.35 (3.38%) | 940.18 (9.29%) | 625.79 (6.07%) |
| Balance drawdown | 281.25 (3.04%) | 882.58 (8.76) | 591.99 (5.76%) |
| Profitable trades (%) | 50 (52.08%) | 82 (51.90%) | 73 (46.79%) |
| Average consecutive wins | 2 | 2 | 2 |
| Testing time including tick generation time | **1.6** seconds | **36.7** seconds | **74** seconds (1 minute 14 seconds) |

Test reports of various modeling modes are displayed below as animated GIF images allowing you to compare the parameters.



The balance and equity graphs are different as well. As we can see, this simple strategy is not impressive – growth periods are followed by drawdowns and the test graphs look more like a ch

## Key paras

Comparing the results allows us to assess the quality in various modes, as well as helps us to use the tester more efficiently in order to receive results faster. "1 minute OHLC" mode allows receiving quick estimated test results, "Every tick" mode is closer to reality, while testing on real ticks is most accurate but time-consuming. Keep in mind that errors in a trading robot's logic may affect the number of trading operations making the strategy test results more susceptible to a selected test mode.

In its turn, the mode "Every tick based on real ticks" has turned out to be even more time-consuming – 74 seconds as compared to 36.7 seconds in "Every tick" mode. This can be easily explained by the fact that more than 34 million ticks have been modeled when using real ticks which is almost two times more than in "Every tick" mode. Thus, the more ticks are used in tests, the more time is required for one pass in the strategy tester.

MetaTrader 5 strategy tester allows checking trading strategies in four tick modeling modes described in the article ["The Fundamentals of Testing in MetaTrader 5".](https://www.mql5.com/en/articles/239) The fastest and most rough mode is "**Open prices only**", at which trading operations can be performed only at the opening of a new bar. No trading actions inside bars are available. The mode is most suitable for testing strategies that are not dependent on the price movements inside bars.

These two modes are suitable for testing a large set of trading strategies, since most traders develop robots for trading at a new bar opening. However, if you need to conduct a more accurate and detailed modeling of the incoming ticks, you will need "**Every tick"** mode. In this mode, the price behavior within each minute bar is additionally modeled. The ticks are generated according to complex (but predefined) laws. The price modeling mechanism for this mode is described in details in the article ["The Algorithm of Ticks' Generation within the Strategy Tester of the MetaTrader 5 Terminal".](https://www.mql5.com/en/articles/75)

If you need the most accurate representation of history data in the strategy tester, use "**Every tick based on real ticks**" mode. In this mode, the tester downloads real ticks from a broker's trade server and uses them to display the price development. In case real ticks are absent for some time intervals, the tester simulates the price just like in the "**Every tick**" mode. Thus, if the broker has all history of the required symbols, you can perform testing of real historical data without artificial modeling. The drawback of the