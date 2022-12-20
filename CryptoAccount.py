# Crypto Account Monitor
# A class which holds all of the values needed to make
# informed decisions what to do with a particular cryptocurrency
# and then perform an action on that cryptocurrency account on coinbase pro

from CryptoStates import CryptoCurrencyPercentageStates
from CryptoSettings import CryptoSettings

class CryptoAccountTracker:
    def __init__(self, accountId: str, productId: str,
                 cryptoName: str, cryptoID: str, minSize: float,
                 cryptoSettingsJsonRaw):

        self.__accountId = accountId  # the account ID on coinbase pro
        self.__productId = productId  # the product ID pair for trading, EX: BTC-USD
        self.__cryptoName = cryptoName
        self.__cryptoID = cryptoID
        self.__minSize = minSize

        self.__referencePrice = 0.0  # in USD
        self.__currentPrice = 0.0  # in USD
        self.__priceSinceLastTransaction = 0.0  # The price of the crypto during the latest transaction
        self.__percentage = 0.0
        self.__cryptoPercentageState = CryptoCurrencyPercentageStates.Neutral
        self.__currentHoldings = 0.0
        # How much assets are stored in the cryptocurrency portfolio compared
        # to the rest
        self.__portfolioPercentage = 0.0

        self.__activePurchases = []

        self.__renewPriceFlag = True
        self.__cryptoSettings = self.__InitCryptoSettings(cryptoSettingsJsonRaw)

    def __InitCryptoSettings(self, cryptoSettingsJsonRaw):
        cryptoSettings = CryptoSettings()
        cryptoSettings.id = cryptoSettingsJsonRaw["id"]
        cryptoSettings.LowPercentageThreshold = float(cryptoSettingsJsonRaw["LowPercentageThreshold"])
        cryptoSettings.HighPercentageThreshold = float(cryptoSettingsJsonRaw["HighPercentageThreshold"])

        cryptoSettings.LowToUpBuyInPercentageThreshold = float(cryptoSettingsJsonRaw["LowToUpBuyInPercentageThreshold"])
        cryptoSettings.MaxPercentageDown = float(cryptoSettingsJsonRaw["MaxPercentageDown"])
        cryptoSettings.HighToDownSellOutPercentageThreshold = float(cryptoSettingsJsonRaw["HighToDownSellOutPercentageThreshold"])

        cryptoSettings.AdjustReferencePriceDownThreshold = float(cryptoSettingsJsonRaw["AdjustReferencePriceDownThreshold"])
        cryptoSettings.AdjustReferencePriceUpThreshold = float(cryptoSettingsJsonRaw["AdjustReferencePriceUpThreshold"])

        cryptoSettings.SmallestAmountToBuyInUSD = float(cryptoSettingsJsonRaw["SmallestAmountToBuyInUSD"])
        cryptoSettings.LargestAmountToBuyInUSD = float(cryptoSettingsJsonRaw["LargestAmountToBuyInUSD"])

        cryptoSettings.MaxPortfolioPercentage = float(cryptoSettingsJsonRaw["MaxPortfolioPercentage"])
        return cryptoSettings

    """
    GetAccountId
    @return: the account id linked to the
    cryptocurreny account on coinbase pro
    """
    def GetAccountId(self):
        return self.__accountId

    """
    GetProductId
    @return: the product id linked to the
    cryptocurrency account on coinbase pro
    """
    def GetProductId(self):
        return self.__productId

    """
    GetCryptoName
    @return: The name of the cryptocurrency used by
    this account tracker
    """
    def GetCryptoName(self):
        return self.__cryptoName

    """
    GetCryptoID
    @return: The crypto ID of the cryptocurrency used by
    this account tracker
    """
    def GetCryptoID(self):
        return self.__cryptoID

    """
    GetMinSize
    @return: The min trading size allowed for buying and selling
    this particular crypto currency
    """
    def GetMinSize(self):
        return self.__minSize

    #TODO: test
    def SetRenewPriceFlag(self, renewPriceFlagValue):
        self.__renewPriceFlag = renewPriceFlagValue

    #TODO: test
    def GetRenewPriceFlag(self):
        return self.__renewPriceFlag

    """
     SetReferencePrice
     @param referencePrice: The price to set as a
     reference for the percentage
     """
    def SetReferencePrice(self, referencePrice: float):
        self.__referencePrice = referencePrice

    """
    GetReferencePrice
    @return: the current reference price set
    """
    def GetReferencePrice(self):
        return self.__referencePrice

    #TODO: test
    def SetPortfolioPercentage(self, portfolioPercentage: float):
        self.__portfolioPercentage = portfolioPercentage

    #TODO: test
    def GetPortfolioPercentage(self):
        return self.__portfolioPercentage

    """
    SetPriceSinceLastTransaction
    @param priceSinceLastTransaction: The price of the crypto currency
    when the last transaction was completed
    """
    def SetPriceSinceLastTransaction(self, priceSinceLastTransaction: float):
        self.__priceSinceLastTransaction = priceSinceLastTransaction

    """
    GetPriceSinceLastTransaction
    @return: The price of the crypto currency when
    the last transaction was completed
    """
    def GetPriceSinceLastTransaction(self):
        return self.__priceSinceLastTransaction

    """
    SetCurrentPrice
    @param currentPrice: The current price to set
    """
    def SetCurrentPrice(self, currentPrice: float):
        self.__currentPrice = currentPrice

    """
    GetCurrentPrice
    @return: the current price of the crypto currency
    """
    def GetCurrentPrice(self):
        return self.__currentPrice

    """
    CalculatePercentage
    Calculates the percentage standing of the crypto currency
    using the reference price and the current price
    """
    def CalculatePercentage(self):
        self.__percentage = round(((float(self.__currentPrice) / float(self.__referencePrice)) - 1) * 100, 2)

    """
    GetPercentage
    @return: The percentage standing of the cryptocurrency
    """
    def GetPercentage(self):
        return self.__percentage

    """
    SetCryptoPercentageState
    @param: cryptoPercentageState: the percentage state of the
    crypto currency (up, down, neutral, etc.) to set
    """
    def SetCryptoPercentageState(self, cryptoPercentageState: CryptoCurrencyPercentageStates):
        self.__cryptoPercentageState = cryptoPercentageState

    """
    GetCryptoPercentageState
    @return: the percentage state of the crypto currency
    """
    def GetCryptoPercentageState(self):
        return self.__cryptoPercentageState

    """
    SetCurrentHoldingsInCoin
    @param currentHoldingsInCoin: The current amount of crypto currency
    the account is holding in the native coin
    """
    def SetCurrentHoldingsInCoin(self, currentHoldingsInCoin: float):
        self.__currentHoldings = currentHoldingsInCoin

    """
    GetCurrentHoldingsInCoin
    @return: the current amount of crypto currency
    the account is holding in the native coin
    """
    def GetCurrentHoldingsInCoin(self):
        return self.__currentHoldings

    """
    GetCurrentHoldingsInUSD
    @return: the current amount of crypto currency
    the account is holding in USD
    """
    def GetCurrentHoldingsInUSD(self):
        return round(self.__currentHoldings * self.__currentPrice, 2)

    """
    AddActivePurchase
    Adds an active purchase for the crypto account tracker to keep
    track of
    @param amountBoughtInCoin: The amount of crypto coin spent on the purchase
    """
    def AddActivePurchase(self, amountBoughtInCoin: float):
        self.__activePurchases.append([amountBoughtInCoin,
                                       self.__currentPrice,  # This is the reference price
                                       self.__currentPrice,
                                       CryptoCurrencyPercentageStates.Neutral])

    #TODO: test
    def RestoreActivePurchasesFromBackup(self, activePurchaseBackup):
        self.__activePurchases = activePurchaseBackup

    """
    UpdateActivePurchasePercentageState
    Updates the Percentage State of a particular active purchase
    @param index: the index of the particular active purchase
    @param percentageState: The percentage state of the particular active purchase
    to set
    """
    def UpdateActivePurchasePercentageState(self, index: int, percentageState):
        self.__activePurchases[index][3] = percentageState

    """
    UpdateActivePurchaseReferencePrice
    Updates the Reference Price of a particular active purchase
    @param index: the index of the particular active purchase
    @param reference: The reference price of the particular active purchase
    to set
    """
    def UpdateActivePurchaseReferencePrice(self, index: int, referencePrice: float):
        self.__activePurchases[index][1] = referencePrice

    """
    RemoveActivePurchase
    Removes an active purchase from the list of active purchases
    @param activePurchaseToRemove: the active purchase to remove from the list
    """
    def RemoveActivePurchase(self, activePurchaseToRemove):
        self.__activePurchases.remove(activePurchaseToRemove)

    """
    GetActivePurchases
    @return: the list of active purchases
    """
    def GetActivePurchases(self):
        return self.__activePurchases

    """
    GetCryptoSettings
    @return: The settings related to this crypto account
    """
    def GetCryptoSettings(self):
        return self.__cryptoSettings
