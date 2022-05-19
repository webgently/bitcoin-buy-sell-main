import sys, json, requests, asyncio
#import websockets
from PyQt5.QtWidgets import *
from PyQt5 import uic, QtCore
import time
from websockets import connect
import threading
from secret import *

instrument = "BTC-PERPETUAL"
access_key = ""
socket_server = 'wss://test.deribit.com/ws/api/v2'

from_class = uic.loadUiType("screen.ui")[0]

msg_auth = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "public/auth",
    "params": {
        "grant_type": "client_credentials",
        "client_id": access_key,
        "client_secret": secret_key
    }
}

msg_public_subscribe = {
    "method": "public/subscribe",
    "params": {
        "channels": [
            "ticker.BTC-PERPETUAL.100ms"
        ]
    },
    "jsonrpc": "2.0",
    "id": 2
}

msg_private_subscribe = {
    "method": "private/subscribe",
    "params": {
        "access_token": "",
        "channels": [
            "user.orders.BTC-PERPETUAL.raw"
        ]
    },
    "jsonrpc": "2.0",
    "id": 5
}


class EchoWebsocket:
    async def __aenter__(self):
        self._conn = connect('wss://test.deribit.com/ws/api/v2')
        self.websocket = await self._conn.__aenter__()
        return self

    async def __aexit__(self, *args, **kwargs):
        await self._conn.__aexit__(*args, **kwargs)

    async def send(self, message):
        await self.websocket.send(message)

    async def receive(self):
        return await self.websocket.recv()

    async def open(self):
        return self.websocket.open()


class MyWindow(QMainWindow, from_class):
    def __init__(self):
        super().__init__()
        self.setFocus()
        app.focusChanged.connect(self.on_focusChanged)
        self.setupUi(self)
        #Always keeps windows on top of others
        #self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        #self.setWindowState()
        self.activateWindow()

        self.access_token = ""
        self.error_msg = ""
        self.last_price = 0
        self.api_counter = 0
        self.lcd_number = 0
        self.order_state = None
        self.order_id = None
        self.socket_status = True
        self.hotkey_status = True
        self.ontop_status = False
        self.filled_amount = None

        self.ws_pub = EchoWebsocket()
        self.ws_pri = EchoWebsocket()
        self.loop_pub = asyncio.new_event_loop()
        self.loop_pri = asyncio.new_event_loop()

        self.WebsocketFlag.stateChanged.connect(self.socket_toggle)
        self.HotkeyFlag.stateChanged.connect(self.hotkey_toggle)
        self.OntopFlag.stateChanged.connect(self.ontop_toggle)

        self.socketConnect()

        self.thrPubSubscribe = threading.Thread(target=self.thread_pubsubscribe, name='public_subscription')
        self.thrPubSubscribe.start()

        self.thrPriSubscribe = threading.Thread(target=self.thread_prisubscribe, name='private_subscription')
        self.thrPriSubscribe.start()

        self.timerF9 = None
        self.timerF10 = None
        self.timerF11 = None
        self.timerF12 = None

        self.b1 = QPushButton("Lux")


    def on_focusChanged(self):
        isInFocus = str(self.isActiveWindow())


        if isInFocus == "True":
            self.inFocus.setStyleSheet('color:blue')
        if isInFocus == "False":
            self.inFocus.setStyleSheet('color:red')
            #time.sleep(2)
            #print("Hiii")
            #self.activateWindow()
            #self.emit(SIGNAL("doSomePrinting()"))
            #self.emit(print("ddd"))

        return self.inFocus.setText(isInFocus)

    def bfunc(self):
        print("Hello World!")

    def keyPressEvent(self, event):
        selKey = event.key()
        if self.socket_status and self.hotkey_status:
            if selKey == QtCore.Qt.Key_F12:
                self.timerF12 = threading.Thread(target=self.f12_pressed, name='F12')
                self.timerF12.start()
            elif selKey == QtCore.Qt.Key_F11:
                self.timerF11 = threading.Thread(target=self.f11_pressed, name='F11')
                self.timerF11.start()
            elif selKey == QtCore.Qt.Key_F10:
                self.timerF10 = threading.Thread(target=self.f10_pressed, name='F10')
                self.timerF10.start()
            elif selKey == QtCore.Qt.Key_F9:
                self.timerF9 = threading.Thread(target=self.f9_pressed, name='F9')
                self.timerF9.start()
            elif selKey == QtCore.Qt.Key_Escape:
                self.esc_press()
            self.Errors.setText(self.error_msg)

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Window Close', 'Are you sure you want to close the window?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.loop_pub.stop()
            self.loop_pri.stop()
            event.accept()
            print('Window closed')
        else:
            event.ignore()

    def socketConnect(self):
        response = requests.get(
            api_server + "public/auth?grant_type=client_credentials&client_id=" + access_key + "&client_secret=" + secret_key)
        response = response.json()
        try:
            self.access_token = response["result"]["access_token"]
            msg_private_subscribe['params']['access_token'] = self.access_token
            print(self.access_token)
        except KeyError:
            print('Oops')

    def thread_pubsubscribe(self):
        self.loop_pub.run_until_complete(self.pubsubscribe())
        self.loop_pub.run_forever()

    def thread_prisubscribe(self):
        self.loop_pri.run_until_complete(self.prisubscribe())
        self.loop_pri.run_forever()

    async def pubsubscribe(self):

        async with self.ws_pub as websocket:
            await websocket.send(json.dumps(msg_public_subscribe))
            while websocket.open:
                response = json.loads(await websocket.receive())
                # print(response)
                if "params" in response:
                    self.last_price = response['params']['data']['last_price']
                    self.mPriceValue.setText(str(self.last_price))




    async def prisubscribe(self):
        async with self.ws_pri as websocket:
            await websocket.send(json.dumps(msg_private_subscribe))
            while websocket.open:
                response = json.loads(await websocket.receive())
                # print(response)
                if "params" in response:
                    self.order_state = response['params']['data']['order_state']
                    self.mOrderState.setText(str(self.order_state))

    def call_api(self, url, api_data={}, is_post=False):
        print(url)
        headers = {'Authorization': 'Bearer ' + self.access_token}
        if is_post:
            resp = requests.post(url, api_data)
        else:
            resp = requests.get(api_server + url, headers=headers)

        return resp.json()

    def f12_pressed(self):
        self.error_msg = "F12 pressed\n"
        self.socketConnect()
        quantity = self.Quantity.text()

        milli_sec1 = int(round(time.time() * 1000))

        self.api_counter = 0

        # /private/buy
        resp = self.call_api("private/buy?amount=" + quantity + "&instrument_name=" + instrument + "&type=market")
        if 'error' in resp:
            self.add_error("private/buy: ", resp['error'])

        # /private/sell
        stop_thrs = float(self.StopThrs.text())
        print("here fetched last price: " + str(self.last_price))
        lastPrice = int(self.last_price - stop_thrs)
        print("here before /private/sell: " + str(lastPrice))
        resp = self.call_api(
            "private/sell?amount=" + quantity + "&instrument_name=" + instrument + "&type=stop_market&trigger=last_price&stop_price=" + str(
                lastPrice))
        print(resp)
        if 'error' in resp:
            self.add_error("private/sell: ", resp['error'])
        else:
            order_id = resp['result']['order']['order_id']
            if self.ItrsFlag.isChecked():
                stop_itrs = self.StopItrs.text()
                loop_cnt = int(stop_itrs) if len(stop_itrs) > 0 else 0
                for i in range(loop_cnt):
                    ii = i + 1
                    lastPrice = int(lastPrice + stop_thrs)
                    print("itr#" + str(ii) + " stop_price: " + str(lastPrice))
                    while True:

                        print(float(self.doubleSpinBox.text().replace(",", ".", 1)))

                        time.sleep(float(self.doubleSpinBox.text().replace(",", ".", 1)))
                        self.api_counter += 1
                        self.mApiCounter.setText(str(self.api_counter))

                        milli_sec2 = int(round(time.time() * 1000))

                        self.lcd_number = milli_sec2 - milli_sec1
                        self.lcdNumber.display(int(self.lcd_number))

                        resp = self.call_api(
                            "private/edit?amount=" + quantity + "&order_id=" + order_id + "&stop_price=" + str(
                                lastPrice))
                        if 'error' not in resp and resp['result']['order']['triggered'] == False:
                            print(resp)
                            print('edit successful')
                            break
                        elif 'error' in resp and resp['error']['message'] == "order_not_found":
                            print('triggered')
                            return
                        if 'error' in resp:
                            continue

    def f9_pressed(self):
        self.error_msg = "F9 pressed\n"
        self.socketConnect()
        quantity = self.Quantity.text()

        # /private/sell
        resp = self.call_api("private/sell?amount=" + quantity + "&instrument_name=" + instrument + "&type=market")
        if 'error' in resp:
            self.add_error("private/sell: ", resp['error'])

        # /private/buy
        stop_thrs = float(self.StopThrs.text())
        print("here fetched last price: " + str(self.last_price))
        lastPrice = int(self.last_price + stop_thrs)
        print("here before /private/buy: " + str(lastPrice))
        resp = self.call_api(
            "private/buy?amount=" + quantity + "&instrument_name=" + instrument + "&type=stop_market&trigger=last_price&stop_price=" + str(
                lastPrice))
        if 'error' in resp:
            self.add_error("private/buy: ", resp['error'])
        else:
            order_id = resp['result']['order']['order_id']
            if self.ItrsFlag.isChecked():
                stop_itrs = self.StopItrs.text()
                loop_cnt = int(stop_itrs) if len(stop_itrs) > 0 else 0
                for i in range(loop_cnt):
                    ii = i + 1
                    lastPrice = int(lastPrice - stop_thrs)
                    print("itr#" + str(ii) + " stop_price: " + str(lastPrice))
                    while True:
                        resp = self.call_api(
                            "private/edit?amount=" + quantity + "&order_id=" + order_id + "&stop_price=" + str(
                                lastPrice))
                        print(resp)
                        if 'error' not in resp and resp['result']['order']['triggered'] == True:
                            break
                        if 'error' in resp and resp['error']['message'] == "order_not_found":
                            break

    def esc_press(self):
        self.error_msg = "Esc pressed\n"
        self.socketConnect()

        resp = self.call_api("private/cancel_all_by_instrument?instrument_name=" + instrument + "&type=all")
        if 'error' in resp:
            self.add_error("private/cancel_all_by_instrument: ", resp['error'])

        resp = self.call_api("private/close_position?instrument_name=" + instrument + "&type=market")
        if 'error' in resp:
            self.add_error("private/close_position: ", resp['error'])

    def f11_pressed(self):
        self.error_msg = "F11 pressed\n"
        self.socketConnect()

        resp = self.call_api('private/get_position?instrument_name=' + instrument)
        if 'error' in resp:
            self.add_error("private/get_position: ", resp['error'])
        else:
            sizeData = abs(int(resp['result']['size']))
            lastPrice = self.last_price
            resp = self.call_api('private/sell?amount=' + str(
                sizeData) + '&instrument_name=' + instrument + '&post_only=true&time_in_force=good_til_cancelled&type=limit&price=' + str(
                lastPrice))
            if 'error' in resp:
                self.add_error("private/sell: ", resp['error'])
            else:
                order_id = resp['result']['order']['order_id']
                while True:
                    if self.order_state == "filled":
                        break

                    cur_price = self.last_price

                    resultData = resp['result']['params']['data']
                    filled_amount = resultData['filled_amount']
                    will_update = False
                    if filled_amount > 0:
                        will_update = True
                        sizeData = sizeData - filled_amount

                    if cur_price < lastPrice:
                        will_update = True
                        lastPrice = cur_price

                    if will_update:
                        resp = self.call_api(
                                "private/edit?amount=" + str(sizeData) + "&order_id=" + order_id + "&price=" + str(
                                lastPrice))
                        if 'error' in resp:
                            self.add_error("private/edit: ", resp['error'])
                            break

    def f10_pressed(self):
        self.error_msg = "F10 pressed\n"
        self.socketConnect()

        resp = self.call_api('private/get_position?instrument_name=' + instrument)
        if 'error' in resp:
            self.add_error("private/get_position: ", resp['error'])
        else:
            sizeData = abs(int(resp['result']['size']))
            lastPrice = self.last_price
            i = 0
            order_id = 0
            while True:
                if i == 0:
                    i = 1
                    funcErr = False
                    resp = self.call_api('private/buy?amount=' + str(
                        sizeData) + '&instrument_name=' + instrument +
                        '&post_only=true&time_in_force=good_til_cancelled&type=limit&price=' + str(lastPrice))
                    if 'error' in resp:
                        self.add_error("private/buy: ", resp['error'])
                        funcErr = True
                    else:
                        order_id = resp['result']['order']['order_id']

                    if funcErr:
                        break

                if self.order_state == "filled":
                    break

                cur_price = self.last_price

                resultData = resp['result']['params']['data']
                filled_amount = resultData['filled_amount']

                will_update = False
                if filled_amount > 0:
                    will_update = True
                    sizeData = sizeData - filled_amount

                if cur_price < lastPrice:
                    will_update = True
                    lastPrice = cur_price

                if will_update:
                    resp = self.call_api(
                        "private/edit?amount=" + str(sizeData) + "&order_id=" + order_id + "&price=" + str(
                            lastPrice))
                    if 'error' in resp:
                        self.add_error("private/edit: ", resp['error'])
                        break

                break

    def socket_toggle(self):
        self.error_msg = "Socket toggle\n"
        self.socket_status = self.WebsocketFlag.isChecked()
        self.Errors.setText(self.error_msg)

    def hotkey_toggle(self):
        self.error_msg = "Hotkey toggle\n"
        self.hotkey_status = self.HotkeyFlag.isChecked()
        self.Errors.setText(self.error_msg)

    def ontop_toggle(self):
        self.error_msg = "Always-on-top toggle\n"
        self.ontop_status = self.OntopFlag.isChecked()
        if self.ontop_status:
            self.setWindowFlags(window.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(window.windowFlags() & ~QtCore.Qt.WindowStaysOnTopHint)
        self.show()
        self.Errors.setText(self.error_msg)

    def add_error(self, prefix_str, resp):
        errMsg = resp['data']['reason'] if 'data' in resp else resp['message']
        self.error_msg += "\n" + prefix_str + errMsg

if __name__=="__main__":
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    #app.connect(window, SIGNAL("doSomePrinting()"), window.bfunc)
    sys.exit(app.exec_())

Q