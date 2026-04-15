# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'MainWindow.ui'
##
## Created by: Qt User Interface Compiler version 6.11.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractScrollArea, QApplication, QButtonGroup, QDoubleSpinBox,
    QFrame, QGridLayout, QHBoxLayout, QLCDNumber,
    QLabel, QLayout, QLineEdit, QMainWindow,
    QMenuBar, QProgressBar, QPushButton, QRadioButton,
    QScrollArea, QSizePolicy, QSlider, QSpacerItem,
    QSpinBox, QStatusBar, QToolButton, QVBoxLayout,
    QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(975, 611)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.verticalLayout_5 = QVBoxLayout()
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.label_4 = QLabel(self.centralwidget)
        self.label_4.setObjectName(u"label_4")

        self.verticalLayout_5.addWidget(self.label_4)

        self.verticalSpacer_8 = QSpacerItem(20, 5, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.verticalLayout_5.addItem(self.verticalSpacer_8)

        self.image_label_left = QLabel(self.centralwidget)
        self.image_label_left.setObjectName(u"image_label_left")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.image_label_left.sizePolicy().hasHeightForWidth())
        self.image_label_left.setSizePolicy(sizePolicy)
        self.image_label_left.setScaledContents(True)

        self.verticalLayout_5.addWidget(self.image_label_left)


        self.horizontalLayout.addLayout(self.verticalLayout_5)

        self.verticalLayout_9 = QVBoxLayout()
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.label_5 = QLabel(self.centralwidget)
        self.label_5.setObjectName(u"label_5")

        self.verticalLayout_9.addWidget(self.label_5)

        self.verticalSpacer_9 = QSpacerItem(20, 5, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.verticalLayout_9.addItem(self.verticalSpacer_9)

        self.image_label_right = QLabel(self.centralwidget)
        self.image_label_right.setObjectName(u"image_label_right")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.image_label_right.sizePolicy().hasHeightForWidth())
        self.image_label_right.setSizePolicy(sizePolicy1)

        self.verticalLayout_9.addWidget(self.image_label_right)


        self.horizontalLayout.addLayout(self.verticalLayout_9)

        self.IMAGE_SPACER = QSpacerItem(15, 15, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.IMAGE_SPACER)

        self.scrollArea = QScrollArea(self.centralwidget)
        self.scrollArea.setObjectName(u"scrollArea")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.scrollArea.sizePolicy().hasHeightForWidth())
        self.scrollArea.setSizePolicy(sizePolicy2)
        self.scrollArea.setMinimumSize(QSize(0, 0))
        self.scrollArea.setMaximumSize(QSize(220, 16777215))
        self.scrollArea.setFrameShape(QFrame.Shape.NoFrame)
        self.scrollArea.setFrameShadow(QFrame.Shadow.Plain)
        self.scrollArea.setLineWidth(0)
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollArea.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored)
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 218, 526))
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.scrollAreaWidgetContents.sizePolicy().hasHeightForWidth())
        self.scrollAreaWidgetContents.setSizePolicy(sizePolicy3)
        self.scrollAreaWidgetContents.setAutoFillBackground(True)
        self.verticalLayout_7 = QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.label_6 = QLabel(self.scrollAreaWidgetContents)
        self.label_6.setObjectName(u"label_6")

        self.verticalLayout_7.addWidget(self.label_6)

        self.name_input = QLineEdit(self.scrollAreaWidgetContents)
        self.name_input.setObjectName(u"name_input")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.name_input.sizePolicy().hasHeightForWidth())
        self.name_input.setSizePolicy(sizePolicy4)
        self.name_input.setMinimumSize(QSize(200, 0))

        self.verticalLayout_7.addWidget(self.name_input)

        self.verticalSpacer_5 = QSpacerItem(20, 15, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.verticalLayout_7.addItem(self.verticalSpacer_5)

        self.label_7 = QLabel(self.scrollAreaWidgetContents)
        self.label_7.setObjectName(u"label_7")

        self.verticalLayout_7.addWidget(self.label_7)

        self.single_picture_button = QRadioButton(self.scrollAreaWidgetContents)
        self.buttonGroup = QButtonGroup(MainWindow)
        self.buttonGroup.setObjectName(u"buttonGroup")
        self.buttonGroup.addButton(self.single_picture_button)
        self.single_picture_button.setObjectName(u"single_picture_button")
        sizePolicy3.setHeightForWidth(self.single_picture_button.sizePolicy().hasHeightForWidth())
        self.single_picture_button.setSizePolicy(sizePolicy3)
        self.single_picture_button.setMinimumSize(QSize(200, 0))
        self.single_picture_button.setAutoFillBackground(False)

        self.verticalLayout_7.addWidget(self.single_picture_button, 0, Qt.AlignmentFlag.AlignRight)

        self.hdr_drago_button = QRadioButton(self.scrollAreaWidgetContents)
        self.buttonGroup.addButton(self.hdr_drago_button)
        self.hdr_drago_button.setObjectName(u"hdr_drago_button")
        sizePolicy5 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        sizePolicy5.setHorizontalStretch(0)
        sizePolicy5.setVerticalStretch(0)
        sizePolicy5.setHeightForWidth(self.hdr_drago_button.sizePolicy().hasHeightForWidth())
        self.hdr_drago_button.setSizePolicy(sizePolicy5)
        self.hdr_drago_button.setMinimumSize(QSize(200, 0))
        self.hdr_drago_button.setAutoFillBackground(False)
        self.hdr_drago_button.setAutoRepeat(False)

        self.verticalLayout_7.addWidget(self.hdr_drago_button)

        self.hdr_robertson_button = QRadioButton(self.scrollAreaWidgetContents)
        self.buttonGroup.addButton(self.hdr_robertson_button)
        self.hdr_robertson_button.setObjectName(u"hdr_robertson_button")
        sizePolicy5.setHeightForWidth(self.hdr_robertson_button.sizePolicy().hasHeightForWidth())
        self.hdr_robertson_button.setSizePolicy(sizePolicy5)
        self.hdr_robertson_button.setMinimumSize(QSize(200, 0))
        self.hdr_robertson_button.setAutoFillBackground(False)

        self.verticalLayout_7.addWidget(self.hdr_robertson_button, 0, Qt.AlignmentFlag.AlignRight)

        self.verticalSpacer_7 = QSpacerItem(20, 15, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.verticalLayout_7.addItem(self.verticalSpacer_7)

        self.label_3 = QLabel(self.scrollAreaWidgetContents)
        self.label_3.setObjectName(u"label_3")

        self.verticalLayout_7.addWidget(self.label_3)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self.horizontalLayout_3.setContentsMargins(-1, 0, -1, -1)
        self.gamma_low = QPushButton(self.scrollAreaWidgetContents)
        self.gamma_low.setObjectName(u"gamma_low")
        sizePolicy6 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        sizePolicy6.setHorizontalStretch(0)
        sizePolicy6.setVerticalStretch(0)
        sizePolicy6.setHeightForWidth(self.gamma_low.sizePolicy().hasHeightForWidth())
        self.gamma_low.setSizePolicy(sizePolicy6)
        self.gamma_low.setMinimumSize(QSize(50, 0))
        self.gamma_low.setMaximumSize(QSize(100, 16777215))

        self.horizontalLayout_3.addWidget(self.gamma_low)

        self.gamma_mid = QPushButton(self.scrollAreaWidgetContents)
        self.gamma_mid.setObjectName(u"gamma_mid")
        sizePolicy6.setHeightForWidth(self.gamma_mid.sizePolicy().hasHeightForWidth())
        self.gamma_mid.setSizePolicy(sizePolicy6)
        self.gamma_mid.setMinimumSize(QSize(50, 0))

        self.horizontalLayout_3.addWidget(self.gamma_mid)

        self.gamma_high = QPushButton(self.scrollAreaWidgetContents)
        self.gamma_high.setObjectName(u"gamma_high")
        sizePolicy6.setHeightForWidth(self.gamma_high.sizePolicy().hasHeightForWidth())
        self.gamma_high.setSizePolicy(sizePolicy6)
        self.gamma_high.setMinimumSize(QSize(50, 0))

        self.horizontalLayout_3.addWidget(self.gamma_high)


        self.verticalLayout_7.addLayout(self.horizontalLayout_3)

        self.label_11 = QLabel(self.scrollAreaWidgetContents)
        self.label_11.setObjectName(u"label_11")

        self.verticalLayout_7.addWidget(self.label_11)

        self.crop_slider = QSlider(self.scrollAreaWidgetContents)
        self.crop_slider.setObjectName(u"crop_slider")
        self.crop_slider.setMaximum(100)
        self.crop_slider.setOrientation(Qt.Orientation.Horizontal)

        self.verticalLayout_7.addWidget(self.crop_slider)

        self.verticalSpacer_4 = QSpacerItem(10, 15, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.verticalLayout_7.addItem(self.verticalSpacer_4)

        self.label_8 = QLabel(self.scrollAreaWidgetContents)
        self.label_8.setObjectName(u"label_8")

        self.verticalLayout_7.addWidget(self.label_8)

        self.base_tv_slider = QSlider(self.scrollAreaWidgetContents)
        self.base_tv_slider.setObjectName(u"base_tv_slider")
        self.base_tv_slider.setMaximum(150)
        self.base_tv_slider.setValue(0)
        self.base_tv_slider.setOrientation(Qt.Orientation.Horizontal)
        self.base_tv_slider.setInvertedAppearance(False)
        self.base_tv_slider.setInvertedControls(False)
        self.base_tv_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.base_tv_slider.setTickInterval(5)

        self.verticalLayout_7.addWidget(self.base_tv_slider)

        self.label_9 = QLabel(self.scrollAreaWidgetContents)
        self.label_9.setObjectName(u"label_9")

        self.verticalLayout_7.addWidget(self.label_9)

        self.hdr_count_input = QSpinBox(self.scrollAreaWidgetContents)
        self.hdr_count_input.setObjectName(u"hdr_count_input")
        self.hdr_count_input.setMinimum(3)
        self.hdr_count_input.setMaximum(9)
        self.hdr_count_input.setSingleStep(2)

        self.verticalLayout_7.addWidget(self.hdr_count_input)

        self.label_10 = QLabel(self.scrollAreaWidgetContents)
        self.label_10.setObjectName(u"label_10")

        self.verticalLayout_7.addWidget(self.label_10)

        self.hdr_ev_input = QDoubleSpinBox(self.scrollAreaWidgetContents)
        self.hdr_ev_input.setObjectName(u"hdr_ev_input")
        self.hdr_ev_input.setDecimals(1)
        self.hdr_ev_input.setMaximum(10.000000000000000)
        self.hdr_ev_input.setSingleStep(0.333333000000000)
        self.hdr_ev_input.setValue(0.000000000000000)

        self.verticalLayout_7.addWidget(self.hdr_ev_input)

        self.verticalSpacer_6 = QSpacerItem(20, 15, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.verticalLayout_7.addItem(self.verticalSpacer_6)

        self.verticalSpacer_3 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_7.addItem(self.verticalSpacer_3)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.horizontalLayout.addWidget(self.scrollArea)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.IMAGE_SPACER_BOTTOM = QSpacerItem(15, 15, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.verticalLayout.addItem(self.IMAGE_SPACER_BOTTOM)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self.horizontalSpacer_3 = QSpacerItem(10, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_3)

        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self.start_button = QPushButton(self.centralwidget)
        self.start_button.setObjectName(u"start_button")
        sizePolicy7 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        sizePolicy7.setHorizontalStretch(0)
        sizePolicy7.setVerticalStretch(0)
        sizePolicy7.setHeightForWidth(self.start_button.sizePolicy().hasHeightForWidth())
        self.start_button.setSizePolicy(sizePolicy7)

        self.gridLayout.addWidget(self.start_button, 2, 0, 1, 1)

        self.stop_button = QPushButton(self.centralwidget)
        self.stop_button.setObjectName(u"stop_button")
        sizePolicy7.setHeightForWidth(self.stop_button.sizePolicy().hasHeightForWidth())
        self.stop_button.setSizePolicy(sizePolicy7)

        self.gridLayout.addWidget(self.stop_button, 2, 2, 1, 1)

        self.pause_button = QPushButton(self.centralwidget)
        self.pause_button.setObjectName(u"pause_button")
        sizePolicy7.setHeightForWidth(self.pause_button.sizePolicy().hasHeightForWidth())
        self.pause_button.setSizePolicy(sizePolicy7)

        self.gridLayout.addWidget(self.pause_button, 2, 1, 1, 1)

        self.hdr_preview_button = QPushButton(self.centralwidget)
        self.hdr_preview_button.setObjectName(u"hdr_preview_button")
        sizePolicy7.setHeightForWidth(self.hdr_preview_button.sizePolicy().hasHeightForWidth())
        self.hdr_preview_button.setSizePolicy(sizePolicy7)

        self.gridLayout.addWidget(self.hdr_preview_button, 1, 2, 1, 1)

        self.status_label = QLabel(self.centralwidget)
        self.status_label.setObjectName(u"status_label")

        self.gridLayout.addWidget(self.status_label, 0, 0, 1, 3)

        self.time_label = QLabel(self.centralwidget)
        self.time_label.setObjectName(u"time_label")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout.addWidget(self.time_label, 1, 1, 1, 1)

        self.label_12 = QLabel(self.centralwidget)
        self.label_12.setObjectName(u"label_12")
        self.label_12.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout.addWidget(self.label_12, 1, 0, 1, 1)


        self.verticalLayout_2.addLayout(self.gridLayout)

        self.progress_bar = QProgressBar(self.centralwidget)
        self.progress_bar.setObjectName(u"progress_bar")
        sizePolicy2.setHeightForWidth(self.progress_bar.sizePolicy().hasHeightForWidth())
        self.progress_bar.setSizePolicy(sizePolicy2)
        self.progress_bar.setMinimumSize(QSize(350, 0))
        self.progress_bar.setValue(24)

        self.verticalLayout_2.addWidget(self.progress_bar)


        self.horizontalLayout_2.addLayout(self.verticalLayout_2)

        self.settings_button = QToolButton(self.centralwidget)
        self.settings_button.setObjectName(u"settings_button")
        icon = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.MailMessageNew))
        self.settings_button.setIcon(icon)
        self.settings_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.settings_button.setArrowType(Qt.ArrowType.NoArrow)

        self.horizontalLayout_2.addWidget(self.settings_button, 0, Qt.AlignmentFlag.AlignBottom)

        self.horizontalSpacer = QSpacerItem(10, 10, QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)

        self.verticalLayout_4 = QVBoxLayout()
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(-1, -1, 0, -1)
        self.move_arm_to_0 = QPushButton(self.centralwidget)
        self.move_arm_to_0.setObjectName(u"move_arm_to_0")

        self.verticalLayout_4.addWidget(self.move_arm_to_0)

        self.move_arm_to_50 = QPushButton(self.centralwidget)
        self.move_arm_to_50.setObjectName(u"move_arm_to_50")

        self.verticalLayout_4.addWidget(self.move_arm_to_50)

        self.pushButton = QPushButton(self.centralwidget)
        self.pushButton.setObjectName(u"pushButton")

        self.verticalLayout_4.addWidget(self.pushButton)

        self.pushButton_2 = QPushButton(self.centralwidget)
        self.pushButton_2.setObjectName(u"pushButton_2")

        self.verticalLayout_4.addWidget(self.pushButton_2)


        self.horizontalLayout_2.addLayout(self.verticalLayout_4)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Maximum)

        self.verticalLayout_3.addItem(self.verticalSpacer)

        self.label = QLabel(self.centralwidget)
        self.label.setObjectName(u"label")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setIndent(0)

        self.verticalLayout_3.addWidget(self.label)

        self.lcd_crane_pos = QLCDNumber(self.centralwidget)
        self.lcd_crane_pos.setObjectName(u"lcd_crane_pos")
        sizePolicy8 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Maximum)
        sizePolicy8.setHorizontalStretch(0)
        sizePolicy8.setVerticalStretch(0)
        sizePolicy8.setHeightForWidth(self.lcd_crane_pos.sizePolicy().hasHeightForWidth())
        self.lcd_crane_pos.setSizePolicy(sizePolicy8)
        self.lcd_crane_pos.setMinimumSize(QSize(80, 40))
        self.lcd_crane_pos.setMaximumSize(QSize(16777215, 40))
        self.lcd_crane_pos.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.lcd_crane_pos.setFrameShape(QFrame.Shape.StyledPanel)
        self.lcd_crane_pos.setFrameShadow(QFrame.Shadow.Plain)
        self.lcd_crane_pos.setSmallDecimalPoint(False)
        self.lcd_crane_pos.setDigitCount(4)
        self.lcd_crane_pos.setMode(QLCDNumber.Mode.Dec)
        self.lcd_crane_pos.setSegmentStyle(QLCDNumber.SegmentStyle.Flat)
        self.lcd_crane_pos.setProperty(u"value", 0.000000000000000)

        self.verticalLayout_3.addWidget(self.lcd_crane_pos)


        self.horizontalLayout_4.addLayout(self.verticalLayout_3)

        self.horizontalSpacer_2 = QSpacerItem(5, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer_2)

        self.verticalLayout_6 = QVBoxLayout()
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Maximum)

        self.verticalLayout_6.addItem(self.verticalSpacer_2)

        self.label_2 = QLabel(self.centralwidget)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_2.setIndent(0)

        self.verticalLayout_6.addWidget(self.label_2)

        self.lcd_table_pos = QLCDNumber(self.centralwidget)
        self.lcd_table_pos.setObjectName(u"lcd_table_pos")
        sizePolicy8.setHeightForWidth(self.lcd_table_pos.sizePolicy().hasHeightForWidth())
        self.lcd_table_pos.setSizePolicy(sizePolicy8)
        self.lcd_table_pos.setMinimumSize(QSize(80, 40))
        self.lcd_table_pos.setMaximumSize(QSize(16777215, 40))
        self.lcd_table_pos.setFrameShape(QFrame.Shape.StyledPanel)
        self.lcd_table_pos.setFrameShadow(QFrame.Shadow.Plain)
        self.lcd_table_pos.setSmallDecimalPoint(False)
        self.lcd_table_pos.setDigitCount(4)
        self.lcd_table_pos.setSegmentStyle(QLCDNumber.SegmentStyle.Flat)

        self.verticalLayout_6.addWidget(self.lcd_table_pos)


        self.horizontalLayout_4.addLayout(self.verticalLayout_6)


        self.horizontalLayout_2.addLayout(self.horizontalLayout_4)

        self.horizontalSpacer_4 = QSpacerItem(10, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_4)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 975, 33))
        MainWindow.setMenuBar(self.menubar)
#if QT_CONFIG(shortcut)
        self.label_6.setBuddy(self.name_input)
        self.label_11.setBuddy(self.crop_slider)
        self.label_9.setBuddy(self.hdr_count_input)
        self.label_10.setBuddy(self.hdr_ev_input)
#endif // QT_CONFIG(shortcut)
        QWidget.setTabOrder(self.scrollArea, self.name_input)
        QWidget.setTabOrder(self.name_input, self.single_picture_button)
        QWidget.setTabOrder(self.single_picture_button, self.hdr_robertson_button)
        QWidget.setTabOrder(self.hdr_robertson_button, self.crop_slider)
        QWidget.setTabOrder(self.crop_slider, self.hdr_count_input)
        QWidget.setTabOrder(self.hdr_count_input, self.hdr_ev_input)
        QWidget.setTabOrder(self.hdr_ev_input, self.hdr_preview_button)
        QWidget.setTabOrder(self.hdr_preview_button, self.start_button)
        QWidget.setTabOrder(self.start_button, self.pause_button)
        QWidget.setTabOrder(self.pause_button, self.stop_button)

        self.retranslateUi(MainWindow)
        self.hdr_robertson_button.toggled.connect(self.hdr_count_input.setEnabled)
        self.single_picture_button.toggled.connect(self.hdr_ev_input.setDisabled)
        self.hdr_drago_button.toggled.connect(self.hdr_count_input.setEnabled)
        self.single_picture_button.toggled.connect(self.hdr_count_input.setDisabled)
        self.hdr_robertson_button.toggled.connect(self.hdr_ev_input.setEnabled)
        self.hdr_drago_button.toggled.connect(self.hdr_ev_input.setEnabled)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"DFGM - PIZZA", None))
        self.label_4.setText(QCoreApplication.translate("MainWindow", u"Aktueller Liveview:", None))
        self.image_label_left.setText("")
        self.label_5.setText(QCoreApplication.translate("MainWindow", u"Zuletzt verarbeitetes Bild:", None))
        self.image_label_right.setText("")
        self.label_6.setText(QCoreApplication.translate("MainWindow", u"Artikelnummer", None))
        self.name_input.setText("")
        self.name_input.setPlaceholderText(QCoreApplication.translate("MainWindow", u"00000", None))
        self.label_7.setText(QCoreApplication.translate("MainWindow", u"Bildmodus", None))
        self.single_picture_button.setText(QCoreApplication.translate("MainWindow", u"Einzelbild", None))
        self.hdr_drago_button.setText(QCoreApplication.translate("MainWindow", u"HDR Aufhellend", None))
        self.hdr_robertson_button.setText(QCoreApplication.translate("MainWindow", u"HDR Abdunkelnd", None))
        self.label_3.setText(QCoreApplication.translate("MainWindow", u"Gamma (Dunkle Teile: ~ Hoch)", None))
        self.gamma_low.setText(QCoreApplication.translate("MainWindow", u"Niedrig", None))
        self.gamma_mid.setText(QCoreApplication.translate("MainWindow", u"Mittel", None))
        self.gamma_high.setText(QCoreApplication.translate("MainWindow", u"Hoch", None))
        self.label_11.setText(QCoreApplication.translate("MainWindow", u"Crop", None))
        self.label_8.setText(QCoreApplication.translate("MainWindow", u"Basis Belichtungszeit", None))
        self.label_9.setText(QCoreApplication.translate("MainWindow", u"Anzahl HDR Bilder", None))
        self.label_10.setText(QCoreApplication.translate("MainWindow", u"Belichtungswert HDR", None))
        self.start_button.setText(QCoreApplication.translate("MainWindow", u"Start", None))
        self.stop_button.setText(QCoreApplication.translate("MainWindow", u"Stop", None))
        self.pause_button.setText(QCoreApplication.translate("MainWindow", u"Pause", None))
        self.hdr_preview_button.setText(QCoreApplication.translate("MainWindow", u"HDR Preview", None))
        self.status_label.setText(QCoreApplication.translate("MainWindow", u"Status", None))
        self.time_label.setText(QCoreApplication.translate("MainWindow", u"10:00 Minuten", None))
        self.label_12.setText(QCoreApplication.translate("MainWindow", u"~ Verbleibend:", None))
#if QT_CONFIG(tooltip)
        self.settings_button.setToolTip(QCoreApplication.translate("MainWindow", u"Einstellungen", None))
#endif // QT_CONFIG(tooltip)
        self.settings_button.setText(QCoreApplication.translate("MainWindow", u"...", None))
        self.move_arm_to_0.setText(QCoreApplication.translate("MainWindow", u"Vertikal: 0\u00b0", None))
        self.move_arm_to_50.setText(QCoreApplication.translate("MainWindow", u"Vertikal: 45\u00b0", None))
        self.pushButton.setText(QCoreApplication.translate("MainWindow", u"Vertikal: 85\u00b0", None))
        self.pushButton_2.setText(QCoreApplication.translate("MainWindow", u"Sweep", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"Vertikal", None))
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"Horizontal", None))
    # retranslateUi

