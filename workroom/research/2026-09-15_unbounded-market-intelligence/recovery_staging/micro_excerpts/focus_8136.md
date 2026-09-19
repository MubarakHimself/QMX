# 8136: Price series discretization, random component and noise

## Sections

### Conclusion

- The nature of the price series is discrete, which stems from the pricing structure.
- A market price is not a function of time, but it is a function of closely related economic processes and currently it is not possible to take them all into account.
- Discretization of a price series into time intervals introduces a significant random component; this distorts the real shape of the price chart, adds noise and non-stationarity to this complex process with unknown parameters.
- It is necessary to take into account the function of which parameter the price is, when developing price series discretization methods.
- The non-stationarity of a price series is formed, among other reasons, due to incorrect discretization parameters.
- Time discretized price charts can be analyzed in an effort to find patterns, but it is necessary to take into account the above aspects, in order to better understand the nature of a particular found pattern.
- The idea is to develop other price series discretization methods which introduce much less distortion in the original data. One of such methods is described in this article.
- Trading algorithms and statistical market studies should be developed taking into account the specific features of the used price series discretization.

Translated from Russian by MetaQuotes Ltd.   
Original article: <https://www.mql5.com/ru/articles/8136>

**Attached files** |

## Key paras

The question can be answered if we know the market price forming mechanism. I will not describe it in detail, as the description is provided in the article "[Principles of Exchange Pricing through the Example of Moscow Exchange's Derivatives Market](https://www.mql5.com/en/articles/1284)". Some participants place orders in the Market Depth, and other participants buy the required amount at the required price. This is what happens when a price chart is formed. The levels are discrete, i.e. it is possible to place an order at a price of 1, 2, 3 and so one, with certain accuracy. The volume set in bids and purchased by buyers is also discrete, because you can buy 1, 2, 3 or more units. Figure 3

I consider the third option most probable, stating that price is a function of redefining benefits. But it is impossible to calculate the benefit of each participant in order to discretize the series. In the first two cases, it is possible to calculate trading and non-trading operations in exchange markets, but there can also be difficulties. For example, an asset can be traded in two or more different exchanges. Or if derivatives of an asset exist, such as futures and options, do we need to calculate the operations which are indirectly connected with the asset? These questions require a separate large study. In any case, all the four cases are indirectly related to each other. The fourth op

1. Take tick volume data of 1-minute candlesticks (from a real account) for the same period and calculate the average number of ticks in a one-minute candlestick - the average number is 59.99 ticks per minute. 2. Load the tick data and find out the average tick size, it is equal to 0.000014378. 3. Calculate the theoretical size of a 1-minute candlestick as (59.99^0.5)\*0.00014378=0.000111363 4. Calculate the theoretical size of a one-hour candlestick as ((59.99\*60)^0.5)\* 0.000014378= 0.00086

Attentive traders may notice that the candlesticks in the market are conventionally divided into groups of "large" and "small" sized candlesticks (areas with high and low volatility), which means that the chart is not a random walk and there are patterns. If time discretization introduced strong distortions, then this effect would not be observed. However, this feature can be explained by the fact that the candlestick size depends on the number of trading operations executed inside this candlestick. How this can be checked? You can simply look at the chart with tick volumes - "small candlestick" periods are accompanied by low tick volumes, and "large candlestick" periods come alongside high 

The simple conclusion of the above analysis suggests that tick data is more suitable for processing and analysis, as they avoid discretization errors in a price series. If we need a larger scale, we will use blocks of 10 or 100 ticks. But the problem is that ticks themselves are also a method of discretization. This method is widely used, but it still can introduce distortions 