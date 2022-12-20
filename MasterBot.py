# Master Bot
# A class which is responsible for monitoring all of the crypto
# currency accounts the user wants to use for trading
import cbpro
import os.path
import sys
import datetime
import time
import json
from math import log10
import CryptoAccount
from CryptoStates import CryptoCurrencyPercentageStates
import MasterBotConstants

class MasterBot:
    def __init__(self, accountKey: str, accountB64secret: str, accountPassphrase: str,
                 usdAccountID: str, operatingPath: str, recordingLogFilename: str,
                 exceptionsLogFilename: str, transactionsLogFoldername: str,
                 cryptoBackupFoldername: str, cryptoSettingsFolderName: str):

        self.__recordingLogFilePath = operatingPath + "/" + recordingLogFilename
        self.__recordingLogFile = self.__InitRecordingFile()

        self.__exceptionsLogFilePath = operatingPath + "/" + exceptionsLogFilename
        self.__exceptionsLogFile = self.__InitExceptionsFile()

        self.__transactionsLogFolderPath = operatingPath + "/" + transactionsLogFoldername
        self.__InitTransactionsFolder()

        self.__cryptoBackupFolderPath = operatingPath + "/" + cryptoBackupFoldername

        self.__cryptoSettingsFolderPath = operatingPath + "/" + cryptoSettingsFolderName
        self.__cryptoIDs, cryptoSettings = self.__GetCryptoIDsAndSettingsFromCryptoSettingsFolder()

        self.__client = self.__InitClient(accountKey, accountB64secret, accountPassphrase)
        self.__usdAccountID = usdAccountID
        # Get the USD Account
        runLoop = True
        while runLoop:
            try:
                self.__usdAccount = self.__client.get_account(self.__usdAccountID)
                self.__usdAmount = round(float(self.__usdAccount['balance']), 2)
                runLoop = False
            except:
                self.__exceptionsLogFile.write(str(datetime.datetime.now()) + "\n")
                self.__exceptionsLogFile.write("An exception occurred trying to initialize the USD account\n\n")
                self.__exceptionsLogFile.close()
                self.__exceptionsLogFile = open(self.__exceptionsLogFilePath, 'a')
                time.sleep(1)
                runLoop = True  # an error occurred so try again


        self.__totalUSDHoldings = 0.0

        self.__cryptoAccountTrackers = self.__InitCryptoAccountTrackers(cryptoSettings)
        self.__RestoreCryptoAccountsFromBackup()
        for cryptoID in self.__cryptoIDs:
            if self.__cryptoAccountTrackers[cryptoID].GetReferencePrice() != 0.0:
                self.__cryptoAccountTrackers[cryptoID].SetRenewPriceFlag(False)

    """
    InitRecordingFile
    Initializes and returns the file used to export recorded data
    @return: an opened file used to log recorded data
    """
    def __InitRecordingFile(self):
        if not os.path.exists(self.__recordingLogFilePath):
            recordingLogFile = open(self.__recordingLogFilePath, 'w')
            recordingLogFile.write(MasterBotConstants.RECORDING_LOG_FILE_FIRST_MESSAGE)
            return recordingLogFile
        else:
            recordingLogFile = open(self.__recordingLogFilePath, 'a')
            return recordingLogFile

    """
    InitExceptionsFile
    Initializes and returns the files used to export exceptions
    @return: an opened files used to log exceptions
    """
    def __InitExceptionsFile(self):
        if not os.path.exists(self.__exceptionsLogFilePath):
            exceptionsLogFile = open(self.__exceptionsLogFilePath, 'w')
            exceptionsLogFile.write(MasterBotConstants.EXCEPTION_LOG_FILE_FIRST_MESSAGE)
            return exceptionsLogFile
        else:
            exceptionsLogFile = open(self.__exceptionsLogFilePath, 'a')
            return exceptionsLogFile

    """
    InitTransactionsFolder
    Initializes the Transactions Folder where transactions related to a
    particular crypto currency are stored
    """
    def __InitTransactionsFolder(self):
        if not os.path.isdir(self.__transactionsLogFolderPath):
            os.mkdir(self.__transactionsLogFolderPath)

    """
    InitClient
    Initializes the coinbase pro authenticated client which is used to access
    all of the crypto accounts
    @param accountKey: The key to the coinbase pro account
    @param accountB64secret: The 64-word secret code for the coinbase pro account
    @param accountPassphrase: The passphrase used for the coinbase pro account
    @return: The authenticated coinbase pro account client
    """
    def __InitClient(self, accountKey: str, accountB64secret: str, accountPassphrase: str):
        runLoop = True
        while runLoop:
            try:
                client = cbpro.AuthenticatedClient(key=accountKey,
                                                   b64secret=accountB64secret,
                                                   passphrase=accountPassphrase)
                return client
            except:
                self.__exceptionsLogFile.write(str(datetime.datetime.now()) + "\n")
                self.__exceptionsLogFile.write("This Exception occurred trying to initialize the base CBPro client")
                self.__exceptionsLogFile.write("Trying again now")
                self.__exceptionsLogFile.close()
                self.__exceptionsLogFile = open(self.__exceptionsLogFilePath, 'a')
                time.sleep(1)
                runLoop = True

    """
    InitCryptoAccountTrackers
    Initializes the crypto currency account trackers used to
    monitor the trends in a particular crypto currency.
    This functions takes the crypto IDs, queries CBPro and extracts
    the necessary data it needs, along with the inputted crypto currency
    settings to properly initialize the crypto currency account trackers
    @param cryptoSettings: a list of all of the crypto currencies' settings
    which will be paired with the appropriate crypto account tracker
    @return: a list of crypto account trackers
    """
    def __InitCryptoAccountTrackers(self, cryptoSettings):
        runLoop = True
        while runLoop:
            try:
                dataOnAllAccounts = self.__client.get_accounts()
                dataOnAllCurrencies = self.__client.get_currencies()
                dataOnAllProducts = self.__client.get_products()
                runLoop = False
            except:
                self.__exceptionsLogFile.write(str(datetime.datetime.now()) + "\n")
                self.__exceptionsLogFile.write("An exception occurred in the InitCryptoAccountTrackers function\n\n")
                self.__exceptionsLogFile.close()
                self.__exceptionsLogFile = open(self.__exceptionsLogFilePath, 'a')
                time.sleep(1)
                runLoop = True  # an error occurred so try again

        cryptoAccountTrackers = {}
        for cryptoID in self.__cryptoIDs:
            currentCryptoAccountID = ""
            currentCryptoName = ""
            currentMinSize = 0.0
            currentCryptoSettings = ""

            for accountData in dataOnAllAccounts:
                if cryptoID == accountData["currency"]:
                    currentCryptoAccountID = accountData["id"]
                    break

            for currencyData in dataOnAllCurrencies:
                if cryptoID == currencyData["id"]:
                    currentCryptoName = currencyData["name"]
                    break

            for productData in dataOnAllProducts:
                if cryptoID + "-USD" == productData["id"]:
                    currentMinSize = float(productData["base_min_size"])
                    break

            for cryptoSetting in cryptoSettings:
                if cryptoID == cryptoSetting["id"]:
                    currentCryptoSettings = cryptoSetting
                    break

            cryptoAccountTracker = CryptoAccount.CryptoAccountTracker(
                accountId=currentCryptoAccountID,
                productId=(cryptoID + "-USD"),
                cryptoName=currentCryptoName,
                cryptoID=cryptoID,
                minSize=currentMinSize,
                cryptoSettingsJsonRaw=currentCryptoSettings)
            # Use a map to map the crypto ID to the account tracker
            cryptoAccountTrackers.update({cryptoID: cryptoAccountTracker})

        return cryptoAccountTrackers

    """
    RestoreCryptoAccountsFromBackup
    Loads the backup files for each crypto account and restores
    the active buy orders and the last reference price and the
    price since the last transaction was made on that crypto account
    """
    def __RestoreCryptoAccountsFromBackup(self):
        if not os.path.isdir(self.__cryptoBackupFolderPath):
            print("Fatal Error!!, no cryptocurrency backup folder found")
            print("Nothing to do exiting!!")
            self.__exceptionsLogFile.write(str(datetime.datetime.now()) + "\n")
            self.__exceptionsLogFile.write("Fatal Error!!, no cryptocurrency backup folder found\n")
            self.__exceptionsLogFile.write("Nothing to do exiting!!\n")
            self.CleanUp()
            sys.exit(-1)

        cryptoBackupFilenames = [f for f in os.listdir(self.__cryptoBackupFolderPath)
                              if os.path.isfile(os.path.join(self.__cryptoBackupFolderPath, f))]

        for filename in cryptoBackupFilenames:
            cryptoID = (filename[:filename.find(".")])
            backupFile = open(self.__cryptoBackupFolderPath + "/" + filename, "r")
            fileContent = backupFile.read().splitlines()
            backupBuyOrders = []
            for line in fileContent:
                if line[:17] == "Reference Price: ":
                    backupReferencePrice = float(line[17:])
                    self.__cryptoAccountTrackers[cryptoID].SetReferencePrice(backupReferencePrice)
                elif line[:24] == "Last Transaction Price: ":
                    backupLastTransactionPrice = float(line[24:])
                    self.__cryptoAccountTrackers[cryptoID].SetPriceSinceLastTransaction(backupLastTransactionPrice)
                else:
                    backupAmountBoughtInCoin = float(line.split(",")[0])
                    backupReferencePriceBoughtInUSD = float(line.split(",")[1])
                    backupPriceBoughtAtInUSD = float(line.split(",")[2])
                    backupCryptoPercentageState = CryptoCurrencyPercentageStates(int(line.split(",")[3]))
                    backupBuyOrders.append([backupAmountBoughtInCoin,
                                            backupReferencePriceBoughtInUSD,
                                            backupPriceBoughtAtInUSD,
                                            backupCryptoPercentageState])

            backupFile.close()
            self.__cryptoAccountTrackers[cryptoID].RestoreActivePurchasesFromBackup(backupBuyOrders)

    """
    GetCryptoIDsAndSettingsFromCryptoSettingsFolder
    Reads all of the crypto setting .json files and creates a list
    of crypto IDs and crypto settings from reading these files
    @return: a list of all the crypto IDs being used
    @return: a list of all the crypto settings to be used
    """
    def __GetCryptoIDsAndSettingsFromCryptoSettingsFolder(self):
        if not os.path.isdir(self.__cryptoSettingsFolderPath):
            print("Fatal Error!!, no cryptocurrency settings folder found")
            print("Nothing to do exiting!!")
            self.__exceptionsLogFile.write(str(datetime.datetime.now()) + "\n")
            self.__exceptionsLogFile.write("Fatal Error!!, no cryptocurrency settings folder found\n")
            self.__exceptionsLogFile.write("Nothing to do exiting!!\n")
            self.CleanUp()
            sys.exit(-1)

        cryptoSettingsFilenames = [f for f in os.listdir(self.__cryptoSettingsFolderPath)
                                 if os.path.isfile(os.path.join(self.__cryptoSettingsFolderPath, f))]
        cryptoIDs = []
        cryptoSettings = []
        for filename in cryptoSettingsFilenames:
            cryptoIDs.append(filename[:filename.find(".")])
            cryptoSettingsPath = self.__cryptoSettingsFolderPath + "/" + filename

            cryptoSettingsFile = open(cryptoSettingsPath, "r")
            cryptoSettings.append(json.load(cryptoSettingsFile))
            cryptoSettingsFile.close()

        return cryptoIDs, cryptoSettings

    """
    UpdateHoldings
    Updates the amount of crypto currency you have in an account,
    this value will not change unless a buy or sell occurs
    @param cryptoID: The crypto ID of the cryptocurrency account to update the holdings of
    """
    def __UpdateHoldings(self, cryptoID: str):
        runLoop = True
        while runLoop:
            try:
                accountData = self.__client.get_account(self.__cryptoAccountTrackers[cryptoID].GetAccountId())
                self.__cryptoAccountTrackers[cryptoID].SetCurrentHoldingsInCoin(float(accountData['balance']))
                runLoop = False  # if succeeded, don't run the loop again
            except:
                self.__exceptionsLogFile.write(str(datetime.datetime.now()) + "\n")
                self.__exceptionsLogFile.write("An exception occurred in the Update Holdings function\n\n")
                self.__exceptionsLogFile.close()
                self.__exceptionsLogFile = open(self.__exceptionsLogFilePath, 'a')
                time.sleep(1)
                runLoop = True  # an error occurred so try again

    """
    UpdateCurrentPrice
    Updates and gets the current price (unit price of a full coin)
    of the crypto currency for a particular account
    @param cryptoID: The crypto ID of the cryptocurrency account to update the holdings of
    """
    def __UpdateCurrentPrice(self, cryptoID: str):
        runLoop = True
        while runLoop:
            try:
                accountProductTables = self.__client.get_product_ticker(
                    product_id=self.__cryptoAccountTrackers[cryptoID].GetProductId())
                self.__cryptoAccountTrackers[cryptoID].SetCurrentPrice(float(accountProductTables['price']))
                runLoop = False
            except:
                self.__exceptionsLogFile.write(str(datetime.datetime.now()) + "\n")
                self.__exceptionsLogFile.write("An exception occurred in the Update Current Price function\n\n")
                self.__exceptionsLogFile.close()
                self.__exceptionsLogFile = open(self.__exceptionsLogFilePath, 'a')
                time.sleep(1)
                runLoop = True  # an error occurred so try again

    """
    GetUSDAmount
    @return: the amount of USD available
    """
    def GetUSDAmount(self):
        return self.__usdAmount

    """
    GetCryptoIDs
    @return: A list of all the cryptoIDs
    """
    def GetCryptoIDs(self):
        return self.__cryptoIDs

    """
    GetCryptoAccountTracker
    Gets a particular crypto account tracker based on the inputted
    crypto ID
    @param cryptoID: The crypto ID of the cryptocurrency account tracker
    @return: The corresponding cryptocurrency account tracker
    """
    def GetCryptoAccountTracker(self, cryptoID: str):
        return self.__cryptoAccountTrackers[cryptoID]

    """
    GetAllCryptoAccountTrackers
    @return: all of the cryptocurrency account trackers
    """
    def GetAllCryptoAccountTrackers(self):
        return self.__cryptoAccountTrackers

    """
    UpdateUSDAccountAndAccountHoldings
    Updates the USD account and the amount of USD in the account
    """
    def UpdateUSDAccountAndAccountHoldings(self):
        runLoop = True
        while runLoop:
            try:
                self.__usdAccount = self.__client.get_account(self.__usdAccountID)
                self.__usdAmount = round(float(self.__usdAccount['balance']), 2)
                runLoop = False
            except:
                self.__exceptionsLogFile.write((str(datetime.datetime.now())) + "\n")
                self.__exceptionsLogFile.write("An exception occurred in the Update USD Account loop\n\n")
                self.__exceptionsLogFile.close()
                self.__exceptionsLogFile = open(self.__exceptionsLogFilePath, 'a')
                time.sleep(1)
                runLoop = True

    """
    UpdateCryptoAccount
    Updates a particular crypto account by getting the current holdings
    in coin, and the current price
    @param cryptoID: The crypto ID of the cryptocurrency to update
    """
    def UpdateCryptoAccount(self, cryptoID):
        self.__UpdateHoldings(cryptoID)
        self.__UpdateCurrentPrice(cryptoID)

    """
    RenewPricesForCryptoAccount
    Used to reset the reference price and the
    price since the last transaction for that account
    by setting them both equal to the current unit price
    @param cryptoID: the cryptoID of the cryptocurrency to renew the price of
    """
    def RenewPricesForCryptoAccount(self, cryptoID):
        currentPrice = self.__cryptoAccountTrackers[cryptoID].GetCurrentPrice()
        self.__cryptoAccountTrackers[cryptoID].SetReferencePrice(currentPrice)
        self.__cryptoAccountTrackers[cryptoID].SetPriceSinceLastTransaction(currentPrice)
        self.__cryptoAccountTrackers[cryptoID].SetCryptoPercentageState(CryptoCurrencyPercentageStates.Neutral)

    """
    RunPercentageCalculationOfCryptoAccount
    Calculates the current percentage of a particular crypto account
    @param cryptoID: The crypto ID of the crypto account to run percentage
    calculations and analysis on
    """
    def RunPercentageCalculationOfCryptoAccount(self, cryptoID):
        cryptoSettings = self.__cryptoAccountTrackers[cryptoID].GetCryptoSettings()
        self.__cryptoAccountTrackers[cryptoID].CalculatePercentage()
        if self.__cryptoAccountTrackers[cryptoID].GetCryptoPercentageState() == CryptoCurrencyPercentageStates.Neutral:

            if self.__cryptoAccountTrackers[cryptoID].GetPercentage() <= cryptoSettings.LowPercentageThreshold:
                self.__cryptoAccountTrackers[cryptoID].SetCryptoPercentageState(CryptoCurrencyPercentageStates.Down)
            elif self.__cryptoAccountTrackers[cryptoID].GetPercentage() >= cryptoSettings.HighPercentageThreshold:
                self.__cryptoAccountTrackers[cryptoID].SetCryptoPercentageState(CryptoCurrencyPercentageStates.Up)

    """
    UpdatePortfolioPercentagesOfAllAccounts
    Updates how much percentage of funds is allocated to each account and sets
    the accordingly to each account
    """
    def UpdatePortfolioPercentagesOfAllAccounts(self):
        for cryptoID in self.__cryptoIDs:
            currentUSDHoldingsInCrypto = self.__cryptoAccountTrackers[cryptoID].GetCurrentHoldingsInUSD()
            portfolioPercentage = round((currentUSDHoldingsInCrypto / self.__totalUSDHoldings) * 100.0, 2)
            self.__cryptoAccountTrackers[cryptoID].SetPortfolioPercentage(portfolioPercentage)

    """
    IsCryptoUp
    @param cryptoID: The ID of the crypto currency to check
    @return: if that cryptocurrency is up
    """
    def IsCryptoUp(self, cryptoID):
        return self.__cryptoAccountTrackers[cryptoID].GetCryptoPercentageState() == CryptoCurrencyPercentageStates.Up

    """
    IsCryptoNeutral
    @param cryptoID: The ID of the crypto currency to check
    @return: if that cryptocurrency is neutral (neither up or down)
    """
    def IsCryptoNeutral(self, cryptoID):
        return self.__cryptoAccountTrackers[cryptoID].GetCryptoPercentageState() == CryptoCurrencyPercentageStates.Neutral

    """
    IsCryptoDown
    @param cryptoID: The ID of the crypto currency to check
    @return: if that cryptocurrency is down
    """
    def IsCryptoDown(self, cryptoID):
        return self.__cryptoAccountTrackers[cryptoID].GetCryptoPercentageState() == CryptoCurrencyPercentageStates.Down

    def IsGoingBackDown(self, cryptoID):
        cryptoSettings = self.__cryptoAccountTrackers[cryptoID].GetCryptoSettings()
        return self.IsCryptoUp(cryptoID) and \
                self.__cryptoAccountTrackers[cryptoID].GetPercentage() < cryptoSettings.HighPercentageThreshold

    def SetCryptoNeutral(self, cryptoID):
        self.__cryptoAccountTrackers[cryptoID].SetCryptoPercentageState(CryptoCurrencyPercentageStates.Neutral)

    """
    ShouldBuy
    @param cryptoID: The crypto ID of the cryptocurrency to check
    @return: If a buy order should be made for this cryptocurrency
    """
    def ShouldBuy(self, cryptoID):
        cryptoSettings = self.__cryptoAccountTrackers[cryptoID].GetCryptoSettings()
        return self.IsCryptoDown(cryptoID) and \
               self.__cryptoAccountTrackers[cryptoID].GetPercentage() >= cryptoSettings.LowToUpBuyInPercentageThreshold

    """
    GetAmountToBuyInUSD
    Calculates the amount of crypto to buy based on its recent status
    @param cryptoID: The cryptoID of the cryptocurrency to use
    @return: The amount to buy into this crypto currency in USD
    """
    def GetAmountToBuyInUSD(self, cryptoID):
        cryptoSettings = self.__cryptoAccountTrackers[cryptoID].GetCryptoSettings()
        cryptoAccount = self.__cryptoAccountTrackers[cryptoID]
        amountToBuyInUSD = 0.0
        percentageSinceLastTransaction = round(((float(cryptoAccount.GetCurrentPrice())
                                                 / float(cryptoAccount.GetPriceSinceLastTransaction())) - 1) * 100, 2)
        if percentageSinceLastTransaction >= cryptoSettings.LowToUpBuyInPercentageThreshold:
            amountToBuyInUSD = cryptoSettings.SmallestAmountToBuyInUSD
        elif cryptoSettings.LowToUpBuyInPercentageThreshold >= percentageSinceLastTransaction >= cryptoSettings.MaxPercentageDown:
            priceDifference = cryptoSettings.LargestAmountToBuyInUSD - cryptoSettings.SmallestAmountToBuyInUSD
            percentageDifference = cryptoSettings.MaxPercentageDown - cryptoSettings.LowToUpBuyInPercentageThreshold
            slope = priceDifference / percentageDifference
            yOffset = (slope * cryptoSettings.MaxPercentageDown) - cryptoSettings.LargestAmountToBuyInUSD
            amountToBuyInUSD = round((slope * percentageSinceLastTransaction) - yOffset, 2)
        else:
            amountToBuyInUSD = cryptoSettings.LargestAmountToBuyInUSD

        # check to make sure you are not going over the portfolio percentage limit
        currentCryptoHoldingsInUSD = self.__cryptoAccountTrackers[cryptoID].GetCurrentHoldingsInUSD()
        holdingsPercentageAfterPurchase = round(((amountToBuyInUSD + currentCryptoHoldingsInUSD) / self.__totalUSDHoldings) * 100.0, 2)
        if holdingsPercentageAfterPurchase > cryptoSettings.MaxPortfolioPercentage:
            currentPortfolioPercentage = self.__cryptoAccountTrackers[cryptoID].GetPortfolioPercentage()
            holdingsPercentageDifference = cryptoSettings.MaxPortfolioPercentage - currentPortfolioPercentage
            amountToBuyInUSD = round(self.__totalUSDHoldings * (holdingsPercentageDifference / 100.0), 2)

        # account for the fees if you barely have enough to buy in
        if amountToBuyInUSD >= round(self.__usdAmount - (self.__usdAmount * 0.006), 2):
            amountToBuyInUSD = round(self.__usdAmount - (self.__usdAmount * 0.006), 2)

        if amountToBuyInUSD < cryptoSettings.SmallestAmountToBuyInUSD:
            amountToBuyInUSD = 0.0

        return amountToBuyInUSD

    """
    GetAmountToBuyInCoin
    Calculates and returns the amount of crypto to buy in terms of
    the crypto coin unit
    @param cryptoID:  The cryptoID of the cryptocurrency to use
    @param amountToBuyInUSD: The goal amount to buy of this cryptocurrency
    @return: The amount to buy of the cryptocurrency in terms of the
    crypto coin unit
    """
    def GetAmountToBuyInCoin(self, cryptoID, amountToBuyUSD: float):
        cryptoAccount = self.__cryptoAccountTrackers[cryptoID]
        rawAmountToBuyInCoin = amountToBuyUSD / cryptoAccount.GetCurrentPrice()
        decimalPlacesToRoundTo = int(log10(1.0 / cryptoAccount.GetMinSize()))
        # A floor function to a certain decimal place
        return round(rawAmountToBuyInCoin - 0.4999 * 10**(-1.0 * decimalPlacesToRoundTo), decimalPlacesToRoundTo)

    """
    BuyIn
    Buys a certain amount of the cryptocurrency and adds it to the
    list of active buy orders
    @param cryptoID: The cryptoID of the cryptocurrency to buy in
    @param amountToBuyInCoin: The amount of cryptocurrency to buy in
    the native coin amount
    """
    #TODO: Test in simulation
    def BuyIn(self, cryptoID, amountToBuyInCoin):
        runLoop = True
        while runLoop:
            try:
                self.__client.buy(product_id=self.__cryptoAccountTrackers[cryptoID].GetProductId(),
                                      order_type="market",
                                      size=amountToBuyInCoin)
                runLoop = False
            except:
                self.__exceptionsLogFile.write(str(datetime.datetime.now()) + "\n")
                self.__exceptionsLogFile.write("An exception occurred trying to buy: ")
                self.__exceptionsLogFile.write(str(amountToBuyInCoin) + " " + cryptoID + "\n")
                self.__exceptionsLogFile.close()
                self.__exceptionsLogFile = open(self.__exceptionsLogFilePath, 'a')
                runLoop = True
                time.sleep(1)

        self.__cryptoAccountTrackers[cryptoID].AddActivePurchase(amountToBuyInCoin)

    """
    EvaluateAndAdjustBuyOrders
    Evaluates the buy orders by comparing the price the order was placed
    to the current price and adjusting the percentage state of that order
    accordingly. It also adjusts the reference price for the buy orders based
    on the current price
    @param cryptoID: the cryptoID of the cryptocurrency to evaluate the
    buy orders of
    """
    def EvaluateAndAdjustBuyOrders(self, cryptoID):
        cryptoSettings = self.__cryptoAccountTrackers[cryptoID].GetCryptoSettings()
        activeBuys = self.__cryptoAccountTrackers[cryptoID].GetActivePurchases()
        lenOfActiveBuys = len(activeBuys)
        i = 0
        while i < lenOfActiveBuys:
            activeBuy = activeBuys[i]
            referencePrice = activeBuy[1]
            currentPercentageState = activeBuy[3]
            referencePercentDifference = round(
                ((self.__cryptoAccountTrackers[cryptoID].GetCurrentPrice() / referencePrice) - 1.0) * 100, 2)
            if currentPercentageState == CryptoCurrencyPercentageStates.Neutral or currentPercentageState == CryptoCurrencyPercentageStates.Down:
                if referencePercentDifference <= cryptoSettings.LowPercentageThreshold:
                    currentPercentageState = CryptoCurrencyPercentageStates.Down

                elif referencePercentDifference >= cryptoSettings.HighPercentageThreshold:
                    currentPercentageState = CryptoCurrencyPercentageStates.Up
                else:
                    currentPercentageState = CryptoCurrencyPercentageStates.Neutral
            self.__cryptoAccountTrackers[cryptoID].UpdateActivePurchasePercentageState(i, currentPercentageState)

            if currentPercentageState == CryptoCurrencyPercentageStates.Up:
                if referencePercentDifference >= cryptoSettings.AdjustReferencePriceUpThreshold:
                    currentPrice = self.__cryptoAccountTrackers[cryptoID].GetCurrentPrice()
                    desiredPercentageDifferenceInDecimal = cryptoSettings.HighPercentageThreshold / 100.0
                    newReferencePrice = round(currentPrice * ((desiredPercentageDifferenceInDecimal - 1.0) * -1.0), 2)
                    self.__cryptoAccountTrackers[cryptoID].UpdateActivePurchaseReferencePrice(i, newReferencePrice)

            i = i + 1

    """
    ShouldSell
    @param cryptoID: The crypto ID of the cryptocurrency to check
    @return: If a sell should be made on one of the active purchases
    """
    def ShouldSell(self, cryptoID):
        cryptoSettings = self.__cryptoAccountTrackers[cryptoID].GetCryptoSettings()
        activeBuys = self.__cryptoAccountTrackers[cryptoID].GetActivePurchases()
        for activeBuy in activeBuys:
            currentPrice = self.__cryptoAccountTrackers[cryptoID].GetCurrentPrice()
            percentage = round(((float(currentPrice) / float(activeBuy[1])) - 1) * 100, 2)
            currentPercentageState = activeBuy[3]
            if currentPercentageState == CryptoCurrencyPercentageStates.Up and \
                    percentage <= cryptoSettings.HighToDownSellOutPercentageThreshold:
                return True
        return False

    """
    GetOrdersToSell
    @param cryptoID: the cryptoID of the cryptocurrency to get orders to sell
    @return: The orders that should be sold
    """
    def GetOrdersToSell(self, cryptoID):
        cryptoSettings = self.__cryptoAccountTrackers[cryptoID].GetCryptoSettings()
        activeBuys = self.__cryptoAccountTrackers[cryptoID].GetActivePurchases()
        ordersToSell = []
        for activeBuy in activeBuys:
            currentPrice = self.__cryptoAccountTrackers[cryptoID].GetCurrentPrice()
            percentage = round(((float(currentPrice) / float(activeBuy[1])) - 1) * 100, 2)
            currentPercentageState = activeBuy[3]
            if currentPercentageState == CryptoCurrencyPercentageStates.Up and \
                    percentage <= cryptoSettings.HighToDownSellOutPercentageThreshold:
                ordersToSell.append(activeBuy)

        return ordersToSell

    """
    SellOut
    Sells out a particular group of orders which have been held
    @param cryptoID: The cryptoID of the cryptocurrency to sell
    @param ordersToSell: A list of the orders to sell
    """
    # TODO: Test in simulation
    def SellOut(self, cryptoID, ordersToSell):
        for orderToSell in ordersToSell:
            amountToSellInCoin = orderToSell[0]
            runLoop = True
            while runLoop:
                try:
                    self.__client.sell(product_id=self.__cryptoAccountTrackers[cryptoID].GetProductId(),
                                      order_type="market",
                                      size=amountToSellInCoin)
                    runLoop = False
                except:
                    self.__exceptionsLogFile.write(str(datetime.datetime.now()) + "\n")
                    self.__exceptionsLogFile.write("An exceptions occurred trying to sell: ")
                    self.__exceptionsLogFile.write(str(amountToSellInCoin) + " " + cryptoID + "\n")
                    self.__exceptionsLogFile.close()
                    self.__exceptionsLogFile = open(self.__exceptionsLogFilePath, 'a')
                    runLoop = True
                    time.sleep(1)

            self.__cryptoAccountTrackers[cryptoID].RemoveActivePurchase(orderToSell)

    """
    WriteBuyTransactionToLogFile
    Write a buy transaction to a log file for evaluation of trading
    @param cryptoID: the crypto ID of the cryptocurrency
    @param amountInUSD: The amount of the cryptocurrency in USD
    @param amountInCoin: The amount of the cryptocurrency in terms of
    the crypto coin
    """
    def WriteBuyTransactionToLogFile(self, cryptoID, amountInCoin):
        amountInUSD = amountInCoin * self.__cryptoAccountTrackers[cryptoID].GetCurrentPrice()
        filePath = self.__transactionsLogFolderPath + "/" + cryptoID + ".csv"
        if not os.path.exists(filePath):
            TransactionLogFile = open(filePath, 'w')
            TransactionLogFile.write("Transaction,Amount ($),Amount (" + cryptoID + "),Current Price,Price Since Last Transaction,Date-Time\n")
            TransactionLogFile.write("Buy,")
            TransactionLogFile.write(str(amountInUSD) + ",")
            TransactionLogFile.write(str(amountInCoin) + ",")
            TransactionLogFile.write(str(self.__cryptoAccountTrackers[cryptoID].GetCurrentPrice()) + ",")
            TransactionLogFile.write(str(self.__cryptoAccountTrackers[cryptoID].GetPriceSinceLastTransaction()) + ",")
            TransactionLogFile.write(str(datetime.datetime.now()) + "\n")
            TransactionLogFile.close()
        else:
            TransactionLogFile = open(filePath, 'a')
            TransactionLogFile.write("Buy,")
            TransactionLogFile.write(str(amountInUSD) + ",")
            TransactionLogFile.write(str(amountInCoin) + ",")
            TransactionLogFile.write(str(self.__cryptoAccountTrackers[cryptoID].GetCurrentPrice()) + ",")
            TransactionLogFile.write(str(self.__cryptoAccountTrackers[cryptoID].GetPriceSinceLastTransaction()) + ",")
            TransactionLogFile.write(str(datetime.datetime.now()) + "\n")
            TransactionLogFile.close()

    """
    WriteSellTransactionToLogFile
    Write a sell transaction to a log file for evaluation of trading
    @param cryptoID: the crypto ID of the cryptocurrency
    @param amountInCoin: The amount of the cryptocurrency in terms of
    the crypto coin
    """
    def WriteSellTransactionToLogFile(self, cryptoID, amountInCoin):
        amountInUSD = amountInCoin * self.__cryptoAccountTrackers[cryptoID].GetCurrentPrice()
        filePath = self.__transactionsLogFolderPath + "/" + cryptoID + ".csv"
        if not os.path.exists(filePath):
            TransactionLogFile = open(filePath, 'w')
            TransactionLogFile.write("Transaction,Amount ($),Amount (" + cryptoID + "),Current Price,Price Since Last Transaction,Date-Time\n")
            TransactionLogFile.write("Sell,")
            TransactionLogFile.write(str(amountInUSD) + ",")
            TransactionLogFile.write(str(amountInCoin) + ",")
            TransactionLogFile.write(str(self.__cryptoAccountTrackers[cryptoID].GetCurrentPrice()) + ",")
            TransactionLogFile.write(str(self.__cryptoAccountTrackers[cryptoID].GetPriceSinceLastTransaction()) + ",")
            TransactionLogFile.write(str(datetime.datetime.now()) + "\n")
            TransactionLogFile.close()
        else:
            TransactionLogFile = open(filePath, 'a')
            TransactionLogFile.write("Sell,")
            TransactionLogFile.write(str(amountInUSD) + ",")
            TransactionLogFile.write(str(amountInCoin) + ",")
            TransactionLogFile.write(str(self.__cryptoAccountTrackers[cryptoID].GetCurrentPrice()) + ",")
            TransactionLogFile.write(str(self.__cryptoAccountTrackers[cryptoID].GetPriceSinceLastTransaction()) + ",")
            TransactionLogFile.write(str(datetime.datetime.now()) + "\n")
            TransactionLogFile.close()

    """
    ShouldRenewPriceForCryptoAccount
    @param cryptoID: The cryptoID of the cryptocurrency to use
    @return: if the reference price for this cryptocurrency should be renewed
    """
    def ShouldRenewPriceForCryptoAccount(self, cryptoID):
        return self.__cryptoAccountTrackers[cryptoID].GetRenewPriceFlag()

    """
    SetRenewPriceFlagForCryptoAccount
    @param cryptoID: The cryptoID of the cryptocurrency to use
    @param renewPriceFlagValue: The value to set the renew price flag to
    """
    def SetRenewPriceFlagForCryptoAccount(self, cryptoID, renewPriceFlagValue):
        self.__cryptoAccountTrackers[cryptoID].SetRenewPriceFlag(renewPriceFlagValue)

    """
    ShouldAdjustFallingReferencePrice
    @param cryptoID: The cryptocurrency to use
    @return: If the reference price of this crypto currency should be re-adjusted
    because the price is falling a lot
    """
    def ShouldAdjustFallingReferencePrice(self, cryptoID):
        cryptoSettings = self.__cryptoAccountTrackers[cryptoID].GetCryptoSettings()
        return self.__cryptoAccountTrackers[cryptoID].GetPercentage() <= cryptoSettings.AdjustReferencePriceDownThreshold

    """
    ShouldAdjustIncreasingReferencePrice
    @param cryptoID: The cryptocurrency to use
    @return: If the reference price of this crypto currency should be re-adjusted
    because the price is increasing a lot
    """
    def ShouldAdjustIncreasingReferencePrice(self, cryptoID):
        cryptoSettings = self.__cryptoAccountTrackers[cryptoID].GetCryptoSettings()
        return self.__cryptoAccountTrackers[cryptoID].GetPercentage() >= cryptoSettings.AdjustReferencePriceUpThreshold

    """
    AdjustFallingReferencePrice
    Adjusts the reference price of the cryptocurrency when it has
    fallen a lot so it is within a certain threshold for evaluation
    @param cryptoID: The crypto ID of the cryptocurrency to adjust the reference price of
    """
    def AdjustFallingReferencePrice(self, cryptoID):
        cryptoSettings = self.__cryptoAccountTrackers[cryptoID].GetCryptoSettings()
        currentPrice = self.__cryptoAccountTrackers[cryptoID].GetCurrentPrice()
        desiredPercentageDifferenceInDecimal = cryptoSettings.LowPercentageThreshold / 100.0
        newReferencePrice = round(currentPrice * ((-1.0 * desiredPercentageDifferenceInDecimal) + 1.0), 2)
        self.__cryptoAccountTrackers[cryptoID].SetReferencePrice(newReferencePrice)

    """
    AdjustIncreasingReferencePrice
    Adjusts the reference price of the cryptocurrency when it has
    increased a lot so it is within a certain threshold for evaluation
    @param cryptoID: The crypto ID of the cryptocurrency to adjust the reference price of
    """
    def AdjustIncreasingReferencePrice(self, cryptoID):
        cryptoSettings = self.__cryptoAccountTrackers[cryptoID].GetCryptoSettings()
        currentPrice = self.__cryptoAccountTrackers[cryptoID].GetCurrentPrice()
        desiredPercentageDifferenceInDecimal = cryptoSettings.HighPercentageThreshold / 100.0
        newReferencePrice = round(currentPrice * ((desiredPercentageDifferenceInDecimal - 1.0) * -1.0), 2)
        self.__cryptoAccountTrackers[cryptoID].SetReferencePrice(newReferencePrice)
        # Only do this for increasing reference price because if you do this for falling as well,
        # you may miss a buy
        self.__cryptoAccountTrackers[cryptoID].SetCryptoPercentageState(CryptoCurrencyPercentageStates.Neutral)
        self.__cryptoAccountTrackers[cryptoID].SetPriceSinceLastTransaction(newReferencePrice)

    """
    UpdateTotalHoldingsInUSDFromAllAccounts
    Updates the total amount of holdings from all of the active
    crypto accounts
    """
    def UpdateTotalHoldingsInUSDFromAllAccounts(self):
        self.__totalUSDHoldings = self.__usdAmount
        for cryptoID in self.__cryptoIDs:
            self.__totalUSDHoldings = self.__totalUSDHoldings + self.__cryptoAccountTrackers[cryptoID].GetCurrentHoldingsInUSD()

    # USED FOR TESTING PURPOSES ONLY
    def SetUSDAmount(self, usdAmount):
        self.__usdAmount = usdAmount
    # USED FOR TESTING PURPOSES ONLY
    def SetTotalHoldings(self, totalHoldings):
        self.__totalUSDHoldings = totalHoldings

    #TODO: test in simulation
    def LogCryptoDataToRecordingFile(self):
        # for the first crypto ID, put in the date and time
        self.__recordingLogFile.write(str(datetime.datetime.now()) + "\n")
        for cryptoID in self.__cryptoIDs:
            self.__recordingLogFile.write(self.__cryptoAccountTrackers[cryptoID].GetCryptoName() + ":\n")
            self.__recordingLogFile.write(
                "   Reference Price: " + str(self.__cryptoAccountTrackers[cryptoID].GetReferencePrice()) + "\n")
            self.__recordingLogFile.write(
                "   Current Price: " + str(self.__cryptoAccountTrackers[cryptoID].GetCurrentPrice()) + "\n")
            self.__recordingLogFile.write(
                "   Percentage: " + str(self.__cryptoAccountTrackers[cryptoID].GetPercentage()) + "\n")
            self.__recordingLogFile.write(
                "   Holdings in Coin: " + str(self.__cryptoAccountTrackers[cryptoID].GetCurrentHoldingsInCoin()) + "\n")
            self.__recordingLogFile.write(
                "   Holdings in USD: " + str(self.__cryptoAccountTrackers[cryptoID].GetCurrentHoldingsInUSD()) + "\n")
            self.__recordingLogFile.write(
                "   Portfolio Percentage: " + str(self.__cryptoAccountTrackers[cryptoID].GetPortfolioPercentage()) +
                "\n")

        usdPortfolioPercentage = round((self.__usdAmount / self.__totalUSDHoldings) * 100.0, 2)
        self.__recordingLogFile.write("USD Account:\n")
        self.__recordingLogFile.write("   Holdings: " + str(self.__usdAmount) + "\n")
        self.__recordingLogFile.write("   Portfolio Percentage: " + str(usdPortfolioPercentage) + "\n\n")
        self.__recordingLogFile.close()
        self.__recordingLogFile = open(self.__recordingLogFilePath, 'a')

    """
    ExportCryptoBackup
    Exports backup information pertaining to the cryptocurrency such as active buy orders,
    the reference price and the price since the last transaction
    @param cryptoID: The cryptoID of the cryptocurrency to write a backup on
    """
    def ExportCryptoBackup(self, cryptoID):
        backupFile = open(self.__cryptoBackupFolderPath + "/" + cryptoID + ".txt", "w")
        activeBuyOrders = self.__cryptoAccountTrackers[cryptoID].GetActivePurchases()
        for activeBuyOrder in activeBuyOrders:
            backupFile.write(str(activeBuyOrder[0]) + ", ")
            backupFile.write(str(activeBuyOrder[1]) + ", ")
            backupFile.write(str(activeBuyOrder[2]) + ", ")
            backupFile.write(str(int(activeBuyOrder[3])) + "\n")
        backupFile.write("Reference Price: " + str(self.__cryptoAccountTrackers[cryptoID].GetReferencePrice()) + "\n")
        backupFile.write("Last Transaction Price: " +
                         str(self.__cryptoAccountTrackers[cryptoID].GetPriceSinceLastTransaction()) + "\n")
        backupFile.close()

    """
    CleanUp
    A destructor function for the MasterBot class
    """
    def CleanUp(self):
        self.__recordingLogFile.close()
        self.__exceptionsLogFile.close()
