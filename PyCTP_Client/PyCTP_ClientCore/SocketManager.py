# -*- coding: utf-8 -*-

import os
from collections import namedtuple
import socket
import sys
import struct
import threading
import json
import queue
from QCTP import QCTP
from QAccountWidget import QAccountWidget
import time
from PyQt4 import QtCore
from QMessageBox import QMessageBox
from multiprocessing import Process, Manager, Value, Array, Queue, Pipe
from User import User

Message = namedtuple("Message", "head checknum buff")


# 创建user(期货账户)
def static_create_user_process(dict_user_info):
    # print("static_create_user_process() dict_user_info =", dict_user_info)
    # print("static_create_user_process() user_id =", dict_user_info['userid'], ", process_id =", os.getpid(), ", dict_user_info =", dict_user_info)
    # ClientMain.socket_manager.signal_label_login_error_text.emit('创建User', dict_user_info['server']['user_info']['userid'])
    obj_user = User(dict_user_info)
    # print("static_create_user_process() obj_user.get_user_id() =", obj_user.get_user_id())
    while True:
        pass
        # print("static_create_user_process() while True time.sleep(2.0) ")
        time.sleep(1.0)


class SocketManager(QtCore.QThread):

    signal_label_login_error_text = QtCore.pyqtSignal(str)  # 定义信号：设置登录界面的消息框文本
    signal_pushButton_login_set_enabled = QtCore.pyqtSignal(bool)  # 定义信号：登录界面登录按钮设置为可用
    signal_ctp_manager_init = QtCore.pyqtSignal()  # 定义信号：调用CTPManager的初始化方法
    signal_update_strategy = QtCore.pyqtSignal()  # 定义信号：收到服务端收到策略类的回报消息
    signal_restore_groupBox = QtCore.pyqtSignal()  # 定义信号：收到查询策略信息后出发信号 -> groupBox界面状态还原（激活查询按钮、恢复“设置持仓”按钮）
    signal_q_ctp_show = QtCore.pyqtSignal()  # 定义信号：收到查询策略信息后出发信号 -> groupBox界面状态还原（激活查询按钮、恢复“设置持仓”按钮）

    def __init__(self, ip_address, port, parent=None):
        # threading.Thread.__init__(self)
        super(SocketManager, self).__init__(parent)
        self.__ip_address = ip_address
        self.__port = port
        self.__sockfd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__event = threading.Event()  # 初始化协程threading.Event()
        self.__msg_ref = 0  # 发送消息引用
        self.__RecvN = True  # RecvN方法运行状态，True正常，False异常
        self.__queue_send_msg = queue.Queue(maxsize=100)  # 创建队列，存储将要发送的消息
        self.__thread_send_msg = threading.Thread(target=self.run_send_msg)  # 创建发送消息线程
        self.__thread_send_msg.start()

    def set_XML_Manager(self, obj):
        self.__xml_manager = obj

    def get_XML_Manager(self):
        return self.__xml_manager

    # 程序主窗口
    def set_QCTP(self, obj_QCTP):
        self.__q_ctp = obj_QCTP

    def get_QCTP(self):
        return self.__q_ctp

    def set_QLogin(self, obj_QLogin):
        self.__q_login = obj_QLogin

    def get_QLogin(self):
        return self.__q_login

    def set_QAccountWidget(self, obj_QAccountWidget):
        self.__QAccountWidget = obj_QAccountWidget

    def get_QAccountWidget(self):
        return self.__QAccountWidget

    def set_QOrderWidget(self, obj_QOrderWidget):
        self.__QOrderWidget = obj_QOrderWidget

    def get_QOrderWidget(self):
        return self.__QOrderWidget

    def get_sockfd(self):
        return self.__sockfd

    def get_msg_ref(self):
        return self.__msg_ref

    def msg_ref_add(self):
        self.__msg_ref += 1
        return self.__msg_ref

    def set_CTPManager(self, obj_CTPManager):
        self.__ctp_manager = obj_CTPManager

    def get_CTPManager(self):
        return self.__ctp_manager
    
    def set_ClientMain(self, obj_ClientMain):
        self.__client_main = obj_ClientMain
        
    def get_QClientMain(self):
        return self.__client_main

    # 设置交易员id
    def set_trader_id(self, str_TraderID):
        self.__trader_id = str_TraderID

    def set_trader_on_off(self, int_on_off):
        self.__trader_on_off = int_on_off

    def get_trader_on_off(self):
        return self.__trader_on_off

    # 获得交易员id
    def get_trader_id(self):
        return self.__trader_id

    def set_trader_name(self, str_TraderName):
        self.__trader_name = str_TraderName

    def get_trader_name(self):
        return self.__trader_name

    def set_list_market_info(self, list_input):
        self.__list_market_info = list_input

    def get_list_market_info(self):
        return self.__list_market_info

    def set_list_user_info(self, list_input):
        self.__list_user_info = list_input

    def get_list_user_info(self):
        return self.__list_user_info

    def set_list_algorithm_info(self, list_input):
        self.__list_algorithm_info = list_input

    def get_list_algorithm_info(self):
        return self.__list_algorithm_info

    def set_list_strategy_info(self, list_input):
        self.__list_strategy_info = list_input
        
    def get_list_strategy_info(self):
        return self.__list_strategy_info

    def set_list_position_detail_for_order(self, list_input):
        self.__list_position_detail_for_order = list_input

    def get_list_position_detail_for_order(self):
        return self.__list_position_detail_for_order

    def set_list_position_detail_for_trade(self, list_input):
        self.__list_position_detail_for_trade = list_input

    def get_list_position_detail_for_trade(self):
        return self.__list_position_detail_for_trade

    # 连接服务器
    def connect(self):
        # 创建socket套接字
        if self.__sockfd:
            # 连接服务器: IP,port
            try:
                # 进行与服务端的连接(ip地址根据实际情况进行更改)
                self.__sockfd.connect((self.__ip_address, self.__port))
            except socket.error as e:
                print("SocketManager.connect() socket error", e)
                QMessageBox().showMessage("错误", "连接服务器失败！")
                sys.exit(1)

    # ------------------------------------------------------
    # RecvN
    #     recv N bytes to target
    # ------------------------------------------------------
    def RecvN(self, socketd, n):
        totalContent = b''
        totalRecved = 0
        while totalRecved < n:
            try:
                onceContent = socketd.recv(n - totalRecved)
                # self.__RecvN = True
            except socket.error as e:
                self.__RecvN = False
                print("SocketManager.RecvN()", e, n, totalRecved)
                QMessageBox().showMessage("错误", "与服务器断开连接！")
                return None
            # print("onceContent", onceContent)
            totalContent += onceContent
            totalRecved = len(totalContent)

        return totalContent

    # 计算校验码
    def msg_check(self, message):
        # 将收到的head以及buff分别累加 % 255
        checknum = 0
        for i in message.head:
            checknum = ((checknum + ord(i)) % 255)
        return checknum

    # 向socket服务端发送数据
    @QtCore.pyqtSlot(str)
    def send_msg_to_server(self, buff):  # sockfd为socket套接字，buff为消息体json数据
        # 构造Message
        m = Message("gmqh_sh_2016", 0, buff)

        # 数据发送前,将校验数据填入Message结构体
        checknum = self.msg_check(m)
        m = Message("gmqh_sh_2016", checknum, buff)
        # print("send m.buff = ", m.buff.encode())
        # print("send m.checknum = ", m.checknum)
        # 打包数据(13位的head,1位校验码,不定长数据段)
        data = struct.pack(">13s1B" + str(len(m.buff.encode()) + 1) + "s", m.head.encode(), m.checknum, m.buff.encode())

        print("SocketManager.slot_send_msg()", data)
        try:
            size = self.__sockfd.send(data)  # 发送数据
        except socket.timeout as e:
            print("SocketManager.slot_send_msg()", e)
        self.__event.clear()
        return size if self.__event.wait(2.0) else -1

    # 将发送消息加入队列
    @QtCore.pyqtSlot(str)
    def slot_send_msg(self, buff):
        # thread = threading.current_thread()
        # print(">>> SocketManager.run() thread.getName()=", thread.getName())
        self.__queue_send_msg.put(buff)

    # 接收消息线程
    def run(self):
        # thread = threading.current_thread()
        # print(">>> SocketManager.run() thread.getName()=", thread.getName())
        while True:
            # 收消息
            if self.__RecvN:  # RecvN状态正常
                try:
                    # 接收数据1038个字节(与服务器端统一:13位head+1位checknum+1024数据段)
                    # data = self.__sockfd.recv(30 * 1024 + 14)
                    data = self.RecvN(self.__sockfd, 30 * 1024 + 14)
                except socket.error as e:
                    print(e)

                # 解包数据
                if data is not None:
                    # return
                    head, checknum, buff = struct.unpack(">13s1B" + str(len(data) - 14) + "s", data)
                    # print(head, checknum, buff, '\n')
                    # 将解包的数据封装为Message结构体
                    m = Message(head.decode().split('\x00')[0], checknum, buff.decode())
                    tmp_checknum = self.msg_check(m)
                    m = Message(head.decode().split('\x00')[0], tmp_checknum, buff.decode().split('\x00')[0])

                    # 将收到的标志位与收到数据重新计算的标志位进行对比+head内容对比
                    if (m.checknum == checknum) and (m.head == "gmqh_sh_2016"):
                        # 打印接收到的数据
                        dict_buff = eval(m.buff)  # str to dict
                        self.receive_msg(dict_buff)
                        if dict_buff['MsgRef'] == self.__msg_ref:  # 收到服务端发送的收到消息回报
                            self.__event.set()
                    else:
                        print("SocketManager.run() 接收到的数据有误", m.buff)
                        continue

    # 发送消息线程
    def run_send_msg(self):
        thread = threading.current_thread()
        print(">>> SocketManager.run_send_msg() thread.getName()=", thread.getName())
        # 发消息
        while True:
            if self.__queue_send_msg.qsize() > 0:
                tmp_msg = self.__queue_send_msg.get()
                if tmp_msg is not None:
                    self.send_msg_to_server(tmp_msg)

    # 处理收到的消息
    def receive_msg(self, buff):
        # 消息源MsgSrc值：0客户端、1服务端
        if buff['MsgSrc'] == 0:  # 由客户端发起的消息类型
            # 内核初始化未完成
            # if self.__ctp_manager.get_init_finished() is False:
            if buff['MsgType'] == 1:  # 收到：交易员登录验证，MsgType=1
                print("SocketManager.receive_msg() MsgType=1，交易员登录", buff)
                if buff['MsgResult'] == 0:  # 验证通过
                    self.signal_label_login_error_text.emit('登陆成功')
                    self.set_trader_name(buff['TraderName'])
                    self.set_trader_id(buff['TraderID'])
                    self.set_trader_on_off(buff['OnOff'])
                    # self.__client_main.set_trader_name(buff['TraderName'])
                    # self.__client_main.set_trader_id(buff['TraderID'])
                    # self.__ctp_manager.set_trader_name(buff['TraderName'])
                    # self.__ctp_manager.set_trader_id(buff['TraderID'])
                    # self.__ctp_manager.set_on_off(buff['OnOff'])
                    self.qry_market_info()  # 发送：查询行情配置，MsgType=4
                elif buff['MsgResult'] == 1:  # 验证不通过
                    self.signal_label_login_error_text.emit(buff['MsgErrorReason'])
                    self.signal_pushButton_login_set_enabled.emit(True)  # 登录按钮激活
            elif buff['MsgType'] == 4:  # 收到：查询行情配置，MsgType=4
                print("SocketManager.receive_msg() MsgType=4，查询行情配置", buff)
                if buff['MsgResult'] == 0:  # 消息结果成功
                    # self.__ctp_manager.set_list_market_info(buff['Info'])  # 将行情信息设置为ctp_manager的属性
                    self.set_list_market_info(buff['Info'])
                    self.qry_user_info()  # 发送：查询期货账户信息，MsgType=2
                elif buff['MsgResult'] == 1:  # 消息结果失败
                    self.signal_label_login_error_text.emit(buff['MsgErrorReason'])
                    self.signal_pushButton_login_set_enabled.emit(True)  # 登录按钮激活
            elif buff['MsgType'] == 2:  # 收到：查询期货账户信息，MsgType=2
                print("SocketManager.receive_msg() MsgType=2，查询期货账户", buff)
                if buff['MsgResult'] == 0:  # 消息结果成功
                    # self.__ctp_manager.set_list_user_info(buff['Info'])  # 将期货账户信息设置为ctp_manager的属性
                    self.set_list_user_info(buff['Info'])
                    self.qry_algorithm_info()  # 发送：查询下单算法，MsgType=11
                elif buff['MsgResult'] == 1:  # 消息结果失败
                    self.signal_label_login_error_text.emit(buff['MsgErrorReason'])
                    self.signal_pushButton_login_set_enabled.emit(True)  # 登录按钮激活
            elif buff['MsgType'] == 11:  # 收到：查询下单算法编号，MsgType=11
                print("SocketManager.receive_msg() MsgType=11，查询下单算法", buff)
                if buff['MsgResult'] == 0:  # 消息结果成功
                    self.set_list_algorithm_info(buff['Info'])
                    self.qry_strategy_info()  # 发送：查询策略信息，MsgType=3
                elif buff['MsgResult'] == 1:  # 消息结果失败
                    self.signal_label_login_error_text.emit(buff['MsgErrorReason'])
                    self.signal_pushButton_login_set_enabled.emit(True)  # 登录按钮激活
            elif buff['MsgType'] == 3:  # 收到：查询策略，MsgType=3
                print("SocketManager.receive_msg() MsgType=3，查询策略", buff)
                if buff['MsgResult'] == 0:  # 消息结果成功
                    self.set_list_strategy_info(buff['Info'])
                    self.qry_position_detial_for_order()  # 发送：查询持仓明细order，MsgType=15
                elif buff['MsgResult'] == 1:  # 消息结果失败
                    self.signal_label_login_error_text.emit(buff['MsgErrorReason'])
                    self.signal_pushButton_login_set_enabled.emit(True)  # 登录按钮激活
            elif buff['MsgType'] == 15:  # 收到：查询持仓明细order，MsgType=15
                print("SocketManager.receive_msg() MsgType=15，查询持仓明细order", buff)
                if buff['MsgResult'] == 0:  # 消息结果成功
                    self.set_list_position_detail_for_order(buff['Info'])
                    self.qry_position_detial_for_trade()  # 发送：查询持仓明细trade，MsgType=17
                elif buff['MsgResult'] == 1:  # 消息结果失败
                    self.signal_label_login_error_text.emit(buff['MsgErrorReason'])
                    self.signal_pushButton_login_set_enabled.emit(True)  # 登录按钮激活
            elif buff['MsgType'] == 17:  # 收到：查询持仓明细，MsgType=17
                print("SocketManager.receive_msg() MsgType=17，查询持仓明细trade", buff)
                if buff['MsgResult'] == 0:  # 消息结果成功
                    self.set_list_position_detail_for_trade(buff['Info'])
                    # self.signal_ctp_manager_init.emit()  # 与服务端初始化通信结束，调用CTPManager的初始化方法
                    # 开始创建user进程
                    self.create_user()
                    #
                elif buff['MsgResult'] == 1:  # 消息结果失败
                    self.signal_label_login_error_text.emit(buff['MsgErrorReason'])
                    self.signal_pushButton_login_set_enabled.emit(True)  # 登录按钮激活
            # 内核初始化完成
            # elif self.__ctp_manager.get_init_UI_finished():
                # if buff['MsgType'] == 3:  # 查询策略，MsgType=3
                #     print("SocketManager.receive_msg() MsgType=3，查询策略", buff)  # 输出错误消息
                #     if buff['MsgResult'] == 0:  # 消息结果成功
                #         self.__listStrategyInfoOnce = buff['Info']  # 转存策略信息到本类的属性里(单次查询)
                #         # 遍历查询到的消息结果列表
                #         for i_Info in self.__listStrategyInfoOnce:
                #             # 遍历策略对象列表，将服务器查询到的策略参数传递给策略，并调用set_arguments方法更新内核参数值
                #             for i_strategy in self.__ctp_manager.get_list_strategy():
                #                 if i_Info['user_id'] == i_strategy.get_user_id() and i_Info['strategy_id'] == i_strategy.get_strategy_id():
                #                     i_strategy.set_arguments(i_Info)  # 将查询参数结果设置到策略内核，所有的策略
                #                     break
                #         self.signal_restore_groupBox.emit()  # 收到消息后将按钮查询策略按钮、恢复设置持仓
                #     elif buff['MsgResult'] == 1:  # 消息结果失败
                #         print("SocketManager.receive_msg() MsgType=3 查询策略失败")
                # elif
            elif buff['MsgType'] == 6:  # 新建策略，MsgType=6
                print("SocketManager.receive_msg() MsgType=6，新建策略", buff)
                if buff['MsgResult'] == 0:  # 消息结果成功
                    # self.__ctp_manager.create_strategy(buff['Info'][0])  # 内核创建策略对象
                    self.create_strategy(buff['Info'][0])  # 与同进程的UI通信，UI
                elif buff['MsgResult'] == 1:  # 消息结果失败
                    print("SocketManager.receive_msg() ", buff['MsgErrorReason'])
                    QMessageBox().showMessage("错误", buff['MsgErrorReason'])
            elif buff['MsgType'] == 5:  # 修改策略参数，MsgType=5
                print("SocketManager.receive_msg() MsgType=5，修改策略参数", buff)
                if buff['MsgResult'] == 0:  # 消息结果成功
                    dict_args = buff['Info'][0]  # 策略参数dict
                    for i_strategy in self.__ctp_manager.get_list_strategy():
                        if i_strategy.get_user_id() == dict_args['user_id'] and i_strategy.get_strategy_id() == dict_args['strategy_id']:
                            i_strategy.set_arguments(dict_args)
                            break
                elif buff['MsgResult'] == 1:  # 消息结果失败
                    print("SocketManager.receive_msg() MsgType=5 修改策略参数失败")
            elif buff['MsgType'] == 12:  # 修改策略持仓，MsgType=12
                print("SocketManager.receive_msg() MsgType=12，修改策略持仓", buff)
                if buff['MsgResult'] == 0:  # 消息结果成功
                    # 更新内核中的策略持仓
                    for i_strategy in self.__ctp_manager.get_list_strategy():
                        if i_strategy.get_user_id() == buff['UserID'] \
                                and i_strategy.get_strategy_id() == buff['StrategyID']:
                            i_strategy.set_position(buff['Info'][0])
                            break
                elif buff['MsgResult'] == 1:  # 消息结果失败
                    print("SocketManager.receive_msg() MsgType=12 修改策略持仓失败")
            elif buff['MsgType'] == 7:  # 删除策略，MsgType=7
                print("SocketManager.receive_msg() MsgType=7，删除策略", buff)
                if buff['MsgResult'] == 0:  # 消息结果成功
                    dict_args = {'user_id': buff['UserID'], 'strategy_id': buff['StrategyID']}
                    self.__ctp_manager.delete_strategy(dict_args)
                elif buff['MsgResult'] == 1:  # 消息结果失败
                    print("SocketManager.receive_msg() MsgType=7 删除策略失败")
            elif buff['MsgType'] == 13:  # 修改策略交易开关
                print("SocketManager.receive_msg() MsgType=13，修改策略交易开关", buff)
                if buff['MsgResult'] == 0:  # 消息结果成功
                    for i_strategy in self.__ctp_manager.get_list_strategy():
                        if i_strategy.get_user_id() == buff['UserID'] \
                                and i_strategy.get_strategy_id() == buff['StrategyID']:
                            i_strategy.set_on_off(buff['OnOff'])  # 更新内核中策略开关
                            break
                elif buff['MsgResult'] == 1:  # 消息结果失败
                    print("SocketManager.receive_msg() MsgType=13 修改策略交易开关失败")
            elif buff['MsgType'] == 14:  # 修改策略只平开关
                print("SocketManager.receive_msg() MsgType=14，修改策略只平开关", buff)
                if buff['MsgResult'] == 0:  # 消息结果成功
                    for i_strategy in self.__ctp_manager.get_list_strategy():
                        if i_strategy.get_user_id() == buff['UserID'] \
                                and i_strategy.get_strategy_id() == buff['StrategyID']:
                            i_strategy.set_only_close(buff['OnOff'])  # 更新内核中策略只平开关
                            break
                elif buff['MsgResult'] == 1:  # 消息结果失败
                    print("SocketManager.receive_msg() MsgType=14 修改策略只平开关失败")
            elif buff['MsgType'] == 8:  # 修改交易员开关
                print("SocketManager.receive_msg() MsgType=8，修改交易员开关", buff)
                if buff['MsgResult'] == 0:  # 消息结果成功
                    self.__ctp_manager.set_on_off(buff['OnOff'])  # 设置内核中交易员开关
                elif buff['MsgResult'] == 1:  # 消息结果失败
                    print("SocketManager.receive_msg() MsgType=8 修改交易员开关失败")
            elif buff['MsgType'] == 9:  # 修改期货账户开关
                print("SocketManager.receive_msg() MsgType=9，修改期货账户开关", buff)
                if buff['MsgResult'] == 0:  # 消息结果成功
                    for i_user in self.__ctp_manager.get_list_user():
                        if i_user.get_user_id().decode() == buff['UserID']:
                            i_user.set_on_off(buff['OnOff'])  # 设置内核中期货账户开关
                            break
                elif buff['MsgResult'] == 1:  # 消息结果失败
                    print("SocketManager.receive_msg() MsgType=9 修改期货账户开关失败")
        elif buff['MsgSrc'] == 1:  # 由服务端发起的消息类型
            pass

    # 查询行情信息
    def qry_market_info(self):
        dict_qry_market_info = {'MsgRef': self.msg_ref_add(),
                                'MsgSendFlag': 0,  # 发送标志，客户端发出0，服务端发出1
                                'MsgSrc': 0,  # 消息源，客户端0，服务端1
                                'MsgType': 4,  # 查询行情信息
                                'TraderID': self.__trader_id
                                }
        json_qry_market_info = json.dumps(dict_qry_market_info)
        self.slot_send_msg(json_qry_market_info)
        self.signal_label_login_error_text.emit('查询行情信息')

    # 查询期货账户信息
    def qry_user_info(self):
        dict_qry_user_info = {'MsgRef': self.msg_ref_add(),
                              'MsgSendFlag': 0,  # 发送标志，客户端发出0，服务端发出1
                              'MsgSrc': 0,  # 消息源，客户端0，服务端1
                              'MsgType': 2,  # 查询期货账户
                              'TraderID': self.__trader_id,
                              'UserID': ''
                              }
        json_qry_user_info = json.dumps(dict_qry_user_info)
        self.slot_send_msg(json_qry_user_info)
        self.signal_label_login_error_text.emit('查询期货账户信息')

    # 查询期货账户会话ID
    def qry_sessions_info(self):
        dict_qry_sessions_info = {'MsgRef': self.msg_ref_add(),
                                  'MsgSendFlag': 0,  # 发送标志，客户端发出0，服务端发出1
                                  'MsgSrc': 0,  # 消息源，客户端0，服务端1
                                  'MsgType': 16,  # 查询sessions
                                  'TraderID': self.__trader_id,
                                  'UserID': ''
                                  }
        # {"MsgRef": 1, "MsgSendFlag": 0, "MsgSrc": 0, "MsgType": 16, "TraderID": "1601", "UserID": ""} UserID为空，返回TraderID所属的所有user的sessions
        json_qry_sessions_info = json.dumps(dict_qry_sessions_info)
        self.slot_send_msg(json_qry_sessions_info)
        self.signal_label_login_error_text.emit('查询sessions')

    # 查询下单算法
    def qry_algorithm_info(self):
        dict_qry_algorithm_info = {'MsgRef': self.msg_ref_add(),
                                   'MsgSendFlag': 0,  # 发送标志，客户端发出0，服务端发出1
                                   'MsgSrc': 0,  # 消息源，客户端0，服务端1
                                   'MsgType': 11,  # 查询期货账户
                                   'TraderID': self.__trader_id,
                                   }
        json_qry_algorithm_info = json.dumps(dict_qry_algorithm_info)
        self.slot_send_msg(json_qry_algorithm_info)
        self.signal_label_login_error_text.emit('查询下单算法')

    # 查询策略
    def qry_strategy_info(self):
        dict_qry_strategy_info = {'MsgRef': self.msg_ref_add(),
                                  'MsgSendFlag': 0,  # 发送标志，客户端发出0，服务端发出1
                                  'MsgSrc': 0,  # 消息源，客户端0，服务端1
                                  'MsgType': 3,  # 查询策略
                                  'TraderID': self.__trader_id,
                                  'UserID': '',
                                  'StrategyID': ''
                                  }
        json_qry_strategy_info = json.dumps(dict_qry_strategy_info)
        self.slot_send_msg(json_qry_strategy_info)
        self.signal_label_login_error_text.emit('查询策略')

    """
    # 查询策略昨仓
    def qry_yesterday_position(self):
        dict_qry_yesterday_position = {
            'MsgRef': self.msg_ref_add(),
            'MsgSendFlag': 0,  # 发送标志，客户端发出0，服务端发出1
            'MsgSrc': 0,  # 消息源，客户端0，服务端1
            'MsgType': 10,  # 查询策略昨仓
            'TraderID': self.__trader_id,
            'UserID': ""  # self.__user_id, 键值为空时查询所有UserID的策略
        }
        json_qry_yesterday_position = json.dumps(dict_qry_yesterday_position)
        self.slot_send_msg(json_qry_yesterday_position)
        self.signal_label_login_error_text.emit('查询策略昨仓')
    """

    # 查询期货账户昨日持仓明细（order）
    def qry_position_detial_for_order(self):
        dict_qry_position_detial_for_order = {
            'MsgRef': self.msg_ref_add(),
            'MsgSendFlag': 0,  # 发送标志，客户端发出0，服务端发出1
            'MsgSrc': 0,  # 消息源，客户端0，服务端1
            'MsgType': 15,  # 查询期货账户昨日持仓明细order
            'TraderID': self.__trader_id,
            'UserID': ""  # self.__user_id, 键值为空时查询所有UserID的持仓明细
        }
        json_qry_position_detial_for_order = json.dumps(dict_qry_position_detial_for_order)
        self.slot_send_msg(json_qry_position_detial_for_order)
        self.signal_label_login_error_text.emit('查询期货账户昨日持仓明细(order)')

    # 查询期货账户昨日持仓明细（trade）
    def qry_position_detial_for_trade(self):
        dict_qry_position_detial_for_trade = {
            'MsgRef': self.msg_ref_add(),
            'MsgSendFlag': 0,  # 发送标志，客户端发出0，服务端发出1
            'MsgSrc': 0,  # 消息源，客户端0，服务端1
            'MsgType': 17,  # 查询期货账户昨日持仓明细trade
            'TraderID': self.__trader_id,
            'UserID': ""  # self.__user_id, 键值为空时查询所有UserID的持仓明细
        }
        json_qry_position_detial_for_trade = json.dumps(dict_qry_position_detial_for_trade)
        self.slot_send_msg(json_qry_position_detial_for_trade)
        self.signal_label_login_error_text.emit('查询期货账户昨日持仓明细(trade)')

    """
    # 查询交易员开关
    def qry_trader_on_off(self):
        dict_qry_trader_on_off = {
            'MsgRef': self.msg_ref_add(),
            'MsgSendFlag': 0,  # 发送标志，客户端发出0，服务端发出1
            'MsgSrc': 0,  # 消息源，客户端0，服务端1
            'MsgType': 8,  # 查询交易员开关
            'TraderID': self.__trader_id,
            'UserID': ""  # self.__user_id, 键值为空时查询所有UserID的策略
        }
        # {"MsgRef": 1, "MsgSendFlag": 0, "MsgType": 8, "TraderID": "1601", "OnOff": 1, "MsgSrc": 0}
        json_qry_trader_on_off = json.dumps(dict_qry_trader_on_off)
        self.slot_send_msg(json_qry_trader_on_off)
        self.signal_label_login_error_text.emit('查询交易员开关')

    # 查询期货账户开关
    def qry_user_on_off(self):
        dict_qry_user_on_off = {
            'MsgRef': self.msg_ref_add(),
            'MsgSendFlag': 0,  # 发送标志，客户端发出0，服务端发出1
            'MsgSrc': 0,  # 消息源，客户端0，服务端1
            'MsgType': 10,  # 查询策略昨仓
            'TraderID': self.__trader_id,
            'UserID': ""  # self.__user_id, 键值为空时查询所有UserID的策略
        }
        json_qry_user_on_off = json.dumps(dict_qry_user_on_off)
        self.slot_send_msg(json_qry_user_on_off)
        self.signal_label_login_error_text.emit('查询期货账户开关')
    """

    # 创建user进程
    def create_user(self):
        # 组织创建user所需要的所有信息：xml文件信息和服务端传来的信息组合成一个dict
        self.__dict_create_user_info = dict()
        """
        样本数据结构
        self.__dict_create_user_info =
        {
            'user_id_1':
            {
                'xml':
                {
                    'user_statistics':
                    [
                        {'user_id': '078681', 'instrument_id': 'rb1705', 'action_count': 0, 'open_count': 0},
                        {'user_id': '078681', 'instrument_id': 'rb1710', 'action_count': 0, 'open_count': 0}
                    ],
                    'arguments':
                    [
                        {user_id="078681" strategy_id="01" trade_model="" order_algorithm="01" lots="10" lots_batch="1" stop_loss="0" strategy_on_off="1" spread_shift="0" a_instrument_id="rb1705" b_instrument_id="rb1705" a_limit_price_shift="0" b_limit_price_shift="0" a_wait_price_tick="0" b_wait_price_tick="0" a_order_action_limit="0" b_order_action_limit="0" buy_open="0" sell_close="0" sell_open="0" buy_close="0" sell_open_on_off="0" buy_close_on_off="0" buy_open_on_off="0" sell_close_on_off="0" position_a_buy="0" position_a_buy_today="0" position_a_buy_yesterday="0" position_b_buy="0" position_b_buy_today="0" position_b_buy_yesterday="0" position_a_sell="0" position_a_sell_today="0" position_a_sell_yesterday="0" position_b_sell="0" position_b_sell_today="0" position_b_sell_yesterday},

                    ],
                    'statistics':
                    [
                        {a_action_count="0" a_commission_count="0" a_order_count="0" a_profit_close="0" a_trade_rate="0" a_traded_amount="0" a_traded_count="0" b_action_count="0" b_commission_count="0" b_order_count="0" b_profit_close="0" b_trade_rate="0" b_traded_amount="0" b_traded_count="0" profit="0" profit_close="0" strategy_id="01" user_id="078681"},
                    ],
                    'position_detail_for_order':
                    [
                        {combhedgeflag="0" comboffsetflag="0" direction="0" insertdate="20170220" inserttime="11:18:30" instrumentid="cu1705" limitprice="3401.0" orderref="100000000401" orderstatus="a" strategy_id="01" tradingday="20170220" tradingdayrecord="20170221" user_id="078681" volumetotal="1" volumetotaloriginal="1" volumetraded="1" volumetradedbatch="1"}，

                    ],
                    'position_detail_for_trade':
                    [
                        {direction="0" hedgeflag="1" instrumentid="cu1705" offsetflag="0" orderref="100000000401" price="3401.0" strategy_id="01" tradedate="20170221" tradingday="20170220" tradingdayrecord="20170221" user_id="078681" volume="1"},
                    ],
                    'xml_status':
                    {
                        'datetime': "2017-03-02 10:42:36", 'tradingday': "2017-03-02", 'status': "True"
                    }
                },
                'server':
                {
                    'user_info': {},
                    'market_info': {},
                    'strategy_info': [{}, {}],
                    'list_position_detail_for_order': [{}, {}],
                    'list_position_detail_for_trade': [{}, {}],
                    'list_algorithm_info': {}
                }
        }
        """

        # 遍历从服务端获取到的期货账户信息列表
        for i_user_info in self.__list_user_info:  # i_user_info为dict
            user_id = i_user_info['userid']  # str，期货账户id
            self.__dict_create_user_info[user_id] = dict()
            self.__dict_create_user_info[user_id]['xml'] = dict()  # 保存从本地xml获取到的数据
            self.__dict_create_user_info[user_id]['server'] = dict()  # 保存从server端获取到的数据

            # 组织从xml获取到的数据
            if self.__xml_manager.get_xml_exist():
                # 获取xml中user级别统计，一个user有多条，数量与user交易的合约数量相等
                dict_user_write_xml_status = list()
                for i_xml in self.__xml_manager.get_list_user_write_xml_status():  # i_xml为dict
                    if i_xml['user_id'] == user_id:
                        dict_user_write_xml_status.append(i_xml)
                self.__dict_create_user_info[user_id]['xml']['dict_user_write_xml_status'] = dict_user_write_xml_status

                # 获取xml中的list_user_instrument_statistics
                list_user_instrument_statistics = list()
                for i_xml in self.__xml_manager.get_list_user_instrument_statistics():
                    if i_xml['user_id'] == user_id:
                        list_user_instrument_statistics.append(i_xml)
                self.__dict_create_user_info[user_id]['xml']['list_user_instrument_statistics'] = list_user_instrument_statistics

                # 获取xml中的strategy参数，数量与strategy个数相等
                list_strategy_arguments = list()
                for i_xml in self.__xml_manager.get_list_strategy_arguments():
                    if i_xml['user_id'] == user_id:
                        list_strategy_arguments.append(i_xml)
                self.__dict_create_user_info[user_id]['xml']['list_strategy_arguments'] = list_strategy_arguments

                # 获取xml中的strategy统计数据，数量与strategy个数相等
                list_strategy_statistics = list()
                for i_xml in self.__xml_manager.get_list_strategy_statistics():
                    if i_xml['user_id'] == user_id:
                        list_strategy_statistics.append(i_xml)
                self.__dict_create_user_info[user_id]['xml']['list_strategy_statistics'] = list_strategy_statistics

                # 获取xml中的持仓明细order数据，数量不定
                list_position_detail_for_order = list()
                for i_xml in self.__xml_manager.get_list_position_detail_for_order():
                    if i_xml['user_id'] == user_id:
                        list_position_detail_for_order.append(i_xml)
                self.__dict_create_user_info[user_id]['xml']['list_position_detail_for_order'] = list_position_detail_for_order

                # 获取xml中的持仓明细trade数据，数量不定
                list_position_detail_for_trade = list()
                for i_xml in self.__xml_manager.get_list_position_detail_for_order():
                    if i_xml['user_id'] == user_id:
                        list_position_detail_for_trade.append(i_xml)
                self.__dict_create_user_info[user_id]['xml']['list_position_detail_for_trade'] = list_position_detail_for_trade

                # 获取xml中的xml保存状态数据
                self.__dict_create_user_info[user_id]['xml']['xml_exist'] = True
            else:
                # 获取xml失败
                self.__dict_create_user_info[user_id]['xml']['xml_status'] = False

            # 组织从server获取到的数据
            if True:
                # 获取server的数据：user_info
                self.__dict_create_user_info[user_id]['server']['user_info'] = i_user_info
                
                # 获取server的数据：market_info
                self.__dict_create_user_info[user_id]['server']['market_info'] = self.__list_market_info[0]
                
                # 获取server的数据：strategy_info
                list_strategy_info = list()
                for i_strategy_info in self.__list_strategy_info:
                    if i_strategy_info['user_id'] == user_id:
                        list_strategy_info.append(i_strategy_info)
                self.__dict_create_user_info[user_id]['server']['strategy_info'] = list_strategy_info
                
                # 获取server的数据：list_position_detail_for_order
                list_position_detail_for_order = list()
                for i_position_detail_for_order in self.__list_position_detail_for_order:
                    if i_position_detail_for_order['userid'] == user_id:
                        list_position_detail_for_order.append(i_position_detail_for_order)
                self.__dict_create_user_info[user_id]['server']['list_position_detail_for_order'] = list_position_detail_for_order
                
                # 获取server的数据：list_position_detail_for_trade
                list_position_detail_for_trade = list()
                for i_position_detail_for_trade in self.__list_position_detail_for_trade:
                    if i_position_detail_for_trade['userid'] == user_id:
                        list_position_detail_for_trade.append(i_position_detail_for_trade)
                self.__dict_create_user_info[user_id]['server']['list_position_detail_for_trade'] = list_position_detail_for_trade

        for user_id in self.__dict_create_user_info:
            dict_user_info = self.__dict_create_user_info[user_id]
            p = Process(target=static_create_user_process, args=(dict_user_info,))  # self.__dict_total_user_process,))  # 创建user独立进程
            p.start()  # 开始进程

        self.signal_q_ctp_show.emit()  # 显示主窗口
        # self.__q_ctp.show()  # 显示主窗口
        # self.__q_login.hide()  # 隐藏登录窗口

                

if __name__ == '__main__':
    # 创建socket套接字
    socket_manager = SocketManager("10.0.0.33", 8888)  # 192.168.5.13
    socket_manager.connect()
    socket_manager.start()

    # 输入提示符
    prompt = b'->'
    while True:
        buff = input(prompt)
        if buff == "":
            continue
        # 发送数据buff
        sm = socket_manager.slot_send_msg(buff)
        if sm < 0:
            print("sm=", sm)
            print("buff=", buff)
            print("send msg error")
            print("socket error")


