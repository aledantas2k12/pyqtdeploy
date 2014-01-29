# Copyright (c) 2014 Riverbank Computing Limited.
#
# This file is part of pyqtdeploy.
#
# This file may be used under the terms of the GNU General Public License
# v2 or v3 as published by the Free Software Foundation which can be found in
# the files LICENSE-GPL2.txt and LICENSE-GPL3.txt included in this package.
# In addition, as a special exception, Riverbank gives you certain additional
# rights.  These rights are described in the Riverbank GPL Exception, which
# can be found in the file GPL-Exception.txt in this package.
#
# This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
# WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.


import fnmatch
import os

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (QFileDialog, QGroupBox, QHBoxLayout, QPushButton,
        QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator, QVBoxLayout)

from ..project import MfsDirectory, MfsFile


class MfsPackageEditor(QGroupBox):
    """ A memory file system package editor. """

    # Emitted when the package has changed.
    package_changed = pyqtSignal()

    def __init__(self, title):
        """ Initialise the editor. """

        super().__init__(title)

        self._package = None
        self._title = title
        self._previous_scan = ''

        layout = QHBoxLayout()

        self._package_edit = QTreeWidget()
        self._package_edit.setHeaderLabels(["Name", "Included"])
        self._package_edit.itemChanged.connect(self._package_changed)

        header = self._package_edit.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, header.Stretch)
        header.setSectionResizeMode(1, header.ResizeToContents)

        layout.addWidget(self._package_edit, stretch=1)

        scan_layout = QVBoxLayout()

        scan_layout.addWidget(QPushButton("Scan...", clicked=self._scan))

        self._exclusions_edit = QTreeWidget()
        self._exclusions_edit.setHeaderLabels(["Exclusions"])
        self._exclusions_edit.setEditTriggers(
                QTreeWidget.DoubleClicked|QTreeWidget.SelectedClicked|
                        QTreeWidget.EditKeyPressed)
        self._exclusions_edit.setRootIsDecorated(False)
        self._exclusions_edit.itemChanged.connect(self._exclusion_changed)

        scan_layout.addWidget(self._exclusions_edit)

        layout.addLayout(scan_layout)

        self.setLayout(layout)

    def setPackage(self, package):
        """ Update the editor with the contents of the given package. """

        # Save the package.
        self._package = package

        # Set the package itself.
        self._visualise()

        # Set the exclusions.
        self._exclusions_edit.clear()

        for exclude in package.exclusions:
            self._add_exclusion_item(QTreeWidgetItem([exclude]))

        # Add one to be edited to create a new entry.
        self._add_exclusion_item(QTreeWidgetItem())

    def _add_exclusion_item(self, itm):
        """ Add a QTreeWidgetItem that holds an exclusion. """

        itm.setFlags(
                Qt.ItemIsSelectable|Qt.ItemIsEditable|Qt.ItemIsEnabled|
                        Qt.ItemNeverHasChildren)

        self._exclusions_edit.addTopLevelItem(itm)

    def _exclusion_changed(self, itm, column):
        """ Invoked when an exclusion has changed. """

        exc_edit = self._exclusions_edit

        new_exc = itm.data(column, Qt.DisplayRole)
        itm_index = exc_edit.indexOfTopLevelItem(itm)

        if new_exc != '':
            # See if we have added a new one.
            if itm_index == exc_edit.topLevelItemCount() - 1:
                self._add_exclusion_item(QTreeWidgetItem())
        else:
            # It is empty so remove it.
            exc_edit.takeTopLevelItem(itm_index)

        # Save the new exclusions.
        self._package.exclusions = [
                exc_edit.topLevelItem(i).data(column, Qt.DisplayRole)
                        for i in range(exc_edit.topLevelItemCount() - 1)]

        self.package_changed.emit()

    def _scan(self, value):
        """ Invoked when the user clicks on the scan button. """

        root = QFileDialog.getExistingDirectory(self._package_edit,
                self._title, self._previous_scan)

        if root == '':
            return

        self._previous_scan = root

        # Save the included state of any existing contents so that they can be
        # restored after the scan.
        old_excluded = []
        it = QTreeWidgetItemIterator(self._package_edit)

        # Skip the root of the tree.
        it += 1

        itm = it.value()
        while itm is not None:
            if not itm._mfs_item.included:
                rel_path = [itm.data(0, Qt.DisplayRole)]

                parent = itm.parent()
                while parent is not None:
                    rel_path.append(parent.data(0, Qt.DisplayRole))
                    parent = parent.parent()

                rel_path.reverse()

                old_excluded.append(os.path.join(*rel_path))

            it += 1
            itm = it.value()

        # Walk the package.
        self._package.name = os.path.basename(root)
        self._add_to_container(self._package, root, [], old_excluded)
        self._visualise()

        self.package_changed.emit()

    def _add_to_container(self, container, path, dir_stack, old_excluded):
        """ Add the files and directories of a package or sub-package to a
        container.
        """

        dir_stack.append(os.path.basename(path))
        contents = []

        for name in os.listdir(path):
            # Apply any exclusions.
            for exc in self._package.exclusions:
                if fnmatch.fnmatch(name, exc):
                    name = None
                    break

            if name is None:
                continue

            # See if we already know the included state.
            rel_path = os.path.join(os.path.join(*dir_stack), name)
            included = (rel_path not in old_excluded)

            # Add the content.
            full_name = os.path.join(path, name)

            if os.path.isdir(full_name):
                mfs = MfsDirectory(name, included)
                self._add_to_container(mfs, full_name, dir_stack, old_excluded)
            elif os.path.isfile(full_name):
                mfs = MfsFile(name, included)
            else:
                continue

            contents.append(mfs)

        contents.sort(key=lambda mfs: mfs.name.lower())
        container.contents = contents
        dir_stack.pop()

    def _visualise(self):
        """ Update the GUI with the package content. """

        blocked = self._package_edit.blockSignals(True)

        self._package_edit.clear()

        root_itm = QTreeWidgetItem([self._package.name])
        self._package_edit.addTopLevelItem(root_itm)

        self._visualise_contents(self._package.contents, root_itm)

        root_itm.setExpanded(True)
        self._package_edit.scrollToItem(root_itm,
                self._package_edit.PositionAtTop)

        self._package_edit.blockSignals(blocked)

    def _visualise_contents(self, contents, parent):
        """ Visualise the contents for a parent. """

        for content in contents:
            itm = QTreeWidgetItem(parent, [content.name])
            itm.setCheckState(1, Qt.Checked if content.included else Qt.Unchecked)
            itm._mfs_item = content

            if isinstance(content, MfsDirectory):
                self._visualise_contents(content.contents, itm)
                itm.setExpanded(True)

    def _package_changed(self, itm, column):
        """ Invoked when part of the package changes. """

        itm._mfs_item.included = (itm.checkState(1) == Qt.Checked)

        self.package_changed.emit()
