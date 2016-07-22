# -*- coding: utf-8 -*-
"""
Created on Tue Jan 12 00:31:14 2016

@author: Zhuolin
"""

import sys
import threading
import PyCTP
import pandas as pd
from pandas import Series, DataFrame
import FunctionLog


class PyCTP_Market_API(PyCTP.CThostFtdcMdApi):

    TIMEOUT = 30

    __RequestID = 0
    __isLogined = False

    def __IncRequestID(self):
        """ 自增并返回请求ID """
        # self.__RequestID += 1
        return self.__RequestID

    def setInvestorID(self, InvestorID):
        self.__InvestorID = InvestorID
        return self.__InvestorID

    def Connect(self, frontAddr):
        """ 连接前置服务器 """
        self.RegisterSpi(self)
        self.RegisterFront(frontAddr)
        self.Init()
        self.__rsp_Connect = dict(event=threading.Event())
        self.__rsp_Connect['event'].clear()
        return 0 if self.__rsp_Connect['event'].wait(self.TIMEOUT) else -4

    def Login(self, BrokerID, UserID, Password):
        """ 用户登录请求 """
        reqUserLogin = dict(BrokerID    = BrokerID
                            , UserID    = UserID
                            , Password  = Password)
        self.__rsp_Login = dict(event       = threading.Event()
                                , RequestID = self.__IncRequestID())
        ret = self.ReqUserLogin(reqUserLogin, self.__rsp_Login['RequestID'])
        if ret == 0:
            self.__rsp_Login['event'].clear()
            if self.__rsp_Login['event'].wait(self.TIMEOUT):
                if self.__rsp_Login['ErrorID'] == 0:
                    self.__isLogined = True
                    self.__BrokerID = BrokerID
                    self.__UserID   = UserID
                    self.__Password = Password
                else:
                    sys.stderr.write(str(self.__rsp_Login['ErrorMsg'], encoding='gb2312'))
                return self.__rsp_Login['ErrorID']
            else:
                return -4
        return ret

    def Logout(self):
        """ 登出请求 """
        reqUserLogout = dict(BrokerID=self.__BrokerID,
                             UserID=self.__UserID)
        self.__rsp_Logout = dict(event=threading.Event(),
                                 RequestID=self.__IncRequestID())
        ret = self.ReqUserLogout(reqUserLogout, self.__rsp_Logout['RequestID'])
        if ret == 0:
            self.__rsp_Logout['event'].clear()
            if self.__rsp_Logout['event'].wait(self.TIMEOUT):
                if self.__rsp_Logout['ErrorID'] == 0:
                    self.__isLogined = False
                return self.__rsp_Logout['ErrorID']
            else:
                return -4
        return ret

    def SubMarketData(self, InstrumentID):
        """ 订阅行情 """
        self.__rsp_SubMarketData = dict(results=[], ErrorID=0, event=threading.Event(), RequestID=self.__IncRequestID())
        ret = self.SubscribeMarketData(InstrumentID, len(InstrumentID))
        if ret == 0:
            self.__rsp_SubMarketData['event'].clear()
            if self.__rsp_SubMarketData['event'].wait(self.TIMEOUT):
                if self.__rsp_SubMarketData['ErrorID'] != 0:
                    return self.__rsp_SubMarketData['ErrorID']
                return self.__rsp_SubMarketData['results']
            else:
                return -4
        return ret

    def UnSubMarketData(self, InstrumentID):
        """ 退订行情 """
        self.__rsp_UnSubMarketData = dict(results=[], ErrorID=0, event=threading.Event(), RequestID=self.__IncRequestID())
        ret = self.UnSubscribeMarketData(InstrumentID, len(InstrumentID))
        if ret == 0:
            self.__rsp_UnSubMarketData['event'].clear()
            if self.__rsp_UnSubMarketData['event'].wait(self.TIMEOUT):
                if self.__rsp_UnSubMarketData['ErrorID'] != 0:
                    return self.__rsp_UnSubMarketData['ErrorID']
                return self.__rsp_UnSubMarketData['results']
            else:
                return -4
        return ret

    def OnFrontConnected(self):
        """ 当客户端与交易后台建立起通信连接时（还未登录前），该方法被调用。 """
        self.__rsp_Connect['event'].set()

    def OnFrontDisconnected(self, nReason):
        """ 当客户端与交易后台通信连接断开时，该方法被调用。当发生这个情况后，API会自动重新连接，客户端可不做处理。
        nReason 错误原因
        0x1001 网络读失败
        0x1002 网络写失败
        0x2001 接收心跳超时
        0x2002 发送心跳失败
        0x2003 收到错误报文
        """
        sys.stderr.write('前置连接中断: %s' % hex(nReason))
        # 登陆状态时掉线, 自动重登陆
        #if self.__isLogined:
        #    self.__Inst_Interval()
        #    sys.stderr.write('自动登陆: %d' % self.Login(self.__BrokerID, self.__UserID, self.__Password))

    def OnRspUserLogin(self, RspUserLogin, RspInfo, RequestID, IsLast):
        """ 登录请求响应 """
        if RequestID == self.__rsp_Login['RequestID'] and IsLast:
            #self.__BrokerID = RspUserLogin['BrokerID']
            #self.__UserID = RspUserLogin['UserID']
            self.__SystemName = RspUserLogin['SystemName']
            self.__TradingDay = RspUserLogin['TradingDay']
            self.__DCETime = RspUserLogin['DCETime']
            self.__SessionID = RspUserLogin['SessionID']
            self.__MaxOrderRef = RspUserLogin['MaxOrderRef']
            self.__INETime = RspUserLogin['INETime']
            self.__LoginTime = RspUserLogin['LoginTime']
            self.__FrontID = RspUserLogin['FrontID']
            self.__FFEXTime = RspUserLogin['FFEXTime']
            self.__CZCETime = RspUserLogin['CZCETime']
            self.__SHFETime = RspUserLogin['SHFETime']
            self.__rsp_Login.update(RspInfo)
            self.__rsp_Login['event'].set()

    def OnRspUserLogout(self, RspUserLogout, RspInfo, RequestID, IsLast):
        """ 登出请求响应 """
        if RequestID == self.__rsp_Logout['RequestID'] and IsLast:
            self.__rsp_Logout.update(RspInfo)
            self.__rsp_Logout['event'].set()

    def OnRspError(self, RspInfo,  RequestID, IsLast):
        """ 错误信息 """
        sys.stderr.write(repr(([RspInfo['ErrorID'], str(RspInfo['ErrorMsg'], encoding='gb2312')], RequestID, IsLast)))

    def OnRspSubMarketData(self, SpecificInstrument, RspInfo, RequestID, IsLast):
        """ 订阅行情应答 """
        if RequestID == self.__rsp_SubMarketData['RequestID']:
            if RspInfo is not None:
                self.__rsp_SubMarketData.update(RspInfo)
            if SpecificInstrument is not None:
                self.__rsp_SubMarketData['results'].append(SpecificInstrument)
            if IsLast:
                self.__rsp_SubMarketData['event'].set()

    def OnRspUnSubMarketData(self, SpecificInstrument, RspInfo, RequestID, IsLast):
        """ 取消订阅行情应答 """
        if RequestID == self.__rsp_UnSubMarketData['RequestID']:
            if RspInfo is not None:
                self.__rsp_UnSubMarketData.update(RspInfo)
            if SpecificInstrument is not None:
                self.__rsp_UnSubMarketData['results'].append(SpecificInstrument)
            if IsLast:
                self.__rsp_UnSubMarketData['event'].set()

    def OnRtnDepthMarketData(self, DepthMarketData):
        """ 行情推送 """
        pass


class PyCTP_Market(PyCTP_Market_API):

    data = []  # type is list
    df_data_columns_name = ['InstrumentID', 'time', 'last', 'volume', 'amount', 'position', 'ask1', 'bid1', 'asize1', 'bsize1']
    df_data = DataFrame(columns=df_data_columns_name, data=None)

    def OnRtnDepthMarketData(self, DepthMarketData):
        import datetime
        tick = dict(InstrumentID=str(DepthMarketData['InstrumentID'], 'gb2312')
                    , time=datetime.datetime.strptime(str(DepthMarketData['ActionDay']+DepthMarketData['UpdateTime'], 'gb2312'), '%Y%m%d%H:%M:%S').replace(microsecond=DepthMarketData['UpdateMillisec']*1000)
                    , last=DepthMarketData['LastPrice']
                    , volume=DepthMarketData['Volume']
                    , amount=DepthMarketData['Turnover']
                    , position=DepthMarketData['OpenInterest']
                    , ask1=DepthMarketData['AskPrice1']
                    , bid1=DepthMarketData['BidPrice1']
                    , asize1=DepthMarketData['AskVolume1']
                    , bsize1=DepthMarketData['BidVolume1'])
        self.data.append(tick)
        PyCTP_Market.df_data = self.df_data.append(other=Series(tick), ignore_index=True, verify_integrity=False)
        # print('tick:', tick)
        # print('line 607>>>type(data):', type(self.data), len(self.data))
        # print('line 609>>>type(df_data):', type(self.df_data), len(self.df_data))
        # s1 = Strategy()
        # Strategy.strategy_1()
        # s1.strategy_2(1, 2)

