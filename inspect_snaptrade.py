import snaptrade_client
print(dir(snaptrade_client))
try:
    from snaptrade_client import SnapTradeClient
    print("SnapTradeClient found")
except ImportError:
    print("SnapTradeClient NOT found")
