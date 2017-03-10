# -*- coding: utf-8 -*-
"""
Created on Wed Jul 20 08:46:13 2016

@author: YuWanying
"""

import os
import time
import threading
from datetime import datetime
import copy
import PyCTP
from pymongo import MongoClient
from PyCTP_Trade import PyCTP_Trader_API
import Utils
from pandas import DataFrame, Series
import pandas as pd
import queue
from PyQt4 import QtCore
from MarketManager import MarketManager
from Strategy import Strategy


# class User(QtCore.QObject):
class User():
    # signal_update_pushButton_start_strategy = QtCore.pyqtSignal()  # 定义信号：内核设置期货账户交易开关 -> 更新窗口“开始策略”按钮状态
    # signal_label_login_error_text = QtCore.pyqtSignal(str)  # 定义信号：->更新登录窗口文本
    # signal_update_panel_show_account = QtCore.pyqtSignal(dict)  # 定义信号：更新界面账户资金信息

    # 初始化参数BrokerID\UserID\Password\frontaddress，参数格式为二进制字符串
    # def __init__(self, dict_arguments, parent=None, ctp_manager=None):
    def __init__(self, dict_arguments):
        print('process_id =', os.getpid(), ', User.__init__() dict_arguments =', dict_arguments)
        # super(User, self).__init__(parent)  # 显示调用父类初始化方法，使用其信号槽机制

        self.__queue_OnRtnTrade = queue.Queue(maxsize=0)  # 缓存OnRtnTrade回调数据
        self.__queue_OnRtnOrder = queue.Queue(maxsize=0)  # 缓存OnRtnOrder回调数据
        self.__threading_OnRtnOrder = threading.Thread(target=self.threading_run_OnRtnOrder)
        self.__threading_OnRtnTrade = threading.Thread(target=self.threading_run_OnRtnTrade)

        # 从服务端获取到的user_info
        self.__dict_user_info = dict_arguments['server']['user_info']
        print("User.__init__() self.__dict_user_info =", self.__dict_user_info)
        # 从服务端获取到的market_info
        self.__dict_market_info = dict_arguments['server']['market_info']
        print("User.__init__() self.__dict_market_info =", self.__dict_market_info)
        # 从服务端获取到的strategy_info
        self.__list_strategy_info = dict_arguments['server']['strategy_info']
        print("User.__init__() self.__list_strategy_info =", self.__list_strategy_info)
        # 从服务端获取到的list_position_detail_for_order
        self.__list_position_detail_for_order = dict_arguments['server']['list_position_detail_for_order']
        print("User.__init__() self.__list_position_detail_for_order =", self.__list_position_detail_for_order)
        # 从服务端获取到的list_position_detail_for_trade
        self.__list_position_detail_for_trade = dict_arguments['server']['list_position_detail_for_trade']
        print("User.__init__() self.__list_position_detail_for_trade =", self.__list_position_detail_for_trade)

        self.__xml_exist = dict_arguments['xml']['xml_exist']  # xml读取是否成功
        print("User.__init__() self.__xml_exist =", self.__xml_exist)
        if self.__xml_exist:
            # 从xml获取到的xml读取状态信息
            self.__dict_user_write_xml_status = dict_arguments['xml']['dict_user_write_xml_status']
            print("User.__init__() self.__dict_user_write_xml_status =", self.__dict_user_write_xml_status)
            # 从xml获取到的list_strategy_arguments
            self.__list_strategy_arguments = dict_arguments['xml']['list_strategy_arguments']
            print("User.__init__() self.__list_strategy_arguments =", self.__list_strategy_arguments)
            # 从xml获取到的list_strategy_statistics
            self.__list_strategy_statistics = dict_arguments['xml']['list_strategy_statistics']
            print("User.__init__() self.__list_strategy_statistics =", self.__list_strategy_statistics)
            # 从xml获取到的list_user_instrument_statistics
            self.list_user_instrument_statistics = dict_arguments['xml']['list_user_instrument_statistics']
            print("User.__init__() self.list_user_instrument_statistics =", self.list_user_instrument_statistics)
            # 从xml获取到的list_position_detail_for_order
            self.__list_position_detail_for_order = dict_arguments['xml']['list_position_detail_for_order']
            print("User.__init__() self.__list_position_detail_for_order =", self.__list_position_detail_for_order)
            # 从xml获取到的list_position_detail_for_trade
            self.__list_position_detail_for_trade = dict_arguments['xml']['list_position_detail_for_trade']
            print("User.__init__() self.__list_position_detail_for_trade =", self.__list_position_detail_for_trade)

        self.__trader_id = self.__dict_user_info['traderid']
        self.__user_id = self.__dict_user_info['userid']
        self.__BrokerID = self.__dict_user_info['brokerid']
        self.__Password = self.__dict_user_info['password']
        self.__FrontAddress = self.__dict_user_info['frontaddress']
        self.__on_off = self.__dict_user_info['on_off']  # 期货账户交易开关
        self.__qry_api_last_time = time.time()  # 类型浮点数，最后一次查询Trade_Api的时间
        self.__order_ref_part2 = 0  # 所有策略共用报单引用编号，报单引用后两位为策略编号，前十位递增一
        self.__TdApi_start_model = PyCTP.THOST_TERT_RESTART  # 初始化启动模式为RESTART，如果xml文件存在且数据可用为RESUME

        # self.__list_sessionid = list()  # 当前交易日，期货账户所有会话id，服务端的
        # self.__list_position_detail_for_order = list()  # 期货账户持仓明细，内部元素结构为order
        # self.__list_position_detail_for_trade = list()  # 期货账户持仓明细，内部元素结构为trade
        # self.__list_order_process = list()  # 挂单列表，未成交、部分成交还在队列中
        # self.__list_OnRtnOrder = []  # 保存单账户所有的OnRtnOrder回调数据
        # self.__list_OnRtnTrade = []  # 保存单账户所有的OnRtnTrade回调数据
        # self.__list_SendOrder = []  # 保存单账户所有调用OrderInsert的记录
        # self.__list_strategy = []  # 期货账户下面的所有交易策略实例列表
        # self.__dict_commission = dict()  # 保存手续费的字典，字典内元素格式为{'cu':{'OpenRatioByVolume': 0.0, 'OpenRatioByMoney': 2.5e-05, 'CloseTodayRatioByVolume': 0.0, 'CloseTodayRatioByMoney': 0.0, 'CloseRatioByVolume': 0.0, 'CloseRatioByMoney': 2.5e-05, 'InstrumentID': 'cu',  'InvestorRange': '1'}}
        # self.__list_InstrumentId = []  # 合约列表，记录撤单次数，在创建策略的时候添加合约，
        # self.__dict_action_counter = dict()  # 记录合约撤单次数的字典，撤单操作时添加次数，交易日换日时初始化值
        # self.__dict_open_counter = dict()  # 记录合约开仓手数的字典，交易日换日时初始化
        # self.__init_finished = False  # 初始化完成
        # self.__init_finished_succeed = True  # user初始化成功，初始化过程中遇到任何异常就设置为False

        # self.__dict_panel_show_account = dict()  # 单账户窗口显示的数据，{动态权益，静态权益，持仓盈亏，平仓盈亏，手续费，可用资金，占用保证金，下单冻结，风险度，今日入金，今日出金}
        # self.__current_margin = 0  # 期货账户的持仓占用保证金
        # self.__commission = 0  # 期货账户手续费
        # self.__profit_position = 0  # 期货账户持仓盈亏
        # self.__profit_close = 0  # 期货账户平仓盈亏
        #
        # self.__df_order = DataFrame()  # 保存该期货账户的所有OnRtnOrder来的记录
        # self.__df_trade = DataFrame()  # 保存该期货账户的所有OnRtnTrade来的记录
        # self.__df_qry_order = DataFrame()  # 保存该期货账户的所有QryOrder返回的记录
        # self.__df_qry_trade = DataFrame()  # 保存该期货账户的所有QryTrade返回的记录
        # self.__df_log = DataFrame()  # 测试时用来保存user全局日志

        # 连接交易前置
        # 创建行情，获取交易日
        self.__dict_create_user_status = dict()  # User创建状态详情，包含marekt创建信息
        self.__market_manager = MarketManager(self.__dict_market_info)
        self.__dict_create_user_status['result_market_connect'] = self.__market_manager.get_result_market_connect()
        self.__dict_create_user_status['get_result_market_login'] = self.__market_manager.get_result_market_login()
        for i in self.__dict_create_user_status:
            if self.__dict_create_user_status[i] != 0:
                print("User.__init__() 创建行情失败，user_id =", self.__user_id, ", self.__dict_create_user_status =", self.__dict_create_user_status)
        self.__MdApi_TradingDay = self.__market_manager.get_TradingDay()

        self.connect_trade_front()  # 连接交易前置
        self.login_trade_account()  # 登录期货账户，期货账户登录成功一刻开始OnRtnOrder、OnRtnTrade就开始返回历史数据
        self.qry_trading_account()  # 查询资金账户
        self.qry_investor_position()  # 查询投资者持仓
        self.qry_inverstor_position_detail()  # 查询投资者持仓明细
        self.qry_instrument_info()  # 查询合约信息
        self.__create_user_success = True  # 初始化创建user失败标志
        for i in self.__dict_create_user_status:
            if self.__dict_create_user_status[i] != 0:
                self.__create_user_success = False  # 创建期货账户失败
        if self.__create_user_success:
            print("User.__init__() User创建成功 user_id =", self.__user_id, ", self.__dict_create_user_status =", self.__dict_create_user_status)
        else:
            print("User.__init__() User创建失败 user_id =", self.__user_id, ", self.__dict_create_user_status =", self.__dict_create_user_status)
            return


        self.create_strategy()  # 创建策略

        """查询user的持仓明细"""
        # order结构的持仓明细
        # for i in self.__ctp_manager.get_SocketManager().get_list_position_detail_info_for_order():
        #     if i['userid'] == self.__user_id:
        #         self.__list_position_detail_for_order.append(i)

        # trade结构的持仓明细
        # for i in self.__ctp_manager.get_SocketManager().get_list_position_detail_info_for_trade():
        #     if i['userid'] == self.__user_id:
        #         self.__list_position_detail_for_trade.append(i)

        """查询成交记录"""
        # time.sleep(1.0)
        # self.qry_api_interval_manager()  # API查询时间间隔管理
        # self.QryTrade()  # 保存查询当天的Trade和Order记录，正常值格式为DataFrame，异常值为None
        # print(">>> User.__init__() len(self.__list_QryTrade) =", len(self.__list_QryTrade))
        # QryTrade查询结果的状态记录到CTPManager的user状态字典，成功为0
        # if isinstance(self.__list_QryTrade, list):
        #     self.__ctp_manager.get_dict_create_user_status()[self.__user_id]['QryTrade'] = 0  # 初始过程中一个步骤的标志位
        #     print("User.__init__() user_id=", self.__user_id, '查询成交记录成功，self.__list_QryTrade=', self.__list_QryTrade)
        # else:
        #     self.__ctp_manager.get_dict_create_user_status()[self.__user_id]['QryTrade'] = 1
        #     print("User.__init__() user_id=", self.__user_id, '查询成交记录失败，self.__list_QryOrder=', self.__list_QryOrder)
        # self.__ctp_manager.get_dict_create_user_status()[self.__user_id]['login_trade_account'] = login_trade_account

        """查询报单记录"""
        # time.sleep(1.0)
        # self.qry_api_interval_manager()  # API查询时间间隔管理
        # self.QryOrder()
        # QryOrder查询结果的状态记录到CTPManager的user状态字典，成功为0
        # if isinstance(self.__list_QryOrder, list):
        #     self.__ctp_manager.get_dict_create_user_status()[self.__user_id]['QryOrder'] = 0
        #     print("User.__init__() user_id=", self.__user_id, '查询报单记录成功，self.__list_QryOrder=', self.__list_QryOrder)
        # else:
        #     self.__ctp_manager.get_dict_create_user_status()[self.__user_id]['QryOrder'] = 1
        #     print("User.__init__() user_id=", self.__user_id, '查询报单记录失败')

        # print("User.__init__() user_id=", self.__user_id, "CTPManager记录User初始化信息 ", {self.__user_id: self.__ctp_manager.get_dict_create_user_status()[self.__user_id]})

        """初始化策略持仓明细列表"""
        # if self.init_list_position_detail() is not True:
        #     print("Strategy.__init__() 策略初始化错误：初始化策略持仓明细列表出错")
        #     self.__init_finished = False  # 策略初始化失败
        #     return

    # 连接交易前置
    def connect_trade_front(self):
        """连接交易前置"""
        # 为每个user创建独立的流文件夹
        s_path = b'conn/td/' + self.__user_id.encode() + b'/'
        Utils.make_dirs(s_path)  # 创建流文件路劲
        self.__trader_api = PyCTP_Trader_API.CreateFtdcTraderApi(s_path)
        self.__trader_api.set_user(self)  # 将该类设置为trade的属性

        # 根据本地xml文件读取状态和信息来决定RESUME或RESTART
        if self.__xml_exist:
            market_TradingDay = self.__MdApi_TradingDay[:4] + '-' + self.__MdApi_TradingDay[4:6] + '-' + self.__MdApi_TradingDay[6:]
            print("User.connect_trade_front() self.__dict_user_write_xml_status[0]['status'] =", self.__dict_user_write_xml_status[0]['status'])
            print("User.connect_trade_front() self.__dict_user_write_xml_status[0]['tradingday'] == market_TradingDay ", self.__dict_user_write_xml_status[0]['tradingday'], market_TradingDay, self.__dict_user_write_xml_status[0]['tradingday'] == market_TradingDay)
            if self.__dict_user_write_xml_status[0]['status'] == 'True' \
                    and self.__dict_user_write_xml_status[0]['tradingday'] == market_TradingDay:
                self.__TdApi_start_model = PyCTP.THOST_TERT_RESUME  # 从上次断开连接到现在的数据
            else:
                self.__TdApi_start_model = PyCTP.THOST_TERT_RESTART  # 从今天开盘到现在的数据
        else:
            self.__TdApi_start_model = PyCTP.THOST_TERT_RESTART  # 从今天开盘到现在的数据
        print("User.connect_trade_front() user_id =", self.__user_id, ", self.__TdApi_start_model =", self.__TdApi_start_model, ", PyCTP.THOST_TERT_RESUME =", PyCTP.THOST_TERT_RESUME, ", PyCTP.THOST_TERT_RESTART =", PyCTP.THOST_TERT_RESTART)

        # 0：发送成功；-1：因网络原因发送失败；-2：未处理请求队列总数量超限；-3：每秒发送请求数量超限
        connect_trade_front = self.__trader_api.Connect(self.__FrontAddress, self.__TdApi_start_model)
        # 连接前置地址状态记录到CTPManager的user状态字典，成功为0
        self.__dict_create_user_status['connect_trade_front'] = connect_trade_front

        # 连接交易前置错误提示
        if connect_trade_front == -1:
            self.signal_label_login_error_text.emit("期货账户" + self.__user_id + "因网络原因发送失败")
            self.__dict_create_user_status['connect_trade_front'] = "因网络原因发送失败"
        elif connect_trade_front == -2:
            self.signal_label_login_error_text.emit("期货账户" + self.__user_id + "未处理请求队列总数量超限")
            self.__dict_create_user_status[
                'connect_trade_front'] = "未处理请求队列总数量超限"
        elif connect_trade_front == -3:
            self.signal_label_login_error_text.emit("期货账户" + self.__user_id + "每秒发送请求数量超限")
            self.__dict_create_user_status['connect_trade_front'] = "每秒发送请求数量超限"
        elif connect_trade_front == -4:
            self.signal_label_login_error_text.emit("期货账户" + self.__user_id + "连接交易前置异常")
            self.__dict_create_user_status['connect_trade_front'] = "连接交易前置异常"

        if connect_trade_front != 0:
            self.__init_finished_succeed = False  # 初始化失败
            print("User.__init__() user_id=", self.__user_id, '连接交易前置失败',
                  Utils.code_transform(connect_trade_front))
        else:
            print("User.__init__() user_id=", self.__user_id, '连接交易前置成功', Utils.code_transform(connect_trade_front))

    # 登录期货账号
    def login_trade_account(self):
        """登录期货账号"""
        self.qry_api_interval_manager()  # API查询时间间隔管理
        login_trade_account = self.__trader_api.Login(self.__BrokerID.encode(), self.__user_id.encode(), self.__Password.encode())
        # 登录期货账号状态记录到CTPManager的user状态字典，成功为0
        # self.__dict_create_user_status['login_trade_account'] = login_trade_account
        if login_trade_account != 0:
            self.__init_finished_succeed = False  # 初始化失败
            print("User.login_trade_account() user_id=", self.__user_id, '登录期货账号失败',
                  Utils.code_transform(login_trade_account))
            return
        else:
            self.__front_id = self.__trader_api.get_front_id()  # 获取前置编号
            self.__session_id = self.__trader_api.get_session_id()  # 获取会话编号
            self.__TradingDay = self.__trader_api.get_TradingDay().decode()  # 获取交易日
            print("User.login_trade_account() user_id=", self.__user_id, '登录期货账号成功', Utils.code_transform(login_trade_account))

    # 查询资金账户
    def qry_trading_account(self):
        """查询资金账户"""
        # time.sleep(1.0)
        self.qry_api_interval_manager()  # API查询时间间隔管理
        list_QryTradingAccount = self.__trader_api.QryTradingAccount()
        if isinstance(list_QryTradingAccount, list):
            if isinstance(list_QryTradingAccount[0], dict):
                self.__QryTradingAccount = Utils.code_transform(list_QryTradingAccount[0])
                self.__dict_create_user_status['QryTradingAccount'] = 0
                print("User.__init__() user_id=", self.__user_id, '查询资金账户成功', self.__QryTradingAccount)
            else:
                print("User.__init__() user_id=", self.__user_id, '查询资金账户失败', Utils.code_transform(list_QryTradingAccount))
                self.__dict_create_user_status['QryTradingAccount'] = Utils.code_transform(list_QryTradingAccount)
        else:
            print("User.__init__() user_id=", self.__user_id, '查询资金账户失败',
                  Utils.code_transform(list_QryTradingAccount))
            self.__dict_create_user_status['QryTradingAccount'] = Utils.code_transform(list_QryTradingAccount)

    # 查询投资者持仓
    def qry_investor_position(self):
        """查询投资者持仓"""
        # time.sleep(1.0)
        self.qry_api_interval_manager()  # API查询时间间隔管理
        self.__QryInvestorPosition = Utils.code_transform(self.__trader_api.QryInvestorPosition())
        if isinstance(self.__QryInvestorPosition, list):
            self.__dict_create_user_status['QryInvestorPosition'] = 0
            print("User.__init__() user_id=", self.__user_id, '查询投资者持仓成功', self.__QryInvestorPosition)
        else:
            self.__dict_create_user_status[
                'QryInvestorPosition'] = self.__QryInvestorPosition
            print("User.__init__() user_id=", self.__user_id, '查询投资者持仓失败', self.__QryInvestorPosition)

    # 查询投资者持仓明细
    def qry_inverstor_position_detail(self):
        """查询投资者持仓明细"""
        # time.sleep(1.0)
        self.qry_api_interval_manager()  # API查询时间间隔管理
        self.__QryInvestorPositionDetail = Utils.code_transform(self.__trader_api.QryInvestorPositionDetail())
        if isinstance(self.__QryInvestorPositionDetail, list):
            self.__dict_create_user_status['QryInvestorPositionDetail'] = 0
            print("User.__init__() user_id=", self.__user_id, '查询投资者持仓明细成功', self.__QryInvestorPositionDetail)
        else:
            self.__dict_create_user_status[
                'QryInvestorPositionDetail'] = self.__QryInvestorPositionDetail
            print("User.__init__() user_id=", self.__user_id, '查询投资者持仓明细失败', self.__QryInvestorPositionDetail)

    # 查询合约信息
    def qry_instrument_info(self):
        # 查询合约，所有交易所的所有合约
        self.qry_api_interval_manager()  # API查询时间间隔管理
        self.__QryInstrument = Utils.code_transform(self.__trader_api.QryInstrument())
        if isinstance(self.__QryInstrument, list):
            if len(self.__QryInstrument) > 0:
                self.__dict_create_user_status['QryInstrument'] = 0
                print("User.qry_instrument_info() user_id=", self.__user_id, "查询合约信息成功", self.__QryInstrument)
                # self.__ctp_manager.set_got_list_instrument_info(True)  # 将获取合约信息的状态设置为真，获取成功
                # self.__ctp_manager.set_instrument_info(self.__QryInstrument)  # 将查询到的合约信息传递给CTPManager
            else:
                self.__dict_create_user_status['QryInstrument'] = self.__QryInstrument
                print("User.qry_instrument_info() user_id=", self.__user_id, "查询合约信息失败", self.__QryInstrument)
        else:
            self.__dict_create_user_status['QryInstrument'] = self.__QryInstrument
            print("User.qry_instrument_info() user_id=", self.__user_id, "查询合约信息失败", self.__QryInstrument)

    # API查询操作管理，记录最后一次查询时间，且与上一次查询时间至少间隔一秒，该方法放置位置在对api查询之前
    def qry_api_interval_manager(self):
        time_interval = time.time() - self.__qry_api_last_time
        if time_interval < 1.0:
            time.sleep(1-time_interval)
        self.__qry_api_last_time = time.time()

    # 装载xml数据
    def load_xml(self):
        # 如果从本地硬盘中正常获取到xml
        if self.__ctp_manager.get_XML_Manager().get_read_xml_status():
            self.__list_statistics = list()  # 从xml文件读取的期货账户维护的统计指标
            for i in self.__ctp_manager.get_XML_Manager().get_list_user_statistics():
                if i['user_id'] == self.__user_id:
                    self.__list_statistics.append(i)  # user对象统计数据list装载xml数据
            # 从xml中取出的数据格式：
            # [{'action_count': 0, 'user_id': '078681', 'instrument_id': 'cu1705', 'open_count': 0},
            #  {'action_count': 0, 'user_id': '078681', 'instrument_id': 'cu1710', 'open_count': 0} ]

            # 将xml中取出的user统计数据，赋值给对应的策略对象
            for obj_strategy in self.__list_strategy:  # 遍历user下的策略对象列表
                for dict_statistics in self.__list_statistics:  # 遍历user下的统计数据列表
                    if dict_statistics['instrument_id'] == obj_strategy.get_a_instrument_id():  # i = 'cu1705'
                        obj_strategy.set_a_action_count(dict_statistics['action_count'])
                        obj_strategy.set_a_open_count(dict_statistics['open_count'])
                    elif dict_statistics['instrument_id'] == obj_strategy.get_b_instrument_id():
                        obj_strategy.set_b_action_count(dict_statistics['action_count'])
                        obj_strategy.set_b_open_count(dict_statistics['open_count'])

    # 创建策略实例
    def create_strategy(self):
        self.__list_strategy = list()  # 存放策略实例对象的列联表
        for i in self.__list_strategy_info:
            obj_strategy = Strategy(i, self)
            self.__list_strategy.append(obj_strategy)
        self.__select_strategy = self.__list_strategy[0]
        self.__threading_OnRtnOrder.start()  # strategy实例化完成，开始线程
        self.__threading_OnRtnTrade.start()

    # 获统计数据
    def get_list_user_statistics(self):
        return self.__list_statistics

    # 将CTPManager类设置为user的属性
    def set_CTPManager(self, obj_CTPManager):
        self.__ctp_manager = obj_CTPManager

    # 获取CTPManager属性
    def get_CTPManager(self):
        return self.__ctp_manager

    # 获取行情端口交易日
    def get_MdApi_TradingDay(self):
        return self.__MdApi_TradingDay

    # 获取TdApi初始化方式：PyCTP.THOST_TERT_RESUME = 1 , PyCTP.THOST_TERT_RESTART = 0
    def get_TdApi_start_model(self):
        return self.__TdApi_start_model

    # 设置数据库管理类DBManager为该类对象
    def set_DBManager(self, obj_DBManager):
        self.__DBManager = obj_DBManager

    # QAccountWidegt设置为属性
    def set_QAccountWidget_signal(self, obj_QAccountWidget):
        self.__QAccountWidget_signal = obj_QAccountWidget

    def get_QAccountWidget_signal(self):
        return self.__QAccountWidget_signal

    # QAccountWidegtTotal设置为属性（总账户的窗口）
    def set_QAccountWidget_total(self, obj_QAccountWidgetTotal):
        self.__QAccountWidget_total = obj_QAccountWidgetTotal

    def get_QAccountWidget_total(self):
        return self.__QAccountWidget_total

    # 获得数据库
    def get_mongodb_CTP(self):
        return self.__mongo_client.CTP

    # 从数据库获取user的strategy参数集合
    def get_col_strategy(self):
        return self.__mongo_client.CTP.get_collection(self.__user_id+'_strategy')

    # 从数据库获取user的持仓汇总集合
    def get_col_position(self):
        return self.__mongo_client.CTP.get_collection(self.__user_id+'_position')

    # 从数据库获取user的持仓明细集合
    def get_col_position_detail(self):
        return self.__mongo_client.CTP.get_collection(self.__user_id+'_position_detail')

    # 从数据库获取user的trade集合
    def get_col_trade(self):
        return self.__mongo_client.CTP.get_collection(self.__user_id+'_trade')

    # 从数据库获取user的order列表
    def get_col_order(self):
        return self.__mongo_client.CTP.get_collection(self.__user_id + '_order')

    def get_read_xml_status(self):
        return self.__read_xml_status

    def set_read_xml_status(self, bool_input):
        self.__read_xml_status = bool_input

    # 获取期货账号
    def get_user_id(self):
        return self.__user_id

    # 获取交易员id
    def get_trader_id(self):
        return self.__trader_id

    # 获取trade实例(TD)
    def get_trader_api(self):
        return self.__trader_api

    # 获取self.__instrument_info
    def get_instrument_info(self):
        return self.__QryInstrument

    # 设置user的交易开关，0关、1开
    def set_on_off(self, int_on_off):
        print(">>>User.set_on_off() 设置期货账户交易开关，user_id=", self.__user_id, int_on_off)
        self.__on_off = int_on_off
        self.signal_update_pushButton_start_strategy.emit()  # 触发信号：内核设置期货账户交易开关 -> 更新窗口“开始策略”按钮状态

    # 获取user的交易开关，0关、1开
    def get_on_off(self):
        return self.__on_off

    # # 设置user的交易开关，0关、1开
    # def set_only_close(self, int_only_close):
    #     self.__only_close = int_only_close
    #
    # # 获取user的交易开关，0关、1开
    # def get_only_close(self):
    #     return self.__only_close

    # 设置user初始化状态
    def set_init_finished(self, bool_input):
        self.__init_finished = bool_input

    # 获取user初始化状态
    def get_init_finished(self):
        return self.__init_finished

    # 获取交易日
    def GetTradingDay(self):
        return self.__TradingDay

    # 获取报单引用，自增1，位置处于第1到第10位，共9位阿拉伯数字，user的所有策略共用
    def add_order_ref_part2(self):
        self.__order_ref_part2 += 1
        return self.__order_ref_part2

    # 添加交易策略实例，到self.__list_strategy
    def add_strategy(self, obj_strategy):
        self.__list_strategy.append(obj_strategy)  # 将交易策略实例添加到本类的交易策略列表
        self.__trader_api.set_list_strategy(self.__list_strategy)  # 将本类的交易策略列表转发给trade
        obj_strategy.set_user(self)  # 将user设置为strategy属性

    # 添加合约代码到user类的self.__dict_action_counter
    # def add_instrument_id_action_counter(self, list_instrument_id):
    #     for i in list_instrument_id:
    #         if i not in self.__dict_action_counter:
    #             self.__dict_action_counter[i] = 0

    # 撤单计数
    def action_counter(self, Order):
        if len(Order['OrderSysID']) == 0:  # 只统计有交易所编码的order
            return
        if Order['OrderStatus'] != '5':  # 值为5：撤单
            return
        if Order['InstrumentID'] in self.__dict_action_counter:  # 已经存在的合约，撤单次数加+1
            self.__dict_action_counter[Order['InstrumentID']] += 1
        else:
            self.__dict_action_counter[Order['InstrumentID']] = 1  # 不存在的合约，撤单次数设置为1

        # 撤单次数赋值到策略对象的合约撤单次数
        for i_strategy in self.__list_strategy:
            if i_strategy.get_a_instrument_id() == Order['InstrumentID']:
                i_strategy.set_a_action_count(self.__dict_action_counter[Order['InstrumentID']])
            elif i_strategy.get_b_instrument_id() == Order['InstrumentID']:
                i_strategy.set_b_action_count(self.__dict_action_counter[Order['InstrumentID']])

    # 删除交易策略实例，从self.__list_strategy
    def del_strategy(self, strategy_id):
        for i in self.__list_strategy:
            if i.get_strategy_id() == strategy_id:
                self.__list_strategy.remove(i)

    # 获取list_strategy
    def get_list_strategy(self):
        return self.__list_strategy

    # 获取合约撤单次数的字典
    def get_dict_action(self):
        return self.__dict_action_counter

    # 查询行情
    def qry_depth_market_data(self, instrument_id):
        return self.__trader_api.QryDepthMarketData(instrument_id)

    # 转PyCTP_Market_API类中回调函数OnRtnOrder
    def OnRtnTrade(self, Trade):
        t = datetime.now()  # 取接收到回调数据的本地系统时间
        self.statistics(trade=Trade)  # 统计期货账户的合约开仓手数

        # 根据字段“OrderRef”筛选出本套利系统的记录，OrderRef规则：第1位为‘1’，第2位至第10位为递增数，第11位至第12位为StrategyID
        if len(Trade['OrderRef']) == 12 and Trade['OrderRef'][:1] == '1':
            # Order新增字段
            Trade['OperatorID'] = self.__trader_id  # 客户端账号（也能区分用户身份或交易员身份）:OperatorID
            Trade['StrategyID'] = Trade['OrderRef'][-2:]  # 报单引用末两位是策略编号
            Trade['ReceiveLocalTime'] = t.strftime("%Y-%m-%d %H:%M:%S %f")  # 收到回报的本地系统时间
            # Trade['RecMicrosecond'] = t.strftime("%f")  # 收到回报中的时间毫秒

            self.__queue_OnRtnTrade.put(Trade)  # 缓存OnRtnTrade回调数据

            # for i in self.__list_strategy:  # 转到strategy回调函数
            #     if Trade['OrderRef'][-2:] == i.get_strategy_id():
            #         i.OnRtnOrder(Trade)

    # 转PyCTP_Market_API类中回调函数OnRtnOrder
    def OnRtnOrder(self, Order):
        t = datetime.now()  #取接收到回调数据的本地系统时间
        self.statistics(order=Order)  # 统计期货账户的合约撤单次数

        # 所有trade回调保存到DataFrame格式变量
        # series_order = Series(Order)
        # self.__df_order = DataFrame.append(self.__df_order, other=series_order, ignore_index=True)
        # self.write_log(t.strftime("%Y-%m-%d %H:%M:%S"), 'OnRtnOrder', '报单回调', str(Order))  # 保存到DataFrame格式日志
        
        # 根据字段“OrderRef”筛选出本套利系统的记录，OrderRef规则：第1位为‘1’，第2位至第10位为递增数，第11位至第12位为StrategyID
        if len(Order['OrderRef']) == 12 and Order['OrderRef'][:1] == '1':
            # Order新增字段
            Order['OperatorID'] = self.__trader_id  # 客户端账号（也能区分用户身份或交易员身份）:OperatorID
            Order['StrategyID'] = Order['OrderRef'][-2:]  # 报单引用末两位是策略编号
            Order['ReceiveLocalTime'] = t.strftime("%Y-%m-%d %H:%M:%S %f")  # 收到回报的时间
            # Order['RecMicrosecond'] = t.strftime("%f")  # 收到回报中的时间毫秒

            self.__queue_OnRtnOrder.put(Order)  # 缓存OnRtnTrade回调数据

            # for i in self.__list_strategy:  # 转到strategy回调函数
            #     if Order['OrderRef'][-2:] == i.get_strategy_id():
            #         i.OnRtnOrder(Order)

        # 记录存到数据库
        # self.__DBManager.insert_trade(Order)
        # self.__mongo_client.CTP.get_collection(self.__user_id+'_Order').insert_one(Order)  # 记录插入到数据库

    # 处理OnRtnOrder的线程
    def threading_run_OnRtnOrder(self):
        while True:
            order = self.__queue_OnRtnOrder.get()
            for obj_strategy in self.__list_strategy:
                if order['StrategyId'] == obj_strategy.get_strategy_id():
                    obj_strategy.OnRtnOrder(order)

    # 处理OnRtnTrade的线程
    def threading_run_OnRtnTrade(self):
        while True:
            trade = self.__queue_OnRtnOrder.get()
            for obj_strategy in self.__list_strategy:
                if trade['StrategyId'] == obj_strategy.get_strategy_id():
                    obj_strategy.OnRtnOrder(trade)

    # 将order和trade记录保存到本地
    def save_df_order_trade(self):
        str_user_id = self.__user_id
        str_time = datetime.now().strftime("%Y-%m-%d %H%M%S")
        order_file_path = "data/order_" + str_user_id + "_" + str_time + '.csv'
        trade_file_path = "data/trade_" + str_user_id + "_" + str_time + '.csv'
        log_file_path = "data/log_" + str_user_id + "_" + str_time + '.csv'
        # qry_order_file_path = "data/qry_order_" + str_user_id + "_" + str_time + '.csv'
        # qry_trade_file_path = "data/qry_trade_" + str_user_id + "_" + str_time + '.csv'
        print(">>> PyCTP_Trade.save_df_order_trade() order_file_path =", order_file_path)
        print(">>> PyCTP_Trade.save_df_order_trade() trade_file_path =", trade_file_path)
        print(">>> PyCTP_Trade.save_df_order_trade() log_file_path =", log_file_path)
        self.__df_order.to_csv(order_file_path)
        self.__df_trade.to_csv(trade_file_path)
        self.__df_log.to_csv(log_file_path)
        # self.__df_qry_order.to_csv(qry_order_file_path)
        # self.__df_qry_trade.to_csv(qry_trade_file_path)

    # 转PyCTP_Market_API类中回调函数QryTrade
    def QryTrade(self):
        list_QryTrade = self.__trader_api.QryTrade()  # 正确返回值为list类型，否则为异常
        self.__list_QryTrade = list()  # 保存本套利系统的Trade记录
        if isinstance(list_QryTrade, list):
            list_QryTrade = Utils.code_transform(list_QryTrade)
            print("User.QryTrade() QryTrade成功，len(list_QryTrade) =", len(list_QryTrade))
        else:
            print("User.QryTrade() QryTrade失败，返回值 =", list_QryTrade)
            return
        # print(">>> User.QryTrade() QryTrade从api获得的样本数 =", len(list_QryTrade))
        # 筛选条件：OrderRef第一位为1，长度为12
        for i in list_QryTrade:
            if len(i['OrderRef']) == 12 and i['OrderRef'][:1] == '1':
                i['StrategyID'] = i['OrderRef'][-2:]  # 增加字段：策略编号"StrategyID"
                self.__list_QryTrade.append(i)
        # print(">>> User.QryTrade() QryTrade过滤后样本数 =", len(self.__list_QryTrade))

    # 转PyCTP_Market_API类中回调函数QryOrder
    def QryOrder(self):
        list_QryOrder = self.__trader_api.QryOrder()  # 正确返回值为list类型，否则为异常
        self.__list_QryOrder = list()  # 保存本套利系统的Order记录
        if isinstance(list_QryOrder, list):
            list_QryOrder = Utils.code_transform(list_QryOrder)
            print("User.QryTrade() QryOrder成功，len(list_QryOrder) =", len(list_QryOrder))
        else:
            print("User.QryTrade() QryOrder失败，返回值 =", list_QryOrder)
            return
        # 筛选条件：OrderRef第一位为1，长度为12
        # print(">>> User.QryOrder() QryOrder过滤前样本数 =", len(list_QryOrder))
        for i in list_QryOrder:
            self.action_counter(i)  # 撤单计数
            if len(i['OrderRef']) == 12 and i['OrderRef'][:1] == '1':
                i['StrategyID'] = i['OrderRef'][-2:]  # 增加字段：策略编号"StrategyID"
                self.__list_QryOrder.append(i)
        # print(">>> User.QryOrder() QryOrder过滤后样本数 =", len(self.__list_QryOrder))

    # 获取listQryOrder
    def get_list_QryOrder(self):
        return self.__list_QryOrder

    # 获取listQryTrade
    def get_list_QryTrade(self):
        return self.__list_QryTrade

    def get_QryTradingAccount(self):
        return self.__QryTradingAccount

    # 形参为包含字段成交量'VolumeTradedBatch'和成交价'Price'的Order结构体
    # 保存手续费的dict结构为{'cu':{'}, 'zn':{}}
    # 形参：合约代码'cu1703'，交易所代码'SHFE'
    def get_commission(self, instrument_id, exchange_id):
        # 获取品种代码，例如cu、zn
        if exchange_id in ['SHFE', 'CFFEX', 'DZCE']:
            commodity_id = instrument_id[:2]
        elif exchange_id in ['DCE']:
            commodity_id = instrument_id[:1]
        if commodity_id not in self.__dict_commission:
            # 通过API查询单个品种的手续费率dict
            self.qry_api_interval_manager()  # API查询时间间隔管理
            # 尝试三次获取指定合约的手续费详细
            flag = 0
            while flag < 3:
                self.qry_api_interval_manager()  # API查询时间间隔管理
                list_commission = self.__trader_api.QryInstrumentCommissionRate(instrument_id.encode())
                if isinstance(list_commission, list):
                    dict_commission = Utils.code_transform(list_commission[0])
                    flag = 0
                    break
                else:
                    flag += 1
                    print("User.get_mmission() 获取手续费失败，尝试次数", flag, "user_id =", self.__user_id, "instrument_id =", instrument_id,
                          "exchange_id =", exchange_id, "手续费获取结果 =", list_commission)
            if flag > 0:  # 正确获取到手续费率的dict则flag值为0，否则为大于0的整数
                print("User.get_mmission() 获取手续费失败， user_id =", self.__user_id, "instrument_id =", instrument_id, "exchange_id =", exchange_id, "手续费获取结果 =", list_commission)
            # print(">>> User.get_commission() ", dict_commission)
            self.__dict_commission[commodity_id] = dict_commission  # 将单个品种手续费率存入到user类的所有品种手续费率dict
        return self.__dict_commission[commodity_id]

    # 添加字段"本次成交量"，order结构中加入字段VolumeTradedBatch
    def add_VolumeTradedBatch(self, order):
        order_new = copy.deepcopy(order)
        if order_new['OrderStatus'] in ['0', '1']:  # 全部成交、部分成交还在队列中
            # 原始报单量为1手，本次成交量就是1手
            if order_new['VolumeTotalOriginal'] == 1:
                order_new['VolumeTradedBatch'] = 1
            else:
                for i in self.__list_order_process:
                    if i['OrderRef'] == order['OrderRef']:  # 在列表中找到相同的OrderRef记录
                        order_new['VolumeTradedBatch'] = order_new['VolumeTraded'] - i['VolumeTraded']  # 本次成交量
                        break
        else:  # 非（全部成交、部分成交还在队列中）
            order_new['VolumeTradedBatch'] = 0
        return order_new

    # 更新挂单列表，重写方法self.update_list_order_pending()
    """
    def update_list_order_process(self, order):
        # order中的字段OrderStatus
        #  0 全部成交
        #  1 部分成交，订单还在交易所撮合队列中
        #  3 未成交，订单还在交易所撮合队列中
        #  5 已撤销
        #  a 未知 - 订单已提交交易所，未从交易所收到确认信息
        if order['OrderStatus'] == '0':
            for i in self.__list_order_process:
                if i['OrderRef'] == order['OrderRef']:  # 在列表中找到相同的OrderRef记录
                    self.__list_order_process.remove(i)  # 删除找到的order记录
                    break
        elif order['OrderStatus'] == '1':
            for i in self.__list_order_process:
                if i['OrderRef'] == order['OrderRef']:  # 在列表中找到相同的OrderRef记录
                    self.__list_order_process.remove(i)  # 删除找到的order记录
                    self.__list_order_process.append(order)  # 添加最新的order记录
                    break
        elif order['OrderStatus'] == '3':
            self.__list_order_process.append(order)
        elif order['OrderStatus'] == '5':
            for i in self.__list_order_process:
                if i['OrderRef'] == order['OrderRef']:  # 在列表中找到相同的OrderRef记录
                    self.__list_order_process.remove(i)  # 删除找到的order记录
                    break
        elif order['OrderStatus'] == 'a':
            pass  # 不需要处理
    """

    # 更新持仓明细列表，形参为order
    """
    def update_list_position_detail(self, input_order):
        order中的CombOffsetFlag 或 trade中的OffsetFlag值枚举：
        0：开仓
        1：平仓
        3：平今
        4：平昨
        # 跳过无成交的order记录
        if input_order['VolumeTraded'] == 0:
            return
        order_new = copy.deepcopy(input_order)  # 形参深度拷贝到方法局部变量，目的是修改局部变量值不会影响到形参
        # order_new中"CombOffsetFlag"值="0"为开仓，不用考虑全部成交还是部分成交，开仓order直接添加到持仓明细列表里
        if order_new['CombOffsetFlag'] == '0':
            self.__list_position_detail_for_order.append(order_new)
        # order_new中"CombOffsetFlag"值="3"为平今
        if order_new['CombOffsetFlag'] == '3':
            for i in self.__list_position_detail_for_order:  # i为order结构体，类型为dict
                # 持仓明细中order与order_new比较：交易日相同、合约代码相同、投保标志相同
                if i['TradingDay'] == order_new['TradingDay'] \
                        and i['InstrumentID'] == order_new['InstrumentID'] \
                        and i['CombHedgeFlag'] == order_new['CombHedgeFlag']:
                    # order_new的VolumeTradedBatch等于持仓列表首个满足条件的order的VolumeTradedBatch
                    if order_new['VolumeTradedBatch'] == i['VolumeTradedBatch']:
                        self.__list_position_detail_for_order.remove(i)
                        break
                    # order_new的VolumeTradedBatch小于持仓列表首个满足条件的order的VolumeTradedBatch
                    elif order_new['VolumeTradedBatch'] < i['VolumeTradedBatch']:
                        i['VolumeTradedBatch'] -= order_new['VolumeTradedBatch']
                        break
                    # order_new的VolumeTradedBatch大于持仓列表首个满足条件的order的VolumeTradedBatch
                    elif order_new['VolumeTradedBatch'] > i['VolumeTradedBatch']:
                        order_new['VolumeTradedBatch'] -= i['VolumeTradedBatch']
                        self.__list_position_detail_for_order.remove(i)
        # order_new中"CombOffsetFlag"值="4"为平昨
        elif order_new['CombOffsetFlag'] == '4':
            for i in self.__list_position_detail_for_order:  # i为order结构体，类型为dict
                # 持仓明细中order与order_new比较：交易日不相同、合约代码相同、投保标志相同
                if i['TradingDay'] != order_new['TradingDay'] \
                        and i['InstrumentID'] == order_new['InstrumentID'] \
                        and i['CombHedgeFlag'] == order_new['CombHedgeFlag']:
                    # order_new的VolumeTradedBatch等于持仓列表首个满足条件的order的VolumeTradedBatch
                    if order_new['VolumeTradedBatch'] == i['VolumeTradedBatch']:
                        self.__list_position_detail_for_order.remove(i)
                        break
                    # order_new的VolumeTradedBatch小于持仓列表首个满足条件的order的VolumeTradedBatch
                    elif order_new['VolumeTradedBatch'] < i['VolumeTradedBatch']:
                        i['VolumeTradedBatch'] -= order_new['VolumeTradedBatch']
                        break
                    # order_new的VolumeTradedBatch大于持仓列表首个满足条件的order的VolumeTradedBatch
                    elif order_new['VolumeTradedBatch'] > i['VolumeTradedBatch']:
                        order_new['VolumeTradedBatch'] -= i['VolumeTradedBatch']
                        self.__list_position_detail_for_order.remove(i)
    """

    # 更新持仓明细列表，形参为order，统计持仓盈亏、平仓盈亏等指标需要，初始化过程和OnRtnTrade中被调用
    """
    def update_list_position_detail_trade(self, input_trade):
        order中的CombOffsetFlag 或 trade中的OffsetFlag值枚举：
        0：开仓
        1：平仓
        3：平今
        4：平昨
        trade_new = copy.deepcopy(input_trade)  # 形参深度拷贝到方法局部变量，目的是修改局部变量值不会影响到形参
        # trade_new中"OffsetFlag"值="0"为开仓，不用考虑全部成交还是部分成交，开仓order直接添加到持仓明细列表里
        if trade_new['OffsetFlag'] == '0':
            self.__list_position_detail_for_trade.append(trade_new)
        # order_new中"OffsetFlag"值="3"为平今
        if trade_new['OffsetFlag'] == '3':
            for i in self.__list_position_detail_for_trade:  # i为order结构体，类型为dict
                # 持仓明细中order与order_new比较：交易日相同、合约代码相同、投保标志相同
                if i['TradingDay'] == trade_new['TradingDay'] \
                        and i['InstrumentID'] == trade_new['InstrumentID'] \
                        and i['CombHedgeFlag'] == trade_new['CombHedgeFlag']:
                    # order_new的VolumeTradedBatch等于持仓列表首个满足条件的order的VolumeTradedBatch
                    if trade_new['VolumeTradedBatch'] == i['VolumeTradedBatch']:
                        self.__list_position_detail_for_trade.remove(i)
                        break
                    # order_new的VolumeTradedBatch小于持仓列表首个满足条件的order的VolumeTradedBatch
                    elif trade_new['VolumeTradedBatch'] < i['VolumeTradedBatch']:
                        i['VolumeTradedBatch'] -= trade_new['VolumeTradedBatch']
                        break
                    # order_new的VolumeTradedBatch大于持仓列表首个满足条件的order的VolumeTradedBatch
                    elif trade_new['VolumeTradedBatch'] > i['VolumeTradedBatch']:
                        trade_new['VolumeTradedBatch'] -= i['VolumeTradedBatch']
                        self.__list_position_detail_for_trade.remove(i)
        # order_new中"OffsetFlag"值="4"为平昨
        elif trade_new['OffsetFlag'] == '4':
            for i in self.__list_position_detail_for_trade:  # i为order结构体，类型为dict
                # 持仓明细中order与order_new比较：交易日不相同、合约代码相同、投保标志相同
                if i['TradingDay'] != trade_new['TradingDay'] \
                        and i['InstrumentID'] == trade_new['InstrumentID'] \
                        and i['CombHedgeFlag'] == trade_new['CombHedgeFlag']:
                    # order_new的VolumeTradedBatch等于持仓列表首个满足条件的order的VolumeTradedBatch
                    if trade_new['VolumeTradedBatch'] == i['VolumeTradedBatch']:
                        self.__list_position_detail_for_trade.remove(i)
                        break
                    # order_new的VolumeTradedBatch小于持仓列表首个满足条件的order的VolumeTradedBatch
                    elif trade_new['VolumeTradedBatch'] < i['VolumeTradedBatch']:
                        i['VolumeTradedBatch'] -= trade_new['VolumeTradedBatch']
                        break
                    # order_new的VolumeTradedBatch大于持仓列表首个满足条件的order的VolumeTradedBatch
                    elif trade_new['VolumeTradedBatch'] > i['VolumeTradedBatch']:
                        trade_new['VolumeTradedBatch'] -= i['VolumeTradedBatch']
                        self.__list_position_detail_for_trade.remove(i)
    """

    # 更新账户资金信息，并刷新界面
    def update_panel_show_account(self):
        # {动态权益，静态权益，持仓盈亏，平仓盈亏，手续费，可用资金，占用保证金，下单冻结，风险度，今日入金，今日出金}
        # 删除下单冻结指标，无实际需求
        # 静态权益 PreBalance
        self.__dict_panel_show_account['PreBalance'] = self.__QryTradingAccount['PreBalance']
        # 入金金额 Deposit
        self.__dict_panel_show_account['Deposit'] = self.__QryTradingAccount['Deposit']
        # 出金金额 Withdraw
        self.__dict_panel_show_account['Withdraw'] = self.__QryTradingAccount['Withdraw']
        # 动态权益=静态权益+入金金额-出金金额+平仓盈亏+持仓盈亏-手续费
        # self.__dict_panel_show_account['Capital'] = self.__QryTradingAccount['PreBalance'] + self.__QryTradingAccount['Deposit'] - self.__QryTradingAccount['Withdraw'] + self.__QryTradingAccount['CloseProfit'] + self.__QryTradingAccount['PositionProfit'] - self.__QryTradingAccount['Commission']
        # 遍历self.__list_strategy
        for i in self.__list_strategy:
            self.__current_margin += i.get_current_margin()  # 期货账户占用保证金
            self.__commission += i.get_commission()  # 期货账户手续费
            self.__profit_position += i.get_profit_position()  # 期货账户持仓盈亏
            self.__profit_close += i.get_profit_close()  # 期货账户平仓盈亏
        self.__dict_panel_show_account['CurrMargin'] = self.__current_margin  # 期货账户占用保证金
        self.__dict_panel_show_account['Commission'] = self.__commission  # 期货账户手续费
        self.__dict_panel_show_account['profit_position'] = self.__profit_position  # 期货账户持仓盈亏
        self.__dict_panel_show_account['profit_close'] = self.__profit_close  # 期货账户平仓盈亏
        # 期货账户动态权益
        self.__dict_panel_show_account['Capital'] = self.__QryTradingAccount['PreBalance'] + self.__QryTradingAccount['Deposit'] - self.__QryTradingAccount['Withdraw'] + self.__profit_close + self.__profit_position - self.__commission
        # 期货账户可用资金
        self.__dict_panel_show_account['Available'] = self.__dict_panel_show_account['Capital'] - self.__current_margin
        # 期货账户风险度
        self.__dict_panel_show_account['Risk'] = 1-(self.__dict_panel_show_account['Available'] / self.__dict_panel_show_account['Capital'])

        # 更新界面显示
        self.signal_update_panel_show_account.emit(self.__dict_panel_show_account)

    # 获取期货账户资金统计信息
    def get_panel_show_account(self):
        return self.__dict_panel_show_account

    # 窗口显示账户资金初始化信息
    def init_panel_show_account(self):
        # 动态权益=静态权益+入金金额-出金金额+平仓盈亏+持仓盈亏-手续费
        Capital = self.__QryTradingAccount['PreBalance'] + self.__QryTradingAccount['Deposit'] - \
                  self.__QryTradingAccount['Withdraw'] + self.__QryTradingAccount['CloseProfit'] + \
                  self.__QryTradingAccount['PositionProfit'] - self.__QryTradingAccount['Commission']
        self.__dict_panel_show_account = {
            'Capital': Capital,
            'PreBalance': self.__QryTradingAccount['PreBalance'],  # 静态权益
            'PositionProfit': self.__QryTradingAccount['PositionProfit'],  # 持仓盈亏
            'CloseProfit': self.__QryTradingAccount['CloseProfit'],  # 平仓盈亏
            'Commission': self.__QryTradingAccount['Commission'],  # 手续费
            'Available': self.__QryTradingAccount['Available'],  # 可用资金
            'CurrMargin': self.__QryTradingAccount['CurrMargin'],  # 占用保证金
            'FrozenMargin': self.__QryTradingAccount['FrozenMargin'],  # 下单冻结
            'Risk': self.__QryTradingAccount['CurrMargin'] / Capital,  # 风险度
            'Deposit': self.__QryTradingAccount['Deposit'],  # 今日入金
            'Withdraw': self.__QryTradingAccount['Withdraw']  # 今日出金
            }
        self.signal_update_panel_show_account.emit(self.__dict_panel_show_account)

    # 保存日志，形参：时间、标题、函数名称、消息主题
    def write_log(self, str_time, str_title, str_function_name, str_msg):
        index_list = ['time', 'str_title', 'function', 'msg']
        s = Series([str_time, str_function_name, str_title, str_msg], index=index_list)
        self.__df_log = DataFrame.append(self.__df_log, other=s, ignore_index=True)

    # 统计User为单位的指标：以合约为单位的开仓手数、撤单次数
    def statistics(self, order=None, trade=None):
        # 根据order统计：撤单次数
        if isinstance(order, dict):
            if len(order['OrderSysID']) == 12 and order['OrderStatus'] == '5':  # 值为5：撤单
                if order['InstrumentID'] in self.__dict_action_counter:  # 字典中已经存在合约代码，值累加1
                    self.__dict_action_counter[order['InstrumentID']] += 1
                else:
                    self.__dict_action_counter[order['InstrumentID']] = 1  # 不存在的合约，撤单次数设置为1
                # 撤单次数赋值到策略对象的合约撤单次数
                for i_strategy in self.__list_strategy:
                    if i_strategy.get_a_instrument_id() == order['InstrumentID']:
                        i_strategy.set_a_action_count(self.__dict_action_counter[order['InstrumentID']])
                    elif i_strategy.get_b_instrument_id() == order['InstrumentID']:
                        i_strategy.set_b_action_count(self.__dict_action_counter[order['InstrumentID']])
        # 根据trade统计：开仓手数
        if isinstance(trade, dict):
            if trade['InstrumentID'] in self.__dict_open_counter:  # 字典中已经存在合约代码，值累加‘Volume’
                self.__dict_open_counter[order['InstrumentID']] += trade['Volume']
            else:
                self.__dict_open_counter[order['InstrumentID']] = trade['Volume']  # 字典中不存在合约代码，创建命名和键值
if __name__ == '__main__':
    print("User.py, if __name__ == '__main__':")
        


