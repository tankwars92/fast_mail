# -*- coding: utf-8 -*-
import Tkinter as tk
import tkFileDialog
import tkMessageBox
import imaplib
import email
import smtplib
from email import encoders
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.header import decode_header

enable_log = False

def decode_mime_words(s):
    try:
        decoded = decode_header(s)
        return u''.join([
            part.decode(charset or 'utf-8') if isinstance(part, bytes) else part
            for part, charset in decoded
        ])
    except:
        return s or u""


class ComposeWindow(tk.Toplevel):
    def __init__(self, master, email_from, password, to_addr="", subject="", body=""):
        tk.Toplevel.__init__(self, master)
        self.title("Новое сообщение")
        self.master.iconbitmap("icon.ico")
        self.email = email_from
        self.password = password
        self.attachments = []

        tk.Label(self, text="Кому:").grid(row=0, column=0, sticky="w")
        self.entry_to = tk.Entry(self, width=40)
        self.entry_to.grid(row=0, column=1, padx=4, pady=2)
        self.entry_to.insert(0, to_addr)

        tk.Label(self, text="Тема:").grid(row=1, column=0, sticky="w")
        self.entry_subj = tk.Entry(self, width=40)
        self.entry_subj.grid(row=1, column=1, padx=4, pady=2)
        self.entry_subj.insert(0, subject)

        self.txt_body = tk.Text(self, width=60, height=15)
        self.txt_body.grid(row=2, column=0, columnspan=2, padx=10, pady=5)
        self.txt_body.insert(tk.END, body)

        btn_attach = tk.Button(self, text="Прикрепить файл", command=self.attach_file)
        btn_attach.grid(row=3, column=0, sticky="w", pady=4, padx=5)

        self.btn_send = tk.Button(self, text="Отправить", command=self.send_email)
        self.btn_send.grid(row=3, column=1, sticky="e", pady=4, padx=5)

    def attach_file(self):
        filepath = tkFileDialog.askopenfilename()
        if filepath:
            self.attachments.append(filepath)

    def send_email(self):
        try:
            to_addr = self.entry_to.get()
            subject = self.entry_subj.get()
            body = self.txt_body.get(1.0, tk.END)

            msg = MIMEMultipart()
            msg["From"] = self.email
            msg["To"] = to_addr
            msg["Subject"] = subject

            msg.attach(MIMEText(body.encode("utf-8"), "plain", "utf-8"))

            for path in self.attachments:
                part = MIMEBase('application', "octet-stream")
                part.set_payload(open(path, "rb").read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment; filename="%s"' % path.split("/")[-1])
                msg.attach(part)

            smtp = smtplib.SMTP("w10.host", 2525)
            smtp.login(self.email, self.password)
            smtp.sendmail(self.email, [to_addr], msg.as_string())
            smtp.quit()
            self.destroy()
        except Exception as e:
            print("ОШИБКА при отправке:", str(e))


class MailClient:
    def __init__(self, master):
        self.master = master
        self.master.title("Byte's FastMail")
        self.master.iconbitmap("icon.ico")
#        self.master.configure(bg="#d4d0c8")

        menubar = tk.Menu(master)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Выход", command=master.quit)
        menubar.add_cascade(label="Файл", menu=file_menu)

        msg_menu = tk.Menu(menubar, tearoff=0)
        msg_menu.add_command(label="Новое сообщение", command=self.compose_new)
        msg_menu.add_command(label="Ответить", command=self.reply)
        menubar.add_cascade(label="Сообщение", menu=msg_menu)

        master.config(menu=menubar)

        bg_main = "#d4d0c8"
        bg_panel = "#f0f0f0"
        font_main = ("MS Sans Serif", 9)

        frm_top = tk.Frame(master, bd=2, relief=tk.GROOVE)
        frm_top.pack(fill=tk.X, padx=2, pady=2)

        tk.Label(frm_top, text="Email:", font=font_main).pack(side=tk.LEFT, padx=2)
        self.entry_email = tk.Entry(frm_top, width=30, font=font_main)
        self.entry_email.pack(side=tk.LEFT, padx=2)

        tk.Label(frm_top, text="Пароль:", font=font_main).pack(side=tk.LEFT, padx=2)
        self.entry_pass = tk.Entry(frm_top, show="*", width=20, font=font_main)
        self.entry_pass.pack(side=tk.LEFT, padx=2)

        self.btn_connect = tk.Button(frm_top, text="Подключиться", font=font_main, command=self.start)
        self.btn_connect.pack(side=tk.LEFT, padx=4)

        frm_middle = tk.PanedWindow(master, sashrelief=tk.RAISED, bd=2, orient=tk.HORIZONTAL)
        frm_middle.pack(fill=tk.BOTH, expand=1, padx=2, pady=2)

        self.lst_messages = tk.Listbox(frm_middle, width=30, font=font_main, bg="white", relief=tk.SUNKEN, borderwidth=2)
        self.lst_messages.bind("<<ListboxSelect>>", self.show_message)
        frm_middle.add(self.lst_messages)

        self.txt_message = tk.Text(frm_middle, font=font_main, bg="white", relief=tk.SUNKEN, borderwidth=2, wrap=tk.WORD)
        self.txt_message.config(state="disabled")
        frm_middle.add(self.txt_message)

        self.lst_attachments = tk.Listbox(frm_middle, width=25, font=font_main, bg="white", relief=tk.SUNKEN, borderwidth=2)
        self.lst_attachments.bind("<Double-Button-1>", self.open_attachment)
        frm_middle.add(self.lst_attachments)

        frm_middle.paneconfig(self.lst_messages, minsize=150)
        frm_middle.paneconfig(self.txt_message, minsize=300)
        frm_middle.paneconfig(self.lst_attachments, minsize=100)

        self.ctx_menu = tk.Menu(master, tearoff=0, font=font_main)
        self.ctx_menu.add_command(label="Получить", command=self.start)
        self.ctx_menu.add_command(label="Ответить", command=self.reply)

        def show_context_menu(event):
            try:
                self.lst_messages.selection_clear(0, tk.END)
                index = self.lst_messages.nearest(event.y)
                self.lst_messages.selection_set(index)
            except:
                pass
            self.ctx_menu.tk_popup(event.x_root, event.y_root)

        self.lst_messages.bind("<Button-3>", show_context_menu)

        self.status = tk.Label(master, text="Ожидание действий...", bd=1, relief=tk.SUNKEN, anchor="w", font=font_main)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

        self.imap = None
        self.email = ""
        self.password = ""
        self.messages = []

    def log(self, msg):
        if enable_log:
            print(msg)
        self.status.config(text=msg)

    def start(self):
        self.email = self.entry_email.get()
        self.password = self.entry_pass.get()
        self.lst_messages.delete(0, tk.END)
        self.txt_message.delete(1.0, tk.END)
        self.messages = []
        self.master.after(100, self.process)

    def process(self):
        try:
            self.log("Соединение с IMAP...")
            self.imap = imaplib.IMAP4("w10.host", 143)
            self.log("Логин...")
            self.imap.login(self.email, self.password)
            self.log("Выбор INBOX...")
            self.imap.select("INBOX")
            self.log("Поиск писем...")
            typ, data = self.imap.search(None, 'ALL')
            ids = data[0].split()

            for mid in reversed(ids[-20:]):
                typ, msg_data = self.imap.fetch(mid, '(RFC822)')
                raw = msg_data[0][1]
                msg = email.message_from_string(raw)
                subject = decode_mime_words(msg.get("Subject", "(нет темы)"))
                from_ = email.utils.parseaddr(msg.get("From", ""))[1]
                self.messages.append(msg)
                self.lst_messages.insert(tk.END, "%s / %s" % (from_, subject))

            self.imap.logout()
        except Exception as e:
            self.log("ОШИБКА: %s" % str(e))

    def show_message(self, event):
        selection = self.lst_messages.curselection()
        if not selection:
            return
        index = int(selection[0])
        msg = self.messages[index]
        body = u""
        attachments = []

        if msg.is_multipart():
            for part in msg.walk():
                disp = part.get("Content-Disposition", "").lower()
                if part.get_content_type() == "text/plain" and not disp.startswith("attachment"):
                    charset = part.get_content_charset() or 'utf-8'
                    body = part.get_payload(decode=True).decode(charset, errors="replace")
                elif "attachment" in disp:
                    filename = decode_mime_words(part.get_filename() or "unnamed")
                    data = part.get_payload(decode=True)
                    attachments.append((filename, data))
        else:
            charset = msg.get_content_charset() or 'utf-8'
            body = msg.get_payload(decode=True).decode(charset, errors="replace")

        self.txt_message.delete(1.0, tk.END)

        self.txt_message.tag_configure("bold", font=("TkDefaultFont", 10, "bold"))

        subject = decode_mime_words(msg.get("Subject", "(нет темы)"))
        from_ = email.utils.parseaddr(msg.get("From", ""))[1]

        self.txt_message.config(state="normal")
        self.txt_message.delete(1.0, tk.END)

        self.txt_message.tag_configure("bold", font=("TkDefaultFont", 10, "bold"))

        self.txt_message.insert(tk.END, u"From: ", "bold")
        self.txt_message.insert(tk.END, from_ + u"\n")

        self.txt_message.insert(tk.END, u"Subject: ", "bold")
        self.txt_message.insert(tk.END, subject + u"\n")

        self.txt_message.insert(tk.END, body)

        self.txt_message.config(state="disabled")


        self.lst_attachments.delete(0, tk.END)
        self.attachments_data = []

        if attachments:
            for i, (fname, data) in enumerate(attachments):
                self.lst_attachments.insert(tk.END, fname)
                self.attachments_data.append((fname, data))

            import os
            folder = "attachments"
            if not os.path.exists(folder):
                os.makedirs(folder)
            for fname, data in attachments:
                try:
                    with open(os.path.join(folder, fname), "wb") as f:
                        f.write(data)
                except:
                    pass

    def open_attachment(self, event):
        selection = self.lst_attachments.curselection()
        if not selection:
            return
        index = int(selection[0])
        fname, data = self.attachments_data[index]
        path = tkFileDialog.asksaveasfilename(initialfile=fname)
        if path:
            try:
                with open(path, "wb") as f:
                    f.write(data)
                self.log("Файл сохранён: %s" % path)
            except Exception as e:
                self.log("Ошибка сохранения: %s" % str(e))

    def compose_new(self):
        ComposeWindow(self.master, self.email, self.password)

    def reply(self):
        selection = self.lst_messages.curselection()
        if not selection:
            return
        index = int(selection[0])
        msg = self.messages[index]
        to_addr = email.utils.parseaddr(msg.get("From", ""))[1]
        subj = decode_mime_words(msg.get("Subject", ""))
        if not subj.lower().startswith("re:"):
            subj = "Re: " + subj
        ComposeWindow(self.master, self.email, self.password, to_addr=to_addr, subject=subj)


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("550x395")
    app = MailClient(root)
    root.mainloop()
