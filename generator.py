# Python libraries
import sys
import os
import json
from pathlib import Path
# The __debug__ lines are ignored in the compilation
if __debug__:
    from timeit import default_timer as timer
# Image manipulation libraries
import layeredimage.io as li
from PIL import Image
# GUI libraries
from PySide6 import QtCore
from PySide6.QtWidgets import (QWidget, QMainWindow, QApplication, QVBoxLayout,
    QHBoxLayout, QComboBox, QLabel, QPushButton, QMessageBox, QCheckBox,
    QProgressBar, QSplashScreen, QStyledItemDelegate, QCompleter, QLineEdit,
    QDialog, QFileDialog)
from PySide6.QtGui import QIcon, QPixmap, QScreen
from PySide6.QtCore import QObject, Qt, QThread, Signal

# Absolute path to the current folder as constant for easy access
THISDIR = str(Path(__file__).resolve().parent)
sys.path.insert(0, os.path.dirname(THISDIR))


class Worker(QObject):
    finished = Signal()
    update_progress = Signal(int)

    def __init__(self, tablecloth, sec_layers, teams_layers, east_id, south_id,
        west_id, north_id, technical_lines=False, save_to=None, bg_image=None,
        parent=None):
        super().__init__()
        self.tablecloth = tablecloth
        self.sec_layers = sec_layers
        self.teams_layers = teams_layers
        self.east_id = east_id
        self.south_id = south_id
        self.west_id = west_id
        self.north_id = north_id
        self.technical_lines = technical_lines
        self.save_to_route = save_to
        self.bg_image = bg_image

    def run(self):
        # Compiles all the layers
        if __debug__:
            start = timer()
        layers = []
        # Make technical lines visible
        # Append all the non-team layers
        if self.bg_image is not None:
            custom_bg = Image.open(self.bg_image)
            layers.append(custom_bg)
        else:
            layers.append(self.sec_layers[1].image)
        layers.append(self.sec_layers[0].image)
        if self.technical_lines:
            layers.append(self.sec_layers[2].image)
        self.update_progress.emit(10)

        # Makes the top image visible
        layers.append(self.teams_layers["TEAM_%d" % self.west_id][1].image)
        # Makes the left image visible
        layers.append(self.teams_layers["TEAM_%d" % self.north_id][0].image)
        # Makes the right image visible
        layers.append(self.teams_layers["TEAM_%d" % self.south_id][2].image)
        # Makes the bottom image visible
        layers.append(self.teams_layers["TEAM_%d" % self.east_id][3].image)

        self.update_progress.emit(40)

        # Let's check the file does not exist first
        if os.path.exists(self.save_to_route+"/Table_Dif.jpg"):
            os.remove(self.save_to_route+"/Table_Dif.jpg")

        self.update_progress.emit(50)
        # Create a new image and save the layers
        final_tablecloth = Image.new("RGB", layers[0].size)
        # Paste the layers onto the tablecloth
        for ly in layers:
            final_tablecloth.paste(ly, (0,0), ly)
        self.update_progress.emit(75)
        # Save
        final_tablecloth.save(self.save_to_route+"/Table_Dif.jpg")
        self.update_progress.emit(90)
        # If it exists, it means that the process was successful
        if os.path.exists(self.save_to_route+"/Table_Dif.jpg"):
            if __debug__:
                end = timer()
                print("This took %d seconds." % (end - start))
            self.update_progress.emit(100)
            self.finished.emit()


class TableClothGenerator(QMainWindow):
    def __init__(self, parent=None):

        super().__init__(parent)

        # Main UI settings
        self.setWindowTitle('Tablecloth Generator')
        self.setWindowIcon(QIcon('icon.ico'))
        self.centralWidget = QWidget()

        self.setCentralWidget(self.centralWidget)
        self.resize(350, 350)
        self.center()

        self.MainUI()

    def MainUI(self):

        # Loading this big ass file at the start to save time
        self.tablecloth = li.openLayer_PDN(THISDIR + "\\league_tablecloth.pdn")
        # Sets the team dictionary and start the counters
        self.teams_layers = {}
        # It goes backwards
        team_ids = 15
        team_num = 0
        num_layers = 1
        # Get the three other layers
        self.sec_layers = self.tablecloth.layers[:3]
        # Ignores the first 3 layers since they are not needed
        layers = self.tablecloth.layers[3:]
        for layer in layers:
            if team_ids == 1:
                break # Gotta find a better way to do this
            define_team = "TEAM_%d" % (team_ids - 1)
            self.teams_layers[define_team] = layers[team_num*4:num_layers*4]
            team_ids -= 1
            team_num += 1
            num_layers += 1

        # Obtain and List the teams
        fp_teams = open(THISDIR + "\\team-information.json", "r",
                            encoding="utf-8").read()
        fp_teams = json.loads(fp_teams)
        self.teams = fp_teams["teams"]
        self.players = fp_teams["players"]
        self.save_to = fp_teams["save_route"]
        # NOTE: This is more of a workaround to make the program efficient
        # since the current imagelayer library is dogshit at speed.
        # In the future this will change so that the bg image gets updated
        # *to* the layer and not having to do this horrible path loading.
        self.bg_image = fp_teams["image_route"]
        self.players_combobox = QComboBox()
        for team, members in self.players.items():
            for member in members:
                self.players_combobox.addItem(member, team)
        self.players_combobox.setEditable(True)
        self.players_combobox.completer()\
                             .setCompletionMode(QCompleter.PopupCompletion)
        self.players_combobox.setInsertPolicy(QComboBox.NoInsert)
        # Set up the GUI
        self.statusBar().showMessage("Remember: Rig responsibly.")
        # Bottom (EAST)
        self.label_east = QLabel(self)
        self.label_east.setText("East Seat")
        self.label_east.setAlignment(QtCore.Qt.AlignCenter)
        self.image_east = QLabel(self)
        self.image_east.setPixmap(QPixmap("logos/team1.png").scaled(100,100))
        self.image_east.setAlignment(QtCore.Qt.AlignCenter)
        self.search_east = QLineEdit()
        self.search_east.setAlignment(QtCore.Qt.AlignCenter)
        self.search_east.editingFinished.connect(
            lambda: self.searchPlayer(self.search_east.text(),
                                      self.cloth_east))
        self.cloth_east = QComboBox()
        self.cloth_east.setModel(self.players_combobox.model())
        self.cloth_east.currentIndexChanged.connect(
            lambda: self.switchImage(self.cloth_east, self.image_east))
        # Right (SOUTH)
        self.label_south = QLabel(self)
        self.label_south.setText("South Seat")
        self.label_south.setAlignment(QtCore.Qt.AlignCenter)
        self.image_south = QLabel(self)
        self.image_south.setPixmap(QPixmap("logos/team1.png").scaled(100,100))
        self.image_south.setAlignment(QtCore.Qt.AlignCenter)
        self.image_south.show()
        self.search_south = QLineEdit()
        self.search_south.setAlignment(QtCore.Qt.AlignCenter)
        self.search_south.editingFinished.connect(
            lambda: self.searchPlayer(self.search_south.text(),
                                      self.cloth_south))
        self.cloth_south = QComboBox()
        self.cloth_south.setModel(self.players_combobox.model())
        self.cloth_south.currentIndexChanged.connect(
            lambda: self.switchImage(self.cloth_south, self.image_south))
        # Top (WEST)
        self.label_west = QLabel(self)
        self.label_west.setText("West Seat")
        self.label_west.setAlignment(QtCore.Qt.AlignCenter)
        self.image_west = QLabel(self)
        self.image_west.setPixmap(QPixmap("logos/team1.png").scaled(100,100))
        self.image_west.setAlignment(QtCore.Qt.AlignCenter)
        self.image_west.show()
        self.cloth_west = QComboBox()
        self.search_west = QLineEdit()
        self.search_west.setAlignment(QtCore.Qt.AlignCenter)
        self.search_west.editingFinished.connect(
            lambda: self.searchPlayer(self.search_west.text(),
                                      self.cloth_west))
        self.cloth_west.setModel(self.players_combobox.model())
        self.cloth_west.currentIndexChanged.connect(
            lambda: self.switchImage(self.cloth_west, self.image_west))
        # Left (NORTH)
        self.label_north = QLabel(self)
        self.label_north.setText("North Seat")
        self.label_north.setAlignment(QtCore.Qt.AlignCenter)
        self.image_north = QLabel(self)
        self.image_north.setPixmap(QPixmap("logos/team1.png").scaled(100,100))
        self.image_north.setAlignment(QtCore.Qt.AlignCenter)
        self.image_north.show()
        self.cloth_north = QComboBox()
        self.search_north = QLineEdit()
        self.search_north.setAlignment(QtCore.Qt.AlignCenter)
        self.search_north.editingFinished.connect(
            lambda: self.searchPlayer(self.search_north.text(),
                                      self.cloth_north))
        self.cloth_north.setModel(self.players_combobox.model())
        self.cloth_north.currentIndexChanged.connect(
            lambda: self.switchImage(self.cloth_north, self.image_north))
        # Technical lines
        self.technical_lines = QCheckBox("Show Technical lines", self)
        # Generate button
        self.generate = QPushButton(self)
        self.generate.setText("Generate Tablecloth")
        self.generate.clicked.connect(self.ConfirmDialog)
        # Add custom mat
        self.custom_mat = QPushButton(self)
        self.custom_mat.setText("Add Mat")
        self.custom_mat.clicked.connect(self.MatDialog)

        # Create the layout
        hbox = QHBoxLayout(self)
        self.setLayout(hbox)
        vbox1 = QVBoxLayout(self)
        self.setLayout(vbox1)
        vbox2 = QVBoxLayout(self)
        self.setLayout(vbox2)
        vbox1.setAlignment(QtCore.Qt.AlignCenter)
        vbox1.setAlignment(QtCore.Qt.AlignTop)
        vbox2.setAlignment(QtCore.Qt.AlignCenter)
        vbox2.setAlignment(QtCore.Qt.AlignTop)
        # Vertical layout (Bottom, right)
        vbox1.addWidget(self.label_east)
        vbox1.addWidget(self.image_east)
        vbox1.addWidget(self.search_east)
        vbox1.addWidget(self.cloth_east)
        vbox1.addWidget(self.label_south)
        vbox1.addWidget(self.image_south)
        vbox1.addWidget(self.search_south)
        vbox1.addWidget(self.cloth_south)
        # Add the option for technical lines
        vbox1.addWidget(self.technical_lines)
        # Add the option to add a custom mat
        vbox1.addWidget(self.custom_mat)
        # Vertical layout 2 (Top, left)
        vbox2.addWidget(self.label_west)
        vbox2.addWidget(self.image_west)
        vbox2.addWidget(self.search_west)
        vbox2.addWidget(self.cloth_west)
        vbox2.addWidget(self.label_north)
        vbox2.addWidget(self.image_north)
        vbox2.addWidget(self.search_north)
        vbox2.addWidget(self.cloth_north)
        # Add the generate button
        vbox2.addWidget(self.generate)
        # Add the layouts to be show
        hbox.addLayout(vbox1)
        hbox.addLayout(vbox2)
        self.centralWidget.setLayout(hbox)

        # Create the window
        self.show()

    def switchImage(self, cloth, image):
        # It shows you the team logo. No way you can miss those, right?
        team_id = self.searchTeamID(cloth, True)
        image.setPixmap(QPixmap(
            "logos/team%d.png" % team_id).scaled(100,100))

    def searchPlayer(self, text, combobox):
        # It even searches the player for you. What more could you want?
        search_index = combobox.findText(text, QtCore.Qt.MatchContains)
        if search_index == -1:
            QMessageBox.warning(self, "Error", "No player found")
        else:
            combobox.setCurrentIndex(search_index)

    def MatDialog(self):

        mat_dialog = QFileDialog(self)
        mat_dialog = QFileDialog.getOpenFileName(filter="Images (*.png *.jpg)",
            selectedFilter="Images (*.png *.jpg)")

        if mat_dialog[0] != "":
            self.MatPreviewWindow(mat_dialog[0])

    def MatPreviewWindow(self, image):
        self.mat_wid = QWidget()
        self.mat_wid.resize(600, 600)
        self.mat_wid.setWindowTitle("Background preview")

        mat_preview_title = QLabel(self)
        mat_preview_title.setText("Selected image (1/4 scale)")
        mat_preview = QLabel(self)
        mat_preview.setPixmap(QPixmap(image).scaled(512,512))
        confirm = QPushButton(self)
        confirm.setText("Confirm")
        confirm.clicked.connect(
            lambda: self.changeMatImage(image))

        vbox = QVBoxLayout(self)
        vbox.setAlignment(QtCore.Qt.AlignCenter)
        vbox.addWidget(mat_preview_title)
        vbox.addWidget(mat_preview)
        vbox.addWidget(confirm)
        self.mat_wid.setLayout(vbox)

        self.mat_wid.show()

    def changeMatImage(self, image):

        new_bg = Image.open(image)
        if new_bg.size != (2048, 2048):
            new_bg = new_bg.resize((2048, 2048))
        if new_bg.mode != "RGBA":
            new_bg = new_bg.convert("RGBA")
        self.sec_layers[1].image = new_bg
        if self.save_to is not None:
            new_bg.save(self.save_to+"\\mat_bg.png")
            self.bg_image = self.save_to+"\\mat_bg.png"
        else:
            new_bg.save(THISDIR+"\\mat_bg.png")
            self.bg_image = THISDIR+"\\mat_bg.png"
        self.mat_wid.close()

    def ConfirmDialog(self):
        # Double check for double idiots
        mbox = QMessageBox()

        mbox.setWindowTitle("Tablecloth Generator")
        mbox.setText("Confirm your selection:")
        mbox.setInformativeText("<strong>East:</strong> %s <i>(%s)</i><br> \
            <strong>South:</strong> %s <i>(%s)</i><br> <strong>West:</strong>\
            %s <i>(%s)</i><br> <strong>North:</strong> %s <i>(%s)</i> %s" %
            (self.cloth_east.currentText(),
             self.teams[self.searchTeamID(self.cloth_east)],
             self.cloth_south.currentText(),
             self.teams[self.searchTeamID(self.cloth_south)],
             self.cloth_west.currentText(),
             self.teams[self.searchTeamID(self.cloth_west)],
             self.cloth_north.currentText(),
             self.teams[self.searchTeamID(self.cloth_north)],
             "<br><b>Technical Lines enabled.</b>" if self.technical_lines\
             .isChecked() else ""))
        mbox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)

        result = mbox.exec()
        if result == QMessageBox.Ok:
            # Freeze the program to avoid a dumbass clicking several times
            # and crashing
            self.statusBar().showMessage('Generating image...')
            self.progress_bar = QProgressBar()
            self.progress_bar.minimum = 0
            self.progress_bar.maximum = 100
            self.progress_bar.setValue(0)
            self.progress_bar.setTextVisible(False)
            self.progress_bar.setGeometry(50, 50, 10, 10)
            self.progress_bar.setAlignment(QtCore.Qt.AlignRight)
            self.progress_bar.adjustSize()
            self.statusBar().addPermanentWidget(self.progress_bar)
            self.changeAppStatus(False)
            # Confirm and go directly to generate the image.
            self.generateImage()

    def GeneratedDialog(self):

        self.statusBar().showMessage('Tablecloth generated. Happy rigging!')
        self.statusBar().removeWidget(self.progress_bar)
        # Now you can go back to rigging
        self.changeAppStatus(True)


        mbox = QMessageBox()

        mbox.setWindowTitle("Tablecloth Generator")
        mbox.setText("Tablecloth Generated!")
        mbox.setStandardButtons(QMessageBox.Ok)

        mbox.exec()

    def UpdateStatus(self, status):
        self.progress_bar.setValue(status)

    def generateImage(self):

        if self.save_to is None:
            self.save_to = THISDIR

        save_to_route = QFileDialog.getExistingDirectory(self,
            "Where to save the image", self.save_to, QFileDialog.ShowDirsOnly \
                | QFileDialog.DontResolveSymlinks)

        if self.save_to != save_to_route:
            temp_file = open(THISDIR + "\\team-information.json", "r",
                                            encoding="utf-8")
            fp_teams = json.loads(temp_file.read())
            fp_teams["save_route"] = save_to_route
            fp_teams["image_route"] = self.bg_image
            new_file = open(THISDIR + "\\team-information.json", "w+",
                                            encoding="utf-8")
            new_file.write(json.dumps(fp_teams, indent=4))
            new_file.close()


        self.thread = QThread()
        east_id = self.searchTeamID(self.cloth_east, True)
        south_id = self.searchTeamID(self.cloth_south, True)
        west_id = self.searchTeamID(self.cloth_west, True)
        north_id = self.searchTeamID(self.cloth_north, True)
        self.worker = Worker(self.tablecloth, self.sec_layers,
           self.teams_layers, east_id, south_id, west_id, north_id,
           self.technical_lines.isChecked(), save_to_route, self.bg_image)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.update_progress.connect(self.UpdateStatus)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.GeneratedDialog)
        self.thread.start()

    def changeAppStatus(self, status):
        # True for enable, False for disable.
        self.cloth_east.setEnabled(status)
        self.search_east.setEnabled(status)
        self.cloth_south.setEnabled(status)
        self.search_south.setEnabled(status)
        self.cloth_west.setEnabled(status)
        self.search_west.setEnabled(status)
        self.cloth_north.setEnabled(status)
        self.search_north.setEnabled(status)
        self.generate.setEnabled(status)

    def searchTeamID(self, cloth, plus_one=False):
        team_id = self.teams.index(cloth.itemData(cloth.currentIndex()))
        if plus_one:
            team_id += 1
        return team_id

    def center(self):
        qr = self.frameGeometry()
        cp = QScreen().availableGeometry().center()
        qr.moveCenter(cp)

def main():

    app = QApplication(sys.argv)
    pixmap = QPixmap("icon.ico")
    splash = QSplashScreen(pixmap)
    splash.show()
    if __debug__:
        start = timer()
    ex = TableClothGenerator()
    app.processEvents()
    ex.show()
    splash.finish(ex)
    if __debug__:
        end = timer()
        print("This took %d seconds." % (end - start))
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
