# CryptoStates.py
# Contains an enumeration of all the possible states
# a cryptocurrency can be in

from enum import IntEnum

class CryptoCurrencyPercentageStates(IntEnum):
    Neutral = 1
    Up = 2
    Down = 3
