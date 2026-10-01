import websocket, json
#import _thread, time
#import rel


def on_message(ws, message):
    print(message)


def on_close(ws):
    print("### closed ###")


if __name__ == "__main__":
    symbolname = 'BTCUSDT'
    interval = '1m'
    socket = f'wss://stream.binance.com:443/ws/{symbolname}@kline_{interval}'

    #websocket.enableTrace(True)
    ws = websocket.WebSocketApp(socket,
                                on_message=on_message,
                                on_close=on_close)

    ws.run_forever()  #dispatcher=rel,
                   #reconnect=5 Set dispatcher to automatic reconnection, 5 second reconnect delay if connection closed unexpectedly
    #rel.signal(2, rel.abort)  # Keyboard Interrupt
    #rel.dispatch()