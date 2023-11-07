#! /usr/bin/python3


from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSpinBox, QCheckBox, QDialog, QButtonGroup
from PyQt5.QtCore import QDateTime, Qt, QTimer, QCoreApplication
from PyQt5.QtGui import QPixmap, QIcon

import RPi.GPIO as GPIO
from datetime import datetime
import sys
import os
import json
import random
import vlc

os.chdir("/home/ksubf/Desktop/prayer/")


# Power Control Relay Setup
RELAY_PIN = 5
DELAY_FOR_TURNON = 100

GPIO.setmode(GPIO.BCM)
#GPIO.setwarnings(False)
GPIO.setup(RELAY_PIN, GPIO.OUT)

#Alarm Time Schedule
TimeSchedule = None

# Audio Power Control
POWER_STATE = False
def powerOn():
    GPIO.output(RELAY_PIN, True)
    power_dialog = PowerDialog(DELAY_FOR_TURNON)
    power_dialog.exec_()

def powerOff():
    GPIO.output(RELAY_PIN, False)
    global POWER_STATE
    POWER_STATE = False

def PowerSequence():
    if POWER_STATE:
        powerOff()
    else:
        powerOn()

class PowerDialog(QDialog):
    def __init__(self, remaining_time):
        super().__init__()
        self.setWindowTitle("Powering On...")
        self.remaining_time = remaining_time

        layout = QVBoxLayout()
        self.time_label = QLabel(f"전원 켜는 중.. {self.remaining_time}초 남음.")
        layout.addWidget(self.time_label)

        self.setLayout(layout)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_remaining_time)
        self.timer.start(1000)

    def update_remaining_time(self):
        self.remaining_time -= 1
        self.time_label.setText(f"전원 켜는 중.. {self.remaining_time}초 남음.")
        if self.remaining_time == 0:
            self.timer.stop()
            global POWER_STATE
            POWER_STATE = True
            self.accept()  # Close the dialog once the process is complete


class ScheduleDialog(QDialog):
    day_group = QButtonGroup()
    day = "mon"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("스케줄 설정")
        self.showFullScreen()


        days_layout = QHBoxLayout()
        days = ["월", "화", "수", "목", "금", "토", "일"]
        for day in days:
            day_button = QPushButton(day)
            day_button.setFixedSize(100, 100)
            day_button.setCheckable(True)
            day_button.setStyleSheet("font-size: 40pt;")
            days_layout.addWidget(day_button)
            self.day_group.addButton(day_button)

        self.day_group.buttonClicked.connect(self.slot)


        time_layout = QHBoxLayout()

        self.hour_spinbox = QSpinBox()
        self.hour_spinbox.setFixedSize(100, 50)
        self.hour_spinbox.setStyleSheet("font-size: 40pt;")
        self.hour_spinbox.setRange(0, 23)
        self.hour_spinbox.valueChanged.connect(self.hourChanged)

        self.minute_spinbox = QSpinBox()
        self.minute_spinbox.setFixedSize(114, 50)
        self.minute_spinbox.setStyleSheet("font-size: 40pt;")
        self.minute_spinbox.setRange(0, 59)
        self.minute_spinbox.valueChanged.connect(self.minuteChanged)

        self.time_spinbox = QSpinBox()
        self.time_spinbox.setFixedSize(114, 50)
        self.time_spinbox.setStyleSheet("font-size: 40pt;")
        self.time_spinbox.setRange(0, 12)
        self.time_spinbox.valueChanged.connect(self.timeChanged)

        self.active_checkbox = QCheckBox("Active")
        self.active_checkbox.setStyleSheet("font-size: 30pt;")
        self.active_checkbox.stateChanged.connect(self.activeChanged)

        self.active_checkbox.setCheckState(TimeSchedule[self.day]["active"])
        self.hour_spinbox.setValue(TimeSchedule[self.day]["hour"])
        self.minute_spinbox.setValue(TimeSchedule[self.day]["min"])
        self.time_spinbox.setValue(TimeSchedule[self.day]["time"])

        time_layout.addStretch(1)
        time_layout.addWidget(self.hour_spinbox)
        time_layout.addWidget(QLabel("시"))
        time_layout.addWidget(self.minute_spinbox)
        time_layout.addWidget(QLabel("분"))
        time_layout.addWidget(self.time_spinbox)
        time_layout.addWidget(QLabel("시간"))
        time_layout.addWidget(self.active_checkbox)
        time_layout.addStretch(1)

        se_layout = QHBoxLayout()

        save_button = QPushButton("설정 저장")
        save_button.setStyleSheet("font-size: 50pt;")
        save_button.clicked.connect(self.save_schedule)
        se_layout.addWidget(save_button)

        exit_button = QPushButton("종료")
        exit_button.setStyleSheet("font-size: 50pt;")
        exit_button.clicked.connect(self.exit_all)
        se_layout.addWidget(exit_button)

        main_layout = QVBoxLayout()
        main_layout.addLayout(days_layout)
        main_layout.addLayout(time_layout)
        main_layout.addLayout(se_layout)

        self.setLayout(main_layout)

    def hourChanged(self):
        global TimeSchedule
        TimeSchedule[self.day]["hour"] = self.hour_spinbox.value()

    def minuteChanged(self):
        global TimeSchedule
        TimeSchedule[self.day]["min"] = self.minute_spinbox.value()

    def timeChanged(self):
        global TimeSchedule
        TimeSchedule[self.day]["time"] = self.time_spinbox.value()

    def activeChanged(self):
        global TimeSchedule
        TimeSchedule[self.day]["active"] = self.active_checkbox.checkState()

    def slot(self, object):
        self.day = {"-2" : "mon", "-3" : "tue", "-4" : "wed", "-5" : "thu","-6" : "fri","-7" : "sat","-8" : "sun"}.get(str(self.day_group.id(object)))
        #boolean = {"True" : 2, "False": 0}
        #self.active_checkbox.setCheckState(boolean.get(TimeSchedule[day]["active"]))
        self.active_checkbox.setCheckState(TimeSchedule[self.day]["active"])
        self.hour_spinbox.setValue(TimeSchedule[self.day]["hour"])
        self.minute_spinbox.setValue(TimeSchedule[self.day]["min"])
        self.time_spinbox.setValue(TimeSchedule[self.day]["time"])

    def save_schedule(self):
        with open('time.json', 'w') as f:
            json.dump(TimeSchedule, f)
        self.accept()

    def exit_all(self):
        if POWER_STATE:
            powerOff()
        QCoreApplication.instance().quit()

class MyWindow(QMainWindow):
    alarmTimer = None

    def __init__(self):
        super().__init__()
        self.setWindowTitle("시계 애플리케이션")
        self.showFullScreen()

        with open('time.json') as f:
            global TimeSchedule
            TimeSchedule = json.load(f)

        self.date_time_label = QLabel("")
        self.date_time_label.setStyleSheet("font-size: 50pt;")
        self.date_time_label.setAlignment(Qt.AlignCenter)

        self.update_date_time()

        power_icon = QIcon(QPixmap("images/power.png"))
        play_icon = QIcon(QPixmap("images/play.png"))
        stop_icon = QIcon(QPixmap("images/stop.png"))
        
        self.buttons_layout = QHBoxLayout()
        power_button = QPushButton(power_icon,"", self)
        power_button.setFixedSize(150, 150)
        power_button.setStyleSheet("border-radius: 20px")
        power_button.clicked.connect(self.power_button_clicked)

        play_button = QPushButton(play_icon,"", self)
        play_button.setFixedSize(150, 150)
        play_button.setStyleSheet("border-radius: 20px")
        play_button.clicked.connect(self.play_button_clicked)

        stop_button = QPushButton(stop_icon,"", self)
        stop_button.setFixedSize(150, 150)
        stop_button.setStyleSheet("border-radius: 20px")
        stop_button.clicked.connect(self.stop_button_clicked)

        power_button.setIconSize(power_button.rect().size())
        play_button.setIconSize(power_button.rect().size())
        stop_button.setIconSize(power_button.rect().size())

        self.buttons_layout.addWidget(power_button)
        self.buttons_layout.addWidget(play_button)
        self.buttons_layout.addWidget(stop_button)

        schedule_button = QPushButton("스케줄 설정")
        schedule_button.setStyleSheet("font-size: 50pt;")
        schedule_button.clicked.connect(self.show_schedule_dialog)

        layout = QVBoxLayout()
        layout.addWidget(self.date_time_label)
        layout.addLayout(self.buttons_layout)
        layout.addWidget(schedule_button)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)


        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_date_time)
        self.timer.start(1000)
        
        self.vlc_instance = vlc.Instance()
        self.player = self.vlc_instance.media_player_new()
        self.media_list = self.vlc_instance.media_list_new()
        self.mp3_files = self.get_mp3_files()
        self.current_mp3 = None

    def watchDog(self):
        now = datetime.now()
        day = {"0" : "mon", "1" : "tue", "2" : "wed", "3" : "thu", "4" : "fri","5" : "sat","6" : "sun"}.get(str(now.weekday()))
        alarm_Set = TimeSchedule[day]

        if alarm_Set["active"]:
            if now.hour == alarm_Set["hour"]:
                if now.minute == alarm_Set["min"]:
                    if now.second == 0:
                        powerOn()
                        self.play_button_()
                        self.alarmTimer = QTimer(self)
                        self.alarmTimer.setInterval(alarm_Set["time"]*60*60*1000)
                        self.alarmTimer.timeout.connect(self.prayTimeout)
                        self.alarmTimer.start()

    def prayTimeout(self):
        self.stop_button_clicked()
        powerOff()

    def update_date_time(self):
        current_datetime = datetime.now()
        formatted_date = current_datetime.strftime("%Y년 %m월 %d일 %A")
        formatted_time = current_datetime.strftime("%H시 %M분 %S초")
        self.date_time_label.setText(formatted_date + "\n" + formatted_time)
        self.watchDog()

    def show_schedule_dialog(self):
        schedule_dialog = ScheduleDialog()
        schedule_dialog.exec()

    def power_button_clicked(self):
        PowerSequence()

    def play_button_clicked(self):
        if POWER_STATE:
            self.play_button_()

        else:
            powerOn()
            self.play_button_()

    def play_button_(self):
        del self.media_list
        self.media_list = self.vlc_instance.media_list_new()

        if self.mp3_files:
            for i in self.mp3_files:
                self.media_list.add_media(random.choice(self.mp3_files))

            self.media_list_player = self.vlc_instance.media_list_player_new()
            self.media_list_player.set_media_list(self.media_list)

        if hasattr(self, 'media_list_player'):
            self.media_list_player.play()

    def stop_button_clicked(self):
        if hasattr(self, 'media_list_player'):
            self.media_list_player.stop()
            del self.media_list_player
        if self.alarmTimer:
            self.alarmTimer.stop()


    def get_mp3_files(self):
        mp3_files = []
        folder_path = "./music/"
        for file in os.listdir(folder_path):
            if file.endswith(".mp3"):
                mp3_files.append(os.path.join(folder_path, file))
        return mp3_files

def closeEvent(self, QCloseEvent):
    GPIO.cleanup()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app.exec_())
