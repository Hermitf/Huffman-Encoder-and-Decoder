from PyQt5 import QtGui
from PyQt5.QtWidgets import *
from PyQt5.uic import loadUi
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtSvg import *
from typing import Dict, List
from graphviz import Digraph
import sys
import os
import socket
import re
import threading
import multiprocessing


class TreeNode:
    parent: 'TreeNode' = None  # 父节点
    lchild: 'TreeNode' = None  # 左节点
    rchild: 'TreeNode' = None  # 右节点
    weight: float = None  # 权重，即字频
    name: str = None  # 名称，即字符

    def __init__(self, name=None, weight=None) -> None:
        self.name = name
        self.weight = weight


class HuffmanTree:
    rootnode: TreeNode = None  # 根节点
    nodes: List[TreeNode] = None  # 各节点组成的列表
    characterset: Dict[str, float] = None  # 字符集构成的字典

    def __init__(self, characterset: Dict[str, float]):
        if characterset == {} or characterset == None:  # 若字符集为空或者无字符集 则直接返回不对树进行构造
            return
        # 建树，先将其写于一个列表list中
        nodes: List[TreeNode] = [TreeNode(key, value) for key, value in characterset.items()] +\
                                [TreeNode()
                                 for _ in range(len(characterset)-1)]
        for i in range(len(characterset), len(nodes)):
            x = self.select(i, nodes)
            nodes[x].parent = nodes[i]
            y = self.select(i, nodes)
            nodes[y].parent = nodes[i]
            nodes[i].lchild = nodes[x]
            nodes[i].rchild = nodes[y]
            nodes[i].weight = nodes[x].weight+nodes[y].weight
        self.rootnode = nodes[-1]
        self.nodes = nodes
        self.characterset = characterset

    def select(self, k: int, nodes: List[TreeNode]) -> int:
        # 在nodes中寻找前k个数中，无父节点且权值最小的节点，并返回最小值
        x: int = None
        for i in range(k):
            if not nodes[i].parent:  # 若找到第一个无父节点的节点，并用x标记
                x = i
                break
        for j in range(x, k):  # 在第x结点以后
            if nodes[j].weight < nodes[x].weight and not nodes[j].parent:
                x = j
                break
        return x

    def encode(self, text: str) -> str:
        # 对text中的文本进行编码
        p, q = '', ''  # p是每个字符的编码，q是整篇文章的编码
        for i in text:
            for j in self.nodes:
                if i == j.name:
                    while j.parent:
                        if j.parent.lchild == j:
                            p += '0'
                        elif j.parent.rchild == j:
                            p += '1'
                        j = j.parent
                    q += p[::-1]
                    p = ''
                    break
            else:
                # 若当前字符并不在字符集中，则返回空的密文
                return None
        return q

    def decode(self, text: str) -> str:
        # 在树中对text中的01串进行解码
        root: TreeNode = self.rootnode
        result = ""
        for i in text:
            if i == '0':
                root = root.lchild
            elif i == '1':
                root = root.rchild
            elif i == '\n':  # 紧凑格式中的'\n'需忽略
                continue
            else:
                return None
            if root.name:
                result += root.name
                root = self.rootnode
        if root != self.rootnode:
            return None
        else:
            return result

    def printTree(self, filename=None):
        # 生成树的图片
        dot = Digraph(comment="生成的树")
        dot.attr('node', fontname="STXinwei", shape='circle', fontsize="20")
        for i, j in enumerate(self.nodes):
            if j.name == '' or not j.name:
                dot.node(str(i), '')
            elif j.name == ' ':
                dot.node(str(i), '[ ]')  # 空格显示为'[ ]'
            elif j.name == '\n':
                dot.node(str(i), '\\\\n')  # 换行符显示为'\n' 转义 此处的还会被调用，因此需要四个斜杠
            elif j.name == '\t':
                dot.node(str(i), '\\\\t')  # 制表符显示为'\t'
            else:
                dot.node(str(i), j.name)
        dot.attr('graph', rankdir='LR')
        for i in self.nodes[::-1]:
            if not (i.rchild or i.lchild):
                break
            if i.lchild:
                dot.edge(str(self.nodes.index(i)), str(
                    self.nodes.index(i.lchild)), '0', constraint='true')
            if i.rchild:
                dot.edge(str(self.nodes.index(i)), str(
                    self.nodes.index(i.rchild)), '1', constraint='true')
        
        dot.render(filename, view=False, format='svg', cleanup=True)


def checkDecodedText(text: str) -> bool:
    # 检查密文内容的合法性
    for i in text:
        if i not in ['0', '1', '\n']:
            return False
    return True


rawTextEdit: QTextEdit = None  # 原文所在的文本框
encodedTextEdit: QTextEdit = None  # 密文所在文本框
HFTree: HuffmanTree = None  # 哈夫曼树
CharacterSet = {}  # 字符集
showSVGWidget: "ShowSVGWidget" = None  # 显示svg的控件
paintTreeWindow:"PaintTreeWindow"=None
charsetWindow:"CharsetWindow"=None

class MainWindow(QWidget):
    encodedTextEdit: QTextEdit

    def __init__(self):
        super().__init__()
        loadUi("ui/main.ui", self)  # 加载了窗体中的各个控件
        self.setWindowIcon(QIcon("ui/icon.ico"))
        global rawTextEdit
        rawTextEdit = self.rawTextEdit
        global encodedTextEdit
        encodedTextEdit = self.encodedTextEdit
        self.rawSaveFileButton.clicked.connect(self.saveRawTextContent)
        self.encodedSaveFileButton.clicked.connect(self.saveEncodedTextContent)
        self.rawOpenFileButton.clicked.connect(self.encodeFileReadin)
        self.encodedOpenFileButton.clicked.connect(self.decodeFileReadin)
        self.pushButton.clicked.connect(lambda: QMessageBox.about(
            self, "关于作者", "姓名：孙斓绮\n学校：浙江理工大学\n日期：2021.6"))
        self.compactFormatButton.clicked.connect(self.compactFormPrint)
        self.encodedButton.clicked.connect(self.encoding)
        self.decodeButton.clicked.connect(self.decoding)

    def saveRawTextContent(self):
        filePath, ok = QFileDialog.getSaveFileName(self, '选择文件')
        if ok:
            with open(filePath, 'w', encoding='utf-8') as file:
                file.write(self.rawTextEdit.toPlainText())

    def saveEncodedTextContent(self):
        if not checkDecodedText(self.encodedTextEdit.toPlainText()):
            QMessageBox.critical(self, "错误", "存在无效字符", QMessageBox.Ok)
            return
        filePath, ok = QFileDialog.getSaveFileName(self, '选择文件')
        if ok:
            with open(filePath, 'w', encoding='utf-8') as file:
                file.write(self.encodedTextEdit.toPlainText())

    def encodeFileReadin(self):
        filePath, ok = QFileDialog.getOpenFileName(self, '选择文件')
        if ok:
            with open(filePath, 'r', encoding='utf-8') as file:
                try:
                    text = file.read()
                except UnicodeDecodeError:
                    QMessageBox.critical(
                        self, "错误", "请确保打开的是UTF-8编码的文本文件", QMessageBox.Ok)
                    return
            self.rawTextEdit.setText(text)

    def decodeFileReadin(self):
        filePath, ok = QFileDialog.getOpenFileName(self, '选择文件')
        if ok:
            with open(filePath, 'r', encoding='utf-8') as file:
                try:
                    encodedTextEdit = file.read()
                except UnicodeDecodeError:
                    QMessageBox.critical(
                        self, "错误", "请确保打开的是UTF-8编码的文本文件", QMessageBox.Ok)
                    return
            if not checkDecodedText(encodedTextEdit):
                QMessageBox.critical(self, "错误", "存在无效字符", QMessageBox.Ok)
                return
            self.encodedTextEdit.setText(encodedTextEdit)

    def compactFormPrint(self):
        Text = self.encodedTextEdit.toPlainText()
        text = ''
        m = 50
        for i in Text.replace('\n', ''):
            text += i
            m -= 1
            if m == 0:
                text += '\n'
                m = 50
        self.encodedTextEdit.setPlainText(text)

    def encoding(self):
        if not HFTree:
            QMessageBox.critical(self, "错误", "当前无建好的树", QMessageBox.Ok)
        elif rawTextEdit.toPlainText() == '':
            QMessageBox.critical(self, "错误", "请输入原文", QMessageBox.Ok)
        else:
            t = HFTree.encode(rawTextEdit.toPlainText())
            if not t:
                QMessageBox.critical(self, "错误", "存在无效字符", QMessageBox.Ok)
                return
            self.encodedTextEdit.setText(t)

    def decoding(self):
        if not HFTree:
            QMessageBox.critical(self, "错误", "当前无建好的树", QMessageBox.Ok)
        elif self.encodedTextEdit.toPlainText() == '':
            QMessageBox.critical(self, "错误", "请输入密文", QMessageBox.Ok)
        else:
            t = HFTree.decode(self.encodedTextEdit.toPlainText())
            if not t:
                QMessageBox.critical(self, "错误", "存在无效字符", QMessageBox.Ok)
                return
            self.rawTextEdit.setText(t)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        try:
            os.remove("tmp.svg")
        except FileNotFoundError:
            pass
        sys.exit()


class DoubleDelegate(QItemDelegate):
    # 限制只能输入浮点类型的数

    def createEditor(self, parent: QWidget, option: 'QStyleOptionViewItem', index: QModelIndex) -> QWidget:
        edit = QLineEdit(parent)
        v = QDoubleValidator(parent)
        v.setBottom(0)
        edit.setValidator(v)
        return edit


class OneCharDelegate(QItemDelegate):
    # 限制只能输入单个字符

    def createEditor(self, parent: QWidget, option: 'QStyleOptionViewItem', index: QModelIndex) -> QWidget:
        edit = QLineEdit(parent)
        v = QRegExpValidator(parent)
        v.setRegExp(QRegExp(r'.'))
        edit.setValidator(v)
        return edit


class CharsetWindow(QWidget):
    tableWidget: QTableWidget

    def __init__(self):
        super().__init__()
        loadUi("ui/charset.ui", self)
        self.tableWidget.setItemDelegateForColumn(0, OneCharDelegate(self))
        self.tableWidget.setItemDelegateForColumn(1, DoubleDelegate(self))
        self.setWindowIcon(QIcon("ui/icon.ico"))
        self.addButton.clicked.connect(self.add)
        self.findButton.clicked.connect(self.find)
        self.deleteButton.clicked.connect(
            lambda: self.tableWidget.removeRow(self.tableWidget.currentRow()))
        self.inputWordFrequencyButton.clicked.connect(self.importWordFrequency)
        self.saveButton.clicked.connect(self.saveWordFrequency)
        self.generateButton.clicked.connect(
            self.generateCharacterSetFromRawtext)
        # 限定输入lineedit的输入为一个字符
        self.wordFrequencyEdit.setValidator(
            QRegExpValidator(QRegExp(r'.'), self))
        d = QDoubleValidator(self)
        d.setBottom(0)
        self.frequencyEdit.setValidator(d)

    def showEvent(self, e):
        if HFTree:  # 如果存在树，就根据现有的树生成字符集
            self.tableWidget.clearContents()
            self.tableWidget.setRowCount(0)
            global CharacterSet
            for i, j in CharacterSet.items():
                self.add()
                item1 = QTableWidgetItem(i)
                item2 = QTableWidgetItem(str(j))
                self.tableWidget.setItem(
                    self.tableWidget.rowCount()-1, 0, item1)
                self.tableWidget.setItem(
                    self.tableWidget.rowCount()-1, 1, item2)

    def add(self):
        # 加入一空行
        self.tableWidget.insertRow(self.tableWidget.rowCount())

    def find(self):
        # 对于字符或字频或字符与字频进行查找
        a: str = self.wordFrequencyEdit.text()
        b: str = self.frequencyEdit.text()
        i: int = 0
        if a and b:
            while i < self.tableWidget.rowCount():
                if self.tableWidget.item(i, 0).text() == a and self.tableWidget.item(i, 1).text() == b:
                    self.resultLabel.setText(str(i+1))
                    break
                i += 1
        elif not a and b:
            while i < self.tableWidget.rowCount():
                if self.tableWidget.item(i, 1).text() == b:
                    self.resultLabel.setText(str(i+1))
                    break
                i += 1
        elif a and not b:
            while i < self.tableWidget.rowCount():
                if self.tableWidget.item(i, 0) and self.tableWidget.item(i, 0).text() == a:
                    self.resultLabel.setText(str(i+1))
                    break
                i += 1
        if i == self.tableWidget.rowCount():
            self.resultLabel.setText("未找到")

    def importWordFrequency(self):
        # 导入字频
        filePath, ok = QFileDialog.getOpenFileName(self, '选择文件')
        if ok:
            self.tableWidget.clearContents()
            self.tableWidget.setRowCount(0)
            with open(filePath, 'r', encoding='utf-8') as file:
                try:
                    frequency = file.read()
                except UnicodeDecodeError:
                    QMessageBox.critical(
                        self, "错误", "请确保打开的是UTF-8编码的文本文件", QMessageBox.OK)
                    return
            global CharacterSet
            CharacterSet = {}
            textlines = re.findall(r'([\s\S])\t(\S+)(\n|$)', frequency)
            if len(textlines) == 0:
                QMessageBox.critical(self, "错误", "字符集生成失败", QMessageBox.Ok)
                return
            for i, j, _ in textlines:
                try:
                    CharacterSet[i] = float(j)
                except ValueError:
                    QMessageBox.critical(
                        self, "错误", "字符集生成失败", QMessageBox.Ok)
                    self.tableWidget.clearContents()
                    self.tableWidget.setRowCount(0)
                    CharacterSet = {}
                    return
                self.add()
                item1 = QTableWidgetItem(i)
                item2 = QTableWidgetItem(j)
                self.tableWidget.setItem(
                    self.tableWidget.rowCount()-1, 0, item1)
                self.tableWidget.setItem(
                    self.tableWidget.rowCount()-1, 1, item2)

    def saveWordFrequency(self):
        # 保存文件
        filePath, ok = QFileDialog.getSaveFileName(self, '选择文件')
        if ok:
            with open(filePath, 'w', encoding='utf-8') as file:
                for i in range(self.tableWidget.rowCount()):
                    m = '\t'.join([self.tableWidget.item(
                        i, 0).text(), self.tableWidget.item(i, 1).text()])
                    file.write(m+'\n')

    def generateCharacterSetFromRawtext(self):
        # 根据原文生成字符集
        self.tableWidget.clearContents()
        self.tableWidget.setRowCount(0)
        def getFrequency(text: str) -> dict:
            # 字频(统计)
            cnt = {}
            for i in text:
                if i not in cnt:
                    cnt[i] = 1
                else:
                    cnt[i] += 1
            return cnt
        CharacterSet = getFrequency(rawTextEdit.toPlainText())
        for i, j in CharacterSet.items():
            self.add()
            item1 = QTableWidgetItem(i)
            item2 = QTableWidgetItem(str(j))
            self.tableWidget.setItem(self.tableWidget.rowCount()-1, 0, item1)
            self.tableWidget.setItem(self.tableWidget.rowCount()-1, 1, item2)

    def closeEvent(self, event):
        # 关闭窗体
        if self.tableWidget.rowCount() == 0:
            return
        global CharacterSet
        CharacterSet = {}
        # 将表格中的字符集存入变量CharacterSet中
        for i in range(self.tableWidget.rowCount()):
            if self.tableWidget.item(i, 0) and self.tableWidget.item(i, 1):
                try:
                    CharacterSet[self.tableWidget.item(i, 0).text()] = float(
                        self.tableWidget.item(i, 1).text())
                except:
                    pass
        global HFTree
        # 将树依据现有的字符集进行更新
        if CharacterSet != {}:
            HFTree = HuffmanTree(CharacterSet)
            global showSVGWidget
            if showSVGWidget:
                HFTree.printTree('tmp')
                showSVGWidget.update()
                paintTreeWindow.printInform()


class NetTransportWindow(QWidget):
    s: socket.socket = None
    lineEdit: QLineEdit  # 服务端端口输入框
    connectIpEditText: QLineEdit  # 客户端IP输入框
    connectPortEditText: QLineEdit  # 客户端端口输入框
    setEncodedTextSign = pyqtSignal(str)  # 修改的密文框信号

    def __init__(self):
        super().__init__()
        loadUi("ui/network.ui", self)
        self.setWindowIcon(QIcon("ui/icon.ico"))
        # 查看本机IP
        self.showIpButton.clicked.connect(lambda: QMessageBox.information(self, '查看本机IP', socket.gethostbyname(
            socket.gethostname()), QMessageBox.Ok))
        self.startServerButton.clicked.connect(self.buildServerConnection)
        self.connectButton.clicked.connect(self.buildClientConnection)
        self.sendTreeButton.clicked.connect(self.sendTree)
        self.sendTextButton.clicked.connect(self.sendText)
        self.setEncodedTextSign.connect(self.setEncodedText)
        self.breakButton.clicked.connect(self.breakConnection)
        # 服务器端端口号输入限制
        self.lineEdit.setValidator(QRegExpValidator(QRegExp(
            r'((6553[0-5])|[655[0-2][0-9]|65[0-4][0-9]{2}|6[0-4][0-9]{3}|[1-5][0-9]{4}|[1-9][0-9]{3}|[1-9][0-9]{2}|[1-9][0-9]|[0-9])'), self))
        # 客户端端端口号输入限制
        self.connectPortEditText.setValidator(QRegExpValidator(QRegExp(
            r'((6553[0-5])|[655[0-2][0-9]|65[0-4][0-9]{2}|6[0-4][0-9]{3}|[1-5][0-9]{4}|[1-9][0-9]{3}|[1-9][0-9]{2}|[1-9][0-9]|[0-9])'), self))
        # 客户端ip地址输入限制
        self.connectIpEditText.setValidator(QRegExpValidator(QRegExp(
            r'((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])[\\.]){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])'), self))

    def buildServerConnection(self):
        # 服务端监听端口
        try:
            # 获取端口号
            port = int(self.lineEdit.text())
        except ValueError:
            QMessageBox.critical(self, "错误", "当前无已输入的端口号", QMessageBox.Ok)
            return
        # 建立一个套接字
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # 设置监听端口并监听
            s.bind(("0.0.0.0", port))
            s.listen()
        except OSError:
            QMessageBox.critical(self, "错误", "端口已被占用", QMessageBox.Ok)
            return
        # 等待客户端连接
        self.stateLabel.setText("等待连接")
        # 开启一个新的线程用于等待连接，防止程序阻塞，并利用daemon标记，以便于主线程结束时，自动结束带有此标记的所有线程
        threading.Thread(target=self.handleClient,
                         args=[s], daemon=True).start()

    def handleClient(self, s: socket.socket):
        # 服务器端等待连接
        c = s.accept()[0]
        self.stateLabel.setText("已连接")
        self.s = c
        # 启动等待接收的线程
        threading.Thread(target=self.waitRecv, args=[c], daemon=True).start()

    def buildClientConnection(self):
        # 客户端建立连接
        try:
            # 获取IP地址
            ip = self.connectIpEditText.text()
            if ip == None:
                QMessageBox.critical(
                    self, "错误", "当前无已输入的IP地址", QMessageBox.Ok)
                return
            port = int(self.connectPortEditText.text())
        except ValueError:
            QMessageBox.critical(self, "错误", "当前无已输入的端口号", QMessageBox.Ok)
            return
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((ip, port))
        except ConnectionRefusedError:
            QMessageBox.critical(self, "错误", "连接失败", QMessageBox.Ok)
            return
        except OSError:
            QMessageBox.critical(self, "错误", "IP或端口错误", QMessageBox.Ok)
            return
        self.stateLabel.setText("已连接")
        self.s = s
        # 连接成功，启动等待接收的线程
        threading.Thread(target=self.waitRecv, args=[s], daemon=True).start()

    def sendTree(self):
        # 发送树
        if not self.s:
            QMessageBox.critical(self, "错误", "请先建立连接", QMessageBox.Ok)
            return
        global CharacterSet
        if not CharacterSet or not HFTree:
            QMessageBox.critical(self, "错误", "当前树为空", QMessageBox.Ok)
            return
        content = 't'  # 发送树的标志
        for i, j in CharacterSet.items():
            content += i+"\t"+str(j)+'\n'
        # 将其转化为Byte进行发送
        self.s.sendall(content.encode())
        QMessageBox.information(self, "提示", "发送成功", QMessageBox.Ok)

    def sendText(self):
        # 发送密文
        if not self.s:
            QMessageBox.critical(self, "错误", "请先建立连接", QMessageBox.Ok)
            return
        global encodedTextEdit
        content = encodedTextEdit.toPlainText()
        if not checkDecodedText(content):
            QMessageBox.critical(self, "错误", "存在无效字符", QMessageBox.Ok)
            return
        self.s.sendall(('c'+content).encode())
        QMessageBox.information(self, "提示", "发送成功", QMessageBox.Ok)

    def setEncodedText(self, text):
        # 将接收到的密文输入到文本框中
        global encodedTextEdit
        encodedTextEdit.setText(text)

    def waitRecv(self, s: socket.socket):
        # 等待接受线程
        try:
            while True:
                data = s.recv(10000000)
                # 将内容转变为str类型
                data = data.decode()
                if data[0] == 't':
                    data = data[1:]
                    textlines = re.findall(r'([\s\S])\t(\S+)(\n|$)', data)
                    global CharacterSet
                    CharacterSet = {}
                    for i, j, _ in textlines:
                        try:
                            CharacterSet[i] = float(j)
                        except ValueError:
                            self.stateLabel.setText("接收到无用数据")
                            self.tableWidget.clearContents()
                            self.tableWidget.setRowCount(0)
                            CharacterSet = {}
                            return
                    global HFTree
                    if CharacterSet != {}:
                        HFTree = HuffmanTree(CharacterSet)
                        self.stateLabel.setText("已收到树")
                    else:
                        self.stateLabel.setText("收到空树")
                elif data[0] == 'c':
                    self.stateLabel.setText("已收到密文")
                    data = data[1:]
                    self.setEncodedTextSign.emit(data)
                else:
                    self.stateLabel.setText("接收到无用数据")
        except ConnectionResetError:  # 对方断开
            self.stateLabel.setText("连接断开")
            self.s = None
        except ConnectionAbortedError:  # 自己断开
            pass

    def breakConnection(self):
        # 断开连接按钮事件
        try:
            self.s.close()
            self.s = None
            self.stateLabel.setText("未连接")
        except:
            pass


class PaintTreeWindow(QWidget):
    # 显示树的窗体
    height: int = 0
    CharacterSet = {}
    paintingLayout: QVBoxLayout

    def __init__(self):
        super().__init__()
        loadUi("ui/tree.ui", self)
        self.setWindowIcon(QIcon("ui/icon.ico"))
        self.findCodeButton.clicked.connect(charsetWindow.show)
        self.saveButton.clicked.connect(self.savetree)
        self.loadButton.clicked.connect(self.importtree)
        global showSVGWidget
        showSVGWidget = ShowSVGWidget(self)
        self.paintingLayout.addWidget(showSVGWidget)

    def showEvent(self, e):
        # 打开时刷新树的图片
        if not HFTree:
            QMessageBox.critical(self, "错误", "当前无建好的树", QMessageBox.Ok)

    def TreeDepth(self, pRoot: HuffmanTree):
        # 计算树的深度
        def currentTreeDepth(pRoot: TreeNode):
            if pRoot is None:
                return 0
            if pRoot.lchild or pRoot.rchild:
                return max(currentTreeDepth(pRoot.lchild), currentTreeDepth(pRoot.rchild))+1
            else:
                return 1
        return currentTreeDepth(pRoot.rootnode)

    def printInform(self):
        # 更新树的信息
        self.treeHeightlabel.setText(str(self.TreeDepth(HFTree)))
        self.nodeCountlabel.setText(str(len(HFTree.characterset)*2-1))
        self.leafCountlabel.setText(str(len(HFTree.characterset)))

    def importtree(self):
        # 将树的信息导入到图片中
        filePath, ok = QFileDialog.getOpenFileName(self, '选择文件')
        if ok:
            with open(filePath, 'r', encoding='utf-8') as file:
                try:
                    text = file.read()
                except UnicodeDecodeError:
                    QMessageBox.critical(
                        self, "错误", "请确保打开的是UTF-8编码的文本文件", QMessageBox.Ok)
                    return
            global CharacterSet
            CharacterSet = self.CharacterSet
            textlines = re.findall(r'([\s\S])\t(\S+)\t\S+(\n|$)', text)
            # 导入后重置字符集信息，并更新内存中的树
            for i, j, _ in textlines:
                CharacterSet[i] = float(j)
            global HFTree
            if CharacterSet != {}:
                HFTree = HuffmanTree(CharacterSet)
                global showSVGWidget
                HFTree.printTree('tmp')
                showSVGWidget.update()
                self.printInform()  # 将树的信息写在面板上

    def savetree(self):
        # 保存树的信息
        filePath, ok = QFileDialog.getSaveFileName(self, '选择文件')
        if ok:
            with open(filePath, 'w', encoding='utf-8') as file:
                for i, j in HFTree.characterset.items():
                    m = '\t'.join([i, str(j), HFTree.encode(i)])
                    file.write(m+'\n')


class ShowSVGWidget(QWidget):
    # 自定义控件，显示svg图片
    leftClick: bool
    svgrender: QSvgRenderer
    defaultSize: QSizeF
    point: QPoint
    scale = 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        # 构造一张空白的svg图像
        self.svgrender = QSvgRenderer(
            b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 0 0"  width="512pt" height="512pt"></svg>')
        # 获取图片默认大小
        self.defaultSize = QSizeF(self.svgrender.defaultSize())
        self.point = QPoint(0, 0)
        self.scale = 1

    def update(self):
        # 更新图片
        self.svgrender = QSvgRenderer("tmp.svg")
        self.defaultSize = QSizeF(self.svgrender.defaultSize())
        self.point = QPoint(0, 0)
        self.scale = 1
        self.repaint()

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        # 绘画事件(回调函数)
        painter = QPainter()  # 画笔
        painter.begin(self)
        self.svgrender.render(painter, QRectF(
            self.point, self.defaultSize*self.scale))  # svg渲染器来进行绘画，(画笔，QRectF(位置，大小))(F表示float)
        painter.end()

    def mouseMoveEvent(self, a0: QtGui.QMouseEvent) -> None:
        # 鼠标移动事件(回调函数)
        if self.leftClick:
            self.endPos = a0.pos()-self.startPos
            self.point += self.endPos
            self.startPos = a0.pos()
            self.repaint()

    def mousePressEvent(self, a0: QtGui.QMouseEvent) -> None:
        # 鼠标点击事件(回调函数)
        if a0.button() == Qt.LeftButton:
            self.leftClick = True
            self.startPos = a0.pos()

    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent) -> None:
        # 鼠标释放事件(回调函数)
        if a0.button() == Qt.LeftButton:
            self.leftClick = False

    def wheelEvent(self, a0: QtGui.QWheelEvent) -> None:
        # 根据光标所在位置进行图像缩放
        oldScale = self.scale
        if a0.angleDelta().y() > 0:
            # 放大
            if self.scale <= 5.0:
                self.scale *= 1.1
        elif a0.angleDelta().y() < 0:
            # 缩小
            if self.scale >= 0.2:
                self.scale *= 0.9
        self.point = a0.pos()-(self.scale/oldScale*(a0.pos()-self.point))
        self.repaint()


# if __name__ == '__main__':
multiprocessing.freeze_support()
app = QApplication(sys.argv)
mainWindow = MainWindow()
charsetWindow = CharsetWindow()
nettansportWindow = NetTransportWindow()
paintTreeWindow = PaintTreeWindow()
mainWindow.show()
mainWindow.editFrequencyButton.clicked.connect(charsetWindow.show)
mainWindow.networkTransportButton.clicked.connect(nettansportWindow.show)
mainWindow.paintTreeButton.clicked.connect(paintTreeWindow.show)
sys.exit(app.exec_())

# 打包命令:①有点问题 pyinstaller -F 哈夫曼编译码器.py --workpath C:\Users\admin\Desktop\哈夫曼编译码器\源文件  --distpath C:\Users\admin\Desktop\哈夫曼编译码器 --icon="ui\mainicon.ico" --noconsole
        # ② cxfreeze .\Huffman_decoding_device.py --base-name=win32gui --icon='ui/mainicon.ico'