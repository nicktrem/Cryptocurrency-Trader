# CBP API trader v1.4
import cbpro
import time
import os
import MasterBot
import AuthenticationConstants
import CryptoAccount
from CryptoStates import CryptoCurrencyPercentageStates
import TransactionConstants
import sys

if __name__ == "__main__":
    masterBot = MasterBot.MasterBot(accountKey=AuthenticationConstants.KEY,
        accountB64secret=AuthenticationConstants.B64SECRET,
        accountPassphrase=AuthenticationConstants.PASS_PHRASE,
        usdAccountID=AuthenticationConstants.USD_ACCOUNT_ID,
        operatingPath=".",
        recordingLogFilename="record.txt",
        exceptionsLogFilename="exceptions.txt",
        transactionsLogFoldername="transactions",
        cryptoBackupFoldername="crypto_records_backup",
        cryptoSettingsFolderName="crypto_settings")

    activeCryptoIDs = masterBot.GetCryptoIDs()
    UpdateRecordingFile = True
    counter = 0
    # Before main loop evaluate and query all of the crypto accounts
    # this is to get their price and calculate their total portfolio percentages
    # before the main loop begins
    for cryptoID in activeCryptoIDs:
        masterBot.UpdateUSDAccountAndAccountHoldings()
        masterBot.UpdateCryptoAccount(cryptoID)

    masterBot.UpdateTotalHoldingsInUSDFromAllAccounts()
    masterBot.UpdatePortfolioPercentagesOfAllAccounts()

    while True:
        for cryptoID in activeCryptoIDs:
            masterBot.UpdateUSDAccountAndAccountHoldings()
            masterBot.UpdateCryptoAccount(cryptoID)
            masterBot.UpdateTotalHoldingsInUSDFromAllAccounts()
            masterBot.UpdatePortfolioPercentagesOfAllAccounts()

            if masterBot.ShouldRenewPriceForCryptoAccount(cryptoID):
                masterBot.RenewPricesForCryptoAccount(cryptoID)
                masterBot.SetRenewPriceFlagForCryptoAccount(cryptoID, False)

            # Do some evaluation before determining buying or selling
            masterBot.RunPercentageCalculationOfCryptoAccount(cryptoID)
            masterBot.EvaluateAndAdjustBuyOrders(cryptoID)

            if masterBot.IsCryptoDown(cryptoID):
                if masterBot.ShouldBuy(cryptoID):
                    amountToBuyInUSD = masterBot.GetAmountToBuyInUSD(cryptoID)
                    amountToBuyInCoin = masterBot.GetAmountToBuyInCoin(cryptoID, amountToBuyInUSD)
                    if amountToBuyInCoin != 0.0:
                        masterBot.BuyIn(cryptoID, amountToBuyInCoin)
                        masterBot.WriteBuyTransactionToLogFile(cryptoID, amountToBuyInCoin)
                    masterBot.SetRenewPriceFlagForCryptoAccount(cryptoID, True)
                    UpdateRecordingFile = True

                elif masterBot.ShouldAdjustFallingReferencePrice(cryptoID):
                    masterBot.AdjustFallingReferencePrice(cryptoID)

            # If crypto is up check if we should readjust the price
            if masterBot.IsCryptoUp(cryptoID):
                if masterBot.ShouldAdjustIncreasingReferencePrice(cryptoID):
                    masterBot.AdjustIncreasingReferencePrice(cryptoID)
                elif masterBot.IsGoingBackDown(cryptoID):
                    masterBot.SetCryptoNeutral(cryptoID)

            # Check the active buy orders and see if we should sell
            if masterBot.ShouldSell(cryptoID):
                ordersToSell = masterBot.GetOrdersToSell(cryptoID)
                masterBot.SellOut(cryptoID, ordersToSell)
                for orderToSell in ordersToSell:
                    amountToSellInCoin = orderToSell[0]
                    masterBot.WriteSellTransactionToLogFile(cryptoID, amountToSellInCoin)
                masterBot.SetRenewPriceFlagForCryptoAccount(cryptoID, True)
                UpdateRecordingFile = True

            masterBot.ExportCryptoBackup(cryptoID)

        # if it is time to log...
        if counter >= 100 or UpdateRecordingFile:
            # Update everything before we log
            masterBot.UpdateUSDAccountAndAccountHoldings()
            for cryptoID in activeCryptoIDs:
                masterBot.UpdateCryptoAccount(cryptoID)
            masterBot.UpdateTotalHoldingsInUSDFromAllAccounts()
            masterBot.UpdatePortfolioPercentagesOfAllAccounts()

            masterBot.LogCryptoDataToRecordingFile()
            UpdateRecordingFile = False
            counter = 0
        else:
            counter = counter + 1

        time.sleep(1)
