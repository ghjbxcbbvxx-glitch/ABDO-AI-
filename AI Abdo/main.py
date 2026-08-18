import os
import json
import uuid
import sqlite3
import threading
import requests

from datetime import datetime

import arabic_reshaper
from bidi.algorithm import get_display

from kivy.app import App
from kivy.clock import mainthread
from kivy.lang import Builder
from kivy.properties import StringProperty, BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.metrics import dp


# ============================================================
# ABDO AI V2
# ============================================================

APP_NAME = "ABDO AI"

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

CONFIG_FILE = os.path.join(
    BASE_DIR,
    "config.json"
)

DATABASE_FILE = os.path.join(
    BASE_DIR,
    "abdo_ai.db"
)

ARABIC_FONT = os.path.join(
    BASE_DIR,
    "fonts",
    "NotoSansArabic-Regular.ttf"
)

API_URL_DEFAULT = (
    "https://api.bluesminds.com/v1/chat/completions"
)

MODEL_DEFAULT = (
    "meta/llama-3.1-8b-instruct"
)


# ============================================================
# ARABIC / RTL
# ============================================================

def contains_arabic(text):
    """
    معرفة هل النص يحتوي على حروف عربية.
    """

    if not text:
        return False

    for char in text:

        code = ord(char)

        if (
            0x0600 <= code <= 0x06FF
            or 0x0750 <= code <= 0x077F
            or 0x08A0 <= code <= 0x08FF
            or 0xFB50 <= code <= 0xFDFF
            or 0xFE70 <= code <= 0xFEFF
        ):
            return True

    return False


def prepare_text_for_display(text):
    """
    تجهيز النص العربي للعرض داخل Kivy.

    مهم:
    النص الأصلي الذي يتم إرساله إلى الـAPI
    لا يتم تغييره.
    """

    if not text:
        return ""

    if not contains_arabic(text):
        return text

    try:

        reshaped = arabic_reshaper.reshape(text)

        return get_display(reshaped)

    except Exception:

        return text


# ============================================================
# KV UI
# ============================================================

KV = r'''

#:import dp kivy.metrics.dp


<ChatBubble>:

    orientation: "vertical"

    size_hint_y: None

    height: message.texture_size[1] + dp(32)

    padding: dp(15), dp(12)

    canvas.before:

        Color:

            rgba: (0.105, 0.115, 0.155, 1) if root.role == "assistant" else (0.30, 0.16, 0.48, 1)

        RoundedRectangle:

            pos: self.pos

            size: self.size

            radius: [dp(18), dp(18), dp(18), dp(18)]


    Label:

        id: message

        text: root.text

        font_name: app.arabic_font

        color: 1, 1, 1, 1

        font_size: dp(15)

        text_size: self.width - dp(8), None

        halign: root.text_alignment

        valign: "top"

        size_hint_y: None

        height: self.texture_size[1]


<MainScreen>:

    BoxLayout:

        orientation: "horizontal"


        canvas.before:

            Color:

                rgba: 0.025, 0.028, 0.040, 1

            Rectangle:

                pos: self.pos

                size: self.size


        # ====================================================
        # SIDEBAR
        # ====================================================

        BoxLayout:

            id: sidebar

            orientation: "vertical"

            size_hint_x: None

            width: dp(290) if app.sidebar_open else 0

            opacity: 1 if app.sidebar_open else 0

            padding: dp(12)

            spacing: dp(9)


            Label:

                text: "ABDO AI"

                font_name: app.arabic_font

                font_size: dp(24)

                bold: True

                color: 0.72, 0.42, 1, 1

                size_hint_y: None

                height: dp(45)


            Label:

                text: "مساعدك الذكي" if app.lang == "ar" else "Your AI Assistant"

                font_name: app.arabic_font

                font_size: dp(12)

                color: 0.48, 0.50, 0.58, 1

                size_hint_y: None

                height: dp(28)


            Button:

                text: "＋  " + ("محادثة جديدة" if app.lang == "ar" else "New Chat")

                font_name: app.arabic_font

                size_hint_y: None

                height: dp(48)

                background_normal: ""

                background_color: 0.38, 0.18, 0.60, 1

                on_release: app.new_chat()


            ScrollView:

                do_scroll_x: False


                BoxLayout:

                    id: history

                    orientation: "vertical"

                    size_hint_y: None

                    height: self.minimum_height

                    spacing: dp(6)


            Widget:


            BoxLayout:

                size_hint_y: None

                height: dp(48)

                spacing: dp(7)


                Button:

                    text: "EN" if app.lang == "ar" else "AR"

                    font_name: app.arabic_font

                    background_normal: ""

                    background_color: 0.09, 0.10, 0.14, 1

                    on_release: app.toggle_language()


                Button:

                    text: "⚙"

                    font_size: dp(20)

                    background_normal: ""

                    background_color: 0.09, 0.10, 0.14, 1

                    on_release: app.open_settings()


        # ====================================================
        # MAIN AREA
        # ====================================================

        BoxLayout:

            orientation: "vertical"


            # =================================================
            # TOP BAR
            # =================================================

            BoxLayout:

                size_hint_y: None

                height: dp(62)

                padding: dp(8)

                spacing: dp(8)


                canvas.before:

                    Color:

                        rgba: 0.045, 0.050, 0.070, 1

                    Rectangle:

                        pos: self.pos

                        size: self.size


                Button:

                    text: "☰"

                    size_hint_x: None

                    width: dp(48)

                    background_normal: ""

                    background_color: 0.09, 0.10, 0.14, 1

                    on_release: app.sidebar_open = not app.sidebar_open


                Label:

                    text: "ABDO AI"

                    font_name: app.arabic_font

                    font_size: dp(19)

                    bold: True

                    color: 1, 1, 1, 1


                Label:

                    text: app.status_text

                    font_name: app.arabic_font

                    font_size: dp(12)

                    color: 0.50, 0.52, 0.60, 1

                    size_hint_x: None

                    width: dp(95)


            # =================================================
            # MESSAGES
            # =================================================

            ScrollView:

                id: scroll

                do_scroll_x: False


                BoxLayout:

                    id: messages

                    orientation: "vertical"

                    size_hint_y: None

                    height: self.minimum_height

                    padding: dp(15), dp(20)

                    spacing: dp(12)


            # =================================================
            # INPUT AREA
            # =================================================

            BoxLayout:

                size_hint_y: None

                height: dp(78)

                padding: dp(10)

                spacing: dp(8)


                TextInput:

                    id: prompt

                    font_name: app.arabic_font

                    hint_text: "اكتب رسالتك..." if app.lang == "ar" else "Message ABDO AI..."

                    multiline: True

                    background_normal: ""

                    background_color: 0.075, 0.080, 0.110, 1

                    foreground_color: 1, 1, 1, 1

                    cursor_color: 0.70, 0.40, 1, 1

                    padding: dp(14), dp(12)

                    halign: "right" if app.rtl else "left"


                Button:

                    text: "➤"

                    font_size: dp(21)

                    size_hint_x: None

                    width: dp(60)

                    background_normal: ""

                    background_color: 0.42, 0.20, 0.68, 1

                    on_release: app.send_message()


<SettingsScreen>:

    BoxLayout:

        orientation: "vertical"

        padding: dp(22)

        spacing: dp(15)


        canvas.before:

            Color:

                rgba: 0.025, 0.028, 0.040, 1

            Rectangle:

                pos: self.pos

                size: self.size


        Label:

            text: "الإعدادات" if app.lang == "ar" else "Settings"

            font_name: app.arabic_font

            font_size: dp(25)

            bold: True

            size_hint_y: None

            height: dp(55)

            halign: "right" if app.rtl else "left"


        Label:

            text: "ABDO AI"

            font_name: app.arabic_font

            font_size: dp(18)

            color: 0.72, 0.42, 1, 1

            size_hint_y: None

            height: dp(35)


        Label:

            text: "عنوان الـ API:\\n" + app.api_url

            font_name: app.arabic_font

            color: 0.65, 0.67, 0.73, 1

            text_size: self.width, None

            halign: "right" if app.rtl else "left"


        Label:

            text: "الموديل:\\n" + app.model_name

            font_name: app.arabic_font

            color: 0.65, 0.67, 0.73, 1

            text_size: self.width, None

            halign: "right" if app.rtl else "left"


        Label:

            text: "مفتاح API يتم حفظه في config.json. لا تنشر المفتاح الحقيقي داخل APK عام."

            font_name: app.arabic_font

            color: 0.65, 0.67, 0.73, 1

            text_size: self.width, None

            halign: "right"


        Widget:


        Button:

            text: "رجوع" if app.lang == "ar" else "Back"

            font_name: app.arabic_font

            size_hint_y: None

            height: dp(50)

            background_normal: ""

            background_color: 0.30, 0.16, 0.45, 1

            on_release: root.manager.current = "main"

'''


# ============================================================
# CHAT BUBBLE
# ============================================================

class ChatBubble(BoxLayout):

    role = StringProperty("assistant")

    text = StringProperty("")

    text_alignment = StringProperty("left")


# ============================================================
# SCREENS
# ============================================================

class MainScreen(Screen):
    pass


class SettingsScreen(Screen):
    pass


# ============================================================
# APP
# ============================================================

class ABDOAI(App):

    lang = StringProperty("ar")

    rtl = BooleanProperty(True)

    sidebar_open = BooleanProperty(True)

    status_text = StringProperty("جاهز")

    api_url = StringProperty(API_URL_DEFAULT)

    model_name = StringProperty(MODEL_DEFAULT)

    arabic_font = StringProperty(ARABIC_FONT)


    # ========================================================
    # BUILD
    # ========================================================

    def build(self):

        self.title = APP_NAME

        Builder.load_string(KV)

        self.load_config()

        self.init_database()

        manager = ScreenManager()

        manager.add_widget(
            MainScreen(name="main")
        )

        manager.add_widget(
            SettingsScreen(name="settings")
        )

        return manager


    # ========================================================
    # CONFIG
    # ========================================================

    def load_config(self):

        self.config = {

            "api_key": "",

            "api_url": API_URL_DEFAULT,

            "model": MODEL_DEFAULT

        }


        if os.path.exists(CONFIG_FILE):

            try:

                with open(
                    CONFIG_FILE,
                    "r",
                    encoding="utf-8"
                ) as file:

                    data = json.load(file)

                    self.config.update(data)

            except Exception as error:

                print(
                    "Config error:",
                    error
                )


        self.api_url = self.config.get(
            "api_url",
            API_URL_DEFAULT
        )


        self.model_name = self.config.get(
            "model",
            MODEL_DEFAULT
        )


    # ========================================================
    # DATABASE
    # ========================================================

    def init_database(self):

        self.db = sqlite3.connect(

            DATABASE_FILE,

            check_same_thread=False

        )


        self.db.execute("""
            CREATE TABLE IF NOT EXISTS chats (

                id TEXT PRIMARY KEY,

                title TEXT,

                messages TEXT,

                created_at TEXT

            )
        """)


        self.db.commit()


        self.chat_id = str(
            uuid.uuid4()
        )


        self.messages_data = []


    # ========================================================
    # ON START
    # ========================================================

    def on_start(self):

        self.refresh_history()


        if not os.path.exists(ARABIC_FONT):

            print(
                "WARNING: Arabic font not found:"
            )

            print(
                ARABIC_FONT
            )


    # ========================================================
    # HISTORY
    # ========================================================

    def refresh_history(self):

        try:

            screen = self.root.get_screen(
                "main"
            )

            history = screen.ids.history

            history.clear_widgets()


            rows = self.db.execute(
                """
                SELECT id, title
                FROM chats
                ORDER BY created_at DESC
                """
            ).fetchall()


            from kivy.uix.button import Button


            for chat_id, title in rows:

                display_title = prepare_text_for_display(
                    title
                )


                button = Button(

                    text=display_title,

                    font_name=self.arabic_font,

                    size_hint_y=None,

                    height=dp(44),

                    background_normal="",

                    background_color=(
                        0.08,
                        0.09,
                        0.13,
                        1
                    )

                )


                button.bind(

                    on_release=lambda
                    btn,
                    cid=chat_id:
                    self.load_chat(cid)

                )


                history.add_widget(
                    button
                )


        except Exception as error:

            print(
                "History error:",
                error
            )


    # ========================================================
    # NEW CHAT
    # ========================================================

    def new_chat(self):

        self.chat_id = str(
            uuid.uuid4()
        )


        self.messages_data = []


        screen = self.root.get_screen(
            "main"
        )


        screen.ids.messages.clear_widgets()


        self.status_text = (

            "جاهز"

            if self.lang == "ar"

            else "Ready"

        )


        screen.ids.prompt.text = ""


    # ========================================================
    # SAVE CHAT
    # ========================================================

    def save_chat(self, title=None):

        if not self.messages_data:

            return


        if title is None:

            title = (
                "محادثة جديدة"
                if self.lang == "ar"
                else "New Chat"
            )


            for message in self.messages_data:

                if message["role"] == "user":

                    title = message["content"][:40]

                    break


        self.db.execute(

            """
            INSERT OR REPLACE INTO chats
            VALUES (?, ?, ?, ?)
            """,

            (

                self.chat_id,

                title,

                json.dumps(

                    self.messages_data,

                    ensure_ascii=False

                ),

                datetime.now().isoformat()

            )

        )


        self.db.commit()


        self.refresh_history()


    # ========================================================
    # LOAD CHAT
    # ========================================================

    def load_chat(self, chat_id):

        row = self.db.execute(

            """
            SELECT title, messages
            FROM chats
            WHERE id=?
            """,

            (chat_id,)

        ).fetchone()


        if not row:

            return


        self.chat_id = chat_id


        self.messages_data = json.loads(
            row[1]
        )


        screen = self.root.get_screen(
            "main"
        )


        screen.ids.messages.clear_widgets()


        for message in self.messages_data:

            self.add_bubble(

                message["role"],

                message["content"]

            )


    # ========================================================
    # ADD BUBBLE
    # ========================================================

    def add_bubble(self, role, text):

        screen = self.root.get_screen(
            "main"
        )


        display_text = prepare_text_for_display(
            text
        )


        alignment = (
            "right"
            if contains_arabic(text)
            else "left"
        )


        bubble = ChatBubble(

            role=role,

            text=display_text,

            text_alignment=alignment

        )


        screen.ids.messages.add_widget(
            bubble
        )


        screen.ids.scroll.scroll_y = 0


    # ========================================================
    # SEND MESSAGE
    # ========================================================

    def send_message(self):

        screen = self.root.get_screen(
            "main"
        )


        prompt = screen.ids.prompt


        original_text = prompt.text.strip()


        if not original_text:

            return


        if self.status_text in (

            "جاري...",

            "Thinking..."

        ):

            return


        prompt.text = ""


        # IMPORTANT:
        # Send original Arabic text to API.
        # DO NOT reshape it here.

        self.messages_data.append({

            "role": "user",

            "content": original_text

        })


        self.add_bubble(

            "user",

            original_text

        )


        self.save_chat()


        self.status_text = (

            "جاري..."

            if self.lang == "ar"

            else "Thinking..."

        )


        messages = list(
            self.messages_data
        )


        threading.Thread(

            target=self.request_ai,

            args=(messages,),

            daemon=True

        ).start()


    # ========================================================
    # API REQUEST
    # ========================================================

    def request_ai(self, messages):

        api_key = self.config.get(
            "api_key",
            ""
        ).strip()


        if not api_key:

            self.finish_error(

                "لم يتم وضع API Key داخل config.json"

            )

            return


        payload = {

            "model": self.model_name,

            "messages": messages,

            "temperature": 0.7

        }


        headers = {

            "Content-Type":
                "application/json",

            "Authorization":
                f"Bearer {api_key}"

        }


        try:

            response = requests.post(

                self.api_url,

                headers=headers,

                json=payload,

                timeout=120

            )


            if response.status_code >= 400:

                self.finish_error(

                    f"API Error {response.status_code}\n"
                    f"{response.text[:700]}"

                )

                return


            data = response.json()


            answer = (

                data

                ["choices"]

                [0]

                ["message"]

                ["content"]

            )


            self.finish_answer(
                answer
            )


        except requests.exceptions.Timeout:

            self.finish_error(

                "انتهت مهلة الاتصال بالـ API."

            )


        except requests.exceptions.ConnectionError:

            self.finish_error(

                "تعذر الاتصال بالإنترنت أو بخادم API."

            )


        except Exception as error:

            self.finish_error(
                str(error)
            )


    # ========================================================
    # FINISH ANSWER
    # ========================================================

    @mainthread
    def finish_answer(self, answer):

        self.messages_data.append({

            "role": "assistant",

            "content": answer

        })


        self.add_bubble(

            "assistant",

            answer

        )


        self.save_chat()


        self.status_text = (

            "جاهز"

            if self.lang == "ar"

            else "Ready"

        )


    # ========================================================
    # ERROR
    # ========================================================

    @mainthread
    def finish_error(self, error):

        self.add_bubble(

            "assistant",

            "⚠️ " + error

        )


        self.status_text = (

            "خطأ"

            if self.lang == "ar"

            else "Error"

        )


    # ========================================================
    # LANGUAGE
    # ========================================================

    def toggle_language(self):

        if self.lang == "ar":

            self.lang = "en"

            self.rtl = False

        else:

            self.lang = "ar"

            self.rtl = True


    # ========================================================
    # SETTINGS
    # ========================================================

    def open_settings(self):

        self.root.current = "settings"


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    ABDOAI().run()