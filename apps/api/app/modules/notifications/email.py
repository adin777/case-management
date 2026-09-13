import smtplib
from email.message import EmailMessage
from typing import Protocol


class EmailProvider(Protocol):
    def send(self,recipient:str,subject:str,body:str)->str|None: ...


class ConsoleEmailProvider:
    """Safe development provider; it performs no network I/O."""
    def send(self,recipient:str,subject:str,body:str)->str:
        return f"console:{recipient}"


class FakeEmailProvider:
    def __init__(self,fail:bool=False):self.fail=fail;self.sent:list[tuple[str,str,str]]=[]
    def send(self,recipient:str,subject:str,body:str)->str:
        if self.fail:raise RuntimeError("simulated email failure")
        self.sent.append((recipient,subject,body));return f"fake-{len(self.sent)}"


class SmtpEmailProvider:
    def __init__(self,host:str,port:int,from_address:str,username:str|None=None,password:str|None=None,use_tls:bool=True):
        self.host=host;self.port=port;self.from_address=from_address;self.username=username;self.password=password;self.use_tls=use_tls

    def send(self,recipient:str,subject:str,body:str)->str|None:
        message=EmailMessage();message["From"]=self.from_address;message["To"]=recipient;message["Subject"]=subject;message.set_content(body)
        with smtplib.SMTP(self.host,self.port,timeout=10) as client:
            if self.use_tls:client.starttls()
            if self.username:client.login(self.username,self.password or "")
            client.send_message(message)
        return message.get("Message-ID")
