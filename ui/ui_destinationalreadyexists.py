# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'DestinationAlreadyExists.ui'
##
## Created by: Qt User Interface Compiler version 6.10.2
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QDialogButtonBox,
    QLabel, QSizePolicy, QSpacerItem, QVBoxLayout,
    QWidget)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.resize(255, 200)
        self.verticalLayout = QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.label = QLabel(Dialog)
        self.label.setObjectName(u"label")
        self.label.setWordWrap(True)

        self.verticalLayout.addWidget(self.label)

        self.verticalSpacer = QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.verticalLayout.addItem(self.verticalSpacer)

        self.label_article_number = QLabel(Dialog)
        self.label_article_number.setObjectName(u"label_article_number")

        self.verticalLayout.addWidget(self.label_article_number)

        self.verticalSpacer_3 = QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.verticalLayout.addItem(self.verticalSpacer_3)

        self.label_2 = QLabel(Dialog)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setWordWrap(True)

        self.verticalLayout.addWidget(self.label_2)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer_2)

        self.buttonBox = QDialogButtonBox(Dialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.No|QDialogButtonBox.StandardButton.Yes)

        self.verticalLayout.addWidget(self.buttonBox)


        self.retranslateUi(Dialog)
        self.buttonBox.rejected.connect(Dialog.reject)
        self.buttonBox.accepted.connect(Dialog.accept)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"Bereits Vergeben", None))
#if QT_CONFIG(accessibility)
        Dialog.setAccessibleName("")
#endif // QT_CONFIG(accessibility)
        self.label.setText(QCoreApplication.translate("Dialog", u"F\u00fcr die Artikelnummer:", None))
        self.label_article_number.setText(QCoreApplication.translate("Dialog", u"Artikelnummer", None))
        self.label_2.setText(QCoreApplication.translate("Dialog", u"Ist bereits ein Ordner angelegt. Soll dieser Ordner \u00fcberschrieben werden?", None))
    # retranslateUi

