
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import sys
import re
import serial
import time

class Modem(object):

    def __init__(self):
        self.ser = None
        
    def Open(self,port):
        ret = True
        try:
            self.ser = serial.Serial(port, 460800,parity=serial.PARITY_NONE,stopbits=serial.STOPBITS_ONE,timeout=0,xonxoff=False)
        except:
            ret = False
        return ret
    
    def SendCmd(self,command):
        loc = QMutex()
        loc.lock()
        self.ser.write(command)
        loc.unlock()
        time.sleep(1)
        
    def initMode(self):
        self.SendCmd('AT+CMGF=1\r')
        
    def Read(self):
        data = self.ser.readline()
        return data
    
    def DeleteSMS(self,index):
        self.index = index
        cmd = "AT+CMGD=" + index+ "\r\n"
        self.SendCmd(cmd)
        
    def SendSMS(self, recipient, message):
        cmd = 'AT+CMGS='+ recipient+'\r\n'+ message + '\r\n'
        self.SendCmd(cmd)
        self.SendCmd(chr(26))
        
    def Close(self):
        if self.ser is not None:
            self.ser.close()
            
    def AllSMS(self):
        self.ser.flushInput()
        self.ser.flushOutput()
        command = 'AT+CMGL="REC UNREAD"\r\n'
        self.SendCmd(command)
        data = self.ser.readall()
        return data
    
class Message:
    def __init__(self,ID,sender,msg):
        self.ID = ID
        self.sender = sender
        self.msg = msg

class Thread(QThread):

    data = pyqtSignal(object)
    Terr = pyqtSignal(object)

    def __init__(self, text):
        QThread.__init__(self)
        self.cport = text
        
    def run(self):
        self.M = Modem()
        if not self.M.Open(self.cport):
            self.Terr.emit("%s"%"Unable to open modem")
            return
        self.M.initMode()
        while True:
            #self.M.SendSMS('"144"','BAL')
            data = self.M.AllSMS()
            data = data.replace('AT+CMGF=1',"")
            data = data.replace('AT+CMGL="REC UNREAD"',"")
            data = data.replace('OK',"")
            for z in self.Separate(data):
                self.ret = self.Process(z)
                if self.ret:
                    self.data.emit("%s\n%s %s\n" % (self.ret.ID,self.ret.sender,self.ret.msg))
                    self.M.DeleteSMS(self.ret.ID)
            #time.sleep(0.1)
            
    def Process(self,text):
        T = text.split(",")
        self.tmp = text
        p = re.search(r'("\+\d+"\r\n?.*|"[a-zA-Z]+"\r\n?.*)',self.tmp)
        if p is not None:
            g3 = p.group()
            sender = re.search(r'("\+\d+"\r|"[a-zA-Z]+"\r)',g3).group()
            sender = sender[:-1]
            msg = g3.replace(sender,"")
            SMS = Message(T[0],sender,msg)
            return SMS
        else:
            return None
        
    def Separate(self,text):
        L = text.split("+CMGL:")
        return L
        
    def __del__(self):
        self.M.Close()
    
class Form(QWidget):
    def __init__(self,parent=None):
        super(Form,self).__init__(parent)
        x = self.loadFile('config.txt')
        if len(x) != 0:
            self.cport = x
        else:
            QMessageBox.warning(self,"Err","Empty Settings file:config.txt")
            exit(0)
        self.browser = QTextBrowser()
        self.linedit = QLineEdit()
        self.label = QLabel("       ")
        self.button = QPushButton("Start")
        self.xbutton = QPushButton("Stop")
        self.hbox = QHBoxLayout()
        self.hbox.addWidget(self.button)
        self.hbox.addWidget(self.label)
        self.hbox.addWidget(self.xbutton)
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.browser)
        self.layout.addLayout(self.hbox)
        self.setLayout(self.layout)
        self.setWindowTitle("SMS Tool -by ASHKEN")
        self.button.clicked.connect(self.doPrime)
        self.connect(self.xbutton,SIGNAL("clicked()"),self.Stop)
        self.xbutton.setEnabled(False)
        self.L = []
        
    def doPrime(self):
        self.button.setEnabled(False)
        self.xbutton.setEnabled(True)
        T = Thread(self.cport)
        T.data.connect(self.on_ready)
        T.Terr.connect(self.on_terr)
        self.L.append(T)
        T.start()
    
    def Stop(self):
        for x in self.L:
            x.M.Close()
            x.terminate()
            print "Terminated"
        self.L = []
        self.button.setEnabled(True)
        
    def on_ready(self, data):
        self.browser.append(unicode(data))
        
    def on_terr(self,terr):
        QMessageBox.warning(self,"Error",unicode(terr))
        self.xbutton.setEnabled(False)
        self.Stop()
        
    def loadFile(self,se_file):
        f = None
        try:
            f = file(se_file).read()
        except:
            QMessageBox.warning(self,"Err","Error reading Settings file:config.txt")
            exit(0)
        return f
        
        
if __name__ == '__main__':
    
    app = QApplication(sys.argv)
    form = Form()
    form.show()
    app.exec_()
