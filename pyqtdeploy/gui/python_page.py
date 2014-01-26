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


from PyQt5.QtWidgets import QFormLayout, QWidget

from .file_name_edit import FileNameEdit


class PythonPage(QWidget):
    """ The GUI for the Python configuration page of a project. """

    # The page's label.
    label = "Python Configuration"

    @property
    def project(self):
        """ The project property getter. """

        return self._project

    @project.setter
    def project(self, value):
        """ The project property setter. """

        if self._project != value:
            self._project = value
            self._update_page()

    def __init__(self):
        """ Initialise the page. """

        super().__init__()

        self._project = None

        # Create the page's GUI.
        form = QFormLayout()

        self._target_inc_edit = FileNameEdit("Target Include Directory",
                placeholderText="Directory name",
                whatsThis="The target interpreter's include directory.",
                textEdited=self._target_inc_changed, directory=True)
        form.addRow("Target include directory", self._target_inc_edit)

        self._target_lib_edit = FileNameEdit("Python Library",
                placeholderText="Library name",
                whatsThis="The target interpreter's Python library.",
                textEdited=self._target_lib_changed)
        form.addRow("Target Python library", self._target_lib_edit)

        self.setLayout(form)

    def _update_page(self):
        """ Update the page using the current project. """

        project = self.project

        self._target_inc_edit.setText(project.python_target_include_dir)
        self._target_lib_edit.setText(project.python_target_library)

    def _target_inc_changed(self, value):
        """ Invoked when the user edits the target include directory name. """

        self.project.python_target_include_dir = value
        self.project.modified = True

    def _target_lib_changed(self, value):
        """ Invoked when the user edits the target Python library name. """

        self.project.python_target_library = value
        self.project.modified = True
