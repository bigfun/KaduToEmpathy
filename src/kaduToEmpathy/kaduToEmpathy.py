#-*- coding: utf-8 -*-
'''
Created on 2010-05-17

@author: bigfun
@summary: Skrypt kopiujacy archiwum rozmów gadu-gadu z programu Kadu do programu empathy
@version: 0.1
@bug: Najprawdopodbniej nie obsluguje nazw kontaktow zawierajacych przecinek
'''

from xml.dom import minidom
import sys 
import os
import re
import time
from optparse import OptionParser


# Klasa przechowująca pojedyńczą wiadomość odczytaną z pliku archiwum kadu
class Message:
    contactId = "" # numer gg
    contactName = "" # nazwa kontaktu na liście kontaktów w gadu gadu
    messageContent = "" # tresc wiadomosci
    messageDate = "" # data wiadomosci 
    messageTime = time.time() # godzina wysłania wiadomości
    userMsg = True # jesli prawda, wiadomosc zostala wyslana przez wlasciciela archiwum
    cmIdCounter = 0 # licznik pomocniczy dla empathy

#funkcja obslugujaca parametry wykonania skryptu
def get_params():
    parser = OptionParser()
    parser.add_option("-n", "--numer", dest="ggId", metavar="numer_gg",
                      help="OBOWIAZKOWY: numer gadu gadu")
    parser.add_option("-k", "--kadu", dest="kaduPath",
                      help="scieżka do katalogu archwium kadu (domyślnie: ~/.kadu/history", metavar="FILE")
    parser.add_option("-e", "--empathy", dest="empathyPath",
                      help="scieżka do katalogu archwium empathy (domyślnie: szukane w ~/.local/share/Empathy/logs",
                      metavar="FILE")
    parser.add_option("-t", "--keephtmltags",action="store_true", default="False", dest="keepHtmlTags",
                      help="Zatrzymuje tagi HTML w w treści wiadomości. Domyślnie je usuwa")
    
    (options, args) = parser.parse_args()
    if options.ggId is None:
        parser.print_help()
        sys.exit(1)
    return (options, args)

# funkcja usuwajaca tagi html. wykorzystywana przy parsowaniu plików gg
def remove_html_tags (data):
    p = re.compile(r'<[^<]*?>')
    return p.sub('', data)

# Poniewaz sciezka do archwium gg empathy nie jest zawsze taka sama, trzeba znalezc odpowiedni katalog,
# jesli uzytkownika nie poda swojego
def searchEmpathyPath(homePath,ggId):
    empathyPossiblePath = homePath+os.sep+".local"+os.sep+"share"+os.sep+"Empathy" +os.sep+"logs"
    logs = os.listdir(empathyPossiblePath)
    if len(logs) == 0:
        return None
    for path in logs:
        if ggId in path.lower():
            return empathyPossiblePath + os.sep + path
    return None


def buildXMLDocument(contactMessages):
    empathyDoc = minidom.Document()
    log = empathyDoc.createElement("log");
    empathyDoc.appendChild(log)  
    for message in contactMessages:
        messageElem = empathyDoc.createElement("message")
        messageElem.setAttribute("time", message.messageDate+"T"+message.messageTime)
        messageElem.setAttribute("cm_id", str(message.cmIdCounter))
        messageElem.setAttribute("id", str(message.contactId))
        messageElem.setAttribute("name", str(message.contactName))
        messageElem.setAttribute("token", "")
        messageElem.setAttribute("isuser", str(message.userMsg).lower())
        messageElem.setAttribute("type","normal")
        messageElem.appendChild(empathyDoc.createTextNode(message.messageContent))
        log.appendChild(messageElem)
    return empathyDoc
# glowna funkcja programu
def main():
    print "Witaj w programie importujacym archiwum rozmów z Kadu do Empathy"
    (options,args) = get_params()
    home = os.getenv("HOME")
    ggId = options.ggId
    kaduPath = options.kaduPath
    empathyPath = options.empathyPath
      
    if (kaduPath is None or empathyPath is None) and home is None:
        print missingHomeEnv()
        return;
    
    if kaduPath is None:
        kaduPath = home + os.sep + ".kadu" + os.sep + "history"
        
    if empathyPath is None:
        empathyPath = searchEmpathyPath(home,ggId)
    
    if not os.access(kaduPath, os.R_OK):
        print wrongPath(kaduPath)
        return;
    if not os.access(empathyPath, os.R_OK or os.W_OK):
        print wrongPath(empathyPath)
        return;
    print "Sciezka do archiwum kadu: ", kaduPath
    print "Sciezka do archwium empathy: ", empathyPath
    print options
    kaduFiles = [];
    kaduLogFiles = [];
    kaduFiles = os.listdir(kaduPath)
    for file in kaduFiles:
        if not "." in file:  # Wybieramy wszystkie pliki archiwum, 
            kaduLogFiles.append(file); # tj. nie zawierające kropki w nazwie
        
    for kaduLogFile in kaduLogFiles:
        kaduLog = open(kaduPath + os.sep + kaduLogFile);
        cm_id_counter = 1;
        contactMessages = []
        for logLine in kaduLog:
            message = Message()
            logLine = logLine.decode("LATIN2") # archiwum w kadu zapisywane jest w iso-8859-2
            
            #w archiwum kadu linijka zaczynajaca sie od chatsend to wiadomosc wyslana przez uzytkownika,
            #linijka zaczynajaca sie od chatrcv to wiadomosc odebrana od rozmowcy
            message.userMsg = logLine.split(",",2)[0] == "chatsend" and True or False; 
            fields = []
            if message.userMsg: # w zaleznosci kto wysylal wiadomosc rozni sie ilosc pol w pliku(czemu?)
                fields = logLine.split(",",4)
            else:
                fields = logLine.split(",",5)
                
            if not message.userMsg:
                message.contactId = fields[1];
                message.contactName = fields[2];
            else:
                message.contactId = ggId;
                message.contactName = ggId; # tutaj moznaby wstawic swoj alias w empathy, moze kiedys...
                
            msgTime = time.localtime(int(fields[3]));
            message.messageDate = time.strftime("%Y%m%d",msgTime);
            message.messageTime = time.strftime("%H:%M:%S",msgTime);
                    
            message.messageContent = ""
            if message.userMsg:
                message.messageContent = fields[4]
            else:
                message.messageContent = fields[5];
                message.cmIdCounter = cm_id_counter;
                cm_id_counter += 1;
            if  options.keepHtmlTags == 'False':
                message.messageContent = remove_html_tags(message.messageContent.strip())
            if (message.messageContent.startswith("\"") and message.messageContent.endswith("\"")):
                message.messageContent = message.messageContent[1:-2]
            message.messageContent = message.messageContent.encode("UTF8")    
            contactMessages.append(message)
            
        empathyContactPath = empathyPath + os.sep + kaduLogFile     
        
        if not os.access(empathyContactPath, os.F_OK):
            os.mkdir(empathyContactPath)
            
        empathyContactFile = open(empathyContactPath + os.sep + "12345678.log", 'w')  
        empathyDoc = buildXMLDocument(contactMessages)
        empathyContactFile.write(empathyDoc.toprettyxml());
        empathyContactFile.close()    
            

def missingHomeEnv():
    return """ Uwaga:
                Twoja sciezka do katalogu jest niezdefiniowana.
                Zdefiniuj zmienną HOME lub poddaj ręcznie ścieżki do archiwów.
          """

def wrongPath(path):
    return """ Błąd:
                Ścieżka: """ + path + """ jest nieprawidłowa,
                lub nie ma praw do odczytu/zapisu
            """                  

if __name__ == '__main__':
    main()