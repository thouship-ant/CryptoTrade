from binance.client import Client


if __name__ == "__main__":
    client = Client('2kpADsGOh27Io3V7gfh5lSvbcdl3PFiWMj43oh9jHJtADawZNB2BitiAuOohwg7k', 'yYd7WPULyK0rN0Va9j0mgl2sKv8jPFp5JeIbAZRGWayMaVIA0JplUBl6uRajjG2U')
#    info = client.get_account()
#    bal = info['balances']
#    for b in bal:
#        if float(b['free']) > 0 or float(b['locked']) > 0:
#            print('asset: {} :: free: {} :: locked: {}'.format(b['asset'], b['free'], b['locked']))
    symbol = 'RNDRUSDT'
    buy_order = client.get_order(symbol=symbol.replace('USDT', 'BUSD'))
    print(buy_order)
