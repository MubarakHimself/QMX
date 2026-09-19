# 3336: Implementing a Scalping Market Depth Using the CGraphic Library

## Sections

### Conclusion

We have discussed the process of scalping Market Depth development.

- We have improved the appearance of the order book
- We have added to the panel a tick chart based on CGraphic and upgraded the graphical engine
- We have improved the Market Depth class and have implemented an algorithm for synchronizing ticks with the current order book.

However, even the current version of Market Depth is very far from a full-fledged scalping version. Of course, many users could be disappointed, having read the article up to this place and not seeing a full analog of a standard Market Depth or specialized programs like Bondar drive or QScalp. But any complex software product must go through a number of evolutionary steps in its development. Here's what can be added to the Market Depth in further versions:

- The ability to send limit orders straight from the Market Depth
- The ability to track large orders on the tick chart
- Differentiation of Last deals by volume and displaying them in different ways on the chart
- Displaying additional indicators with the tick chart. For example, below the tick chart we can display a histogram of the ratio of all Buy Limit orders to all Sell Limit orders.
- And, finally, the most important part is to download and save the Market Depth history, and to be able to create trading strategies with the offline testing mode.

All these ideas can be implemented. Probably such options will appear some day. If readers find this subject interesting, the series of articles will be continued.

Translated from Russian by MetaQuotes Ltd.   
Original article: <https://www.mql5.com/ru/articles/3336>

**Attached files** |

## Key paras

The order book is a dynamic structure, whose values may change dozens of times per second on volatile markets. To access the current state of the order book, you must handle a special BookEvent in the corresponding event handler, the OnBookEvent function. When the order book changes, the terminal calls OnBookEvent, indicating the symbol corresponding to changes. In the previous article, we developed the CMarketBook class that provided a convenient access to the current order book state. The current state of the order book could be obtained in this class by calling the Refresh() method in the OnBookEvent function. That's how it looked like:

In order to understand how ticks are formed, let's check the article [Principles of Exchange Pricing through the Example of Moscow Exchange's Derivatives Market](https://www.mql5.com/en/articles/1284) and consider a Market Depth for gold:

---

