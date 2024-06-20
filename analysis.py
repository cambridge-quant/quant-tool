"""
Analysis of candelstick patterns
"""

# Import libraries
import pandas as pd

from typing import Optional
from data import read_local_file, check_bad_values, correct_dates
from data import correct_changes, asym_rolling_minmax, expanding_quantiles
from plotting import summary_plot, candlestick_plot, scatter_matrix_plot

# List potential candlestick patterns
patterns = ["hammer", "inv_hammer",
            "bull_engulf", "piercing",
            "morning", "soldiers",
            "hanging", "shooting",
            "bear_engulf", "evening",
            "crows", "cloud",
            "doji", "spinning",
            "falling", "rising"]

class Strategy:
    """
    OOP strategy class
    """

    def __init__(self,
                 country: str,
                 pattern: str,
                 start_date: Optional[str] = "2000-01-01",
                 end_date: Optional[str] = "2025-01-01") -> None:

        self.country = country
        self.pattern = pattern
        self.start_date = start_date
        self.end_date = end_date

        filename = country + "-bond-yield.csv"
        df = read_local_file(filename)
        if df is None:
            raise Exception("Program closing.")
        else:
            check_bad_values(df)
            correct_dates(df)
            correct_changes(df)
            df.sort_values(["Date"], ignore_index=True, inplace=True)
        
        mask = (df["Date"] >= start_date) & (df["Date"] <= end_date)
        self.data = df.loc[mask]
        print("Selected", self.data.shape[0], "entries")
    
    def print_data(self, number: int) -> None:
        """
        Print the dataframe
        """
        
        print("Printing dataframe of first {} values by date".format(number))
        print(self.data.head(number))

    def initial_plot(self) -> None:
        """
        Print some initial graphs
        """
        
        # Print summary plot
        print("Printing summary plot")
        summary_plot(self.country, self.data)
        # Print candlestick plot
        print("Printing candelstick plot")
        candlestick_plot(self.country, self.data)
        # Print scatter matrix plot
        print("Printing scatter matrix plot")
        scatter_matrix_plot(self.data)
    
    def analyse_pattern(self) -> None:
        """
        Calculate important derivative data
        """

        # Calculate body length
        self.data["Body"] = abs(self.data["Open"] - self.data["Price"])
        # Calculate lower wick length
        self.data["L-Wick"] = self.data[["Open", "Price"]].min(axis=1) - self.data["Low"]
        # Calculate the upper wick length
        self.data["U-Wick"] = self.data["High"] - self.data[["Open", "Price"]].max(axis=1)
        # Calculate quantile data of body length
        self.data = expanding_quantiles(self.data, "Body", [0.25, 0.50])
        # Calculate local minimum over (asymmetrical) window size
        #window_size = 7
        #self.data["Min"] = (self.data["Price"] == self.data["Price"].rolling(window=window_size, center=True).min())
        # We can only detect a local minimum look_forward days after it has happened
        look_back, look_forward = 3, 1
        self.data["Min"] = (self.data["Price"] == asym_rolling_minmax(self.data, look_back, look_forward, True))
        self.data["Max"] = (self.data["Price"] == asym_rolling_minmax(self.data, look_back, look_forward, False))

        if self.pattern == "hammer":
            print("Searching for bullish hammer pattern")
            self.hammer()
        elif self.pattern == "inv_hammer":
            print("Searching for bullish inverse hammer pattern")
            self.inv_hammer()
        elif self.pattern == "bull_engulf":
            print("Searching for bullish engulfing pattern")
            self.bull_engulf()
        elif self.pattern == "piercing":
            print("Searching for bullish piercing line pattern")
            self.piercing()
        elif self.pattern == "morning":
            print("Searching for bullish morning star pattern")
            self.morning()
        elif self.pattern == "soldiers":
            print("Searching for bullish three white soldier pattern")
            self.soldiers()
        elif self.pattern == "hanging":
            print("Searching for bearish hanging man pattern")
            self.hanging()
        elif self.pattern == "shooting":
            print("Searching for bearish shooting star pattern")
            self.shooting()
        else:
            print("Error: Pattern not recognised")

    def hammer(self) -> pd.DataFrame:
        """
        The hammer candlestick pattern is formed of a short body with a long lower wick,
        and is found at the bottom of a downward trend.
        
        A hammer shows that although there were selling pressures during the day,
        ultimately a strong buying pressure drove the price back up.
        The colour of the body can vary,
        but green hammers indicate a stronger bull market than red hammers.
        """

        # Lower wick >= 150% of body
        mask_long_wick = (1.5*self.data["Body"] <= self.data["L-Wick"])
        # Body within the 25th percentile
        mask_short_body = (self.data["Body"] <= self.data["25 Body"])
        # Local minimum
        mask_minimum = (self.data["Min"] == True)
        
        mask = mask_long_wick & mask_short_body & mask_minimum
        filtered_data = self.data.loc[mask]

        if filtered_data.empty:
            print("No hammer pattern detected from", self.start_date, "to", self.end_date)
        else:
            print("Hammer patterns detected at:")
            print(filtered_data)
        
        return filtered_data

    def inv_hammer(self) -> pd.DataFrame:
        """
        A similarly bullish pattern is the inverted hammer.
        The only difference being that the upper wick is long,
        while the lower wick is short.
        
        It indicates a buying pressure,
        followed by a selling pressure that was not strong enough to drive the market price down.
        The inverse hammer suggests that buyers will soon have control of the market.
        """

        # Lower wick <= 25% of body
        mask_short_wick = (0.25*self.data["Body"] >= self.data["L-Wick"])
        # Upper wick >= 150% of body
        mask_long_wick = (1.5*self.data["Body"] <= self.data["U-Wick"])
        # Local minimum
        mask_minimum = (self.data["Min"] == True)

        mask = mask_short_wick & mask_long_wick & mask_minimum
        filtered_data = self.data.loc[mask]

        if filtered_data.empty:
            print("No inverse hammer pattern detected from", self.start_date, "to", self.end_date)
        else:
            print("Inverse hammer patterns detected at:")
            print(filtered_data)

        return filtered_data
    
    def bull_engulf(self) -> pd.DataFrame:
        """
        The bullish engulfing pattern is formed of two candlesticks.
        The first candle is a short red body that is completely engulfed by a larger green candle.
        
        Though the second day opens lower than the first,
        the bullish market pushes the price up,
        culminating in an obvious win for buyers.
        """

        # Second candle has a green body
        mask_second_red = (self.data["Price"] > self.data["Open"])
        # First candle has a red body
        mask_first_green = (self.data["Open"].shift(1) > self.data["Price"].shift(1))
        # First candle has a short body (body within the 50th percentile)
        mask_first_short = (self.data["Body"].shift(1) <= self.data["50 Body"])
        # First candle is engulfed by the second candle
        mask_engulf = (self.data["Open"] < self.data["Price"].shift(1)) & (self.data["Price"] > self.data["Open"].shift(1))

        mask = mask_second_red & mask_first_green & mask_first_short & mask_engulf
        filtered_data = self.data.loc[mask]

        if filtered_data.empty:
            print("No bullish engulfing pattern detected from", self.start_date, "to", self.end_date)
        else:
            print("Bullish engulfing pattern detected at:")
            print(filtered_data)

        return filtered_data
    
    def piercing(self) -> pd.DataFrame:
        """
        The piercing line is also a two-stick pattern,
        made up of a long red candle, followed by a long green candle.
        
        There is usually a significant gap down between the first candlestick's closing price,
        and the green candlestick's opening.
        It indicates a strong buying pressure,
        as the price is pushed up to or above the mid-price of the previous day.
        """

        # Second candle has a green body
        mask_second_red = (self.data["Price"] > self.data["Open"])
        # First candle has a red body
        mask_first_green = (self.data["Open"].shift(1) > self.data["Price"].shift(1))
        # Both candles have long bodies (body greater than the 50th percentile)
        mask_first_long = (self.data["Body"].shift(1) >= self.data["50 Body"])
        mask_second_long = (self.data["Body"] >= self.data["50 Body"])
        # Significant gap down between first candle price and second candle opening
        mask_gap_down = (self.data["Price"].shift(1) - self.data["Open"] >= self.data["25 Body"])
        # Price on second bar must be must be more than halfway up the body of the first bar
        mask_body = (self.data["Price"] >= self.data["Price"].shift(1) + self.data["Body"].shift(1)/2)

        mask = mask_second_red & mask_first_green & mask_first_long & mask_second_long & mask_gap_down & mask_body
        filtered_data = self.data.loc[mask]

        if filtered_data.empty:
            print("No piercing line pattern detected from", self.start_date, "to", self.end_date)
        else:
            print("Piercing line patterns detected at:")
            print(filtered_data)

        return filtered_data
    
    def morning(self) -> pd.DataFrame:
        """
        The morning star candlestick pattern is considered a sign of hope in a bleak market downtrend.
        It is a three-stick pattern: one short-bodied candle between a long red and a long green.
        Traditionally, the 'star' will have no overlap with the longer bodies,
        as the market gaps both on open and close.
        
        It signals that the selling pressure of the first day is subsiding,
        and a bull market is on the horizon.
        """

        # Third candle has a green body
        mask_third_green = (self.data["Price"] > self.data["Open"])
        # First candle has a red body
        mask_first_red = (self.data["Open"].shift(2) > self.data["Price"].shift(2))
        # First and third candles have long bodies (body greater than the 50th percentile)
        mask_first_long = (self.data["Body"].shift(2) >= self.data["50 Body"])
        mask_third_long = (self.data["Body"] >= self.data["50 Body"])
        # Second candle has a short body (less than the 25th percentile)
        mask_second_short = (self.data["Body"].shift(1) <= self.data["25 Body"])

        mask = mask_third_green & mask_first_red & mask_first_long & mask_third_long & mask_second_short
        filtered_data = self.data.loc[mask]

        if filtered_data.empty:
            print("No morning star pattern detected from", self.start_date, "to", self.end_date)
        else:
            print("Morning star pattern detected at:")
            print(filtered_data)

        return filtered_data
    
    def soldiers(self) -> pd.DataFrame:
        """
        The three white soldiers pattern occurs over three days.
        It consists of consecutive long green (or white) candles with small wicks,
        which open and close progressively higher than the previous day.
        
        It is a very strong bullish signal that occurs after a downtrend,
        and shows a steady advance of buying pressure.
        """

        # All three bodies are green
        mask_green = (self.data["Price"] > self.data["Open"]) & (self.data["Price"].shift(1) > self.data["Open"].shift(1)) & (self.data["Price"].shift(2) > self.data["Open"].shift(2))
        # All three candles have small wicks (less than 25% of the body)
        mask_upper_wicks = (0.25*self.data["Body"] >= self.data["U-Wick"]) & (0.25*self.data["Body"].shift(1) >= self.data["U-Wick"].shift(1)) & (0.25*self.data["Body"].shift(2) >= self.data["U-Wick"].shift(2))
        mask_lower_wicks = (0.25*self.data["Body"] >= self.data["L-Wick"]) & (0.25*self.data["Body"].shift(1) >= self.data["L-Wick"].shift(1)) & (0.25*self.data["Body"].shift(2) >= self.data["L-Wick"].shift(2))
        # Successive candles open and close progressively higher
        mask_close = (self.data["Price"] > self.data["Price"].shift(1)) & (self.data["Price"].shift(1) > self.data["Price"].shift(2))
        mask_open = (self.data["Open"] > self.data["Open"].shift(1)) & (self.data["Open"].shift(1) > self.data["Open"].shift(2))

        mask = mask_green & mask_lower_wicks & mask_upper_wicks & mask_close & mask_open
        filtered_data = self.data.loc[mask]

        if filtered_data.empty:
            print("No three white soldier pattern detected from", self.start_date, "to", self.end_date)
        else:
            print("Three white soldier pattern detected at:")
            print(filtered_data)

        return filtered_data
    
    def hanging(self) -> pd.DataFrame:
        """
        The hanging man is the bearish equivalent of a hammer;
        it has the same shape but forms at the end of an uptrend.
        
        It indicates that there was a significant sell-off during the day,
        but that buyers were able to push the price up again.
        The large sell-off is often seen as an indication that the bulls are losing control of the market.
        """

        # Lower wick >= 150% of body
        mask_long_wick = (1.5*self.data["Body"] <= self.data["L-Wick"])
        # Body within the 25th percentile
        mask_short_body = (self.data["Body"] <= self.data["25 Body"])
        # Local maximum
        mask_maximum = (self.data["Max"] == True)

        mask = mask_long_wick & mask_short_body & mask_maximum
        filtered_data = self.data.loc[mask]

        if filtered_data.empty:
            print("No hanging man pattern detected from", self.start_date, "to", self.end_date)
        else:
            print("Hanging man pattern detected at:")
            print(filtered_data)

        return filtered_data
    
    def shooting(self) -> pd.DataFrame:
        """
        The shooting star is the same shape as the inverted hammer,
        but is formed in an uptrend: it has a small lower body, and a long upper wick.
        
        Usually, the market will gap slightly higher on opening,
        and rally to an intra-day high before closing at a price just above the open,
        like a star falling to the ground.
        """

        # Lower wick <= 25% of body
        mask_short_wick = (0.25*self.data["Body"] >= self.data["L-Wick"])
        # Upper wick >= 150% of body
        mask_long_wick = (1.5*self.data["Body"] <= self.data["U-Wick"])
        # Local maximum
        mask_maximum = (self.data["Max"] == True)
        # Candle has a red body
        mask_green = (self.data["Open"] > self.data["Price"])

        mask = mask_short_wick & mask_long_wick & mask_maximum & mask_green
        filtered_data = self.data.loc[mask]

        if filtered_data.empty:
            print("No shooting star pattern detected from", self.start_date, "to", self.end_date)
        else:
            print("Shooting star patterns detected at:")
            print(filtered_data)

        return filtered_data